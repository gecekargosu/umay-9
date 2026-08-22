"""Deterministic, evidence-based project audit helpers.

The audit layer deliberately separates discovered commands from commands that
were actually executed. A finding is only reported as a concrete issue when
there is file/line/test evidence for it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import core.agent_tools as tools


def discover_validation_commands() -> list[dict[str, Any]]:
    root = tools.ACTIVE_WORKSPACE
    commands: list[dict[str, Any]] = []
    if (root / "tests").is_dir() or (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
        commands.append({"kind": "python_tests", "command": "python -m pytest -q", "status": "DISCOVERED"})
    package = root / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
            for name in ("lint", "test", "build"):
                if name in scripts:
                    commands.append({"kind": f"npm_{name}", "command": f"npm run {name}", "status": "DISCOVERED"})
        except (OSError, UnicodeError, json.JSONDecodeError):
            commands.append({"kind": "package_json", "command": "package.json parse", "status": "ERROR"})
    if (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists() or (root / "compose.yml").exists() or (root / "compose.yaml").exists():
        commands.append({"kind": "docker", "command": "docker compose config", "status": "DISCOVERED"})
    return commands


def _syntax_findings() -> list[dict[str, Any]]:
    findings = []
    for f in tools.ACTIVE_WORKSPACE.rglob("*.py"):
        if any(x in {"__pycache__", ".venv", "node_modules", "chroma", ".git"} for x in f.parts):
            continue
        try:
            compile(f.read_text(encoding="utf-8", errors="ignore"), str(f), "exec")
        except SyntaxError as exc:
            findings.append({
                "id": f"PY-SYNTAX-{len(findings)+1:03d}",
                "severity": "P0",
                "category": "syntax",
                "path": str(f.relative_to(tools.ACTIVE_WORKSPACE)),
                "line": exc.lineno,
                "message": exc.msg,
                "evidence": f"Python compile failed at line {exc.lineno}: {exc.msg}",
            })
    return findings


def run_static_audit() -> dict[str, Any]:
    findings = _syntax_findings()
    test = tools.run_test_suite("python -m pytest -q") if (tools.ACTIVE_WORKSPACE / "tests").exists() else {"status": "NOT_RUN"}
    if test.get("status") == "FAIL":
        findings.append({
            "id": f"TEST-FAIL-{len(findings)+1:03d}",
            "severity": "P1",
            "category": "tests",
            "path": "tests",
            "line": None,
            "message": "Test suite failed.",
            "evidence": test.get("summary", "")[-4000:],
        })
    return {
        "workspace": str(tools.ACTIVE_WORKSPACE),
        "project": tools.inspect_project(),
        "findings": findings,
        "syntax_findings": findings,
        "tests": test,
        "validation_commands": discover_validation_commands(),
    }


def findings_to_todo(audit: dict) -> list[str]:
    out = []
    for f in audit.get("findings", audit.get("syntax_findings", [])):
        location = f"{f.get('path')}:{f.get('line')}" if f.get("line") else str(f.get("path"))
        out.append(f"- [ ] {f.get('severity','P2')} {location} — {f.get('message','')}")
        if f.get("evidence"):
            out.append(f"  - Evidence: {f['evidence'][:800]}")
    return out


def audit_summary(audit: dict) -> dict[str, Any]:
    findings = audit.get("findings", [])
    return {
        "workspace": audit.get("workspace"),
        "finding_count": len(findings),
        "severity_counts": {level: sum(1 for f in findings if f.get("severity") == level) for level in ("P0", "P1", "P2", "P3")},
        "tests": audit.get("tests", {}).get("status", "NOT_RUN"),
        "validation_commands": audit.get("validation_commands", []),
    }

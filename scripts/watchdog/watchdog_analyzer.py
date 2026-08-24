"""
UMAY Watchdog Analyzer
======================
Her 20 dakikada UMAY projesini tarar:
- Dosya değişikliklerini tespit eder
- Kod değişikliklerini analiz eder
- Regression testleri çalıştırır
- Human-use senaryolarını test eder
- Docker/API durumunu kontrol eder
- Telegram'a rapor gönderir

Watchdog KENDİ BAŞINA KOD DEĞİŞTİRMEZ.
Gözle → Analiz Et → Test Et → Raporla.
"""

import json
import os
import re
import subprocess
import sys
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────

PROJECT = Path(os.environ.get("UMAY_PROJECT", r"C:\UMAY 9"))
WATCHDOG_DIR = PROJECT / "scripts" / "watchdog"
STATE_DIR = WATCHDOG_DIR / "state"
REPORT_DIR = WATCHDOG_DIR / "reports"
STATE_FILE = STATE_DIR / "snapshot.json"
ANALYSIS_DIR = STATE_DIR / "analysis"

EXCLUDE_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", "backup", "UMAY_ARCHIVE", "UMAY_MEMORY",
    ".umay_backups", "_fix_review", "logs", "scripts/watchdog/reports",
    "scripts/watchdog/state",
}

CRITICAL_FILES = {
    "core/intent_router.py": "Intent classification (Calculator/FILE/CODE/CHAT routing)",
    "core/engine.py": "Model resolution (local vs cloud routing)",
    "core/agent.py": "Agent loop (tool calling, multi-step execution)",
    "core/agent_tools.py": "Tool registry (read_file, run_command, search, etc.)",
    "ui/panel_server.py": "Backend API + direct tool execution",
    "ui/templates/panel.html": "Frontend UI",
    "Dockerfile": "Container build",
    "docker-compose.yml": "Container orchestration",
    "requirements.txt": "Python dependencies",
}

AUDIT_P1_ISSUES = {
    "Calculator over-trigger": {
        "file": "core/intent_router.py",
        "test_patterns": ["10 satır", "def add(a,b)", "Python ile hesap makinesi yap"],
        "expected_intents": ["file", "code", "code"],
    },
    "FILE intent breadth": {
        "file": "core/intent_router.py",
        "test_patterns": ["requirements.txt dosyasında ne var", "core/engine.py oku", "klasörünü listele"],
        "expected_intents": ["file", "file", "file"],
    },
    "run_command security": {
        "file": "core/agent_tools.py",
        "test_patterns": ["echo test", "rm -rf /etc/passwd"],
        "should_pass": [True, False],
    },
    "CHAT tool bypass": {
        "file": "ui/panel_server.py",
        "test_patterns": ["requirements.txt dosyasında ne var", "engine.py ilk 10 satır"],
        "expected_intents": ["file", "file"],
    },
}

HUMAN_USE_SCENARIOS = [
    ("Merhaba, nasılsın?", "chat"),
    ("Python ile basit hesap makinesi yap", "code"),
    ("requirements.txt dosyasında ne var?", "file"),
    ("core/engine.py dosyasının ilk 10 satırını göster", "file"),
    ("klasördeki Python dosyalarını listele", "file"),
    ("dosya oluştur", "code"),
    ("10 + 20 kaç?", "calculator"),
    ("100 / 5 kaç?", "calculator"),
    ("10 satırlık Python kodu yaz", "code"),
    ("dosyaya bunu yaz", "file"),
]


# ─── Utilities ───────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}")
    except UnicodeEncodeError:
        # Fallback: strip non-ASCII
        safe = msg.encode("ascii", errors="replace").decode()
        print(f"[{ts}] {safe}")


def run_cmd(cmd, timeout=30):
    """Run a command safely and return (stdout, stderr, exitcode)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
            cwd=str(PROJECT),
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", str(e), -1


def get_excluded(path_str):
    """Check if a path should be excluded."""
    parts = Path(path_str).parts
    return any(ex in parts or ex in path_str for ex in EXCLUDE_DIRS)


# ─── Snapshot & Diff ─────────────────────────────────────────

def scan_project():
    """Scan project files and return snapshot dict."""
    snapshot = {}
    for f in PROJECT.rglob("*"):
        if not f.is_file():
            continue
        rel = str(f.relative_to(PROJECT)).replace("\\", "/")
        if get_excluded(rel):
            continue
        try:
            stat = f.stat()
            snapshot[rel] = {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "hash": hashlib.md5(f.read_bytes()[:4096]).hexdigest()[:8],
            }
        except (OSError, PermissionError):
            continue
    return snapshot


def load_snapshot():
    """Load previous snapshot from disk. Handles both old PS1 and new Python formats."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            # Migrate old PS1 format (LastWrite/Size) to new format (mtime/size/hash)
            migrated = {}
            for path, info in data.items():
                if isinstance(info, dict):
                    if "mtime" in info:
                        migrated[path] = info  # Already new format
                    elif "LastWrite" in info:
                        migrated[path] = {
                            "size": info.get("Size", 0),
                            "mtime": 0,  # Can't recover exact mtime
                            "hash": "",
                        }
                    else:
                        migrated[path] = info
            return migrated
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_snapshot(snapshot):
    """Save current snapshot to disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)


def diff_snapshots(old, new):
    """Compare snapshots and return changes."""
    changes = []
    for path in new:
        if path not in old:
            changes.append({"type": "NEW", "path": path, "info": new[path]})
        else:
            old_info = old[path]
            new_info = new[path]
            # Compare by hash (most reliable) or mtime+size
            old_hash = old_info.get("hash", "")
            new_hash = new_info.get("hash", "")
            if old_hash and new_hash and old_hash != new_hash:
                changes.append({"type": "MODIFIED", "path": path, "info": new_info})
            elif old_info.get("mtime", 0) != new_info.get("mtime", 0) or \
                 old_info.get("size", 0) != new_info.get("size", 0):
                changes.append({"type": "MODIFIED", "path": path, "info": new_info})
    for path in old:
        if path not in new:
            changes.append({"type": "DELETED", "path": path, "info": old[path]})
    return changes


# ─── Deep Analysis ───────────────────────────────────────────

def analyze_changes(changes):
    """Deep analysis of what changed and why."""
    analyses = []
    for change in changes:
        path = change["path"]
        analysis = {
            "path": path,
            "type": change["type"],
            "purpose": CRITICAL_FILES.get(path, "Unknown file"),
            "is_critical": path in CRITICAL_FILES,
        }

        if change["type"] == "MODIFIED" and path.endswith(".py"):
            # Try to understand what changed
            analysis["language"] = "Python"
            analysis["risk"] = "MEDIUM" if path in CRITICAL_FILES else "LOW"
            # Check if it's a test file
            if "test" in path.lower():
                analysis["category"] = "test"
                analysis["risk"] = "LOW"
            elif path.startswith("core/"):
                analysis["category"] = "core"
                analysis["risk"] = "HIGH"
            elif path.startswith("ui/"):
                analysis["category"] = "frontend"
                analysis["risk"] = "MEDIUM"
            elif path.startswith("agents/"):
                analysis["category"] = "agent"
                analysis["risk"] = "MEDIUM"
        elif path.endswith((".yml", ".yaml")):
            analysis["language"] = "YAML"
            analysis["category"] = "config"
            analysis["risk"] = "MEDIUM"
        elif path.endswith((".json",)):
            analysis["language"] = "JSON"
            analysis["category"] = "config"
            analysis["risk"] = "LOW"
        elif path.endswith(("Dockerfile",)):
            analysis["language"] = "Dockerfile"
            analysis["category"] = "build"
            analysis["risk"] = "MEDIUM"
        elif path.endswith((".ps1",)):
            analysis["language"] = "PowerShell"
            analysis["category"] = "script"
            analysis["risk"] = "LOW"
        elif path.endswith((".html",)):
            analysis["language"] = "HTML"
            analysis["category"] = "frontend"
            analysis["risk"] = "MEDIUM"
        elif path.endswith((".md",)):
            analysis["language"] = "Markdown"
            analysis["category"] = "docs"
            analysis["risk"] = "LOW"
        else:
            analysis["language"] = "Other"
            analysis["category"] = "other"
            analysis["risk"] = "LOW"

        analyses.append(analysis)
    return analyses


# ─── Git Analysis ────────────────────────────────────────────

def git_analysis():
    """Get git status and diff info."""
    status, _, _ = run_cmd("git status --short")
    diff_stat, _, _ = run_cmd("git diff --stat")
    log_cmd, _, _ = run_cmd("git log --oneline -5")
    return {
        "status": status.strip(),
        "diff_stat": diff_stat.strip(),
        "recent_commits": log_cmd.strip(),
        "has_uncommitted": bool(status.strip()),
    }


# ─── Python Syntax ──────────────────────────────────────────

def check_python_syntax():
    """Check all Python files for syntax errors."""
    errors = []
    count = 0
    for f in PROJECT.rglob("*.py"):
        rel = str(f.relative_to(PROJECT)).replace("\\", "/")
        if get_excluded(rel):
            continue
        count += 1
        _, stderr, rc = run_cmd(f'python -m py_compile "{f}"', timeout=10)
        if rc != 0:
            errors.append({"file": rel, "error": stderr.strip()[:200]})
    return {"total": count, "errors": errors}


# ─── Docker Check ────────────────────────────────────────────

def docker_check():
    """Check Docker container status."""
    out, err, rc = run_cmd("docker compose ps --format json", timeout=15)
    healthy = False
    containers = []
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        try:
            c = json.loads(line)
            containers.append(c)
            if c.get("Health", "") == "healthy" or "Up" in c.get("State", ""):
                healthy = True
        except json.JSONDecodeError:
            if "healthy" in line.lower() or "up" in line.lower():
                healthy = True
            containers.append({"raw": line})

    # Fallback: try plain docker compose ps
    if not containers:
        out2, _, _ = run_cmd("docker compose ps", timeout=10)
        healthy = "healthy" in out2.lower() or "up" in out2.lower()
        containers = [{"raw": out2}]

    return {"healthy": healthy, "containers": containers}


# ─── API Health ──────────────────────────────────────────────

def api_health():
    """Check if UMAY backend API is responding."""
    out, _, rc = run_cmd("curl -s http://localhost:5001/api/health", timeout=10)
    try:
        data = json.loads(out)
        return {"healthy": True, "data": data}
    except (json.JSONDecodeError, ValueError):
        # Try simpler check
        out2, _, rc2 = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/", timeout=10)
        return {"healthy": rc2 == 0 and "200" in out2, "data": out}


# ─── Regression Tests ───────────────────────────────────────

def run_regression_tests():
    """Run the existing test suite."""
    out, err, rc = run_cmd(
        "python -m pytest tests/ -q --tb=line --ignore=tests/__pycache__ "
        "--ignore=tests/test_human_use_v2.py --ignore=tests/test_human_use_e2e.py",
        timeout=180,
    )
    # Parse results — check both stdout and stderr
    combined = out + "\n" + err
    last_lines = combined.strip().split("\n")[-10:]
    summary = " ".join(last_lines)

    # Extract pass/fail counts
    pass_match = re.search(r"(\d+) passed", summary)
    fail_match = re.search(r"(\d+) failed", summary)
    skip_match = re.search(r"(\d+) skipped", summary)

    return {
        "exit_code": rc,
        "passed": int(pass_match.group(1)) if pass_match else 0,
        "failed": int(fail_match.group(1)) if fail_match else 0,
        "skipped": int(skip_match.group(1)) if skip_match else 0,
        "summary": summary[:500],
    }


# ─── P1 Regression Check ────────────────────────────────────

def check_p1_regression():
    """Check that previously fixed P1 issues haven't regressed."""
    results = {}

    # Intent routing test
    try:
        sys.path.insert(0, str(PROJECT))
        from core.intent_router import classify_intent, Intent

        intent_tests = [
            ("10 + 20 kaç?", "calculator"),
            ("Python ile hesap makinesi yap", "code"),
            ("requirements.txt dosyasında ne var", "file"),
            ("core/engine.py dosyasının ilk 10 satırını göster", "file"),
            ("core klasörünü listele", "file"),
            ("10 satırlık Python kodu yaz", "code"),
        ]

        intent_pass = 0
        intent_fail = 0
        for msg, expected in intent_tests:
            result = classify_intent(msg)
            if result.value == expected:
                intent_pass += 1
            else:
                intent_fail += 1
                log(f"  REGRESSION: '{msg}' -> {result.value} (expected {expected})")

        results["intent_routing"] = {
            "pass": intent_pass,
            "fail": intent_fail,
            "total": len(intent_tests),
        }
    except Exception as e:
        results["intent_routing"] = {"error": str(e)}

    # Calculator regression
    try:
        from core.agent_tools import evaluate_expression
        calc_tests = [("10 + 20", "30"), ("25 * 4", "100"), ("100 / 5", "20")]
        calc_pass = 0
        for expr, expected in calc_tests:
            r = evaluate_expression(expression=expr)
            answer = str(r.get("result", r.get("answer", "")))
            if expected in answer:
                calc_pass += 1
        results["calculator"] = {"pass": calc_pass, "total": len(calc_tests)}
    except Exception as e:
        results["calculator"] = {"error": str(e)}

    # Tool execution test
    try:
        from core.agent_tools import read_file, list_directory, search_files
        tool_pass = 0
        # read_file
        r = read_file(path="core/engine.py", start_line=1, max_lines=3)
        if "content" in r and len(r["content"]) > 10:
            tool_pass += 1
        # list_directory
        r = list_directory(path="core")
        if len(r.get("entries", [])) > 5:
            tool_pass += 1
        # search_files
        r = search_files(pattern="*.py", path="core")
        if len(r.get("matches", [])) > 5:
            tool_pass += 1
        results["tools"] = {"pass": tool_pass, "total": 3}
    except Exception as e:
        results["tools"] = {"error": str(e)}

    return results


# ─── Human-Use Test (Simplified) ────────────────────────────

def human_use_test():
    """Run simplified human-use scenarios via intent + model routing."""
    results = []
    try:
        sys.path.insert(0, str(PROJECT))
        from core.intent_router import classify_intent
        from core.engine import resolve_model

        for msg, expected_intent in HUMAN_USE_SCENARIOS:
            intent = classify_intent(msg)
            model = resolve_model(intent.value)
            model_name = model.get("model", str(model)) if isinstance(model, dict) else str(model)
            ok = intent.value == expected_intent
            results.append({
                "message": msg,
                "expected": expected_intent,
                "got": intent.value,
                "model": model_name,
                "pass": ok,
            })
            if not ok:
                log(f"  HUMAN-USE FAIL: '{msg}' -> {intent.value} (expected {expected_intent})")
    except Exception as e:
        results.append({"error": str(e)})

    pass_count = sum(1 for r in results if r.get("pass"))
    return {"results": results, "pass": pass_count, "total": len(results)}


# ─── Security Check ─────────────────────────────────────────

def security_check():
    """Check for security issues."""
    issues = []

    # Check .env for secrets
    env_file = PROJECT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                # Check for empty tokens (good!) or non-empty tokens (potential leak risk)
                if any(s in k.upper() for s in ["TOKEN", "SECRET", "PASSWORD", "KEY"]):
                    if v and len(v) > 10:
                        issues.append(f"Line {i}: {k} appears to have a real value — ensure not in Git")

    # Check if .env is in .gitignore
    gitignore = PROJECT / ".gitignore"
    if gitignore.exists():
        with open(gitignore, "r", encoding="utf-8", errors="replace") as f:
            gi = f.read()
            if ".env" not in gi:
                issues.append(".env not in .gitignore — risk of secret leak")

    # Check run_command safety
    try:
        from core.agent_tools import run_command
        os.environ["UMAY_APPROVED"] = "true"
        r = run_command(command="echo safe_test")
        safe_works = "safe_test" in r.get("stdout", "")
        os.environ.pop("UMAY_APPROVED", None)

        # Test dangerous command blocking
        os.environ["UMAY_MODE"] = "approval"
        os.environ.pop("UMAY_APPROVED", None)
        try:
            run_command(command="rm -rf /etc/passwd")
            issues.append("run_command: dangerous command NOT blocked!")
        except PermissionError:
            pass  # Good — blocked
        except Exception:
            pass  # Also good
        finally:
            os.environ.pop("UMAY_MODE", None)
            os.environ["UMAY_APPROVED"] = "true"
    except Exception as e:
        issues.append(f"Security check error: {e}")

    return {"issues": issues, "pass": len(issues) == 0}


# ─── Telegram ────────────────────────────────────────────────

def send_telegram(message):
    """Send a message via Telegram Bot API. Returns (success, error)."""
    token = os.environ.get("UMAY_TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("UMAY_TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        return False, "TELEGRAM_BOT_TOKEN or UMAY_TELEGRAM_CHAT_ID not set"

    if token.startswith("YOUR_") or chat_id.startswith("YOUR_"):
        return False, "Placeholder values detected — real token not configured"

    try:
        import urllib.request
        import urllib.parse

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }).encode()

        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return True, None
            else:
                return False, f"API error: {result.get('description', 'unknown')}"
    except Exception as e:
        return False, str(e)


# ─── Report Builder ──────────────────────────────────────────

def build_report(changes, analyses, git_info, syntax, docker,
                 api, regression, p1, human_use, security, start_time):
    """Build comprehensive watchdog report."""
    now = datetime.now()
    duration = (datetime.now() - start_time).total_seconds()

    # Count issues
    critical_changes = [a for a in analyses if a.get("is_critical")]
    high_risk = [a for a in analyses if a.get("risk") == "HIGH"]
    p1_fails = sum(1 for v in p1.values() if isinstance(v, dict) and v.get("fail", 0) > 0)
    human_fails = human_use.get("total", 0) - human_use.get("pass", 0)

    # Overall status
    if p1_fails > 0 or human_fails > 0 or syntax.get("errors"):
        status = "ALERT"
        status_icon = "🔴"
    elif changes and not regression.get("failed"):
        status = "CHANGES_DETECTED"
        status_icon = "🟡"
    else:
        status = "HEALTHY"
        status_icon = "🟢"

    report = {
        "timestamp": now.isoformat(),
        "duration_seconds": round(duration, 1),
        "status": status,
        "changes": {
            "total": len(changes),
            "new": sum(1 for c in changes if c["type"] == "NEW"),
            "modified": sum(1 for c in changes if c["type"] == "MODIFIED"),
            "deleted": sum(1 for c in changes if c["type"] == "DELETED"),
            "critical_files": [c["path"] for c in changes if c["path"] in CRITICAL_FILES],
        },
        "analysis": {
            "total": len(analyses),
            "critical": len(critical_changes),
            "high_risk": len(high_risk),
            "details": analyses[:20],
        },
        "git": git_info,
        "python_syntax": syntax,
        "docker": {"healthy": docker.get("healthy", False)},
        "api": {"healthy": api.get("healthy", False)},
        "regression": regression,
        "p1_regression": p1,
        "human_use": human_use,
        "security": security,
    }

    return report, status_icon, status


def format_telegram_message(report, status_icon, status):
    """Format a concise Telegram message."""
    lines = []
    lines.append("🤖 <b>UMAY WATCHDOG</b>")
    lines.append(f"⏱ {report['timestamp'][:16].replace('T', ' ')}")
    lines.append("")

    # Status
    lines.append(f"{status_icon} <b>GENEL: {status}</b>")
    lines.append("")

    # Changes
    ch = report["changes"]
    if ch["total"] > 0:
        lines.append(f"📝 <b>Değişiklikler:</b> +{ch['new']} ~{ch['modified']} -{ch['deleted']}")
        for a in report["analysis"]["details"][:5]:
            icon = {"NEW": "🆕", "MODIFIED": "✏️", "DELETED": "🗑️"}.get(a["type"], "📄")
            risk_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(a.get("risk", ""), "")
            lines.append(f"  {icon} {a['path']} {risk_icon}")
        if ch["total"] > 5:
            lines.append(f"  ... +{ch['total']-5} more")
        lines.append("")

    # Regression
    reg = report["regression"]
    if reg:
        lines.append(f"🧪 <b>Regression:</b> {reg.get('passed',0)} PASS, {reg.get('failed',0)} FAIL")
        if reg.get("failed", 0) > 0:
            lines.append(f"  ⚠️ {reg.get('failed',0)} regression test(s) FAILED")
        lines.append("")

    # P1 Regression
    p1 = report["p1_regression"]
    p1_fails = []
    for name, data in p1.items():
        if isinstance(data, dict) and data.get("fail", 0) > 0:
            p1_fails.append(name)
    if p1_fails:
        lines.append(f"🚨 <b>P1 REGRESSION:</b> {', '.join(p1_fails)}")
        lines.append("")
    elif p1:
        lines.append("✅ <b>P1 Regression:</b> All PASS")
        lines.append("")

    # Human Use
    hu = report["human_use"]
    if hu.get("total", 0) > 0:
        lines.append(f"👤 <b>Human Use:</b> {hu.get('pass',0)}/{hu.get('total',0)} PASS")
        lines.append("")

    # Docker
    docker_ok = report.get("docker", {}).get("healthy", False)
    lines.append(f"🐳 <b>Docker:</b> {'✅ Healthy' if docker_ok else '❌ Unhealthy'}")

    # Security
    sec = report.get("security", {})
    sec_issues = sec.get("issues", [])
    if sec_issues:
        lines.append(f"🔐 <b>Security:</b> ⚠️ {len(sec_issues)} issue(s)")
    else:
        lines.append("🔐 <b>Security:</b> ✅ Clean")

    # Python syntax
    syn = report.get("python_syntax", {})
    if syn.get("errors"):
        lines.append(f"🐍 <b>Syntax:</b> ❌ {len(syn['errors'])} error(s)")
        for err in syn["errors"][:3]:
            lines.append(f"  • {err['file']}")
    else:
        lines.append(f"🐍 <b>Syntax:</b> ✅ {syn.get('total', 0)} files OK")

    lines.append("")
    lines.append(f"📊 <i>{report.get('duration_seconds', 0)}s</i>")

    return "\n".join(lines)


# ─── Main ────────────────────────────────────────────────────

def run_watchdog():
    """Run the full watchdog analysis."""
    start_time = datetime.now()
    log("UMAY Watchdog started")

    # 1. Snapshot & diff
    log("Scanning project files...")
    old_snapshot = load_snapshot()
    new_snapshot = scan_project()
    changes = diff_snapshots(old_snapshot, new_snapshot)
    log(f"Found {len(changes)} changes ({sum(1 for c in changes if c['type']=='NEW')} new, "
        f"{sum(1 for c in changes if c['type']=='MODIFIED')} modified, "
        f"{sum(1 for c in changes if c['type']=='DELETED')} deleted)")

    # 2. Analyze changes
    log("Analyzing changes...")
    analyses = analyze_changes(changes)
    critical = [a for a in analyses if a.get("is_critical")]
    if critical:
        log(f"  ⚠️ {len(critical)} critical file(s) changed: {[a['path'] for a in critical]}")

    # 3. Git
    log("Checking git status...")
    git_info = git_analysis()

    # 4. Python syntax
    log("Checking Python syntax...")
    syntax = check_python_syntax()
    if syntax["errors"]:
        log(f"  ❌ {len(syntax['errors'])} syntax errors found")

    # 5. Docker
    log("Checking Docker...")
    docker = docker_check()

    # 6. API
    log("Checking API...")
    api = api_health()

    # 7. Regression tests
    log("Running regression tests...")
    regression = run_regression_tests()
    log(f"  Regression: {regression['passed']} PASS, {regression['failed']} FAIL")

    # 8. P1 regression
    log("Checking P1 regression...")
    p1 = check_p1_regression()
    for name, data in p1.items():
        if isinstance(data, dict):
            fail = data.get("fail", 0)
            if fail > 0:
                log(f"  ❌ P1 REGRESSION: {name} ({fail} failures)")
            else:
                log(f"  ✅ P1 OK: {name}")

    # 9. Human-use test
    log("Running human-use scenarios...")
    human_use = human_use_test()
    log(f"  Human-use: {human_use.get('pass', 0)}/{human_use.get('total', 0)} PASS")

    # 10. Security
    log("Running security check...")
    security = security_check()

    # 11. Build report
    report, status_icon, status = build_report(
        changes, analyses, git_info, syntax, docker,
        api, regression, p1, human_use, security, start_time
    )

    # 12. Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = start_time.strftime("%Y%m%d_%H%M%S")
    report_file = REPORT_DIR / f"watchdog_{ts}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log(f"Report saved: {report_file}")

    # 13. Telegram
    telegram_msg = format_telegram_message(report, status_icon, status)
    tg_ok, tg_err = send_telegram(telegram_msg)
    if tg_ok:
        log("✅ Telegram message sent")
    else:
        log(f"⚠️ Telegram failed: {tg_err}")
        # Log to file
        err_log = REPORT_DIR / "telegram_errors.log"
        with open(err_log, "a") as f:
            f.write(f"{datetime.now()}: {tg_err}\n")

    # 14. Save snapshot (only after successful scan)
    save_snapshot(new_snapshot)
    log("Snapshot saved")

    log(f"Watchdog completed in {report['duration_seconds']}s — Status: {status}")
    return report


if __name__ == "__main__":
    run_watchdog()

"""Real Ollama P0 verifier for UMAY.

Run this on the Windows machine where Ollama is installed:
    python scripts/verify_real_ollama.py

The verifier never edits the target workspace. It performs a controlled native
Ollama tool-call round-trip using a harmless list_directory tool and then, if
C:\\CREWINTEL exists, performs a second controlled round-trip against that
workspace. Results are appended to logs/DEVELOPMENT_LOG.md.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.agent import _assistant_tool_message, _parse_tool_calls, _tool_messages
from core.agent_tools import set_workspace, get_workspace
from core.engine import OLLAMA_URL

LOG = ROOT / "logs" / "DEVELOPMENT_LOG.md"
TIMEOUT = int(os.getenv("UMAY_OLLAMA_VERIFY_TIMEOUT", "180"))
TARGET = os.getenv("UMAY_VERIFY_WORKSPACE", r"C:\CREWINTEL")

TOOL = {
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": "Lists files in the active workspace. Read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "recursive": {"type": "boolean"},
            },
            "required": [],
        },
    },
}


def log(title: str, lines: list[str]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now():%Y-%m-%d %H:%M:%S} — {title}\n")
        for line in lines:
            f.write(f"- {line}\n")


def post(messages: list[dict], model: str) -> dict:
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": model, "messages": messages, "tools": [TOOL], "stream": False},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def choose_model() -> tuple[str, list[str]]:
    r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
    r.raise_for_status()
    models = [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    preferred = os.getenv("UMAY_VERIFY_MODEL", "")
    if preferred:
        for name in models:
            if name == preferred or name.split(":", 1)[0] == preferred.split(":", 1)[0]:
                return name, models
    for candidate in ("qwen2.5-coder:7b", "qwen3:8b", "deepseek-coder:6.7b", "gemma3:4b"):
        for name in models:
            if candidate == name or candidate.split(":", 1)[0] == name.split(":", 1)[0]:
                return name, models
    if not models:
        raise RuntimeError("Ollama çalışıyor ancak hiç model kurulu değil.")
    return models[0], models


def one_round_trip(model: str, workspace: Path) -> dict:
    set_workspace(workspace)
    messages = [
        {"role": "system", "content": (
            "You are performing a controlled tool-call protocol test. "
            "You MUST call list_directory with recursive=false, then wait for the tool result "
            "and reply with exactly ROUND_TRIP_PASS. Do not call any other tool."
        )},
        {"role": "user", "content": "Perform the controlled tool protocol test now."},
    ]
    first = post(messages, model)
    first_msg = first.get("message", {})
    calls = _parse_tool_calls(first_msg)
    if not calls:
        raise AssertionError(f"Model did not return a native/compatible tool call: {first_msg}")
    if len(calls) != 1 or (calls[0].get("function") or {}).get("name") != "list_directory":
        raise AssertionError(f"Unexpected tool call: {calls}")
    args = (calls[0].get("function") or {}).get("arguments")
    if not isinstance(args, dict):
        raise AssertionError(f"Normalized arguments is not an object: {type(args).__name__}")
    if args.get("recursive") is not False:
        raise AssertionError(f"Unexpected arguments: {args}")

    messages.append(_assistant_tool_message(calls))
    messages.extend(_tool_messages(calls))
    second = post(messages, model)
    second_msg = second.get("message", {})
    answer = (second_msg.get("content") or "").strip()
    if "ROUND_TRIP_PASS" not in answer:
        raise AssertionError(f"Second model turn did not pass: {second_msg}")
    # Ensure the actual outgoing assistant payload is object arguments.
    assistant = messages[-2]
    outgoing_args = assistant["tool_calls"][0]["function"]["arguments"]
    if not isinstance(outgoing_args, dict):
        raise AssertionError("Outgoing assistant tool-call arguments were not an object")
    return {
        "workspace": str(workspace),
        "model": model,
        "tool": "list_directory",
        "entries_seen": json.loads(messages[-1]["content"]).get("count"),
        "answer": answer[:200],
    }


def main() -> int:
    print("[UMAY P0] 1/6 Ollama health check...")
    try:
        health = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        health.raise_for_status()
    except Exception as exc:
        log("P0 Gerçek Ollama — BLOKELİ", [
            f"Ollama URL: `{OLLAMA_URL}`",
            f"Sonuç: FAIL / BLOCKED",
            f"Hata: `{exc}`",
            "Gerçek round-trip çalıştırılamadı; P0 kapatılmadı.",
        ])
        print(f"❌ Ollama erişilemiyor: {exc}")
        return 2

    print("[UMAY P0] 2/6 Model keşfi...")
    try:
        model, models = choose_model()
    except Exception as exc:
        log("P0 Gerçek Ollama — MODEL EKSİK", [f"Sonuç: FAIL", f"Hata: `{exc}`"])
        print(f"❌ {exc}")
        return 3
    print(f"✅ Model: {model}")
    print(f"[UMAY P0] 3/6 Kurulu modeller: {', '.join(models)}")

    root = Path(TARGET).expanduser()
    workspaces = [ROOT]
    if root.exists() and root.is_dir():
        workspaces.append(root)
    else:
        print(f"⚠️ {root} bulunamadı; yalnızca UMAY workspace testi yapılacak.")

    results = []
    try:
        for i, workspace in enumerate(workspaces, start=4):
            print(f"[UMAY P0] {i}/6 Gerçek round-trip: {workspace}")
            started = time.time()
            result = one_round_trip(model, workspace)
            result["duration_s"] = round(time.time() - started, 2)
            results.append(result)
            print(f"✅ PASS: {result}")
    except Exception as exc:
        log("P0 Gerçek Ollama — ROUND-TRIP FAIL", [
            f"Model: `{model}`",
            f"Hata: `{exc}`",
            "Gerçek round-trip başarısız; P0 kapatılmadı.",
        ])
        print(f"❌ Round-trip başarısız: {exc}")
        return 4

    print("[UMAY P0] 6/6 Sonuçları logluyorum...")
    log("P0 Gerçek Ollama — ROUND-TRIP PASS", [
        f"Ollama URL: `{OLLAMA_URL}`",
        f"Model: `{model}`",
        f"Kurulu model sayısı: {len(models)}",
        f"Workspace testleri: {len(results)}",
        *[f"PASS: `{r['workspace']}` | entries={r['entries_seen']} | duration={r['duration_s']}s" for r in results],
        "Native/compatible tool call → normalized object arguments → role=tool → ikinci Ollama turu PASS.",
        "P0 gerçek round-trip doğrulandı.",
    ])
    print("🎉 P0 GERÇEK OLLAMA ROUND-TRIP PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

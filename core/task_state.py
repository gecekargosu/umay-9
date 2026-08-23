"""Lightweight JSONL task/checkpoint persistence for long UMAY agent jobs.

Supports WAITING_FOR_APPROVAL status for interactive approval flows.
Approval state is persisted alongside task state.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TASK_LOG = ROOT / "logs" / "tasks.jsonl"


def _append(event: dict[str, Any]) -> dict[str, Any]:
    TASK_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": time.time(), **event}
    with TASK_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def start_task(request: str, workspace: str, model: str, task_id: str | None = None) -> str:
    task_id = task_id or f"task-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    _append({"event": "start", "task_id": task_id, "request": request, "workspace": workspace, "model": model, "step": 0, "status": "RUNNING"})
    return task_id


def waiting_for_approval(
    task_id: str,
    step: int,
    workspace: str,
    approval_id: str,
    tool_name: str,
    action: str,
    target: str = "",
    risk: str = "medium",
    messages: list[dict[str, Any]] | None = None,
) -> None:
    """Task'ı WAITING_FOR_APPROVAL durumuna geçir.

    Approval bilgilerini JSONL'e kaydeder, restart sonrası korunur.
    """
    snapshot = messages or []
    raw = json.dumps(snapshot, ensure_ascii=False)
    if len(raw) > 100_000:
        snapshot = snapshot[-12:]
    _append({
        "event": "waiting_approval",
        "task_id": task_id,
        "step": step,
        "workspace": workspace,
        "status": "WAITING_FOR_APPROVAL",
        "approval_id": approval_id,
        "tool_name": tool_name,
        "action": action,
        "target": target,
        "risk": risk,
        "messages": snapshot,
    })


def resume_task(task_id: str, step: int, workspace: str, status: str = "RESUMING") -> None:
    """Task'ı resume edilen duruma geçir."""
    _append({
        "event": "resume",
        "task_id": task_id,
        "step": step,
        "workspace": workspace,
        "status": status,
    })


def pending_tasks() -> list[dict[str, Any]]:
    """WAITING_FOR_APPROVAL durumundaki tüm task'ları bul.

    Restart sonrası devam edilebilecek task'ları listeler.
    """
    if not TASK_LOG.exists():
        return []
    latest: dict[str, dict[str, Any]] = {}
    with TASK_LOG.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            task_id = event.get("task_id")
            if task_id:
                latest[task_id] = event
    return [
        t for t in latest.values()
        if t.get("status") == "WAITING_FOR_APPROVAL"
    ]


def checkpoint(
    task_id: str,
    step: int,
    workspace: str,
    status: str,
    tool_names: list[str] | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> None:
    snapshot = messages or []
    raw = json.dumps(snapshot, ensure_ascii=False)
    if len(raw) > 100_000:
        # Keep the protocol tail; tool results are already bounded upstream.
        snapshot = snapshot[-12:]
    _append({
        "event": "checkpoint",
        "task_id": task_id,
        "step": step,
        "workspace": workspace,
        "status": status,
        "tool_names": tool_names or [],
        "messages": snapshot,
    })


def finish_task(task_id: str, step: int, status: str, answer: str = "", result: dict | None = None) -> None:
    """Finish task and persist full result dict for wait_for_completion fallback."""
    event = {"event": "finish", "task_id": task_id, "step": step, "status": status, "answer": answer[:4000]}
    if result and isinstance(result, dict):
        # Persist full result (truncated for safety)
        import copy
        _r = copy.deepcopy(result)
        if "latency" in _r:
            _r["latency"] = {k: v for k, v in _r["latency"].items() if isinstance(v, (int, float))}
        event["result"] = _r
    _append(event)


def load_task(task_id: str) -> dict[str, Any] | None:
    if not TASK_LOG.exists():
        return None
    latest: dict[str, Any] | None = None
    with TASK_LOG.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("task_id") == task_id:
                latest = event
    return latest


def list_tasks(limit: int = 20) -> list[dict[str, Any]]:
    if not TASK_LOG.exists():
        return []
    latest: dict[str, dict[str, Any]] = {}
    with TASK_LOG.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            task_id = event.get("task_id")
            if task_id:
                latest[task_id] = event
    return list(latest.values())[-max(1, int(limit)):]



def list_tasks_for_workspace(workspace: str, limit: int = 20) -> list[dict[str, Any]]:
    """Workspace'e gore task listesi - STEP-05 / STEP-03 absorption."""
    if not TASK_LOG.exists():
        return []
    latest: dict[str, dict[str, Any]] = {}
    with TASK_LOG.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            task_id = event.get("task_id")
            if task_id:
                latest[task_id] = event
    filtered = [
        t for t in latest.values()
        if t.get("workspace") == workspace
    ]
    return filtered[-max(1, int(limit)):]


def get_status(task_id: str) -> dict | None:
    """Get latest task status including full result dict."""
    task = load_task(task_id)
    if not task:
        return None
    return {
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "answer": task.get("answer", ""),
        "result": task.get("result"),
    }


def update_status(task_id: str, status: str) -> bool:
    """Update task status - STEP-05 lifecycle."""
    _append({
        "event": "status_update",
        "task_id": task_id,
        "status": status,
    })
    return True

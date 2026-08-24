"""UMAY Audit Timeline — human-readable event timeline.

Converts raw JSONL audit logs into a readable timeline.
Supports filtering by task_id, time range, and action type.

Usage:
    from core.audit_timeline import get_timeline, format_timeline
    events = get_timeline(task_id="task-xxx")
    print(format_timeline(events))
"""
import json
import os
import time
from pathlib import Path
from typing import Optional


LOGS_DIR = Path(os.getenv("UMAY_LOGS_DIR", "logs"))


def _read_jsonl(filepath: Path) -> list[dict]:
    """Read a JSONL file and return list of dicts."""
    entries = []
    if not filepath.exists():
        return entries
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return entries


def get_timeline(
    task_id: Optional[str] = None,
    since: Optional[float] = None,
    limit: int = 50,
) -> list[dict]:
    """Get audit events as a timeline.
    
    Args:
        task_id: Filter by task ID
        since: Filter events after this timestamp
        limit: Max events to return
    
    Returns:
        List of event dicts sorted by time
    """
    events = []
    
    # Read from actions log
    actions_file = LOGS_DIR / "actions.jsonl"
    for entry in _read_jsonl(actions_file):
        events.append({
            "time": entry.get("timestamp", entry.get("time", 0)),
            "action": entry.get("action", entry.get("event", "unknown")),
            "tool": entry.get("tool", ""),
            "task_id": entry.get("task_id", ""),
            "status": entry.get("status", ""),
            "detail": entry.get("detail", entry.get("message", "")),
            "source": "actions",
        })
    
    # Read from tasks log
    tasks_file = LOGS_DIR / "tasks.jsonl"
    for entry in _read_jsonl(tasks_file):
        events.append({
            "time": entry.get("timestamp", entry.get("time", 0)),
            "action": entry.get("action", "task_event"),
            "tool": "",
            "task_id": entry.get("task_id", entry.get("id", "")),
            "status": entry.get("status", ""),
            "detail": entry.get("detail", entry.get("result", "")),
            "source": "tasks",
        })
    
    # Read from approvals log
    approvals_file = LOGS_DIR / "approvals.jsonl"
    for entry in _read_jsonl(approvals_file):
        events.append({
            "time": entry.get("timestamp", entry.get("time", 0)),
            "action": f"approval_{entry.get('status', 'unknown')}",
            "tool": entry.get("tool", ""),
            "task_id": entry.get("task_id", ""),
            "status": entry.get("status", ""),
            "detail": entry.get("message", ""),
            "source": "approvals",
        })
    
    # Filter
    if task_id:
        events = [e for e in events if e["task_id"] == task_id]
    if since:
        events = [e for e in events if e["time"] >= since]
    
    # Sort by time
    events.sort(key=lambda e: e.get("time", 0))
    
    # Limit
    return events[-limit:]


def format_timeline(events: list[dict]) -> str:
    """Format timeline events as human-readable text."""
    if not events:
        return "No events found."
    
    lines = ["=== UMAY AUDIT TIMELINE ===", ""]
    
    for event in events:
        ts = event.get("time", 0)
        if ts:
            # Convert to readable time
            try:
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                time_str = str(int(ts))
        else:
            time_str = "??:??:??"
        
        action = event.get("action", "?")
        status = event.get("status", "")
        detail = event.get("detail", "")
        tool = event.get("tool", "")
        
        # Build line
        parts = [f"  [{time_str}]"]
        
        # Status icon
        if status in ("COMPLETED", "approved", "OK", "PASS"):
            parts.append("[OK]")
        elif status in ("FAILED", "ERROR", "rejected", "FAIL"):
            parts.append("[!!]")
        elif status in ("RUNNING", "PENDING"):
            parts.append("[..]")
        else:
            parts.append("[--]")
        
        parts.append(action)
        if tool:
            parts.append(f"({tool})")
        if detail:
            parts.append(f"- {detail[:80]}")
        
        lines.append(" ".join(parts))
    
    lines.append("")
    lines.append(f"Total: {len(events)} events")
    
    return "\n".join(lines)


def get_task_summary(task_id: str) -> dict:
    """Get a summary for a specific task."""
    events = get_timeline(task_id=task_id, limit=100)
    
    return {
        "task_id": task_id,
        "total_events": len(events),
        "actions": [e["action"] for e in events],
        "status": events[-1]["status"] if events else "unknown",
        "start_time": events[0]["time"] if events else 0,
        "end_time": events[-1]["time"] if events else 0,
        "tools_used": list(set(e["tool"] for e in events if e["tool"])),
    }

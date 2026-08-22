"""UMAY Background Worker & Event System.

Runs background tasks: Gmail monitoring, Telegram polling, scheduled jobs.
Designed to work inside Docker container with proper lifecycle management.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import json
from datetime import datetime, timezone
from typing import Callable, Any

from core.utils.logger import log


class Event:
    """Simple event object."""

    def __init__(self, event_type: str, data: dict | None = None, source: str = "system"):
        self.type = event_type
        self.data = data or {}
        self.source = source
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.processed = False

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class EventBus:
    """In-memory event bus for decoupled communication."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._history: list[Event] = []
        self._lock = threading.Lock()
        self._max_history = 1000

    def on(self, event_type: str, handler: Callable):
        """Register a handler for an event type."""
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def off(self, event_type: str, handler: Callable):
        """Unregister a handler."""
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]

    def emit(self, event: Event):
        """Emit an event to all registered handlers."""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event.type, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                handler(event)
                event.processed = True
            except Exception as exc:
                log(f"[EVENT] Handler error for {event.type}: {exc}")

    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[dict]:
        """Get recent events."""
        with self._lock:
            events = self._history
            if event_type:
                events = [e for e in events if e.type == event_type]
            return [e.to_dict() for e in events[-limit:]]


class BackgroundWorker:
    """Background worker that runs periodic tasks."""

    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._event_bus = EventBus()
        self._lock = threading.Lock()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    def register_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int = 300,
        enabled: bool = True,
        description: str = "",
    ):
        """Register a periodic background task."""
        with self._lock:
            self._tasks[name] = {
                "func": func,
                "interval": interval_seconds,
                "enabled": enabled,
                "description": description,
                "last_run": None,
                "run_count": 0,
                "error_count": 0,
                "last_error": None,
            }
        log(f"[WORKER] Task registered: {name} (every {interval_seconds}s)")

    def enable_task(self, name: str):
        with self._lock:
            if name in self._tasks:
                self._tasks[name]["enabled"] = True

    def disable_task(self, name: str):
        with self._lock:
            if name in self._tasks:
                self._tasks[name]["enabled"] = False

    def _run_loop(self):
        """Main worker loop."""
        log("[WORKER] Background worker started")
        while self._running:
            now = time.time()
            with self._lock:
                tasks_snapshot = dict(self._tasks)

            for name, task in tasks_snapshot.items():
                if not task["enabled"]:
                    continue
                last_run = task["last_run"] or 0
                if now - last_run >= task["interval"]:
                    try:
                        log(f"[WORKER] Running task: {name}")
                        task["func"]()
                        with self._lock:
                            self._tasks[name]["last_run"] = now
                            self._tasks[name]["run_count"] += 1
                        self._event_bus.emit(Event(
                            event_type="task_completed",
                            data={"task": name},
                            source="worker",
                        ))
                    except Exception as exc:
                        log(f"[WORKER] Task {name} error: {exc}")
                        with self._lock:
                            self._tasks[name]["error_count"] += 1
                            self._tasks[name]["last_error"] = str(exc)
                        self._event_bus.emit(Event(
                            event_type="task_error",
                            data={"task": name, "error": str(exc)},
                            source="worker",
                        ))

            time.sleep(10)  # Check every 10 seconds

    def start(self):
        """Start the background worker."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log("[WORKER] Background worker thread started")

    def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log("[WORKER] Background worker stopped")

    def get_status(self) -> dict:
        """Get worker status."""
        with self._lock:
            tasks_status = {}
            for name, task in self._tasks.items():
                tasks_status[name] = {
                    "enabled": task["enabled"],
                    "interval": task["interval"],
                    "last_run": task["last_run"],
                    "run_count": task["run_count"],
                    "error_count": task["error_count"],
                    "description": task["description"],
                }
        return {
            "running": self._running,
            "tasks": tasks_status,
            "event_count": len(self._event_bus._history),
        }

    def run_task_now(self, name: str) -> bool:
        """Immediately run a specific task."""
        with self._lock:
            task = self._tasks.get(name)
        if not task:
            return False
        try:
            task["func"]()
            with self._lock:
                self._tasks[name]["last_run"] = time.time()
                self._tasks[name]["run_count"] += 1
            self._event_bus.emit(Event(
                event_type="task_completed",
                data={"task": name},
                source="worker",
            ))
            return True
        except Exception as exc:
            log(f"[WORKER] Manual run of {name} failed: {exc}")
            self._event_bus.emit(Event(
                event_type="task_error",
                data={"task": name, "error": str(exc)},
                source="worker",
            ))
            return False


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_worker: BackgroundWorker | None = None


def get_worker() -> BackgroundWorker:
    """Get or create the global background worker."""
    global _worker
    if _worker is None:
        _worker = BackgroundWorker()
    return _worker


def start_worker():
    """Start the global background worker."""
    worker = get_worker()
    worker.start()
    return worker


def stop_worker():
    """Stop the global background worker."""
    global _worker
    if _worker:
        _worker.stop()

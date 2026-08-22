"""UMAY Task Scheduler.

Provides cron-like scheduling for periodic and one-time tasks.
Persists scheduled tasks to survive Docker restarts.
"""
from __future__ import annotations

import json
import os
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Callable

from core.utils.logger import log


SCHEDULER_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "logs", "scheduler_state.json"
)


class ScheduledTask:
    """A scheduled task definition."""

    def __init__(
        self,
        task_id: str,
        name: str,
        func_name: str,
        interval_seconds: int | None = None,
        cron_expression: str | None = None,
        one_time: bool = False,
        run_at: str | None = None,
        enabled: bool = True,
        description: str = "",
        payload: dict | None = None,
    ):
        self.task_id = task_id
        self.name = name
        self.func_name = func_name
        self.interval_seconds = interval_seconds
        self.cron_expression = cron_expression
        self.one_time = one_time
        self.run_at = run_at
        self.enabled = enabled
        self.description = description
        self.payload = payload or {}
        self.last_run: str | None = None
        self.next_run: str | None = None
        self.run_count = 0
        self.error_count = 0
        self.last_error: str | None = None

        if interval_seconds and not run_at:
            self.next_run = (
                datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
            ).isoformat()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "func_name": self.func_name,
            "interval_seconds": self.interval_seconds,
            "cron_expression": self.cron_expression,
            "one_time": self.one_time,
            "run_at": self.run_at,
            "enabled": self.enabled,
            "description": self.description,
            "payload": self.payload,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScheduledTask:
        task = cls(
            task_id=data["task_id"],
            name=data["name"],
            func_name=data["func_name"],
            interval_seconds=data.get("interval_seconds"),
            cron_expression=data.get("cron_expression"),
            one_time=data.get("one_time", False),
            run_at=data.get("run_at"),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            payload=data.get("payload", {}),
        )
        task.last_run = data.get("last_run")
        task.next_run = data.get("next_run")
        task.run_count = data.get("run_count", 0)
        task.error_count = data.get("error_count", 0)
        task.last_error = data.get("last_error")
        return task


class Scheduler:
    """Task scheduler with persistence."""

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._functions: dict[str, Callable] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._load_state()

    def register_function(self, name: str, func: Callable):
        """Register a callable that can be scheduled."""
        self._functions[name] = func

    def add_task(
        self,
        task_id: str,
        name: str,
        func_name: str,
        interval_seconds: int | None = None,
        one_time: bool = False,
        run_at: str | None = None,
        enabled: bool = True,
        description: str = "",
        payload: dict | None = None,
    ) -> ScheduledTask:
        """Add a scheduled task."""
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            func_name=func_name,
            interval_seconds=interval_seconds,
            one_time=one_time,
            run_at=run_at,
            enabled=enabled,
            description=description,
            payload=payload,
        )
        with self._lock:
            self._tasks[task_id] = task
        self._save_state()
        log(f"[SCHEDULER] Task added: {name} ({task_id})")
        return task

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._save_state()
                return True
        return False

    def enable_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = True
                self._save_state()
                return True
        return False

    def disable_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = False
                self._save_state()
                return False
        return False

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        return [t.to_dict() for t in self._tasks.values()]

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        func = self._functions.get(task.func_name)
        if not func:
            log(f"[SCHEDULER] Function not found: {task.func_name}")
            return

        try:
            log(f"[SCHEDULER] Executing: {task.name}")
            if task.payload:
                func(**task.payload)
            else:
                func()
            now = datetime.now(timezone.utc).isoformat()
            task.last_run = now
            task.run_count += 1
            if task.one_time:
                task.enabled = False
            elif task.interval_seconds:
                task.next_run = (
                    datetime.now(timezone.utc) + timedelta(seconds=task.interval_seconds)
                ).isoformat()
            log(f"[SCHEDULER] Completed: {task.name}")
        except Exception as exc:
            task.error_count += 1
            task.last_error = str(exc)
            log(f"[SCHEDULER] Error in {task.name}: {exc}")

        self._save_state()

    def _run_loop(self):
        """Main scheduler loop."""
        log("[SCHEDULER] Scheduler started")
        while self._running:
            now = datetime.now(timezone.utc)
            with self._lock:
                tasks_snapshot = list(self._tasks.values())

            for task in tasks_snapshot:
                if not task.enabled:
                    continue

                should_run = False
                if task.one_time and task.run_at:
                    run_at = datetime.fromisoformat(task.run_at)
                    if now >= run_at:
                        should_run = True
                elif task.interval_seconds and task.next_run:
                    next_run = datetime.fromisoformat(task.next_run)
                    if now >= next_run:
                        should_run = True

                if should_run:
                    self._execute_task(task)

            time.sleep(15)  # Check every 15 seconds

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log("[SCHEDULER] Scheduler thread started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log("[SCHEDULER] Scheduler stopped")

    def _save_state(self):
        """Persist scheduler state to disk."""
        try:
            os.makedirs(os.path.dirname(SCHEDULER_STATE_FILE), exist_ok=True)
            with self._lock:
                state = {tid: t.to_dict() for tid, t in self._tasks.items()}
            with open(SCHEDULER_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            log(f"[SCHEDULER] Save state error: {exc}")

    def _load_state(self):
        """Load scheduler state from disk."""
        if not os.path.exists(SCHEDULER_STATE_FILE):
            return
        try:
            with open(SCHEDULER_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            for tid, data in state.items():
                self._tasks[tid] = ScheduledTask.from_dict(data)
            log(f"[SCHEDULER] Loaded {len(self._tasks)} tasks from state")
        except Exception as exc:
            log(f"[SCHEDULER] Load state error: {exc}")


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


def start_scheduler():
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.stop()

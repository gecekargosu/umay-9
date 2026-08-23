"""UMAY Task Executor - STEP-05 background chat execution.

Runs chat tasks in background threads with pause/resume/cancel.
Uses callback pattern: the caller provides the execute function.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Optional

from core.utils.logger import log


class TaskCancelledException(Exception):
    pass


_registry_lock = threading.Lock()
_tasks: dict[str, dict[str, Any]] = {}


def _gen_task_id() -> str:
    return f"task-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"


class TaskExecutor:
    """Background task executor with pause/resume/cancel lifecycle."""

    def __init__(self):
        self._on_status_callbacks: dict[str, Callable] = {}  # task_id -> callback

    def submit(self, session_id: str, soru: str, execute_fn: Callable | None = None,
               attachments: list[dict] | None = None, task_id: str | None = None,
               *, on_status: Callable | None = None,
               on_complete: Callable | None = None,
               on_error: Callable | None = None,
               **kwargs) -> str:
        """Submit a task. execute_fn(task_id, session_id, soru, attachments,
           on_status, on_complete, on_error, **kwargs) will run in a background thread.
           Extra kwargs (e.g. model, mode) are forwarded to execute_fn."""
        if execute_fn is None:
            def _default_exec(task_id, session_id, soru, attachments, *, on_status=None, on_complete=None, on_error=None):
                import time
                from core.engine import chat as _chat
                check_cancel(task_id)
                if on_status: on_status(task_id, "thinking", "Thinking...")
                check_cancel(task_id)
                if on_status: on_status(task_id, "calling_model", "Calling model...")
                result = _chat([{"role": "user", "content": soru}])
                check_cancel(task_id)
                msg = result.get("message", {}) if isinstance(result, dict) else {}
                cevap = msg.get("content", "") if msg else str(result)
                if on_status: on_status(task_id, "completed", "Done")
                if on_complete: on_complete(task_id, {"cevap": cevap, "model": "default", "gorev": "chat", "latency": {"total": 0.01}})
            execute_fn = _default_exec
        task_id = task_id or _gen_task_id()
        pe = threading.Event()
        re2 = threading.Event()
        cf = {"cancelled": False}
        completion_ev = threading.Event()

        with _registry_lock:
            _tasks[task_id] = {
                "task_id": task_id, "session_id": session_id, "soru": soru,
                "status": "CREATED", "thread": None,
                "pause_event": pe, "resume_event": re2, "cancel_flag": cf,
                "completion_event": completion_ev,
                "created_at": time.time(), "result": None, "error": None,
            }

        # Wrap on_complete to capture result for task_state persistence
        captured_result = {"data": None}
        def _capture_complete(tid, result):
            captured_result["data"] = result
            if on_complete:
                on_complete(tid, result)

        def _wrapper():
            self._set_status(task_id, "RUNNING")
            if on_status:
                on_status(task_id, "running", "Görev çalışıyor...")
            try:
                execute_fn(task_id, session_id, soru, attachments or [],
                          on_status=on_status, on_complete=_capture_complete, on_error=on_error, **kwargs)
                # Success path: capture result and finalize lifecycle
                self._set_status(task_id, "COMPLETED")
                self._finish(task_id, "COMPLETED", captured_result["data"] or {"status": "COMPLETED"})
            except TaskCancelledException:
                log(f"[EXECUTOR] Task cancelled: {task_id}")
                self._set_status(task_id, "CANCELLED")
                if on_status:
                    on_status(task_id, "cancelled", f"Task iptal edildi: {task_id}")
                self._finish(task_id, "CANCELLED", {"cancelled": True})
                if on_complete:
                    on_complete(task_id, {"status": "CANCELLED"})
            except Exception as exc:
                log(f"[EXECUTOR] Task error: {task_id} -- {exc}")
                self._set_status(task_id, "ERROR")
                if on_status:
                    on_status(task_id, "error", f"Task hatasi: {exc}")
                self._finish(task_id, "FAILED", {"error": str(exc)})
                if on_error:
                    on_error(task_id, {"error": str(exc)})
            finally:
                self._cleanup(task_id)

        t = threading.Thread(target=_wrapper, daemon=True, name=f"task-{task_id}")
        with _registry_lock:
            _tasks[task_id]["thread"] = t
        t.start()
        log(f"[EXECUTOR] Task submitted: {task_id} session={session_id}")
        return task_id

    def _set_status(self, task_id, status):
        with _registry_lock:
            if task_id in _tasks:
                _tasks[task_id]["status"] = status

    def wait_for_completion(self, task_id: str, timeout: float = 300) -> dict | None:
        """Block until task completes. Returns result dict or None on timeout."""
        with _registry_lock:
            info = _tasks.get(task_id)
            if not info:
                return None
            completion_ev = info.get("completion_event")
        if completion_ev:
            completion_ev.wait(timeout=timeout)
        with _registry_lock:
            info = _tasks.get(task_id)
            if not info:
                # Task cleaned up — check task_state for result
                try:
                    from core import task_state
                    ts = task_state.get_status(task_id)
                    if ts and ts.get("answer"):
                        return {"cevap": ts["answer"], "model": "auto", "gorev": "chat", "latency": {"total": 0}}
                except Exception:
                    pass
                return {"cevap": "", "model": "auto", "gorev": "chat", "latency": {"total": 0}, "status": "COMPLETED"}
            return info.get("result") or info.get("error")

    def _finish(self, task_id, status, result=None):
        with _registry_lock:
            if task_id in _tasks:
                _tasks[task_id]["status"] = status
                _tasks[task_id]["result"] = result
                _tasks[task_id]["finished_at"] = time.time()
                completion_ev = _tasks[task_id].get("completion_event")
                if completion_ev:
                    completion_ev.set()
        try:
            from core import task_state
            step = 0; answer = ""
            if result and isinstance(result, dict):
                lat = result.get("latency", {})
                step = int(lat.get("total", 0)) if lat else 0
                answer = result.get("cevap", result.get("error", ""))
            task_state.finish_task(task_id, step=step, status=status, answer=str(answer)[:4000])
        except Exception as e:
            log(f"[EXECUTOR] task_state.finish_task error: {e}")

    def _cleanup(self, task_id):
        with _registry_lock:
            info = _tasks.pop(task_id, None)
            if info:
                log(f"[EXECUTOR] Task cleaned up: {task_id} status={info.get('status')}")

    def pause(self, task_id):
        with _registry_lock:
            info = _tasks.get(task_id)
            if not info or info["status"] not in ("RUNNING",):
                return False
            info["pause_event"].set()
            info["status"] = "PAUSE_REQUESTED"
        log(f"[EXECUTOR] Task pause requested: {task_id}")
        return True

    def get_status(self, task_id) -> str | None:
        with _registry_lock:
            info = _tasks.get(task_id)
            return info["status"] if info else None

    def resume(self, task_id):
        with _registry_lock:
            info = _tasks.get(task_id)
            if not info or info["status"] not in ("PAUSED", "PAUSE_REQUESTED"):
                return False
            info["resume_event"].set()
            info["status"] = "RESUMING"
        log(f"[EXECUTOR] Task resume requested: {task_id}")
        return True

    def cancel(self, task_id):
        with _registry_lock:
            info = _tasks.get(task_id)
            if not info or info["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                return False
            info["cancel_flag"]["cancelled"] = True
            info["resume_event"].set()
            info["status"] = "CANCEL_REQUESTED"
        log(f"[EXECUTOR] Task cancel requested: {task_id}")
        return True

    def is_running(self, task_id):
        with _registry_lock:
            info = _tasks.get(task_id)
            return info is not None and info["status"] in ("CREATED", "RUNNING", "RESUMING", "PAUSE_REQUESTED")

    def get_task_info(self, task_id):
        with _registry_lock:
            info = _tasks.get(task_id)
            if not info:
                return None
            return {k: info[k] for k in ("task_id", "session_id", "soru", "status", "created_at", "finished_at") if k in info}

    def get_tasks_by_session(self, session_id):
        with _registry_lock:
            return [
                {k: info[k] for k in ("task_id", "session_id", "soru", "status", "created_at", "finished_at") if k in info}
                for info in _tasks.values() if info["session_id"] == session_id
            ]


# Global singleton
_executor = None

def get_executor():
    global _executor
    if _executor is None:
        _executor = TaskExecutor()
    return _executor


def check_cancel(task_id):
    """Check if task should be cancelled. Call from execute_fn.

    Raises TaskCancelledException if cancel was requested.
    Should be called at safe points between model calls.
    """
    with _registry_lock:
        info = _tasks.get(task_id)
        if info and info["cancel_flag"]["cancelled"]:
            raise TaskCancelledException(task_id)


def check_pause(task_id):
    """Check if task should pause. Call from execute_fn.

    Blocks the calling thread until resume() or cancel() is called.
    Returns True if resumed, False if cancelled.
    """
    with _registry_lock:
        info = _tasks.get(task_id)
        if not info:
            return True
        pause_ev = info["pause_event"]
        resume_ev = info["resume_event"]
        cancel_flag = info["cancel_flag"]
    if not pause_ev.is_set():
        return True
    # Transition to PAUSED
    with _registry_lock:
        _tasks[task_id]["status"] = "PAUSED"
    log(f"[EXECUTOR] Task paused: {task_id}")
    # Block until resume or cancel
    resume_ev.wait()
    resume_ev.clear()
    pause_ev.clear()
    # Check if cancelled while paused
    if cancel_flag["cancelled"]:
        raise TaskCancelledException(task_id)
    # Transition back to RUNNING
    with _registry_lock:
        if task_id in _tasks:
            _tasks[task_id]["status"] = "RUNNING"
    log(f"[EXECUTOR] Task resumed: {task_id}")
    return True

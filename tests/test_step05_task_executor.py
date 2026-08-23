"""Tests for STEP-05: Background task execution, lifecycle, pause/resume/cancel."""
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _FakeOllamaHandler(BaseHTTPRequestHandler):
    received_bodies = []
    response_content = "test cevap"
    delay = 0

    def _send(self, payload):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send({"models": [{"name": "qwen2.5:7b"}]})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", ""))
        body = json.loads(self.rfile.read(length))
        _FakeOllamaHandler.received_bodies.append(body)
        if self.delay:
            time.sleep(self.delay)
        self._send({"message": {"role": "assistant", "content": self.response_content}})

    def log_message(self, *_args):
        pass


@pytest.fixture
def fake_ollama(monkeypatch):
    _FakeOllamaHandler.received_bodies = []
    _FakeOllamaHandler.response_content = "test cevap"
    _FakeOllamaHandler.delay = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOllamaHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    import core.engine as engine
    monkeypatch.setattr(engine, "OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
    yield _FakeOllamaHandler
    server.shutdown()
    server.server_close()


@pytest.fixture
def fresh_executor():
    from core.task_executor import TaskExecutor, _tasks, _registry_lock
    with _registry_lock:
        _tasks.clear()
    executor = TaskExecutor()
    yield executor
    with _registry_lock:
        _tasks.clear()


@pytest.fixture
def session_id():
    return f"step05-test-{uuid.uuid4().hex[:8]}"


class TestTaskLifecycle:
    def test_submit_returns_task_id(self, fresh_executor, session_id):
        tid = fresh_executor.submit(session_id=session_id, soru="test")
        assert tid is not None
        assert tid.startswith("task-")
    def test_task_runs_and_completes(self, fresh_executor, session_id, fake_ollama):
        completed = threading.Event()
        result_store = {}
        def on_complete(tid, result):
            result_store[tid] = result
            completed.set()
        tid = fresh_executor.submit(session_id=session_id, soru="test", on_complete=on_complete)
        completed.wait(timeout=10)
        assert tid in result_store
        assert result_store[tid].get("cevap") == "test cevap"

    def test_task_status_lifecycle(self, fresh_executor, session_id, fake_ollama):
        statuses = []
        completed = threading.Event()
        def on_status(tid, phase, message, **kw):
            statuses.append(phase)
        def on_complete(tid, result):
            completed.set()
        tid = fresh_executor.submit(session_id=session_id, soru="test", on_status=on_status, on_complete=on_complete)
        completed.wait(timeout=10)
        assert "thinking" in statuses

    def test_task_info_available(self, fresh_executor, session_id, fake_ollama):
        completed = threading.Event()
        def on_complete(tid, result):
            completed.set()
        tid = fresh_executor.submit(session_id=session_id, soru="merhaba", on_complete=on_complete)
        info = fresh_executor.get_task_info(tid)
        assert info is not None
        assert info["task_id"] == tid
        assert info["session_id"] == session_id
        assert info["soru"] == "merhaba"


class TestTaskCancel:
    def test_cancel_running_task(self, fake_ollama):
        from core.task_executor import TaskExecutor, _tasks, _registry_lock
        with _registry_lock:
            _tasks.clear()
        executor = TaskExecutor()
        _FakeOllamaHandler.delay = 0.5
        cancelled = threading.Event()
        result_store = {}
        def on_complete(tid, result):
            result_store[tid] = result
            cancelled.set()
        tid = executor.submit(session_id="cancel-test", soru="test", on_complete=on_complete)
        time.sleep(0.05)
        ok = executor.cancel(tid)
        assert ok is True
        cancelled.wait(timeout=5)
        assert result_store.get(tid, {}).get("status") == "CANCELLED"
        with _registry_lock:
            _tasks.clear()

    def test_cancel_completed_returns_false(self, fresh_executor, session_id, fake_ollama):
        completed = threading.Event()
        def on_complete(tid, result):
            completed.set()
        tid = fresh_executor.submit(session_id=session_id, soru="test", on_complete=on_complete)
        completed.wait(timeout=5)
        ok = fresh_executor.cancel(tid)
        assert ok is False


class TestTaskListing:
    def test_list_tasks_for_workspace(self, fresh_executor, session_id, fake_ollama):
        from core import task_state
        tid = task_state.start_task("test request", workspace=session_id, model="qwen2.5")
        tasks = task_state.list_tasks_for_workspace(session_id)
        assert len(tasks) >= 1
        assert any(t.get("task_id") == tid for t in tasks)

    def test_list_tasks_empty_workspace(self):
        from core import task_state
        tasks = task_state.list_tasks_for_workspace("nonexistent-workspace-xyz")
        assert tasks == []

    def test_get_task_info_nonexistent(self, fresh_executor):
        info = fresh_executor.get_task_info("nonexistent-id")
        assert info is None


class TestConversationTaskLinkage:
    def test_set_and_get_last_task_id(self):
        from core import conversation_store
        sid = f"linkage-test-{uuid.uuid4().hex[:8]}"
        tid = f"task-{uuid.uuid4().hex[:8]}"
        conversation_store.set_last_task_id(sid, tid)
        result = conversation_store.get_last_task_id(sid)
        assert result == tid

    def test_overwrite_last_task_id(self):
        from core import conversation_store
        sid = f"linkage-test-{uuid.uuid4().hex[:8]}"
        tid1 = f"task-{uuid.uuid4().hex[:8]}"
        tid2 = f"task-{uuid.uuid4().hex[:8]}"
        conversation_store.set_last_task_id(sid, tid1)
        conversation_store.set_last_task_id(sid, tid2)
        result = conversation_store.get_last_task_id(sid)
        assert result == tid2

    def test_get_last_task_id_returns_none_for_unknown(self):
        from core import conversation_store
        result = conversation_store.get_last_task_id("nonexistent-session-xyz")
        assert result is None


class TestChatAPIBackground:
    def test_background_mode_returns_task_id(self, fake_ollama):
        """chat_api() blocks until task completes, returns {cevap, task_id}."""
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.post("/api/chat", json={"soru": "test", "session_id": "bg-test-session", "background": True})
            assert r.status_code == 200
            data = r.get_json()
            assert "task_id" in data
            assert "cevap" in data
            assert isinstance(data["cevap"], str)
        from core.task_executor import _tasks, _registry_lock
        with _registry_lock:
            _tasks.clear()

    def test_sync_mode_still_works(self, fake_ollama):
        """chat_api() blocks and returns {cevap, model, latency} for frontend."""
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.post("/api/chat", json={"soru": "test", "session_id": "sync-test"})
            assert r.status_code == 200
            data = r.get_json()
            assert "cevap" in data
            assert "model" in data
            assert "latency" in data
            assert "task_id" in data
            assert isinstance(data["cevap"], str)


class TestTaskManagementEndpoints:
    def test_list_tasks_endpoint(self, fake_ollama):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.get("/api/chat/tasks?session_id=default")
            assert r.status_code == 200
            data = r.get_json()
            assert "active_tasks" in data or "tasks" in data or "total" in data

    def test_get_task_nonexistent(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.get("/api/chat/tasks/nonexistent-task-id")
            assert r.status_code == 404

    def test_pause_nonexistent_task(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.post("/api/chat/tasks/nonexistent-task-id/pause")
            assert r.status_code == 400

    def test_resume_nonexistent_task(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.post("/api/chat/tasks/nonexistent-task-id/resume")
            assert r.status_code == 400

    def test_cancel_nonexistent_task(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.post("/api/chat/tasks/nonexistent-task-id/cancel")
            assert r.status_code == 400


class TestConcurrentTasks:
    def test_concurrent_tasks_run_independently(self, fresh_executor, fake_ollama):
        results = {}
        events = {}
        def make_complete(key):
            events[key] = threading.Event()
            def on_complete(tid, result):
                results[key] = result
                events[key].set()
            return on_complete
        tid_a = fresh_executor.submit(session_id="concurrent-a", soru="task-a", on_complete=make_complete("a"))
        tid_b = fresh_executor.submit(session_id="concurrent-b", soru="task-b", on_complete=make_complete("b"))
        events["a"].wait(timeout=10)
        events["b"].wait(timeout=10)
        assert "a" in results
        assert "b" in results
        assert tid_a != tid_b


class TestTaskStatePersistence:
    def test_start_task_creates_jsonl_entry(self):
        from core import task_state
        tid = task_state.start_task("persistence test", workspace="persist-test", model="test-model")
        loaded = task_state.load_task(tid)
        assert loaded is not None
        assert loaded["task_id"] == tid
        assert loaded["status"] == "RUNNING"

    def test_finish_task_updates_jsonl(self):
        from core import task_state
        tid = task_state.start_task("finish test", workspace="finish-test", model="m")
        task_state.finish_task(tid, step=1, status="COMPLETED", answer="done")
        loaded = task_state.load_task(tid)
        assert loaded is not None
        assert loaded["status"] == "COMPLETED"

    def test_checkpoint_persists(self):
        from core import task_state
        tid = task_state.start_task("cp test", workspace="cp-test", model="m")
        task_state.checkpoint(tid, step=1, workspace="cp-test", status="RUNNING")
        loaded = task_state.load_task(tid)
        assert loaded is not None

    def test_update_status_appends_event(self):
        from core import task_state
        tid = task_state.start_task("upd test", workspace="upd-test", model="m")
        ok = task_state.update_status(tid, "PAUSED")
        assert ok is True
        loaded = task_state.load_task(tid)
        assert loaded["status"] == "PAUSED"
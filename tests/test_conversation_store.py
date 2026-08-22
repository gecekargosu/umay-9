"""Tests for core/conversation_store.py and its wiring into ui/panel_server.py.

Covers:
- Basic roundtrip (add -> get)
- Trimming behavior (matches old in-memory _MAX_HISTORY window)
- Clearing a conversation
- Persistence across an actual OS-level process restart (the bug this
  STEP fixes — see docs/development/CHAT_CURRENT_STATE.md section 2)
- panel_server's public helpers (_get_session_history / _add_to_history /
  _clear_session) still behave the same as before, now backed by SQLite
"""
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def conv_store():
    from core import conversation_store
    return conversation_store


@pytest.fixture
def conversation_id():
    return f"test-{uuid.uuid4().hex[:8]}"


class TestConversationStoreBasics:
    def test_new_conversation_has_empty_history(self, conv_store, conversation_id):
        assert conv_store.get_history(conversation_id) == []

    def test_add_and_get_roundtrip(self, conv_store, conversation_id):
        conv_store.add_message(conversation_id, "user", "merhaba")
        conv_store.add_message(conversation_id, "assistant", "selam")
        history = conv_store.get_history(conversation_id)
        assert history == [
            {"role": "user", "content": "merhaba"},
            {"role": "assistant", "content": "selam"},
        ]

    def test_trims_to_max_pairs(self, conv_store, conversation_id):
        for i in range(30):
            conv_store.add_message(conversation_id, "user", f"soru-{i}")
            conv_store.add_message(conversation_id, "assistant", f"cevap-{i}")
        history = conv_store.get_history(conversation_id, max_pairs=5)
        assert len(history) == 10
        assert history[0]["content"] == "soru-25"
        assert history[-1]["content"] == "cevap-29"

    def test_full_history_retained_on_disk_even_when_trimmed_at_read(self, conv_store, conversation_id):
        for i in range(10):
            conv_store.add_message(conversation_id, "user", f"soru-{i}")
        # trimmed view
        assert len(conv_store.get_history(conversation_id, max_pairs=1)) == 2
        # untrimmed view proves nothing was deleted, only the read was windowed
        assert len(conv_store.get_history(conversation_id, max_pairs=100)) == 10

    def test_clear_conversation_removes_all_messages(self, conv_store, conversation_id):
        conv_store.add_message(conversation_id, "user", "hello")
        assert conv_store.get_history(conversation_id) != []
        conv_store.clear_conversation(conversation_id)
        assert conv_store.get_history(conversation_id) == []

    def test_list_conversations_includes_recent(self, conv_store, conversation_id):
        conv_store.add_message(conversation_id, "user", "hi")
        ids = [c["id"] for c in conv_store.list_conversations(limit=200)]
        assert conversation_id in ids


class TestPanelServerHelpersUsePersistentStore:
    def test_helpers_roundtrip(self, conversation_id):
        from ui import panel_server as ps
        assert ps._get_session_history(conversation_id) == []
        ps._add_to_history(conversation_id, "user", "test mesaji")
        assert ps._get_session_history(conversation_id) == [
            {"role": "user", "content": "test mesaji"}
        ]
        ps._clear_session(conversation_id)
        assert ps._get_session_history(conversation_id) == []


class TestRestartPersistence:
    """The actual regression this STEP exists to fix: history must survive
    the web process being killed and restarted, not just survive within one
    Python process's lifetime. Uses two genuinely separate OS processes —
    a shared module-level dict would fail this test even though it would
    pass every in-process test above."""

    def test_history_survives_process_restart(self, conversation_id):
        writer = subprocess.run(
            [sys.executable, "-c", f"""
import sys; sys.path.insert(0, '.')
from ui import panel_server as ps
sid = {conversation_id!r}
ps._add_to_history(sid, "user", "restart test soru")
ps._add_to_history(sid, "assistant", "restart test cevap")
"""],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert writer.returncode == 0, writer.stderr

        reader = subprocess.run(
            [sys.executable, "-c", f"""
import sys; sys.path.insert(0, '.')
from ui import panel_server as ps
sid = {conversation_id!r}
hist = ps._get_session_history(sid)
assert hist == [
    {{"role": "user", "content": "restart test soru"}},
    {{"role": "assistant", "content": "restart test cevap"}},
], hist
print("OK")
"""],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert reader.returncode == 0, reader.stderr
        assert "OK" in reader.stdout

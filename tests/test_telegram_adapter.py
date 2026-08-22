"""
UMAY Telegram Adapter + Communication Manager Tests
Unit tests for telegram_adapter.py and communication_manager.py
"""
from __future__ import annotations

import json
import time
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ─── Isolation Fixture ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolated():
    """Her testi izole çalıştır."""
    from core import communication_manager as cm_mod
    from core import telegram_adapter as ta_mod
    from core import approval_manager as am_mod
    # Singleton'ları sıfırla
    cm_mod._manager = None
    ta_mod._adapter = None
    am_mod._manager = None
    yield
    cm_mod._manager = None
    ta_mod._adapter = None
    am_mod._manager = None


# ─── CommunicationManager Tests ─────────────────────────────────────────────

class TestCommunicationManager:
    """CommunicationManager temel fonksiyon testleri."""

    def test_singleton(self):
        from core.communication_manager import get_communication_manager
        cm1 = get_communication_manager()
        cm2 = get_communication_manager()
        assert cm1 is cm2

    def test_register_adapter(self):
        from core.communication_manager import get_communication_manager
        cm = get_communication_manager()
        mock_adapter = MagicMock()
        cm.register_adapter("telegram", mock_adapter)
        assert cm.get_adapter("telegram") is mock_adapter

    def test_is_channel_active_no_adapter(self):
        from core.communication_manager import get_communication_manager
        cm = get_communication_manager()
        assert cm.is_channel_active("telegram") is False

    def test_is_channel_active_with_adapter(self):
        from core.communication_manager import get_communication_manager
        cm = get_communication_manager()
        mock_adapter = MagicMock()
        mock_adapter.is_active.return_value = True
        cm.register_adapter("telegram", mock_adapter)
        assert cm.is_channel_active("telegram") is True

    def test_send_task_started(self):
        from core.communication_manager import get_communication_manager
        cm = get_communication_manager()
        mock_adapter = MagicMock()
        cm.register_adapter("telegram", mock_adapter)
        cm.send_task_started("telegram", "task-001", "Test görev")
        mock_adapter.send_message.assert_called_once()
        msg = mock_adapter.send_message.call_args[0][0]
        assert msg.message_type == "TASK_STARTED"
        assert msg.task_id == "task-001"

    def test_send_approval_required(self):
        from core.communication_manager import get_communication_manager
        cm = get_communication_manager()
        mock_adapter = MagicMock()
        cm.register_adapter("telegram", mock_adapter)
        cm.send_approval_required(
            channel="telegram",
            task_id="task-002",
            approval_id="appr-001",
            tool_name="write_file",
            action="Dosya oluşturulacak",
            target="test.txt",
            risk="medium",
        )
        mock_adapter.send_message.assert_called_once()
        msg = mock_adapter.send_message.call_args[0][0]
        assert msg.message_type == "APPROVAL_REQUIRED"
        assert msg.task_id == "task-002"
        assert msg.approval_id == "appr-001"
        assert "write_file" in msg.body

    def test_send_task_completed(self):
        from core.communication_manager import get_communication_manager
        cm = get_communication_manager()
        mock_adapter = MagicMock()
        cm.register_adapter("telegram", mock_adapter)
        cm.send_task_completed("telegram", "task-003", "Tamamlandı")
        msg = mock_adapter.send_message.call_args[0][0]
        assert msg.message_type == "TASK_COMPLETED"

    def test_send_text(self):
        from core.communication_manager import get_communication_manager
        cm = get_communication_manager()
        mock_adapter = MagicMock()
        cm.register_adapter("telegram", mock_adapter)
        cm.send_text("telegram", "Merhaba dünya")
        msg = mock_adapter.send_message.call_args[0][0]
        assert msg.message_type == "TEXT"
        assert "Merhaba dünya" in msg.body

    def test_resolve_inbound_type_approve(self):
        from core.communication_manager import CommunicationManager
        assert CommunicationManager.resolve_inbound_type("evet") == "APPROVE"
        assert CommunicationManager.resolve_inbound_type("ONAYLA") == "APPROVE"
        assert CommunicationManager.resolve_inbound_type("onaylıyorum") == "APPROVE"
        assert CommunicationManager.resolve_inbound_type("tamam") == "APPROVE"
        assert CommunicationManager.resolve_inbound_type("devam et") == "APPROVE"

    def test_resolve_inbound_type_reject(self):
        from core.communication_manager import CommunicationManager
        assert CommunicationManager.resolve_inbound_type("hayır") == "REJECT"
        assert CommunicationManager.resolve_inbound_type("REDDET") == "REJECT"
        assert CommunicationManager.resolve_inbound_type("iptal") == "REJECT"
        assert CommunicationManager.resolve_inbound_type("dur") == "REJECT"

    def test_resolve_inbound_type_command(self):
        from core.communication_manager import CommunicationManager
        assert CommunicationManager.resolve_inbound_type("/help") == "COMMAND"
        assert CommunicationManager.resolve_inbound_type("/status") == "COMMAND"
        assert CommunicationManager.resolve_inbound_type("/approve task-001") == "COMMAND"

    def test_resolve_inbound_type_text(self):
        from core.communication_manager import CommunicationManager
        assert CommunicationManager.resolve_inbound_type("merhaba") == "TEXT"
        assert CommunicationManager.resolve_inbound_type("nasılsın") == "TEXT"

    def test_extract_task_id(self):
        from core.communication_manager import CommunicationManager
        assert CommunicationManager.extract_task_id("task-20260821-120000-a1b2c3d4") == "task-20260821-120000-a1b2c3d4"
        assert CommunicationManager.extract_task_id("Lütfen task-20260821-120000-a1b2c3d4 onayla") == "task-20260821-120000-a1b2c3d4"
        assert CommunicationManager.extract_task_id("appr-20260821-120000-a1b2c3") == "appr-20260821-120000-a1b2c3"
        assert CommunicationManager.extract_task_id("merhaba") is None

    def test_handler_registration(self):
        from core.communication_manager import get_communication_manager, InboundMessage
        cm = get_communication_manager()
        handler = MagicMock(return_value="OK")
        cm.register_handler("APPROVE", handler)
        msg = InboundMessage(
            channel="telegram",
            sender_id="123",
            sender_name="Test",
            text="evet",
            inbound_type="APPROVE",
            task_id="task-001",
        )
        result = cm.handle_inbound(msg)
        assert result == "OK"
        handler.assert_called_once()

    def test_no_handler_returns_default(self):
        from core.communication_manager import get_communication_manager, InboundMessage
        cm = get_communication_manager()
        msg = InboundMessage(
            channel="telegram",
            sender_id="123",
            sender_name="Test",
            text="merhaba",
            inbound_type="TEXT",
        )
        result = cm.handle_inbound(msg)
        assert "tanınamadı" in result


# ─── TelegramAdapter Tests ──────────────────────────────────────────────────

class TestTelegramAdapter:
    """TelegramAdapter unit testleri."""

    def test_singleton(self):
        from core.telegram_adapter import get_telegram_adapter
        ta1 = get_telegram_adapter()
        ta2 = get_telegram_adapter()
        assert ta1 is ta2

    def test_not_active_without_token(self):
        from core.telegram_adapter import get_telegram_adapter
        ta = get_telegram_adapter()
        assert ta.is_active() is False

    def test_not_configured(self):
        from core.telegram_adapter import is_telegram_configured
        assert is_telegram_configured() is False

    def test_start_without_token(self):
        from core.telegram_adapter import get_telegram_adapter
        ta = get_telegram_adapter()
        result = ta.start()
        assert result is False

    def test_start_without_allowlist_is_blocked(self, monkeypatch):
        from core.telegram_adapter import TelegramAdapter
        import core.telegram_adapter as telegram_module

        ta = TelegramAdapter()
        ta._authenticated_users.clear()
        monkeypatch.setattr(telegram_module, "TELEGRAM_BOT_TOKEN", "configured-for-test")
        ta._setup_bot = MagicMock()

        assert ta.start() is False
        ta._setup_bot.assert_not_called()
        assert ta.is_active() is False

    def test_stop_closes_client_and_waits_for_polling(self):
        from core.telegram_adapter import TelegramAdapter

        ta = TelegramAdapter()
        ta._running = True
        ta._http_client = MagicMock()
        thread = MagicMock()
        thread.is_alive.return_value = True
        ta._thread = thread

        ta.stop()

        assert ta._running is False
        thread.join.assert_called_once_with(timeout=35)

    def test_authorization_no_users_configured(self):
        """Allowed user tanımlanmamışsa erişim reddedilir."""
        from core.telegram_adapter import get_telegram_adapter
        ta = get_telegram_adapter()
        assert ta._is_authorized(12345) is False

    def test_authorization_with_configured_users(self):
        from core.telegram_adapter import TelegramAdapter
        ta = TelegramAdapter()
        ta._authenticated_users = {111, 222}
        assert ta._is_authorized(111) is True
        assert ta._is_authorized(333) is False

    def test_extract_task_id(self):
        from core.communication_manager import CommunicationManager
        assert CommunicationManager.extract_task_id("task-20260821-120000-a1b2c3d4") is not None

    def test_send_message_no_bot(self):
        """Bot yokken mesaj gönderme hata vermemeli."""
        from core.telegram_adapter import get_telegram_adapter
        ta = get_telegram_adapter()
        msg = MagicMock()
        msg.telegram_chat_id = 123
        msg.message_type = "TEXT"
        msg.body = "test"
        # Hata vermeden geçmeli
        ta.send_message(msg)

    def test_handle_command_start(self):
        from core.telegram_adapter import get_telegram_adapter
        ta = get_telegram_adapter()
        ta._send_message = MagicMock()
        ta._handle_command(123, "/start", 111, "Test")
        ta._send_message.assert_called_once()
        call_args = ta._send_message.call_args
        assert call_args[0][0] == 123
        assert "UMAY" in call_args[0][1]

    def test_handle_command_help(self):
        from core.telegram_adapter import get_telegram_adapter
        ta = get_telegram_adapter()
        ta._send_message = MagicMock()
        ta._handle_command(123, "/help", 111, "Test")
        ta._send_message.assert_called_once()
        assert "Komutları" in ta._send_message.call_args[0][1]

    def test_handle_command_unknown(self):
        from core.telegram_adapter import get_telegram_adapter
        ta = get_telegram_adapter()
        ta._send_message = MagicMock()
        ta._handle_command(123, "/unknown", 111, "Test")
        ta._send_message.assert_called_once()
        assert "Bilinmeyen" in ta._send_message.call_args[0][1]

    def test_handle_approve_no_task_id_no_pending(self):
        from core.telegram_adapter import TelegramAdapter
        from core.approval_manager import ApprovalManager
        import core.approval_manager as am_mod
        am_mod._manager = None  # singleton'ı sıfırla
        am = ApprovalManager()
        am._pending.clear()  # Tüm pending'leri temizle
        ta = TelegramAdapter()
        ta.set_approval_manager(am)
        ta._send_message = MagicMock()
        ta._handle_approve(123, None, 111, "Test", "")
        ta._send_message.assert_called_once()
        assert "yok" in ta._send_message.call_args[0][1]

    def test_handle_approve_with_task_id(self):
        from core.telegram_adapter import get_telegram_adapter
        from core.approval_manager import ApprovalManager
        ta = get_telegram_adapter()
        am = ApprovalManager()
        ta.set_approval_manager(am)
        # Onay talebi oluştur
        am.request_approval(
            task_id="task-test-001", tool_name="write_file", action="test", risk="low",
            owner_user_id=111, owner_chat_id=123,
        )
        ta._send_message = MagicMock()
        ta._resume_agent = MagicMock()
        ta._handle_approve(123, "task-test-001", 111, "Test", "")
        # Onaylandı mesajı gönderilmeli
        assert ta._send_message.call_count >= 1

    def test_handle_reject_with_task_id(self):
        from core.telegram_adapter import get_telegram_adapter
        from core.approval_manager import ApprovalManager
        ta = get_telegram_adapter()
        am = ApprovalManager()
        ta.set_approval_manager(am)
        am.request_approval(
            task_id="task-test-002", tool_name="run_command", action="test", risk="high",
            owner_user_id=111, owner_chat_id=123,
        )
        ta._send_message = MagicMock()
        ta._handle_reject(123, "task-test-002", 111, "Test", "")
        assert ta._send_message.call_count >= 1

    def test_unauthorized_user_rejected(self):
        from core.telegram_adapter import TelegramAdapter
        ta = TelegramAdapter()
        ta._authenticated_users = {111}
        ta._send_message = MagicMock()
        ta._handle_message({
            "from": {"id": 999, "first_name": "Hacker"},
            "text": "evet",
            "chat": {"id": 123},
        })
        ta._send_message.assert_called_once()
        assert "Yetkisiz" in ta._send_message.call_args[0][1]

    def test_telegram_registered_in_communication_manager(self):
        from core.communication_manager import CommunicationManager
        from core.telegram_adapter import TelegramAdapter

        manager = CommunicationManager()
        adapter = TelegramAdapter()
        adapter.set_communication_manager(manager)

        assert manager.get_adapter("telegram") is adapter
        assert len(manager._handlers["TEXT"]) == 1

    def test_message_reaches_agent_router_engine_and_telegram(self, monkeypatch):
        from core import agent as agent_module
        from core import router as router_module
        from core.communication_manager import CommunicationManager
        from core.telegram_adapter import TelegramAdapter

        manager = CommunicationManager()
        adapter = TelegramAdapter()
        adapter._authenticated_users = {111}
        adapter._bot = {"id": 1}
        adapter._send_message = MagicMock()
        adapter.set_communication_manager(manager)
        adapter.set_agent_module(agent_module)

        router_calls = []
        engine_calls = []
        agent_calls = []
        original_run_agent = agent_module.run_agent

        def fake_route(text):
            router_calls.append(text)
            return "qwen3:8b", "chat"

        def fake_engine(messages, **kwargs):
            engine_calls.append((messages, kwargs))
            return {"message": {"role": "assistant", "content": "Merhaba, ben UMAY."}}

        def spy_run_agent(*args, **kwargs):
            agent_calls.append((args, kwargs))
            return original_run_agent(*args, **kwargs)

        monkeypatch.setattr(router_module, "model_sec", fake_route)
        monkeypatch.setattr(agent_module, "resolve_model", lambda task: "qwen3:8b")
        monkeypatch.setattr(agent_module, "chat", fake_engine)
        monkeypatch.setattr(agent_module, "eylem_baslat", lambda *a, **k: "test-action")
        monkeypatch.setattr(agent_module, "eylem_tamamla", lambda *a, **k: None)
        monkeypatch.setattr(agent_module, "eylem_hata", lambda *a, **k: None)
        monkeypatch.setattr(agent_module, "_log_markdown", lambda *a, **k: None)
        monkeypatch.setattr(agent_module, "start_task", lambda *a, **k: "task-test-001")
        monkeypatch.setattr(agent_module, "finish_task", lambda *a, **k: None)
        monkeypatch.setattr(agent_module, "run_agent", spy_run_agent)

        adapter._handle_message({
            "message_id": 9,
            "from": {"id": 111, "first_name": "Cengiz"},
            "chat": {"id": 222},
            "text": "Merhaba UMAY",
        })

        assert len(agent_calls) == 1
        assert router_calls == ["Merhaba UMAY"]
        assert len(engine_calls) == 1
        assert engine_calls[0][1]["model"] == "qwen3:8b"
        assert adapter._send_message.call_args[0][0] == 222
        assert "Merhaba" in adapter._send_message.call_args[0][1]

    def test_callback_dict_uses_answer_callback(self):
        from core.telegram_adapter import TelegramAdapter

        adapter = TelegramAdapter()
        adapter._authenticated_users = {111}
        adapter._handle_approve = MagicMock()
        adapter._answer_callback = MagicMock()

        adapter._handle_callback_query({
            "id": "callback-1",
            "from": {"id": 111},
            "message": {"chat": {"id": 222}},
            "data": "approve:task-20260821-120000-a1b2c3d4",
        })

        adapter._handle_approve.assert_called_once()
        adapter._answer_callback.assert_called_once()
        assert adapter._answer_callback.call_args[0][0] == "callback-1"

    def test_media_and_voice_boundaries(self, monkeypatch):
        from core.telegram_adapter import TelegramAdapter

        adapter = TelegramAdapter()
        adapter._authenticated_users = {111}
        adapter._send_message = MagicMock()
        adapter._handle_media_message({
            "voice": {"file_id": "voice-1"},
        }, 222)
        assert "desteklenmiyor" in adapter._send_message.call_args[0][1]

    def test_polling_status_errors_are_classified(self):
        from core.telegram_adapter import (
            TelegramAdapter,
            TelegramAuthError,
            TelegramConflictError,
            TelegramPollingError,
            TelegramRateLimitError,
        )

        class Response:
            def __init__(self, status, payload=None):
                self.status_code = status
                self._payload = payload or {}

            def json(self):
                return self._payload

        cases = [
            (401, {}, TelegramAuthError),
            (409, {}, TelegramConflictError),
            (429, {"parameters": {"retry_after": 4}}, TelegramRateLimitError),
            (500, {}, TelegramPollingError),
        ]
        for status, payload, expected in cases:
            adapter = TelegramAdapter()
            client = MagicMock()
            client.get.return_value = Response(status, payload)
            adapter._http_client = client
            with pytest.raises(expected):
                adapter._get_updates()

    def test_duplicate_update_is_not_handled_twice(self):
        from core.telegram_adapter import TelegramAdapter

        adapter = TelegramAdapter()
        adapter._running = True
        handled = []
        calls = [
            [{"update_id": 7, "message": {}}],
            [{"update_id": 7, "message": {}}],
        ]

        def get_updates(**_kwargs):
            result = calls.pop(0)
            if not calls:
                adapter._running = False
            return result

        adapter._get_updates = get_updates
        adapter._handle_update = lambda update: handled.append(update)
        adapter._polling_loop()

        assert len(handled) == 1

    def test_long_message_chunks_and_markdown_fallback(self):
        from core.telegram_adapter import TelegramAdapter

        adapter = TelegramAdapter()
        responses = iter([
            MagicMock(status_code=400, json=lambda: {"ok": False}),
            MagicMock(status_code=200, json=lambda: {"ok": True}),
            MagicMock(status_code=200, json=lambda: {"ok": True}),
        ])
        calls = []

        def send(endpoint, payload, timeout):
            calls.append((endpoint, payload, timeout))
            return next(responses)

        adapter._send_telegram_json = send
        adapter._send_message(222, "*" * 5000)

        assert len(calls) == 3
        assert calls[0][1]["parse_mode"] == "Markdown"
        assert "parse_mode" not in calls[1][1]
        assert sum(len(call[1]["text"]) for call in calls[::2]) >= 5000


# ─── Integration Tests ──────────────────────────────────────────────────────

class TestTelegramApprovalIntegration:
    """Telegram + Approval Manager entegrasyon testleri."""

    def test_full_approval_flow(self):
        """Tam onay akışı: request → telegram → approve → resume."""
        from core.telegram_adapter import TelegramAdapter
        from core.approval_manager import ApprovalManager

        am = ApprovalManager()
        ta = TelegramAdapter()
        ta.set_approval_manager(am)
        ta._send_message = MagicMock()
        ta._resume_agent = MagicMock()

        # 1. Onay talebi oluştur
        apr = am.request_approval(
            task_id="task-flow-001",
            tool_name="write_file",
            action="Dosya oluşturulacak: output.py",
            target="output.py",
            risk="medium",
            owner_user_id=111,
            owner_chat_id=123,
        )
        assert apr.status == "PENDING"

        # 2. Telegram'dan onay gelir
        ta._handle_approve(123, "task-flow-001", 111, "Cengiz", "")
        assert apr.status == "APPROVED"

        # 3. Resume çağrılmalı
        ta._resume_agent.assert_called_once()

    def test_reject_flow(self):
        """Red akışı: request → telegram → reject."""
        from core.telegram_adapter import TelegramAdapter
        from core.approval_manager import ApprovalManager

        am = ApprovalManager()
        ta = TelegramAdapter()
        ta.set_approval_manager(am)
        ta._send_message = MagicMock()

        apr = am.request_approval(
            task_id="task-reject-001",
            tool_name="gmail_send_email",
            action="E-posta gönderilecek",
            risk="high",
            owner_user_id=111,
            owner_chat_id=123,
        )

        ta._handle_reject(123, "task-reject-001", 111, "Cengiz", "Şimdi yapma")
        assert apr.status == "REJECTED"

    def test_duplicate_approval_prevented(self):
        """Aynı onay iki kez verilememeli."""
        from core.telegram_adapter import TelegramAdapter
        from core.approval_manager import ApprovalManager
        import core.approval_manager as am_mod
        am_mod._manager = None
        am = ApprovalManager()
        am._pending.clear()
        ta = TelegramAdapter()
        ta.set_approval_manager(am)
        ta._send_message = MagicMock()

        apr = am.request_approval(
            task_id="task-dup-001", tool_name="write_file", action="test", risk="low",
            owner_user_id=111, owner_chat_id=123,
        )

        # İlk onay
        ta._handle_approve(123, "task-dup-001", 111, "Cengiz", "")
        assert apr.status == "APPROVED"

        # İkinci onay — zaten onaylanmış
        ta._send_message.reset_mock()
        ta._handle_approve(123, "task-dup-001", 111, "Cengiz", "")
        # "bulunamadı" veya "zaten" mesajı gelmeli
        last_msg = ta._send_message.call_args[0][1]
        assert "bulunamadı" in last_msg or "zaten" in last_msg or "APPROVED" in last_msg

    def test_multiple_pending_tasks(self):
        """Birden fazla pending task varsa rastgele seçim yapılmamalı."""
        from core.telegram_adapter import TelegramAdapter
        from core.approval_manager import ApprovalManager

        am = ApprovalManager()
        ta = TelegramAdapter()
        ta.set_approval_manager(am)
        ta._send_message = MagicMock()

        am.request_approval(
            task_id="task-multi-001", tool_name="write_file", action="a1", risk="low",
            owner_user_id=111, owner_chat_id=123,
        )
        am.request_approval(
            task_id="task-multi-002", tool_name="run_command", action="a2", risk="high",
            owner_user_id=111, owner_chat_id=123,
        )

        # Task ID olmadan onay denemesi
        ta._handle_approve(123, None, 111, "Cengiz", "")
        # Listeleme mesajı gelmeli
        ta._send_message.assert_called_once()
        msg = ta._send_message.call_args[0][1]
        assert "birden fazla" in msg.lower() or "bekliyor" in msg.lower()

    def test_cross_user_approval_is_denied(self):
        from core.telegram_adapter import TelegramAdapter
        from core.approval_manager import ApprovalManager

        am = ApprovalManager()
        ta = TelegramAdapter()
        ta.set_approval_manager(am)
        ta._send_message = MagicMock()
        approval = am.request_approval(
            task_id="task-owner-001",
            tool_name="write_file",
            action="test",
            risk="medium",
            owner_user_id=111,
            owner_chat_id=123,
        )

        ta._handle_approve(456, "task-owner-001", 222, "Other", "")

        assert approval.status == "PENDING"
        assert "bulunamadı" in ta._send_message.call_args[0][1]


# ─── Chat Regression Tests ─────────────────────────────────────────────────

class TestExistingChatRegression:
    """Mevcut chat özelliklerinin bozulmadığını doğrula."""

    def test_router_intact(self):
        from core.router import model_sec
        model, task = model_sec("Sen kimsin?")
        assert task == "chat"

    def test_engine_intact(self):
        from core.engine import MODEL_PREFERENCES
        assert "chat" in MODEL_PREFERENCES
        assert "agent" in MODEL_PREFERENCES

    def test_agent_tools_intact(self):
        from core.agent_tools import DISPATCH
        assert "read_file" in DISPATCH
        assert "write_file" in DISPATCH

    def test_identity_intact(self):
        from core.identity import UMAY_SYSTEM
        assert "UMAY" in UMAY_SYSTEM
        assert len(UMAY_SYSTEM) > 1000

    def test_approval_manager_intact(self):
        from core.approval_manager import ApprovalManager, needs_approval
        assert needs_approval("write_file") is True
        assert needs_approval("read_file") is False

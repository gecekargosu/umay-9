import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


def test_user_adapter_requires_session_and_allowlist(monkeypatch, tmp_path):
    from core.telegram_user_adapter import TelegramUserAdapter

    monkeypatch.setenv("TELEGRAM_USER_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_USER_API_HASH", "hash")
    monkeypatch.setenv("TELEGRAM_USER_ALLOWED_USER_ID", "111")
    monkeypatch.setenv("TELEGRAM_USER_SESSION_PATH", str(tmp_path / "umay_user"))
    assert TelegramUserAdapter.is_configured() is False

    Path(tmp_path / "umay_user.session").touch()
    assert TelegramUserAdapter.is_configured() is True


def test_user_adapter_authorization_uses_numeric_user_or_chat_ids(monkeypatch):
    from core.telegram_user_adapter import TelegramUserAdapter

    monkeypatch.setenv("TELEGRAM_USER_ALLOWED_USER_ID", "111, 222")
    monkeypatch.setenv("TELEGRAM_USER_ALLOWED_CHAT_ID", "-333")
    adapter = TelegramUserAdapter()
    assert adapter._authorized(111, 999) is True
    assert adapter._authorized(999, -333) is True
    assert adapter._authorized(999, 999) is False


def test_user_adapter_routes_text_through_shared_agent(monkeypatch):
    from core.communication_manager import CommunicationManager
    from core.telegram_user_adapter import TelegramUserAdapter

    manager = CommunicationManager()
    adapter = TelegramUserAdapter()
    agent = MagicMock()
    agent.run_agent.return_value = "UMAY cevap"
    adapter.set_agent_module(agent)
    adapter.set_communication_manager(manager)

    message = SimpleNamespace(
        text="Merhaba",
        context={"channel": "telegram_user", "telegram_chat_id": 44},
    )
    result = adapter._handle_text_inbound(message)

    assert result == "UMAY cevap"
    agent.run_agent.assert_called_once_with(message.text, context=message.context)
    assert manager.get_adapter("telegram_user") is adapter


def test_user_adapter_chunks_outbound_messages():
    from core.telegram_user_adapter import TelegramUserAdapter

    adapter = TelegramUserAdapter()
    sent = []

    class FakeClient:
        async def send_message(self, chat_id, text):
            sent.append((chat_id, text))

    adapter._client = FakeClient()
    error = []

    def run_sender():
        try:
            asyncio.run(adapter._send_text(44, "x" * 8500))
        except Exception as exc:
            error.append(exc)

    thread = threading.Thread(target=run_sender)
    thread.start()
    thread.join()
    assert not error

    assert [item[0] for item in sent] == [44, 44, 44]
    assert sum(len(item[1]) for item in sent) == 8500
    assert all(len(item[1]) <= 4000 for item in sent)

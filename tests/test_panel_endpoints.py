"""Tests for UMAY panel_server endpoints.

Covers:
- /api/health endpoint
- /api/telegram_status endpoint
- Telegram status background thread exists
- _get_telegram_status function
"""
import pytest


class TestHealthEndpoint:
    """Health check endpoint tests."""

    def test_health_returns_ok(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.get("/api/health")
            assert r.status_code == 200
            data = r.get_json()
            assert data["status"] == "ok"
            assert data["service"] == "umay-panel"

    def test_health_is_json(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.get("/api/health")
            assert r.content_type.startswith("application/json")


class TestTelegramStatusEndpoint:
    """Telegram status endpoint tests."""

    def test_telegram_status_returns_expected_keys(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.get("/api/telegram_status")
            assert r.status_code == 200
            data = r.get_json()
            assert "telegram_bot_connected" in data
            assert "telegram_user_connected" in data
            assert "bot_connected" in data
            assert "user_connected" in data

    def test_telegram_status_values_are_booleans(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.get("/api/telegram_status")
            data = r.get_json()
            assert isinstance(data["telegram_bot_connected"], bool)
            assert isinstance(data["telegram_user_connected"], bool)
            assert isinstance(data["bot_connected"], bool)
            assert isinstance(data["user_connected"], bool)

    def test_telegram_status_false_when_not_configured(self):
        from ui.panel_server import app
        with app.test_client() as client:
            r = client.get("/api/telegram_status")
            data = r.get_json()
            # Without bot token, status should be False
            assert data["bot_connected"] is False


class TestGetTelegramStatusFunction:
    """_get_telegram_status function tests."""

    def test_function_exists(self):
        from ui.panel_server import _get_telegram_status
        assert callable(_get_telegram_status)

    def test_function_returns_dict(self):
        from ui.panel_server import _get_telegram_status
        result = _get_telegram_status()
        assert isinstance(result, dict)

    def test_function_has_all_keys(self):
        from ui.panel_server import _get_telegram_status
        result = _get_telegram_status()
        expected_keys = {
            "telegram_bot_connected",
            "telegram_user_connected",
            "bot_connected",
            "user_connected",
        }
        assert expected_keys == set(result.keys())


class TestTelegramStatusThread:
    """Telegram status background thread tests."""

    def test_thread_function_exists(self):
        from ui.panel_server import telegram_status_dongu
        assert callable(telegram_status_dongu)


class TestPanelRegression:
    """Ensure existing functionality is not broken."""

    def test_router_intact(self):
        from core.router import model_sec
        model, task = model_sec("Merhaba")
        assert model is not None
        assert task in ("chat", "coding", "agent", "reasoning", "vision", "analysis")

    def test_engine_intact(self):
        from core.engine import resolve_model, MODEL_PREFERENCES
        assert "chat" in MODEL_PREFERENCES
        assert "coding" in MODEL_PREFERENCES

    def test_agent_tools_intact(self):
        from core.agent_tools import TOOLS, DISPATCH
        assert len(TOOLS) > 0
        assert len(DISPATCH) > 0

    def test_identity_intact(self):
        from core.identity import UMAY_SYSTEM
        assert "UMAY" in UMAY_SYSTEM
        assert len(UMAY_SYSTEM) > 100

    def test_approval_manager_intact(self):
        from core.approval_manager import get_approval_manager, needs_approval
        assert callable(needs_approval)
        mgr = get_approval_manager()
        assert mgr is not None

    def test_panel_server_has_all_routes(self):
        from ui.panel_server import app
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        assert "/" in rules
        assert "/api/chat" in rules
        assert "/api/git" in rules
        assert "/api/health" in rules
        assert "/api/telegram_status" in rules

"""
UMAY Browser Agent Tests
Browser automation, form filling, and page interaction tests.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ─── BrowserAgent Class Tests (Mock) ────────────────────────────────────────

class TestBrowserAgentInit:
    """BrowserAgent başlatma testleri."""

    def test_init_default(self):
        """Varsayılan değerlerle oluşturulabilmeli."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert agent.gorunur is True
        assert agent.yavas_mod is False
        assert agent.tarayici is None
        assert agent.sayfa is None
        assert agent.durduruldu is False

    def test_init_headless(self):
        """Headless modda oluşturulabilmeli."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent(gorunur=False)
        assert agent.gorunur is False

    def test_init_slow_mode(self):
        """Yavaş modda oluşturulabilmeli."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent(yavas_mod=True)
        assert agent.yavas_mod is True


class TestBrowserAgentMethods:
    """BrowserAgent metod testleri."""

    def test_durdur_devam_et(self):
        """Durdur/devam et mantığı çalışmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert agent.durduruldu is False
        agent.durdur()
        assert agent.durduruldu is True
        agent.devam_et()
        assert agent.durduruldu is False


class TestPageAnalysis:
    """Sayfa analiz testleri (mock ile)."""

    def test_analiz_et_returns_dict(self):
        """analiz_et dict döndürmeli."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        # sayfa None iken analiz_et çağrılırsa boş dict dönmeli
        result = agent.analiz_et()
        assert isinstance(result, dict)


class TestGoogleSearch:
    """Google arama testleri."""

    def test_google_ara_function_exists(self):
        """google_ara fonksiyonu mevcut olmalı."""
        from agents.browser_agent import google_ara
        assert callable(google_ara)

    def test_site_analiz_et_function_exists(self):
        """site_analiz_et fonksiyonu mevcut olmalı."""
        from agents.browser_agent import site_analiz_et
        assert callable(site_analiz_et)


class TestToolIntegration:
    """Tool system entegrasyon testleri."""

    def test_browser_tools_registered(self):
        """Browser tool'ları kayıtlı olmalı."""
        from core.agent_tools import TOOLS, DISPATCH

        tool_names = {t["function"]["name"] for t in TOOLS}
        assert "browser_open" in tool_names
        assert "browser_read" in tool_names
        assert "browser_click" in tool_names
        assert "browser_type" in tool_names
        assert "browser_screenshot" in tool_names
        assert "browser_close" in tool_names

        assert "browser_open" in DISPATCH
        assert "browser_read" in DISPATCH


class TestScreenshotDir:
    """Screenshot dizini testleri."""

    def test_screenshot_dir_exists(self):
        """Screenshot dizini mevcut olmalı."""
        from agents.browser_agent import SCREENSHOT_DIR
        assert SCREENSHOT_DIR.exists() or SCREENSHOT_DIR.parent.exists()

    def test_screenshot_dir_is_path(self):
        """Screenshot dizini Path nesnesi olmalı."""
        from agents.browser_agent import SCREENSHOT_DIR
        assert isinstance(SCREENSHOT_DIR, Path)


class TestFormFilling:
    """Form doldurma testleri."""

    def test_form_doldur_method_exists(self):
        """form_doldur metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "form_doldur")
        assert callable(agent.form_doldur)

    def test_dropdown_sec_method_exists(self):
        """dropdown_sec metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "dropdown_sec")
        assert callable(agent.dropdown_sec)

    def test_checkbox_isaretle_method_exists(self):
        """checkbox_isaretle metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "checkbox_isaretle")
        assert callable(agent.checkbox_isaretle)

    def test_radio_sec_method_exists(self):
        """radio_sec metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "radio_sec")
        assert callable(agent.radio_sec)


class TestTableReading:
    """Tablo okuma testleri."""

    def test_tablo_oku_method_exists(self):
        """tablo_oku metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "tablo_oku")
        assert callable(agent.tablo_oku)

    def test_linkleri_oku_method_exists(self):
        """linkleri_oku metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "linkleri_oku")
        assert callable(agent.linkleri_oku)


class TestNewCapabilities:
    """Yeni yetenek testleri."""

    def test_buton_bul_method_exists(self):
        """buton_bul metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "buton_bul")
        assert callable(agent.buton_bul)

    def test_sayfa_ozet_method_exists(self):
        """sayfa_ozet metodu mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        assert hasattr(agent, "sayfa_ozet")
        assert callable(agent.sayfa_ozet)

    def test_sayfa_ozet_returns_dict(self):
        """sayfa_ozet dict döndürmeli."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        result = agent.sayfa_ozet()
        assert isinstance(result, dict)


# ─── Regression Test ────────────────────────────────────────────────────────

class TestRegression:
    """Regresyon testleri."""

    def test_all_original_methods_exist(self):
        """Tüm orijinal metodlar mevcut olmalı."""
        from agents.browser_agent import BrowserAgent
        agent = BrowserAgent()
        
        original_methods = [
            "baslat", "kapat", "git", "yaz", "tikla", "ara",
            "sayfa_metni", "sayfa_html", "sayfa_baslik", "ekran_al",
            "analiz_et", "dosya_yukle", "bekle_eleman",
            "durdur", "devam_et",
        ]
        
        for method in original_methods:
            assert hasattr(agent, method), f"{method} metodu eksik"

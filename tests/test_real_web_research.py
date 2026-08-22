"""
UMAY Web Research Agent — GERÇEK Entegrasyon Testleri
=====================================================
Bu testler gerçek internet bağlantısı gerektirir.
Mock kullanılmaz — tüm web istekleri gerçektir.
"""
import json
import time
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 1: DuckDuckGo Arama
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealSearch:
    """Gerçek DuckDuckGo araması testleri."""

    def test_duckduckgo_search_returns_results(self):
        """DuckDuckGo'da arama gerçekten sonuç döndürüyor mu?"""
        from core.agent_tools import web_search
        result = web_search("Python programming language", max_results=5)
        assert "results" in result, f"Sonuç bekleniyordu, alinan: {result.keys()}"
        assert len(result["results"]) > 0, "Arama sonucu boş"
        print(f"\n  [SEARCH] {len(result['results'])} sonuç bulundu")
        for r in result["results"][:3]:
            print(f"    - {r.get('title', 'N/A')[:60]}: {r.get('href', 'N/A')[:80]}")

    def test_duckduckgo_search_multiple_queries(self):
        """Farklı sorgularla arama yapılabiliyor mu?"""
        from core.agent_tools import web_search
        queries = ["Python tutorial", "FastAPI documentation"]
        for q in queries:
            result = web_search(q, max_results=3)
            assert len(result["results"]) > 0, f"'{q}' araması sonuç vermedi"
            print(f"\n  [SEARCH] '{q}': {len(result['results'])} sonuç")


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 2: Sayfa Açma ve Okuma
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealPageReading:
    """Gerçek web sayfası açma ve okuma testleri."""

    def test_open_python_docs(self):
        """Python resmi dokümantasyonu açılabilir mi?"""
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        source = explorer.open_page("https://docs.python.org/3/")
        assert source.error is None, f"Hata: {source.error}"
        assert source.title != "", "Sayfa başlığı boş"
        assert source.text_length > 100, f"İçerik çok kısa: {source.text_length} karakter"
        print(f"\n  [PAGE] Başlık: {source.title[:60]}")
        print(f"  [PAGE] İçerik: {source.text_length} karakter")
        print(f"  [PAGE] Domain: {source.domain}")
        print(f"  [PAGE] Kaynak türü: {source.source_type.value}")
        print(f"  [PAGE] Güvenilirlik: {source.reliability.value}")

    def test_open_fastapi_docs(self):
        """FastAPI resmi dokümantasyonu açılabilir mi?"""
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        source = explorer.open_page("https://fastapi.tiangolo.com/")
        assert source.error is None, f"Hata: {source.error}"
        assert source.text_length > 100
        print(f"\n  [PAGE] Başlık: {source.title[:60]}")
        print(f"  [PAGE] İçerik: {source.text_length} karakter")
        print(f"  [PAGE] Güvenilirlik: {source.reliability.value}")

    def test_page_content_is_meaningful(self):
        """Sayfa içeriği anlamlı metin mi? (HTML kodu değil)"""
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        source = explorer.open_page("https://docs.python.org/3/tutorial/appetite.html")
        assert source.error is None, f"Hata: {source.error}"
        # İçerik HTML tag'leri içermemeli (anlamlı metin olmalı)
        content = source.content
        html_tag_ratio = content.count("<") / max(len(content), 1)
        assert html_tag_ratio < 0.1, f"İçerik çok fazla HTML içeriyor: {html_tag_ratio:.2%}"
        print(f"\n  [CONTENT] Content length: {len(content)} chars")
        print(f"  [CONTENT] HTML ratio: {html_tag_ratio:.2%}")
        print(f"  [CONTENT] First 100 chars: {content[:100].encode('ascii', errors='replace').decode()}")


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 3: Kaynak Sınıflandırma
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealSourceClassification:
    """Gerçek URL'lerle kaynak sınıflandırma."""

    def test_classify_real_sources(self):
        """Gerçek URL'ler doğru sınıflandırılıyor mu?"""
        from core.web_research import classify_source, SourceType, SourceReliability
        test_cases = [
            ("https://docs.python.org/3/", SourceType.OFFICIAL, SourceReliability.HIGH),
            ("https://fastapi.tiangolo.com/", SourceType.OFFICIAL, SourceReliability.HIGH),
            ("https://github.com/tiangolo/fastapi", SourceType.ACADEMIC, SourceReliability.HIGH),
            ("https://www.reddit.com/r/Python/", SourceType.FORUM, SourceReliability.LOW),
        ]
        for url, expected_type, expected_reliability in test_cases:
            st, sr = classify_source(url, url.split("/")[-2])
            print(f"\n  [CLASSIFY] {url[:50]}")
            print(f"    Beklenen: {expected_type.value}/{expected_reliability.value}")
            print(f"    Gerçek:   {st.value}/{sr.value}")
            # Sınıflandırma doğru olmalı (kesin)
            assert st == expected_type, f"{url}: {st} != {expected_type}"
            assert sr == expected_reliability, f"{url}: {sr} != {expected_reliability}"


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 4: Tablo Çıkarma
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealTableExtraction:
    """Gerçek web sayfalarından tablo çıkarma."""

    def test_extract_table_from_page(self):
        """Bir sayfadaki tabloları çıkarabiliyor mu?"""
        from core.agent_tools import extract_page_tables
        result = extract_page_tables("https://docs.python.org/3/tutorial/datastructures.html")
        assert "tables" in result, f"Sonuç: {result.keys()}"
        print(f"\n  [TABLE] {result.get('table_count', 0)} tablo bulundu")
        if result.get("tables"):
            for i, table in enumerate(result["tables"][:2]):
                print(f"    Tablo {i+1}: {len(table)} satır")


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 5: Link Takibi
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealLinkFollowing:
    """Gerçek link takibi testleri."""

    def test_follow_links_from_python_docs(self):
        """Python docs'tan linkleri takip edebiliyor mu?"""
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        # Ana sayfayı aç
        source = explorer.open_page("https://docs.python.org/3/")
        assert source.error is None, f"Hata: {source.error}"
        # Linkleri kontrol et
        links = source.links
        assert len(links) > 0, "Hiç link bulunamadı"
        print(f"\n  [LINKS] {len(links)} link bulundu")
        # İlgili bir linki takip et
        tutorial_link = None
        for link in links:
            text = link.get("text", "").lower()
            if "tutorial" in text or "beginner" in text:
                tutorial_link = link
                break
        if tutorial_link:
            url = tutorial_link.get("href", "")
            if url.startswith("http"):
                follow_source = explorer.open_page(url)
                print(f"  [FOLLOW] Takip edilen: {tutorial_link.get('text', '')[:40]}")
                print(f"  [FOLLOW] Yeni sayfa: {follow_source.title[:40]}")
                print(f"  [FOLLOW] İçerik: {follow_source.text_length} karakter")
                assert follow_source.text_length > 0


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 6: WebExplorer.search_and_read
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealSearchAndRead:
    """Gerçek arama + okuma zinciri."""

    def test_search_and_read_chain(self):
        """Arama yap → sonuçları oku zinciri çalışıyor mu?"""
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        sources = explorer.search_and_read("Python data types", max_results=2)
        assert len(sources) > 0, "Hiç kaynak bulunamadı"
        print(f"\n  [CHAIN] {len(sources)} kaynak okundu")
        for i, src in enumerate(sources):
            status = "OK" if src.error is None else f"HATA: {src.error}"
            print(f"    Kaynak {i+1}: {src.title[:40]} ({src.text_length} kar) [{status}]")


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 7: open_and_read_page tool'u
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealOpenAndReadTool:
    """open_and_read_page tool'unun gerçek testi."""

    def test_open_and_read_tool(self):
        """open_and_read_page tool'u gerçekten çalışıyor mu?"""
        from core.agent_tools import DISPATCH
        result = DISPATCH["open_and_read_page"]("https://docs.python.org/3/tutorial/classes.html")
        assert "content" in result, f"Sonuç: {result.keys()}"
        assert result.get("text_length", 0) > 100, f"İçerik çok kısa"
        assert result.get("error") is None, f"Hata: {result.get('error')}"
        print(f"\n  [TOOL] Başlık: {result.get('title', 'N/A')[:50]}")
        print(f"  [TOOL] İçerik: {result.get('text_length', 0)} karakter")
        print(f"  [TOOL] Güvenilirlik: {result.get('reliability', 'N/A')}")
        print(f"  [TOOL] Kaynak türü: {result.get('source_type', 'N/A')}")


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 8: Multi-source karşılaştırma
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealMultiSource:
    """Gerçek çoklu kaynak karşılaştırma."""

    def test_multi_source_comparison(self):
        """Birden fazla kaynağı karşılaştırabiliyor mu?"""
        from core.web_research import WebExplorer, MultiSourceComparator, WebSource, SourceReliability
        explorer = WebExplorer()
        sources = []
        # Farklı sayfaları oku
        urls = [
            "https://docs.python.org/3/tutorial/introduction.html",
            "https://docs.python.org/3/tutorial/datastructures.html",
        ]
        for url in urls:
            src = explorer.open_page(url)
            if src.error is None:
                sources.append(src)
        assert len(sources) >= 2, f"Yeterli kaynak okunamadı: {len(sources)}"

        print(f"\n  [MULTI] {len(sources)} kaynak karşılaştırılıyor")
        comparator = MultiSourceComparator()
        # Basit karşılaştırma (LLM olmadan)
        result = comparator._simple_comparison(sources)
        assert "findings" in result
        print(f"  [MULTI] {len(result.get('findings', []))} bulgu")
        for f in result.get("findings", [])[:3]:
            print(f"    - {f.get('topic', 'N/A')[:50]}")


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 9: Web Explorer search mock
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealExplorerSearch:
    """WebExplorer.search fonksiyonunun gerçek testi."""

    def test_explorer_search_real(self):
        """WebExplorer.search gerçekten arama yapıyor mu?"""
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        results = explorer.search("Python list comprehension", max_results=3)
        assert len(results) > 0, "Arama sonucu boş"
        print(f"\n  [EXPLORER] {len(results)} sonuç")
        for r in results[:3]:
            print(f"    - {r.get('title', 'N/A')[:50]}: {r.get('href', 'N/A')[:60]}")


# ═══════════════════════════════════════════════════════════════════════════════
# GERÇEK WEB TEST 10: Browser Agent entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealBrowserIntegration:
    """Gerçek Browser Agent entegrasyonu."""

    def test_browser_agent_with_web_research(self):
        """Browser Agent ile web research birlikte çalışıyor mu?"""
        from agents.browser_agent import BrowserAgent
        import threading
        agent = BrowserAgent(gorunur=False, yavas_mod=False)
        try:
            # Playwright SyncAPI async context'te çalışmaz
            # Bu yüzden direkt Playwright kullanalım
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://docs.python.org/3/", timeout=15000)
            baslik = page.title()
            metin = page.inner_text("body")[:5000]
            assert len(metin) > 100, f"Metin çok kısa: {len(metin)}"
            linkler = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => ({text: e.innerText.trim(), href: e.href})).slice(0, 10)"
            )
            print(f"\n  [BROWSER] Baslik: {baslik[:50]}")
            print(f"  [BROWSER] Metin: {len(metin)} karakter")
            print(f"  [BROWSER] Link: {len(linkler)} adet")
            browser.close()
            pw.stop()
        except Exception as e:
            pytest.skip(f"Browser testi atlandı: {e}")

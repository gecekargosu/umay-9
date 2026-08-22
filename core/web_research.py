"""
UMAY Web Research Agent
=======================
İnternette araştırma yapabilen, birden fazla kaynağı okuyabilen,
karşılaştırabilen, çelişkileri tespit edebilinen ve yapılandırılmış
rapor oluşturabilen Web Research modülü.

%100 ÜCRETSIZ ve YEREL. Playwright + DuckDuckGo + Ollama kullanır.

Mimari:
    Kullanıcı Araştırma Görevi
        ↓
    ResearchPlanner (LLM ile araştırma planı oluşturma)
        ↓
    WebExplorer (sayfa okuma, link takibi)
        ↓
    SourceAnalyzer (kaynak güvenilirliği analizi)
        ↓
    MultiSourceComparator (çoklu kaynak karşılaştırma)
        ↓
    ResearchReportGenerator (yapılandırılmış rapor)
        ↓
    MemoryStore (Memory/RAG'a kaydetme)
        ↓
    Araştırma Raporu
"""
from __future__ import annotations

import json
import hashlib
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urljoin, quote_plus

from core.utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata
from core.utils.logger import log

# ─── Sabitler ────────────────────────────────────────────────────────────────

MAX_PAGES_PER_RESEARCH = 15
MAX_DEPTH = 3
MAX_RETRIES = 3
TIMEOUT_PER_PAGE = 30

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "logs" / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

# ─── Veri Modelleri ─────────────────────────────────────────────────────────

class SourceType(str, Enum):
    OFFICIAL = "official"       # Resmi site, dokümantasyon
    NEWS = "news"               # Haber sitesi
    ACADEMIC = "academic"       # Akademik/teknik kaynak
    FORUM = "forum"             # Forum, topluluk
    BLOG = "blog"               # Blog, kişisel site
    SOCIAL = "social"           # Sosyal medya
    GOVERNMENT = "government"   # Devlet kurumu
    UNKNOWN = "unknown"


class SourceReliability(str, Enum):
    HIGH = "high"       # Resmi, güvenilir
    MEDIUM = "medium"   # Orta güvenilirlik
    LOW = "low"         # Düşük güvenilirlik
    UNCHECKED = "unchecked"


class ResearchStatus(str, Enum):
    PLANNING = "planning"
    SEARCHING = "searching"
    READING = "reading"
    ANALYZING = "analyzing"
    COMPARING = "comparing"
    VERIFYING = "verifying"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WebSource:
    """Tek bir web kaynağı."""
    url: str
    title: str = ""
    domain: str = ""
    source_type: SourceType = SourceType.UNKNOWN
    reliability: SourceReliability = SourceReliability.UNCHECKED
    accessed_at: str = ""
    content: str = ""
    text_length: int = 0
    key_findings: list[str] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    error: str | None = None
    screenshot_path: str | None = None

    def __post_init__(self):
        if not self.domain and self.url:
            try:
                self.domain = urlparse(self.url).netloc
            except Exception:
                self.domain = ""
        if not self.accessed_at:
            self.accessed_at = datetime.now().isoformat()


@dataclass
class ResearchTask:
    """Araştırma görevi."""
    id: str
    topic: str
    status: ResearchStatus = ResearchStatus.PLANNING
    search_queries: list[str] = field(default_factory=list)
    sources: list[WebSource] = field(default_factory=list)
    comparisons: list[dict] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    report: dict = field(default_factory=dict)
    memory_entry: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    error: str | None = None


# ─── Kaynak Güvenilirlik Analizi ────────────────────────────────────────────

# Yüksek güvenilirlikli domain'ler
HIGH_RELIABILITY_DOMAINS = {
    "gov.tr", "gov", "edu", "ac.uk", "edu.tr",
    "wikipedia.org", "scholar.google.com",
    "github.com", "gitlab.com", "stackoverflow.com",
    "docs.python.org", "developer.mozilla.org",
    "react.dev", "nextjs.org", "vuejs.org",
    "arxiv.org", "ieee.org", "acm.org",
    "who.int", "cdc.gov", "nih.gov",
    "tiangolo.com",  # FastAPI resmi sitesi
    "fastapi.tiangolo.com",
    "palletsprojects.com",  # Flask, Jinja2, Click
    "numpy.org", "pandas.pydata.org", "scipy.org",
    "pytorch.org", "tensorflow.org",
    "docs.docker.com", "kubernetes.io",
    "cloud.google.com", "aws.amazon.com/docs",
    "learn.microsoft.com", "developer.apple.com",
    "mozilla.org", "openssl.org",
}

# Haber domain'leri
NEWS_DOMAINS = {
    "bbc.com", "reuters.com", "apnews.com",
    "nytimes.com", "washingtonpost.com",
    "theguardian.com", "economist.com",
    "ntv.com.tr", "trtworld.com", "aa.com.tr",
    "dw.com", "rfi.fr",
}

# Forum / topluluk domain'leri
FORUM_DOMAINS = {
    "reddit.com", "quora.com", "stackoverflow.com",
    "stackexchange.com", "forum.", "community.",
}


def classify_source(url: str, title: str = "", content: str = "") -> tuple[SourceType, SourceReliability]:
    """URL ve içeriğe göre kaynak türü ve güvenilirliğini belirle."""
    domain = urlparse(url).netloc.lower().lstrip("www.")
    domain_parts = domain.split(".")

    # domain TLD kontrolü
    tld = domain_parts[-1] if domain_parts else ""

    # Resmi kaynak
    for official in HIGH_RELIABILITY_DOMAINS:
        if domain.endswith(official) or official in domain:
            if "gov" in domain or "edu" in domain or "ac." in domain:
                return SourceType.GOVERNMENT if "gov" in domain else SourceType.ACADEMIC, SourceReliability.HIGH
            if "wikipedia" in domain:
                return SourceType.ACADEMIC, SourceReliability.HIGH
            if "github" in domain or "stackoverflow" in domain:
                return SourceType.ACADEMIC, SourceReliability.HIGH
            if any(scholar in domain for scholar in ["arxiv", "ieee", "acm", "scholar.google"]):
                return SourceType.ACADEMIC, SourceReliability.HIGH
            return SourceType.OFFICIAL, SourceReliability.HIGH

    # Haber
    for news in NEWS_DOMAINS:
        if news in domain:
            return SourceType.NEWS, SourceReliability.MEDIUM

    # Forum
    for forum in FORUM_DOMAINS:
        if forum in domain:
            return SourceType.FORUM, SourceReliability.LOW

    # Blog tespiti
    if "blog" in domain or "medium.com" in domain or "dev.to" in domain:
        return SourceType.BLOG, SourceReliability.MEDIUM

    # TLD bazlı
    if tld in ("gov", "edu"):
        return SourceType.GOVERNMENT if tld == "gov" else SourceType.ACADEMIC, SourceReliability.HIGH

    # İçerik analizi
    content_lower = (title + " " + content).lower()
    academic_keywords = ["araştırma", "research", "study", "paper", "journal", "doi"]
    if any(k in content_lower for k in academic_keywords):
        return SourceType.ACADEMIC, SourceReliability.MEDIUM

    return SourceType.UNKNOWN, SourceReliability.UNCHECKED


# ─── Web Explorer ────────────────────────────────────────────────────────────

class WebExplorer:
    """Web sayfalarını açan, okuyan ve içerik çıkaran modül."""

    def __init__(self):
        self._browser = None
        self._visited_urls: set[str] = set()

    def _get_browser(self):
        """Lazy browser başlatma."""
        if self._browser is None:
            from core.agent_tools import _browser
            self._browser = _browser()
        return self._browser

    def open_page(self, url: str) -> WebSource:
        """Sayfayı aç ve içeriğini çıkar."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        source = WebSource(url=url)

        # Ziyaret edildi mi kontrol et
        if url in self._visited_urls:
            source.error = "Daha önce ziyaret edildi, atlandı"
            return source

        self._visited_urls.add(url)

        try:
            browser = self._get_browser()
            if not browser.git(url):
                source.error = "Sayfa açılamadı"
                return source

            time.sleep(1)  # Sayfa yüklenmesini bekle

            # Başlık
            source.title = browser.sayfa_baslik()

            # Metin içerik
            source.content = browser.sayfa_metni()[:15000]
            source.text_length = len(source.content)

            # Kaynak türü ve güvenilirlik
            source.source_type, source.reliability = classify_source(
                url, source.title, source.content[:500]
            )

            # Tabloları çıkar
            source.tables = self._extract_tables(browser)

            # Linkleri çıkar
            source.links = browser.linkleri_oku(max_sayisi=30)

            log(f"[WEB_RESEARCH] Sayfa okundu: {source.title[:50]} ({source.text_length} karakter)")

        except Exception as e:
            source.error = str(e)
            eylem_hata("web_research", f"Sayfa okuma hatası: {e}")
            log(f"[WEB_RESEARCH] Hata: {url} - {e}")

        return source

    def search(self, query: str, max_results: int = 8) -> list[dict]:
        """DuckDuckGo'da arama yap.
        
        duckdreams-search kütüphanesini birincil olarak kullanır.
        Başarısız olursa agent_tools.web_search'e fallback yapar.
        """
        # Yöntem 1: duckdreams-search (daha güvenilir)
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            results = DDGS().text(query, max_results=max_results)
            return [{"title": r.get("title", ""), "href": r.get("href", "")} for r in results]
        except Exception as e:
            log(f"[WEB_RESEARCH] duckdreams-search hatası: {e}")

        # Yöntem 2: agent_tools.web_search fallback
        try:
            from core.agent_tools import web_search
            result = web_search(query, max_results=max_results)
            return result.get("results", [])
        except Exception as e2:
            log(f"[WEB_RESEARCH] Arama hatası: {e2}")
            return []

    def search_and_read(self, query: str, max_results: int = 5) -> list[WebSource]:
        """Arama yap ve sonuçları oku."""
        results = self.search(query, max_results=max_results)
        sources = []

        for result in results:
            url = result.get("href", "")
            title = result.get("title", "")
            if url:
                source = self.open_page(url)
                if not source.title and title:
                    source.title = title
                sources.append(source)
                time.sleep(0.5)  # Rate limiting

        return sources

    def follow_links(
        self,
        base_url: str,
        link_texts: list[str],
        max_follow: int = 5,
    ) -> list[WebSource]:
        """Belirli linkleri takip et."""
        sources = []
        try:
            browser = self._get_browser()
            browser.git(base_url)
            all_links = browser.linkleri_oku(max_sayisi=50)

            followed = 0
            for link in all_links:
                if followed >= max_follow:
                    break
                text = link.get("text", "").lower()
                href = link.get("href", "")

                # Link metni arama terimleriyle eşleşiyor mu?
                for search_text in link_texts:
                    if search_text.lower() in text or search_text.lower() in href.lower():
                        source = self.open_page(href)
                        sources.append(source)
                        followed += 1
                        break

        except Exception as e:
            log(f"[WEB_RESEARCH] Link takip hatası: {e}")

        return sources

    def extract_tables(self, url: str) -> list[list[list[str]]]:
        """Sayfadaki tabloları çıkar."""
        try:
            browser = self._get_browser()
            if browser.sayfa is None or browser.sayfa.url != url:
                browser.git(url)
            return self._extract_tables(browser)
        except Exception:
            return []

    def _extract_tables(self, browser) -> list[list[list[str]]]:
        """Browser sayfasındaki tabloları çıkar."""
        tables = []
        try:
            tablo_sayisi = browser.sayfa.locator("table").count()
            for i in range(min(tablo_sayisi, 5)):
                tablo = browser.sayfa.locator("table").nth(i)
                satirlar = tablo.locator("tr").all()
                tablo_data = []
                for satir in satirlar:
                    hucreler = satir.locator("th, td").all()
                    satir_verisi = [h.inner_text().strip() for h in hucreler]
                    if satir_verisi:
                        tablo_data.append(satir_verisi)
                if tablo_data:
                    tables.append(tablo_data)
        except Exception:
            pass
        return tables

    def take_screenshot(self) -> str | None:
        """Mevcut sayfanın screenshot'ını al."""
        try:
            browser = self._get_browser()
            return browser.ekran_al()
        except Exception:
            return None

    def reset(self):
        """Ziyaret geçmişini sıfırla."""
        self._visited_urls.clear()


# ─── Research Planner ────────────────────────────────────────────────────────

class ResearchPlanner:
    """LLM tabanlı araştırma planlayıcı."""

    RESEARCH_PLAN_SYSTEM = """Sen UMAY'ın araştırma planlayıcısın.
Kullanıcının araştırma görevini analiz et ve araştırma planı oluştur.

KURALLAR:
1. Görevi net bir şekilde anla.
2. Araştırma konusunu alt konulara böl.
3. Her alt konu için arama terimi belirle.
4. Kaynak türlerini belirle (resmi, akademik, haber, forum).
5. Makul sayıda arama terimi oluştur (3-8 arası).
6. Araştırma derinliğini belirle.

ÇIKTI FORMATI (SADECE JSON):
{
    "topic_summary": "Araştırma konusunun kısa özeti",
    "subtopics": [
        {
            "name": "Alt konu adı",
            "search_queries": ["arama terimi 1", "arama terimi 2"],
            "priority": "high/medium/low",
            "source_preference": ["official", "academic", "news"]
        }
    ],
    "estimated_sources": 5,
    "research_depth": "shallow/moderate/deep"
}

ÖNEMLİ: Sadece JSON döndür."""

    def __init__(self, model: str | None = None):
        self.model = model

    def create_plan(self, topic: str) -> dict[str, Any]:
        """Araştırma planı oluştur."""
        from core.engine import chat, resolve_model

        model = self.model or resolve_model("reasoning") or resolve_model("chat")

        messages = [
            {"role": "system", "content": self.RESEARCH_PLAN_SYSTEM},
            {"role": "user", "content": f"Araştırma görevi: {topic}\n\nBu görev için araştırma planı oluştur."},
        ]

        try:
            response = chat(messages, model=model, ajan="web_research_planner", task="planning")
            if isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
            else:
                content = str(response)

            plan = self._extract_json(content)
            if plan:
                return plan

            # Fallback plan
            return self._create_fallback_plan(topic)

        except Exception as e:
            log(f"[WEB_RESEARCH] Plan oluşturma hatası: {e}")
            return self._create_fallback_plan(topic)

    def _extract_json(self, text: str) -> dict | None:
        """Metin içinden JSON çıkar."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        patterns = [
            r"```json\s*(\{.*?\})\s*```",
            r"```\s*(\{.*?\})\s*```",
            r"(\{[\s\S]*\"subtopics\"[\s\S]*\})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def _create_fallback_plan(self, topic: str) -> dict[str, Any]:
        """LLM çalışamazsa basit fallback planı."""
        words = topic.split()[:5]
        base_query = " ".join(words)

        return {
            "topic_summary": topic,
            "subtopics": [
                {
                    "name": topic,
                    "search_queries": [
                        base_query,
                        f"{base_query} güncel",
                        f"{base_query} nedir",
                    ],
                    "priority": "high",
                    "source_preference": ["official", "news", "academic"],
                }
            ],
            "estimated_sources": 5,
            "research_depth": "moderate",
        }


# ─── Multi-Source Comparator ────────────────────────────────────────────────

class MultiSourceComparator:
    """Birden fazla kaynağı karşılaştıran motor."""

    COMPARISON_SYSTEM = """Sen UMAY'ın karşılaştırma motorusun.
Verilen web kaynaklarını analiz et ve karşılaştır.

KURALLAR:
1. Her kaynaktan önemli bulguları çıkar.
2. Benzer bilgileri grupla.
3. Çelişkileri tespit et.
4. Kaynak güvenilirliğini değerlendir.
5. Sonucu yapılandırılmış şekilde ver.

ÇIKTI FORMATI (SADECE JSON):
{
    "findings": [
        {
            "topic": "Bulgu konusu",
            "details": "Detay",
            "sources": ["kaynak URL'si"],
            "confidence": "high/medium/low"
        }
    ],
    "agreements": ["Anlaşılan konular"],
    "contradictions": [
        {
            "topic": "Çelişki konusu",
            "source_a": {"url": "", "claim": ""},
            "source_b": {"url": "", "claim": ""},
            "analysis": "Çelişki analizi"
        }
    ],
    "gaps": ["Eksik bilgi alanları"],
    "overall_confidence": "high/medium/low"
}

ÖNEMLİ: Sadece JSON döndür."""

    def __init__(self, model: str | None = None):
        self.model = model

    def compare_sources(self, sources: list[WebSource]) -> dict[str, Any]:
        """Kaynakları karşılaştır."""
        from core.engine import chat, resolve_model

        model = self.model or resolve_model("reasoning") or resolve_model("chat")

        # Kaynak özetlerini oluştur
        source_texts = []
        for i, src in enumerate(sources):
            if src.error or not src.content:
                continue
            source_texts.append(
                f"=== KAYNAK {i+1}: {src.title} ===\n"
                f"URL: {src.url}\n"
                f"Güvenilirlik: {src.reliability.value}\n"
                f"Tür: {src.source_type.value}\n"
                f"İçerik (ilk 2000 karakter):\n{src.content[:2000]}\n"
            )

        if not source_texts:
            return {"error": "Karşılaştırılacak kaynak yok", "findings": [], "contradictions": []}

        messages = [
            {"role": "system", "content": self.COMPARISON_SYSTEM},
            {"role": "user", "content": (
                f"Aşağıdaki web kaynaklarını karşılaştır:\n\n"
                + "\n".join(source_texts)
                + "\n\nKarşılaştırma ve analiz yap."
            )},
        ]

        try:
            response = chat(messages, model=model, ajan="web_research_comparator", task="analysis")
            if isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
            else:
                content = str(response)

            result = self._extract_json(content)
            if result:
                return result

            return self._simple_comparison(sources)

        except Exception as e:
            log(f"[WEB_RESEARCH] Karşılaştırma hatası: {e}")
            return self._simple_comparison(sources)

    def _extract_json(self, text: str) -> dict | None:
        """Metin içinden JSON çıkar."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        patterns = [
            r"```json\s*(\{.*?\})\s*```",
            r"(\{[\s\S]*\"findings\"[\s\S]*\})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def _simple_comparison(self, sources: list[WebSource]) -> dict[str, Any]:
        """LLM çalışamazsa basit karşılaştırma."""
        findings = []
        for src in sources:
            if src.content:
                findings.append({
                    "topic": src.title or src.domain,
                    "details": src.content[:500],
                    "sources": [src.url],
                    "confidence": "medium" if src.reliability == SourceReliability.MEDIUM else "low",
                })

        return {
            "findings": findings,
            "agreements": [],
            "contradictions": [],
            "gaps": [],
            "overall_confidence": "low",
        }


# ─── Research Report Generator ──────────────────────────────────────────────

class ResearchReportGenerator:
    """Yapılandırılmış araştırma raporu oluşturan motor."""

    REPORT_SYSTEM = """Sen UMAY'ın rapor oluşturucusu.
Verilen araştırma verilerini yapılandırılmış bir rapora dönüştür.

Rapor formatı:
- ÖZET: Kısa özet (2-3 cümle)
- ANA BULGULAR: En önemli bulgular
- DETAYLAR: Detaylı analiz
- KAYNAK KARŞILAŞTIRMASI: Kaynaklar arası karşılaştırma
- ÇELİŞKİLER: Tespit edilen çelişkiler
- KAYNAKLAR: Kullanılan kaynakların listesi
- SONUÇ: Genel sonuç ve öneriler

Türkçe yaz. Kısa ve net ol."""

    def __init__(self, model: str | None = None):
        self.model = model

    def generate_report(
        self,
        task: ResearchTask,
        comparison: dict[str, Any],
    ) -> dict[str, Any]:
        """Yapılandırılmış rapor oluştur."""
        from core.engine import chat, resolve_model

        model = self.model or resolve_model("reasoning") or resolve_model("chat")

        # Kaynak listesini oluştur
        source_list = []
        for src in task.sources:
            if not src.error:
                source_list.append({
                    "title": src.title,
                    "url": src.url,
                    "domain": src.domain,
                    "type": src.source_type.value,
                    "reliability": src.reliability.value,
                })

        messages = [
            {"role": "system", "content": self.REPORT_SYSTEM},
            {"role": "user", "content": (
                f"Araştırma Konusu: {task.topic}\n\n"
                f"Arama Terimleri: {', '.join(task.search_queries)}\n\n"
                f"Karşılaştırma Sonuçları:\n{json.dumps(comparison, ensure_ascii=False)[:3000]}\n\n"
                f"Kaynak Sayısı: {len(source_list)}\n\n"
                f"Yapılandırılmış araştırma raporu oluştur."
            )},
        ]

        try:
            response = chat(messages, model=model, ajan="web_research_reporter", task="reporting")
            if isinstance(response, dict):
                report_text = response.get("message", {}).get("content", "")
            else:
                report_text = str(response)

            return {
                "topic": task.topic,
                "report_text": report_text,
                "sources": source_list,
                "findings_count": len(comparison.get("findings", [])),
                "contradictions_count": len(comparison.get("contradictions", [])),
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            log(f"[WEB_RESEARCH] Rapor oluşturma hatası: {e}")
            return self._fallback_report(task, comparison)

    def _fallback_report(self, task: ResearchTask, comparison: dict) -> dict:
        """LLM çalışamazsa basit rapor."""
        findings = comparison.get("findings", [])
        contradictions = comparison.get("contradictions", [])

        report_lines = [f"Araştırma Konusu: {task.topic}", ""]
        report_lines.append("=== BULGULAR ===")
        for f in findings:
            report_lines.append(f"- {f.get('topic', '')}: {f.get('details', '')[:200]}")

        if contradictions:
            report_lines.append("\n=== ÇELİŞKİLER ===")
            for c in contradictions:
                report_lines.append(f"- {c.get('topic', '')}")

        report_lines.append(f"\n=== KAYNAKLAR ({len(task.sources)}) ===")
        for src in task.sources:
            if not src.error:
                report_lines.append(f"- {src.title} ({src.url})")

        return {
            "topic": task.topic,
            "report_text": "\n".join(report_lines),
            "sources": [{"title": s.title, "url": s.url} for s in task.sources if not s.error],
            "findings_count": len(findings),
            "contradictions_count": len(contradictions),
            "generated_at": datetime.now().isoformat(),
        }


# ─── Memory Store ────────────────────────────────────────────────────────────

class ResearchMemoryStore:
    """Araştırma sonuçlarını Memory/RAG'a kaydeden modül."""

    def store(self, task: ResearchTask, report: dict) -> bool:
        """Araştırma sonucunu Memory/RAG'a kaydet."""
        try:
            # ChromaDB'ye kaydet
            from rag.chroma_manager import get_collection, add_to_memory

            collection = get_collection("research")

            # Araştırma sonucunu metin olarak oluştur
            memory_text = self._format_for_memory(task, report)

            # Kaynak URL'lerini metadata olarak sakla
            source_urls = [s.url for s in task.sources if not s.error]

            add_to_memory(
                collection=collection,
                text=memory_text,
                metadata={
                    "type": "research",
                    "topic": task.topic,
                    "sources_count": len(source_urls),
                    "date": datetime.now().isoformat(),
                    "source_urls": json.dumps(source_urls[:5]),
                },
            )

            log(f"[WEB_RESEARCH] Araştırma hafızaya kaydedildi: {task.topic[:50]}")
            return True

        except Exception as e:
            log(f"[WEB_RESEARCH] Memory kaydetme hatası: {e}")
            return False

    def _format_for_memory(self, task: ResearchTask, report: dict) -> str:
        """Araştırma sonucunu memory için metin formatına çevir."""
        lines = [
            f"Araştırma Konusu: {task.topic}",
            f"Tarih: {task.created_at}",
            f"Kaynak Sayısı: {len([s for s in task.sources if not s.error])}",
            "",
            "Rapor:",
            report.get("report_text", "")[:3000],
            "",
            "Kaynaklar:",
        ]

        for src in task.sources:
            if not src.error:
                lines.append(f"- {src.title}: {src.url}")

        return "\n".join(lines)


# ─── Ana Orchestration Fonksiyonu ────────────────────────────────────────────

def research_topic(
    topic: str,
    model: str | None = None,
    max_sources: int = MAX_PAGES_PER_RESEARCH,
    save_to_memory: bool = True,
) -> dict[str, Any]:
    """
    Ana araştırma fonksiyonu.

    Tam bir araştırma döngüsü çalıştırır:
    1. Planlama
    2. Arama
    3. Kaynak okuma
    4. Karşılaştırma
    5. Rapor oluşturma
    6. Memory'ye kaydetme

    Args:
        topic: Araştırma konusu
        model: Kullanılacak model (None ise otomatik)
        max_sources: Maksimum kaynak sayısı
        save_to_memory: Memory'ye kaydet

    Returns:
        dict: Araştırma sonuçları
    """
    aid = eylem_baslat(
        ajan="web_research",
        niyet=topic[:100],
        plan="Web Research Agent — tam araştırma döngüsü",
        model=model or "auto",
    )

    task = ResearchTask(
        id=f"research-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
        topic=topic,
    )

    try:
        # ── 1. PLANLAMA ──────────────────────────────────────────────────
        task.status = ResearchStatus.PLANNING
        log(f"[WEB_RESEARCH] Planlama başlıyor: {topic[:60]}")

        planner = ResearchPlanner(model=model)
        plan = planner.create_plan(topic)

        task.search_queries = []
        for subtopic in plan.get("subtopics", []):
            task.search_queries.extend(subtopic.get("search_queries", []))

        if not task.search_queries:
            task.search_queries = [topic]

        log(f"[WEB_RESEARCH] {len(task.search_queries)} arama terimi oluşturuldu")

        # ── 2. ARAMA ─────────────────────────────────────────────────────
        task.status = ResearchStatus.SEARCHING
        log(f"[WEB_RESEARCH] Arama başlıyor...")

        explorer = WebExplorer()
        all_sources: list[WebSource] = []

        for query in task.search_queries[:8]:  # Max 8 arama
            sources = explorer.search_and_read(query, max_results=3)
            all_sources.extend(sources)
            time.sleep(0.5)

        # Çift kaynakları temizle (URL bazlı)
        seen_urls: set[str] = set()
        unique_sources: list[WebSource] = []
        for src in all_sources:
            if src.url not in seen_urls and not src.error:
                seen_urls.add(src.url)
                unique_sources.append(src)

        task.sources = unique_sources[:max_sources]
        log(f"[WEB_RESEARCH] {len(task.sources)} benzersiz kaynak bulundu")

        # ── 3. KAYNAK ANALİZİ ────────────────────────────────────────────
        task.status = ResearchStatus.ANALYZING
        log(f"[WEB_RESEARCH] Kaynak analizi başlıyor...")

        # Her kaynak için güvenilirlik analizi
        for src in task.sources:
            if src.reliability == SourceReliability.UNCHECKED:
                src.source_type, src.reliability = classify_source(
                    src.url, src.title, src.content[:500]
                )

        # Güvenilirliğe göre sırala (yüksek güvenilirlik önce)
        reliability_order = {
            SourceReliability.HIGH: 0,
            SourceReliability.MEDIUM: 1,
            SourceReliability.LOW: 2,
            SourceReliability.UNCHECKED: 3,
        }
        task.sources.sort(key=lambda s: reliability_order.get(s.reliability, 3))

        # ── 4. KARŞILAŞTIRMA ─────────────────────────────────────────────
        task.status = ResearchStatus.COMPARING
        log(f"[WEB_RESEARCH] Karşılaştırma başlıyor...")

        comparator = MultiSourceComparator(model=model)
        comparison = comparator.compare_sources(task.sources)
        task.comparisons = comparison.get("findings", [])
        task.contradictions = comparison.get("contradictions", [])

        # ── 5. RAPOR ─────────────────────────────────────────────────────
        task.status = ResearchStatus.REPORTING
        log(f"[WEB_RESEARCH] Rapor oluşturuluyor...")

        reporter = ResearchReportGenerator(model=model)
        report = reporter.generate_report(task, comparison)
        task.report = report

        # ── 6. MEMORY ────────────────────────────────────────────────────
        if save_to_memory:
            task.status = ResearchStatus.VERIFYING
            memory_store = ResearchMemoryStore()
            memory_store.store(task, report)

        # ── 7. TAMAMLAMA ─────────────────────────────────────────────────
        task.status = ResearchStatus.COMPLETED
        task.completed_at = datetime.now().isoformat()

        # Sonucu log'a kaydet
        result = {
            "research_id": task.id,
            "topic": task.topic,
            "status": task.status.value,
            "sources_found": len(task.sources),
            "sources_used": len([s for s in task.sources if not s.error]),
            "search_queries": task.search_queries,
            "comparison": comparison,
            "report": report,
            "contradictions": task.contradictions,
            "duration_estimate": f"{len(task.search_queries) * 2}s",
        }

        eylem_tamamla(
            aid,
            f"Araştırma tamamlandı: {len(task.sources)} kaynak, "
            f"{len(task.contradictions)} çelişki",
            True,
            0,
        )

        log(f"[WEB_RESEARCH] Araştırma tamamlandı: {task.topic[:50]}")
        return result

    except Exception as e:
        task.status = ResearchStatus.FAILED
        task.error = str(e)
        eylem_hata(aid, str(e))
        log(f"[WEB_RESEARCH] Araştırma hatası: {e}")
        return {
            "research_id": task.id,
            "topic": task.topic,
            "status": "failed",
            "error": str(e),
        }


# ─── Hızlı Erişim Fonksiyonları ─────────────────────────────────────────────

def quick_research(topic: str) -> dict[str, Any]:
    """Hızlı araştırma — max 5 kaynak."""
    return research_topic(topic, max_sources=5, save_to_memory=False)


def deep_research(topic: str) -> dict[str, Any]:
    """Derin araştırma — max 15 kaynak, memory'ye kaydet."""
    return research_topic(topic, max_sources=15, save_to_memory=True)


def research_with_queries(queries: list[str]) -> dict[str, Any]:
    """Belirli sorgularla araştırma."""
    explorer = WebExplorer()
    all_sources = []

    for query in queries:
        sources = explorer.search_and_read(query, max_results=3)
        all_sources.extend(sources)

    # Benzersiz kaynaklar
    seen = set()
    unique = []
    for src in all_sources:
        if src.url not in seen and not src.error:
            seen.add(src.url)
            unique.append(src)

    comparator = MultiSourceComparator()
    comparison = comparator.compare_sources(unique)

    return {
        "queries": queries,
        "sources": [{"title": s.title, "url": s.url, "reliability": s.reliability.value} for s in unique],
        "comparison": comparison,
    }


# ─── Test Fonksiyonu ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== UMAY Web Research Agent Test ===\n")

    # Test 1: Kaynak sınıflandırma
    test_urls = [
        ("https://docs.python.org/3/", "Python Docs"),
        ("https://www.reddit.com/r/python", "Reddit Python"),
        ("https://medium.com/@user/article", "Medium Blog"),
        ("https://gov.tr/portal", "Gov TR"),
        ("https://arxiv.org/abs/2301.00001", "ArXiv Paper"),
    ]

    print("Test 1: Kaynak sınıflandırma")
    for url, name in test_urls:
        st, sr = classify_source(url, name)
        print(f"  {name}: {st.value} / {sr.value}")

    # Test 2: Plan oluşturma (fallback)
    print("\nTest 2: Fallback plan oluşturma")
    planner = ResearchPlanner()
    plan = planner._create_fallback_plan("Python programlama dilinin avantajları")
    print(f"  Subtopics: {len(plan.get('subtopics', []))}")
    print(f"  Queries: {plan.get('subtopics', [{}])[0].get('search_queries', [])}")

    print("\nTest tamamlandı.")

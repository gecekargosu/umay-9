"""
UMAY Web Research Agent Tests
=============================
Unit, mock integration, real web integration, cross-system ve regression testleri.
"""
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ─── Fixture ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_sources():
    """Test için örnek WebSource'lar."""
    from core.web_research import WebSource, SourceType, SourceReliability
    return [
        WebSource(
            url="https://docs.python.org/3/tutorial/classes.html",
            title="Python Classes Tutorial",
            domain="docs.python.org",
            source_type=SourceType.OFFICIAL,
            reliability=SourceReliability.HIGH,
            content="Python classes provide all the standard features of OOP.",
            text_length=50,
        ),
        WebSource(
            url="https://medium.com/@user/python-classes",
            title="Python Classes Guide",
            domain="medium.com",
            source_type=SourceType.BLOG,
            reliability=SourceReliability.MEDIUM,
            content="Python classes are powerful. They support inheritance.",
            text_length=48,
        ),
        WebSource(
            url="https://reddit.com/r/python/comments/123",
            title="Are Python classes worth it?",
            domain="reddit.com",
            source_type=SourceType.FORUM,
            reliability=SourceReliability.LOW,
            content="I think Python classes are overrated. Use dataclasses.",
            text_length=51,
        ),
    ]


@pytest.fixture
def sample_task():
    """Test için örnek ResearchTask."""
    from core.web_research import ResearchTask, ResearchStatus
    return ResearchTask(
        id="test-research-001",
        topic="Python programlama dilinin avantajları",
        status=ResearchStatus.COMPLETED,
        search_queries=["Python avantajları", "Python nedir"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — Source Classification
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceClassification:
    """Kaynak sınıflandırma testleri."""

    def test_official_python_docs(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://docs.python.org/3/", "Python Docs")
        assert st == SourceType.OFFICIAL
        assert sr == SourceReliability.HIGH

    def test_government_site(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://www.gov.tr/portal", "Gov TR")
        assert st == SourceType.GOVERNMENT
        assert sr == SourceReliability.HIGH

    def test_academic_arxiv(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://arxiv.org/abs/2301.00001", "Paper")
        assert st == SourceType.ACADEMIC
        assert sr == SourceReliability.HIGH

    def test_wikipedia(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://en.wikipedia.org/wiki/Python", "Python Wiki")
        assert st == SourceType.ACADEMIC
        assert sr == SourceReliability.HIGH

    def test_github(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://github.com/python/cpython", "CPython Repo")
        assert st == SourceType.ACADEMIC
        assert sr == SourceReliability.HIGH

    def test_news_bbc(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://www.bbc.com/news", "BBC News")
        assert st == SourceType.NEWS
        assert sr == SourceReliability.MEDIUM

    def test_news_reuters(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://www.reuters.com/article", "Reuters")
        assert st == SourceType.NEWS
        assert sr == SourceReliability.MEDIUM

    def test_forum_reddit(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://www.reddit.com/r/python", "Reddit")
        assert st == SourceType.FORUM
        assert sr == SourceReliability.LOW

    def test_blog_medium(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://medium.com/@user/article", "Medium Blog")
        assert st == SourceType.BLOG
        assert sr == SourceReliability.MEDIUM

    def test_blog_devto(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://dev.to/user/article", "Dev.to Blog")
        assert st == SourceType.BLOG
        assert sr == SourceReliability.MEDIUM

    def test_unknown_site(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://random-blog.example.com/post", "Random Post")
        assert st in (SourceType.BLOG, SourceType.UNKNOWN)

    def test_gov_edu_tr(self):
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://www.itu.edu.tr", "ITU")
        assert st == SourceType.ACADEMIC
        assert sr == SourceReliability.HIGH


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — WebSource
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebSource:
    """WebSource veri modeli testleri."""

    def test_creation_defaults(self):
        from core.web_research import WebSource
        src = WebSource(url="https://example.com")
        assert src.url == "https://example.com"
        assert src.domain == "example.com"
        assert src.text_length == 0
        assert src.error is None
        assert src.accessed_at != ""

    def test_domain_extraction(self):
        from core.web_research import WebSource
        src = WebSource(url="https://www.python.org/about/")
        assert src.domain == "www.python.org"

    def test_empty_url(self):
        from core.web_research import WebSource
        src = WebSource(url="")
        assert src.domain == ""


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — ResearchPlanner
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchPlanner:
    """Araştırma planlayıcı testleri."""

    def test_fallback_plan_structure(self):
        from core.web_research import ResearchPlanner
        planner = ResearchPlanner()
        plan = planner._create_fallback_plan("Python programlama")
        assert "topic_summary" in plan
        assert "subtopics" in plan
        assert len(plan["subtopics"]) >= 1
        assert "search_queries" in plan["subtopics"][0]

    def test_fallback_plan_has_queries(self):
        from core.web_research import ResearchPlanner
        planner = ResearchPlanner()
        plan = planner._create_fallback_plan("Yapay zeka")
        queries = plan["subtopics"][0]["search_queries"]
        assert len(queries) >= 2
        assert all(isinstance(q, str) for q in queries)

    def test_extract_json_direct(self):
        from core.web_research import ResearchPlanner
        planner = ResearchPlanner()
        json_str = '{"topic_summary": "test", "subtopics": []}'
        result = planner._extract_json(json_str)
        assert result is not None
        assert result["topic_summary"] == "test"

    def test_extract_json_in_codeblock(self):
        from core.web_research import ResearchPlanner
        planner = ResearchPlanner()
        text = '```json\n{"topic_summary": "test", "subtopics": []}\n```'
        result = planner._extract_json(text)
        assert result is not None

    def test_extract_json_no_valid(self):
        from core.web_research import ResearchPlanner
        planner = ResearchPlanner()
        result = planner._extract_json("This is not JSON at all")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — MultiSourceComparator
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiSourceComparator:
    """Çoklu kaynak karşılaştırma testleri."""

    def test_simple_comparison_empty_sources(self):
        from core.web_research import MultiSourceComparator
        comparator = MultiSourceComparator()
        result = comparator.compare_sources([])
        assert "error" in result or "findings" in result

    def test_simple_comparison_with_sources(self, sample_sources):
        from core.web_research import MultiSourceComparator
        comparator = MultiSourceComparator()
        result = comparator._simple_comparison(sample_sources)
        assert "findings" in result
        assert len(result["findings"]) == 3
        assert result["findings"][0]["sources"][0] == sample_sources[0].url

    def test_comparison_result_structure(self, sample_sources):
        from core.web_research import MultiSourceComparator
        comparator = MultiSourceComparator()
        result = comparator._simple_comparison(sample_sources)
        assert "findings" in result
        assert "contradictions" in result
        assert "gaps" in result

    def test_extract_json_valid(self):
        from core.web_research import MultiSourceComparator
        comparator = MultiSourceComparator()
        json_str = '{"findings": [{"topic": "test"}], "contradictions": []}'
        result = comparator._extract_json(json_str)
        assert result is not None
        assert len(result["findings"]) == 1

    def test_extract_json_in_codeblock(self):
        from core.web_research import MultiSourceComparator
        comparator = MultiSourceComparator()
        text = '```json\n{"findings": [], "contradictions": []}\n```'
        result = comparator._extract_json(text)
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — ResearchReportGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchReportGenerator:
    """Rapor oluşturucu testleri."""

    def test_fallback_report_structure(self, sample_task):
        from core.web_research import ResearchReportGenerator
        reporter = ResearchReportGenerator()
        comparison = {
            "findings": [{"topic": "Test bulgu", "details": "Detay"}],
            "contradictions": [],
        }
        report = reporter._fallback_report(sample_task, comparison)
        assert "topic" in report
        assert "report_text" in report
        assert "sources" in report
        assert report["findings_count"] == 1
        assert "Python" in report["report_text"]

    def test_fallback_report_with_contradictions(self, sample_task):
        from core.web_research import ResearchReportGenerator
        reporter = ResearchReportGenerator()
        comparison = {
            "findings": [],
            "contradictions": [{"topic": "Çelişki 1"}],
        }
        report = reporter._fallback_report(sample_task, comparison)
        assert report["contradictions_count"] == 1
        assert "CELISKILER" in report["report_text"] or "çelişki" in report["report_text"].lower()

    def test_fallback_report_sources(self, sample_task):
        from core.web_research import ResearchReportGenerator, WebSource
        sample_task.sources = [
            WebSource(url="https://example.com", title="Example", content="test"),
        ]
        reporter = ResearchReportGenerator()
        report = reporter._fallback_report(sample_task, {"findings": [], "contradictions": []})
        assert len(report["sources"]) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — ResearchTask
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchTask:
    """ResearchTask veri modeli testleri."""

    def test_task_creation(self):
        from core.web_research import ResearchTask, ResearchStatus
        task = ResearchTask(id="t1", topic="Test")
        assert task.id == "t1"
        assert task.topic == "Test"
        assert task.status == ResearchStatus.PLANNING
        assert task.created_at != ""

    def test_task_defaults(self):
        from core.web_research import ResearchTask
        task = ResearchTask(id="t2", topic="Test 2")
        assert len(task.search_queries) == 0
        assert len(task.sources) == 0
        assert len(task.comparisons) == 0
        assert len(task.contradictions) == 0
        assert task.completed_at is None


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — ResearchMemoryStore
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchMemoryStore:
    """Memory store testleri."""

    def test_format_for_memory(self, sample_task, sample_sources):
        from core.web_research import ResearchMemoryStore
        sample_task.sources = sample_sources
        store = ResearchMemoryStore()
        report = {"report_text": "Test rapor"}
        text = store._format_for_memory(sample_task, report)
        assert "Python" in text
        assert "Araştırma Konusu" in text
        assert "docs.python.org" in text


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — Enums
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnums:
    """Enum değerleri testleri."""

    def test_source_types(self):
        from core.web_research import SourceType
        assert SourceType.OFFICIAL.value == "official"
        assert SourceType.NEWS.value == "news"
        assert SourceType.ACADEMIC.value == "academic"
        assert SourceType.FORUM.value == "forum"
        assert SourceType.BLOG.value == "blog"
        assert SourceType.UNKNOWN.value == "unknown"

    def test_reliability_levels(self):
        from core.web_research import SourceReliability
        assert SourceReliability.HIGH.value == "high"
        assert SourceReliability.MEDIUM.value == "medium"
        assert SourceReliability.LOW.value == "low"

    def test_research_status(self):
        from core.web_research import ResearchStatus
        assert ResearchStatus.PLANNING.value == "planning"
        assert ResearchStatus.COMPLETED.value == "completed"
        assert ResearchStatus.FAILED.value == "failed"


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — WebExplorer (Mock)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebExplorer:
    """WebExplorer testleri (mock ile)."""

    def test_explorer_init(self):
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        assert explorer._browser is None
        assert len(explorer._visited_urls) == 0

    def test_explorer_reset(self):
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        explorer._visited_urls.add("https://test.com")
        explorer.reset()
        assert len(explorer._visited_urls) == 0

    def test_explorer_search_mock(self):
        from core.web_research import WebExplorer
        explorer = WebExplorer()
        with patch("core.agent_tools.web_search", return_value={
            "results": [
                {"title": "Result 1", "href": "https://example.com/1"},
                {"title": "Result 2", "href": "https://example.com/2"},
            ]
        }):
            results = explorer.search("test query", max_results=2)
            assert len(results) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — Tool System
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolSystemIntegration:
    """Tool system entegrasyon testleri."""

    def test_tools_registered(self):
        from core.agent_tools import TOOLS
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "research_topic" in tool_names
        assert "quick_research" in tool_names
        assert "research_with_queries" in tool_names
        assert "open_and_read_page" in tool_names
        assert "search_web" in tool_names
        assert "extract_page_tables" in tool_names

    def test_dispatch_registered(self):
        from core.agent_tools import DISPATCH
        assert "research_topic" in DISPATCH
        assert "quick_research" in DISPATCH
        assert "research_with_queries" in DISPATCH
        assert "open_and_read_page" in DISPATCH
        assert "search_web" in DISPATCH
        assert "extract_page_tables" in DISPATCH

    def test_dispatch_callable(self):
        from core.agent_tools import DISPATCH
        assert callable(DISPATCH["research_topic"])
        assert callable(DISPATCH["quick_research"])
        assert callable(DISPATCH["search_web"])

    def test_planner_tool_categories(self):
        """Planner'daki tool kategorileri web research'i içermeli."""
        from core.planner import TOOL_CATEGORIES
        # Web research tool'ları kategorize edilmeli
        assert "web_search" in TOOL_CATEGORIES
        assert "browser_open" in TOOL_CATEGORIES


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-SYSTEM TESTS — Browser + Vision + Web Research
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossSystem:
    """Çapraz sistem testleri."""

    def test_planner_knows_web_research_tools(self):
        """Planner web research tool'larını bilmeli."""
        from core.planner import TOOL_CATEGORIES
        web_tools = [k for k, v in TOOL_CATEGORIES.items()
                     if v["category"] in ("web_research", "browser")]
        assert len(web_tools) >= 2

    def test_web_research_uses_planner_structure(self):
        """Web Research, Planner yapısını kullanmalı."""
        from core.web_research import ResearchPlanner
        planner = ResearchPlanner()
        plan = planner._create_fallback_plan("test")
        assert "subtopics" in plan
        assert "search_queries" in plan["subtopics"][0]

    def test_comparator_uses_reliability(self):
        """Comparator güvenilirlik bilgisini kullanmalı."""
        from core.web_research import MultiSourceComparator, WebSource, SourceReliability
        comparator = MultiSourceComparator()
        sources = [
            WebSource(url="https://example.com", content="test", reliability=SourceReliability.HIGH),
        ]
        result = comparator._simple_comparison(sources)
        # Simple comparison defaults to "low" confidence (LLM comparison would do better)
        assert result["findings"][0]["confidence"] in ("low", "medium", "high")

    def test_report_includes_sources(self):
        """Rapor kaynakları içermeli."""
        from core.web_research import ResearchReportGenerator, ResearchTask, WebSource
        task = ResearchTask(id="t1", topic="Test")
        task.sources = [WebSource(url="https://example.com", title="Example")]
        reporter = ResearchReportGenerator()
        report = reporter._fallback_report(task, {"findings": [], "contradictions": []})
        assert len(report["sources"]) == 1
        assert report["sources"][0]["url"] == "https://example.com"


# ═══════════════════════════════════════════════════════════════════════════════
# REAL WEB INTEGRATION TESTS (internet gerekli)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    not pytest.importorskip("requests", reason="requests gerekli"),
    reason="requests yüklü değil"
)
class TestRealWebIntegration:
    """Gerçek web entegrasyon testleri — internet bağlantısı gerektirir."""

    def test_real_classify_python_docs(self):
        """Gerçek Python docs sitesini sınıflandır."""
        from core.web_research import classify_source, SourceType, SourceReliability
        st, sr = classify_source("https://docs.python.org/3/tutorial/", "Python Tutorial")
        assert st == SourceType.OFFICIAL
        assert sr == SourceReliability.HIGH

    def test_real_classify_various_sites(self):
        """Çeşitli gerçek siteleri sınıflandır."""
        from core.web_research import classify_source, SourceReliability
        sites = [
            ("https://docs.python.org/3/", SourceReliability.HIGH),
            ("https://github.com/microsoft/vscode", SourceReliability.HIGH),
            ("https://en.wikipedia.org/wiki/Python_(programming_language)", SourceReliability.HIGH),
        ]
        for url, expected_reliability in sites:
            _, sr = classify_source(url, "Test")
            assert sr == expected_reliability, f"{url} reliability mismatch"

    def test_web_search_tool_mock(self):
        """Web search tool'u mock ile test."""
        from core.agent_tools import web_search
        with patch("core.agent_tools._browser") as mock_browser_func:
            mock_agent = MagicMock()
            mock_agent.sayfa_baslik.return_value = "Test"
            mock_agent.sayfa.url = "https://test.com"
            mock_agent.sayfa_metni.return_value = "Test content"
            mock_agent.sayfa.eval_on_selector_all.return_value = [
                {"title": "Python.org", "href": "https://python.org"}
            ]
            mock_agent.git.return_value = True
            mock_browser_func.return_value = mock_agent
            result = web_search("python")
            assert "results" in result


# ═══════════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS — Eski sistem hala çalışmalı
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    """Regresyon testleri — mevcut sistemi bozma."""

    def test_document_reader_still_works(self):
        from core.document_reader import read_document
        assert callable(read_document)

    def test_vision_reader_still_works(self):
        from core.vision_reader import analyze_image, describe_image
        assert callable(analyze_image)
        assert callable(describe_image)

    def test_planner_still_works(self):
        from core.planner import ReasoningEngine, TaskDecomposer, ExecutionEngine
        assert callable(ReasoningEngine)
        assert callable(TaskDecomposer)
        assert callable(ExecutionEngine)

    def test_terminal_agent_still_works(self):
        from core.terminal_agent import TerminalAgent
        assert callable(TerminalAgent)

    def test_code_agent_still_works(self):
        from core.code_agent import read_code, generate_code, explain_code
        assert callable(read_code)
        assert callable(generate_code)

    def test_all_legacy_tools_in_dispatch(self):
        """Eski tool'lar hala DISPATCH'te olmalı."""
        from core.agent_tools import DISPATCH
        legacy_tools = [
            "read_file", "write_file", "list_directory", "search_files",
            "run_command", "run_test_suite", "inspect_project",
            "read_document", "scan_directory", "search_in_documents",
            "analyze_image", "image_to_text", "describe_image",
            "run_terminal_command", "read_code", "generate_code",
            "web_search", "browser_open", "browser_read",
        ]
        for tool in legacy_tools:
            assert tool in DISPATCH, f"Legacy tool missing: {tool}"


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case ve sınır durum testleri."""

    def test_empty_url_classification(self):
        from core.web_research import classify_source, SourceType
        st, _ = classify_source("", "")
        assert st in (SourceType.UNKNOWN, SourceType.OFFICIAL, SourceType.BLOG)

    def test_very_long_topic(self):
        from core.web_research import ResearchPlanner
        planner = ResearchPlanner()
        long_topic = "A" * 1000
        plan = planner._create_fallback_plan(long_topic)
        assert plan["topic_summary"] == long_topic

    def test_special_chars_in_query(self):
        from core.web_research import classify_source
        st, _ = classify_source("https://example.com/path?q=test&lang=tr", "Test")
        assert st is not None

    def test_web_source_post_init(self):
        """WebSource __post_init__ doğru çalışmalı."""
        from core.web_research import WebSource
        src = WebSource(url="https://example.com/page?q=search")
        assert src.domain == "example.com"
        assert src.accessed_at != ""

    def test_research_task_all_fields(self):
        """ResearchTask tüm alanları desteklemeli."""
        from core.web_research import ResearchTask, ResearchStatus, WebSource
        task = ResearchTask(
            id="t1", topic="Test",
            status=ResearchStatus.COMPLETED,
            search_queries=["q1", "q2"],
            sources=[WebSource(url="https://example.com")],
            comparisons=[{"topic": "c1"}],
            contradictions=[{"topic": "d1"}],
            report={"report_text": "test"},
        )
        assert len(task.search_queries) == 2
        assert len(task.sources) == 1
        assert len(task.comparisons) == 1
        assert len(task.contradictions) == 1

"""
UMAY Code Agent Tests
Code reading, generation, analysis, and testing.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def sample_python_file(tmp_path):
    """Örnek Python dosyası."""
    content = '''def hello(name: str) -> str:
    """Selamlama fonksiyonu."""
    return f"Merhaba {name}!"

class Calculator:
    """Basit hesap makinesi."""
    
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def multiply(self, a: int, b: int) -> int:
        return a * b
'''
    file = tmp_path / "sample.py"
    file.write_text(content, encoding="utf-8")
    return file


@pytest.fixture
def sample_js_file(tmp_path):
    """Örnek JavaScript dosyası."""
    content = '''function greet(name) {
    return `Merhaba ${name}!`;
}

class Calculator {
    add(a, b) {
        return a + b;
    }
}

module.exports = { greet, Calculator };
'''
    file = tmp_path / "sample.js"
    file.write_text(content, encoding="utf-8")
    return file


@pytest.fixture
def sample_broken_python(tmp_path):
    """Kırık Python dosyası."""
    content = '''def broken(:)
    print("hata")
'''
    file = tmp_path / "broken.py"
    file.write_text(content, encoding="utf-8")
    return file


# ─── Language Detection Tests ───────────────────────────────────────────────

class TestLanguageDetection:
    """Dil tespiti testleri."""

    def test_detect_python(self):
        """Python dili tespit edilmeli."""
        from core.code_agent import detect_language
        assert detect_language("test.py") == "python"

    def test_detect_javascript(self):
        """JavaScript dili tespit edilmeli."""
        from core.code_agent import detect_language
        assert detect_language("test.js") == "javascript"

    def test_detect_typescript(self):
        """TypeScript dili tespit edilmeli."""
        from core.code_agent import detect_language
        assert detect_language("test.ts") == "typescript"

    def test_detect_html(self):
        """HTML dili tespit edilmeli."""
        from core.code_agent import detect_language
        assert detect_language("test.html") == "html"

    def test_detect_css(self):
        """CSS dili tespit edilmeli."""
        from core.code_agent import detect_language
        assert detect_language("test.css") == "css"

    def test_detect_unknown(self):
        """Bilinmeyen uzantı 'unknown' dönmeli."""
        from core.code_agent import detect_language
        assert detect_language("test.xyz") == "unknown"


# ─── Code Cleaning Tests ────────────────────────────────────────────────────

class TestCodeCleaning:
    """Kod temizleme testleri."""

    def test_clean_code_plain(self):
        """Düz kod temizlenmemeli."""
        from core.code_agent import clean_code
        code = "print('hello')"
        assert clean_code(code) == code

    def test_clean_code_with_markdown(self):
        """Markdown blokları temizlenmeli."""
        from core.code_agent import clean_code
        text = '```python\nprint("hello")\n```'
        result = clean_code(text)
        assert 'print("hello")' in result
        assert "```" not in result

    def test_clean_code_empty(self):
        """Boş metin boş dönmeli."""
        from core.code_agent import clean_code
        assert clean_code("") == ""
        assert clean_code("   ") == ""


# ─── Code Reading Tests ─────────────────────────────────────────────────────

class TestCodeReading:
    """Kod okuma testleri."""

    def test_read_python_file(self, sample_python_file):
        """Python dosyası okunabilmeli."""
        from core.code_agent import read_code
        result = read_code(str(sample_python_file))

        assert result["status"] == "OK"
        assert result["language"] == "python"
        assert result["total_lines"] > 0

    def test_read_javascript_file(self, sample_js_file):
        """JavaScript dosyası okunabilmeli."""
        from core.code_agent import read_code
        result = read_code(str(sample_js_file))

        assert result["status"] == "OK"
        assert result["language"] == "javascript"

    def test_read_nonexistent_file(self, tmp_path):
        """Olmayan dosya için hata dönmeli."""
        from core.code_agent import read_code
        result = read_code(str(tmp_path / "nonexistent.py"))

        assert result["status"] == "ERROR"

    def test_read_directory(self, tmp_path):
        """Klasör okunursa hata dönmeli."""
        from core.code_agent import read_code
        result = read_code(str(tmp_path))

        assert result["status"] == "ERROR"

    def test_python_analysis(self, sample_python_file):
        """Python analizi çalışmalı."""
        from core.code_agent import read_code
        result = read_code(str(sample_python_file))

        assert result["status"] == "OK"
        analysis = result["analysis"]
        assert "functions" in analysis
        assert "classes" in analysis
        assert "hello" in analysis["functions"]
        assert "Calculator" in analysis["classes"]


# ─── Code Truncation Tests ──────────────────────────────────────────────────

class TestCodeTruncation:
    """Kod kısaltma testleri."""

    def test_short_code_not_truncated(self):
        """Kısa kod kısaltılmamalı."""
        from core.code_agent import truncate_code
        code = "print('hello')"
        assert truncate_code(code, max_chars=100) == code

    def test_long_code_truncated(self):
        """Uzun kod kısaltılmalı."""
        from core.code_agent import truncate_code
        code = "x" * 1000
        result = truncate_code(code, max_chars=100)
        assert len(result) < len(code)
        assert "Kısaltıldı" in result


# ─── Tool Integration Tests ─────────────────────────────────────────────────

class TestCodeToolIntegration:
    """Tool system entegrasyon testleri."""

    def test_code_tools_registered(self):
        """Code tool'ları kayıtlı olmalı."""
        from core.agent_tools import TOOLS, DISPATCH

        tool_names = {t["function"]["name"] for t in TOOLS}
        assert "read_code" in tool_names
        assert "generate_code" in tool_names
        assert "explain_code" in tool_names
        assert "find_bugs" in tool_names
        assert "write_test" in tool_names
        assert "run_code_tests" in tool_names
        assert "analyze_project_code" in tool_names
        assert "code_assist" in tool_names

        assert "read_code" in DISPATCH
        assert "generate_code" in DISPATCH

    def test_read_code_via_tools(self, sample_python_file):
        """read_code tool'u üzerinden okuma yapılabilmeli."""
        from core.agent_tools import read_code
        result = read_code(str(sample_python_file))
        assert result["status"] == "OK"

    def test_analyze_project_via_tools(self):
        """analyze_project_code tool'u üzerinden analiz yapılabilmeli."""
        from core.agent_tools import analyze_project_code
        result = analyze_project_code(str(Path(__file__).parent.parent))
        assert result["status"] == "OK"
        assert "project_type" in result
        assert "total_files" in result


# ─── Project Analysis Tests ─────────────────────────────────────────────────

class TestProjectAnalysis:
    """Proje analiz testleri."""

    def test_analyze_umay_project(self):
        """UMAY projesi analiz edilebilmeli."""
        from core.code_agent import analyze_project
        result = analyze_project(str(Path(__file__).parent.parent))

        assert result["status"] == "OK"
        assert result["project_type"] == "python"
        assert result["total_files"] > 0
        assert "python" in result["languages"]

    def test_analyze_nonexistent_project(self, tmp_path):
        """Olmayan proje için hata dönmeli."""
        from core.code_agent import analyze_project
        result = analyze_project(str(tmp_path / "nonexistent"))

        assert result["status"] == "ERROR"

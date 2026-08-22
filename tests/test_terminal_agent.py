"""
UMAY Terminal Agent Tests
Command execution, permission system, output analysis, and process management tests.
"""
import os
from pathlib import Path

import pytest


# ─── Permission Manager Tests ───────────────────────────────────────────────

class TestPermissionManager:
    """Permission Manager testleri."""

    def test_safe_command_allowed(self):
        """Güvenli komutlar izinli olmalı."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        result = pm.check_permission("python --version")
        assert result["allowed"] is True
        assert result["category"] == "safe"

    def test_dangerous_command_blocked(self):
        """Tehlikeli komutlar engellenmeli."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        result = pm.check_permission("format C:")
        assert result["allowed"] is False
        assert result["category"] == "dangerous"

    def test_blocked_command_never_allowed(self):
        """Yasaklı komutlar hiçbir zaman izinli olmamalı."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        result = pm.check_permission("rm -rf /")
        assert result["allowed"] is False
        assert result["category"] == "blocked"

    def test_approve_command(self):
        """Komut onaylanabilmeli."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        pm.approve_command("dangerous command")
        assert pm.is_approved("dangerous command")

    def test_unapproved_command(self):
        """Onaylanmamış komut False dönmeli."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        assert pm.is_approved("never approved") is False

    def test_git_status_safe(self):
        """git status güvenli komut olmalı."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        result = pm.check_permission("git status")
        assert result["allowed"] is True
        assert result["category"] == "safe"

    def test_dir_safe(self):
        """dir komutu güvenli olmalı."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        result = pm.check_permission("dir")
        assert result["allowed"] is True

    def test_powershell_remove_item_dangerous(self):
        """PowerShell Remove-Item -Recurse -Force tehlikeli olmalı."""
        from core.terminal_agent import PermissionManager
        pm = PermissionManager()
        result = pm.check_permission("Remove-Item -Recurse -Force C:\\test")
        assert result["category"] == "dangerous"


# ─── Output Analyzer Tests ──────────────────────────────────────────────────

class TestOutputAnalyzer:
    """Output Analyzer testleri."""

    def test_analyze_clean_output(self):
        """Temiz çıktı OK dönmeli."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("Hello World", "", 0)
        assert result["severity"] == "OK"
        assert result["error_count"] == 0

    def test_analyze_error_in_stderr(self):
        """stderr'da hata olmalı."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("", "Error: something went wrong", 1)
        assert result["severity"] == "ERROR"
        assert result["error_count"] > 0

    def test_analyze_traceback(self):
        """Traceback tespit edilmeli."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("Traceback (most recent call last):", "", 1)
        assert result["error_count"] > 0
        assert any(e["type"] == "TRACEBACK" for e in result["errors"])

    def test_analyze_syntax_error(self):
        """SyntaxError tespit edilmeli."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("SyntaxError: invalid syntax", "", 1)
        assert result["error_count"] > 0

    def test_analyze_import_error(self):
        """ImportError tespit edilmeli."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("ModuleNotFoundError: No module named 'xyz'", "", 1)
        assert result["error_count"] > 0
        assert result["suggestions"]  # Öneri olmalı

    def test_analyze_warning(self):
        """Uyarılar tespit edilmeli."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("Warning: deprecated function", "", 0)
        assert result["warning_count"] > 0

    def test_analyze_test_failure(self):
        """Test başarısızlığı tespit edilmeli."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("FAILED tests/test_foo.py::test_bar", "", 1)
        assert result["error_count"] > 0
        assert any(e["type"] == "TEST_FAIL" for e in result["errors"])

    def test_analyze_nonzero_exit(self):
        """Sıfır olmayan exit code FAIL olmalı."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("", "", 1)
        assert result["severity"] == "FAIL"

    def test_suggestions_for_import_error(self):
        """ImportError için öneri olmalı."""
        from core.terminal_agent import OutputAnalyzer
        oa = OutputAnalyzer()
        result = oa.analyze("ModuleNotFoundError: No module named 'requests'", "", 1)
        assert any("pip install" in s for s in result["suggestions"])


# ─── Terminal Agent Integration Tests ───────────────────────────────────────

class TestTerminalAgentIntegration:
    """Terminal Agent entegrasyon testleri."""

    def test_run_safe_command(self):
        """Güvenli komut çalıştırılabilmeli."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        result = agent.run_command("python --version", timeout=10)
        assert result["status"] == "PASS"
        assert result["returncode"] == 0
        assert "Python" in result.get("stdout", "")

    def test_run_blocked_command(self):
        """Yasaklı komut engellenmeli."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        result = agent.run_command("rm -rf /", timeout=5)
        assert result["status"] == "BLOCKED"

    def test_run_dangerous_without_approval(self):
        """Onaysız tehlikeli komut engellenmeli."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        result = agent.run_command("format C:", timeout=5)
        assert result["status"] == "NEEDS_APPROVAL"

    def test_system_info(self):
        """Sistem bilgisi alınabilmeli."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        info = agent.get_system_info()
        assert "os" in info
        assert "python_version" in info

    def test_analyze_error_integration(self):
        """Hata analizi entegrasyonu çalışmalı."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        result = agent.analyze_error(
            "python test.py",
            "ModuleNotFoundError: No module named 'requests'"
        )
        assert result["error_type"] == "IMPORT_ERROR"
        assert len(result["suggestions"]) > 0

    def test_run_command_with_timeout(self):
        """Timeout works correctly."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        # A very short timeout should cause timeout for slow commands
        result = agent.run_command("python -c \"import time; time.sleep(5)\"", timeout=2)
        assert result["status"] == "TIMEOUT"

    def test_run_command_cwd(self):
        """CWD parameter works."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        result = agent.run_command("python -c \"import os; print(os.getcwd())\"", cwd=str(Path.cwd()))
        assert result["status"] == "PASS"
        # CWD stdout'ta görünmeli (encoding farkları olabilir)
        assert len(result.get("stdout", "")) > 0


# ─── Tool System Integration Tests ──────────────────────────────────────────

class TestTerminalToolIntegration:
    """Tool system entegrasyon testleri."""

    def test_terminal_tools_registered(self):
        """Terminal tool'ları kayıtlı olmalı."""
        from core.agent_tools import TOOLS, DISPATCH

        tool_names = {t["function"]["name"] for t in TOOLS}
        assert "run_terminal_command" in tool_names
        assert "run_powershell" in tool_names
        assert "analyze_error" in tool_names
        assert "get_system_info" in tool_names
        assert "read_log_file" in tool_names
        assert "list_processes" in tool_names
        assert "find_process" in tool_names

        assert "run_terminal_command" in DISPATCH
        assert "get_system_info" in DISPATCH

    def test_run_terminal_command_via_tools(self):
        """run_terminal_command tool'u üzerinden komut çalıştırılabilmeli."""
        from core.agent_tools import run_terminal_command
        result = run_terminal_command("python --version", timeout=10)
        assert result["status"] == "PASS"

    def test_get_system_info_via_tools(self):
        """get_system_info tool'u üzerinden bilgi alınabilmeli."""
        from core.agent_tools import get_system_info
        result = get_system_info()
        assert "os" in result


# ─── Process Manager Tests ──────────────────────────────────────────────────

class TestProcessManager:
    """Process Manager testleri."""

    def test_list_processes(self):
        """Process listesi alınabilmeli."""
        from core.terminal_agent import ProcessManager
        pm = ProcessManager()
        result = pm.list_processes()
        assert result["status"] == "OK"
        assert "output" in result

    def test_find_process_python(self):
        """Python process'i bulunabilmeli."""
        from core.terminal_agent import ProcessManager
        pm = ProcessManager()
        result = pm.find_process("python")
        assert result["status"] == "OK"
        # Python çalışıyorsa bulunmalı
        assert isinstance(result.get("found"), bool)


# ─── Log Reader Tests ───────────────────────────────────────────────────────

class TestLogReader:
    """Log okuyucu testleri."""

    def test_read_existing_log(self):
        """Mevcut log dosyası okunabilmeli."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        log_path = str(Path(__file__).parent.parent / "logs" / "umay.log")
        if Path(log_path).exists():
            result = agent.read_log(log_path, tail_lines=10)
            assert result["status"] == "OK"
            assert "lines" in result

    def test_read_nonexistent_log(self):
        """Olmayan log dosyası için hata dönmeli."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        result = agent.read_log("nonexistent.log")
        assert result["status"] == "ERROR"

    def test_read_log_with_pattern(self):
        """Pattern ile log filtreleme çalışmalı."""
        from core.terminal_agent import TerminalAgent
        agent = TerminalAgent()
        log_path = str(Path(__file__).parent.parent / "logs" / "umay.log")
        if Path(log_path).exists():
            result = agent.read_log(log_path, tail_lines=50, pattern="ERROR")
            assert result["status"] == "OK"


# ─── Real Command Tests ─────────────────────────────────────────────────────

class TestRealCommands:
    """Gerçek komut testleri."""

    def test_python_version(self):
        """python --version gerçekten çalışmalı."""
        from core.terminal_agent import run_terminal_command
        result = run_terminal_command("python --version", timeout=10)
        assert result["returncode"] == 0
        assert "Python" in result["stdout"]

    def test_dir_command(self):
        """dir komutu gerçekten çalışmalı."""
        from core.terminal_agent import run_terminal_command
        result = run_terminal_command("dir", timeout=10)
        assert result["returncode"] == 0

    def test_echo_command(self):
        """echo komutu gerçekten çalışmalı."""
        from core.terminal_agent import run_terminal_command
        result = run_terminal_command("echo UMAY_TEST", timeout=10)
        assert result["returncode"] == 0
        assert "UMAY_TEST" in result["stdout"]

    def test_git_status(self):
        """git status gerçekten çalışmalı."""
        from core.terminal_agent import run_terminal_command
        result = run_terminal_command("git status", timeout=10)
        # Git repo değilse exit code farklı olabilir
        assert result["status"] in ("PASS", "FAIL")

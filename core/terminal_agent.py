"""
UMAY Terminal Agent — Kontrollü Komut Çalıştırma ve Çıktı Analizi.

Bu modül UMAY'ın bilgisayarda kontrollü şekilde işlem yapmasını sağlar.

Özellikler:
- CMD / PowerShell komut çalıştırma
- Komut çıktısını okuma ve analiz etme
- Hata tespiti ve çözüm önerisi
- Permission sistemi (tehlikeli komutlar için onay)
- Process yönetimi
- Log okuma

%100 ÜCRETSIZ ve YEREL.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from core.utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata

# ─── Sabitler ────────────────────────────────────────────────────────────────

MAX_OUTPUT_CHARS = 20_000
MAX_COMMAND_TIMEOUT = 300
DEFAULT_TIMEOUT = 120

# ─── Güvenlik Kuralları ─────────────────────────────────────────────────────

# Tehlikeli komutlar — kullanıcı onayı gerektirir
DANGEROUS_COMMANDS = [
    r"\bformat\b",
    r"\bdel\s+/[sq]\b",
    r"\brd\s+/[sq]\b",
    r"\bRemove-Item\b.*-Recurse.*-Force",
    r"\bshutdown\b",
    r"\brestart-computer\b",
    r"\bStop-Computer\b",
    r"\breg\s+delete\b",
    r"\bdiskpart\b",
    r"\bdrop\s+table\b",
    r"\bdrop\s+database\b",
    r"\bdelete\s+from\b",
    r"\btruncate\b",
    r"\bsudo\b",
    r"\brm\s+-rf\b",
    r"\bchmod\s+777\b",
    r"\bchown\b",
    r"\bkill\s+-9\b",
    r"\bsystemctl\s+(stop|disable|mask)\b",
    r"\bnet\s+(user|localgroup)\b",
    r"\bregedit\b",
    r"\bgpupdate\b",
    r"\bsfc\s+/scannow\b",
    r"\bdism\b",
]

# Güvenli komutlar — otomatik çalıştırılabilir
SAFE_COMMANDS = [
    r"^python(?:\.exe)?\s+-m\s+pytest",
    r"^pytest(?:\.exe)?",
    r"^python(?:\.exe)?\s+--version$",
    r"^node(?:\.exe)?\s+--version$",
    r"^npm(?:\.cmd)?\s+--version$",
    r"^npm(?:\.cmd)?\s+run\s+(lint|test|build)",
    r"^git\s+(status|diff|log|branch|show|remote)",
    r"^dir\b",
    r"^ls\b",
    r"^cat\b",
    r"^type\b",
    r"^echo\b",
    r"^cd\b",
    r"^pwd\b",
    r"^whoami$",
    r"^hostname$",
    r"^date$",
    r"^time$",
    r"^ver$",
    r"^systeminfo$",
    r"^tasklist$",
    r"^netstat\b",
    r"^ipconfig\b",
    r"^ping\b",
    r"^tracert\b",
    r"^nslookup\b",
    r"^curl\b",
    r"^wget\b",
    r"^pip\s+list$",
    r"^pip\s+show\b",
    r"^ollama\s+(list|show|ps)$",
    r"^docker\s+(ps|images|logs)\b",
    r"^npm\s+(list|info|view)$",
    r"^cargo\s+(build|test|run)\b",
    r"^go\s+(build|test|run)\b",
]

# Yasaklı komutlar — hiçbir zaman çalıştırılmaz
BLOCKED_COMMANDS = [
    r"\brm\s+-rf\s+/",
    r"\bmkfs\b",
    r"\bdd\s+if=.*of=\/dev\/",
    r"\b:(){ :\|:& };:\b",  # fork bomb
]


# ─── Permission Manager ─────────────────────────────────────────────────────

class PermissionManager:
    """Komut izin yöneticisi."""

    def __init__(self, auto_approve_safe: bool = True):
        self.auto_approve_safe = auto_approve_safe
        self.approved_commands: set[str] = set()

    def check_permission(self, command: str) -> dict[str, Any]:
        """
        Komut için izin kontrolü yap.

        Returns:
            dict: {allowed, reason, needs_approval, category}
        """
        cmd_lower = command.lower().strip()

        # Yasaklı komut kontrolü
        for pattern in BLOCKED_COMMANDS:
            if re.search(pattern, cmd_lower, re.IGNORECASE):
                return {
                    "allowed": False,
                    "reason": "Bu komut UMAY güvenlik politikası tarafından engellendi.",
                    "needs_approval": False,
                    "category": "blocked",
                }

        # Tehlikeli komut kontrolü
        for pattern in DANGEROUS_COMMANDS:
            if re.search(pattern, cmd_lower, re.IGNORECASE):
                return {
                    "allowed": False,
                    "reason": f"Tehlikeli komut tespit edildi: {pattern}",
                    "needs_approval": True,
                    "category": "dangerous",
                }

        # Güvenli komut kontrolü
        if self.auto_approve_safe:
            for pattern in SAFE_COMMANDS:
                if re.search(pattern, cmd_lower, re.IGNORECASE):
                    return {
                        "allowed": True,
                        "reason": "Güvenli komut",
                        "needs_approval": False,
                        "category": "safe",
                    }

        # Diğer komutlar — dikkatli ol
        return {
            "allowed": True,
            "reason": "Bilinmeyen komut — dikkatli çalıştırılmalı",
            "needs_approval": False,
            "category": "unknown",
        }

    def approve_command(self, command: str) -> None:
        """Bir komutu onayla."""
        self.approved_commands.add(command.strip().lower())

    def is_approved(self, command: str) -> bool:
        """Komut daha önce onaylanmış mı?"""
        return command.strip().lower() in self.approved_commands


# ─── Çıktı Analiz Motoru ────────────────────────────────────────────────────

class OutputAnalyzer:
    """Komut çıktılarını analiz eden motor."""

    # Hata kalıpları (özel olanlar önce, genel olanlar sonra)
    ERROR_PATTERNS = [
        (r"(?i)syntaxerror", "SYNTAX_ERROR", "Sözdizimi hatası"),
        (r"(?i)nameerror", "NAME_ERROR", "Tanımsız değişken"),
        (r"(?i)typeerror", "TYPE_ERROR", "Tür hatası"),
        (r"(?i)valueerror", "VALUE_ERROR", "Değer hatası"),
        (r"(?i)keyerror", "KEY_ERROR", "Anahtar bulunamadı"),
        (r"(?i)indexerror", "INDEX_ERROR", "İndex hatası"),
        (r"(?i)file(?:notfound)?error", "FILE_ERROR", "Dosya bulunamadı"),
        (r"(?i)(?:import|module)(?:notfound)?error", "IMPORT_ERROR", "Import hatası"),
        (r"(?i)no module named", "IMPORT_ERROR", "Modül bulunamadı"),
        (r"(?i)permission(?:denied)?error", "PERMISSION_ERROR", "İzin hatası"),
        (r"(?i)connection(?:refused|error|refused)", "CONNECTION_ERROR", "Bağlantı hatası"),
        (r"(?i)timeout(?:error)?", "TIMEOUT_ERROR", "Zaman aşımı"),
        (r"(?i)memoryerror", "MEMORY_ERROR", "Bellek hatası"),
        (r"(?i)recursiondepth", "RECURSION_ERROR", "Recursion hatası"),
        (r"(?i)assertion(?:error)?", "ASSERTION_ERROR", "Assertion hatası"),
        (r"(?i)traceback", "TRACEBACK", "Hata izleme"),
        (r"(?i)exception[:\s]", "EXCEPTION", "İstisna"),
        (r"(?i)error[:\s]", "GENERIC_ERROR", "Genel hata"),
        (r"(?i)permission(?:denied)?error", "PERMISSION_ERROR", "İzin hatası"),
        (r"(?i)connection(?:refused|error|refused)", "CONNECTION_ERROR", "Bağlantı hatası"),
        (r"(?i)timeout(?:error)?", "TIMEOUT_ERROR", "Zaman aşımı"),
        (r"(?i)memoryerror", "MEMORY_ERROR", "Bellek hatası"),
        (r"(?i)recursiondepth", "RECURSION_ERROR", "Recursion hatası"),
        (r"(?i)assertion(?:error)?", "ASSERTION_ERROR", "Assertion hatası"),
        (r"(?i)failed|FAIL", "TEST_FAIL", "Test başarısız"),
        (r"(?i)fatal", "FATAL", "Kritik hata"),
        (r"(?i)panic", "PANIC", "Sistem panik"),
        (r"(?i)segmentation\s+fault", "SEGFAULT", "Bellek erişim hatası"),
        (r"(?i)access\s+denied", "ACCESS_DENIED", "Erişim engellendi"),
        (r"(?i)not\s+found", "NOT_FOUND", "Bulunamadı"),
        (r"(?i)no\s+such\s+file", "NO_SUCH_FILE", "Dosya yok"),
        (r"(?i)command\s+not\s+found", "CMD_NOT_FOUND", "Komut bulunamadı"),
        (r"(?i)is\s+a\s+directory", "IS_DIRECTORY", "Klasör"),
        (r"(?i)permission\s+denied", "PERM_DENIED", "İzin yok"),
    ]

    # Uyarı kalıpları
    WARNING_PATTERNS = [
        (r"(?i)warning[:\s]", "WARNING", "Uyarı"),
        (r"(?i)deprecat", "DEPRECATED", "Kullanımdan kaldırılmış"),
        (r"(?i)futurewarning", "FUTURE_WARNING", "Gelecek uyarısı"),
        (r"(?i)pending", "PENDING", "Beklemede"),
        (r"(?i)skipped", "SKIPPED", "Atlandı"),
    ]

    def analyze(self, stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
        """
        Komut çıktısını analiz et.

        Returns:
            dict: {errors, warnings, summary, severity, suggestions}
        """
        errors = []
        warnings = []

        # Hata ara
        for line in (stdout + "\n" + stderr).split("\n"):
            for pattern, error_type, description in self.ERROR_PATTERNS:
                if re.search(pattern, line):
                    errors.append({
                        "type": error_type,
                        "description": description,
                        "line": line.strip()[:200],
                    })
                    break

        # Uyarı ara
        for line in (stdout + "\n" + stderr).split("\n"):
            for pattern, warning_type, description in self.WARNING_PATTERNS:
                if re.search(pattern, line):
                    warnings.append({
                        "type": warning_type,
                        "description": description,
                        "line": line.strip()[:200],
                    })
                    break

        # Özet oluştur
        severity = "OK"
        if errors:
            severity = "ERROR"
        elif warnings:
            severity = "WARNING"
        elif returncode != 0:
            severity = "FAIL"

        summary = {
            "returncode": returncode,
            "severity": severity,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors[:10],
            "warnings": warnings[:10],
            "suggestions": self._generate_suggestions(errors, returncode),
        }

        return summary

    def _generate_suggestions(self, errors: list[dict], returncode: int) -> list[str]:
        """Hatalara göre çözüm önerileri oluştur."""
        suggestions = []

        for error in errors:
            error_type = error["type"]

            if error_type == "IMPORT_ERROR":
                suggestions.append("Eksik paketi kurmayı deneyin: pip install <paket>")
            elif error_type == "FILE_ERROR":
                suggestions.append("Dosya yolunu ve adını kontrol edin")
            elif error_type == "PERMISSION_ERROR":
                suggestions.append("Yönetici izni gerekebilir")
            elif error_type == "SYNTAX_ERROR":
                suggestions.append("Kod sözdizimini kontrol edin")
            elif error_type == "TEST_FAIL":
                suggestions.append("Test hatalarını inceleyin ve düzeltin")
            elif error_type == "CONNECTION_ERROR":
                suggestions.append("İnternet bağlantısını kontrol edin")
            elif error_type == "TIMEOUT_ERROR":
                suggestions.append("İşlem zaman aşımına uğradı. Daha uzun timeout deneyin")
            elif error_type == "MEMORY_ERROR":
                suggestions.append("Bellek yetersiz. Daha küçük veri ile deneyin")

        if returncode != 0 and not errors:
            suggestions.append(f"Komut{returncode} hata kodu ile çıktı")

        return suggestions


# ─── Process Manager ─────────────────────────────────────────────────────────

class ProcessManager:
    """Çalışan process'leri yönetir."""

    def list_processes(self) -> dict[str, Any]:
        """Çalışan process'leri listele."""
        try:
            if os.name == "nt":
                cmd = "tasklist /FO CSV /NH"
            else:
                cmd = "ps aux --sort=-pcpu"
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=10,
                shell=True, encoding="utf-8", errors="replace",
            )
            return {
                "status": "OK",
                "output": result.stdout[:MAX_OUTPUT_CHARS],
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}

    def find_process(self, name: str) -> dict[str, Any]:
        """Belirli bir process'i bul."""
        try:
            if os.name == "nt":
                cmd = f'tasklist /FI "IMAGENAME eq {name}" /FO CSV'
            else:
                cmd = f"ps aux | grep {name}"

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
                shell=True, encoding="utf-8", errors="replace",
            )
            return {
                "status": "OK",
                "found": name.lower() in result.stdout.lower(),
                "output": result.stdout[:MAX_OUTPUT_CHARS],
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}


# ─── Terminal Agent ──────────────────────────────────────────────────────────

class TerminalAgent:
    """UMAY Terminal Agent — Kontrollü komut çalıştırma."""

    def __init__(self, auto_approve_safe: bool = True):
        self.permission_manager = PermissionManager(auto_approve_safe)
        self.output_analyzer = OutputAnalyzer()
        self.process_manager = ProcessManager()

    def run_command(
        self,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
        cwd: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Komut çalıştır.

        Args:
            command: Çalıştırılacak komut
            timeout: Zaman aşımı (saniye)
            cwd: Çalışma dizini
            force: İzin kontrolünü atla

        Returns:
            dict: {stdout, stderr, returncode, analysis, permission}
        """
        # Permission kontrolü
        permission = self.permission_manager.check_permission(command)

        # Önce onay gerektiren komutları kontrol et (tehlikeli ama çalıştırılabilir)
        if permission["needs_approval"] and not self.permission_manager.is_approved(command):
            return {
                "error": "Bu komut için kullanıcı onayı gerekiyor",
                "permission": permission,
                "status": "NEEDS_APPROVAL",
                "command": command,
            }

        if not permission["allowed"] and not force:
            return {
                "error": permission["reason"],
                "permission": permission,
                "status": "BLOCKED",
            }

        # Action logging
        aid = eylem_baslat(
            ajan="terminal_agent",
            niyet=f"Komut çalıştır: {command[:80]}",
            plan=f"Timeout: {timeout}s, CWD: {cwd or 'aktif workspace'}",
            model="",
        )

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True,
                timeout=min(timeout, MAX_COMMAND_TIMEOUT),
                cwd=cwd,
                encoding="utf-8",
                errors="replace",
            )

            duration = time.time() - start_time
            stdout = result.stdout or ""
            stderr = result.stderr or ""

            # Çıktıyı kısalt
            stdout_display = stdout[-MAX_OUTPUT_CHARS:] if len(stdout) > MAX_OUTPUT_CHARS else stdout
            stderr_display = stderr[-MAX_OUTPUT_CHARS:] if len(stderr) > MAX_OUTPUT_CHARS else stderr

            # Çıktıyı analiz et
            analysis = self.output_analyzer.analyze(stdout_display, stderr_display, result.returncode)

            output = {
                "command": command,
                "returncode": result.returncode,
                "stdout": stdout_display,
                "stderr": stderr_display,
                "duration_s": round(duration, 2),
                "analysis": analysis,
                "permission": permission,
                "status": "PASS" if result.returncode == 0 else "FAIL",
            }

            # Log
            status_text = "başarılı" if result.returncode == 0 else f"hatalı (exit={result.returncode})"
            eylem_tamamla(
                aid,
                f"Komut {status_text}: {command[:50]} ({duration:.1f}s)",
                result.returncode == 0,
                duration,
            )

            return output

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            error_msg = f"Komut zaman aşımı: {timeout} saniye"
            eylem_hata(aid, error_msg)
            return {
                "command": command,
                "error": error_msg,
                "duration_s": round(duration, 2),
                "status": "TIMEOUT",
            }
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Komut çalıştırma hatası: {e}"
            eylem_hata(aid, error_msg)
            return {
                "command": command,
                "error": error_msg,
                "duration_s": round(duration, 2),
                "status": "ERROR",
            }

    def run_powershell(
        self,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        """PowerShell komutu çalıştır."""
        ps_command = f'powershell -Command "{command}"'
        return self.run_command(ps_command, timeout=timeout)

    def run_cmd(
        self,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        """CMD komutu çalıştır."""
        cmd_command = f'cmd /c "{command}"'
        return self.run_command(cmd_command, timeout=timeout)

    def analyze_error(
        self,
        command: str,
        error_output: str,
    ) -> dict[str, Any]:
        """
        Hata çıktısını analiz et ve çözüm öner.

        Returns:
            dict: {error_type, description, suggestions, related_commands}
        """
        analysis = self.output_analyzer.analyze("", error_output, 1)

        # Çözüm önerileri
        suggestions = analysis.get("suggestions", [])

        # İlgili komutlar
        related_commands = []
        if analysis["errors"]:
            error_type = analysis["errors"][0]["type"]

            if error_type == "IMPORT_ERROR":
                # Eksik paketi bul
                match = re.search(r"No module named ['\"](.+?)['\"]", error_output)
                if match:
                    module_name = match.group(1)
                    related_commands.append(f"pip install {module_name}")

            elif error_type == "FILE_ERROR":
                related_commands.append("dir / ls ile dosya yolunu kontrol edin")

            elif error_type == "TEST_FAIL":
                related_commands.append("python -m pytest -v")

        return {
            "error_type": analysis["errors"][0]["type"] if analysis["errors"] else "UNKNOWN",
            "description": analysis["errors"][0]["description"] if analysis["errors"] else "Bilinmeyen hata",
            "suggestions": suggestions,
            "related_commands": related_commands,
            "full_analysis": analysis,
        }

    def get_system_info(self) -> dict[str, Any]:
        """Sistem bilgisi topla."""
        info = {}

        # OS
        info["os"] = os.name
        info["platform"] = os.sys.platform

        # Python
        info["python_version"] = os.sys.version

        # Working directory
        info["cwd"] = os.getcwd()

        # Disk kullanımı (Windows)
        if os.name == "nt":
            result = self.run_command("wmic logicaldisk get size,freespace,caption", timeout=5)
            if result.get("status") == "PASS":
                info["disk"] = result["stdout"][:500]

        return info

    def read_log(
        self,
        log_path: str,
        tail_lines: int = 100,
        pattern: str | None = None,
    ) -> dict[str, Any]:
        """
        Log dosyasını oku.

        Args:
            log_path: Log dosya yolu
            tail_lines: Son N satır
            pattern: Filtre kalıbı (regex)

        Returns:
            dict: {lines, total_lines, filtered_count}
        """
        path = Path(log_path)

        if not path.exists():
            return {"error": f"Log dosyası bulunamadı: {log_path}", "status": "ERROR"}

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

            # Filtrele
            if pattern:
                regex = re.compile(pattern, re.IGNORECASE)
                lines = [l for l in lines if regex.search(l)]

            # Tail
            total = len(lines)
            lines = lines[-tail_lines:]

            return {
                "path": str(path),
                "total_lines": total,
                "shown_lines": len(lines),
                "lines": lines,
                "status": "OK",
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}


# ─── Ana Fonksiyonlar ───────────────────────────────────────────────────────

# Varsayılan agent instance
_agent = TerminalAgent()


def run_terminal_command(
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Terminal komutu çalıştır (tool system için wrapper)."""
    return _agent.run_command(command, timeout=timeout, cwd=cwd)


def run_powershell(command: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """PowerShell komutu çalıştır."""
    return _agent.run_powershell(command, timeout=timeout)


def analyze_error(command: str, error_output: str) -> dict[str, Any]:
    """Hata çıktısını analiz et."""
    return _agent.analyze_error(command, error_output)


def get_system_info() -> dict[str, Any]:
    """Sistem bilgisi al."""
    return _agent.get_system_info()


def read_log_file(
    log_path: str,
    tail_lines: int = 100,
    pattern: str | None = None,
) -> dict[str, Any]:
    """Log dosyası oku."""
    return _agent.read_log(log_path, tail_lines=tail_lines, pattern=pattern)


def list_processes() -> dict[str, Any]:
    """Çalışan process'leri listele."""
    return _agent.process_manager.list_processes()


def find_process(name: str) -> dict[str, Any]:
    """Process bul."""
    return _agent.process_manager.find_process(name)


# ─── Dosya/Klasör Açma Fonksiyonları ─────────────────────────────────────

def open_file(path: str) -> dict[str, Any]:
    """Bir dosyayı varsayılan uygulama ile aç (Windows: start, Linux: xdg-open)."""
    import subprocess
    import platform
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return {"status": "ERROR", "error": f"Dosya bulunamadı: {path}"}

    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(str(p.resolve()))
        elif system == "Darwin":
            subprocess.Popen(["open", str(p.resolve())])
        else:
            subprocess.Popen(["xdg-open", str(p.resolve())])
        return {"status": "OK", "message": f"Dosya açıldı: {p.name}", "path": str(p.resolve())}
    except Exception as e:
        return {"status": "ERROR", "error": f"Dosya açılamadı: {e}"}


def open_folder(path: str = ".") -> dict[str, Any]:
    """Klasörü dosya yöneticisinde aç."""
    import subprocess
    import platform
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return {"status": "ERROR", "error": f"Klasör bulunamadı: {path}"}
    if not p.is_dir():
        p = p.parent

    try:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["explorer", str(p.resolve())])
        elif system == "Darwin":
            subprocess.Popen(["open", str(p.resolve())])
        else:
            subprocess.Popen(["xdg-open", str(p.resolve())])
        return {"status": "OK", "message": f"Klasör açıldı: {p.resolve()}", "path": str(p.resolve())}
    except Exception as e:
        return {"status": "ERROR", "error": f"Klasör açılamadı: {e}"}


def open_url(url: str) -> dict[str, Any]:
    """URL'yi varsayılan tarayıcıda aç."""
    import subprocess
    import platform

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["start", url], shell=True)
        elif system == "Darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        return {"status": "OK", "message": f"URL açıldı: {url}"}
    except Exception as e:
        return {"status": "ERROR", "error": f"URL açılamadı: {e}"}


def open_with_app(app_name: str, path: str) -> dict[str, Any]:
    """Belirli bir uygulama ile dosya aç (örn: notepad, code, calc)."""
    import subprocess
    import platform
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return {"status": "ERROR", "error": f"Dosya bulunamadı: {path}"}

    try:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen([app_name, str(p.resolve())])
        else:
            subprocess.Popen([app_name, str(p.resolve())])
        return {"status": "OK", "message": f"{app_name} ile açıldı: {p.name}", "path": str(p.resolve())}
    except Exception as e:
        return {"status": "ERROR", "error": f"Açılamadı: {e}"}


# ─── Test Fonksiyonu ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== UMAY Terminal Agent Test ===\n")

    agent = TerminalAgent()

    # Test 1: Güvenli komut
    print("Test 1: Güvenli komut (python --version)")
    result = agent.run_command("python --version")
    print(f"  Durum: {result['status']}")
    print(f"  Çıktı: {result.get('stdout', '')[:100]}")

    # Test 2: Sistem bilgisi
    print("\nTest 2: Sistem bilgisi")
    info = agent.get_system_info()
    print(f"  OS: {info.get('os')}")
    print(f"  Python: {info.get('python_version', '')[:50]}")

    # Test 3: Permission kontrolü
    print("\nTest 3: Permission kontrolü")
    perm = agent.permission_manager.check_permission("format C:")
    print(f"  format C: → {perm['category']} (allowed: {perm['allowed']})")

    perm = agent.permission_manager.check_permission("python --version")
    print(f"  python --version → {perm['category']} (allowed: {perm['allowed']})")

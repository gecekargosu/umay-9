"""UMAY filesystem/terminal tools with a dynamically selected active workspace."""
from __future__ import annotations

import os
import re
import subprocess
import json
import shutil
import time
import threading
from pathlib import Path
from urllib.parse import quote_plus
from typing import Any

from core.utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_WORKSPACE = Path(os.getenv("UMAY_WORKSPACE", str(PROJECT_ROOT))).resolve()

MAX_READ = 120_000
MAX_LIST = 2_000
MAX_SEARCH = 500
EXECUTION_MODE = os.getenv("UMAY_MODE", "approval").lower()
BACKUP_DIR_NAME = ".umay_backups"

SKIP_PARTS = {".git", "__pycache__", ".venv", "node_modules", "dist", "build", ".next", ".cache"}
SAFE_COMMANDS = [
    r"^python(?:\.exe)?\s+-m\s+pytest(?:\s|$)",
    r"^pytest(?:\.exe)?(?:\s|$)",
    r"^python(?:\.exe)?\s+--version$",
    r"^node(?:\.exe)?\s+--version$",
    r"^npm(?:\.cmd)?\s+--version$",
    r"^npm(?:\.cmd)?\s+run\s+lint(?:\s|$)",
    r"^git\s+(?:status|diff(?:\s|$)|log(?:\s|$)|branch(?:\s|$))",
    r"^docker(?:\.exe)?\s+compose\s+(?:ps|config)(?:\s|$)",
]

DENIED_COMMANDS = [
    r"\bformat\b", r"\bdel\s+/[sq]\b", r"\brd\s+/[sq]\b",
    r"\bRemove-Item\b.*-Recurse.*-Force", r"\bshutdown\b",
    r"\brestart-computer\b", r"\bStop-Computer\b", r"\breg\s+delete\b",
    r"\bdiskpart\b",
]


def set_workspace(path: str | Path) -> Path:
    """Set the active project root used by all workspace tools."""
    global ACTIVE_WORKSPACE
    target = Path(path).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError(f"Workspace klasörü bulunamadı: {target}")
    ACTIVE_WORKSPACE = target
    return ACTIVE_WORKSPACE


def get_workspace() -> Path:
    return ACTIVE_WORKSPACE


def _safe_path(path: str) -> Path:
    raw = Path(path)
    target = (ACTIVE_WORKSPACE / raw).resolve() if not raw.is_absolute() else raw.resolve()
    # Allow /host/* paths (Windows host filesystem mounts)
    if str(target).startswith("/host/"):
        return target
    if target != ACTIVE_WORKSPACE and ACTIVE_WORKSPACE not in target.parents:
        raise PermissionError(f"Workspace dışına erişim yasak: {target}")
    return target


def _skip(item: Path) -> bool:
    return any(part in SKIP_PARTS for part in item.parts)


def list_directory(path: str = ".", recursive: bool = False) -> dict[str, Any]:
    target = _safe_path(path)
    if not target.is_dir():
        raise FileNotFoundError(f"Klasör bulunamadı: {path}")
    entries = []
    iterator = target.rglob("*") if recursive else target.iterdir()
    for item in iterator:
        if len(entries) >= MAX_LIST:
            break
        if _skip(item):
            continue
        try:
            # Handle /host/* paths (Windows host filesystem mounts)
            if str(target).startswith("/host/"):
                rel = str(item.relative_to(target))
            else:
                rel = str(item.relative_to(ACTIVE_WORKSPACE))
            entries.append({
                "path": rel,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
        except OSError:
            pass
    return {"workspace": str(ACTIVE_WORKSPACE), "count": len(entries), "entries": entries}


def read_file(path: str, start_line: int = 1, max_lines: int = 400) -> dict[str, Any]:
    target = _safe_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    start = max(1, int(start_line))
    end = min(len(lines), start - 1 + max(1, int(max_lines)))
    content = "\n".join(f"{i}: {lines[i-1]}" for i in range(start, end + 1))
    return {
        "path": str(target.relative_to(ACTIVE_WORKSPACE)),
        "lines": len(lines), "start_line": start, "end_line": end,
        "content": content[:MAX_READ],
    }


def search_files(pattern: str, path: str = ".", max_results: int = 100) -> dict[str, Any]:
    target = _safe_path(path)
    regex = re.compile(pattern, re.IGNORECASE)
    max_results = max(1, min(int(max_results), MAX_SEARCH))
    matches = []
    files = target.rglob("*") if target.is_dir() else [target]
    for file in files:
        if not file.is_file() or _skip(file):
            continue
        try:
            for lineno, line in enumerate(file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if regex.search(line):
                    matches.append({
                        "path": str(file.relative_to(ACTIVE_WORKSPACE)),
                        "line": lineno, "text": line[:500],
                    })
                    if len(matches) >= max_results:
                        return {"pattern": pattern, "matches": matches}
        except (OSError, UnicodeError):
            continue
    return {"pattern": pattern, "matches": matches}


def write_file(path: str, content: str) -> dict[str, Any]:
    if not _approved():
        raise PermissionError("Dosya değişikliği için UMAY_MODE=auto_fix veya UMAY_APPROVED=true gerekir.")
    target = _safe_path(path)
    if target == ACTIVE_WORKSPACE:
        raise PermissionError("Kök klasör dosya değildir")
    aid = eylem_baslat(
        "umay_tool",
        f"Dosya değişikliği: {path}",
        f"Workspace içinde dosya yaz: {ACTIVE_WORKSPACE}",
        "",
    )
    backup_path = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            backup_root = ACTIVE_WORKSPACE / BACKUP_DIR_NAME
            backup_root.mkdir(exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = backup_root / f"{target.name}.{stamp}.bak"
            shutil.copy2(target, backup_path)
        old = target.read_text(encoding="utf-8", errors="replace") if target.exists() else None
        target.write_text(content, encoding="utf-8")
        result = {
            "path": str(target.relative_to(ACTIVE_WORKSPACE)),
            "created": old is None,
            "bytes": len(content.encode("utf-8")),
            "backup": str(backup_path.relative_to(ACTIVE_WORKSPACE)) if backup_path else None,
        }
        eylem_tamamla(aid, f"Dosya {'oluşturuldu' if old is None else 'güncellendi'}: {result['path']}", True)
        return result
    except Exception as exc:
        eylem_hata(aid, str(exc))
        raise


def _command_is_safe(command: str) -> bool:
    normalized = command.strip()
    return any(re.search(rule, normalized, re.IGNORECASE) for rule in SAFE_COMMANDS)


def _approved() -> bool:
    return EXECUTION_MODE == "auto_fix" or os.getenv("UMAY_APPROVED", "false").lower() == "true"


def run_command(command: str, timeout: int = 120) -> dict[str, Any]:
    if any(re.search(rule, command, re.IGNORECASE) for rule in DENIED_COMMANDS):
        raise PermissionError("Bu komut UMAY güvenlik politikası tarafından engellendi.")
    if not _command_is_safe(command) and not _approved():
        raise PermissionError(
            "Bu komut değişiklik/yan etki riski taşıyor. "
            "UMAY_MODE=auto_fix veya UMAY_APPROVED=true ile açık onay verin."
        )
    aid = eylem_baslat("umay_tool", f"Komut: {command[:100]}",
                       f"Workspace içinde komut çalıştır: {ACTIVE_WORKSPACE}", "")
    started = time.time()
    try:
        result = subprocess.run(
            command, cwd=str(ACTIVE_WORKSPACE), shell=True,
            capture_output=True, text=True,
            timeout=max(1, min(int(timeout), 600)),
            encoding="utf-8", errors="replace",
        )
        out = (result.stdout or "")[-20_000:]
        err = (result.stderr or "")[-20_000:]
        eylem_tamamla(aid, f"exit={result.returncode}", result.returncode == 0,
                      time.time() - started)
        status = "PASS" if result.returncode == 0 else "FAIL"
        return {
            "workspace": str(ACTIVE_WORKSPACE), "command": command,
            "returncode": result.returncode, "status": status,
            "stdout": out, "stderr": err, "duration_s": round(time.time()-started, 2),
        }
    except Exception as exc:
        eylem_hata(aid, str(exc))
        raise


def run_test_suite(command: str = "python -m pytest -q", timeout: int = 180) -> dict[str, Any]:
    result = run_command(command, timeout)
    return {"status": result.get("status"), "returncode": result.get("returncode"), "command": command,
            "summary": (result.get("stdout", "") + "\n" + result.get("stderr", ""))[-12000:]}


def git_diff_summary() -> dict[str, Any]:
    if not (ACTIVE_WORKSPACE / ".git").exists():
        return {"status":"NOT_A_GIT_REPO","summary":"Aktif workspace Git repository değil."}
    result = subprocess.run("git diff --stat && git status --short", cwd=str(ACTIVE_WORKSPACE), shell=True, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
    return {"status":"PASS" if result.returncode==0 else "FAIL", "returncode":result.returncode,
            "summary":(result.stdout+"\n"+result.stderr)[-12000:]}


def rollback_backup(backup_relative: str, target_relative: str) -> dict[str, Any]:
    if EXECUTION_MODE != "auto_fix" and os.getenv("UMAY_APPROVED", "false").lower() != "true":
        raise PermissionError("Rollback için UMAY_MODE=auto_fix veya UMAY_APPROVED=true gerekir.")
    backup=_safe_path(backup_relative); target=_safe_path(target_relative)
    if not backup.is_file(): raise FileNotFoundError(backup)
    target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(backup,target)
    return {"status":"PASS","restored":str(target.relative_to(ACTIVE_WORKSPACE)),"backup":str(backup.relative_to(ACTIVE_WORKSPACE))}

def inspect_project() -> dict[str, Any]:
    root = ACTIVE_WORKSPACE
    files = [p for p in root.rglob("*") if p.is_file() and not _skip(p)]
    names={p.name.lower() for p in files}
    dirs={p.name.lower() for p in root.iterdir() if p.is_dir()} if root.exists() else set()
    kind=[]
    if "pyproject.toml" in names or "requirements.txt" in names: kind.append("python")
    if "package.json" in names: kind.append("node")
    if "dockerfile" in names or "docker-compose.yml" in names or "docker-compose.yaml" in names: kind.append("docker")
    if ".git" in dirs: kind.append("git")
    if any("pytest" in p.name.lower() for p in files) or (root/"tests").is_dir(): kind.append("tests")
    return {"workspace":str(root),"project_types":kind,"file_count":len(files),"top_level":sorted(p.name for p in root.iterdir())}


# ---------------------------------------------------------------------------
# Browser / online gateway
# ---------------------------------------------------------------------------
_BROWSER = None
_BROWSER_LOCK = threading.Lock()


def _browser():
    """Lazy-create one browser session so online tools share the same page."""
    global _BROWSER
    with _BROWSER_LOCK:
        if _BROWSER is None:
            from agents.browser_agent import BrowserAgent
            headless = os.getenv("UMAY_BROWSER_HEADLESS", "true").lower() == "true"
            _BROWSER = BrowserAgent(gorunur=not headless, yavas_mod=False)
            if not _BROWSER.baslat():
                _BROWSER = None
                raise RuntimeError("Browser başlatılamadı. Playwright/Chromium kurulumunu kontrol edin.")
        return _BROWSER


def browser_open(url: str) -> dict[str, Any]:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    agent = _browser()
    if not agent.git(url):
        raise RuntimeError(f"Sayfa açılamadı: {url}")
    return {
        "url": agent.sayfa.url,
        "title": agent.sayfa_baslik(),
        "text": agent.sayfa_metni()[:12000],
        "screenshot": agent.ekran_al(),
    }


def browser_read() -> dict[str, Any]:
    agent = _browser()
    return {
        "url": agent.sayfa.url,
        "title": agent.sayfa_baslik(),
        "text": agent.sayfa_metni()[:12000],
        "html": agent.sayfa_html()[:12000],
    }


def web_search(query: str, max_results: int = 8) -> dict[str, Any]:
    """Read-only web search; no API key required.
    
    duckduckgo-search kütüphanesi ile arama yapar.
    Başarısız olursa Playwright fallback kullanır.
    """
    max_results = max(1, min(int(max_results), 20))
    aid = eylem_baslat("web_gateway", f"Web araması: {query[:100]}", "DuckDuckGo araması", "")
    
    # Yöntem 1: duckduckgo-search kütüphanesi (daha güvenilir)
    links = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=max_results)
        links = [{"title": r.get("title", ""), "href": r.get("href", "")} for r in results]
    except Exception as e:
        log(f"[SEARCH] duckduckgo-search hatası: {e}, Playwright deneniyor")
        # Yöntem 2: Playwright fallback
        try:
            agent = _browser()
            url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
            if agent.git(url):
                time.sleep(2)
                links = agent.sayfa.eval_on_selector_all(
                    "a.result__a, a.result-link, a[href]",
                    "els => els.map(e => ({title: e.innerText.trim(), href: e.href})).filter(e => e.title.length > 3).slice(0, %d)" % max_results,
                )
        except Exception as e2:
            log(f"[SEARCH] Playwright fallback de başarısız: {e2}")
    
    result = {
        "query": query,
        "results": links,
        "count": len(links),
    }
    eylem_tamamla(aid, f"{len(links)} arama sonucu", len(links) > 0)
    return result


def browser_click(selector: str) -> dict[str, Any]:
    if not _approved():
        raise PermissionError("Tarayıcı tıklaması için açık onay gerekir: UMAY_APPROVED=true veya UMAY_MODE=auto_fix")
    agent = _browser()
    if not agent.tikla(selector):
        raise RuntimeError(f"Element tıklanamadı: {selector}")
    return {"url": agent.sayfa.url, "title": agent.sayfa_baslik(), "text": agent.sayfa_metni()[:8000]}


def browser_type(selector: str, text: str) -> dict[str, Any]:
    if not _approved():
        raise PermissionError("Tarayıcıya veri yazmak için açık onay gerekir: UMAY_APPROVED=true veya UMAY_MODE=auto_fix")
    agent = _browser()
    if not agent.yaz(selector, text):
        raise RuntimeError(f"Elemente yazılamadı: {selector}")
    return {"url": agent.sayfa.url, "title": agent.sayfa_baslik(), "text": agent.sayfa_metni()[:8000]}


def browser_screenshot() -> dict[str, Any]:
    agent = _browser()
    return {"path": agent.ekran_al(), "url": agent.sayfa.url, "title": agent.sayfa_baslik()}


def browser_close() -> dict[str, Any]:
    global _BROWSER
    with _BROWSER_LOCK:
        if _BROWSER is not None:
            _BROWSER.kapat()
            _BROWSER = None
    return {"status": "PASS", "message": "Browser kapatıldı."}


# ─── Dosya/Klasör/URL Açma Tool'ları ─────────────────────────────────────

def open_file(path: str) -> dict[str, Any]:
    """Bir dosyayı varsayılan uygulama ile aç."""
    from core.terminal_agent import open_file as _open_file
    return _open_file(path)


def open_folder(path: str = ".") -> dict[str, Any]:
    """Klasörü dosya yöneticisinde aç."""
    from core.terminal_agent import open_folder as _open_folder
    return _open_folder(path)


def open_url(url: str) -> dict[str, Any]:
    """URL'yi varsayılan tarayıcıda aç."""
    from core.terminal_agent import open_url as _open_url
    return _open_url(url)


def open_with_app(app_name: str, path: str) -> dict[str, Any]:
    """Belirli bir uygulama ile dosya aç."""
    from core.terminal_agent import open_with_app as _open_with
    return _open_with(app_name, path)


# ─── System Clock / Date Tools ────────────────────────────────────────────────

import platform
import subprocess


def get_current_time(timezone: str = "Europe/Istanbul") -> dict[str, Any]:
    """Sistemin gerçek saatini döndür. Ollama/LLM tarafından uydurulmaz."""
    from datetime import datetime, timezone as tz, timedelta
    try:
        now = datetime.now()
        return {
            "time": now.strftime("%H:%M:%S"),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": timezone,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
        }
    except Exception as exc:
        return {"error": str(exc)}


def get_current_date() -> dict[str, Any]:
    """Sistemin gerçek tarihini döndür."""
    from datetime import datetime
    try:
        now = datetime.now()
        day_names_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        month_names_tr = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        return {
            "date": now.strftime("%Y-%m-%d"),
            "day_of_week": day_names_tr[now.weekday()],
            "day": now.day,
            "month": now.month,
            "month_name": month_names_tr[now.month],
            "year": now.year,
            "formatted": f"{day_names_tr[now.weekday()]}, {now.day} {month_names_tr[now.month]} {now.year}",
        }
    except Exception as exc:
        return {"error": str(exc)}


def get_system_info() -> dict[str, Any]:
    """Sistem bilgisi toplar."""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        mem = psutil.virtual_memory()
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "python": platform.python_version(),
            "hostname": platform.node(),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_percent": disk.percent,
            "memory_total_gb": round(mem.total / (1024**3), 1),
            "memory_percent": mem.percent,
        }
    except ImportError:
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "python": platform.python_version(),
            "hostname": platform.node(),
        }


def list_processes() -> dict[str, Any]:
    """Çalışan process'leri listeler."""
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                procs.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'cpu': round(info.get('cpu_percent', 0) or 0, 1),
                    'memory': round(info.get('memory_percent', 0) or 0, 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x.get('cpu', 0), reverse=True)
        return {"processes": procs[:50], "count": len(procs)}
    except ImportError:
        result = subprocess.run(['tasklist', '/FO', 'CSV'], capture_output=True, text=True, timeout=10)
        return {"raw": result.stdout[:5000], "note": "psutil kurulu değil"}


def find_process(name: str) -> dict[str, Any]:
    """Belirli bir processi bulur."""
    try:
        import psutil
        found = []
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if name.lower() in (p.info['name'] or '').lower():
                    found.append({
                        'pid': p.info['pid'],
                        'name': p.info['name'],
                        'cmdline': ' '.join(p.info.get('cmdline') or [])[:200],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {"matches": found, "count": len(found)}
    except ImportError:
        result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {name}*'], capture_output=True, text=True, timeout=10)
        return {"raw": result.stdout[:3000]}


# ─── Calculator Tool ─────────────────────────────────────────────────────────

import ast as _ast
import operator as _op

_SAFE_OPS = {
    _ast.Add: _op.add, _ast.Sub: _op.sub, _ast.Mult: _op.mul,
    _ast.Div: _op.truediv, _ast.Mod: _op.mod, _ast.Pow: _op.pow,
    _ast.USub: _op.neg, _ast.UAdd: _op.pos,
}


def evaluate_expression(expression: str) -> dict[str, Any]:
    """Matematiksel ifadeyi güvenli şekilde değerlendir. LLM kullanmadan doğrudan hesapla."""
    try:
        # Temizleme
        expr = expression.strip()
        # Türkçe karakterleri temizle
        expr = expr.replace('×', '*').replace('÷', '/').replace('x', '*').replace('X', '*')
        # '=' işaretini kaldır
        if expr.endswith('='):
            expr = expr[:-1].strip()
        # Güvenli AST evaluation
        tree = _ast.parse(expr, mode='eval')
        result = _eval_node(tree.body)
        return {
            "expression": expression,
            "result": result,
            "formatted": f"{expression} = {result}",
        }
    except ZeroDivisionError:
        return {"error": "Sıfıra bölemezsin", "expression": expression}
    except Exception as exc:
        return {"error": f"Hesaplama hatası: {exc}", "expression": expression}


def _eval_node(node: _ast.AST) -> float:
    """AST node'unu güvenli şekilde değerlendir."""
    if isinstance(node, _ast.Num):
        return node.n
    elif isinstance(node, _ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, _ast.BinOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Desteklenmeyen operatör: {type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))
    elif isinstance(node, _ast.UnaryOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Desteklenmeyen operatör: {type(node.op).__name__}")
        return op(_eval_node(node.operand))
    else:
        raise ValueError(f"Desteklenmeyen ifade tipi: {type(node).__name__}")


# ─── Time Tool Definitions ────────────────────────────────────────────────────
TIME_TOOLS = [
    {"type": "function", "function": {
        "name": "get_current_time",
        "description": "Sistemin gerçek saatini döndürür. Ollama/LLM tarafından uydurulmaz, gerçek sistem saati kullanılır.",
        "parameters": {"type": "object", "properties": {
            "timezone": {"type": "string", "description": "Saat dilimi (varsayılan: Europe/Istanbul)"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "get_current_date",
        "description": "Sistemin gerçek tarihini ve gününü döndürür.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "evaluate_expression",
        "description": "Matematiksel ifadeyi hesaplar (toplama, çıkarma, çarpma, bölme, üs alma). LLM kullanmadan doğrudan sonucu üretir.",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "Hesaplanacak matematiksel ifade (ör: '9/1*2-3+4')"}
        }, "required": ["expression"]}}},
]

TOOLS = [
    {"type": "function", "function": {
        "name": "list_directory",
        "description": "Aktif workspace içindeki dosya ve klasörleri listeler.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "recursive": {"type": "boolean"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Aktif workspace içindeki metin dosyasını satır numaralarıyla okur.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "start_line": {"type": "integer"},
            "max_lines": {"type": "integer"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "search_files",
        "description": "Aktif workspace dosyalarında regex/metin arar.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"}, "path": {"type": "string"},
            "max_results": {"type": "integer"}
        }, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Aktif workspace içinde dosya oluşturur/günceller; yalnızca kullanıcı değişiklik yetkisi verdiğinde kullan.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}
        }, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_test_suite", "description": "Belirtilen test komutunu çalıştırır ve standart PASS/FAIL sonucu üretir.", "parameters": {"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"integer"}},"required":[]}}},
    {"type": "function", "function": {"name": "git_diff_summary", "description": "Git çalışma ağacının değişiklik özetini çıkarır.", "parameters": {"type":"object","properties":{},"required":[]}}},
    {"type": "function", "function": {"name": "rollback_backup", "description": "Daha önce oluşturulmuş UMAY yedeğini geri yükler; onay gerektirir.", "parameters": {"type":"object","properties":{"backup_relative":{"type":"string"},"target_relative":{"type":"string"}},"required":["backup_relative","target_relative"]}}},
    {"type": "function", "function": {"name": "inspect_project", "description": "Aktif workspace'in proje türünü, temel dosyalarını ve test yapısını keşfeder.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "web_search", "description": "İnternette salt-okuma araması yapar ve ilk sonuçları döndürür.", "parameters": {"type":"object","properties":{"query":{"type":"string"},"max_results":{"type":"integer"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "browser_open", "description": "Web sayfasını açar ve metnini okur; salt-okuma işlemidir.", "parameters": {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
    {"type": "function", "function": {"name": "browser_read", "description": "Mevcut web sayfasının metin ve HTML içeriğini okur.", "parameters": {"type":"object","properties":{},"required":[]}}},
    {"type": "function", "function": {"name": "browser_click", "description": "Web sayfasındaki elementi tıklar; açık kullanıcı onayı gerekir.", "parameters": {"type":"object","properties":{"selector":{"type":"string"}},"required":["selector"]}}},
    {"type": "function", "function": {"name": "browser_type", "description": "Web sayfasındaki alana veri yazar; açık kullanıcı onayı gerekir.", "parameters": {"type":"object","properties":{"selector":{"type":"string"},"text":{"type":"string"}},"required":["selector","text"]}}},
    {"type": "function", "function": {"name": "browser_screenshot", "description": "Mevcut sayfanın ekran görüntüsünü alır.", "parameters": {"type":"object","properties":{},"required":[]}}},
    {"type": "function", "function": {"name": "browser_close", "description": "Açık browser oturumunu kapatır.", "parameters": {"type":"object","properties":{},"required":[]}}},
    {"type": "function", "function": {"name": "open_file", "description": "Bir dosyayı varsayılan uygulama ile açar (PDF, resim, video, belge vb.).", "parameters": {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
    {"type": "function", "function": {"name": "open_folder", "description": "Klasörü dosya yöneticisinde açar.", "parameters": {"type":"object","properties":{"path":{"type":"string"}},"required":[]}}},
    {"type": "function", "function": {"name": "open_url", "description": "URL'yi varsayılan tarayıcıda açar.", "parameters": {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
    {"type": "function", "function": {"name": "open_with_app", "description": "Belirli bir uygulama ile dosya açar (notepad, code, calc vb.).", "parameters": {"type":"object","properties":{"app_name":{"type":"string"},"path":{"type":"string"}},"required":["app_name","path"]}}},
    {"type": "function", "function": {
        "name": "run_command",
        "description": "Aktif workspace kökünde test/lint/build/git gibi komutları çalıştırır.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}, "timeout": {"type": "integer"}
        }, "required": ["command"]}}},
    # ─── Document Reader Tool'ları ───────────────────────────────────────────
    {"type": "function", "function": {
        "name": "read_document",
        "description": "PDF, Word, Excel, CSV, TXT, Markdown gibi belgeleri okur. Otomatik format algılar.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "max_pages": {"type": "integer"},
            "max_rows": {"type": "integer"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "scan_directory",
        "description": "Klasörü tara ve desteklenen belgeleri listele (PDF, Word, Excel, CSV vb.).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "recursive": {"type": "boolean"},
            "file_types": {"type": "array", "items": {"type": "string"}},
            "max_files": {"type": "integer"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "search_in_documents",
        "description": "Belgelerde metin/regex ara (PDF, Word, Excel, kod dosyaları dahil).",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "path": {"type": "string"},
            "file_types": {"type": "array", "items": {"type": "string"}},
            "max_results": {"type": "integer"}
        }, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "document_to_memory",
        "description": "Belge içeriğini RAG/hafıza sistemine aktarır.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "source": {"type": "string"}
        }, "required": ["path"]}}},
]

# Time tool'ları TOOLS listesine ekle
TOOLS.extend(TIME_TOOLS)

# Document Reader import'u (opsiyonel)
try:
    from core.document_reader import read_document as _read_document
    from core.document_reader import scan_directory as _scan_directory
    from core.document_reader import search_in_documents as _search_in_documents
    from core.document_reader import document_to_memory as _document_to_memory
except ImportError:
    _read_document = None
    _scan_directory = None
    _search_in_documents = None
    _document_to_memory = None


def read_document(path: str, max_pages: int = 50, max_rows: int = 500) -> dict[str, Any]:
    """Wrapper for document reader."""
    if _read_document is None:
        return {"error": "Document Reader modülü yüklenemedi.", "status": "ERROR"}
    return _read_document(path, max_pages=max_pages, max_rows=max_rows)


def scan_directory(path: str = ".", recursive: bool = True, file_types: list[str] | None = None, max_files: int = 200) -> dict[str, Any]:
    """Wrapper for directory scanner."""
    if _scan_directory is None:
        return {"error": "Document Reader modülü yüklenemedi.", "status": "ERROR"}
    # Mutlak yollar workspace dışına erişim izni verir (tarama salt-okuma)
    raw = Path(path)
    if raw.is_absolute():
        target = raw.resolve()
    elif path == ".":
        target = ACTIVE_WORKSPACE
    else:
        target = _safe_path(path)
    return _scan_directory(target, recursive=recursive, file_types=file_types, max_files=max_files)


def search_in_documents(query: str, path: str | None = None, file_types: list[str] | None = None, max_results: int = 50) -> dict[str, Any]:
    """Wrapper for document search."""
    if _search_in_documents is None:
        return {"error": "Document Reader modülü yüklenemedi.", "status": "ERROR"}
    return _search_in_documents(query, dir_path=path, file_types=file_types, max_results=max_results)


def document_to_memory(path: str, source: str = "document") -> dict[str, Any]:
    """Wrapper for document to memory transfer."""
    if _document_to_memory is None:
        return {"error": "Document Reader modülü yüklenemedi.", "status": "ERROR"}
    return _document_to_memory(path, source=source)


# ─── Vision Reader Import ──────────────────────────────────────────────────

try:
    from core.vision_reader import analyze_image as _analyze_image
    from core.vision_reader import image_to_text as _image_to_text
    from core.vision_reader import describe_image as _describe_image
    from core.vision_reader import image_qa as _image_qa
    from core.vision_reader import image_to_memory as _image_to_memory
    from core.vision_reader import analyze_images_batch as _analyze_images_batch
except ImportError:
    _analyze_image = None
    _image_to_text = None
    _describe_image = None
    _image_qa = None
    _image_to_memory = None
    _analyze_images_batch = None


def analyze_image(path: str, question: str = "Bu gorseli detayli sekilde acikla.", use_ocr: bool = True, model: str | None = None) -> dict[str, Any]:
    """Wrapper for image analysis."""
    if _analyze_image is None:
        return {"error": "Vision Reader modulu yuklenemedi.", "status": "ERROR"}
    return _analyze_image(path, question=question, use_ocr=use_ocr, model=model)


def image_to_text(path: str, model: str | None = None) -> dict[str, Any]:
    """Wrapper for image text extraction."""
    if _image_to_text is None:
        return {"error": "Vision Reader modulu yuklenemedi.", "status": "ERROR"}
    return _image_to_text(path, model=model)


def describe_image(path: str, detail_level: str = "detailed", model: str | None = None) -> dict[str, Any]:
    """Wrapper for image description."""
    if _describe_image is None:
        return {"error": "Vision Reader modulu yuklenemedi.", "status": "ERROR"}
    return _describe_image(path, detail_level=detail_level, model=model)


def image_qa(path: str, question: str, model: str | None = None) -> dict[str, Any]:
    """Wrapper for image Q&A."""
    if _image_qa is None:
        return {"error": "Vision Reader modulu yuklenemedi.", "status": "ERROR"}
    return _image_qa(path, question=question, model=model)


def image_to_memory(path: str, source: str = "image", model: str | None = None) -> dict[str, Any]:
    """Wrapper for image to memory transfer."""
    if _image_to_memory is None:
        return {"error": "Vision Reader modulu yuklenemedi.", "status": "ERROR"}
    return _image_to_memory(path, source=source, model=model)


def analyze_images_batch(paths: list[str], question: str = "Bu gorselleri acikla.", model: str | None = None) -> dict[str, Any]:
    """Wrapper for batch image analysis."""
    if _analyze_images_batch is None:
        return {"error": "Vision Reader modulu yuklenemedi.", "status": "ERROR"}
    return _analyze_images_batch(paths, question=question, model=model)


# ─── Terminal Agent Import ─────────────────────────────────────────────────

try:
    from core.terminal_agent import run_terminal_command as _run_terminal_command
    from core.terminal_agent import run_powershell as _run_powershell
    from core.terminal_agent import analyze_error as _analyze_error
    from core.terminal_agent import get_system_info as _get_system_info
    from core.terminal_agent import read_log_file as _read_log_file
    from core.terminal_agent import list_processes as _list_processes
    from core.terminal_agent import find_process as _find_process
except ImportError:
    _run_terminal_command = None
    _run_powershell = None
    _analyze_error = None
    _get_system_info = None
    _read_log_file = None
    _list_processes = None
    _find_process = None


def run_terminal_command(command: str, timeout: int = 120, cwd: str | None = None) -> dict[str, Any]:
    """Wrapper for terminal command execution."""
    if _run_terminal_command is None:
        return {"error": "Terminal Agent modulu yuklenemedi.", "status": "ERROR"}
    return _run_terminal_command(command, timeout=timeout, cwd=cwd)


def run_powershell(command: str, timeout: int = 120) -> dict[str, Any]:
    """Wrapper for PowerShell command."""
    if _run_powershell is None:
        return {"error": "Terminal Agent modulu yuklenemedi.", "status": "ERROR"}
    return _run_powershell(command, timeout=timeout)


def analyze_error(command: str, error_output: str) -> dict[str, Any]:
    """Wrapper for error analysis."""
    if _analyze_error is None:
        return {"error": "Terminal Agent modulu yuklenemedi.", "status": "ERROR"}
    return _analyze_error(command, error_output)


def get_system_info() -> dict[str, Any]:
    """Wrapper for system info."""
    if _get_system_info is None:
        return {"error": "Terminal Agent modulu yuklenemedi.", "status": "ERROR"}
    return _get_system_info()


def read_log_file(log_path: str, tail_lines: int = 100, pattern: str | None = None) -> dict[str, Any]:
    """Wrapper for log file reading."""
    if _read_log_file is None:
        return {"error": "Terminal Agent modulu yuklenemedi.", "status": "ERROR"}
    return _read_log_file(log_path, tail_lines=tail_lines, pattern=pattern)


def list_processes() -> dict[str, Any]:
    """Wrapper for process listing."""
    if _list_processes is None:
        return {"error": "Terminal Agent modulu yuklenemedi.", "status": "ERROR"}
    return _list_processes()


def find_process(name: str) -> dict[str, Any]:
    """Wrapper for process finding."""
    if _find_process is None:
        return {"error": "Terminal Agent modulu yuklenemedi.", "status": "ERROR"}
    return _find_process(name)


# ─── Code Agent Import ──────────────────────────────────────────────────────

try:
    from core.code_agent import read_code as _read_code
    from core.code_agent import generate_code as _generate_code
    from core.code_agent import explain_code as _explain_code
    from core.code_agent import find_bugs as _find_bugs
    from core.code_agent import write_test as _write_test
    from core.code_agent import run_tests as _run_tests
    from core.code_agent import analyze_project as _analyze_project_code
    from core.code_agent import code_assist as _code_assist
except ImportError:
    _read_code = None
    _generate_code = None
    _explain_code = None
    _find_bugs = None
    _write_test = None
    _run_tests = None
    _analyze_project_code = None
    _code_assist = None


def read_code(path: str, start_line: int = 1, max_lines: int = 500) -> dict[str, Any]:
    """Wrapper for code reading."""
    if _read_code is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _read_code(path, start_line=start_line, max_lines=max_lines)


def generate_code(description: str, language: str = "python", model: str | None = None, context: str = "") -> dict[str, Any]:
    """Wrapper for code generation."""
    if _generate_code is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _generate_code(description, language=language, model=model, context=context)


def explain_code(code: str, language: str = "python", model: str | None = None) -> dict[str, Any]:
    """Wrapper for code explanation."""
    if _explain_code is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _explain_code(code, language=language, model=model)


def find_bugs(code: str, language: str = "python", error_message: str = "", model: str | None = None) -> dict[str, Any]:
    """Wrapper for bug detection."""
    if _find_bugs is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _find_bugs(code, language=language, error_message=error_message, model=model)


def write_test(code: str, language: str = "python", model: str | None = None) -> dict[str, Any]:
    """Wrapper for test writing."""
    if _write_test is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _write_test(code, language=language, model=model)


def run_code_tests(test_path: str = "tests/", command: str = "python -m pytest", timeout: int = 120) -> dict[str, Any]:
    """Wrapper for test running."""
    if _run_tests is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _run_tests(test_path, command=command, timeout=timeout)


def analyze_project_code(project_path: str = ".") -> dict[str, Any]:
    """Wrapper for project analysis."""
    if _analyze_project_code is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _analyze_project_code(project_path)


def code_assist(request: str, code: str = "", language: str = "python", model: str | None = None) -> dict[str, Any]:
    """Wrapper for code assistance."""
    if _code_assist is None:
        return {"error": "Code Agent modulu yuklenemedi.", "status": "ERROR"}
    return _code_assist(request, code=code, language=language, model=model)


# ─── Code Tool Definitions ─────────────────────────────────────────────────
CODE_TOOLS = [
    {"type": "function", "function": {
        "name": "read_code",
        "description": "Kod dosyasini okur ve analiz eder. Python icin AST analizi yapar.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer"},
            "max_lines": {"type": "integer"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "generate_code",
        "description": "LLM ile kod uretir.", "parameters": {"type": "object", "properties": {
            "description": {"type": "string"},
            "language": {"type": "string"},
            "context": {"type": "string"}
        }, "required": ["description"]}}},
    {"type": "function", "function": {
        "name": "explain_code",
        "description": "Kodu aciklar.", "parameters": {"type": "object", "properties": {
            "code": {"type": "string"},
            "language": {"type": "string"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "find_bugs",
        "description": "Kodda hata tespit eder ve duzeltme onerisi sunar.", "parameters": {"type": "object", "properties": {
            "code": {"type": "string"},
            "language": {"type": "string"},
            "error_message": {"type": "string"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "write_test",
        "description": "Verilen kod icin test yazar.", "parameters": {"type": "object", "properties": {
            "code": {"type": "string"},
            "language": {"type": "string"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "run_code_tests",
        "description": "Testleri calistirir ve sonuclari analiz eder.", "parameters": {"type": "object", "properties": {
            "test_path": {"type": "string"},
            "command": {"type": "string"},
            "timeout": {"type": "integer"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "analyze_project_code",
        "description": "Proje yapisini analiz eder (dosya turleri, diller, proje tipi).",
        "parameters": {"type": "object", "properties": {
            "project_path": {"type": "string"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "code_assist",
        "description": "Cok yonlu kod asistani: yazma, aciklama, hata bulma, test yazma.", "parameters": {"type": "object", "properties": {
            "request": {"type": "string"},
            "code": {"type": "string"},
            "language": {"type": "string"}
        }, "required": ["request"]}}},
]

# Code tool'lari TOOLS listesine ekle
TOOLS.extend(CODE_TOOLS)


# ─── Terminal Tool Definitions ─────────────────────────────────────────────
TERMINAL_TOOLS = [
    {"type": "function", "function": {
        "name": "run_terminal_command",
        "description": "Terminal komutu calistirir (CMD/PowerShell). Guvenli komutlar otomatik, tehlikeli komutlar onay gerektirir.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer"},
            "cwd": {"type": "string"}
        }, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "run_powershell",
        "description": "PowerShell komutu calistirir.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer"}
        }, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "analyze_error",
        "description": "Hata ciktisini analiz eder ve cozum onerisi sunar.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "error_output": {"type": "string"}
        }, "required": ["command", "error_output"]}}},
    {"type": "function", "function": {
        "name": "get_system_info",
        "description": "Sistem bilgisi toplar (OS, Python, disk vb.).", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "read_log_file",
        "description": "Log dosyasini okur, filtreler ve son N satiri gosterir.",
        "parameters": {"type": "object", "properties": {
            "log_path": {"type": "string"},
            "tail_lines": {"type": "integer"},
            "pattern": {"type": "string"}
        }, "required": ["log_path"]}}},
    {"type": "function", "function": {
        "name": "list_processes",
        "description": "Calisan process'leri listeler.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "find_process",
        "description": "Belirli bir processi bulur.", "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}
        }, "required": ["name"]}}},
]

# Terminal tool'ları TOOLS listesine ekle
TOOLS.extend(TERMINAL_TOOLS)


# ─── Vision Tool Definitions ───────────────────────────────────────────────
VISION_TOOLS = [
    {"type": "function", "function": {
        "name": "analyze_image",
        "description": "Gorseli analiz eder: metadata, OCR, ve vision model ile aciklama. JPG, PNG, WebP destekler.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "question": {"type": "string"},
            "use_ocr": {"type": "boolean"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "image_to_text",
        "description": "Gorseldeki metinleri cikarir (OCR + Vision).", "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "describe_image",
        "description": "Gorseli aciklar (brief/detailed/very_detailed).", "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "detail_level": {"type": "string", "enum": ["brief", "detailed", "very_detailed"]}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "image_qa",
        "description": "Gorsel hakkinda soru-cevap. Belirli bir soruyu Vision modeline sorar.", "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "question": {"type": "string"}
        }, "required": ["path", "question"]}}},
    {"type": "function", "function": {
        "name": "image_to_memory",
        "description": "Gorsel analiz sonucunu RAG/hafiza sistemine aktarir.", "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "source": {"type": "string"}
        }, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "analyze_images_batch",
        "description": "Birden fazla gorseli toplu analiz eder.", "parameters": {"type": "object", "properties": {
            "paths": {"type": "array", "items": {"type": "string"}},
            "question": {"type": "string"}
        }, "required": ["paths"]}}},
]

# Vision tool'ları TOOLS listesine ekle
TOOLS.extend(VISION_TOOLS)


# ─── Web Research Tool Definitions ─────────────────────────────────────────

WEB_RESEARCH_TOOLS = [
    {"type": "function", "function": {
        "name": "research_topic",
        "description": "Bir konuyu internette kapsamlı şekilde araştırır. Birden fazla kaynak bulur, okur, karşılaştırır ve yapılandırılmış rapor oluşturur.",
        "parameters": {"type": "object", "properties": {
            "topic": {"type": "string", "description": "Araştırma konusu"},
            "max_sources": {"type": "integer", "description": "Maksimum kaynak sayısı (varsayılan: 10)"},
            "save_to_memory": {"type": "boolean", "description": "Sonucu Memory/RAG'a kaydet"}
        }, "required": ["topic"]}}},
    {"type": "function", "function": {
        "name": "quick_research",
        "description": "Hızlı araştırma — max 5 kaynak, memory'ye kaydetmez. Hızlı sonuç gerekirken kullanılır.",
        "parameters": {"type": "object", "properties": {
            "topic": {"type": "string", "description": "Araştırma konusu"}
        }, "required": ["topic"]}}},
    {"type": "function", "function": {
        "name": "research_with_queries",
        "description": "Belirli arama sorgularıyla araştırma yapar. Sorguları siz belirlersiniz.",
        "parameters": {"type": "object", "properties": {
            "queries": {"type": "array", "items": {"type": "string"}, "description": "Arama sorguları listesi"}
        }, "required": ["queries"]}}},
    {"type": "function", "function": {
        "name": "open_and_read_page",
        "description": "Bir web sayfasını açar, okur ve anlamlı içerik çıkarır.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "OKunacak sayfa URL'si"}
        }, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "search_web",
        "description": "DuckDuckGo'da arama yapar ve sonuçları listeler.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Arama terimi"},
            "max_results": {"type": "integer", "description": "Maksimum sonuç sayısı"}
        }, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "extract_page_tables",
        "description": "Bir web sayfasındaki tabloları yapılandırılmış şekilde çıkarır.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "Sayfa URL'si"}
        }, "required": ["url"]}}},
]

TOOLS.extend(WEB_RESEARCH_TOOLS)


# ─── Web Research Wrapper Functions ──────────────────────────────────────────

def _research_topic(topic: str, max_sources: int = 10, save_to_memory: bool = True) -> dict[str, Any]:
    from core.web_research import research_topic as _rt
    return _rt(topic, max_sources=max_sources, save_to_memory=save_to_memory)


def _quick_research(topic: str) -> dict[str, Any]:
    from core.web_research import quick_research as _qr
    return _qr(topic)


def _research_with_queries(queries: list[str]) -> dict[str, Any]:
    from core.web_research import research_with_queries as _rwq
    return _rwq(queries)


def _open_and_read_page(url: str) -> dict[str, Any]:
    from core.web_research import WebExplorer
    explorer = WebExplorer()
    source = explorer.open_page(url)
    return {
        "url": source.url,
        "title": source.title,
        "domain": source.domain,
        "source_type": source.source_type.value,
        "reliability": source.reliability.value,
        "text_length": source.text_length,
        "content": source.content[:10000],
        "tables": source.tables,
        "links_count": len(source.links),
        "error": source.error,
    }


def _search_web(query: str, max_results: int = 8) -> dict[str, Any]:
    from core.web_research import WebExplorer
    explorer = WebExplorer()
    results = explorer.search(query, max_results=max_results)
    return {
        "query": query,
        "results": results,
        "count": len(results),
    }


def extract_page_tables(url: str) -> dict[str, Any]:
    from core.web_research import WebExplorer
    explorer = WebExplorer()
    tables = explorer.extract_tables(url)
    return {
        "url": url,
        "tables": tables,
        "table_count": len(tables),
    }


# ─── Gmail Tool Definitions ──────────────────────────────────────────────────

GMAIL_TOOLS = [
    {"type": "function", "function": {
        "name": "gmail_list_emails",
        "description": "E-posta kutusunu listeler. IMAP kullanarak sunucudan e-posta listesini çeker.",
        "parameters": {"type": "object", "properties": {
            "folder": {"type": "string", "description": "Klasör (varsayılan: INBOX)"},
            "max_count": {"type": "integer", "description": "Maksimum e-posta sayısı"},
            "unread_only": {"type": "boolean", "description": "Yalnızca okunmamış e-postalar"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "gmail_search",
        "description": "E-posta kutusunda gelişmiş arama yapar (gönderen, konu, tarih, anahtar kelime).",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Arama terimi"},
            "sender": {"type": "string", "description": "Gönderen e-posta adresi"},
            "subject": {"type": "string", "description": "Konu filtresi"},
            "folder": {"type": "string"},
            "max_count": {"type": "integer"}
        }, "required": []}}},
    {"type": "function", "function": {
        "name": "gmail_get_email",
        "description": "Tek bir e-postanın tam içeriğini okur.",
        "parameters": {"type": "object", "properties": {
            "uid": {"type": "string", "description": "E-posta UID numarası"},
            "folder": {"type": "string"}
        }, "required": ["uid"]}}},
    {"type": "function", "function": {
        "name": "gmail_list_attachments",
        "description": "Bir e-postanın eklerini listeler.",
        "parameters": {"type": "object", "properties": {
            "uid": {"type": "string", "description": "E-posta UID"},
            "folder": {"type": "string"}
        }, "required": ["uid"]}}},
    {"type": "function", "function": {
        "name": "gmail_summarize",
        "description": "E-postayı Ollama LLM ile özetler.",
        "parameters": {"type": "object", "properties": {
            "uid": {"type": "string", "description": "E-posta UID"},
            "folder": {"type": "string"}
        }, "required": ["uid"]}}},
    {"type": "function", "function": {
        "name": "gmail_draft_reply",
        "description": "E-postaya cevap taslağı oluşturur (GÖNDERMEZ, güvenli).",
        "parameters": {"type": "object", "properties": {
            "uid": {"type": "string", "description": "Cevaplanacak e-posta UID"},
            "reply_body": {"type": "string", "description": "Cevap metni"},
            "folder": {"type": "string"}
        }, "required": ["uid", "reply_body"]}}},
    {"type": "function", "function": {
        "name": "gmail_folder_info",
        "description": "E-posta klasör bilgilerini alır.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
]

TOOLS.extend(GMAIL_TOOLS)


def _gmail_list_emails(folder: str = "INBOX", max_count: int = 20, unread_only: bool = False) -> dict:
    from core.gmail_agent import gmail_list_emails as _g
    return _g(folder=folder, max_count=max_count, unread_only=unread_only)

def _gmail_search(query: str = "", sender: str = "", subject: str = "", folder: str = "INBOX", max_count: int = 20) -> dict:
    from core.gmail_agent import gmail_search as _g
    return _g(query=query, sender=sender, subject=subject, folder=folder, max_count=max_count)

def _gmail_get_email(uid: str, folder: str = "INBOX") -> dict:
    from core.gmail_agent import gmail_get_email as _g
    return _g(uid=uid, folder=folder)

def _gmail_list_attachments(uid: str, folder: str = "INBOX") -> dict:
    from core.gmail_agent import gmail_list_attachments as _g
    return _g(uid=uid, folder=folder)

def _gmail_summarize(uid: str, folder: str = "INBOX") -> dict:
    from core.gmail_agent import gmail_summarize as _g
    return _g(uid=uid, folder=folder)

def _gmail_draft_reply(uid: str, reply_body: str, folder: str = "INBOX") -> dict:
    from core.gmail_agent import gmail_draft_reply as _g
    return _g(uid=uid, reply_body=reply_body, folder=folder)

def _gmail_folder_info() -> dict:
    from core.gmail_agent import gmail_folder_info as _g
    return _g()

def _gmail_send_email(to: str, subject: str, body: str, is_html: bool = False) -> dict:
    """E-posta gonder — UMAY permission onayi gerektirir."""
    if not _approved():
        raise PermissionError(
            "E-posta gonderme icin acik onay gerekir: "
            "UMAY_MODE=auto_fix veya UMAY_APPROVED=true"
        )
    from core.gmail_agent import gmail_send_email as _g
    return _g(to=to, subject=subject, body=body, is_html=is_html)


# Gmail send tool definition
GMAIL_SEND_TOOLS = [
    {"type": "function", "function": {
        "name": "gmail_send_email",
        "description": "E-posta gonderir. ACIK KULLANICI ONAYI GEREKTIRIR. UMAY_MODE=auto_fix veya UMAY_APPROVED=true olmadan calismaz.",
        "parameters": {"type": "object", "properties": {
            "to": {"type": "string", "description": "Alici e-posta adresi"},
            "subject": {"type": "string", "description": "E-posta konusu"},
            "body": {"type": "string", "description": "E-posta icerigi"},
            "is_html": {"type": "boolean", "description": "HTML icerik mi?"}
        }, "required": ["to", "subject", "body"]}}},
]
TOOLS.extend(GMAIL_SEND_TOOLS)


DISPATCH = {
    "list_directory": list_directory, "read_file": read_file,
    "search_files": search_files, "write_file": write_file,
    "run_command": run_command, "run_test_suite": run_test_suite, "git_diff_summary": git_diff_summary, "rollback_backup": rollback_backup, "inspect_project": inspect_project,
    "web_search": web_search, "browser_open": browser_open, "browser_read": browser_read,
    "browser_click": browser_click, "browser_type": browser_type,
    "browser_screenshot": browser_screenshot, "browser_close": browser_close,
    "open_file": open_file, "open_folder": open_folder,
    "open_url": open_url, "open_with_app": open_with_app,
    "read_document": read_document, "scan_directory": scan_directory,
    "search_in_documents": search_in_documents, "document_to_memory": document_to_memory,
    "analyze_image": analyze_image, "image_to_text": image_to_text,
    "describe_image": describe_image, "image_qa": image_qa,
    "image_to_memory": image_to_memory, "analyze_images_batch": analyze_images_batch,
    "run_terminal_command": run_terminal_command, "run_powershell": run_powershell,
    "analyze_error": analyze_error, "get_system_info": get_system_info,
    "read_log_file": read_log_file, "list_processes": list_processes,
    "find_process": find_process,
    "read_code": read_code, "generate_code": generate_code,
    "explain_code": explain_code, "find_bugs": find_bugs,
    "write_test": write_test, "run_code_tests": run_code_tests,
    "analyze_project_code": analyze_project_code, "code_assist": code_assist,
    "research_topic": _research_topic, "quick_research": _quick_research,
    "research_with_queries": _research_with_queries,
    "open_and_read_page": _open_and_read_page, "search_web": _search_web,
    "extract_page_tables": extract_page_tables,
    "gmail_list_emails": _gmail_list_emails, "gmail_search": _gmail_search,
    "gmail_get_email": _gmail_get_email, "gmail_list_attachments": _gmail_list_attachments,
    "gmail_summarize": _gmail_summarize, "gmail_draft_reply": _gmail_draft_reply,
    "gmail_folder_info": _gmail_folder_info, "gmail_send_email": _gmail_send_email,
    "evaluate_expression": evaluate_expression,
    "get_current_time": get_current_time, "get_current_date": get_current_date,
}

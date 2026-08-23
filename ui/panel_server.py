"""
UMAY Kontrol Paneli — Split-Screen Web Arayuzu
Flask + SocketIO ile canli browser gorunumu ve chat
Adres: http://localhost:5001
"""

import os
import sys
import base64
import threading
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# Path
ROOT = Path(__file__).parent.parent
CORE = ROOT / "core"
sys.path.insert(0, str(CORE))

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("UMAY_SECRET_KEY", "change-me-local-only")
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5001", "http://127.0.0.1:5001"], async_mode="threading")

# ─── Host Filesystem Path Resolution + Sandbox ──────────────────────────────
# Windows host user folders are mounted to /host/* in the container.
# This function maps Windows paths to container paths with sandbox security.

_ALLOWED_HOST_ROOTS = ["/host/Desktop", "/host/Documents", "/host/Downloads"]

def _resolve_host_path(path_str: str) -> str | None:
    """Resolve a Windows host path to container path with sandbox security.
    
    Returns:
        Container path if allowed, None if blocked.
    
    Security:
        - Only /host/Desktop, /host/Documents, /host/Downloads are allowed.
        - Path traversal (..) is blocked.
        - Non-existent paths return None.
    """
    if not path_str:
        return None
    
    # Block path traversal
    if ".." in path_str:
        return None
    
    # Map Windows paths to container paths
    _win_to_container = {
        "c:\\users\\isitm\\desktop": "/host/Desktop",
        "c:\\users\\isitm\\documents": "/host/Documents",
        "c:\\users\\isitm\\downloads": "/host/Downloads",
        "c:\\users\\isitm\\masaustu": "/host/Desktop",
        "c:\\users\\isitm\\belgeler": "/host/Documents",
        "c:\\users\\isitm\\indirilenler": "/host/Downloads",
    }
    
    # Normalize path for comparison
    path_lower = path_str.lower().replace("\\\\", "/").replace("\\", "/")
    
    # Check exact mapping first
    for win_path, container_path in _win_to_container.items():
        if path_lower.startswith(win_path):
            # Check if target exists
            target = container_path
            if os.path.exists(target):
                return target
            return None
    
    # Check if path starts with /host/ (already a container path)
    if path_str.startswith("/host/"):
        # Validate against allowed roots
        for root in _ALLOWED_HOST_ROOTS:
            if path_str == root or path_str.startswith(root + "/"):
                if os.path.exists(path_str):
                    return path_str
                return None
        return None
    
    # Not a host path — return as-is (local container path)
    return path_str

# Global durum
browser_agent = None
agent_aktif = False
_browser_lock = threading.Lock()

# Chat session history — persisted in SQLite (core/conversation_store.py),
# keyed by session_id. Previously an in-memory dict (`_chat_sessions`) that
# lost all history on every process restart — see
# docs/development/CHAT_CURRENT_STATE.md section 2 and CHAT_DECISIONS.md
# STEP-01. The three helper functions below keep their original signatures
# and behavior on purpose so nothing else in this file has to change.
from core import conversation_store as _conv_store
from core.task_executor import get_executor, check_pause, check_cancel, TaskCancelledException
_MAX_HISTORY = 20  # max mesaj çifti (40 mesaj) — same window as before

# Image store — hash -> base64 (for vision requests)
_image_store: dict[str, str] = {}


def _get_session_history(session_id: str) -> list[dict]:
    """Get chat history for a session (persisted, survives restart)."""
    return _conv_store.get_history(session_id, max_pairs=_MAX_HISTORY)


def _add_to_history(session_id: str, role: str, content: str):
    """Add a message to session history (persisted)."""
    _conv_store.add_message(session_id, role, content)


def _clear_session(session_id: str):
    """Clear session history (persisted)."""
    _conv_store.clear_conversation(session_id)


def _resolve_image_base64(att: dict) -> str | None:
    """Resolve stored image to base64 for Ollama vision API.
    
    Uses in-memory image_store (populated during attach).
    Falls back to filesystem search.
    """
    import base64 as _b64
    file_hash = att.get("hash", "")
    
    # Fast path: in-memory store
    if file_hash and file_hash in _image_store:
        return _image_store[file_hash]
    
    # Fallback: search uploads directory
    filename = att.get("filename", "")
    uploads_dir = ROOT / "uploads"
    if uploads_dir.exists():
        for month_dir in uploads_dir.iterdir():
            if month_dir.is_dir():
                for f in month_dir.iterdir():
                    if f.is_file() and file_hash and file_hash in f.name:
                        try:
                            data = f.read_bytes()
                            b64 = _b64.b64encode(data).decode()
                            _image_store[file_hash] = b64  # Cache it
                            return b64
                        except Exception:
                            pass
    
    return None


# ─── Ekran Gonderici ─────────────────────────────────────

def ekran_gonder_dongu():
    """Her 1.5 saniyede son screenshot'i panele gonderir.
    Diger kaynaklardan (web research, vision vb.) gelen
    screenshot'lari da yakalar.
    """
    screenshot_dir = ROOT / "logs" / "screenshots"
    son_dosya = None

    while True:
        try:
            dosyalar = sorted(screenshot_dir.glob("*.png"))
            if dosyalar:
                son = dosyalar[-1]
                if son != son_dosya:
                    son_dosya = son
                    try:
                        with open(son, "rb") as f:
                            veri = base64.b64encode(f.read()).decode()
                        socketio.emit("screenshot", {"img": veri, "dosya": son.name})
                    except Exception as e:
                        print(f"[SCREENSHOT] emit hatasi: {e}")
        except Exception:
            pass
        time.sleep(1.5)


def _emit_screenshot(base64_data: str, filename: str = ""):
    """Base64 screenshot verisini dogrudan panele gonderir."""
    if base64_data:
        socketio.emit("screenshot", {"img": base64_data, "dosya": filename})
        print(f"[SOCKET] EVENT=screenshot EMIT=SUCCESS SIZE={len(base64_data)}")


# ─── Log Gonderici ─────────────────────────────────────

def log_gonder_dongu():
    """Her 2 saniyede yeni log satirlarini panele gonderir."""
    log_dosya = ROOT / "logs" / "umay.log"
    son_boyut = 0

    while True:
        try:
            if log_dosya.exists():
                boyut = log_dosya.stat().st_size
                if boyut > son_boyut:
                    with open(log_dosya, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(son_boyut)
                        yeni = f.read()
                    if yeni.strip():
                        socketio.emit("log", {"metin": yeni})
                    son_boyut = boyut
        except Exception:
            pass
        time.sleep(2)


# ─── Telegram Status Gonderici ─────────────────────────

def telegram_status_dongu():
    """Her 5 saniyede Telegram adapter durumunu panele gonderir."""
    while True:
        try:
            status = _get_telegram_status()
            socketio.emit("telegram_status", status)
        except Exception:
            pass
        time.sleep(5)


def _get_telegram_status() -> dict:
    """Telegram adapter durumunu topla."""
    bot_connected = False
    user_connected = False
    try:
        from core.telegram_adapter import get_telegram_adapter
        tg = get_telegram_adapter()
        bot_connected = tg.is_active()
    except Exception:
        pass
    try:
        from core.telegram_user_adapter import get_telegram_user_adapter
        user_tg = get_telegram_user_adapter()
        user_connected = user_tg.is_active()
    except Exception:
        pass
    return {
        "telegram_bot_connected": bot_connected,
        "telegram_user_connected": user_connected,
        "bot_connected": bot_connected,
        "user_connected": user_connected,
    }


# ─── Rotalar ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("panel.html")


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "umay-panel"})


@app.route("/api/git", methods=["POST"])
def siteye_git():
    """Verilen URL'ye gider — tek browser, her navigasyonda screenshot + analiz."""
    global browser_agent, agent_aktif
    veri = request.json
    url = veri.get("url", "")

    def calistir():
        global browser_agent, agent_aktif
        agent_aktif = True
        socketio.emit("durum", {"mesaj": f"Gidiliyor: {url}", "renk": "blue"})

        sys.path.insert(0, str(ROOT / "agents"))
        from browser_agent import BrowserAgent

        # Her istekte yeni browser — Playwright thread bagimliligi nedeniyle
        # onceki browser'i kapat
        with _browser_lock:
            eski = browser_agent
            browser_agent = None
        if eski:
            try:
                eski.kapat()
            except Exception:
                pass

        # Yeni browser baslat
        agent = BrowserAgent(gorunur=False, yavas_mod=False)
        if not agent.baslat():
            socketio.emit("durum", {"mesaj": "Tarayici baslatilamadi", "renk": "red"})
            agent_aktif = False
            return

        with _browser_lock:
            browser_agent = agent

        try:
            # 1) NAVIGATE
            print(f"[BROWSER] Navigate basladi: {url}")
            if not agent.git(url):
                socketio.emit("durum", {"mesaj": f"Sayfa yuklenemedi: {url}", "renk": "red"})
                return

            # 2) SCREENSHOT (bagimsiz — analizden once)
            print("[SCREENSHOT] Aliniyor...")
            screenshot_path, screenshot_b64 = agent.ekran_al_ve_dosyaya_kaydet()
            if screenshot_b64:
                _emit_screenshot(screenshot_b64, os.path.basename(screenshot_path))
                print("[SCREENSHOT] Panele gonderildi")
            else:
                print("[SCREENSHOT] [HATA] Screenshot alinamadi")

            # 3) ANALYSIS (screenshot'tan bagimsiz)
            print("[ANALYSIS] Basladi...")
            analiz = agent.analiz_et()
            socketio.emit("analiz", {
                "baslik": analiz.get("baslik", ""),
                "url": analiz.get("url", ""),
                "linkler": analiz.get("linkler", [])[:5],
                "formlar": analiz.get("formlar", [])[:5],
            })
            socketio.emit("durum", {
                "mesaj": f"Hazir: {analiz.get('baslik', '') or url}",
                "renk": "green"
            })
            print(f"[ANALYSIS] Tamamlandi: {analiz.get('baslik', '')}")
        finally:
            # Browser'i kapat — bir sonraki istek icin temiz baslangic
            try:
                agent.kapat()
            except Exception:
                pass
            with _browser_lock:
                browser_agent = None
            agent_aktif = False

    threading.Thread(target=calistir, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/durdur", methods=["POST"])
def durdur():
    """Agenti durdurur (insan mudahalesi)."""
    global browser_agent
    with _browser_lock:
        if browser_agent:
            browser_agent.durdur()
    socketio.emit("durum", {"mesaj": "DURDURULDU - insan kontrolünde", "renk": "orange"})
    return jsonify({"ok": True})


@app.route("/api/devam", methods=["POST"])
def devam():
    """Duraklatilmis agenti devam ettirir."""
    global browser_agent
    with _browser_lock:
        if browser_agent:
            browser_agent.devam_et()
    socketio.emit("durum", {"mesaj": "Devam ediyor...", "renk": "green"})
    return jsonify({"ok": True})


@app.route("/api/kapat", methods=["POST"])
def kapat():
    """Tarayiciyi kapatir."""
    global browser_agent
    with _browser_lock:
        eski = browser_agent
        browser_agent = None
    if eski:
        try:
            eski.kapat()
        except Exception:
            pass
    socketio.emit("durum", {"mesaj": "Tarayici kapatildi", "renk": "gray"})
    return jsonify({"ok": True})


from core.identity import UMAY_SYSTEM


@app.route("/api/telegram_status")
def telegram_status_api():
    """Telegram adapter durumunu dondurur."""
    return jsonify(_get_telegram_status())


@app.route("/api/chat/attach", methods=["POST"])
def chat_attach():
    """Attach a file to chat — processes via Attachment Engine."""
    from core.attachment_engine import process_upload

    if "file" not in request.files:
        return jsonify({"error": "Dosya bulunamadı"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Dosya adı boş"}), 400

    file_data = f.read()
    result = process_upload(file_data, f.filename, source="chat")

    if not result.get("ok"):
        return jsonify(result), 400

    att = result["attachment"]
    # Store image base64 in memory for vision requests
    if att["type"] == "image":
        # Read the uploaded file data and encode as base64
        try:
            import base64 as _b64
            b64 = _b64.b64encode(file_data).decode()
            _image_store[att["hash"]] = b64
        except Exception:
            pass
    # Don't send large base64 back to frontend — only flag it
    response = {
        "ok": True,
        "filename": att["filename"],
        "ext": att["ext"],
        "type": att["type"],
        "icon": att["icon"],
        "content": att.get("content", "")[:2000],  # Preview for frontend
        "has_content": bool(att.get("content")),
        "is_vision": att["type"] == "image",
        "size": att["size"],
        "hash": att.get("hash", ""),
    }
    return jsonify(response)


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """File upload endpoint."""
    if "file" not in request.files:
        return jsonify({"error": "Dosya bulunamadı"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Dosya adı boş"}), 400
    try:
        from core.file_manager import save_upload
        result = save_upload(f.stream, f.filename, source="web")
        return jsonify({"ok": True, "file": result})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/uploads", methods=["GET"])
def list_uploads():
    """List recent uploads."""
    from core.file_manager import get_upload_history
    return jsonify({"uploads": get_upload_history()})


@app.route("/api/chat/clear", methods=["POST"])
def chat_clear():
    """Clear chat session history."""
    veri = request.json or {}
    session_id = veri.get("session_id", "default")
    _clear_session(session_id)
    return jsonify({"ok": True, "message": "Session cleared"})


def _format_tool_result(last_result, tool_name=None):
    """Format tool result for display — no raw JSON dumps."""
    import json as _json
    try:
        rdata = _json.loads(last_result) if isinstance(last_result, str) else last_result
    except Exception:
        # Not JSON — return as-is (truncated)
        return str(last_result)[:1000] if last_result else "Sonuc bos."

    if not isinstance(rdata, dict):
        return str(rdata)[:1000]

    # Web search results → markdown links
    if "results" in rdata and isinstance(rdata["results"], list):
        results = rdata["results"]
        query = rdata.get("query", "")
        count = len(results)
        listing = chr(10).join([
            "  " + str(i+1) + ". [" + res.get("title", "") + "](" + res.get("href", "") + ")"
            for i, res in enumerate(results[:30])
        ])
        return chr(128269) + " " + str(count) + " arama sonucu (" + query + "):" + chr(10) + chr(10) + listing

    # Terminal/command result
    if "stdout" in rdata:
        stdout = rdata.get("stdout", "")[:800]
        stderr = rdata.get("stderr", "")
        rc = rdata.get("returncode", "?")
        cmd = rdata.get("command", "")
        out = "Konsol cikti (" + cmd + "):" + chr(10) + chr(10)
        out += "```" + chr(10) + stdout + chr(10) + "```"
        if stderr:
            out += chr(10) + chr(10) + "Hata:" + chr(10) + "```" + chr(10) + stderr[:300] + chr(10) + "```"
        return out

    # Time result
    if "time" in rdata:
        return "Saat: " + str(rdata.get("time", ""))

    # Calculator result
    if "result" in rdata:
        return "Sonuc: " + str(rdata["result"])

    # Date result
    if "date" in rdata:
        return "Tarih: " + str(rdata["date"])

    # File listing
    if "entries" in rdata:
        entries = rdata["entries"]
        count = rdata.get("count", len(entries))
        listing = chr(10).join(["  " + e["path"] + " (" + e["type"] + ")" for e in entries[:20]])
        return str(count) + " dosya/klasor bulundu:" + chr(10) + listing

    # File content
    if "content" in rdata:
        content = rdata["content"][:800]
        return "Dosya icerigi:" + chr(10) + "```" + chr(10) + content + chr(10) + "```"

    # Browser page content
    if "url" in rdata and "text" in rdata:
        text = rdata.get("text", "")[:600]
        url = rdata.get("url", "")
        if text:
            return "Sayfa icerigi [" + url + "](" + url + "):" + chr(10) + chr(10) + text
        else:
            return "Sayfa acildi: [" + url + "](" + url + ")"

    # Fallback — show keys only, not full JSON
    keys = list(rdata.keys())
    return "Sonuc (" + ", ".join(keys) + "): " + str(rdata)[:500]


# ─── STEP-05: Background Chat Execution ──────────────────────────────────────

def execute_chat_task(task_id, session_id, soru, attachments, *, on_status=None, on_complete=None, on_error=None, model_override="auto", mode="auto"):
    """Background chat execution — runs inside TaskExecutor thread.

    Contains the full STEP-04 chat logic (tool calling, vision routing,
    token budget, context compression, failure recovery) with cooperative
    pause/cancel checkpoints injected at safe points (before each model call).

    Called by TaskExecutor.submit() in a background thread.
    """
    from core.engine import chat as umay_chat, resolve_model
    from core.router import model_sec
    from core.agent_tools import TOOLS, DISPATCH
    from core.agent import (
        _parse_tool_calls, _assistant_tool_message,
        _tool_messages, _bounded_tool_result,
    )
    from core.identity import UMAY_SYSTEM as _UMAY_SYSTEM, CHAT_IDENTITY as _CHAT_IDENTITY
    from core.utils.logger import log

    # ── Intent Router entegrasyonu ──────────────────────────────────────
    try:
        from core.intent_router import classify_intent, get_available_tools as _intent_tools, Intent
        _intent = classify_intent(soru)
        _intent_tools_list = _intent_tools(_intent)
    except ImportError:
        _intent = None
        _intent_tools_list = None

    t_start = time.time()

    # ── TOOL EXECUTION LOGGING ─────────────────────────────────────────
    def _tool_trace(tool_name, tool_input, tool_result, tool_error, duration_ms):
        """Structured log for every tool call."""
        import json as _j
        trace = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "task_id": task_id,
            "session_id": session_id,
            "intent": _intent.value if _intent else None,
            "mode": mode,
            "tool": tool_name,
            "input": str(tool_input)[:300],
            "status": "ERROR" if tool_error else "OK",
            "error": str(tool_error)[:200] if tool_error else None,
            "duration_ms": round(duration_ms),
            "result_preview": str(tool_result)[:300] if tool_result else None,
        }
        log(f"[TOOL_TRACE] {_j.dumps(trace, ensure_ascii=False)}")

    if on_status:
        on_status(task_id, "thinking", "Düşüniyor...")

    # Initialize defaults — respect user's model/mode selection
    model = model_override if model_override and model_override != "auto" else None
    gorev = "chat"

    # ── MODE ROUTING ──
    # Check internet connectivity for ONLINE/AUTO mode
    _internet_ok = True
    try:
        import urllib.request as _urlreq
        _urlreq.urlopen("https://www.google.com", timeout=3)
    except Exception:
        _internet_ok = False

    # ── MODE POLICY ──
    MODE_POLICY = {
        "local":  {"web_allowed": False, "terminal_allowed": True},
        "online": {"web_allowed": True,  "terminal_allowed": True},
        "auto":   {"web_allowed": True,  "terminal_allowed": True},
    }
    policy = MODE_POLICY.get(mode, MODE_POLICY["auto"])

    # LOCAL mode: web research not available, use knowledge response
    if not policy["web_allowed"] and _intent == Intent.WEB:
        _intent = Intent.KNOWLEDGE
        _intent_tools_list = None
        if on_status:
            on_status(task_id, "info", "LOCAL modda web araması yapılamaz")
    # ONLINE mode but no internet: fall back to local
    elif mode == "online" and not _internet_ok:
        mode = "local"
        if on_status:
            on_status(task_id, "warning", "İnternet bağlantısı yok — LOCAL moda düşüldü")

    # Check if any attachment is an image -> route to vision model
    has_image = any(a.get("is_vision") or a.get("type") == "image" for a in attachments)
    if has_image:
        vision_model = resolve_model("vision")
        if vision_model:
            model = vision_model
            gorev = "vision"
        else:
            attachments = [a for a in attachments if a.get("type") != "image"]
            has_image = False
            if on_status:
                on_status(task_id, "warning", "Vision model bulunamadı.")

    # Router ile gorev ve model sec (if not overridden by vision)
    t_router = time.time()
    if gorev != "vision":
        if _intent is not None and _intent_tools_list is not None:
            # Intent router tool kullanacaksa ona göre model seç
            # MODE-AWARE: LOCAL mode sadece local model kullanır
            if mode == "local":
                # LOCAL: sadece local model, online provider kullanma
                model = resolve_model("chat")
                gorev = "chat"
            else:
                # AUTO/ONLINE: full routing
                model, gorev = model_sec(soru)
                model = model or resolve_model("chat")
        elif _intent is not None and _intent in (Intent.CHAT, Intent.KNOWLEDGE):
            # Basit sohbet/bilgi → chat model, tool yok
            gorev = "chat"
            model = resolve_model("chat")
        else:
            model, gorev = model_sec(soru)
            model = model or resolve_model("chat")
    t_router_done = time.time()

    # Tool calling: Intent Router'a göre tool seçimi
    if _intent_tools_list is not None:
        use_tools = True
        # Intent-based tool listesi kullan
        active_tools = [t for t in TOOLS if t["function"]["name"] in _intent_tools_list]
    elif gorev in ("coding", "agent"):
        use_tools = True
        active_tools = TOOLS
    else:
        use_tools = False
        active_tools = None

    # System prompt seçimi: CHAT/KNOWLEDGE intent'leri için CHAT_IDENTITY kullan
    if _intent in (Intent.CHAT, Intent.KNOWLEDGE):
        _system_prompt = _CHAT_IDENTITY
    else:
        _system_prompt = _UMAY_SYSTEM

    # ── DIRECT TOOL EXECUTION (TIME/CALCULATOR/FILE/DOCUMENT/WEB/TERMINAL) ──
    # These tools are deterministic and don't need LLM involvement
    log(f"[DEBUG-ATTACH] intent={_intent}, tools={_intent_tools_list}, has_image={has_image}, attachments_len={len(attachments)}, attachments_bool={bool(attachments)}")
    if _intent in (Intent.TIME, Intent.CALCULATOR, Intent.FILE, Intent.DOCUMENT, Intent.WEB, Intent.TERMINAL) and _intent_tools_list and not has_image and not attachments:
        try:
            from core.agent_tools import DISPATCH as _DISPATCH
            tool_results = []
            for tool_name in _intent_tools_list:
                if tool_name in _DISPATCH:
                    t_tool_start = time.time()
                    # Determine args based on intent
                    tool_args = {}
                    if _intent == Intent.TIME:
                        # TIME tools: get_current_time needs timezone, get_current_date needs nothing
                        if tool_name == "get_current_time":
                            tool_args = {"timezone": "Europe/Istanbul"}
                        # get_current_date takes no required args
                    elif _intent == Intent.CALCULATOR:
                        # Extract math expression from message
                        import re as _re

                        # 1. Try Turkish natural language → math conversion
                        _soru_lower_calc = soru.lower().strip()
                        _calc_expr = None

                        # "X in karesi" → X**2 (apostrophe between digit and suffix)
                        _m = _re.search(r"(\d+)[\x27'\s]*(?:nin|nın|ün|ün|in|in)\s*karesi(?:ni)?", _soru_lower_calc)
                        if _m:
                            _calc_expr = f"{_m.group(1)}**2"

                        # "X in kupu" → X**3 (apostrophe between digit and suffix)
                        if not _calc_expr:
                            _m = _re.search(r"(\d+)[\x27'\s]*(?:nin|nın|ün|ün|in|in)\s*(?:k[üu]p[üu]n[üu]|k[üu]p[üu])", _soru_lower_calc)
                            if _m:
                                _calc_expr = f"{_m.group(1)}**3"

                        # "X ile Y topla" / "X i Y ye topla" → X+Y
                        if not _calc_expr:
                            _m = _re.search(r'(\d+)\s*(?:ile|i|yi|yı)\s*(\d+)\s*topla', _soru_lower_calc)
                            if _m:
                                _calc_expr = f"{_m.group(1)}+{_m.group(2)}"

                        # "X den Y cikar" → X-Y
                        if not _calc_expr:
                            _m = _re.search(r'(\d+)\s*den\s*(\d+)\s*(?:c[iı]kar|c[iı]kart)', _soru_lower_calc)
                            if _m:
                                _calc_expr = f"{_m.group(1)}-{_m.group(2)}"

                        # "X ile Y carp" → X*Y
                        if not _calc_expr:
                            _m = _re.search(r'(\d+)\s*(?:ile|i|yi|yı)\s*(\d+)\s*(?:[cç][aı]rp)', _soru_lower_calc)
                            if _m:
                                _calc_expr = f"{_m.group(1)}*{_m.group(2)}"

                        # "X u Y e bol" → X/Y (optional 'e' before bol)
                        if not _calc_expr:
                            _m = _re.search(r'(\d+)\s*(?:[üu]|yi|yı)\s*(\d+)\s*(?:e\s*)?b[öo]l', _soru_lower_calc)
                            if _m:
                                _calc_expr = f"{_m.group(1)}/{_m.group(2)}"

                        if _calc_expr:
                            tool_args = {"expression": _calc_expr}
                        else:
                            # 2. Try direct math expression like 9*8, 3+5, 9/1*2-3+4
                            math_match = _re.search(r'([\d]+\s*[+\-*/÷×^]\s*[\d]+[\s+\-*/÷×^\d]*)', soru)
                            if math_match:
                                tool_args = {"expression": math_match.group(1).strip()}
                            else:
                                # 3. Fallback: strip non-math characters
                                tool_args = {"expression": _re.sub(r'[^\d+\-*/().^\s]', '', soru).strip()}
                    elif _intent == Intent.FILE:
                        # Only run appropriate tool based on message keywords
                        _soru_lower_file = soru.lower()
                        _is_list = any(w in _soru_lower_file for w in ['listele', 'listele', 'goster', 'göster', 'icerik', 'içerik', 'ne var'])
                        _is_read = any(w in _soru_lower_file for w in ['oku', 'okuma', 'ac', 'aç', 'icerigi', 'içeriği'])
                        _is_search = any(w in _soru_lower_file for w in ['ara', 'bul', 'search', 'find'])
                        # Skip tools that don't match the message intent
                        if _is_list and tool_name not in ('list_directory', 'scan_directory'):
                            continue
                        if _is_read and tool_name not in ('read_file', 'read_document'):
                            continue
                        if _is_search and tool_name not in ('search_files', 'search_in_documents'):
                            continue
                        if tool_name == "list_directory":
                            # Extract path from message or use workspace
                            import re as _re
                            _resolved_path = None
                            # Try Windows absolute path first
                            path_match = _re.search(r'[A-Za-z]:\\[^\s"\'<>]+', soru)
                            if path_match:
                                _resolved_path = _resolve_host_path(path_match.group(1))
                            if not _resolved_path:
                                # Resolve common Turkish folder names to host paths
                                _soru_lower = soru.lower()
                                _folder_map = {
                                    'masaüstü': '/host/Desktop', 'masaustu': '/host/Desktop',
                                    'masaüstündeki': '/host/Desktop', 'masaustundeki': '/host/Desktop',
                                    'masaüstünü': '/host/Desktop', 'masaustunu': '/host/Desktop',
                                    'masaüstünde': '/host/Desktop', 'masaustunde': '/host/Desktop',
                                    'belgeler': '/host/Documents', 'belgeleri': '/host/Documents',
                                    'belgelerdeki': '/host/Documents',
                                    'indirilenler': '/host/Downloads', 'downloads': '/host/Downloads',
                                    'desktop': '/host/Desktop', 'documents': '/host/Documents',
                                }
                                for key, container_path in _folder_map.items():
                                    if key in _soru_lower:
                                        if os.path.exists(container_path):
                                            _resolved_path = container_path
                                        break
                            if _resolved_path:
                                tool_args = {"path": _resolved_path}
                            else:
                                tool_args = {"path": "."}
                        elif tool_name == "read_file":
                            # Try to find a file path in the message
                            import re as _re
                            file_match = _re.search(r'[A-Za-z]:\\[^\s"\'<>]+\.\w+', soru)
                            if file_match:
                                tool_args = {"path": file_match.group(1)}
                            else:
                                continue  # Skip if no file path found
                        elif tool_name == "search_files":
                            # Extract search pattern from message
                            tool_args = {"pattern": soru, "path": "."}
                    elif _intent == Intent.DOCUMENT:
                        if tool_name == "read_document":
                            import re as _re
                            doc_match = _re.search(r'[A-Za-z]:\\[^\s"\'<>]+\.\w+', soru)
                            if doc_match:
                                tool_args = {"path": doc_match.group(1)}
                            else:
                                continue
                        elif tool_name == "scan_directory":
                            tool_args = {"path": "."}
                    elif _intent == Intent.WEB:
                        if tool_name == "web_search":
                            # Sorudan arama sorgusunu çıkar
                            import re as _re
                            _fillers_re = r"^(internette|webde|web'de|google'da|google'de|şeklinde|araştır|ğağıt)\s+"
                            _trailing_re = r"\s+(ara|bul|şeklinde|araştır|istiyorum|edebilirim|yap|mı?)?$"
                            _query = _re.sub(_fillers_re, "", soru, flags=_re.IGNORECASE).strip()
                            _query = _re.sub(_trailing_re, "", _query, flags=_re.IGNORECASE).strip()
                            if not _query or len(_query) < 3:
                                _query = soru
                            tool_args = {"query": _query, "max_results": 50}
                        elif tool_name in ("browser_open", "browser_read", "research_topic", "quick_research", "search_web", "open_and_read_page", "research_with_queries"):
                            continue  # Sadece web_search direct — digerleri LLM'e biraksin
                    elif _intent == Intent.TERMINAL:
                        if tool_name == "run_command":
                            import re as _re
                            _cmd = soru.strip()
                            # Komut prefix/suffix temizleme
                            _cleanup_patterns = [
                                r'^(cmdde|cmd de|terminalde|terminal de|powershellde)\s*',
                                r'\s*(komutunu|komutu|komut)\s*(calistir|calıstır|çalıştır|calıstır)?\s*$',
                                r'\s*(calistir|calıstır|çalıştır|calıstır)\s*$',
                            ]
                            for _pat in _cleanup_patterns:
                                _cmd = _re.sub(_pat, '', _cmd, flags=_re.IGNORECASE).strip()
                            if not _cmd:
                                _cmd = 'dir'  # Fallback
                            tool_args = {"command": _cmd}
                        elif tool_name == "run_powershell":
                            continue  # Sadece run_command — powershell gereksiz
                    try:
                        tool_result = _DISPATCH[tool_name](**tool_args)
                        t_tool_done = time.time()
                        tool_results.append({
                            "tool": tool_name,
                            "result": tool_result,
                            "duration": round(t_tool_done - t_tool_start, 2),
                            "status": "PASS"
                        })
                    except Exception:
                        continue  # Skip tools that fail for lack of args
            # Build response from tool results
            if tool_results:
                result_parts = []
                for tr in tool_results:
                    r = tr["result"]
                    if "formatted" in r: result_parts.append(r["formatted"])
                    elif "time" in r: result_parts.append(f"Saat: {r['time']}")
                    elif "result" in r: result_parts.append(f"Sonuc: {r['result']}")
                    elif "date" in r: result_parts.append(f"Tarih: {r['date']}")
                    elif "entries" in r:
                        # File listing
                        entries = r["entries"]
                        count = r.get("count", len(entries))
                        listing = "\n".join([f"  {e['path']} ({e['type']})" for e in entries[:20]])
                        result_parts.append(f"{count} dosya/klasor bulundu:\n{listing}")
                    elif "content" in r:
                        # File content
                        content = r["content"][:500]
                        result_parts.append(f"Dosya icerigi:\n{content}")
                    elif "matches" in r:
                        # Search results
                        matches = r["matches"]
                        result_parts.append(f"{len(matches)} eslesme bulundu")
                    elif "results" in r and isinstance(r["results"], list):
                        import sys as _dbg2; print(f"[DEBUG-WEB] Found web results: {len(r.get('results', []))} items, tool={tr.get('tool')}", file=_dbg2.stderr)
                        # Web search results -- format as clickable markdown links
                        results = r["results"]
                        count = r.get("count", len(results))
                        query = r.get("query", soru)
                        # Build markdown links for LLM (up to 50 results)
                        results_text = "Arama sorgusu: " + query + chr(10) + chr(10) + "Bulunan sonuclar (linkler dahil):" + chr(10)
                        for i, res in enumerate(results[:50]):
                            title = res.get("title", "")
                            href = res.get("href", "")
                            results_text += str(i+1) + ". [" + title + "](" + href + ")" + chr(10)
                        # LLM: analyze results and include clickable links in response
                        try:
                            _llm_prompt = ("Sen UMAY'sin. Asagidaki web arama sonuclarini analiz et ve kullanicinin sorusuna gore cevap hazirla." + chr(10) + chr(10) +
                                "ZORUNLU KURAL: Asagidaki sonuclardaki TUM [baslik](url) formatindaki linkleri cevabina MUTLAKA dahil et." + chr(10) +
                                "En az 5-10 farkli linki [baslik](url) formatinda cevabina yaz." + chr(10) +
                                "Ornek: [Haber Basligi](https://haber.com) seklinde yaz." + chr(10) + chr(10) +
                                "Kullanici sorusu: " + soru + chr(10) + chr(10) + results_text + chr(10) + chr(10) +
                                "Bu sonuclara gore kisa ve anlamlı bir cevap hazirla. En az 5-10 kaynagi [baslik](url) formatinda belirt.")
                            _llm_result = umay_chat([{"role": "user", "content": _llm_prompt}], model=resolve_model("chat"))
                            if isinstance(_llm_result, dict):
                                _llm_msg = _llm_result.get("message", {})
                                cevap = _llm_msg.get("content", "") if isinstance(_llm_msg, dict) else str(_llm_result)
                            else:
                                cevap = str(_llm_result)
                        except Exception as _llm_err:
                            # Fallback: markdown links without LLM
                            listing = chr(10).join(["  " + str(i+1) + ". [" + res.get("title", "") + "](" + res.get("href", "") + ")" for i, res in enumerate(results[:50])])
                            cevap = "🔍 " + str(count) + " arama sonucu (" + query + "):" + chr(10) + chr(10) + listing
                        # Append clickable results list below LLM answer
                        import sys as _dbg; print(f"[DEBUG] LLM cevap length: {len(cevap)}, appending results...", file=_dbg.stderr)
                        _results_listing = chr(10) + chr(10) + "---" + chr(10) + chr(10)
                        _results_listing += "🔍 " + str(count) + " arama sonucu:" + chr(10) + chr(10)
                        for i, res in enumerate(results[:30]):
                            _title = res.get("title", "")
                            _href = res.get("href", "")
                            _results_listing += str(i+1) + ". [" + _title + "](" + _href + ")" + chr(10)
                        cevap = cevap + _results_listing
                        # Direkt cevap olarak don
                        t_end = time.time()
                        latency = {"total": round(t_end - t_start, 2), "router": round(t_router_done - t_router, 3), "model": 0}
                        _add_to_history(session_id, "user", soru)
                        _add_to_history(session_id, "assistant", cevap)
                        resp_data = {"cevap": cevap, "model": "direct", "gorev": "web", "latency": latency, "mode": mode}
                        if tool_results:
                            resp_data["tool"] = tool_results[0]["tool"]
                            resp_data["tool_status"] = "PASS"
                        if on_complete:
                            on_complete(task_id, resp_data)
                        return
                    elif "url" in r and "text" in r:
                        # Browser open result
                        text = r.get("text", "")[:500]
                        if text:
                            result_parts.append(f"📄 Sayfa icerigi ({r.get('url', '')}):\n{text}")
                        else:
                            result_parts.append(f"📄 Sayfa acildi: {r.get('url', '')}")
                    elif "file_count" in r:
                        # Document/Directory scan — show summary + top files
                        fc = r['file_count']
                        tc = r.get('type_counts', {})
                        top_files = r.get('files', [])[:10]
                        type_summary = ", ".join([f"{v} {k}" for k, v in sorted(tc.items(), key=lambda x: -x[1])[:5]])
                        listing = "\n".join([f"  {f.get('name', f.get('path', ''))} ({f.get('type', '')})" for f in top_files])
                        result_parts.append(f"{fc} dosya bulundu ({type_summary}):\n{listing}")
                    elif "results" in r and isinstance(r["results"], list):
                        # Document search
                        results = r["results"]
                        result_parts.append(f"{len(results)} sonuc bulundu")
                    elif "stdout" in r:
                        # Terminal/command result
                        _ts_stdout = r.get("stdout", "")[:800]
                        _ts_stderr = r.get("stderr", "")
                        _ts_cmd = r.get("command", "")
                        _ts_out = "Konsol cikti (" + _ts_cmd + "):" + chr(10) + chr(10) + "```" + chr(10) + _ts_stdout + chr(10) + "```"
                        if _ts_stderr:
                            _ts_out += chr(10) + chr(10) + "Hata:" + chr(10) + "```" + chr(10) + _ts_stderr[:300] + chr(10) + "```"
                        result_parts.append(_ts_out)
                    elif "os" in r and "platform" in r:
                        # System info
                        result_parts.append("Sistem: " + r.get("os","?") + " / " + r.get("platform","?") + " | Python: " + str(r.get("python_version","?"))[:30] + " | CWD: " + r.get("cwd","?"))
                    elif "output" in r and "status" in r:
                        # Process list
                        result_parts.append("Aktif surecler:" + chr(10) + chr(10) + "```" + chr(10) + r.get("output","")[:500] + chr(10) + "```")
                    else:
                        result_parts.append(str(r)[:300])
                cevap = "\n".join(result_parts)
                t_end = time.time()
                latency = {
                    "total": round(t_end - t_start, 2),
                    "router": round(t_router_done - t_router, 3),
                    "model": 0,
                    "tool": tool_results[0]["duration"] if tool_results else 0,
                }
                _add_to_history(session_id, "user", soru)
                _add_to_history(session_id, "assistant", cevap)
                resp_data = {
                    "cevap": cevap,
                    "model": "direct",
                    "gorev": _intent.value,
                    "latency": latency,
                    "tool": tool_results[0]["tool"] if tool_results else None,
                    "tool_status": "PASS",
                    "tool_result": str(tool_results[0]["result"])[:200] if tool_results else None,
                    "mode": mode,
                }
                if on_complete:
                    on_complete(task_id, resp_data)
                return
        except Exception as direct_exc:
            # Fall through to normal LLM path
            pass

    # Build context from attachments
    from core.attachment_engine import build_chat_context
    att_context = build_chat_context(attachments, soru)

    # Session history — conversation context korunur
    history = _get_session_history(session_id)
    messages = [
        {"role": "system", "content": _system_prompt},
        *history,
        {"role": "user", "content": att_context}
    ]

    # STEP-04.3: Pre-flight token budget check
    from core.token_budget import estimate_usage, check_budget
    preflight_usage = estimate_usage(messages)
    preflight_check = check_budget(preflight_usage)
    if preflight_check.status != "OK":
        if on_status:
            on_status(task_id, "budget_warning",
                     f"Token bütçesi {preflight_check.status}: ~{preflight_check.used_tokens}/{preflight_check.limit_tokens}",
                     budget=preflight_check.as_dict())

    # STEP-04.4: Context compression
    from core.context_compression import compress_context
    compression_result = compress_context(messages)
    if compression_result.was_compressed:
        messages = compression_result.compressed_messages
        if on_status:
            on_status(task_id, "context_compressed",
                     f"Bağlam sıkıştırıldı: {compression_result.original_count} → {compression_result.compressed_count}")

    # If vision, find the stored image and read its base64
    vision_image = None
    if has_image:
        for a in attachments:
            if a.get("is_vision") or a.get("type") == "image":
                vision_image = _resolve_image_base64(a)
                break

    if has_image and vision_image:
        # ── VISION PATH ──
        if on_status:
            on_status(task_id, "calling_model", f"Görsel analiz modeli çağrılıyor ({model})...")

        # Cooperative pause/cancel checkpoint — before model call
        check_cancel(task_id)
        check_pause(task_id)

        t_model_start = time.time()
        try:
            import requests as _req
            from core.engine import OLLAMA_URL

            # STEP-04.5 fix: use att_context (not raw soru)
            vision_msgs = [
                {"role": "system", "content": _UMAY_SYSTEM},
                {"role": "user", "content": att_context, "images": [vision_image]}
            ]
            r = _req.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": model, "messages": vision_msgs, "stream": False},
                timeout=180,
            )
            t_model_done = time.time()
            if r.ok:
                vision_resp = r.json()
                cevap = vision_resp.get("message", {}).get("content", "Görsel analiz yapılamadı.")
                from core.token_budget import usage_from_ollama_response
                vision_usage = usage_from_ollama_response(vision_resp)
            else:
                cevap = f"Vision model hatası: HTTP {r.status_code}"
        except Exception as ve:
            t_model_done = time.time()
            cevap = f"Görsel analiz hatası: {ve}"
            vision_usage = None
            vision_error = True

        t_end = time.time()
        latency = {
            "total": round(t_end - t_start, 2),
            "router": round(t_router_done - t_router, 3),
            "model": round(t_model_done - t_model_start, 2),
        }
        is_vision_error = 'vision_error' in dir() and vision_error
        _add_to_history(session_id, "user", soru)
        _add_to_history(session_id, "assistant", cevap)
        resp_data = {"cevap": cevap, "model": model, "gorev": gorev, "latency": latency}
        if vision_usage:
            resp_data["usage"] = vision_usage.as_dict()
        if is_vision_error:
            resp_data["error"] = True
        if on_complete:
            on_complete(task_id, resp_data)

    elif use_tools:
        # ── TOOL CALLING PATH ──
        if on_status:
            on_status(task_id, "calling_model", f"Model çağrılıyor ({model or 'auto'})...")

        # Cooperative pause/cancel checkpoint — before model call
        check_cancel(task_id)
        check_pause(task_id)

        t_model_start = time.time()
        try:
            result = umay_chat(messages, model=model, tools=active_tools if use_tools else None, mode=mode)
        except Exception as tool_exc:
            t_model_done = time.time()
            if on_status:
                on_status(task_id, "error", f"Tool model hatası: {tool_exc}")
            _add_to_history(session_id, "user", soru)
            _add_to_history(session_id, "assistant", f"[Hata: {tool_exc}]")
            if on_error:
                on_error(task_id, {"error": str(tool_exc)})
            return
        t_model_done = time.time()
        msg = result.get("message", {}) if isinstance(result, dict) else {}
        tool_usage = result.get("usage") if isinstance(result, dict) else None
        tool_calls = _parse_tool_calls(msg)
        last_tool_name = None
        last_tool_status = None
        last_tool_duration = None
        last_tool_result = None

        if tool_calls:
            for tc in tool_calls:
                func_name = tc.get("function", {}).get("name", "unknown")
                last_tool_name = func_name
                if on_status:
                    on_status(task_id, "tool_running", f"Tool çalışıyor: {func_name}")

            messages.append(_assistant_tool_message(tool_calls))
            tool_msgs = _tool_messages(tool_calls)
            messages.extend(tool_msgs)
            # Extract tool result info
            if tool_msgs:
                last_tool_result_raw = tool_msgs[-1].get("content", "")
                last_tool_result = last_tool_result_raw[:200] if last_tool_result_raw else None
                last_tool_status = "PASS"

            if on_status:
                on_status(task_id, "tool_done", "Tool tamamlandı, yanıt oluşturuluyor...")

            # Cooperative pause/cancel checkpoint — after tool execution
            check_cancel(task_id)
            check_pause(task_id)

            last_result = tool_msgs[-1].get("content", "") if tool_msgs else ""
            try:
                import json as _json
                rdata = _json.loads(last_result) if isinstance(last_result, str) else last_result
                if isinstance(rdata, dict) and rdata.get("status") == "OK":
                    lines = rdata.get("lines", [])
                    if lines:
                        cevap = "Dosyanin istenen satirlari:\n" + "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
                    else:
                        cevap = f"Dosya okundu: {rdata.get('shown_lines', '?')} satir gosterildi."
                else:
                    # Smart formatting based on result type
                    cevap = _format_tool_result(last_result, last_tool_name)
            except Exception:
                cevap = _format_tool_result(last_result, last_tool_name)
        else:
            cevap = msg.get("content", "") if msg else str(result)

        t_end = time.time()
        latency = {
            "total": round(t_end - t_start, 2),
            "router": round(t_router_done - t_router, 3),
            "model": round(t_model_done - t_model_start, 2),
        }
        _add_to_history(session_id, "user", soru)
        _add_to_history(session_id, "assistant", cevap)
        resp_data = {"cevap": cevap, "model": model, "gorev": gorev, "latency": latency}
        if last_tool_name:
            resp_data["tool"] = last_tool_name
            resp_data["tool_status"] = last_tool_status or "PASS"
            resp_data["tool_result"] = last_tool_result
        if tool_usage:
            resp_data["usage"] = tool_usage
        if on_complete:
            on_complete(task_id, resp_data)

    else:
        # ── SIMPLE CHAT PATH (no tools) ──
        if on_status:
            on_status(task_id, "calling_model", f"Sohbet modeli çağrılıyor ({model or 'auto'})...")

        # Cooperative pause/cancel checkpoint — before model call
        check_cancel(task_id)
        check_pause(task_id)

        t_model_start = time.time()
        user_content = att_context if attachments else soru
        messages[-1] = {"role": "user", "content": user_content}

        # STEP-04.6: Wrap model call with failure recovery
        from core.failure_recovery import with_recovery, graceful_error_response
        recovery = with_recovery(umay_chat, messages, model=model)
        t_model_done = time.time()

        if not recovery.success:
            if on_status:
                on_status(task_id, "error", f"Model hatası ({recovery.attempts} deneme)")
            _add_to_history(session_id, "user", soru)
            _add_to_history(session_id, "assistant", "[Hata: model yanıt üretemedi]")
            error_data = graceful_error_response(
                RuntimeError(recovery.errors[-1] if recovery.errors else "Unknown error"),
                model=model, recovery_result=recovery,
            )
            if on_error:
                on_error(task_id, error_data)
            return

        result = recovery.result
        msg = result.get("message", {}) if isinstance(result, dict) else {}
        plain_usage = result.get("usage") if isinstance(result, dict) else None
        cevap = msg.get("content", "") if msg else str(result)

        t_end = time.time()
        latency = {
            "total": round(t_end - t_start, 2),
            "router": round(t_router_done - t_router, 3),
            "model": round(t_model_done - t_model_start, 2),
        }
        _add_to_history(session_id, "user", soru)
        _add_to_history(session_id, "assistant", cevap)
        resp_data = {"cevap": cevap, "model": model, "gorev": gorev, "latency": latency}
        if plain_usage:
            resp_data["usage"] = plain_usage
        if recovery.attempts > 1:
            resp_data["recovery"] = recovery.as_dict()
        if on_complete:
            on_complete(task_id, resp_data)


# ─── STEP-05: SocketIO Callbacks ────────────────────────────────────────────

def _emit_task_status(task_id, phase, message, **extra):
    """Callback for TaskExecutor — emit SocketIO task_status events."""
    data = {
        "phase": phase,
        "message": message,
        "task_id": task_id,
    }
    data.update(extra)
    socketio.emit("task_status", data)


def _on_task_complete(task_id, result):
    """Callback for TaskExecutor — task finished successfully."""
    # Store result for wait_for_completion to read
    from core.task_executor import _results_store
    if result and isinstance(result, dict) and result.get('cevap'):
        _results_store[task_id] = result
    socketio.emit("task_completed", {
        "task_id": task_id,
        "result": result,
    })


def _on_task_error(task_id, error):
    """Callback for TaskExecutor — task failed."""
    socketio.emit("task_completed", {
        "task_id": task_id,
        "error": error,
    })


# ─── STEP-05: Chat API (Background Task) ─────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat_api():
    """UMAY chat API — STEP-05 background task execution.

    Creates a background task via TaskExecutor, blocks until completion,
    then returns {cevap, model, latency} for the frontend.
    SocketIO events are also emitted for real-time status updates.
    STEP-04 features (token budget, compression, recovery) preserved.
    """
    veri = request.json
    soru = veri.get("soru", "")
    session_id = veri.get("session_id", "default")
    attachments = veri.get("attachments", [])
    model_override = veri.get("model", "auto")
    mode = veri.get("mode", "auto")

    if not soru and not attachments:
        return jsonify({"error": "Soru bos"}), 400

    # STEP-05: Create task via task_state
    from core import task_state
    task_id = task_state.start_task(
        request=soru[:200],
        workspace=session_id,
        model="auto",
    )

    # STEP-05: Link conversation to task
    _conv_store.set_last_task_id(session_id, task_id)

    # Emit task_created event
    socketio.emit("task_status", {
        "phase": "task_created",
        "message": f"Görev oluşturuldu: {task_id}",
        "icon": "📋",
        "task_id": task_id,
        "session_id": session_id,
    })

    # STEP-05: Submit to background executor
    executor = get_executor()
    executor.submit(
        session_id=session_id,
        soru=soru,
        execute_fn=execute_chat_task,
        attachments=attachments,
        task_id=task_id,
        on_status=_emit_task_status,
        on_complete=_on_task_complete,
        on_error=_on_task_error,
        model_override=model_override,
        mode=mode,
    )

    # STEP-05: Block until task completes (preserves STEP-04 sync behavior)
    # This ensures frontend gets {cevap, model, latency} in the HTTP response.
    result = executor.wait_for_completion(task_id, timeout=300)

    if result and isinstance(result, dict):
        # Ensure standard response format for frontend
        resp = {
            "cevap": result.get("cevap", ""),
            "model": result.get("model", "auto"),
            "gorev": result.get("gorev", "chat"),
            "latency": result.get("latency", {}),
            "task_id": task_id,
            "mode": result.get("mode", mode),
        }
        if "usage" in result:
            resp["usage"] = result["usage"]
        if "error" in result:
            resp["error"] = result["error"]
        return jsonify(resp)
    else:
        return jsonify({"cevap": "Task zaman asimi", "model": "auto", "latency": {"total": 0}})


# ─── STEP-05: Task Management Endpoints ──────────────────────────────────────

@app.route("/api/chat/tasks", methods=["GET"])
def chat_tasks_list():
    """List tasks — STEP-03/STEP-05 task listing."""
    session_id = request.args.get("session_id", "default")
    limit = request.args.get("limit", 20, type=int)

    executor = get_executor()
    executor_tasks = executor.get_tasks_by_session(session_id)

    from core import task_state
    try:
        ws_tasks = task_state.list_tasks_for_workspace(session_id, limit=limit)
    except Exception:
        ws_tasks = []

    return jsonify({
        "session_id": session_id,
        "active_tasks": executor_tasks,
        "historical_tasks": ws_tasks,
        "total": len(executor_tasks) + len(ws_tasks),
    })


@app.route("/api/chat/tasks/<task_id>", methods=["GET"])
def chat_task_detail(task_id):
    """Get task detail — STEP-05."""
    executor = get_executor()
    info = executor.get_task_info(task_id)
    if info:
        return jsonify(info)

    from core import task_state
    task = task_state.load_task(task_id)
    if task:
        return jsonify(task)
    return jsonify({"error": "Task not found"}), 404


@app.route("/api/chat/tasks/<task_id>/pause", methods=["POST"])
def chat_task_pause(task_id):
    """Pause a running task — STEP-05."""
    executor = get_executor()
    ok = executor.pause(task_id)
    if ok:
        return jsonify({"ok": True, "status": "PAUSE_REQUESTED"})
    return jsonify({"ok": False, "error": "Task not pausable"}), 400


@app.route("/api/chat/tasks/<task_id>/resume", methods=["POST"])
def chat_task_resume(task_id):
    """Resume a paused task — STEP-05."""
    executor = get_executor()
    ok = executor.resume(task_id)
    if ok:
        return jsonify({"ok": True, "status": "RESUMING"})
    return jsonify({"ok": False, "error": "Task not resumable"}), 400


@app.route("/api/chat/tasks/<task_id>/cancel", methods=["POST"])
def chat_task_cancel(task_id):
    """Cancel a running task — STEP-05."""
    executor = get_executor()
    ok = executor.cancel(task_id)
    if ok:
        return jsonify({"ok": True, "status": "CANCEL_REQUESTED"})
    return jsonify({"ok": False, "error": "Task not cancellable"}), 400


# ─── Dashboard API ─────────────────────────────────────

@app.route("/api/system")
def system_status():
    """System status endpoint — CPU, RAM, Docker, Ollama, etc."""
    import psutil
    import subprocess
    result = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "disk_percent": psutil.disk_usage('/').percent,
        "python_version": sys.version.split()[0],
        "uptime": time.time() - psutil.boot_time(),
    }
    # Ollama
    try:
        from core.engine import OLLAMA_URL
        import requests as _req
        r = _req.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.ok:
            models = [m["name"] for m in r.json().get("models", [])]
            result["ollama"] = {"status": "connected", "url": OLLAMA_URL, "models": models}
        else:
            result["ollama"] = {"status": "error", "code": r.status_code}
    except Exception as e:
        result["ollama"] = {"status": "disconnected", "error": str(e)[:100]}
    # Docker — container icinde docker ps calismaz (socket mount yok)
    # Health-check tabanli: API calisiyorsa container saglikli
    try:
        import subprocess
        dr = subprocess.run(["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Image}}"],
                          capture_output=True, text=True, timeout=3)
        containers = []
        for line in dr.stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                containers.append({"name": parts[0], "status": parts[1], "image": parts[2] if len(parts) > 2 else ""})
        if containers:
            result["docker"] = {"containers": containers, "count": len(containers)}
        else:
            raise Exception("docker ps returned empty")
    except Exception:
        # Fallback: API calisiyorsa bu container saglikli demektir
        result["docker"] = {
            "containers": [{"name": "umay-agent", "status": "Up (healthy) — self", "image": "umay9-umay"}],
            "count": 1,
            "note": "Docker socket not mounted; status inferred from API health"
        }
    return jsonify(result)


@app.route("/api/agents")
def agents_status():
    """Agent status endpoint — lists all agents with their status."""
    agents = [
        {"name": "Browser Agent", "key": "browser", "role": "web_researcher", "icon": "🌐", "status": "idle"},
        {"name": "Coding Agent", "key": "coding", "role": "code_agent", "icon": "💻", "status": "idle"},
        {"name": "Terminal Agent", "key": "terminal", "role": "system_agent", "icon": "🖥️", "status": "idle"},
        {"name": "Document Agent", "key": "document", "role": "document_agent", "icon": "📄", "status": "idle"},
        {"name": "Vision Agent", "key": "vision", "role": "image_analyzer", "icon": "👁️", "status": "idle"},
        {"name": "Web Research", "key": "web", "role": "researcher", "icon": "🔍", "status": "idle"},
        {"name": "Gmail Agent", "key": "gmail", "role": "email_agent", "icon": "📧", "status": "not_configured" if not os.getenv("GMAIL_USER") else "idle"},
        {"name": "Telegram Bot", "key": "telegram_bot", "role": "messaging", "icon": "📱", "status": "not_configured" if not os.getenv("TELEGRAM_BOT_TOKEN") else "idle"},
        {"name": "Orchestrator", "key": "orchestrator", "role": "multi_agent", "icon": "🎯", "status": "idle"},
        {"name": "Planner", "key": "planner", "role": "task_planner", "icon": "📋", "status": "idle"},
    ]
    # Check if browser is active
    if agent_aktif:
        for a in agents:
            if a["key"] == "browser":
                a["status"] = "running"
    return jsonify({"agents": agents, "total": len(agents)})


@app.route("/api/tools")
def tools_list():
    """Tool registry endpoint."""
    try:
        from core.agent_tools import TOOLS
        tools = []
        for t in TOOLS:
            func = t.get("function", {})
            tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
            })
        return jsonify({"tools": tools, "total": len(tools)})
    except Exception as e:
        return jsonify({"tools": [], "total": 0, "error": str(e)})


@app.route("/api/memory")
def memory_status():
    """Memory/RAG status endpoint."""
    result = {"chromadb": {}, "memories": [], "stats": {}}
    try:
        from core.memory.memory_bridge import recall
        memories = recall("genel", limit=5)
        result["memories"] = memories
        result["stats"]["recall_count"] = len(memories)
    except Exception as e:
        result["error"] = str(e)
    try:
        chroma_path = ROOT / "memory" / "chroma" / "chroma.sqlite3"
        result["chromadb"] = {
            "exists": chroma_path.exists(),
            "path": str(chroma_path),
            "size_mb": round(chroma_path.stat().st_size / (1024*1024), 2) if chroma_path.exists() else 0,
        }
    except Exception:
        pass
    return jsonify(result)


@app.route("/api/scheduler_status")
def scheduler_status_api():
    """Scheduler status endpoint."""
    try:
        from core.scheduler import get_scheduler
        s = get_scheduler()
        tasks = s.list_tasks()
        return jsonify({"tasks": tasks, "total": len(tasks)})
    except Exception as e:
        return jsonify({"tasks": [], "total": 0, "error": str(e)})


@app.route("/api/logs")
def logs_api():
    """Log entries endpoint."""
    log_file = ROOT / "logs" / "umay.log"
    lines = []
    try:
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                lines = [l.rstrip() for l in all_lines[-50:]]
    except Exception:
        pass
    return jsonify({"lines": lines, "count": len(lines)})


@app.route("/api/workers")
def workers_status():
    """Worker status endpoint."""
    try:
        from core.worker import get_worker
        w = get_worker()
        return jsonify(w.get_status())
    except Exception as e:
        return jsonify({"running": False, "tasks": {}, "error": str(e)})


@app.route("/api/config")
def config_api():
    """Config endpoint (non-sensitive)."""
    return jsonify({
        "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "primary_provider": os.getenv("PRIMARY_PROVIDER", "OLLAMA"),
        "mimo_configured": bool(os.getenv("MIMO_API_KEY")),
        "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "gmail_configured": bool(os.getenv("GMAIL_USER")),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
    })


@app.route("/api/models")
def models_api():
    """List available models with capabilities for model selector."""
    try:
        from core.engine import installed_models, MODEL_PREFERENCES, OLLAMA_URL
        import requests as _req
        models = installed_models()
        # Categorize models
        categorized = {
            "chat": MODEL_PREFERENCES.get("chat", []),
            "coding": MODEL_PREFERENCES.get("coding", []),
            "vision": MODEL_PREFERENCES.get("vision", []),
            "reasoning": MODEL_PREFERENCES.get("reasoning", []),
            "analysis": MODEL_PREFERENCES.get("analysis", []),
        }
        # Match installed models to categories
        result = []
        for m in models:
            cats = []
            for cat, prefs in categorized.items():
                for p in prefs:
                    if m == p or m.split(":")[0] == p.split(":")[0]:
                        cats.append(cat)
                        break
            result.append({
                "name": m,
                "categories": cats if cats else ["general"],
                "tags": cats,
            })
        return jsonify({"models": result, "total": len(result)})
    except Exception as e:
        return jsonify({"models": [], "total": 0, "error": str(e)})


@app.route("/api/chat/history")
def chat_history_api():
    """Get chat conversation history for a session."""
    session_id = request.args.get("session_id", "panel")
    try:
        from core import conversation_store as _conv
        messages = _conv.get_history(session_id, max_pairs=20)
        return jsonify({"messages": messages, "session_id": session_id})
    except Exception as e:
        return jsonify({"messages": [], "error": str(e)})


@app.route("/api/conversations")
def conversations_list_api():
    """List all conversations for history sidebar."""
    try:
        from core import conversation_store as _conv
        convs = _conv.list_conversations(limit=50)
        result = []
        for c in convs:
            history = _conv.get_history(c["id"], max_pairs=1)

            last_msg = history[-1]["content"][:80] if history else ""
            result.append({
                "id": c["id"],
                "title": c.get("title") or last_msg[:50] or c["id"],
                "updated_at": c["updated_at"],
                "message_count": len(_conv.get_history(c["id"], max_pairs=100)),
            })
        return jsonify({"conversations": result})
    except Exception as e:
        return jsonify({"conversations": [], "error": str(e)})


# ─── Diagnostics ──────────────────────────────────────

@app.route("/api/diagnostics")
def diagnostics():
    """UMAY system diagnostics — checks all subsystems."""
    checks = []
    # 1. Core
    try:
        from core.engine import OLLAMA_URL, resolve_model
        checks.append({"name": "Core Engine", "status": "PASS", "detail": f"OLLAMA_URL={OLLAMA_URL}"})
    except Exception as e:
        checks.append({"name": "Core Engine", "status": "FAIL", "detail": str(e)[:100]})
    # 2. Router
    try:
        from core.router import model_sec
        m, g = model_sec("test")
        checks.append({"name": "Router", "status": "PASS", "detail": f"model={m}, task={g}"})
    except Exception as e:
        checks.append({"name": "Router", "status": "FAIL", "detail": str(e)[:100]})
    # 3. Tool Registry
    try:
        from core.agent_tools import TOOLS
        checks.append({"name": "Tool Registry", "status": "PASS", "detail": f"{len(TOOLS)} tools"})
    except Exception as e:
        checks.append({"name": "Tool Registry", "status": "FAIL", "detail": str(e)[:100]})
    # 4. Ollama
    try:
        from core.engine import OLLAMA_URL
        import requests as _req
        r = _req.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])] if r.ok else []
        checks.append({"name": "Ollama", "status": "PASS" if r.ok else "FAIL", "detail": f"{len(models)} models"})
    except Exception as e:
        checks.append({"name": "Ollama", "status": "FAIL", "detail": str(e)[:100]})
    # 5. Memory
    try:
        from core.memory.memory_bridge import recall
        results = recall("test", limit=1)
        checks.append({"name": "Memory", "status": "PASS", "detail": f"{len(results)} results"})
    except Exception as e:
        checks.append({"name": "Memory", "status": "FAIL", "detail": str(e)[:100]})
    # 6. Browser
    try:
        from agents.browser_agent import BrowserAgent
        checks.append({"name": "Browser Agent", "status": "PASS", "detail": "class available"})
    except Exception as e:
        checks.append({"name": "Browser Agent", "status": "FAIL", "detail": str(e)[:100]})
    # 7. Scheduler
    try:
        from core.scheduler import get_scheduler
        s = get_scheduler()
        tasks = s.list_tasks()
        checks.append({"name": "Scheduler", "status": "PASS", "detail": f"{len(tasks)} tasks"})
    except Exception as e:
        checks.append({"name": "Scheduler", "status": "FAIL", "detail": str(e)[:100]})
    # 8. Worker
    try:
        from core.worker import get_worker
        w = get_worker()
        checks.append({"name": "Worker", "status": "PASS", "detail": f"running={w._running}"})
    except Exception as e:
        checks.append({"name": "Worker", "status": "FAIL", "detail": str(e)[:100]})
    # 9. Telegram
    tg = _get_telegram_status()
    tg_ok = tg.get("bot_connected") or tg.get("user_connected")
    checks.append({"name": "Telegram", "status": "PASS" if tg_ok else "NOT CONFIGURED", "detail": f"bot={tg.get('bot_connected')}, user={tg.get('user_connected')}"})
    # 10. Gmail
    gmail_ok = bool(os.getenv("GMAIL_USER"))
    checks.append({"name": "Gmail", "status": "PASS" if gmail_ok else "NOT CONFIGURED", "detail": "configured" if gmail_ok else "credentials missing"})
    passed = sum(1 for c in checks if c["status"] == "PASS")
    total = len(checks)
    return jsonify({"checks": checks, "passed": passed, "total": total})


@app.route("/api/model_benchmark")
def model_benchmark():
    """Quick model benchmark — tests each chat model with a short prompt."""
    import requests as _req
    try:
        from core.engine import OLLAMA_URL
    except Exception:
        return jsonify({"error": "Engine not available"}), 500
    chat_models = ["phi4-mini:latest", "qwen3:8b", "deepseek-r1:8b", "gemma3:4b"]
    results = []
    for model in chat_models:
        t0 = time.time()
        try:
            r = _req.post(f"{OLLAMA_URL}/api/chat", json={
                "model": model,
                "messages": [{"role": "user", "content": "Merhaba, kendini bir cumleyle tanit."}],
                "stream": False,
            }, timeout=60)
            elapsed = round(time.time() - t0, 2)
            if r.ok:
                content = r.json().get("message", {}).get("content", "")
                results.append({"model": model, "status": "PASS", "latency": elapsed, "length": len(content), "response": content[:150]})
            else:
                results.append({"model": model, "status": "FAIL", "latency": elapsed, "error": f"HTTP {r.status_code}"})
        except _req.Timeout:
            results.append({"model": model, "status": "TIMEOUT", "latency": 60, "error": "60s timeout"})
        except Exception as e:
            results.append({"model": model, "status": "FAIL", "latency": round(time.time() - t0, 2), "error": str(e)[:100]})
    return jsonify({"results": results})


# ─── SocketIO Olaylari ─────────────────────────────────

@socketio.on("connect")
def on_connect():
    emit("durum", {"mesaj": "UMAY Kontrol Paneli hazir!", "renk": "green"})
    # Telegram durumunu hemen gonder
    try:
        emit("telegram_status", _get_telegram_status())
    except Exception:
        pass


# ─── SocketIO Chat (non-blocking, with task controls) ───────────────────────
# Current task tracking per session for pause/resume/cancel
_socket_tasks: dict[str, str] = {}  # session_id -> task_id


@socketio.on("chat_message")
def on_chat_message(data):
    """Handle chat via SocketIO — non-blocking, supports pause/resume/cancel."""
    soru = data.get("soru", "")
    session_id = data.get("session_id", "default")
    model_override = data.get("model", "auto")
    mode = data.get("mode", "auto")
    attachments = data.get("attachments", [])

    if not soru and not attachments:
        emit("chat_response", {"error": "Soru bos"})
        return

    # Create task via task_state
    from core import task_state
    task_id = task_state.start_task(
        request=soru[:200],
        workspace=session_id,
        model="auto",
    )

    # Track task for this session
    _socket_tasks[session_id] = task_id

    # Link conversation to task
    _conv_store.set_last_task_id(session_id, task_id)

    # Emit task created
    emit("task_status", {
        "phase": "task_created",
        "message": f"Gorev olusturuldu: {task_id}",
        "icon": "📋",
        "task_id": task_id,
        "session_id": session_id,
    })

    # Submit to background executor with socketio callbacks
    def _socket_on_status(tid, phase, message, **extra):
        socketio.emit("task_status", {
            "phase": phase,
            "message": message,
            "task_id": tid,
            "session_id": session_id,
            **extra,
        })

    def _socket_on_complete(tid, result):
        # Store result for wait_for_completion to read
        from core.task_executor import _results_store
        if result and isinstance(result, dict) and result.get('cevap'):
            _results_store[tid] = result
        socketio.emit("chat_response", {
            "task_id": tid,
            "session_id": session_id,
            **(result if isinstance(result, dict) else {"cevap": str(result)}),
        })
        # Cleanup tracking
        _socket_tasks.pop(session_id, None)

    def _socket_on_error(tid, error):
        socketio.emit("chat_response", {
            "task_id": tid,
            "session_id": session_id,
            "error": error.get("error", str(error)) if isinstance(error, dict) else str(error),
        })
        _socket_tasks.pop(session_id, None)

    executor = get_executor()
    executor.submit(
        session_id=session_id,
        soru=soru,
        execute_fn=execute_chat_task,
        attachments=attachments,
        task_id=task_id,
        on_status=_socket_on_status,
        on_complete=_socket_on_complete,
        on_error=_socket_on_error,
        model_override=model_override,
        mode=mode,
    )


@socketio.on("pause_task")
def on_pause_task(data):
    """Pause the current task for a session."""
    session_id = data.get("session_id", "default")
    task_id = _socket_tasks.get(session_id)
    if not task_id:
        emit("task_status", {"phase": "error", "message": "Aktif gorev bulunamadi"})
        return
    executor = get_executor()
    ok = executor.pause(task_id)
    emit("task_status", {
        "phase": "paused" if ok else "error",
        "message": "Durduruldu" if ok else "Durdurulamadi",
        "task_id": task_id,
    })


@socketio.on("resume_task")
def on_resume_task(data):
    """Resume the paused task for a session."""
    session_id = data.get("session_id", "default")
    task_id = _socket_tasks.get(session_id)
    if not task_id:
        emit("task_status", {"phase": "error", "message": "Aktif gorev bulunamadi"})
        return
    executor = get_executor()
    ok = executor.resume(task_id)
    emit("task_status", {
        "phase": "resumed" if ok else "error",
        "message": "Devam ediyor" if ok else "Devam ettirilemedi",
        "task_id": task_id,
    })


@socketio.on("cancel_task")
def on_cancel_task(data):
    """Cancel the current task for a session."""
    session_id = data.get("session_id", "default")
    task_id = _socket_tasks.get(session_id)
    if not task_id:
        emit("task_status", {"phase": "error", "message": "Aktif gorev bulunamadi"})
        return
    executor = get_executor()
    ok = executor.cancel(task_id)
    emit("task_status", {
        "phase": "cancelled" if ok else "error",
        "message": "Iptal edildi" if ok else "Iptal edilemedi",
        "task_id": task_id,
    })


# ─── Baslangic ─────────────────────────────────────────

# Initialize conversation store DB on startup
try:
    _conv_store.init_db()
except Exception as e:
    print(f"[WARN] Conversation store init: {e}")

if __name__ == "__main__":
    # Arka plan threadleri
    threading.Thread(target=ekran_gonder_dongu, daemon=True).start()
    threading.Thread(target=log_gonder_dongu, daemon=True).start()
    threading.Thread(target=telegram_status_dongu, daemon=True).start()

    # Telegram adapter (eğer yapılandırılmışsa)
    try:
        from core.telegram_adapter import get_telegram_adapter, is_telegram_configured
        if is_telegram_configured():
            tg = get_telegram_adapter()
            from core.approval_manager import get_approval_manager
            from core.communication_manager import get_communication_manager
            from core import agent as agent_module
            tg.set_approval_manager(get_approval_manager())
            tg.set_communication_manager(get_communication_manager())
            tg.set_agent_module(agent_module)
            if tg.start():
                print(" Telegram: BAĞLANTI KURULDU")
            else:
                print(" Telegram: BAŞLATILAMADI")
        else:
            print(" Telegram: YAPILANDIRILMAMIŞ (devre dışı)")

        from core.telegram_user_adapter import get_telegram_user_adapter
        user_tg = get_telegram_user_adapter()
        if user_tg.is_configured():
            from core.approval_manager import get_approval_manager
            from core.communication_manager import get_communication_manager
            from core import agent as agent_module
            user_tg.set_approval_manager(get_approval_manager())
            user_tg.set_communication_manager(get_communication_manager())
            user_tg.set_agent_module(agent_module)
            print(
                " Telegram User Account: BAĞLANTI KURULDU"
                if user_tg.start()
                else " Telegram User Account: BAŞLATILAMADI"
            )
        else:
            print(" Telegram User Account: YAPILANDIRILMAMIŞ (devre dışı)")
    except Exception as e:
        print(f" Telegram: Başlatılamadı — {e}")

    # Background Worker & Scheduler
    try:
        from core.worker import start_worker
        from core.scheduler import start_scheduler
        start_worker()
        start_scheduler()
        print(" Background Worker: BAŞLATILDI")
        print(" Scheduler: BAŞLATILDI")
    except Exception as e:
        print(f" Worker/Scheduler: Başlatılamadı — {e}")

    print("\n" + "="*50)
    print(" UMAY Kontrol Paneli")
    print(" Adres: http://localhost:5001")
    print("="*50 + "\n")

    socketio.run(app, host="0.0.0.0", port=5001, debug=False, allow_unsafe_werkzeug=True)

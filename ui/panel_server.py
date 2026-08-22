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


@app.route("/api/chat", methods=["POST"])
def chat_api():
    """UMAY chat API'si — tool calling + real-time status destekli."""
    from core.engine import chat as umay_chat, resolve_model
    from core.router import model_sec
    from core.agent_tools import TOOLS, DISPATCH
    from core.agent import (
        _parse_tool_calls, _assistant_tool_message,
        _tool_messages, _bounded_tool_result,
    )

    veri = request.json
    soru = veri.get("soru", "")
    session_id = veri.get("session_id", "default")
    attachments = veri.get("attachments", [])  # List of attachment dicts from frontend
    t_start = time.time()

    # Real-time status: Düşünüyor
    socketio.emit("task_status", {
        "phase": "thinking",
        "message": "Düşünüyor...",
        "icon": "🧠"
    })

    # Initialize defaults
    model = None
    gorev = "chat"

    # Check if any attachment is an image -> route to vision model
    has_image = any(a.get("is_vision") or a.get("type") == "image" for a in attachments)
    if has_image:
        vision_model = resolve_model("vision")
        if vision_model:
            model = vision_model
            gorev = "vision"
        else:
            # No vision model available, strip image refs and continue
            attachments = [a for a in attachments if a.get("type") != "image"]
            has_image = False
            socketio.emit("task_status", {
                "phase": "warning",
                "message": "Vision model bulunamadı, görsel analiz yapılamıyor.",
                "icon": "⚠️"
            })

    # Router ile gorev ve model sec (if not overridden by vision)
    t_router = time.time()
    if gorev != "vision":
        model, gorev = model_sec(soru)
        model = model or resolve_model("chat")
    t_router_done = time.time()

    # Tool calling: sadece gercekten tool gerektiren gorevlerde aktif
    use_tools = gorev in ("coding", "agent")

    # Build context from attachments
    from core.attachment_engine import build_chat_context, build_vision_message
    att_context = build_chat_context(attachments, soru)

    # Session history — conversation context korunur
    history = _get_session_history(session_id)
    messages = [
        {"role": "system", "content": UMAY_SYSTEM},
        *history,
        {"role": "user", "content": att_context}
    ]

    # STEP-04.3: Pre-flight token budget check
    from core.token_budget import estimate_usage, check_budget, STATUS_OK
    preflight_usage = estimate_usage(messages)
    preflight_check = check_budget(preflight_usage)
    if preflight_check.status != "OK":
        socketio.emit("task_status", {
            "phase": "budget_warning",
            "message": f"Token bütçesi {preflight_check.status}: ~{preflight_check.used_tokens}/{preflight_check.limit_tokens} ({round(preflight_check.ratio * 100, 1)}%)",
            "icon": "⚠️" if preflight_check.status == "WARNING" else "🔴",
            "budget": preflight_check.as_dict()
        })

    # STEP-04.4: Context compression — compress older messages if budget exceeded
    from core.context_compression import compress_context
    compression_result = compress_context(messages)
    if compression_result.was_compressed:
        messages = compression_result.compressed_messages
        socketio.emit("task_status", {
            "phase": "context_compressed",
            "message": f"Bağlam sıkıştırıldı: {compression_result.original_count} → {compression_result.compressed_count} mesaj (~{compression_result.tokens_saved_estimate} token tasarruf)",
            "icon": "📦",
            "compression": compression_result.as_dict()
        })

    # If vision, find the stored image and read its base64
    vision_image = None
    if has_image:
        for a in attachments:
            if a.get("is_vision") or a.get("type") == "image":
                # Find the stored file by hash and read base64
                vision_image = _resolve_image_base64(a)
                break

    if has_image and vision_image:
        # Vision request — use Ollama vision API directly
        socketio.emit("task_status", {
            "phase": "calling_model",
            "message": f"Görsel analiz modeli çağrılıyor ({model})...",
            "icon": "👁️",
            "model": model,
            "task": "vision"
        })

        t_model_start = time.time()
        try:
            import requests as _req
            from core.engine import OLLAMA_URL

            # Build vision messages with image.
            # STEP-04.5 fix: use att_context (built above from ALL
            # attachments — image placeholder + every other attachment's
            # extracted text) instead of raw `soru`. Previously this used
            # `soru` alone, so any PDF/code/text attachment sent alongside
            # an image in the same turn was silently dropped from what the
            # vision model saw.
            vision_msgs = [
                {"role": "system", "content": UMAY_SYSTEM},
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
                # STEP-04.3: Extract real token usage from vision Ollama response
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
        socketio.emit("task_status", {
            "phase": "completed" if not is_vision_error else "error",
            "message": f"{'Görsel analiz hatası' if is_vision_error else 'Görsel analiz tamamlandı'}. ({latency['total']}s)",
            "icon": "🟢" if not is_vision_error else "❌"
        })
        _add_to_history(session_id, "user", soru)
        _add_to_history(session_id, "assistant", cevap)
        resp_data = {"cevap": cevap, "model": model, "gorev": gorev, "latency": latency}
        if vision_usage:
            resp_data["usage"] = vision_usage.as_dict()
        if is_vision_error:
            resp_data["error"] = True
        return jsonify(resp_data)

    elif use_tools:
        # Real-time status: Model çağrılıyor
        socketio.emit("task_status", {
            "phase": "calling_model",
            "message": f"Model çağrılıyor ({model or 'auto'})...",
            "icon": "⚡",
            "model": model,
            "task": gorev
        })

        # Tool calling: 1 tool call, sonucu direkt don
        t_model_start = time.time()
        try:
            result = umay_chat(messages, model=model, tools=TOOLS)
        except Exception as tool_exc:
            t_model_done = time.time()
            socketio.emit("task_status", {"phase": "error", "message": f"Tool model hatası: {tool_exc}", "icon": "❌"})
            _add_to_history(session_id, "user", soru)
            _add_to_history(session_id, "assistant", f"[Hata: {tool_exc}]")
            return jsonify(graceful_error_response(tool_exc, model=model))
        t_model_done = time.time()
        msg = result.get("message", {}) if isinstance(result, dict) else {}
        tool_usage = result.get("usage") if isinstance(result, dict) else None
        tool_calls = _parse_tool_calls(msg)

        if tool_calls:
            # Real-time status: Tool çalışıyor
            for tc in tool_calls:
                func_name = tc.get("function", {}).get("name", "unknown")
                socketio.emit("task_status", {
                    "phase": "tool_running",
                    "message": f"Tool çalışıyor: {func_name}",
                    "icon": "🔧",
                    "tool": func_name
                })

            # Tool sonucunu al ve model'e goster
            messages.append(_assistant_tool_message(tool_calls))
            tool_msgs = _tool_messages(tool_calls)
            messages.extend(tool_msgs)

            # Real-time status: Tool tamamlandı
            socketio.emit("task_status", {
                "phase": "tool_done",
                "message": "Tool tamamlandı, yanıt oluşturuluyor...",
                "icon": "✅"
            })

            # Tool sonucunu basitce formatla
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
                    cevap = f"Tool sonucu: {last_result[:500]}"
            except Exception:
                cevap = f"Tool sonucu: {last_result[:500]}"
        else:
            cevap = msg.get("content", "") if msg else str(result)

        # Real-time status: Tamamlandı
        t_end = time.time()
        latency = {
            "total": round(t_end - t_start, 2),
            "router": round(t_router_done - t_router, 3),
            "model": round(t_model_done - t_model_start, 2),
        }
        socketio.emit("task_status", {
            "phase": "completed",
            "message": f"Görev tamamlandı. ({latency['total']}s)",
            "icon": "🟢"
        })

        # Session history'ye kaydet
        _add_to_history(session_id, "user", soru)
        _add_to_history(session_id, "assistant", cevap)

        resp_data = {"cevap": cevap, "model": model, "gorev": gorev, "latency": latency}
        if tool_usage:
            resp_data["usage"] = tool_usage
        return jsonify(resp_data)
    else:
        # Basit sohbet — tool calling yok, hizli cevap
        socketio.emit("task_status", {
            "phase": "calling_model",
            "message": f"Sohbet modeli çağrılıyor ({model or 'auto'})...",
            "icon": "💬",
            "model": model
        })
        t_model_start = time.time()
        # Build final user content with attachment context
        user_content = att_context if attachments else soru
        messages[-1] = {"role": "user", "content": user_content}

        # STEP-04.6: Wrap model call with failure recovery
        from core.failure_recovery import with_recovery, graceful_error_response
        recovery = with_recovery(umay_chat, messages, model=model)
        t_model_done = time.time()

        if not recovery.success:
            socketio.emit("task_status", {
                "phase": "error",
                "message": f"Model hatası ({recovery.attempts} deneme)",
                "icon": "❌"
            })
            _add_to_history(session_id, "user", soru)
            _add_to_history(session_id, "assistant", "[Hata: model yanıt üretemedi]")
            return jsonify(graceful_error_response(
                RuntimeError(recovery.errors[-1] if recovery.errors else "Unknown error"),
                model=model, recovery_result=recovery,
            ))

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
        socketio.emit("task_status", {
            "phase": "completed",
            "message": f"Yanıt hazır. ({latency['total']}s)" + (f" [retry: {recovery.attempts}x]" if recovery.attempts > 1 else ""),
            "icon": "🟢"
        })

        # Session history'ye kaydet
        _add_to_history(session_id, "user", soru)
        _add_to_history(session_id, "assistant", cevap)

        resp_data = {"cevap": cevap, "model": model, "gorev": gorev, "latency": latency}
        if plain_usage:
            resp_data["usage"] = plain_usage
        if recovery.attempts > 1:
            resp_data["recovery"] = recovery.as_dict()
        return jsonify(resp_data)


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

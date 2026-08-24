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

    # Real-time status: Düşünüyor
    socketio.emit("task_status", {
        "phase": "thinking",
        "message": "Düşünüyor...",
        "icon": "🧠"
    })

    # Router ile gorev ve model sec
    model, gorev = model_sec(soru)
    model = model or resolve_model("chat")

    # Tool calling: sadece gercekten tool gerektiren gorevlerde aktif
    use_tools = gorev in ("coding", "agent")

    messages = [
        {"role": "system", "content": UMAY_SYSTEM},
        {"role": "user", "content": soru}
    ]

    if use_tools:
        # Real-time status: Model çağrılıyor
        socketio.emit("task_status", {
            "phase": "calling_model",
            "message": f"Model çağrılıyor ({model or 'auto'})...",
            "icon": "⚡",
            "model": model,
            "task": gorev
        })

        # Tool calling: 1 tool call, sonucu direkt don
        result = umay_chat(messages, model=model, tools=TOOLS)
        msg = result.get("message", {}) if isinstance(result, dict) else {}
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
        socketio.emit("task_status", {
            "phase": "completed",
            "message": "Görev tamamlandı.",
            "icon": "🟢"
        })

        return jsonify({"cevap": cevap, "model": model, "gorev": gorev})
    else:
        # Basit sohbet — tool calling yok, hizli cevap
        socketio.emit("task_status", {
            "phase": "calling_model",
            "message": f"Sohbet modeli çağrılıyor ({model or 'auto'})...",
            "icon": "💬",
            "model": model
        })
        result = umay_chat(messages, model=model)
        msg = result.get("message", {}) if isinstance(result, dict) else {}
        cevap = msg.get("content", "") if msg else str(result)

        socketio.emit("task_status", {
            "phase": "completed",
            "message": "Yanıt hazır.",
            "icon": "🟢"
        })

        return jsonify({"cevap": cevap, "model": model, "gorev": gorev})


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

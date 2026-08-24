"""UMAY Telegram Adapter — İki yönlü iletişim, onay kontrolü, görev yönetimi.

Bu modül UMAY Core ile Telegram arasındaki köprüyü kurar.
Telegram'dan bağımsız UMAY core'un çalışmasını etkilemez.

Mimari:
    UMAY CORE
        ↓
    Communication Manager
        ↓
    Telegram Adapter  ← Bu dosya
        ↓
    Telegram Bot API

Kullanım:
    adapter = TelegramAdapter()
    adapter.start()  # Background thread'de polling başlatır
    adapter.stop()   # Polling'i durdurur

Çalışma prensibi:
- Telegram'dan gelen mesajları Authentication → Parse → Route eder
- UMAY'dan giden mesajları Telegram formatına çevirir
- ApprovalManager ile entegre çalışır
- Hiçbir core logic'i kopyalamaz
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from core.utils.logger import log

# ─── Constants ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
POLLING_STATE_FILE = ROOT / "logs" / "telegram_polling_state.json"

# Config from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID", "")
TELEGRAM_MAX_FILE_BYTES = int(os.getenv("TELEGRAM_MAX_FILE_BYTES", "20000000"))
SUPPORTED_TELEGRAM_DOCUMENT_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".json", ".xml", ".html",
    ".py", ".js", ".ts", ".css", ".yaml", ".yml", ".toml", ".ini", ".log",
    ".sql", ".sh", ".bat", ".ps1",
}


class TelegramPollingError(RuntimeError):
    """Recoverable Telegram polling failure."""


class TelegramAuthError(TelegramPollingError):
    """Telegram rejected the bot token."""


class TelegramConflictError(TelegramPollingError):
    """Another polling consumer is active for this bot."""


class TelegramRateLimitError(TelegramPollingError):
    def __init__(self, retry_after: int = 1):
        super().__init__(f"Telegram rate limit; retry after {retry_after}s")
        self.retry_after = max(1, retry_after)


# ─── Telegram Adapter ───────────────────────────────────────────────────────

class TelegramAdapter:
    """Telegram bot adapter — polling tabanlı, bağımsız çalışır.

    Bu sınıf:
    - Telegram Bot API'ye bağlanır (polling)
    - Gelen mesajları parse eder
    - Authentication kontrolü yapar
    - Approval komutlarını yönlendirir
    - Outbound mesajları Telegram formatına çevirir
    - Hiçbir core logic'i kopyalamaz
    """

    def __init__(self):
        self._running = False
        self._bot = None
        self._app = None
        self._thread: threading.Thread | None = None
        self._comm_manager = None
        self._approval_manager = None
        self._agent_module = None
        self._authenticated_users: set[int] = set()
        self._conversation_history: dict[str, list[dict[str, str]]] = {}
        self._conversation_lock = threading.RLock()
        self._agent_execution_lock = threading.RLock()
        self._processed_update_ids: deque[int] = deque(maxlen=1000)

        # Parse allowed user IDs
        if TELEGRAM_ALLOWED_USER_ID:
            for uid in TELEGRAM_ALLOWED_USER_ID.split(","):
                uid = uid.strip()
                if uid.isdigit():
                    self._authenticated_users.add(int(uid))

    # ─── Lifecycle ─────────────────────────────────────────────────────

    def is_active(self) -> bool:
        """Adapter aktif mi?"""
        return self._running and self._bot is not None

    def start(self):
        """Telegram polling'i başlat (background thread)."""
        if not TELEGRAM_BOT_TOKEN:
            log("[TELEGRAM] Bot token tanımlanmamış — Telegram devre dışı.")
            return False
        if not self._authenticated_users:
            log("[TELEGRAM] Allowed user listesi yok/geçersiz — polling başlatılmadı.")
            return False

        try:
            if not self._setup_bot():
                self._running = False
                return False
            self._running = True
            self._thread = threading.Thread(
                target=self._polling_loop,
                daemon=True,
                name="umay-telegram-polling",
            )
            self._thread.start()
            log("[TELEGRAM] Polling başlatıldı.")
            return True
        except Exception as exc:
            log(f"[TELEGRAM] Başlatma hatası: {type(exc).__name__}")
            return False

    def stop(self):
        """Polling'i durdur."""
        self._running = False
        client = getattr(self, "_http_client", None)
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
            self._http_client = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=35)
            if self._thread.is_alive():
                log("[TELEGRAM] Polling thread kapanmadı; daemon olarak bırakıldı.")
        log("[TELEGRAM] Polling durduruldu.")

    def set_communication_manager(self, manager):
        """Communication Manager referansını ayarla."""
        self._comm_manager = manager
        manager.register_adapter("telegram", self)
        manager.register_handler("TEXT", self._handle_text_inbound)

    def set_approval_manager(self, manager):
        """Approval Manager referansını ayarla."""
        self._approval_manager = manager

    def set_agent_module(self, module):
        """Agent modülü referansını ayarla."""
        self._agent_module = module

    def _handle_text_inbound(self, message):
        """Route normal Telegram text through the shared UMAY agent."""
        agent_module = self._agent_module
        if agent_module is None:
            from core import agent as agent_module
        with self._agent_execution_lock:
            return agent_module.run_agent(message.text, context=message.context)

    # ─── Bot Setup ─────────────────────────────────────────────────────

    def _setup_bot(self) -> bool:
        """Telegram bot'u hazırla."""
        try:
            import httpx
            self._http_client = httpx.Client(
                base_url="https://api.telegram.org",
                timeout=30.0,
            )
            # Token'ı doğrula
            resp = self._http_client.get(f"/bot{TELEGRAM_BOT_TOKEN}/getMe")
            if resp.status_code == 200:
                bot_info = resp.json().get("result", {})
                log(f"[TELEGRAM] Bot bağlandı: @{bot_info.get('username', 'unknown')}")
                self._bot = bot_info
                return True
            else:
                log(f"[TELEGRAM] Token doğrulanamadı: {resp.status_code}")
                self._bot = None
                return False
        except ImportError:
            # httpx yoksa requests kullan
            import requests
            self._http_client = None
            resp = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe",
                timeout=10)
            if resp.status_code == 200:
                bot_info = resp.json().get("result", {})
                log(f"[TELEGRAM] Bot bağlandı: @{bot_info.get('username', 'unknown')}")
                self._bot = bot_info
                return True
            else:
                log(f"[TELEGRAM] Token doğrulanamadı: {resp.status_code}")
                self._bot = None
                return False
        except Exception as exc:
            self._bot = None
            raise TelegramPollingError(f"bot setup failed: {type(exc).__name__}") from exc

    # ─── Polling ───────────────────────────────────────────────────────

    def _polling_loop(self):
        """Telegram long-polling döngüsü."""
        offset = self._load_polling_offset()
        backoff = 1
        while self._running:
            try:
                updates = self._get_updates(offset=offset, timeout=30)
                backoff = 1
                if updates:
                    for update in updates:
                        update_id = update.get("update_id")
                        if isinstance(update_id, int) and update_id in self._processed_update_ids:
                            continue
                        self._handle_update(update)
                        if isinstance(update_id, int):
                            self._processed_update_ids.append(update_id)
                            offset = update_id + 1
                            self._save_polling_offset(offset)
            except TelegramAuthError as exc:
                self._bot = None
                self._running = False
                log(f"[TELEGRAM] Kimlik doğrulama başarısız: {exc}")
            except TelegramRateLimitError as exc:
                log(f"[TELEGRAM] Rate limit; {exc.retry_after}s sonra tekrar denenecek.")
                time.sleep(exc.retry_after)
            except TelegramConflictError as exc:
                log(f"[TELEGRAM] Polling conflict: {exc}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
            except TelegramPollingError as exc:
                log(f"[TELEGRAM] Polling bağlantı hatası: {exc}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
            except Exception as e:
                if self._running:
                    log(f"[TELEGRAM] Polling hatası: {e}")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)

    def _get_updates(self, offset: int = 0, timeout: int = 30) -> list[dict]:
        """Telegram'dan güncelleme al."""
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"offset": offset, "timeout": timeout, "allowed_updates": '["message","callback_query"]'}
        try:
            if self._http_client:
                resp = self._http_client.get("/getUpdates", params=params)
            else:
                import requests
                resp = requests.get(url, params=params, timeout=timeout + 10)
        except Exception as exc:
            raise TelegramPollingError(f"request failed: {type(exc).__name__}") from exc

        status = getattr(resp, "status_code", 0)
        if status == 401:
            raise TelegramAuthError("Telegram token rejected")
        if status == 409:
            raise TelegramConflictError("another getUpdates consumer is active")
        if status == 429:
            retry_after = 1
            try:
                retry_after = int(resp.json().get("parameters", {}).get("retry_after", 1))
            except (TypeError, ValueError, AttributeError):
                pass
            raise TelegramRateLimitError(retry_after)
        if status >= 500:
            raise TelegramPollingError(f"Telegram server HTTP {status}")
        if status != 200:
            raise TelegramPollingError(f"Telegram HTTP {status}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise TelegramPollingError("Telegram malformed JSON response") from exc
        if not payload.get("ok", True):
            raise TelegramPollingError("Telegram returned ok=false")
        return payload.get("result", [])

    @staticmethod
    def _load_polling_offset() -> int:
        try:
            if POLLING_STATE_FILE.exists():
                with POLLING_STATE_FILE.open("r", encoding="utf-8") as handle:
                    value = json.load(handle).get("offset", 0)
                    return max(0, int(value))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            log("[TELEGRAM] Polling state okunamadı; offset sıfırdan başlatıldı.")
        return 0

    @staticmethod
    def _save_polling_offset(offset: int) -> None:
        try:
            POLLING_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            temporary = POLLING_STATE_FILE.with_suffix(".tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump({"offset": int(offset)}, handle)
            temporary.replace(POLLING_STATE_FILE)
        except OSError:
            log("[TELEGRAM] Polling offset kalıcılaştırılamadı.")

    def _handle_update(self, update: dict):
        """Tek bir Telegram güncellemesini işle."""
        # Callback query (inline button)
        callback_query = update.get("callback_query")
        if callback_query:
            self._handle_callback_query(callback_query)
            return

        # Message
        message = update.get("message")
        if message:
            self._handle_message(message)
            return

    # ─── Message Handling ──────────────────────────────────────────────

    def _handle_message(self, message: dict):
        """Gelen Telegram mesajını işle."""
        from_user = message.get("from", {})
        user_id = from_user.get("id", 0)
        user_name = from_user.get("first_name", "Bilinmeyen")
        text = message.get("text") or message.get("caption", "")
        chat_id = message.get("chat", {}).get("id", 0)
        reply_to = message.get("reply_to_message")
        reply_to_id = reply_to.get("message_id") if reply_to else None

        # Authentication kontrolü
        if not self._is_authorized(user_id):
            if self._authenticated_users:
                self._send_message(chat_id, "⛔ Yetkisiz kullanıcı.")
            else:
                self._send_message(chat_id, "⛔ Telegram yetkilendirmesi yapılandırılmamış.")
            return

        if not text:
            self._handle_media_message(message, chat_id)
            return

        # Inbound message oluştur
        from core.communication_manager import InboundMessage, InboundType, get_communication_manager

        communication_manager = self._comm_manager or get_communication_manager()

        inbound_type = communication_manager.resolve_inbound_type(text)
        task_id = None
        approval_id = None

        # Task ID'yi çöz
        task_id = communication_manager.extract_task_id(text)

        # Reply üzerinden task çöz
        if not task_id and reply_to_id:
            task_id = self._resolve_task_from_reply(chat_id, reply_to_id)

        session_id = f"telegram:{chat_id}"
        with self._conversation_lock:
            history = self._conversation_history.setdefault(session_id, [])
            context = {
                "channel": "telegram",
                "session_id": session_id,
                "telegram_user_id": user_id,
                "telegram_chat_id": chat_id,
                "telegram_message_id": message.get("message_id"),
                "username": from_user.get("username", ""),
                "first_name": user_name,
                "history": list(history[-10:]),
            }
            history.append({"role": "user", "content": text})

        inbound = InboundMessage(
            channel="telegram",
            sender_id=str(user_id),
            sender_name=user_name,
            text=text,
            inbound_type=inbound_type,
            task_id=task_id,
            reply_to_message_id=reply_to_id,
            raw_data={"message_id": message.get("message_id")},
            context=context,
        )
        communication_manager.log_inbound(inbound)

        # Komut işleme
        if text.startswith("/"):
            self._handle_command(chat_id, text, user_id, user_name)
            return

        # Onay/Red komutu
        if inbound_type == InboundType.APPROVE.value:
            self._handle_approve(chat_id, task_id, user_id, user_name, text)
            return
        if inbound_type == InboundType.REJECT.value:
            self._handle_reject(chat_id, task_id, user_id, user_name, text)
            return

        # Normal text: shared CommunicationManager -> Agent -> Ollama.
        result = communication_manager.handle_inbound(inbound)
        with self._conversation_lock:
            self._conversation_history[session_id].append(
                {"role": "assistant", "content": str(result)}
            )
            self._conversation_history[session_id] = self._conversation_history[session_id][-20:]
        communication_manager.send_text(
            "telegram",
            str(result),
            task_id=task_id,
            telegram_chat_id=chat_id,
        )

    def _handle_media_message(self, message: dict, chat_id: int):
        """Route supported Telegram media through existing UMAY readers."""
        if message.get("voice"):
            self._send_message(chat_id, "🎙️ Voice mesajları henüz desteklenmiyor.")
            return

        media_kind = ""
        file_id = None
        suffix = ".bin"
        if message.get("photo"):
            media_kind = "photo"
            photo = message["photo"]
            if isinstance(photo, list) and photo:
                file_id = photo[-1].get("file_id")
            suffix = ".jpg"
        elif message.get("document"):
            media_kind = "document"
            document = message["document"]
            file_id = document.get("file_id")
            filename = Path(document.get("file_name", "")).name
            candidate = Path(filename).suffix
            if re.fullmatch(r"\.[A-Za-z0-9]{1,10}", candidate):
                suffix = candidate.lower()
            if suffix not in SUPPORTED_TELEGRAM_DOCUMENT_EXTENSIONS:
                self._send_message(chat_id, "⚠️ Bu belge türü desteklenmiyor.")
                return
            mime_type = document.get("mime_type", "")
            if mime_type and not (
                mime_type.startswith("text/")
                or mime_type.startswith("application/")
                or mime_type.startswith("image/")
            ):
                self._send_message(chat_id, "⚠️ Belge MIME türü desteklenmiyor.")
                return

        if not file_id:
            self._send_message(chat_id, "⚠️ Telegram medya bilgisi geçersiz.")
            return

        temporary_path = self._download_file(file_id, suffix)
        if temporary_path is None:
            self._send_message(chat_id, "⚠️ Telegram dosyası indirilemedi veya boyutu çok büyük.")
            return

        try:
            if media_kind == "photo":
                from core.vision_reader import analyze_image
                result = analyze_image(
                    temporary_path,
                    question=message.get("caption") or "Bu görseli analiz et.",
                    use_ocr=True,
                )
                response = result.get("analysis") or result.get("error") or "Görsel analiz sonucu boş."
            else:
                from core.document_reader import read_document
                result = read_document(temporary_path)
                response = result.get("content") or result.get("text") or result.get("error") or "Belge sonucu boş."
            self._send_message(chat_id, str(response))
        except Exception as exc:
            log(f"[TELEGRAM] Medya işleme hatası: {type(exc).__name__}")
            self._send_message(chat_id, "⚠️ Medya işlenirken hata oluştu.")
        finally:
            try:
                Path(temporary_path).unlink(missing_ok=True)
            except OSError:
                pass

    def _download_file(self, file_id: str, suffix: str) -> str | None:
        """Download a Telegram file into a bounded temporary file."""
        try:
            if getattr(self, "_http_client", None):
                metadata_response = self._http_client.get(
                    f"/bot{TELEGRAM_BOT_TOKEN}/getFile", params={"file_id": file_id}
                )
            else:
                import requests
                metadata_response = requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
                    params={"file_id": file_id}, timeout=15)
            if not self._telegram_response_ok(metadata_response):
                return None
            file_path = metadata_response.json().get("result", {}).get("file_path")
            if not file_path:
                return None

            if getattr(self, "_http_client", None):
                response = self._http_client.get(
                    f"/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                )
            else:
                import requests
                response = requests.get(
                    f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
                    timeout=30)
            headers = getattr(response, "headers", {}) or {}
            content_length = headers.get("content-length")
            if content_length and int(content_length) > TELEGRAM_MAX_FILE_BYTES:
                return None
            if getattr(response, "status_code", 0) != 200:
                return None
            content = response.content
            if len(content) > TELEGRAM_MAX_FILE_BYTES:
                return None
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(content)
                return handle.name
        except Exception as exc:
            log(f"[TELEGRAM] Dosya indirme hatası: {type(exc).__name__}")
            return None

    def _handle_callback_query(self, callback_query: dict):
        """Inline button tıklamasını işle."""
        from_user = callback_query.get("from", {})
        user_id = from_user.get("id", 0)
        chat_id = callback_query.get("message", {}).get("chat", {}).get("id", 0)
        data = callback_query.get("data", "")
        callback_id = callback_query.get("id")

        if not self._is_authorized(user_id):
            if callback_id:
                self._answer_callback(callback_id, "⛔ Yetkisiz")
            return

        # Callback data: "approve:TASK_ID" veya "reject:TASK_ID"
        answer = "İşlem tanınamadı."
        try:
            if data.startswith("approve:"):
                task_id = data.split(":", 1)[1]
                self._handle_approve(chat_id, task_id, user_id, "callback", "")
                answer = "✅ Onay işlendi"
            elif data.startswith("reject:"):
                task_id = data.split(":", 1)[1]
                self._handle_reject(chat_id, task_id, user_id, "callback", "")
                answer = "❌ Red işlendi"
        finally:
            if callback_id:
                self._answer_callback(callback_id, answer)

    # ─── Command Handling ──────────────────────────────────────────────

    def _handle_command(self, chat_id: int, text: str, user_id: int, user_name: str):
        """Telegram komutlarını işle."""
        parts = text.strip().split()
        cmd = parts[0].split("@", 1)[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd in {"/approve", "/reject", "/cancel"} and args:
            if not re.fullmatch(r"task-\d{8}-\d{6}-[a-f0-9]{8}", args[0], re.IGNORECASE):
                self._send_message(chat_id, "⚠️ Geçersiz task ID.")
                return

        if cmd == "/start":
            self._send_message(
                chat_id,
                "🤖 **UMAY Agent**\n\n"
                "Merhaba! Ben UMAY'ım.\n"
                "Sana yardımcı olmak için buradayım.\n\n"
                "Komutlar:\n"
                "/help — Yardım\n"
                "/status — Durum\n"
                "/tasks — Bekleyen görevler"
            )
        elif cmd == "/help":
            self._send_message(
                chat_id,
                "📋 **UMAY Komutları**\n\n"
                "/start — Başlangıç mesajı\n"
                "/help — Bu mesaj\n"
                "/status — Sistem durumu\n"
                "/tasks — Bekleyen görevler\n"
                "/approve TASK_ID — Görevi onayla\n"
                "/reject TASK_ID — Görevi reddet\n\n"
                "Doğal dil:\n"
                "ONAYLA / EVET / TAMAM → Onay\n"
                "HAYIR / RED / İPTAL → Red"
            )
        elif cmd == "/status":
            self._handle_status(chat_id)
        elif cmd == "/tasks":
            self._handle_tasks(chat_id)
        elif cmd == "/approve":
            task_id = args[0] if args else None
            self._handle_approve(chat_id, task_id, user_id, user_name, "")
        elif cmd == "/reject":
            task_id = args[0] if args else None
            self._handle_reject(chat_id, task_id, user_id, user_name, "")
        elif cmd == "/cancel":
            task_id = args[0] if args else None
            self._handle_cancel(chat_id, task_id, user_id, user_name)
        else:
            self._send_message(chat_id, f"❓ Bilinmeyen komut: {cmd}\nYardım için /help")

    def _handle_status(self, chat_id: int):
        """Sistem durumunu göster."""
        from core.engine import ollama_available

        ollama_status = "🟢 ONLINE" if ollama_available() else "🔴 OFFLINE"
        docker_status = "🟢 RUNNING"

        pending_count = 0
        if self._approval_manager:
            pending_count = len(self._approval_manager.list_pending())

        text = (
            f"🟢 **UMAY ONLINE**\n\n"
            f"Docker: {docker_status}\n"
            f"Ollama: {ollama_status}\n"
            f"Bekleyen onay: {pending_count}\n"
            f"Telegram: 🟢 BAĞLI"
        )
        self._send_message(chat_id, text)

    def _handle_tasks(self, chat_id: int):
        """Bekleyen görevleri göster."""
        from core.task_state import pending_tasks

        tasks = pending_tasks()
        if not tasks:
            self._send_message(chat_id, "📋 Bekleyen görev yok.")
            return

        text = "📋 **BEKLEYEN GÖREVLER**\n\n"
        for i, task in enumerate(tasks[:10], 1):
            task_id = task.get("task_id", "?")
            status = task.get("status", "?")
            action = task.get("action", "")
            text += f"{i}. `{task_id}`\n   Durum: {status}\n"
            if action:
                text +=   f"   İşlem: {action}\n"
            text += "\n"

        text += "Onay için: /approve TASK_ID"
        self._send_message(chat_id, text)

    # ─── Approval Handling ─────────────────────────────────────────────

    def _handle_approve(self, chat_id: int, task_id: str | None, user_id: int, user_name: str, text: str):
        """Onay işlemini yönet."""
        if not self._approval_manager:
            self._send_message(chat_id, "❌ Approval Manager bağlı değil.")
            return
        if not task_id:
            pending = self._approval_manager.list_pending(user_id=user_id, chat_id=chat_id)
            if len(pending) == 1:
                task_id = pending[0].task_id
            elif len(pending) > 1:
                msg = "⚠️ Birden fazla görev bekliyor:\n\n"
                for item in pending[:5]:
                    msg += f"• `{item.task_id}` — {item.action[:50]}\n"
                self._send_message(chat_id, msg + "\nLütfen /approve TASK_ID yazın.")
                return
            else:
                self._send_message(chat_id, "📋 Onay bekleyen görev yok.")
                return

        approval = self._approval_manager.get_pending_for_task(
            task_id, user_id=user_id, chat_id=chat_id
        )
        if not approval:
            self._send_message(chat_id, f"⚠️ `{task_id}` için bekleyen onay bulunamadı.")
            return

        result = self._approval_manager.approve(
            approval.id,
            responded_by=f"telegram:{user_id}",
            message=text,
        )
        if not result:
            self._send_message(chat_id, f"❌ Onay verilemedi: `{task_id}`")
            return

        self._send_message(
            chat_id,
            f"✅ **Onaylandı**\n\nGörev: `{task_id}`\n"
            f"Tool: {approval.tool_name}\nİşlem: {approval.action}\n\n"
            "Agent devam ediyor...",
        )
        self._resume_agent(
            task_id,
            context={
                "channel": "telegram",
                "telegram_user_id": user_id,
                "telegram_chat_id": chat_id,
                "resume": True,
            },
        )

    def _handle_reject(self, chat_id: int, task_id: str | None, user_id: int, user_name: str, text: str):
        """Red işlemini yönet."""
        if not self._approval_manager:
            self._send_message(chat_id, "❌ Approval Manager bağlı değil.")
            return
        if not task_id:
            pending = self._approval_manager.list_pending(user_id=user_id, chat_id=chat_id)
            if len(pending) == 1:
                task_id = pending[0].task_id
            elif len(pending) > 1:
                self._send_message(chat_id, "⚠️ Birden fazla görev bekliyor; TASK_ID belirtin.")
                return
            else:
                self._send_message(chat_id, "📋 Onay bekleyen görev yok.")
                return

        approval = self._approval_manager.get_pending_for_task(
            task_id, user_id=user_id, chat_id=chat_id
        )
        if not approval:
            self._send_message(chat_id, f"⚠️ `{task_id}` için bekleyen onay bulunamadı.")
            return
        result = self._approval_manager.reject(
            approval.id,
            responded_by=f"telegram:{user_id}",
            message=text,
        )
        if result:
            from core.task_state import finish_task
            finish_task(approval.task_id, approval.pending_step or 0, "CANCELLED", "Telegram reddi")
            self._send_message(chat_id, f"❌ **Reddedildi**\n\nGörev: `{task_id}`")
        else:
            self._send_message(chat_id, f"❌ Red verilemedi: `{task_id}`")

    def _handle_cancel(self, chat_id: int, task_id: str | None, user_id: int, user_name: str):
        """İptal işlemini yönet."""
        if not task_id:
            self._send_message(chat_id, "⚠️ Task ID belirtin.\nKullanım: /cancel task-XXXXXXXX")
            return
        if not self._approval_manager:
            self._send_message(chat_id, "❌ Approval Manager bağlı değil.")
            return
        approval = self._approval_manager.get_pending_for_task(
            task_id, user_id=user_id, chat_id=chat_id
        )
        if not approval:
            self._send_message(chat_id, f"⚠️ `{task_id}` için bekleyen onay bulunamadı.")
            return
        result = self._approval_manager.cancel(
            approval.id, reason=f"Kullanıcı iptal etti: {user_id}"
        )
        if result:
            from core.task_state import finish_task
            finish_task(task_id, approval.pending_step or 0, "CANCELLED", "Telegram iptali")
            self._send_message(chat_id, f"⚪ **İptal Edildi**\n\nGörev: `{task_id}`")
        else:
            self._send_message(chat_id, f"❌ İptal edilemedi: `{task_id}`")

    # ─── Agent Resume ──────────────────────────────────────────────────

    def _resume_agent(self, task_id: str, context: dict | None = None):
        """Approval sonrası agent'ı resume et (background thread)."""
        def _do_resume():
            try:
                if self._agent_module:
                    with self._agent_execution_lock:
                        result = self._agent_module.run_agent(
                            f"Resume task: {task_id}",
                            task_id=task_id,
                            resume=True,
                            context=context,
                        )
                    log(f"[TELEGRAM] Resume tamamlandı: {task_id} → {result[:100]}")
            except Exception as exc:
                log(f"[TELEGRAM] Resume hatası: {exc}")

        thread = threading.Thread(target=_do_resume, daemon=True)
        thread.start()

    # ─── Outbound: UMAY → Telegram ────────────────────────────────────

    def send_message(self, outbound_msg):
        """Communication Manager'dan gelen outbound mesajı Telegram'a gönder."""
        if not self._bot or not outbound_msg.telegram_chat_id:
            return

        chat_id = outbound_msg.telegram_chat_id
        text = outbound_msg.body

        # Inline keyboard ekle (approval required ise)
        keyboard = None
        if outbound_msg.message_type == "APPROVAL_REQUIRED" and outbound_msg.callback_data:
            task_id = outbound_msg.callback_data.get("task_id", "")
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ ONAYLA", "callback_data": f"approve:{task_id}"},
                        {"text": "❌ REDDET", "callback_data": f"reject:{task_id}"},
                    ]
                ]
            }

        self._send_message(chat_id, text, reply_markup=keyboard)

    # ─── Utility ───────────────────────────────────────────────────────

    @staticmethod
    def _message_chunks(text: str, limit: int = 4000) -> list[str]:
        if len(text) <= limit:
            return [text]
        chunks = []
        remaining = text
        while remaining:
            cut = min(limit, len(remaining))
            if cut < len(remaining):
                boundary = remaining.rfind("\n", 0, cut)
                if boundary > limit // 2:
                    cut = boundary
            chunks.append(remaining[:cut])
            remaining = remaining[cut:]
        return chunks

    def _send_message(self, chat_id: int, text: str, reply_markup: dict | None = None):
        """Telegram API'ye kontrollü, chunk'lanmış mesaj gönder."""
        for index, chunk in enumerate(self._message_chunks(str(text))):
            markup = reply_markup if index == 0 else None
            payload = {"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"}
            if markup:
                payload["reply_markup"] = json.dumps(markup)
            response = self._send_telegram_json("/sendMessage", payload, timeout=10)
            if not self._telegram_response_ok(response):
                fallback = {"chat_id": chat_id, "text": chunk}
                if markup:
                    fallback["reply_markup"] = json.dumps(markup)
                fallback_response = self._send_telegram_json("/sendMessage", fallback, timeout=10)
                if not self._telegram_response_ok(fallback_response):
                    status = getattr(fallback_response, "status_code", "no-response")
                    log(f"[TELEGRAM] Mesaj gönderilemedi; HTTP={status}")

    def _send_telegram_json(self, endpoint: str, payload: dict, timeout: int):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}{endpoint}"
        try:
            if getattr(self, "_http_client", None):
                return self._http_client.post(endpoint, json=payload)
            import requests
            return requests.post(url, json=payload, timeout=timeout)
        except Exception as exc:
            log(f"[TELEGRAM] API gönderim hatası: {type(exc).__name__}")
            return None

    @staticmethod
    def _telegram_response_ok(response) -> bool:
        if response is None or getattr(response, "status_code", 0) != 200:
            return False
        try:
            return bool(response.json().get("ok", False))
        except (ValueError, AttributeError, TypeError):
            return False

    def _answer_callback(self, callback_query_id: str, text: str):
        """Callback query cevabı."""
        payload = {"callback_query_id": callback_query_id, "text": text}
        response = self._send_telegram_json("/answerCallbackQuery", payload, timeout=5)
        if not self._telegram_response_ok(response):
            status = getattr(response, "status_code", "no-response")
            log(f"[TELEGRAM] Callback cevaplanamadı; HTTP={status}")

    def _is_authorized(self, user_id: int) -> bool:
        """Kullanıcı yetkili mi?"""
        if not self._authenticated_users:
            return False
        return user_id in self._authenticated_users

    def _resolve_task_from_reply(self, chat_id: int, reply_to_message_id: int) -> str | None:
        """Reply mesajı üzerinden task çöz."""
        # Bu.reply_to_message_id -> task binding'i JSONL'de aranabilir
        # Şimdilik basit çözüm: pending tasks'tan ara
        from core.task_state import pending_tasks
        tasks = pending_tasks()
        if len(tasks) == 1:
            return tasks[0].get("task_id")
        return None

    # ─── Public API for Communication Manager ──────────────────────────

    def get_chat_id(self) -> int | None:
        """Aktif Telegram chat ID'sini döndür (ilk yetkili kullanıcı)."""
        if self._authenticated_users:
            # Gerçek uygulamada bu mapping saklanmalı
            return None
        return None

    def set_chat_id(self, chat_id: int):
        """Telegram chat ID'sini ayarla (ilk mesaj geldiğinde otomatik)."""
        # Gelecekte conversation mapping için kullanılabilir
        pass


# ─── Module-level singleton ─────────────────────────────────────────────────

_adapter: TelegramAdapter | None = None


def get_telegram_adapter() -> TelegramAdapter:
    """Global TelegramAdapter singleton'ı."""
    global _adapter
    if _adapter is None:
        _adapter = TelegramAdapter()
    return _adapter


def is_telegram_configured() -> bool:
    """Telegram yapılandırılmış mı?"""
    return bool(TELEGRAM_BOT_TOKEN)

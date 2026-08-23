"""Telegram personal-account adapter using Telethon MTProto.

This adapter is intentionally separate from the Bot API adapter. It only
connects when an existing authorized session and a non-empty user allowlist
are present; the interactive login flow lives in scripts/telegram_user_login.py.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

from core.communication_manager import InboundMessage, InboundType
from core.utils.logger import log

ROOT = Path(__file__).resolve().parents[1]
SESSION_PATH = Path(os.getenv("TELEGRAM_USER_SESSION_PATH", "telegram_user_sessions/umay_user"))
if not SESSION_PATH.is_absolute():
    SESSION_PATH = ROOT / SESSION_PATH
MAX_FILE_BYTES = int(os.getenv("TELEGRAM_MAX_FILE_BYTES", "20000000"))
ACCEPT_OUTGOING = os.getenv("TELEGRAM_USER_ACCEPT_OUTGOING", "true").lower() == "true"
DOCUMENT_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".json", ".xml", ".html",
    ".py", ".js", ".ts", ".css", ".yaml", ".yml", ".toml", ".ini", ".log",
    ".sql", ".sh", ".bat", ".ps1",
}


def _ids(value: str) -> set[int]:
    result = set()
    for item in value.split(","):
        item = item.strip()
        if item.lstrip("-").isdigit():
            result.add(int(item))
    return result


class TelegramUserAdapter:
    """Persistent Telegram personal-account client backed by Telethon."""

    def __init__(self):
        self.api_id = int(os.getenv("TELEGRAM_USER_API_ID", "0") or "0")
        self.api_hash = os.getenv("TELEGRAM_USER_API_HASH", "")
        self.allowed_users = _ids(os.getenv("TELEGRAM_USER_ALLOWED_USER_ID", ""))
        self.allowed_chats = _ids(os.getenv("TELEGRAM_USER_ALLOWED_CHAT_ID", ""))
        self.session_path = SESSION_PATH
        self._comm_manager = None
        self._approval_manager = None
        self._agent_module = None
        self._client = None
        self._loop = None
        self._thread = None
        self._running = False
        self._ready = threading.Event()
        self._error = None
        self._agent_lock = threading.RLock()
        self._outgoing_msg_ids: set[int] = set()

    @classmethod
    def is_configured(cls) -> bool:
        api_id = os.getenv("TELEGRAM_USER_API_ID", "")
        api_hash = os.getenv("TELEGRAM_USER_API_HASH", "")
        allowed = os.getenv("TELEGRAM_USER_ALLOWED_USER_ID", "")
        allowed_chats = os.getenv("TELEGRAM_USER_ALLOWED_CHAT_ID", "")
        session = Path(os.getenv("TELEGRAM_USER_SESSION_PATH", "telegram_user_sessions/umay_user"))
        if not session.is_absolute():
            session = ROOT / session
        session_exists = session.exists() or session.with_suffix(".session").exists()
        return bool(api_id.isdigit() and api_hash and (allowed or allowed_chats) and session_exists)

    def is_active(self) -> bool:
        return self._running and self._ready.is_set()

    def set_communication_manager(self, manager):
        self._comm_manager = manager
        manager.register_adapter("telegram_user", self)
        manager.register_handler("TEXT", self._handle_text_inbound)

    def set_approval_manager(self, manager):
        self._approval_manager = manager

    def set_agent_module(self, module):
        self._agent_module = module

    def start(self) -> bool:
        if not self.is_configured():
            log("[TELEGRAM_USER] Session/API/allowlist yapılandırılmamış; user client başlatılmadı.")
            return False
        try:
            from telethon import TelegramClient, events
        except ImportError:
            log("[TELEGRAM_USER] Telethon kurulu değil; user client başlatılmadı.")
            return False

        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(
            target=self._run_thread,
            name="umay-telegram-user-client",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=15)
        if not self.is_active():
            if self._error:
                log(f"[TELEGRAM_USER] Başlatma hatası: {self._error}")
            return False
        return True

    def _run_thread(self):
        from telethon import TelegramClient, events
        log("[TELEGRAM_USER] Thread started — creating event loop")
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._client = TelegramClient(str(self.session_path), self.api_id, self.api_hash)
            log("[TELEGRAM_USER] TelegramClient created, connecting...")
            self._loop.run_until_complete(self._connect(events))
            if not self._ready.is_set():
                log("[TELEGRAM_USER] _ready not set after _connect — thread exiting")
                return
            log("[TELEGRAM_USER] Entering run_until_disconnected...")
            self._loop.run_until_complete(self._client.run_until_disconnected())
            log("[TELEGRAM_USER] Client disconnected — thread exiting")
        except Exception as exc:
            log(f"[TELEGRAM_USER][ERROR] Thread exception: {type(exc).__name__}: {exc}")
            self._error = type(exc).__name__
            self._running = False
            self._ready.set()
        finally:
            self._running = False
            if self._client and not self._client.is_connected():
                self._client = None
            self._loop.close()
            log("[TELEGRAM_USER] Thread finished — loop closed")

    async def _connect(self, events):
        log("[TELEGRAM_USER] Connecting to Telegram...")
        await self._client.connect()
        if not await self._client.is_user_authorized():
            log("[TELEGRAM_USER] Session yetkili değil; login bootstrap çalıştırılmalı.")
            await self._client.disconnect()
            self._ready.set()
            return
        me = await self._client.get_me()
        log(f"[TELEGRAM_USER] Logged in as: {me.first_name} (@{me.username}) ID={me.id}")
        # incoming=None: hem incoming hem outgoing mesajları dinle.
        # Self-message kontrolü _handle_event içinde yapılıyor (sonsuz döngü engeli).
        self._client.add_event_handler(self._handle_event, events.NewMessage())
        handlers = self._client.list_event_handlers()
        log(f"[TELEGRAM_USER] Event handlers registered: {len(handlers)}")
        self._running = True
        self._ready.set()
        log("[TELEGRAM_USER] User account client bağlandı — ready.")

    def stop(self):
        self._running = False
        if self._client and self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._client.disconnect(), self._loop)
            try:
                future.result(timeout=10)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15)

    async def _handle_event(self, event):
        log("[TELEGRAM_USER] EVENT_RECEIVED: message_id=" + str(event.message.id))
        sender_id = event.sender_id
        chat_id = event.chat_id
        if not self._authorized(sender_id, chat_id):
            log(f"[TELEGRAM_USER] UNAUTHORIZED: sender={sender_id} chat={chat_id}")
            return
        message = event.message
        # Self-message check: UMAY'nin kendi gonderdigi mesajlari isleme (sonsuz dongu engeli)
        if message.id in self._outgoing_msg_ids:
            self._outgoing_msg_ids.discard(message.id)
            log(f"[TELEGRAM_USER] SELF_MESSAGE_SKIP: msg_id={message.id}")
            return
        text = event.raw_text or ""
        log(f"[TELEGRAM_USER] MESSAGE_RECEIVED: sender={sender_id} text={text[:100]}")
        context = {
            "channel": "telegram_user",
            "session_id": f"telegram_user:{chat_id}",
            "telegram_user_id": sender_id,
            "telegram_chat_id": chat_id,
            "telegram_message_id": message.id,
            "account_type": "user",
        }
        if message.photo or message.document:
            await self._handle_media(event, chat_id)
            return
        if not text:
            return

        inbound_type = self._comm_manager.resolve_inbound_type(text)
        inbound = InboundMessage(
            channel="telegram_user",
            sender_id=str(sender_id),
            sender_name="telegram-user",
            text=text,
            inbound_type=inbound_type,
            raw_data={"message_id": message.id},
            context=context,
        )
        self._comm_manager.log_inbound(inbound)
        if text.startswith("/") or inbound_type in {InboundType.APPROVE.value, InboundType.REJECT.value}:
            await self._handle_approval_command(chat_id, sender_id, text)
            return
        result = await asyncio.to_thread(self._handle_text_inbound, inbound)
        self._comm_manager.send_text("telegram_user", str(result), telegram_chat_id=chat_id)

    def _authorized(self, user_id: int | None, chat_id: int | None) -> bool:
        if not self.allowed_users and not self.allowed_chats:
            return False
        return (user_id in self.allowed_users if self.allowed_users else False) or (
            chat_id in self.allowed_chats if self.allowed_chats else False
        )

    def _handle_text_inbound(self, message):
        log(f"[TELEGRAM_USER] ROUTING_TO_UMAY: text={message.text[:80]}")
        agent = self._agent_module
        if agent is None:
            log("[TELEGRAM_USER] ERROR: agent module not set")
            from core import agent
            agent = agent
        try:
            with self._agent_lock:
                result = agent.run_agent(message.text, context=message.context)
            log(f"[TELEGRAM_USER] UMAY_RESPONSE: {str(result)[:100]}")
            return result
        except Exception as e:
            log(f"[TELEGRAM_USER][ERROR] Agent failed: {e}")
            return f"Agent hatası: {e}"

    async def _handle_approval_command(self, chat_id: int, user_id: int, text: str):
        parts = text.strip().split()
        command = parts[0].split("@", 1)[0].lower() if parts else ""
        task_id = parts[1] if len(parts) > 1 else None
        if command in {"/approve", "/reject", "/cancel"} and task_id:
            if not re.fullmatch(r"task-\d{8}-\d{6}-[a-f0-9]{8}", task_id, re.IGNORECASE):
                await self._send_text(chat_id, "Geçersiz task ID.")
                return
        if command not in {"/approve", "/reject", "/cancel"}:
            await self._send_text(chat_id, "User account komutları: /approve, /reject, /cancel")
            return
        if not task_id or not self._approval_manager:
            await self._send_text(chat_id, "Task ID gerekli veya approval manager bağlı değil.")
            return
        approval = self._approval_manager.get_pending_for_task(task_id, user_id=user_id, chat_id=chat_id)
        if not approval:
            await self._send_text(chat_id, "Bu task için yetkili bekleyen approval bulunamadı.")
            return
        if command == "/approve":
            result = self._approval_manager.approve(approval.id, responded_by=f"telegram_user:{user_id}")
            if result:
                await self._send_text(chat_id, "Approval kabul edildi; Agent devam ediyor.")
                await asyncio.to_thread(self._resume_agent, task_id, user_id, chat_id)
        elif command == "/reject":
            result = self._approval_manager.reject(approval.id, responded_by=f"telegram_user:{user_id}")
            if result:
                await self._send_text(chat_id, "Approval reddedildi.")
        else:
            result = self._approval_manager.cancel(approval.id, reason=f"telegram_user:{user_id}")
            if result:
                await self._send_text(chat_id, "Approval iptal edildi.")

    def _resume_agent(self, task_id: str, user_id: int, chat_id: int):
        if not self._agent_module:
            return
        context = {
            "channel": "telegram_user",
            "telegram_user_id": user_id,
            "telegram_chat_id": chat_id,
            "resume": True,
        }
        with self._agent_lock:
            self._agent_module.run_agent(
                f"Resume task: {task_id}", task_id=task_id, resume=True, context=context
            )

    async def _handle_media(self, event, chat_id: int):
        file_info = getattr(event.message, "file", None)
        filename = getattr(file_info, "name", None) or ".bin"
        suffix = ".jpg" if event.message.photo else Path(filename).suffix.lower()
        if suffix not in DOCUMENT_EXTENSIONS and suffix != ".jpg":
            await self._send_text(chat_id, "Desteklenmeyen medya türü.")
            return
        mime_type = getattr(file_info, "mime_type", "") or ""
        if mime_type and not (
            mime_type.startswith("text/")
            or mime_type.startswith("application/")
            or mime_type.startswith("image/")
        ):
            await self._send_text(chat_id, "Belge MIME türü desteklenmiyor.")
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            temporary_path = handle.name
        try:
            downloaded = await event.download_media(file=temporary_path)
            if not downloaded or Path(temporary_path).stat().st_size > MAX_FILE_BYTES:
                await self._send_text(chat_id, "Dosya indirilemedi veya boyutu çok büyük.")
                return
            if suffix == ".jpg":
                from core.vision_reader import analyze_image
                result = await asyncio.to_thread(analyze_image, temporary_path, use_ocr=True)
                response = result.get("analysis") or result.get("error", "Vision sonucu boş.")
            else:
                from core.document_reader import read_document
                result = await asyncio.to_thread(read_document, temporary_path)
                response = result.get("content") or result.get("text") or result.get("error", "Belge sonucu boş.")
            await self._send_text(chat_id, str(response))
        finally:
            try:
                Path(temporary_path).unlink(missing_ok=True)
            except OSError:
                pass

    def send_message(self, outbound_msg):
        chat_id = outbound_msg.telegram_chat_id
        if not chat_id or not self.is_active() or not self._loop:
            return
        if threading.current_thread() is self._thread:
            self._loop.create_task(self._send_text(chat_id, outbound_msg.body))
            return
        future = asyncio.run_coroutine_threadsafe(
            self._send_text(chat_id, outbound_msg.body), self._loop
        )
        try:
            future.result(timeout=30)
        except Exception as exc:
            log(f"[TELEGRAM_USER] Outbound hata: {type(exc).__name__}")

    async def _send_text(self, chat_id: int, text: str):
        log(f"[TELEGRAM_USER] RESPONSE_SENDING: chat={chat_id} len={len(str(text))}")
        for index in range(0, len(str(text)) or 1, 4000):
            chunk = str(text)[index:index + 4000]
            msg = await self._client.send_message(chat_id, chunk)
            if msg and hasattr(msg, 'id'):
                self._outgoing_msg_ids.add(msg.id)
        log(f"[TELEGRAM_USER] RESPONSE_SENT: chat={chat_id}")


_user_adapter: TelegramUserAdapter | None = None


def get_telegram_user_adapter() -> TelegramUserAdapter:
    global _user_adapter
    if _user_adapter is None:
        _user_adapter = TelegramUserAdapter()
    return _user_adapter

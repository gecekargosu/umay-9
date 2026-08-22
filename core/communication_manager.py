"""UMAY Communication Manager — Kanal bağımsız mesaj yönlendirme.

UMAY Core ile dış adapter'lar (Telegram, Web, Voice) arasındaki
iletişimi yönetir. Channel-agnostic tasarım.

Mimari:
    UMAY CORE
        ↓
    Communication Manager
        ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
  WEB CHAT   TELEGRAM    VOICE (gelecek)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable


# ─── Constants ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
COMM_LOG = ROOT / "logs" / "communication.jsonl"


# ─── Message Types ──────────────────────────────────────────────────────────

class MessageType(str, Enum):
    """UMAY'dan dışarıya gönderilen mesaj türleri."""
    TASK_STARTED = "TASK_STARTED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    TASK_ERROR = "TASK_ERROR"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_CANCELLED = "TASK_CANCELLED"
    STATUS_UPDATE = "STATUS_UPDATE"
    TEXT = "TEXT"


class InboundType(str, Enum):
    """Dışarıdan UMAY'a gelen mesaj türleri."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    COMMAND = "COMMAND"
    TEXT = "TEXT"


# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class OutboundMessage:
    """UMAY'dan dışarıya gönderilen mesaj."""
    id: str
    channel: str  # "telegram", "web", "voice"
    message_type: str  # MessageType value
    task_id: str | None = None
    approval_id: str | None = None
    title: str = ""
    body: str = ""
    action: str = ""
    target: str = ""
    risk: str = ""
    tool_name: str = ""
    created_at: float = 0.0
    # Telegram-specific
    telegram_chat_id: int | None = None
    telegram_message_id: int | None = None
    # Callback data for inline buttons
    callback_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class InboundMessage:
    """Dışarıdan UMAY'a gelen mesaj."""
    channel: str
    sender_id: str
    sender_name: str
    text: str
    inbound_type: str  # InboundType value
    task_id: str | None = None
    approval_id: str | None = None
    reply_to_message_id: int | None = None
    raw_data: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


# ─── Communication Manager ─────────────────────────────────────────────────

class CommunicationManager:
    """Kanal bağımsız mesaj yönlendirme.

    Adapter'lar register_adapter() ile bağlanır.
    Outbound mesajlar doğru adapter'a yönlendirilir.
    Inbound mesajlar ilgili handler'a iletilir.
    """

    def __init__(self):
        self._adapters: dict[str, Any] = {}  # channel -> adapter
        self._handlers: dict[str, list[Callable]] = {}  # inbound_type -> handlers
        self._message_log: list[OutboundMessage] = []

    # ─── Adapter Management ────────────────────────────────────────────

    def register_adapter(self, channel: str, adapter: Any):
        """Bir communication adapter'ı kaydet."""
        self._adapters[channel] = adapter

    def get_adapter(self, channel: str):
        """Kanal adapter'ını al."""
        return self._adapters.get(channel)

    def is_channel_active(self, channel: str) -> bool:
        """Kanal aktif mi?"""
        adapter = self._adapters.get(channel)
        if adapter and hasattr(adapter, "is_active"):
            return adapter.is_active()
        return False

    # ─── Outbound: UMAY → Dış Dünya ───────────────────────────────────

    def send_task_started(self, channel: str, task_id: str, description: str = ""):
        """Görev başladığını bildir."""
        msg = OutboundMessage(
            id=f"msg-{int(time.time())}",
            channel=channel,
            message_type=MessageType.TASK_STARTED.value,
            task_id=task_id,
            title="🔵 Görev Başladı",
            body=description or f"Görev başlatıldı: {task_id}",
            created_at=time.time(),
        )
        self._send(channel, msg)

    def send_approval_required(
        self,
        channel: str,
        task_id: str,
        approval_id: str,
        tool_name: str,
        action: str,
        target: str = "",
        risk: str = "medium",
        telegram_chat_id: int | None = None,
    ):
        """Onay gerektiğini bildir."""
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "⛔"}.get(risk, "🟡")

        body = (
            f"📋 **Görev:** {task_id}\n"
            f"🔧 **Tool:** {tool_name}\n"
            f"📝 **İşlem:** {action}\n"
        )
        if target:
            body += f"🎯 **Hedef:** {target}\n"
        body += f"{risk_emoji} **Risk:** {risk}\n\n"
        body += "Devam etmem için onaylıyor musun?"

        msg = OutboundMessage(
            id=f"msg-{int(time.time())}",
            channel=channel,
            message_type=MessageType.APPROVAL_REQUIRED.value,
            task_id=task_id,
            approval_id=approval_id,
            title=f"{risk_emoji} UMAY Onay Bekliyor",
            body=body,
            action=action,
            target=target,
            risk=risk,
            tool_name=tool_name,
            created_at=time.time(),
            telegram_chat_id=telegram_chat_id,
            callback_data={"task_id": task_id, "approval_id": approval_id},
        )
        self._send(channel, msg)

    def send_task_completed(self, channel: str, task_id: str, summary: str = ""):
        """Görev tamamlandığını bildir."""
        msg = OutboundMessage(
            id=f"msg-{int(time.time())}",
            channel=channel,
            message_type=MessageType.TASK_COMPLETED.value,
            task_id=task_id,
            title="✅ Görev Tamamlandı",
            body=summary or f"Görev tamamlandı: {task_id}",
            created_at=time.time(),
        )
        self._send(channel, msg)

    def send_task_error(self, channel: str, task_id: str, error: str = ""):
        """Görev hatası bildir."""
        msg = OutboundMessage(
            id=f"msg-{int(time.time())}",
            channel=channel,
            message_type=MessageType.TASK_ERROR.value,
            task_id=task_id,
            title="🔴 Görev Hatası",
            body=error or f"Görev sırasında hata: {task_id}",
            created_at=time.time(),
        )
        self._send(channel, msg)

    def send_task_cancelled(self, channel: str, task_id: str, reason: str = ""):
        """Görev iptalini bildir."""
        msg = OutboundMessage(
            id=f"msg-{int(time.time())}",
            channel=channel,
            message_type=MessageType.TASK_CANCELLED.value,
            task_id=task_id,
            title="⚪ Görev İptal Edildi",
            body=reason or f"Görev iptal edildi: {task_id}",
            created_at=time.time(),
        )
        self._send(channel, msg)

    def send_text(
        self,
        channel: str,
        text: str,
        task_id: str | None = None,
        telegram_chat_id: int | None = None,
    ):
        """Serbest metin mesajı gönder."""
        msg = OutboundMessage(
            id=f"msg-{int(time.time())}",
            channel=channel,
            message_type=MessageType.TEXT.value,
            task_id=task_id,
            title="",
            body=text,
            created_at=time.time(),
            telegram_chat_id=telegram_chat_id,
        )
        self._send(channel, msg)

    # ─── Inbound: Dış Dünya → UMAY ────────────────────────────────────

    def handle_inbound(self, message: InboundMessage) -> str:
        """Gelen mesajı ilgili handler'a yönlendir.

        Returns:
            İşlem sonucu mesajı
        """
        # Handler'ları çağır
        handlers = self._handlers.get(message.inbound_type, [])
        for handler in handlers:
            try:
                result = handler(message)
                if result:
                    return str(result)
            except Exception as e:
                return f"İşlem hatası: {e}"

        return "İşlem tanınamadı."

    def register_handler(self, inbound_type: str, handler: Callable):
        """Inbound message handler'ı kaydet."""
        if inbound_type not in self._handlers:
            self._handlers[inbound_type] = []
        if handler not in self._handlers[inbound_type]:
            self._handlers[inbound_type].append(handler)

    # ─── Message Resolution ────────────────────────────────────────────

    @staticmethod
    def resolve_inbound_type(text: str) -> str:
        """Serbest metin mesajından inbound type çözümlle."""
        text_lower = text.lower().strip()

        # Onay komutları
        approve_words = {"evet", "onay", "onayla", "onaylıyorum", "tamam", "devam",
                         "devam et", "yap", "gönder", "approve", "yes", "ok"}
        reject_words = {"hayır", "hayir", "red", "reddet", "iptal", "dur", "olmaz",
                        "reject", "no", "cancel", "stop"}

        if text_lower in approve_words:
            return InboundType.APPROVE.value
        if text_lower in reject_words:
            return InboundType.REJECT.value

        # Komut kontrolü
        if text_lower.startswith("/"):
            return InboundType.COMMAND.value

        return InboundType.TEXT.value

    @staticmethod
    def extract_task_id(text: str) -> str | None:
        """Mesaj içinden task ID çıkar."""
        import re
        # task-YYYYMMDD-HHMMSS-XXXXXXXX formatı
        match = re.search(r'(task-\d{8}-\d{6}-[a-f0-9]{8})', text)
        if match:
            return match.group(1)
        # appr-YYYYMMDD-HHMMSS-XXXXXX formatı (approval ID)
        match = re.search(r'(appr-\d{8}-\d{6}-[a-f0-9]{6})', text)
        if match:
            return match.group(1)
        return None

    # ─── Internal ──────────────────────────────────────────────────────

    def _send(self, channel: str, message: OutboundMessage):
        """Mesajı ilgili adapter'a gönder."""
        self._message_log.append(message)
        self._log_message(message)

        adapter = self._adapters.get(channel)
        if adapter and hasattr(adapter, "send_message"):
            try:
                adapter.send_message(message)
            except Exception:
                pass

    def _log_message(self, message: OutboundMessage):
        """Mesajı JSONL'e logla."""
        try:
            COMM_LOG.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": time.time(),
                "direction": "outbound",
                **message.to_dict(),
            }
            with COMM_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def log_inbound(self, message: InboundMessage):
        """Inbound mesajı JSONL'e logla."""
        try:
            COMM_LOG.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": time.time(),
                "direction": "inbound",
                "channel": message.channel,
                "sender_id": message.sender_id,
                "text": message.text[:500],
                "inbound_type": message.inbound_type,
                "task_id": message.task_id,
            }
            with COMM_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


# ─── Module-level singleton ─────────────────────────────────────────────────

_manager: CommunicationManager | None = None


def get_communication_manager() -> CommunicationManager:
    """Global CommunicationManager singleton'ı."""
    global _manager
    if _manager is None:
        _manager = CommunicationManager()
    return _manager

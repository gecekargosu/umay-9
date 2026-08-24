"""UMAY Approval Manager — Task onay mekanizması.

WAITING_FOR_APPROVAL state'ini yönetir.
Channel-agnostic: Telegram, Web, Voice gibi herhangi bir adapter bağlanabilir.
Persistent: JSONL dosyasında saklanır, restart sonrası korunur.
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ─── Constants ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
APPROVAL_LOG = ROOT / "logs" / "approvals.jsonl"

# Timeout: 24 saat
DEFAULT_TIMEOUT_SECONDS = 86400

# Tools that require user approval before execution
APPROVAL_TOOLS: set[str] = {
    "write_file",
    "rollback_backup",
    "run_command",
    "run_terminal_command",
    "run_powershell",
    "browser_click",
    "browser_type",
    "gmail_send_email",
}


# ─── Enums ──────────────────────────────────────────────────────────────────

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    EXPIRED = "EXPIRED"


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RESUMING = "RESUMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ─── Data Model ─────────────────────────────────────────────────────────────

@dataclass
class ApprovalRequest:
    """Tek bir onay talebi."""
    id: str
    task_id: str
    tool_name: str
    action: str
    target: str
    reason: str
    risk: str  # "low", "medium", "high", "critical"
    created_at: float
    status: str  # ApprovalStatus value
    responded_at: float | None = None
    responded_by: str | None = None
    response_message: str | None = None
    expires_at: float | None = None
    tool_args: dict[str, Any] | None = None
    # Pending tool call info (for resume)
    pending_tool_call: dict[str, Any] | None = None
    pending_messages: list[dict[str, Any]] | None = None
    pending_step: int | None = None
    owner_user_id: int | None = None
    owner_chat_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRequest:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ─── Approval Manager ───────────────────────────────────────────────────────

class ApprovalManager:
    """Task onay mekanizmasını yönetir.

    Channel-agnostic: herhangi bir adapter (Telegram, Web, Voice)
    approve() / reject() / cancel() metodlarını çağırabilir.
    """

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds
        self._pending: dict[str, ApprovalRequest] = {}  # approval_id -> request
        self._callbacks: list = []
        self._load_pending()

    # ─── Public API ─────────────────────────────────────────────────────

    def request_approval(
        self,
        task_id: str,
        tool_name: str,
        action: str,
        target: str = "",
        reason: str = "",
        risk: str = "medium",
        tool_args: dict[str, Any] | None = None,
        pending_tool_call: dict[str, Any] | None = None,
        pending_messages: list[dict[str, Any]] | None = None,
        pending_step: int | None = None,
        owner_user_id: int | None = None,
        owner_chat_id: int | None = None,
    ) -> ApprovalRequest:
        """Yeni bir onay talebi oluştur.

        Args:
            task_id: İlgili task ID
            tool_name: Onay istenen tool adı
            action: Yapılacak işlem açıklaması
            target: Hedef dosya/komut/sayfa
            reason: Onay gerektirmesinin nedeni
            risk: Risk seviyesi (low/medium/high/critical)
            tool_args: Tool argümanları
            pending_tool_call: Duraklatılmış tool call bilgisi
            pending_messages: Duraklatılmış mesaj geçmişi
            pending_step: Duraklatılmış step numarası

        Returns:
            ApprovalRequest: Oluşturulan onay talebi
        """
        approval_id = f"appr-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        request = ApprovalRequest(
            id=approval_id,
            task_id=task_id,
            tool_name=tool_name,
            action=action,
            target=target,
            reason=reason,
            risk=risk,
            created_at=time.time(),
            status=ApprovalStatus.PENDING.value,
            expires_at=time.time() + self.timeout_seconds,
            tool_args=tool_args,
            pending_tool_call=pending_tool_call,
            pending_messages=pending_messages,
            pending_step=pending_step,
            owner_user_id=owner_user_id,
            owner_chat_id=owner_chat_id,
        )

        self._pending[approval_id] = request
        self._append_log(request, "created")
        self._notify_callbacks(request)
        return request

    def approve(
        self,
        approval_id: str,
        responded_by: str = "user",
        message: str = "",
    ) -> ApprovalRequest | None:
        """Onay ver.

        Args:
            approval_id: Onay talebi ID
            responded_by: Onayı veren (örn: "telegram:cengiz", "web:panel")
            message: Opsiyonel mesaj

        Returns:
            Güncellenmiş ApprovalRequest veya None (bulunamadıysa)
        """
        request = self._pending.get(approval_id)
        if not request:
            return None
        if request.status != ApprovalStatus.PENDING.value:
            return None

        request.status = ApprovalStatus.APPROVED.value
        request.responded_at = time.time()
        request.responded_by = responded_by
        request.response_message = message

        self._append_log(request, "approved")
        self._notify_callbacks(request)
        return request

    def reject(
        self,
        approval_id: str,
        responded_by: str = "user",
        message: str = "",
    ) -> ApprovalRequest | None:
        """Reddet.

        Args:
            approval_id: Onay talebi ID
            responded_by: Reddi yapan
            message: Red nedeni

        Returns:
            Güncellenmiş ApprovalRequest veya None
        """
        request = self._pending.get(approval_id)
        if not request:
            return None
        if request.status != ApprovalStatus.PENDING.value:
            return None

        request.status = ApprovalStatus.REJECTED.value
        request.responded_at = time.time()
        request.responded_by = responded_by
        request.response_message = message

        self._append_log(request, "rejected")
        self._notify_callbacks(request)
        return request

    def cancel(
        self,
        approval_id: str,
        reason: str = "",
    ) -> ApprovalRequest | None:
        """Onay talebini iptal et (sistem tarafından).

        Args:
            approval_id: Onay talebi ID
            reason: İptal nedeni

        Returns:
            Güncellenmiş ApprovalRequest veya None
        """
        request = self._pending.get(approval_id)
        if not request:
            return None
        if request.status != ApprovalStatus.PENDING.value:
            return None

        request.status = ApprovalStatus.CANCELLED.value
        request.responded_at = time.time()
        request.response_message = reason

        self._append_log(request, "cancelled")
        self._notify_callbacks(request)
        return request

    def get_pending(self, approval_id: str) -> ApprovalRequest | None:
        """Bekleyen onay talebini getir."""
        request = self._pending.get(approval_id)
        if request and request.status == ApprovalStatus.PENDING.value:
            return request
        return None

    def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        """Herhangi bir durumdaki approval kaydını getir."""
        request = self._pending.get(approval_id)
        if request:
            return request
        if not APPROVAL_LOG.exists():
            return None
        latest = None
        with APPROVAL_LOG.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("id") == approval_id:
                    latest = entry
        if not latest:
            return None
        try:
            return ApprovalRequest.from_dict(latest)
        except TypeError:
            return None

    def get_pending_for_task(
        self,
        task_id: str,
        user_id: int | None = None,
        chat_id: int | None = None,
    ) -> ApprovalRequest | None:
        """Belirli bir task'ın bekleyen onayını bul."""
        for request in self._pending.values():
            if (request.task_id == task_id and
                    request.status == ApprovalStatus.PENDING.value and
                    (user_id is None or request.owner_user_id == user_id) and
                    (chat_id is None or request.owner_chat_id == chat_id)):
                return request
        return None

    def list_pending(
        self,
        user_id: int | None = None,
        chat_id: int | None = None,
    ) -> list[ApprovalRequest]:
        """Tüm bekleyen onayları listele."""
        return [
            r for r in self._pending.values()
            if r.status == ApprovalStatus.PENDING.value
            and (user_id is None or r.owner_user_id == user_id)
            and (chat_id is None or r.owner_chat_id == chat_id)
        ]

    def check_timeout(self) -> list[ApprovalRequest]:
        """Zaman aşımına uğrayan onayları kontrol et ve işaretle."""
        now = time.time()
        timed_out = []
        for request in list(self._pending.values()):
            if (request.status == ApprovalStatus.PENDING.value and
                    request.expires_at and now > request.expires_at):
                request.status = ApprovalStatus.TIMEOUT.value
                request.responded_at = now
                request.response_message = "Onay süresi doldu"
                self._append_log(request, "timeout")
                self._notify_callbacks(request)
                timed_out.append(request)
        return timed_out

    def cleanup_old(self, max_age_seconds: int = 604800) -> int:
        """Eski onay kayıtlarını temizle (varsayılan: 7 gün)."""
        now = time.time()
        to_remove = []
        for aid, request in self._pending.items():
            if request.status != ApprovalStatus.PENDING.value:
                age = now - request.created_at
                if age > max_age_seconds:
                    to_remove.append(aid)
        for aid in to_remove:
            del self._pending[aid]
        return len(to_remove)

    # ─── Callbacks ──────────────────────────────────────────────────────

    def on_status_change(self, callback):
        """Durum değişikliğinde çağrılacak callback kaydet.

        İleride Telegram adapter bu callback'e bağlanabilir.
        """
        self._callbacks.append(callback)

    # ─── Tool Risk Classification ───────────────────────────────────────

    @staticmethod
    def tool_needs_approval(tool_name: str) -> bool:
        """Bu tool onay gerektiriyor mu?"""
        return tool_name in APPROVAL_TOOLS

    @staticmethod
    def get_tool_risk(tool_name: str) -> str:
        """Tool için risk seviyesini döndür."""
        HIGH_RISK = {"gmail_send_email", "rollback_backup", "run_command", "run_powershell"}
        MEDIUM_RISK = {"write_file", "browser_click", "browser_type", "run_terminal_command"}
        LOW_RISK = {"read_file", "list_directory", "search_files", "web_search", "browser_open",
                     "browser_read", "browser_screenshot", "read_document", "scan_directory",
                     "search_in_documents", "image_to_text", "describe_image", "image_qa",
                     "read_log_file", "get_system_info", "list_processes", "find_process",
                     "analyze_error", "read_code", "explain_code", "find_bugs"}
        if tool_name in HIGH_RISK:
            return "high"
        elif tool_name in MEDIUM_RISK:
            return "medium"
        elif tool_name in LOW_RISK:
            return "low"
        return "medium"  # Unknown tools default to medium risk

    @staticmethod
    def describe_action(tool_name: str, args: dict[str, Any]) -> tuple[str, str]:
        """Tool adı ve argümanlarından insancıl açıklama üret.

        Returns:
            (action, target) tuple
        """
        if tool_name == "write_file":
            path = args.get("path", "?")
            return f"Dosya oluşturulacak/güncellenecek: {path}", path
        elif tool_name == "run_command":
            cmd = args.get("command", "?")
            return f"Komut çalıştırılacak: {cmd}", cmd
        elif tool_name == "run_terminal_command":
            cmd = args.get("command", "?")
            return f"Terminal komutu çalıştırılacak: {cmd}", cmd
        elif tool_name == "run_powershell":
            cmd = args.get("command", "?")
            return f"PowerShell komutu çalıştırılacak: {cmd}", cmd
        elif tool_name == "browser_click":
            sel = args.get("selector", "?")
            return f"Tarayıcıda tıklama yapılacak: {sel}", sel
        elif tool_name == "browser_type":
            sel = args.get("selector", "?")
            text = args.get("text", "?")[:50]
            return f"Tarayıcıya veri yazılacak: {sel} → {text}...", sel
        elif tool_name == "rollback_backup":
            backup = args.get("backup_relative", "?")
            target = args.get("target_relative", "?")
            return f"Yedek geri yüklenecek: {backup} → {target}", target
        elif tool_name == "gmail_send_email":
            to = args.get("to", "?")
            subj = args.get("subject", "?")[:50]
            return f"E-posta gönderilecek: {to} — Konu: {subj}", to
        return f"İşlem: {tool_name}", tool_name

    # ─── Persistence ────────────────────────────────────────────────────

    def _append_log(self, request: ApprovalRequest, event: str):
        """Onay olayını JSONL'e yaz."""
        APPROVAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.time(),
            "event": event,
            **request.to_dict(),
        }
        with APPROVAL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_pending(self):
        """Başlangıçta pending onayları JSONL'den yükle."""
        if not APPROVAL_LOG.exists():
            return
        # Son durumları bul (her approval_id için en son event)
        latest: dict[str, dict[str, Any]] = {}
        with APPROVAL_LOG.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                aid = entry.get("id")
                if aid:
                    latest[aid] = entry

        # Hala PENDING olanları yükle
        for aid, entry in latest.items():
            if entry.get("status") == ApprovalStatus.PENDING.value:
                try:
                    request = ApprovalRequest.from_dict(entry)
                    # Timeout kontrolü
                    if request.expires_at and time.time() > request.expires_at:
                        request.status = ApprovalStatus.TIMEOUT.value
                        self._append_log(request, "timeout_on_load")
                    else:
                        self._pending[aid] = request
                except Exception:
                    pass

    def _notify_callbacks(self, request: ApprovalRequest):
        """Tüm kayıtlı callback'leri çağır."""
        for cb in self._callbacks:
            try:
                cb(request)
            except Exception:
                pass

    # ─── Serialization for Task State ───────────────────────────────────

    def to_task_state(self, task_id: str) -> dict[str, Any] | None:
        """Task'ın onay durumunu task state formatında döndür."""
        request = self.get_pending_for_task(task_id)
        if not request:
            return None
        return {
            "approval_id": request.id,
            "tool_name": request.tool_name,
            "action": request.action,
            "target": request.target,
            "risk": request.risk,
            "status": request.status,
            "created_at": request.created_at,
            "expires_at": request.expires_at,
        }


# ─── Module-level singleton ─────────────────────────────────────────────────

_manager: ApprovalManager | None = None


def get_approval_manager() -> ApprovalManager:
    """Global ApprovalManager singleton'ı."""
    global _manager
    if _manager is None:
        _manager = ApprovalManager()
    return _manager


def needs_approval(tool_name: str) -> bool:
    """便捷 fonksiyon: tool onay gerektiriyor mu?"""
    return ApprovalManager.tool_needs_approval(tool_name)


def request_approval(
    task_id: str,
    tool_name: str,
    action: str,
    target: str = "",
    reason: str = "",
    risk: str = "medium",
    tool_args: dict[str, Any] | None = None,
    pending_tool_call: dict[str, Any] | None = None,
    pending_messages: list[dict[str, Any]] | None = None,
    pending_step: int | None = None,
    owner_user_id: int | None = None,
    owner_chat_id: int | None = None,
) -> ApprovalRequest:
    """便捷 fonksiyon: onay talebi oluştur."""
    return get_approval_manager().request_approval(
        task_id=task_id,
        tool_name=tool_name,
        action=action,
        target=target,
        reason=reason,
        risk=risk,
        tool_args=tool_args,
        pending_tool_call=pending_tool_call,
        pending_messages=pending_messages,
        pending_step=pending_step,
        owner_user_id=owner_user_id,
        owner_chat_id=owner_chat_id,
    )


def approve(approval_id: str, responded_by: str = "user", message: str = "") -> ApprovalRequest | None:
    """便捷 fonksiyon: onay ver."""
    return get_approval_manager().approve(approval_id, responded_by=responded_by, message=message)


def reject(approval_id: str, responded_by: str = "user", message: str = "") -> ApprovalRequest | None:
    """便捷 fonksiyon: red et."""
    return get_approval_manager().reject(approval_id, responded_by=responded_by, message=message)


def cancel(approval_id: str, reason: str = "") -> ApprovalRequest | None:
    """便捷 fonksiyon: iptal et."""
    return get_approval_manager().cancel(approval_id, reason=reason)


def get_pending_approval(
    task_id: str,
    user_id: int | None = None,
    chat_id: int | None = None,
) -> ApprovalRequest | None:
    """便捷 fonksiyon: task'ın bekleyen onayını bul."""
    return get_approval_manager().get_pending_for_task(task_id, user_id=user_id, chat_id=chat_id)


def get_approval_by_id(approval_id: str) -> ApprovalRequest | None:
    """Herhangi bir durumdaki approval kaydını getir."""
    return get_approval_manager().get_by_id(approval_id)

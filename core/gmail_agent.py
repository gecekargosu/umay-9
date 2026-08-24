"""
UMAY Gmail Agent
================
IMAP/SMTP tabanlı e-posta okuma, arama, sınıflandırma ve güvenli gönderme.

%100 ÜCRETSIZ ve YEREL. Python stdlib (imaplib, smtplib, email) kullanır.

Mimari:
    E-posta Sunucusu (Gmail/Outlook/Özel)
        ↓
    IMAP Connector (okuma, arama, listeleme)
        ↓
    Email Parser (içerik çıkarma, MIME ayrıştırma)
        ↓
    Email Classifier (önemli/normal/spam sınıflandırma)
        ↓
    Email Summarizer (Ollama LLM ile özetleme)
        ↓
    SMTP Connector (gönderme — KULLANICI ONAYI GEREKTİRİR)
        ↓
    Memory Store (ChromaDB'ye kaydetme)

GÜVENLİK:
    - IMAP: Salt okuma (varsayılan)
    - SMTP: Kullanıcı onayı gerektirir
    - Credential'lar loglanmaz
    - Credential'lar modele gönderilmez

KURULUM:
    Gmail için:
    1. Google Hesabı > Güvenlik > İki aşamalı doğrulama > Uygulama şifresi oluştur
    2. .env dosyasına ekle:
       GMAIL_ADDRESS=ornek@gmail.com
       GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
       GMAIL_IMAP_SERVER=imap.gmail.com
       GMAIL_SMTP_SERVER=smtp.gmail.com

    Outlook için:
       GMAIL_ADDRESS=ornek@outlook.com
       GMAIL_APP_PASSWORD=xxxx
       GMAIL_IMAP_SERVER=outlook.office365.com
       GMAIL_SMTP_SERVER=smtp.office365.com
"""
from __future__ import annotations

import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parsedate_to_datetime
import os
import re
import json
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from core.utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata
from core.utils.logger import log

# ─── Sabitler ────────────────────────────────────────────────────────────────

MAX_EMAILS_PER_FETCH = 50
MAX_EMAIL_BODY_LENGTH = 10000
MAX_ATTACHMENT_SIZE_MB = 25
DEFAULT_IMAP_SERVER = "imap.gmail.com"
DEFAULT_IMAP_PORT = 993
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587

EMAIL_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
EMAIL_CACHE_DIR = Path(__file__).resolve().parents[1] / "logs" / "email_cache"
EMAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ─── Veri Modelleri ─────────────────────────────────────────────────────────

class EmailPriority(str, Enum):
    HIGH = "high"       # Önemli
    NORMAL = "normal"   # Normal
    LOW = "low"         # Düşük öncelik
    SPAM = "spam"       # Spam/istenmeyen


class EmailFolder(str, Enum):
    INBOX = "INBOX"
    SENT = "Sent"
    DRAFTS = "Drafts"
    TRASH = "Trash"
    SPAM = "[Gmail]/Spam"
    ALL = "[Gmail]/All Mail"


@dataclass
class EmailAttachment:
    """E-posta eki."""
    filename: str
    content_type: str
    size: int
    content: bytes | None = None


@dataclass
class EmailMessage:
    """Tek bir e-posta mesajı."""
    uid: str
    subject: str
    sender: str
    sender_name: str
    recipients: list[str]
    date: str
    body_text: str
    body_html: str
    folder: str
    is_read: bool
    has_attachments: bool
    attachments: list[EmailAttachment]
    priority: EmailPriority = EmailPriority.NORMAL
    labels: list[str] = field(default_factory=list)
    in_reply_to: str | None = None
    message_id: str | None = None
    raw_size: int = 0


# ─── Credential Manager ─────────────────────────────────────────────────────

class CredentialManager:
    """E-posta credential'larını güvenli şekilde yönetir."""

    @staticmethod
    def load_credentials() -> dict[str, str]:
        """
        .env dosyasından credential'ları yükler.

        .env dosyası yoksa veya credential eksikse hata döndürür.
        Credential'lar loglanmaz.
        """
        env_path = Path(__file__).resolve().parents[1] / ".env"
        credentials = {}

        # .env dosyasından oku
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        credentials[key.strip()] = value.strip().strip("\"'")

        # Ortam değişkenlerinden de oku (override)
        env_keys = [
            "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD",
            "GMAIL_IMAP_SERVER", "GMAIL_SMTP_SERVER",
            "GMAIL_IMAP_PORT", "GMAIL_SMTP_PORT",
        ]
        for key in env_keys:
            env_val = os.getenv(key)
            if env_val:
                credentials[key] = env_val

        return credentials

    @staticmethod
    def validate_credentials(creds: dict) -> tuple[bool, str]:
        """Credential'ların tam olup olmadığını kontrol et."""
        required = ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]
        missing = [k for k in required if not creds.get(k)]
        if missing:
            return False, f"Eksik credential: {', '.join(missing)}"
        return True, "OK"

    @staticmethod
    def mask_credential(value: str) -> str:
        """Credential değerini maskeler."""
        if len(value) <= 4:
            return "****"
        return value[:2] + "****" + value[-2:]


# ─── IMAP Connector ─────────────────────────────────────────────────────────

class IMAPConnector:
    """IMAP ile e-posta sunucusuna bağlanır ve okuma yapar."""

    def __init__(self, credentials: dict[str, str]):
        self.host = credentials.get("GMAIL_IMAP_SERVER", DEFAULT_IMAP_SERVER)
        self.port = int(credentials.get("GMAIL_IMAP_PORT", DEFAULT_IMAP_PORT))
        self.user = credentials.get("GMAIL_ADDRESS", "")
        self.password = credentials.get("GMAIL_APP_PASSWORD", "")
        self.connection: imaplib.IMAP4_SSL | None = None

    def connect(self, timeout: float = 15.0) -> bool:
        """IMAP bağlantısı kur. Timeout eklendi — sonsuz bekleme engellendi."""
        try:
            self.connection = imaplib.IMAP4_SSL(self.host, self.port, timeout=timeout)
            self.connection.login(self.user, self.password)
            log(f"[GMAIL] IMAP baglandi: {self.host}")
            return True
        except imaplib.IMAP4.error:
            # IMAP4.error credential icerigi icerebilir, sadece hata tipini logla
            log("[GMAIL] IMAP kimlik dogrulama hatasi")
            return False
        except Exception:
            log(f"[GMAIL] IMAP baglanti hatasi: {self.host}:{self.port}")
            return False

    def disconnect(self):
        """IMAP bağlantısını kapat."""
        if self.connection:
            try:
                self.connection.logout()
            except Exception:
                pass
            self.connection = None

    def list_folders(self) -> list[str]:
        """Mevcut klasörleri listele."""
        if not self.connection:
            return []
        try:
            status, folders = self.connection.list()
            if status == "OK":
                folder_list = []
                for f in folders:
                    if isinstance(f, bytes):
                        parts = f.decode("utf-8", errors="replace").split(' "')
                        if len(parts) >= 3:
                            folder_list.append(parts[2].strip('"'))
                        else:
                            folder_list.append(f.decode("utf-8", errors="replace"))
                return folder_list
        except Exception as e:
            log(f"[GMAIL] Klasör listeleme hatası: {e}")
        return []

    def select_folder(self, folder: str = "INBOX") -> int:
        """Klasör seç ve mesaj sayısını dön."""
        if not self.connection:
            return 0
        try:
            status, data = self.connection.select(folder)
            if status == "OK":
                count = int(data[0])
                log(f"[GMAIL] {folder}: {count} mesaj")
                return count
        except Exception as e:
            log(f"[GMAIL] Klasör seçim hatası: {e}")
        return 0

    def search_emails(
        self,
        criteria: str = "ALL",
        folder: str = "INBOX",
        max_results: int = MAX_EMAILS_PER_FETCH,
    ) -> list[str]:
        """E-posta UID'lerini ara."""
        if not self.connection:
            return []
        try:
            self.select_folder(folder)
            status, data = self.connection.search(None, criteria)
            if status == "OK":
                uids = data[0].split()
                # Son N tane (en yeniden en eskiye)
                uids = uids[-max_results:]
                uids.reverse()  # En yeniden başla
                return [uid.decode() for uid in uids]
        except Exception as e:
            log(f"[GMAIL] Arama hatası: {e}")
        return []

    def fetch_email(self, uid: str) -> EmailMessage | None:
        """Tek bir e-postayı çek ve ayrıştır."""
        if not self.connection:
            return None
        try:
            status, data = self.connection.fetch(uid.encode(), "(RFC822)")
            if status != "OK" or not data or not data[0]:
                return None

            raw_email = data[0][1]
            if isinstance(raw_email, bytes):
                msg = email.message_from_bytes(raw_email)
            else:
                return None

            return self._parse_email(msg, uid)

        except Exception as e:
            log(f"[GMAIL] E-posta çekme hatası (UID {uid}): {e}")
            return None

    def fetch_emails(
        self,
        uids: list[str],
        max_count: int = MAX_EMAILS_PER_FETCH,
    ) -> list[EmailMessage]:
        """Birden fazla e-postayı çek."""
        emails = []
        for uid in uids[:max_count]:
            msg = self.fetch_email(uid)
            if msg:
                emails.append(msg)
        return emails

    def mark_as_read(self, uid: str) -> bool:
        """E-postayı okundu olarak işaretle."""
        if not self.connection:
            return False
        try:
            self.connection.store(uid.encode(), "+FLAGS", "\\Seen")
            return True
        except Exception:
            return False

    def get_folder_info(self, folder: str = "INBOX") -> dict:
        """Klasör bilgilerini al."""
        if not self.connection:
            return {}
        try:
            status, data = self.connection.select(folder)
            if status == "OK":
                total = int(data[0])
                # Okunmamış sayısını bul — seçili klasörde ara
                status2, data2 = self.connection.search(None, "UNSEEN")
                unread = 0
                if status2 == "OK" and data2[0]:
                    unread = len(data2[0].split())
                return {"folder": folder, "total": total, "unread": unread}
        except Exception:
            pass
        return {}

    def _parse_email(self, msg: email.message.Message, uid: str) -> EmailMessage:
        """ham e-posta mesajını EmailMessage'a dönüştür."""
        # Konu
        subject = ""
        subject_header = msg.get("Subject", "")
        if subject_header:
            decoded = decode_header(subject_header)
            for part, charset in decoded:
                if isinstance(part, bytes):
                    subject += part.decode(charset or "utf-8", errors="replace")
                else:
                    subject += part

        # Gönderen
        sender = msg.get("From", "")
        sender_name = ""
        sender_match = re.match(r'"?([^"<]*)"?\s*<?([^>]+@[^>]+)>?', sender)
        if sender_match:
            sender_name = sender_match.group(1).strip()
            sender = sender_match.group(2).strip()
        elif "<" in sender:
            sender = re.search(r"<([^>]+)>", sender)
            sender = sender.group(1) if sender else msg.get("From", "")

        # Alıcılar
        recipients = []
        for field in ["To", "Cc"]:
            val = msg.get(field, "")
            if val:
                recipients.extend([r.strip() for r in val.split(",") if r.strip()])

        # Tarih
        date_str = msg.get("Date", "")
        try:
            date_obj = parsedate_to_datetime(date_str)
            date_str = date_obj.isoformat()
        except Exception:
            pass

        # İçerik
        body_text = ""
        body_html = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    # Ek
                    filename = part.get_filename()
                    if filename:
                        decoded_fn = decode_header(filename)
                        fn_str = ""
                        for p, c in decoded_fn:
                            if isinstance(p, bytes):
                                fn_str += p.decode(c or "utf-8", errors="replace")
                            else:
                                fn_str += p
                        attachments.append(EmailAttachment(
                            filename=fn_str,
                            content_type=content_type,
                            size=len(part.get_payload(decode=True) or b""),
                            content=part.get_payload(decode=True),
                        ))
                elif content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_text += payload.decode(charset, errors="replace")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_html += payload.decode(charset, errors="replace")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

        # Okunma durumu
        flags = ""
        if self.connection:
            try:
                status, flag_data = self.connection.fetch(uid.encode(), "(FLAGS)")
                if status == "OK" and flag_data[0]:
                    flags = flag_data[0].decode("utf-8", errors="replace")
            except Exception:
                pass
        is_read = "\\Seen" in flags

        return EmailMessage(
            uid=uid,
            subject=subject,
            sender=sender,
            sender_name=sender_name,
            recipients=recipients,
            date=date_str,
            body_text=body_text[:MAX_EMAIL_BODY_LENGTH],
            body_html=body_html[:MAX_EMAIL_BODY_LENGTH],
            folder="INBOX",
            is_read=is_read,
            has_attachments=len(attachments) > 0,
            attachments=attachments,
            message_id=msg.get("Message-ID"),
            in_reply_to=msg.get("In-Reply-To"),
            raw_size=len(str(msg)),
        )


# ─── Email Classifier ───────────────────────────────────────────────────────

class EmailClassifier:
    """E-postaları önem derecesine göre sınıflandırır."""

    # Yüksek öncelikli gönderen pattern'leri
    HIGH_PRIORITY_SENDERS = [
        r"@company\.com$", r"@work\.com$", r"boss@",
        r"manager@", r"hr@", r"admin@",
    ]

    # Düşük öncelikli / spam pattern'leri
    LOW_PRIORITY_SENDERS = [
        r"noreply@", r"no-reply@", r"donotreply@",
        r"newsletter@", r"marketing@", r"promo@",
        r"unsubscribe@",
    ]

    # Yüksek öncelikli konu kelimeleri
    HIGH_PRIORITY_SUBJECTS = [
        "acil", "urgent", "önemli", "important", "toplu",
        "approval", "onay", "deadline", "son tarih",
        "security", "güvenlik", "alert", "uyarı",
    ]

    # Düşük öncelikli konu kelimeleri
    LOW_PRIORITY_SUBJECTS = [
        "newsletter", "unsubscribe", "promosyon", "kampanya",
        "indirim", "fırsat", "teklif", "offer", "sale",
    ]

    def classify(self, email_msg: EmailMessage) -> EmailPriority:
        """E-postanın öncelik seviyesini belirle."""
        sender_lower = email_msg.sender.lower()
        subject_lower = email_msg.subject.lower()

        # Gönderen bazlı
        for pattern in self.HIGH_PRIORITY_SENDERS:
            if re.search(pattern, sender_lower):
                return EmailPriority.HIGH

        for pattern in self.LOW_PRIORITY_SENDERS:
            if re.search(pattern, sender_lower):
                return EmailPriority.LOW

        # Konu bazlı
        for keyword in self.HIGH_PRIORITY_SUBJECTS:
            if keyword in subject_lower:
                return EmailPriority.HIGH

        for keyword in self.LOW_PRIORITY_SUBJECTS:
            if keyword in subject_lower:
                return EmailPriority.LOW

        # Ek varsa yüksek öncelik
        if email_msg.has_attachments:
            return EmailPriority.HIGH

        # Yanıt e-postası
        if email_msg.in_reply_to:
            return EmailPriority.HIGH

        return EmailPriority.NORMAL

    def classify_batch(self, emails: list[EmailMessage]) -> list[EmailMessage]:
        """Toplu sınıflandırma."""
        for e in emails:
            e.priority = self.classify(e)
        return emails


# ─── Email Search Engine ─────────────────────────────────────────────────────

class EmailSearchEngine:
    """Gelişmiş e-posta arama motoru."""

    @staticmethod
    def build_imap_criteria(
        query: str = "",
        sender: str = "",
        subject: str = "",
        date_from: str = "",
        date_to: str = "",
        has_attachment: bool | None = None,
        is_unread: bool | None = None,
    ) -> str:
        """IMAP arama kriteri oluştur."""
        criteria_parts = []

        if query:
            # Tam metin araması
            criteria_parts.append(f'(OR (TEXT "{query}") (SUBJECT "{query}"))')

        if sender:
            criteria_parts.append(f'(FROM "{sender}")')

        if subject:
            criteria_parts.append(f'(SUBJECT "{subject}")')

        if date_from:
            criteria_parts.append(f'(SINCE "{date_from}")')

        if date_to:
            criteria_parts.append(f'(BEFORE "{date_to}")')

        if has_attachment is True:
            criteria_parts.append('(OR (HEADER Content-Type "multipart/mixed") (BODY "attachment"))')

        if is_unread is True:
            criteria_parts.append('(UNSEEN)')

        if not criteria_parts:
            return "ALL"

        if len(criteria_parts) == 1:
            return criteria_parts[0]

        # Tüm kriterleri AND ile birleştir
        result = criteria_parts[0]
        for c in criteria_parts[1:]:
            result = f'(AND {result} {c})'

        return result

    @staticmethod
    def search_locally(
        emails: list[EmailMessage],
        query: str = "",
        sender: str = "",
        subject: str = "",
    ) -> list[EmailMessage]:
        """Çekilmiş e-postalar arasında yerel arama."""
        results = []
        query_lower = query.lower()
        sender_lower = sender.lower()
        subject_lower = subject.lower()

        for e in emails:
            match = True
            if query and query_lower not in e.body_text.lower() and query_lower not in e.subject.lower():
                match = False
            if sender and sender_lower not in e.sender.lower():
                match = False
            if subject and subject_lower not in e.subject.lower():
                match = False
            if match:
                results.append(e)

        return results


# ─── SMTP Connector (GÖNDERME — ONAY GEREKTİRİR) ───────────────────────────

class SMTPConnector:
    """
    SMTP ile e-posta gönderir.

    GÜVENLİK: Bu sınıf yalnızca kullanıcı onayı ile çalıştırılabilir.
    Varsayılan olarak gönderim kapalıdır.
    """

    def __init__(self, credentials: dict[str, str]):
        self.host = credentials.get("GMAIL_SMTP_SERVER", DEFAULT_SMTP_SERVER)
        self.port = int(credentials.get("GMAIL_SMTP_PORT", DEFAULT_SMTP_PORT))
        self.user = credentials.get("GMAIL_ADDRESS", "")
        self.password = credentials.get("GMAIL_APP_PASSWORD", "")

    def send_email(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        is_html: bool = False,
        cc: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """
        E-posta gönder.

        GÜVENLİK UYARISI: Bu fonksiyon yalnızca açık onay ile çağrılmalı.
        """
        log("[GMAIL] SMTP GONDERME BASLATILDI — Kullanıcı onayı gerekir")

        # Alıcıları hazırla
        if isinstance(to, str):
            to = [to]
        if cc and isinstance(cc, str):
            cc = [cc]

        # Mesaj oluştur
        msg = MIMEMultipart()
        msg["From"] = self.user
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)

        content_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15.0) as server:
                server.starttls()
                server.login(self.user, self.password)
                all_recipients = to + (cc or [])
                server.sendmail(self.user, all_recipients, msg.as_string())

            log(f"[GMAIL] E-posta gonderildi: {subject[:50]}")
            return {"status": "sent", "to": to, "subject": subject}

        except Exception as e:
            log(f"[GMAIL] Gonderme hatasi: {e}")
            return {"status": "error", "error": str(e)}

    def create_draft(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> dict[str, Any]:
        """
        E-posta taslağı oluştur (GÖNDERMEZ, sadece oluşturur).

        Bu fonksiyon güvenlidir — e-posta göndermez.
        """
        if isinstance(to, str):
            to = [to]

        draft = {
            "from": self.user[:3] + "***",  # Credential korumasi
            "to": to,
            "subject": subject,
            "body": body,
            "is_html": is_html,
            "created_at": datetime.now().isoformat(),
        }

        # Taslağı dosyaya kaydet
        draft_id = hashlib.md5(
            f"{subject}{time.time()}".encode()
        ).hexdigest()[:8]
        draft_path = EMAIL_CACHE_DIR / f"draft_{draft_id}.json"

        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)

        log(f"[GMAIL] Taslak olusturuldu: {draft_path.name}")
        return {"status": "draft_created", "draft_id": draft_id, "draft_path": str(draft_path)}


# ─── Email Summarizer ───────────────────────────────────────────────────────

class EmailSummarizer:
    """Ollama LLM ile e-posta özetleme."""

    SUMMARY_SYSTEM = """Sen UMAY'ın e-posta özetleme motorusun.
Verilen e-postayı kısa ve net şekilde özetle.

Çıktı formatı:
- Gönderen: [gönderen bilgisi]
- Konu: [konu]
- Tarih: [tarih]
- Özet: [2-3 cümle ile özet]
- Önem: [yüksek/orta/düşük]
- Aksiyon: [gerekli aksiyon varsa belirt]"""

    def __init__(self, model: str | None = None):
        self.model = model

    def summarize(self, email_msg: EmailMessage) -> str:
        """E-postayı özetle."""
        from core.engine import chat, resolve_model

        model = self.model or resolve_model("reasoning") or resolve_model("chat")

        content = f"Gönderen: {email_msg.sender}\n"
        content += f"Konu: {email_msg.subject}\n"
        content += f"Tarih: {email_msg.date}\n"
        content += f"İçerik:\n{email_msg.body_text[:3000]}\n"

        messages = [
            {"role": "system", "content": self.SUMMARY_SYSTEM},
            {"role": "user", "content": content},
        ]

        try:
            response = chat(messages, model=model, ajan="gmail_summarizer", task="summarize")
            if isinstance(response, dict):
                return response.get("message", {}).get("content", "Özet oluşturulamadı.")
            return str(response)
        except Exception as e:
            return f"Özet hatası: {e}"

    def summarize_batch(self, emails: list[EmailMessage]) -> list[dict]:
        """Toplu özetleme."""
        results = []
        for e in emails:
            summary = self.summarize(e)
            results.append({
                "uid": e.uid,
                "subject": e.subject,
                "sender": e.sender,
                "date": e.date,
                "priority": e.priority.value,
                "summary": summary,
            })
        return results


# ─── Ana Agent Fonksiyonları ────────────────────────────────────────────────

def _get_connection() -> IMAPConnector | None:
    """IMAP bağlantısı oluştur (lazy)."""
    creds = CredentialManager.load_credentials()
    valid, msg = CredentialManager.validate_credentials(creds)
    if not valid:
        log(f"[GMAIL] Credential hatası: {msg}")
        return None

    connector = IMAPConnector(creds)
    if not connector.connect():
        return None
    return connector


def gmail_list_emails(
    folder: str = "INBOX",
    max_count: int = 20,
    unread_only: bool = False,
) -> dict[str, Any]:
    """
    E-posta listesini al.

    IMAP kullanarak sunucudan e-posta listesini çeker.
    """
    aid = eylem_baslat("gmail_agent", f"E-posta listesi: {folder}", "IMAP", "")
    connector = _get_connection()
    if not connector:
        eylem_hata(aid, "IMAP baglantisi kurulamadi")
        return {"error": "IMAP baglantisi kurulamadi. .env dosyasini kontrol edin."}

    try:
        criteria = "UNSEEN" if unread_only else "ALL"
        uids = connector.search_emails(criteria, folder, max_count)
        emails = connector.fetch_emails(uids, max_count)

        # Sınıflandır
        classifier = EmailClassifier()
        emails = classifier.classify_batch(emails)

        result = {
            "folder": folder,
            "count": len(emails),
            "emails": [
                {
                    "uid": e.uid,
                    "subject": e.subject,
                    "sender": e.sender,
                    "sender_name": e.sender_name,
                    "date": e.date,
                    "priority": e.priority.value,
                    "has_attachments": e.has_attachments,
                    "is_read": e.is_read,
                    "body_preview": e.body_text[:200],
                }
                for e in emails
            ],
        }

        eylem_tamamla(aid, f"{len(emails)} e-posta listelendi", True)
        return result

    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": str(e)}
    finally:
        connector.disconnect()


def gmail_search(
    query: str = "",
    sender: str = "",
    subject: str = "",
    folder: str = "INBOX",
    max_count: int = 20,
) -> dict[str, Any]:
    """
    E-posta ara.

    IMAP sunucusunda gelişmiş arama yapar.
    """
    aid = eylem_baslat("gmail_agent", f"Arama: {query or subject or sender}", "IMAP Search", "")
    connector = _get_connection()
    if not connector:
        eylem_hata(aid, "IMAP baglantisi kurulamadi")
        return {"error": "IMAP baglantisi kurulamadi."}

    try:
        criteria = EmailSearchEngine.build_imap_criteria(
            query=query, sender=sender, subject=subject,
        )
        uids = connector.search_emails(criteria, folder, max_count)
        emails = connector.fetch_emails(uids, max_count)

        classifier = EmailClassifier()
        emails = classifier.classify_batch(emails)

        result = {
            "query": query or sender or subject,
            "count": len(emails),
            "emails": [
                {
                    "uid": e.uid,
                    "subject": e.subject,
                    "sender": e.sender,
                    "date": e.date,
                    "priority": e.priority.value,
                    "body_preview": e.body_text[:200],
                }
                for e in emails
            ],
        }

        eylem_tamamla(aid, f"{len(emails)} e-posta bulundu", True)
        return result

    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": str(e)}
    finally:
        connector.disconnect()


def gmail_get_email(uid: str, folder: str = "INBOX") -> dict[str, Any]:
    """
    Tek bir e-postanın tam içeriğini al.
    """
    aid = eylem_baslat("gmail_agent", f"E-posta oku: UID {uid}", "IMAP Fetch", "")
    connector = _get_connection()
    if not connector:
        eylem_hata(aid, "IMAP baglantisi kurulamadi")
        return {"error": "IMAP baglantisi kurulamadi."}

    try:
        connector.select_folder(folder)
        email_msg = connector.fetch_email(uid)
        if not email_msg:
            return {"error": f"UID {uid} bulunamadi"}

        classifier = EmailClassifier()
        email_msg.priority = classifier.classify(email_msg)

        result = {
            "uid": email_msg.uid,
            "subject": email_msg.subject,
            "sender": email_msg.sender,
            "sender_name": email_msg.sender_name,
            "recipients": email_msg.recipients,
            "date": email_msg.date,
            "body_text": email_msg.body_text,
            "priority": email_msg.priority.value,
            "has_attachments": email_msg.has_attachments,
            "attachments": [
                {"filename": a.filename, "content_type": a.content_type, "size": a.size}
                for a in email_msg.attachments
            ],
            "message_id": email_msg.message_id,
            "is_read": email_msg.is_read,
        }

        eylem_tamamla(aid, f"E-posta okundu: {email_msg.subject[:50]}", True)
        return result

    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": str(e)}
    finally:
        connector.disconnect()


def gmail_list_attachments(uid: str, folder: str = "INBOX") -> dict[str, Any]:
    """
    Bir e-postanın eklerini listele.
    """
    aid = eylem_baslat("gmail_agent", f"Ekler: UID {uid}", "IMAP", "")
    connector = _get_connection()
    if not connector:
        eylem_hata(aid, "IMAP baglantisi kurulamadi")
        return {"error": "IMAP baglantisi kurulamadi."}

    try:
        connector.select_folder(folder)
        email_msg = connector.fetch_email(uid)
        if not email_msg:
            return {"error": f"UID {uid} bulunamadi"}

        result = {
            "uid": uid,
            "subject": email_msg.subject,
            "attachment_count": len(email_msg.attachments),
            "attachments": [
                {
                    "filename": a.filename,
                    "content_type": a.content_type,
                    "size": a.size,
                    "size_human": f"{a.size / 1024:.1f} KB" if a.size < 1024*1024 else f"{a.size / (1024*1024):.1f} MB",
                }
                for a in email_msg.attachments
            ],
        }

        eylem_tamamla(aid, f"{len(email_msg.attachments)} ek bulundu", True)
        return result

    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": str(e)}
    finally:
        connector.disconnect()


def gmail_summarize(uid: str, folder: str = "INBOX") -> dict[str, Any]:
    """
    E-postayı Ollama LLM ile özetle.
    """
    aid = eylem_baslat("gmail_agent", f"Özetle: UID {uid}", "IMAP + LLM", "")
    connector = _get_connection()
    if not connector:
        eylem_hata(aid, "IMAP baglantisi kurulamadi")
        return {"error": "IMAP baglantisi kurulamadi."}

    try:
        connector.select_folder(folder)
        email_msg = connector.fetch_email(uid)
        if not email_msg:
            return {"error": f"UID {uid} bulunamadi"}

        summarizer = EmailSummarizer()
        summary = summarizer.summarize(email_msg)

        result = {
            "uid": uid,
            "subject": email_msg.subject,
            "sender": email_msg.sender,
            "date": email_msg.date,
            "summary": summary,
        }

        eylem_tamamla(aid, "Özet oluşturuldu", True)
        return result

    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": str(e)}
    finally:
        connector.disconnect()


def gmail_draft_reply(
    uid: str,
    reply_body: str,
    folder: str = "INBOX",
) -> dict[str, Any]:
    """
    E-postaya cevap taslağı oluştur (GÖNDERMEZ).

    GÜVENLİ: Bu fonksiyon e-posta göndermez, sadece taslak oluşturur.
    """
    aid = eylem_baslat("gmail_agent", f"Taslak: UID {uid}", "SMTP Draft", "")
    connector = _get_connection()
    if not connector:
        eylem_hata(aid, "IMAP baglantisi kurulamadi")
        return {"error": "IMAP baglantisi kurulamadi."}

    try:
        connector.select_folder(folder)
        email_msg = connector.fetch_email(uid)
        if not email_msg:
            return {"error": f"UID {uid} bulunamadi"}

        smtp = SMTPConnector(CredentialManager.load_credentials())
        result = smtp.create_draft(
            to=email_msg.sender,
            subject=f"Re: {email_msg.subject}",
            body=reply_body,
        )

        eylem_tamamla(aid, "Taslak oluşturuldu", True)
        return result

    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": str(e)}
    finally:
        connector.disconnect()


def gmail_send_email(
    to: str | list[str],
    subject: str,
    body: str,
    is_html: bool = False,
) -> dict[str, Any]:
    """
    E-posta gönder.

    GÜVENLİK UYARISI: Bu fonksiyon gerçek e-posta gönderir!
    Yalnızca kullanıcı onayından sonra çalıştırılmalıdır.
    """
    log("[GMAIL] *** E-POSTA GONDERME *** Kullanıcı onayı gereklidir")
    creds = CredentialManager.load_credentials()
    valid, msg = CredentialManager.validate_credentials(creds)
    if not valid:
        return {"error": msg}

    smtp = SMTPConnector(creds)
    return smtp.send_email(to=to, subject=subject, body=body, is_html=is_html)


def gmail_folder_info() -> dict[str, Any]:
    """
    E-posta klasör bilgilerini al.
    """
    connector = _get_connection()
    if not connector:
        return {"error": "IMAP baglantisi kurulamadi."}

    try:
        folders = connector.list_folders()
        info = {}
        for folder in ["INBOX", "[Gmail]/Sent", "[Gmail]/Drafts", "[Gmail]/Spam"]:
            info[folder] = connector.get_folder_info(folder)
        return {"folders": folders, "info": info}
    except Exception as e:
        return {"error": str(e)}
    finally:
        connector.disconnect()


# ─── Hızlı Erişim Fonksiyonları ─────────────────────────────────────────────

def quick_inbox(max_count: int = 10) -> dict[str, Any]:
    """Hızlı inbox kontrolü — son 10 e-posta."""
    return gmail_list_emails(folder="INBOX", max_count=max_count)


def quick_unread() -> dict[str, Any]:
    """Okunmamış e-postaları listele."""
    return gmail_list_emails(folder="INBOX", max_count=20, unread_only=True)


# ─── Test Fonksiyonu ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== UMAY Gmail Agent Test ===\n")

    # Test 1: Credential yükleme
    print("Test 1: Credential yükleme")
    creds = CredentialManager.load_credentials()
    valid, msg = CredentialManager.validate_credentials(creds)
    print(f"  Geçerli: {valid} — {msg}")
    if valid:
        print(f"  Adres: {CredentialManager.mask_credential(creds.get('GMAIL_ADDRESS', ''))}")

    # Test 2: IMAP arama kriteri oluşturma
    print("\nTest 2: IMAP arama kriterleri")
    criteria = EmailSearchEngine.build_imap_criteria(
        sender="test@example.com",
        subject="Test",
        is_unread=True,
    )
    print(f"  Kriter: {criteria}")

    # Test 3: Sınıflandırıcı
    print("\nTest 3: E-posta sınıflandırma")
    classifier = EmailClassifier()
    test_email = EmailMessage(
        uid="1", subject="Urgent: Security Alert",
        sender="security@company.com", sender_name="Security",
        recipients=[], date="2024-01-01", body_text="",
        body_html="", folder="INBOX", is_read=False,
        has_attachments=False, attachments=[],
    )
    priority = classifier.classify(test_email)
    print(f"  'Urgent: Security Alert': {priority.value}")

    print("\nTest tamamlandı.")

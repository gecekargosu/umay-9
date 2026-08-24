"""UMAY File Manager — Secure file upload, storage, and document processing.

Handles file uploads from Web panel and Telegram.
Validates file types, prevents path traversal, enforces size limits.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import BinaryIO

from core.utils.logger import log

# Configuration
ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT / "uploads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".doc", ".txt", ".csv", ".xlsx", ".xls",
    ".pptx", ".ppt", ".md", ".rtf", ".odt", ".ods",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff",
    # Data
    ".json", ".xml", ".yaml", ".yml", ".toml",
    # Code
    ".py", ".js", ".ts", ".html", ".css", ".java", ".go", ".rs",
    ".cpp", ".c", ".h", ".sh", ".ps1", ".bat",
    # Archive
    ".zip", ".tar", ".gz",
}
DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".pif", ".vbs", ".js"}


class FileValidationError(Exception):
    pass


class FileTooLargeError(FileValidationError):
    pass


class DangerousFileError(FileValidationError):
    pass


class PathTraversalError(FileValidationError):
    pass


def _file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_filename(filename: str) -> str:
    """Sanitize filename — prevent path traversal."""
    # Remove path components
    filename = os.path.basename(filename)
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    return f"{name}{ext}"


def validate_file(filename: str, file_size: int) -> None:
    """Validate file before upload."""
    if not filename:
        raise FileValidationError("Dosya adı boş")

    ext = os.path.splitext(filename)[1].lower()

    if ext in DANGEROUS_EXTENSIONS:
        raise DangerousFileError(f"Tehlikeli dosya türü: {ext}")

    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(f"Desteklenmeyen dosya türü: {ext}")

    if file_size > MAX_FILE_SIZE:
        raise FileTooLargeError(f"Dosya çok büyük: {file_size / 1024 / 1024:.1f}MB (max: {MAX_FILE_SIZE / 1024 / 1024}MB)")

    if file_size == 0:
        raise FileValidationError("Dosya boş")


def save_upload(file_data: BinaryIO, original_filename: str, source: str = "web") -> dict:
    """Save uploaded file with validation.

    Returns dict with file info including hash, path, size.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(original_filename)
    ext = os.path.splitext(safe_name)[1].lower()

    # Read data
    data = file_data.read()
    validate_file(original_filename, len(data))

    # Hash for dedup
    file_hash = _file_hash(data)[:16]

    # Create storage path: uploads/YYYY-MM/
    date_dir = time.strftime("%Y-%m")
    storage_dir = UPLOAD_DIR / date_dir
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Check for duplicate
    for existing in storage_dir.iterdir():
        if existing.is_file():
            try:
                with open(existing, "rb") as f:
                    if _file_hash(f.read()) == _file_hash(data):
                        log(f"[FILE] Duplicate detected: {safe_name} == {existing.name}")
                        return _file_info(existing, source, duplicate_of=existing.name)
            except Exception:
                pass

    # Save with unique name
    timestamp = int(time.time())
    stored_name = f"{timestamp}_{file_hash}_{safe_name}"
    stored_path = storage_dir / stored_name

    with open(stored_path, "wb") as f:
        f.write(data)

    log(f"[FILE] Uploaded: {safe_name} -> {stored_path.name} ({len(data)} bytes)")

    return _file_info(stored_path, source)


def _file_info(path: Path, source: str, duplicate_of: str | None = None) -> dict:
    """Build file info dict."""
    stat = path.stat()
    return {
        "filename": path.name,
        "original_name": path.name.split("_", 2)[-1] if "_" in path.name else path.name,
        "path": str(path),
        "size": stat.st_size,
        "hash": _file_hash(path.read_bytes())[:16],
        "source": source,
        "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        "extension": path.suffix.lower(),
        "duplicate_of": duplicate_of,
    }


def get_upload_history(limit: int = 50) -> list[dict]:
    """List recent uploads."""
    files = []
    if not UPLOAD_DIR.exists():
        return files
    for month_dir in sorted(UPLOAD_DIR.iterdir(), reverse=True):
        if not month_dir.is_dir():
            continue
        for f in sorted(month_dir.iterdir(), reverse=True):
            if f.is_file():
                files.append({
                    "filename": f.name,
                    "size": f.stat().st_size,
                    "path": str(f),
                })
                if len(files) >= limit:
                    return files
    return files


def delete_upload(filename: str, date_dir: str) -> bool:
    """Delete an uploaded file."""
    path = UPLOAD_DIR / date_dir / filename
    if path.exists() and path.parent == UPLOAD_DIR / date_dir:
        path.unlink()
        log(f"[FILE] Deleted: {filename}")
        return True
    return False

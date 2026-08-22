"""UMAY Archive System — Topic-based and date-based memory organization.

Dual library:
1. UMAY_MEMORY/ — organized by topic
2. UMAY_ARCHIVE/ — organized by date
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from core.utils.logger import log


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "UMAY_MEMORY"
ARCHIVE_DIR = ROOT / "UMAY_ARCHIVE"

# Topic categories
TOPICS = [
    "UMAY", "CREWINTEL", "PATENT", "IS", "CV", "EGITIM",
    "TEKNIK", "PROJELER", "KISISEL_GOREVLER", "DIGER"
]


def _hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()[:16]


def _now() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
    }


def _ensure_dirs():
    Path(MEMORY_DIR).mkdir(parents=True, exist_ok=True)
    Path(ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)
    for topic in TOPICS:
        (Path(MEMORY_DIR) / topic).mkdir(parents=True, exist_ok=True)


class ArchiveEntry:
    """A single memory/archive entry."""

    def __init__(
        self,
        content: str,
        topic: str = "DIGER",
        source: str = "chat",
        keywords: list[str] | None = None,
        importance: str = "normal",
        file_path: str | None = None,
    ):
        self.id = _hash(content + time.time().__str__())
        self.content = content
        self.topic = topic if topic in TOPICS else "DIGER"
        self.source = source
        self.keywords = keywords or []
        self.importance = importance
        self.file_path = file_path
        self.created_at = _now()
        self.summary = content[:200] if len(content) > 200 else content

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "topic": self.topic,
            "source": self.source,
            "keywords": self.keywords,
            "importance": self.importance,
            "file_path": self.file_path,
            "created_at": self.created_at,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ArchiveEntry:
        entry = cls(
            content=data.get("content", ""),
            topic=data.get("topic", "DIGER"),
            source=data.get("source", "chat"),
            keywords=data.get("keywords", []),
            importance=data.get("importance", "normal"),
            file_path=data.get("file_path"),
        )
        entry.id = data.get("id", entry.id)
        entry.created_at = data.get("created_at", entry.created_at)
        entry.summary = data.get("summary", entry.summary)
        return entry


class ArchiveStore:
    """Manages topic-based and date-based archive entries."""

    def __init__(self):
        _ensure_dirs()

    def _topic_path(self, topic: str) -> Path:
        return Path(MEMORY_DIR) / topic / "entries.jsonl"

    def _date_path(self, date_str: str) -> Path:
        parts = date_str.split("-")
        if len(parts) == 3:
            return Path(ARCHIVE_DIR) / parts[0] / parts[1] / f"{parts[2]}.jsonl"
        return Path(ARCHIVE_DIR) / "misc" / "entries.jsonl"

    def add(self, entry: ArchiveEntry) -> bool:
        """Add entry to both topic and date libraries."""
        try:
            # Check for duplicate content
            if self._is_duplicate(entry.content):
                log(f"[ARCHIVE] Duplicate skipped: {entry.content[:50]}")
                return False

            # Save to topic library
            topic_path = self._topic_path(entry.topic)
            topic_path.parent.mkdir(parents=True, exist_ok=True)
            with open(topic_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

            # Save to date library
            date_str = entry.created_at.get("date", _now()["date"])
            date_path = self._date_path(date_str)
            date_path.parent.mkdir(parents=True, exist_ok=True)
            with open(date_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

            log(f"[ARCHIVE] Added: topic={entry.topic}, date={date_str}")
            return True
        except Exception as exc:
            log(f"[ARCHIVE] Error adding entry: {exc}")
            return False

    def _is_duplicate(self, content: str) -> bool:
        """Check if content already exists in any archive."""
        content_hash = _hash(content)
        for topic_dir in Path(MEMORY_DIR).iterdir():
            if not topic_dir.is_dir():
                continue
            entries_file = topic_dir / "entries.jsonl"
            if entries_file.exists():
                try:
                    with open(entries_file, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                data = json.loads(line.strip())
                                if _hash(data.get("content", "")) == content_hash:
                                    return True
                            except json.JSONDecodeError:
                                continue
                except Exception:
                    pass
        return False

    def search_by_topic(self, topic: str, limit: int = 20) -> list[dict]:
        """Search entries by topic."""
        entries = []
        path = self._topic_path(topic)
        if not path.exists():
            return entries
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return entries[-limit:]

    def search_by_date(self, date_str: str, limit: int = 20) -> list[dict]:
        """Search entries by date (YYYY-MM-DD or YYYY-MM)."""
        entries = []
        if len(date_str) == 10:  # YYYY-MM-DD
            path = self._date_path(date_str)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                entries.append(json.loads(line.strip()))
                            except json.JSONDecodeError:
                                continue
                except Exception:
                    pass
        elif len(date_str) == 7:  # YYYY-MM
            month_dir = Path(ARCHIVE_DIR) / date_str.replace("-", "/")
            if month_dir.exists():
                for day_file in sorted(month_dir.iterdir()):
                    if day_file.suffix == ".jsonl":
                        try:
                            with open(day_file, "r", encoding="utf-8") as f:
                                for line in f:
                                    try:
                                        entries.append(json.loads(line.strip()))
                                    except json.JSONDecodeError:
                                        continue
                        except Exception:
                            pass
        return entries[-limit:]

    def search_keywords(self, keywords: list[str], limit: int = 20) -> list[dict]:
        """Search entries by keywords."""
        results = []
        keyword_set = set(k.lower() for k in keywords)
        for topic_dir in Path(MEMORY_DIR).iterdir():
            if not topic_dir.is_dir():
                continue
            entries_file = topic_dir / "entries.jsonl"
            if not entries_file.exists():
                continue
            try:
                with open(entries_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            entry_keywords = set(k.lower() for k in data.get("keywords", []))
                            content_lower = data.get("content", "").lower()
                            if keyword_set & entry_keywords or any(k in content_lower for k in keywords):
                                results.append(data)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass
        return results[-limit:]

    def get_stats(self) -> dict:
        """Get archive statistics."""
        stats = {"topics": {}, "total_entries": 0, "total_size": 0}
        for topic in TOPICS:
            path = self._topic_path(topic)
            if path.exists():
                count = 0
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                count += 1
                except Exception:
                    pass
                stats["topics"][topic] = count
                stats["total_entries"] += count
                stats["total_size"] += path.stat().st_size
        return stats


# Global singleton
_archive: ArchiveStore | None = None


def get_archive() -> ArchiveStore:
    global _archive
    if _archive is None:
        _archive = ArchiveStore()
    return _archive

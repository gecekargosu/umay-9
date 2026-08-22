"""UMAY Conversation Store — persistent chat history.

Replaces the previous in-memory-only `_chat_sessions` dict in
`ui/panel_server.py`, which lost all conversation history on every process
restart (see docs/development/CHAT_CURRENT_STATE.md, section 2).

Design notes (kept deliberately minimal — see
docs/development/CHAT_DECISIONS.md STEP-01):
- SQLite, not a new service/framework: the rest of UMAY already persists
  state as local files (JSONL task/approval logs, JSON memory, ChromaDB for
  vectors). SQLite is the smallest addition consistent with that pattern and
  needs no new dependency (stdlib `sqlite3`).
- One row per message; one row per conversation (id, title, timestamps).
- The public functions intentionally mirror the exact shape/behavior of the
  in-memory helpers they replace in `ui/panel_server.py`
  (`_get_session_history`, `_add_to_history`, `_clear_session`) so the
  caller-facing interface does not change — only the storage backing does.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "memory" / "conversations.db"

# Same trim window the previous in-memory implementation used
# (ui/panel_server.py: _MAX_HISTORY = 20 message pairs).
DEFAULT_MAX_PAIRS = 20

_lock = threading.Lock()
_local = threading.local()


def _connect() -> sqlite3.Connection:
    """One connection per thread (SQLite connections aren't safely shared
    across threads without care; Flask + SocketIO threading mode uses
    multiple worker threads)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call repeatedly / on every
    app startup (idempotent)."""
    with _lock:
        conn = _connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                project TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages(conversation_id, id);
            """
        )
        # Migration: last_task_id links a conversation to the most recent
        # core/task_state.py task_id run on its behalf (STEP-02). Added via
        # ALTER TABLE rather than in CREATE TABLE above so existing
        # conversations.db files from STEP-01 upgrade in place without a
        # separate migration script.
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(conversations)")}
        if "last_task_id" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN last_task_id TEXT")
        conn.commit()


def _ensure_conversation(conversation_id: str) -> None:
    conn = _connect()
    now = time.time()
    conn.execute(
        """
        INSERT INTO conversations (id, title, project, created_at, updated_at)
        VALUES (?, NULL, NULL, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (conversation_id, now, now),
    )
    conn.commit()


def get_history(conversation_id: str, max_pairs: int = DEFAULT_MAX_PAIRS) -> list[dict[str, Any]]:
    """Return the conversation's messages as [{"role": ..., "content": ...}],
    oldest first, trimmed to the most recent `max_pairs` user/assistant pairs
    — same trimming behavior the old in-memory helper had, now applied at
    read time instead of at write time (so full history is still retained on
    disk even if only the recent window is sent to the model)."""
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()
    messages = [{"role": r["role"], "content": r["content"]} for r in rows]
    max_messages = max_pairs * 2
    if len(messages) > max_messages:
        messages = messages[-max_messages:]
    return messages


def add_message(conversation_id: str, role: str, content: str) -> None:
    with _lock:
        _ensure_conversation(conversation_id)
        conn = _connect()
        now = time.time()
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.commit()


def clear_conversation(conversation_id: str) -> None:
    """Delete a conversation and all its messages. Mirrors the old
    `_clear_session`'s behavior of dropping the session entirely."""
    with _lock:
        conn = _connect()
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()


def set_last_task_id(conversation_id: str, task_id: str) -> None:
    """Record which core/task_state.py task_id was most recently run for
    this conversation (STEP-02: Chat -> Task State integration)."""
    with _lock:
        _ensure_conversation(conversation_id)
        conn = _connect()
        conn.execute(
            "UPDATE conversations SET last_task_id = ?, updated_at = ? WHERE id = ?",
            (task_id, time.time(), conversation_id),
        )
        conn.commit()


def get_last_task_id(conversation_id: str) -> str | None:
    conn = _connect()
    row = conn.execute(
        "SELECT last_task_id FROM conversations WHERE id = ?",
        (conversation_id,),
    ).fetchone()
    return row["last_task_id"] if row else None


def list_conversations(limit: int = 50) -> list[dict[str, Any]]:
    """List conversations, most recently updated first. Not yet wired into
    any API route — provided now because the schema already supports it and
    later History/Search steps (spec §5/§12) will need it; adding the route
    is left to that step to keep this STEP's scope to persistence only."""
    conn = _connect()
    rows = conn.execute(
        "SELECT id, title, project, created_at, updated_at FROM conversations "
        "ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


init_db()

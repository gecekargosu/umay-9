"""UMAY Post-it Store — persistent sticky notes.

SQLite-backed storage for desktop Post-it notes.
Similar pattern to conversation_store.py.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "memory" / "postits.db"

_lock = threading.Lock()
_local = threading.local()


def _connect() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _lock:
        conn = _connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS postits (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                color TEXT NOT NULL DEFAULT '#FEF08A',
                x INTEGER NOT NULL DEFAULT 100,
                y INTEGER NOT NULL DEFAULT 100,
                width INTEGER NOT NULL DEFAULT 280,
                height INTEGER NOT NULL DEFAULT 200,
                pinned INTEGER NOT NULL DEFAULT 1,
                visible INTEGER NOT NULL DEFAULT 1,
                opacity REAL NOT NULL DEFAULT 0.95,
                font_size INTEGER NOT NULL DEFAULT 14,
                source_app TEXT,
                source_url TEXT,
                source_document TEXT,
                memory_id TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def create_postit(
    title: str = "",
    content: str = "",
    color: str = "#FEF08A",
    x: int = 100,
    y: int = 100,
    width: int = 280,
    height: int = 200,
    pinned: bool = True,
    source_app: str | None = None,
    source_url: str | None = None,
    source_document: str | None = None,
) -> dict:
    """Create a new Post-it note."""
    postit_id = str(uuid.uuid4())
    now = time.time()
    conn = _connect()
    with _lock:
        conn.execute(
            """
            INSERT INTO postits (id, title, content, color, x, y, width, height,
                                 pinned, visible, opacity, font_size,
                                 source_app, source_url, source_document,
                                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0.95, 14, ?, ?, ?, ?, ?)
            """,
            (postit_id, title, content, color, x, y, width, height,
             1 if pinned else 0, source_app, source_url, source_document,
             now, now),
        )
        conn.commit()
    return get_postit(postit_id)


def get_postit(postit_id: str) -> Optional[dict]:
    """Get a single Post-it by ID."""
    conn = _connect()
    row = conn.execute("SELECT * FROM postits WHERE id = ?", (postit_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_postits(visible_only: bool = False) -> list[dict]:
    """List all Post-its, optionally only visible ones."""
    conn = _connect()
    if visible_only:
        rows = conn.execute(
            "SELECT * FROM postits WHERE visible = 1 ORDER BY updated_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM postits ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_postit(postit_id: str, **fields) -> Optional[dict]:
    """Update a Post-it's fields."""
    if not fields:
        return get_postit(postit_id)
    allowed = {
        "title", "content", "color", "x", "y", "width", "height",
        "pinned", "visible", "opacity", "font_size",
        "source_app", "source_url", "source_document", "memory_id",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_postit(postit_id)
    # Convert booleans to int
    for bool_key in ("pinned", "visible"):
        if bool_key in updates:
            updates[bool_key] = 1 if updates[bool_key] else 0
    updates["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [postit_id]
    conn = _connect()
    with _lock:
        conn.execute(f"UPDATE postits SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_postit(postit_id)


def delete_postit(postit_id: str) -> bool:
    """Delete a Post-it permanently."""
    conn = _connect()
    with _lock:
        cursor = conn.execute("DELETE FROM postits WHERE id = ?", (postit_id,))
        conn.commit()
        return cursor.rowcount > 0


def hide_postit(postit_id: str) -> Optional[dict]:
    """Hide a Post-it (close without deleting)."""
    return update_postit(postit_id, visible=False)


def show_postit(postit_id: str) -> Optional[dict]:
    """Show a hidden Post-it."""
    return update_postit(postit_id, visible=True)


def toggle_pin(postit_id: str) -> Optional[dict]:
    """Toggle pin state."""
    postit = get_postit(postit_id)
    if not postit:
        return None
    return update_postit(postit_id, pinned=not postit["pinned"])


def save_position(postit_id: str, x: int, y: int) -> Optional[dict]:
    """Save Post-it position after drag."""
    return update_postit(postit_id, x=x, y=y)


def save_size(postit_id: str, width: int, height: int) -> Optional[dict]:
    """Save Post-it size after resize."""
    return update_postit(postit_id, width=width, height=height)


def search_postits(query: str) -> list[dict]:
    """Search Post-its by title or content."""
    conn = _connect()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM postits WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
        (q, q),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_stats() -> dict:
    """Get Post-it statistics."""
    conn = _connect()
    total = conn.execute("SELECT COUNT(*) as c FROM postits").fetchone()["c"]
    visible = conn.execute("SELECT COUNT(*) as c FROM postits WHERE visible = 1").fetchone()["c"]
    pinned = conn.execute("SELECT COUNT(*) as c FROM postits WHERE pinned = 1 AND visible = 1").fetchone()["c"]
    return {"total": total, "visible": visible, "pinned": pinned}


# Initialize on import
init_db()

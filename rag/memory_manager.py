"""UMAY long-term memory backed by ChromaDB."""
from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb

from core.config_manager import get as get_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "memory" / "chroma"
DEFAULT_COLLECTION_NAME = "umay_memory"

configured_db_path = get_config("memory_db_path", str(DEFAULT_DB_PATH))
configured_collection_name = get_config("memory_collection_name", DEFAULT_COLLECTION_NAME)
DB_PATH = Path(configured_db_path)
if not DB_PATH.is_absolute():
    DB_PATH = (ROOT / DB_PATH).resolve()

DB_PATH.mkdir(parents=True, exist_ok=True)
client = chromadb.PersistentClient(path=str(DB_PATH))
collection = client.get_or_create_collection(name=configured_collection_name)


def _make_id(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def add_memory(text: str, source: str = "chat") -> bool:
    text = text.strip()
    if not text:
        return False

    memory_id = _make_id(text)
    existing = collection.get(ids=[memory_id])
    if existing.get("ids"):
        return False

    collection.add(
        ids=[memory_id],
        documents=[text],
        metadatas=[{"source": source}],
    )
    return True


def search_memory(query: str, limit: int = 3) -> list[str]:
    query = query.strip()
    if not query or collection.count() == 0:
        return []

    limit = max(1, min(int(limit), 20))
    result = collection.query(
        query_texts=[query],
        n_results=min(limit, collection.count()),
        include=["documents", "distances"],
    )

    docs = result.get("documents") or [[]]
    distances = result.get("distances") or [[]]
    return [
        f"DISTANCE:{distance:.4f} | {doc}"
        for doc, distance in zip(docs[0], distances[0])
    ]

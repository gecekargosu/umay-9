from __future__ import annotations

from core.memory.memory_manager import get_history, get_status, get_todo, save_status
from core.utils.logger import log
from rag.memory_manager import add_memory, search_memory


def remember(query: str) -> dict:
    """Retrieve relevant memories, status, todo, and recent history."""
    try:
        memory = search_memory(query)
    except Exception as exc:
        memory = [f"Hafıza araması başarısız: {exc}"]

    return {
        "query": query,
        "memory": memory,
        "status": get_status(),
        "todo": get_todo(),
        "history": get_history()[-10:],
    }


def learn(fact: str, source: str = "user") -> bool:
    """Store a new piece of knowledge in long-term memory.

    Example:
        learn("Cengiz 20+ yıl inşaat deneyimine sahip")
        learn("Proje X deadline'i 15 Ekim", source="task")
    """
    if not fact or not fact.strip():
        return False
    try:
        added = add_memory(fact.strip(), source=source)
        if added:
            log(f"[MEMORY] Yeni bilgi öğrenildi: {fact[:80]}")
        return added
    except Exception as exc:
        log(f"[MEMORY] Öğrenme hatası: {exc}")
        return False


def recall(query: str, limit: int = 5) -> list[str]:
    """Search long-term memory for relevant information."""
    try:
        return search_memory(query, limit=limit)
    except Exception as exc:
        log(f"[MEMORY] Hatırlatma hatası: {exc}")
        return []


def get_context_for_agent(query: str) -> str:
    """Build context string for agent from memory + status + todo.

    Injected into agent's system prompt for context-aware responses.
    """
    parts = []

    memories = recall(query, limit=3)
    if memories:
        parts.append("Hafızamdaki ilgili bilgiler:")
        for m in memories:
            parts.append(f"  - {m}")

    status = get_status()
    if status:
        parts.append(f"Aktif durum: {status}")

    todo = get_todo()
    if todo:
        parts.append(f"Yapılacaklar: {todo}")

    return "\n".join(parts) if parts else ""


def update_status(key: str, value) -> bool:
    """Update a status field."""
    try:
        status = get_status()
        status[key] = value
        save_status(status)
        return True
    except Exception as exc:
        log(f"[MEMORY] Status güncelleme hatası: {exc}")
        return False

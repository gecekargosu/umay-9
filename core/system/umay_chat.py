"""Legacy CLI chat kept for compatibility with older UMAY launch commands."""
from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "core") not in sys.path:
    sys.path.insert(0, str(ROOT / "core"))

from core.engine import chat as ollama_chat
from core.memory.memory_bridge import remember
from core.memory.memory_manager import get_history, save_history
from core.engine import resolve_model


def build_prompt(user_message: str) -> str:
    memory = remember(user_message)
    # remember() bir dict dönüyor; LLM'e anlamlı bağlam olarak formatla
    if isinstance(memory, dict):
        mem_lines = []
        for item in memory.get("memory", []):
            mem_lines.append(f"- {item}")
        for item in memory.get("history", [])[-3:]:
            soru = item.get("soru") or item.get("user", "")
            cevap = item.get("cevap") or item.get("umay", "")
            if soru and cevap:
                mem_lines.append(f"- Geçmiş: {soru} → {cevap[:100]}")
        memory_text = "\n".join(mem_lines) if mem_lines else "(hafıza boş)"
    else:
        memory_text = str(memory)

    return f"""Sen UMAY isimli kişisel yapay zeka asistanısın.
Geliştiricin ve kullanıcın: Cengiz Kılıç.

Hafıza:
{memory_text}

Kullanıcı mesajı:
{user_message}

Kurallar:
- Türkçe cevap ver.
- Kendini UMAY olarak tanıt; Cengiz olduğunu iddia etme.
- Hafızadaki bilgileri kullan.
- Bilmediğin bilgiyi uydurma.
- Gereksiz uzunlukta cevap verme.
"""


def ask_ollama(prompt: str) -> str:
    return ollama_chat(
        [{"role": "system", "content": "Sen UMAY'sın. Türkçe, doğru ve net cevap ver."},
         {"role": "user", "content": prompt}],
        model=resolve_model("chat"),
        ajan="umay_chat",
        task="chat",
    )


def save_chat(user: str, cevap: str, model: str | None = None):
    history = get_history()
    history.append({
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "soru": user,
        "cevap": cevap,
        "model": model,
    })
    save_history(history)


def chat():
    print("UMAY aktif. Çıkmak için: çık")
    while True:
        user = input("\nCengiz: ").strip()
        if user.lower() in {"çık", "quit", "exit", "q"}:
            break
        if not user:
            continue
        prompt = build_prompt(user)
        model = resolve_model("chat")
        cevap = ollama_chat(
            [{"role": "system", "content": "Sen UMAY'sın. Türkçe, doğru ve net cevap ver."},
             {"role": "user", "content": prompt}],
            model=model,
            ajan="umay_chat",
            task="chat",
        )
        print("\nUMAY:", cevap)
        save_chat(user, cevap, model)


if __name__ == "__main__":
    chat()

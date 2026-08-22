import subprocess
import requests
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]

sys.path.append(str(ROOT))

try:
    from core.memory.memory_bridge import remember
    from core.memory.memory_manager import save_history, get_history
except ImportError as e:
    print(f"[UMAY] Legacy chat modülü eksik bağımlılık: {e}")
    def remember(_text): return ""
    def get_history(): return []
    def save_history(_data): pass


def ask_ollama(prompt):

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "gemma3:4b",
        "prompt": prompt,
        "stream": False
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        return data["response"].strip()

    except Exception as e:

        return f"[OLLAMA HATASI] {e}"



def build_prompt(user_message):

    memory = remember(user_message)

    context = f"""
Sen UMAY isimli kişisel yapay zeka asistanısın.

Senin geliştiricin ve kullanıcın:
Cengiz Kılıç

Hafızadan gelen bilgiler:

{memory}


Kullanıcının mesajı:

{user_message}


Kurallar:

- Türkçe cevap ver.
- Sen UMAY'sın, Cengiz değilsin.
- Cengiz hakkında sorulan sorulara kullanıcı bilgisi olarak cevap ver.
- "Ben kimim?" sorusuna Cengiz Kılıç hakkında cevap ver.
- Kendini Cengiz olarak tanıtma.
- Kendinden bahsederken "Ben UMAY'ım" ifadesini kullan.
- Hafızadaki bilgileri kullan.
- Bilmediğin bilgiyi uydurma.
- Kısa ve anlaşılır cevap ver.
"""

    return context



def save_chat(user, cevap):

    history = get_history()

    history.append(
        {
            "date": str(datetime.now()),
            "user": user,
            "umay": cevap
        }
    )

    save_history(history)



def chat():

    print("UMAY aktif. Çıkmak için: çık")


    while True:

        user = input("\nCengiz: ")


        if user.lower() == "çık":
            break


        prompt = build_prompt(user)


        cevap = ask_ollama(prompt)


        print("\nUMAY:", cevap)


        save_chat(
            user,
            cevap
        )



if __name__ == "__main__":
    chat()
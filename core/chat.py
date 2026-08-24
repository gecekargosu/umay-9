import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_PROJECT = Path(__file__).resolve().parents[1]
if str(ROOT_PROJECT) not in sys.path:
    sys.path.insert(0, str(ROOT_PROJECT))
from core.engine import chat
from core.router import model_sec

# --- Klasör yolları ---
ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = ROOT / "memory" / "history.json"
KNOWLEDGE_DIR = ROOT / "knowledge"

# --- UMAY Kimliği ---
SYSTEM_PROMPT = """Sen UMAY'sın. Başka bir ismin yok. Microsoft Phi, Gemma, DeepSeek gibi model isimlerini kullanma.
UMAY; Cengiz Kılıç tarafından geliştirilen kişisel bir yapay zeka işletim sistemidir.
Sen bu sistemin dil motorusun. Kullanıcı sana hangi model olduğunu sorsa bile sadece "Ben UMAY'ım" de.
Görevin: Cengiz'in projelerinde (UMAY AI OS, akıllı kordon, patent, yazılım) yardımcı olmak.
Türkçe konuş. Kısa ve net cevap ver."""


def load_knowledge() -> str:
    """knowledge/ klasöründeki tüm .md ve .txt dosyalarını okur (alt klasörler hariç)."""
    if not KNOWLEDGE_DIR.exists():
        return ""

    MAX_TOPLAM = 4000
    bilgi = []
    toplam = 0

    dosyalar = sorted(list(KNOWLEDGE_DIR.rglob("*.md")) + list(KNOWLEDGE_DIR.rglob("*.txt")))

    for dosya in dosyalar:
        if toplam >= MAX_TOPLAM:
            break
        kalan = MAX_TOPLAM - toplam
        icerik = dosya.read_text(encoding="utf-8", errors="ignore")
        parcalanmis = icerik[:min(1500, kalan)]
        bilgi.append(f"=== {dosya.name} ===\n{parcalanmis}")
        toplam += len(parcalanmis)

    return "\n\n".join(bilgi)


def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def run():
    print("\n========== UMAY ==========")
    print("Cengiz'in kişisel AI asistanı")
    print("Çıkmak için 'quit' yaz\n")

    # Bilgi tabanını yükle
    knowledge = load_knowledge()
    dosya_sayisi = len(list(KNOWLEDGE_DIR.rglob("*.md")) + list(KNOWLEDGE_DIR.rglob("*.txt"))) if KNOWLEDGE_DIR.exists() else 0
    if knowledge:
        system = SYSTEM_PROMPT + "\n\n--- Proje Bilgi Tabanı ---\n" + knowledge
        print(f"({dosya_sayisi} bilgi dosyası yüklendi)\n")
    else:
        system = SYSTEM_PROMPT
        print("(Bilgi tabanı boş)\n")

    # Geçmiş konuşmaları yükle
    history = load_history()
    messages = [{"role": "system", "content": system}]

    for h in history[-4:]:
        try:
            messages.append({"role": "user", "content": h["soru"]})
            messages.append({"role": "assistant", "content": h["cevap"]})
        except KeyError:
            pass

    if history:
        print(f"(Son {min(len(history), 4)} konuşma hafızadan yüklendi)\n")

    while True:
        soru = input("Sen: ").strip()

        if soru.lower() in ["quit", "exit", "q"]:
            print("\nUMAY kapatılıyor. Görüşmek üzere!")
            break

        if not soru:
            continue

        # Akıllı model seçimi
        secilen_model, gorev = model_sec(soru)

        messages.append({"role": "user", "content": soru})
        cevap = chat(messages, model=secilen_model)
        print(f"\nUMAY [{gorev}]: {cevap}\n")
        messages.append({"role": "assistant", "content": cevap})

        # Context window'un taşmasını önle: son 20 turdan fazlasını kes
        MAX_TURNS = 20  # 20 user + 20 assistant = 40 mesaj + system
        if len(messages) > MAX_TURNS * 2 + 1:
            messages = [messages[0]] + messages[-(MAX_TURNS * 2):]

        history.append({
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "soru": soru,
            "cevap": cevap,
            "model": secilen_model
        })
        save_history(history)


if __name__ == "__main__":
    run()

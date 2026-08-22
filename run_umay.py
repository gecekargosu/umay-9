"""UMAY launcher with local Ollama chat and autonomous workspace tools."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from core.engine import chat, resolve_model, installed_models
from core.router import model_sec
try:
    from core.memory.memory_bridge import remember
except ImportError:
    # Memory is optional for basic local chat/agent startup. If ChromaDB is
    # unavailable, UMAY still keeps Ollama + workspace tools usable.
    def remember(_text: str) -> dict:
        return {}
from core.system.system_info import system_check
from core.agent import run_agent

SYSTEM = """Sen UMAY'sın. Cengiz Kılıç'ın yerel yapay zeka asistanısın.
Türkçe cevap ver. Bilmediğini uydurma. Eski hafıza ile canlı sistem bilgisini karıştırma.
Model adın ne sorulursa 'Ben UMAY'ım; dil motoru yerel Ollama modeli kullanıyor.' diyebilirsin.
Web veya güncel bilgi istendiğinde agent moduna geçip web_search/browser araçlarını kullan.
"""

AGENT_KEYWORDS = [
    "klasörü incele", "klasörü tara", "projeyi incele", "projeyi tara", "dosyaları incele",
    "dosyaları tara", "kod tabanını incele", "repository", "repo", "audit", "denetle",
    "hataları bul", "hata listesi", "eksikleri bul", "düzelt", "düzeltmeleri yap",
    "testleri çalıştır", "build çalıştır", "lint çalıştır", "crewintel",
    "c:\\", "dosya sistemine", "terminali kullan", "yazılım mühendisi gibi",
    "internetten araştır", "internetten ara", "web'de ara", "webde ara", "web ara",
    "güncel bilgi", "güncel haber", "siteye git", "tarayıcıyı kullan", "browser",
    "google'da ara", "google ara", "interneti kullan", "internet araştır", "web sitesi",
    "website oluştur", "site oluştur",
]


def is_agent_request(text: str) -> bool:
    t=text.lower()
    return any(k.lower() in t for k in AGENT_KEYWORDS)


def live_context() -> str:
    models = installed_models()
    return "CANLI OLLAMA DURUMU (RAG'dan daha öncelikli):\n" + "\n".join(f"- {m}" for m in models)


def main():
    print("\n========== UMAY ==========")
    print("Local Ollama chat + Workspace Agent | çıkmak için: çık\n")
    models=installed_models()
    print(f"Ollama : {'OK' if models else 'ERROR'} ({len(models)} model)")
    print(f"Varsayılan model: {resolve_model('chat') or '[KURULU MODEL YOK]'}\n")

    while True:
        try:
            question = input("Cengiz: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nUMAY kapatılıyor.")
            return
        if question.lower() in {"çık", "exit", "quit", "q"}:
            return
        if not question:
            continue

        if is_agent_request(question):
            print("\n[AGENT] Workspace analizi başlatılıyor...\n")
            answer = run_agent(question)
            print(f"\nUMAY [agent]: {answer}\n")
            continue

        memory = remember(question)
        task_model, task = model_sec(question)
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

        messages = [
            {"role": "system", "content": SYSTEM + "\n\n" + live_context()},
            {"role": "user", "content": f"Hafıza yalnızca yardımcı bağlamdır; canlı sistem bilgisi önceliklidir.\n{memory_text}\n\nSoru:\n{question}"},
        ]
        answer = chat(messages, model=task_model, ajan="umay", task=task)
        print(f"\nUMAY [{task} / {task_model}]: {answer}\n")


if __name__ == "__main__":
    main()

"""
UMAY Action Logger
Her AI eylemi; kim yaptı, ne yaptı, nasıl yaptı, sonuç ne oldu şeklinde kaydeder.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# Log klasörü
ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

TEXT_LOG = LOG_DIR / "umay.log"
JSON_LOG = LOG_DIR / "actions.jsonl"


def _zaman() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def eylem_baslat(ajan: str, niyet: str, plan: str, model: str = "") -> str:
    """
    Bir AI eylemi başlatır ve log'a kaydeder.
    Döner: action_id (tamamlama için kullanılır)
    """
    action_id = str(uuid.uuid4())[:8]
    zaman = _zaman()

    # JSON log
    kayit = {
        "id": action_id,
        "zaman": zaman,
        "durum": "başladı",
        "ajan": ajan,
        "niyet": niyet,
        "plan": plan,
        "model": model,
        "sonuc": None,
        "test": None,
        "sure_sn": None,
    }

    with open(JSON_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    # Metin log
    with open(TEXT_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{zaman}] #{action_id} BAŞLADI\n")
        f.write(f"  AJAN   : {ajan}\n")
        f.write(f"  NİYET  : {niyet}\n")
        f.write(f"  PLAN   : {plan}\n")
        if model:
            f.write(f"  MODEL  : {model}\n")

    print(f"[LOG] #{action_id} -> {ajan}: {niyet[:50]}")
    return action_id


def eylem_tamamla(action_id: str, sonuc: str, test_gecti: bool = True, sure_sn: float = 0):
    """Bir eylemi tamamlandı olarak işaretler."""
    zaman = _zaman()
    durum = "[TAMAM]" if test_gecti else "[UYARI] (test basarisiz)"

    # JSON log
    with open(JSON_LOG, "a", encoding="utf-8") as f:
        kayit = {
            "id": action_id,
            "zaman": zaman,
            "durum": "tamamlandı",
            "sonuc": sonuc,
            "test": test_gecti,
            "sure_sn": round(sure_sn, 1),
        }
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    # Metin log
    with open(TEXT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{zaman}] #{action_id} {durum}\n")
        f.write(f"  SONUÇ  : {sonuc}\n")
        f.write(f"  TEST   : {'Gecti [OK]' if test_gecti else 'Basarisiz [HATA]'}\n")
        f.write(f"  SÜRE   : {sure_sn:.1f} sn\n")

    print(f"[LOG] #{action_id} tamamlandı ({sure_sn:.1f}sn)")


def eylem_hata(action_id: str, hata: str):
    """Bir eylemde hata oluştuğunu kaydeder."""
    zaman = _zaman()

    with open(JSON_LOG, "a", encoding="utf-8") as f:
        kayit = {
            "id": action_id,
            "zaman": zaman,
            "durum": "hata",
            "hata": hata,
        }
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    with open(TEXT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{zaman}] #{action_id} [HATA]\n")
        f.write(f"  HATA   : {hata}\n")

    print(f"[LOG] #{action_id} HATA: {hata[:60]}")


def log_goster(son_n: int = 10):
    """Son N log kaydini gosterir."""
    if not TEXT_LOG.exists():
        print("Henuz log yok.")
        return

    satirlar = TEXT_LOG.read_text(encoding="utf-8").strip().split("\n")
    son = satirlar[-min(son_n * 6, len(satirlar)):]
    # Emoji karakterleri ASCII'ye cevir
    cikti = "\n".join(son)
    cikti = cikti.replace("[OK]", "[OK]").replace("[HATA]", "[HATA]")
    print(cikti.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    # Test
    import time
    print("=== UMAY Action Logger Test ===\n")

    aid = eylem_baslat(
        ajan="coding_agent",
        niyet="Python hello world yaz",
        plan="print() fonksiyonunu kullan",
        model="local-coding-model"
    )

    time.sleep(1)

    eylem_tamamla(
        action_id=aid,
        sonuc="print('Hello, World!') kodu üretildi",
        test_gecti=True,
        sure_sn=1.2
    )

    print("\n--- Log dosyası ---")
    log_goster()

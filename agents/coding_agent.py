"""Small local coding agent used by UMAY.

It generates Python with an installed local model and executes it with a timeout.
This is NOT a security sandbox; do not execute untrusted code with it.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.engine import MODEL_PREFERENCES, chat, resolve_model
from core.utils.action_logger import eylem_baslat, eylem_hata, eylem_tamamla

AJAN_ADI = "coding_agent"

SYSTEM_PROMPT = """Sen UMAY'in Coding Agent'isin.
İstenen işi yapan çalışabilir Python kodu üret.
Açıklama yazma; yalnızca saf Python kodu döndür.
"""


def kod_yaz(istek: str) -> str:
    model = resolve_model("coding")
    action_id = eylem_baslat(
        ajan=AJAN_ADI,
        niyet=f"Kod yazma: {istek[:60]}",
        plan="Yerel coding modeli ile kod üret",
        model=model or "yok",
    )
    try:
        if not model:
            raise RuntimeError("Kurulu bir coding modeli bulunamadı.")
        cevap = chat(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": f"Şu işi yapan Python kodunu yaz: {istek}"}],
            model=model,
            ajan=AJAN_ADI,
            task="coding",
        )
        kod = _kod_temizle(cevap)
        if not kod:
            raise RuntimeError("Model boş kod döndürdü.")
        eylem_tamamla(action_id, f"Kod üretildi ({len(kod)} karakter)", True)
        return kod
    except Exception as exc:
        eylem_hata(action_id, str(exc))
        return f"# Hata: {exc}"


def kod_calistir(kod: str, zaman_asimi: int = 10) -> tuple[bool, str]:
    """Run generated Python with a timeout. This is not a security sandbox."""
    action_id = eylem_baslat(
        ajan=AJAN_ADI,
        niyet="Kod çalıştırma ve test",
        plan=f"Geçici dosya + subprocess (max {zaman_asimi}s)",
    )
    tmp_yolu = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(kod)
            tmp_yolu = tmp.name

        result = subprocess.run(
            [os.environ.get("PYTHON", "python"), tmp_yolu],
            capture_output=True,
            text=True,
            timeout=max(1, int(zaman_asimi)),
            encoding="utf-8",
            errors="replace",
        )
        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()
        if result.returncode == 0:
            eylem_tamamla(action_id, f"Başarılı: {output[:80]}", True)
            return True, output or "(çıktı yok)"
        eylem_tamamla(action_id, f"Hata: {error[:80]}", False)
        return False, error or f"Process exit code: {result.returncode}"
    except subprocess.TimeoutExpired:
        eylem_hata(action_id, f"Zaman aşımı ({zaman_asimi}s)")
        return False, f"Zaman aşımı: {zaman_asimi} saniye"
    except Exception as exc:
        eylem_hata(action_id, str(exc))
        return False, str(exc)
    finally:
        if tmp_yolu:
            try:
                Path(tmp_yolu).unlink(missing_ok=True)
            except OSError:
                pass


def _kod_temizle(metin: str) -> str:
    metin = metin.strip()
    if not metin:
        return ""
    if "```" not in metin:
        return metin
    blocks = []
    lines = metin.splitlines()
    inside = False
    for line in lines:
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            blocks.append(line)
    return "\n".join(blocks).strip() or metin.replace("```python", "").replace("```", "").strip()


def calistir(istek: str) -> dict:
    kod = kod_yaz(istek)
    basarili, cikti = kod_calistir(kod)
    return {"istek": istek, "kod": kod, "basarili": basarili, "cikti": cikti}


if __name__ == "__main__":
    print(calistir("1'den 5'e kadar sayıları ekrana yazdır"))

"""
UMAY Vision Reader — Ücretsiz/Yerel Görsel Anlama Motoru.

Strateji:
- Pillow: Görsel okuma, metadata, temel işleme
- Ollama LLaVA/gemma3: Görsel anlama, metin çıkarma, soru-cevap
- pytesseract (opsiyonel): Hassas OCR (Tesseract kuruluysa)

%100 ÜCRETSIZ ve YEREL. Dış API gerektirmez.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from core.utils.action_logger import eylem_baslat, eylem_hata, eylem_tamamla

# ─── Desteklenen Formatlar ───────────────────────────────────────────────────

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".ico", ".svg",
}

MAX_IMAGE_SIZE_MB = 20  # Maksimum dosya boyutu
MAX_DIMENSION = 2048  # Maksimum genişlik/yükseklik (Ollama için)


# ─── Pillow ile Görsel Okuma ────────────────────────────────────────────────

def read_image_info(file_path: Path) -> dict[str, Any]:
    """
    Pillow ile görsel bilgilerini oku.

    Returns:
        dict: Görsel metadata bilgileri
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except ImportError:
        return {"error": "Pillow kütüphanesi yüklü değil.", "status": "ERROR"}

    try:
        img = Image.open(file_path)

        # EXIF bilgileri
        exif_data = {}
        try:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, (str, int, float)):
                        exif_data[str(tag)] = value
        except (AttributeError, Exception):
            pass

        return {
            "path": str(file_path.name),
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": file_path.stat().st_size,
            "has_transparency": img.mode in ("RGBA", "LA", "PA"),
            "exif": exif_data,
            "status": "OK",
        }
    except Exception as e:
        return {"error": f"Görsel okuma hatası: {e}", "status": "ERROR"}


def image_to_base64(file_path: Path, max_dim: int = MAX_DIMENSION) -> str | None:
    """
    Görseli base64 formatına dönüştür (Ollama için).

    Args:
        file_path: Görsel dosya yolu
        max_dim: Maksimum boyut (piksel)

    Returns:
        str: base64 encoded görsel veya None
    """
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        img = Image.open(file_path)

        # RGBA → RGB dönüştürme (JPEG için)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = background

        # Boyut küçültme (Ollama için)
        if max(img.width, img.height) > max_dim:
            ratio = max_dim / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Base64'e dönüştür
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


# ─── Tesseract OCR (Opsiyonel) ──────────────────────────────────────────────

def _tesseract_available() -> bool:
    """Tesseract'ın kurulu olup olmadığını kontrol et."""
    try:
        import pytesseract
        # Tesseract executable'ı test et
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_with_tesseract(
    file_path: Path,
    lang: str = "tur+eng",
) -> dict[str, Any]:
    """
    Tesseract ile OCR yap.

    Args:
        file_path: Görsel dosya yolu
        lang: OCR dili (varsayılan: Türkçe + İngilizce)

    Returns:
        dict: OCR sonuçları
    """
    if not _tesseract_available():
        return {
            "error": "Tesseract OCR kurulu değil. Görsel anlama için Ollama vision modelleri kullanılıyor.",
            "available": False,
            "status": "FALLBACK",
        }

    try:
        import pytesseract
        from PIL import Image

        img = Image.open(file_path)

        # Tam metin
        text = pytesseract.image_to_string(img, lang=lang)

        # Kelime bazlı detay
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

        words = []
        for i, word in enumerate(data["text"]):
            if word.strip():
                words.append({
                    "text": word,
                    "confidence": data["conf"][i],
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                })

        return {
            "path": str(file_path.name),
            "text": text.strip(),
            "word_count": len(words),
            "words": words[:100],  # İlk 100 kelime
            "language": lang,
            "available": True,
            "status": "OK",
        }
    except Exception as e:
        return {"error": f"OCR hatası: {e}", "status": "ERROR"}


# ─── Ollama Vision Entegrasyonu ─────────────────────────────────────────────

def _resolve_vision_model() -> str | None:
    """Mevcut vision modelleri arasından en iyisini seç."""
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        r = requests.get(f"{ollama_url}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]

        # Öncelik sırası: gemma3 > llava
        for preferred in ["gemma3:4b", "llava:7b", "llava:latest"]:
            for name in models:
                if name == preferred or name.split(":")[0] == preferred.split(":")[0]:
                    return name

        # Herhangi bir vision modeli
        for name in models:
            if any(v in name.lower() for v in ["llava", "vision", "gemma3"]):
                return name

        return models[0] if models else None
    except Exception:
        return None


def ask_vision_model(
    image_path: Path,
    question: str = "Bu görseli detaylı şekilde açıkla.",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Ollama vision modeli ile görsel hakkında soru-cevap.

    Args:
        image_path: Görsel dosya yolu
        question: Görsel hakkında soru
        model: Kullanılacak model (None ise otomatik seç)

    Returns:
        dict: Vision model cevabı
    """
    selected_model = model or _resolve_vision_model()
    if not selected_model:
        return {"error": "Vision modeli bulunamadı. Ollama çalışıyor mu?", "status": "ERROR"}

    # Görseli base64'e dönüştür
    img_b64 = image_to_base64(image_path)
    if not img_b64:
        return {"error": f"Görsel base64'e dönüştürülemedi: {image_path}", "status": "ERROR"}

    # Ollama API çağrısı
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")

        payload = {
            "model": selected_model,
            "messages": [
                {
                    "role": "user",
                    "content": question,
                    "images": [img_b64],
                }
            ],
            "stream": False,
        }

        start_time = time.time()
        response = requests.post(
            f"{ollama_url}/api/chat",
            json=payload,
            timeout=120)
        response.raise_for_status()
        duration = time.time() - start_time

        result = response.json()
        answer = result.get("message", {}).get("content", "").strip()

        if not answer:
            return {"error": "Vision model boş cevap döndürdü.", "status": "ERROR"}

        return {
            "path": str(image_path.name),
            "model": selected_model,
            "question": question,
            "answer": answer,
            "duration_s": round(duration, 2),
            "status": "OK",
        }
    except requests.ConnectionError:
        return {"error": "Ollama'ya bağlanılamadı.", "status": "ERROR"}
    except requests.Timeout:
        return {"error": "Vision model zaman aşımı (120s).", "status": "ERROR"}
    except Exception as e:
        return {"error": f"Vision hatası: {e}", "status": "ERROR"}


# ─── Yüksek Seviye Fonksiyonlar ─────────────────────────────────────────────

def analyze_image(
    file_path: str | Path,
    question: str = "Bu görseli detaylı şekilde açıkla. Varsa görseldeki yazıları da yaz.",
    use_ocr: bool = True,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Görseli kapsamlı şekilde analiz et.

    1. Görsel metadata'sını oku (Pillow)
    2. OCR yap (Tesseract varsa)
    3. Vision model ile analiz et (Ollama LLaVA/gemma3)
    4. Sonuçları birleştir

    Args:
        file_path: Görsel dosya yolu
        question: Görsel hakkında soru
        use_ocr: OCR kullanılsın mı?
        model: Vision modeli

    Returns:
        dict: Kapsamlı analiz sonucu
    """
    path = Path(file_path)

    if not path.exists():
        return {"error": f"Dosya bulunamadı: {path}", "status": "ERROR"}

    if not path.is_file():
        return {"error": f"Bu bir dosya değil: {path}", "status": "ERROR"}

    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        return {
            "error": f"Desteklenmeyen görsel formatı: {path.suffix}",
            "supported": sorted(SUPPORTED_IMAGE_EXTENSIONS),
            "status": "ERROR",
        }

    # Action logging
    aid = eylem_baslat(
        ajan="vision_reader",
        niyet=f"Görsel analiz: {path.name}",
        plan=f"Soru: {question[:80]}",
        model=model or "auto",
    )

    result = {
        "path": str(path.name),
        "absolute_path": str(path.resolve()),
        "file_size": path.stat().st_size,
    }

    # 1. Görsel metadata
    metadata = read_image_info(path)
    result["metadata"] = metadata

    # 2. OCR (opsiyonel)
    if use_ocr:
        ocr_result = ocr_with_tesseract(path)
        result["ocr"] = ocr_result
        if ocr_result.get("text"):
            result["extracted_text"] = ocr_result["text"]

    # 3. Vision model analizi
    vision_result = ask_vision_model(path, question, model)
    result["vision"] = vision_result

    if vision_result.get("answer"):
        result["analysis"] = vision_result["answer"]
        result["model_used"] = vision_result.get("model", "")
        result["duration_s"] = vision_result.get("duration_s", 0)

    # Durum belirleme
    has_analysis = bool(result.get("analysis"))
    has_ocr = bool(result.get("extracted_text"))

    if has_analysis or has_ocr:
        result["status"] = "OK"
        eylem_tamamla(
            aid,
            f"Görsel analiz tamam: {result.get('model_used', 'N/A')}",
            True,
            result.get("duration_s", 0),
        )
    else:
        result["status"] = "PARTIAL"
        eylem_hata(aid, "Görsel analiz başarısız")

    return result


def image_to_text(
    file_path: str | Path,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Görseldeki metni çıkar.

    OCR + Vision model kombinasyonu kullanır.

    Args:
        file_path: Görsel dosya yolu
        model: Vision modeli

    Returns:
        dict: Çıkarılan metin
    """
    return analyze_image(
        file_path,
        question="Bu görseldeki tüm metinleri birebir yaz. Metinleri olduğu gibi koru, çevirme.",
        use_ocr=True,
        model=model,
    )


def describe_image(
    file_path: str | Path,
    detail_level: str = "detailed",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Görseli açıkla.

    Args:
        file_path: Görsel dosya yolu
        detail_level: "brief", "detailed", "very_detailed"
        model: Vision modeli

    Returns:
        dict: Görsel açıklaması
    """
    questions = {
        "brief": "Bu görseli 1-2 cümlede kısaca açıkla.",
        "detailed": "Bu görseli detaylı şekilde açıkla. İçeriği, renkleri, nesneleri, varsa yazıları belirt.",
        "very_detailed": "Bu görseli çok detaylı şekilde analiz et. İçeriği, renkleri, nesneleri, konumları, varsa yazıları, duygu durumunu, olası bağlamını açıkla.",
    }

    question = questions.get(detail_level, questions["detailed"])
    return analyze_image(file_path, question=question, use_ocr=False, model=model)


def image_qa(
    file_path: str | Path,
    question: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Görsel hakkında soru-cevap.

    Args:
        file_path: Görsel dosya yolu
        question: Soru
        model: Vision modeli

    Returns:
        dict: Cevap
    """
    return analyze_image(file_path, question=question, use_ocr=False, model=model)


# ─── Görsel → Memory/RAG Aktarımı ──────────────────────────────────────────

def image_to_memory(
    file_path: str | Path,
    source: str = "image",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Görsel analiz sonucunu RAG/hafıza sistemine aktar.

    Args:
        file_path: Görsel dosya yolu
        source: Kaynak etiketi
        model: Vision modeli

    Returns:
        dict: Aktarım sonucu
    """
    try:
        from rag.memory_manager import add_memory
    except ImportError:
        return {"error": "memory_manager modülü bulunamadı.", "status": "ERROR"}

    # Görseli analiz et
    analysis = analyze_image(
        file_path,
        question="Bu görseli detaylı şekilde açıkla. Varsa görseldeki tüm yazıları yaz.",
        use_ocr=True,
        model=model,
    )

    if "error" in analysis and not analysis.get("analysis"):
        return analysis

    # Analiz sonucunu hafızaya ekle
    content_parts = []
    if analysis.get("analysis"):
        content_parts.append(f"Görsel Analizi: {analysis['analysis']}")
    if analysis.get("extracted_text"):
        content_parts.append(f"Çıkarılan Metin: {analysis['extracted_text']}")

    content = "\n\n".join(content_parts)
    if not content.strip():
        return {"error": "Analiz sonucu boş.", "status": "ERROR"}

    # Hafızaya ekle
    metadata = f"{source}:{analysis.get('path', 'unknown')}"
    added = add_memory(content, source=metadata)

    return {
        "path": str(file_path),
        "added_to_memory": added,
        "content_preview": content[:500],
        "status": "OK",
    }


# ─── Batch İşleme ───────────────────────────────────────────────────────────

def analyze_images_batch(
    file_paths: list[str | Path],
    question: str = "Bu görseli açıkla.",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Birden fazla görseli toplu analiz et.

    Args:
        file_paths: Görsel dosya yolları
        question: Her görsel için soru
        model: Vision modeli

    Returns:
        dict: Toplu analiz sonuçları
    """
    results = []
    errors = []

    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            errors.append({"path": str(fp), "error": "Dosya bulunamadı"})
            continue

        if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            errors.append({"path": str(fp), "error": f"Desteklenmeyen format: {path.suffix}"})
            continue

        result = analyze_image(path, question=question, use_ocr=False, model=model)
        results.append(result)

    return {
        "total": len(file_paths),
        "analyzed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
        "status": "OK" if results else "ERROR",
    }


# ─── Test Fonksiyonu ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== UMAY Vision Reader Test ===\n")

    # Tesseract durumu
    print(f"Tesseract OCR: {'Kurulu' if _tesseract_available() else 'Kurulu değil (opsiyonel)'}")

    # Vision model durumu
    model = _resolve_vision_model()
    print(f"Vision Model: {model or 'Bulunamadı'}")

    # Örnek görsel analizi (varsa)
    import sys
    if len(sys.argv) > 1:
        img_path = Path(sys.argv[1])
        if img_path.exists():
            print(f"\nGörsel analiz ediliyor: {img_path}")
            result = analyze_image(img_path)
            print(f"Durum: {result.get('status')}")
            if result.get("analysis"):
                print(f"Analiz: {result['analysis'][:500]}")
        else:
            print(f"Dosya bulunamadı: {img_path}")
    else:
        print("\nKullanım: python vision_reader.py <görsel_dosyası>")

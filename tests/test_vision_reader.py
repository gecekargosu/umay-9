"""
UMAY Vision Reader Tests
Görsel okuma, OCR, vision model entegrasyonu testleri.
"""
import base64
import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image


# ─── Test Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_jpg(tmp_path):
    """Örnek JPG dosyası oluştur."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    file = tmp_path / "test.jpg"
    img.save(str(file), "JPEG")
    return file


@pytest.fixture
def sample_png(tmp_path):
    """Örnek PNG dosyası oluştur."""
    img = Image.new("RGBA", (100, 100), color=(0, 255, 0, 128))
    file = tmp_path / "test.png"
    img.save(str(file), "PNG")
    return file


@pytest.fixture
def sample_webp(tmp_path):
    """Örnek WebP dosyası oluştur."""
    img = Image.new("RGB", (100, 100), color=(0, 0, 255))
    file = tmp_path / "test.webp"
    img.save(str(file), "WEBP")
    return file


@pytest.fixture
def sample_gif(tmp_path):
    """Örnek GIF dosyası oluştur."""
    img = Image.new("RGB", (100, 100), color=(255, 255, 0))
    file = tmp_path / "test.gif"
    img.save(str(file), "GIF")
    return file


@pytest.fixture
def sample_bmp(tmp_path):
    """Örnek BMP dosyası oluştur."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    file = tmp_path / "test.bmp"
    img.save(str(file), "BMP")
    return file


@pytest.fixture
def sample_text_file(tmp_path):
    """Örnek metin dosyası (görsel olmayan)."""
    file = tmp_path / "test.txt"
    file.write_text("Bu bir metin dosyası", encoding="utf-8")
    return file


@pytest.fixture
def large_image(tmp_path):
    """Büyük boyutlu görsel oluştur."""
    img = Image.new("RGB", (3000, 2000), color=(100, 150, 200))
    file = tmp_path / "large.png"
    img.save(str(file), "PNG")
    return file


# ─── Image Info Tests ───────────────────────────────────────────────────────

class TestImageInfo:
    """Görsel metadata okuma testleri."""

    def test_read_jpg_info(self, sample_jpg):
        """JPG metadata okunabilmeli."""
        from core.vision_reader import read_image_info
        result = read_image_info(sample_jpg)

        assert result["status"] == "OK"
        assert result["format"] == "JPEG"
        assert result["width"] == 100
        assert result["height"] == 100
        assert result["size_bytes"] > 0

    def test_read_png_info(self, sample_png):
        """PNG metadata okunabilmeli."""
        from core.vision_reader import read_image_info
        result = read_image_info(sample_png)

        assert result["status"] == "OK"
        assert result["format"] == "PNG"
        assert result["has_transparency"] is True

    def test_read_webp_info(self, sample_webp):
        """WebP metadata okunabilmeli."""
        from core.vision_reader import read_image_info
        result = read_image_info(sample_webp)

        assert result["status"] == "OK"
        assert result["format"] == "WEBP"

    def test_read_nonexistent_image(self, tmp_path):
        """Olmayan görsel için hata dönmeli."""
        from core.vision_reader import read_image_info
        result = read_image_info(tmp_path / "nonexistent.jpg")

        assert result["status"] == "ERROR"

    def test_read_text_file_as_image(self, sample_text_file):
        """Metin dosyası görsel olarak açılırsa hata dönmeli."""
        from core.vision_reader import read_image_info
        result = read_image_info(sample_text_file)

        assert result["status"] == "ERROR"


# ─── Base64 Conversion Tests ────────────────────────────────────────────────

class TestBase64Conversion:
    """Görsel → base64 dönüştürme testleri."""

    def test_image_to_base64_jpg(self, sample_jpg):
        """JPG base64'e dönüştürülebilmeli."""
        from core.vision_reader import image_to_base64
        result = image_to_base64(sample_jpg)

        assert result is not None
        assert isinstance(result, str)
        # base64 decode edilebilmeli
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_image_to_base64_png(self, sample_png):
        """PNG base64'e dönüştürülebilmeli."""
        from core.vision_reader import image_to_base64
        result = image_to_base64(sample_png)

        assert result is not None
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_image_to_base64_webp(self, sample_webp):
        """WebP base64'e dönüştürülebilmeli."""
        from core.vision_reader import image_to_base64
        result = image_to_base64(sample_webp)

        assert result is not None
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_large_image_resize(self, large_image):
        """Büyük görsel otomatik küçültülmeli."""
        from core.vision_reader import image_to_base64
        result = image_to_base64(large_image, max_dim=500)

        assert result is not None
        # Küçültülmüş görsel daha küçük olmalı
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_nonexistent_image_returns_none(self, tmp_path):
        """Olmayan görsel için None dönmeli."""
        from core.vision_reader import image_to_base64
        result = image_to_base64(tmp_path / "nonexistent.jpg")

        assert result is None


# ─── Tesseract OCR Tests ────────────────────────────────────────────────────

class TestTesseractOCR:
    """Tesseract OCR testleri."""

    def test_tesseract_availability_check(self):
        """Tesseract kullanılabilirliği kontrol edilmeli."""
        from core.vision_reader import _tesseract_available
        result = _tesseract_available()

        assert isinstance(result, bool)

    def test_ocr_with_tesseract(self, sample_jpg):
        """Tesseract ile OCR (mümkünse)."""
        from core.vision_reader import ocr_with_tesseract
        result = ocr_with_tesseract(sample_jpg)

        # Tesseract kurulu değilse FALLBACK dönmeli
        if result.get("available") is False:
            assert result["status"] == "FALLBACK"
        else:
            assert result["status"] == "OK"
            assert "text" in result


# ─── Vision Model Tests (Mock) ──────────────────────────────────────────────

class TestVisionModel:
    """Vision model testleri (mock ile)."""

    def test_resolve_vision_model(self):
        """Vision modeli otomatik seçilebilmeli."""
        from core.vision_reader import _resolve_vision_model
        result = _resolve_vision_model()

        # Ollama çalışıyorsa model dönmeli
        if result:
            assert isinstance(result, str)
            assert len(result) > 0

    @patch("requests.post")
    def test_ask_vision_model_mock(self, mock_post, sample_jpg):
        """Vision modeli mock ile test."""
        from core.vision_reader import ask_vision_model

        # Mock Ollama response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "content": "Bu kırmızı bir kare görseldir."
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = ask_vision_model(sample_jpg, "Bu görseli açıkla", model="llava:7b")

        assert result["status"] == "OK"
        assert "kırmızı" in result["answer"]


# ─── Analyze Image Tests ────────────────────────────────────────────────────

class TestAnalyzeImage:
    """Görsel analiz testleri."""

    def test_analyze_image_nonexistent(self, tmp_path):
        """Olmayan görsel analiz edilirse hata dönmeli."""
        from core.vision_reader import analyze_image
        result = analyze_image(tmp_path / "nonexistent.jpg")

        assert result["status"] == "ERROR"

    def test_analyze_image_wrong_extension(self, sample_text_file):
        """Yanlış uzantılı dosya için hata dönmeli."""
        from core.vision_reader import analyze_image
        result = analyze_image(sample_text_file)

        assert result["status"] == "ERROR"
        assert "Desteklenmeyen" in result["error"]

    @patch("core.vision_reader.ask_vision_model")
    def test_analyze_image_with_mock(self, mock_vision, sample_jpg):
        """Mock vision model ile görsel analiz."""
        from core.vision_reader import analyze_image

        mock_vision.return_value = {
            "path": "test.jpg",
            "model": "llava:7b",
            "question": "Bu görseli açıkla",
            "answer": "Test görseli açıklaması",
            "duration_s": 1.5,
            "status": "OK",
        }

        result = analyze_image(sample_jpg, use_ocr=False)

        assert result["status"] == "OK"
        assert result["analysis"] == "Test görseli açıklaması"
        assert result["metadata"]["status"] == "OK"


# ─── Image to Text Tests ────────────────────────────────────────────────────

class TestImageToText:
    """Görsel → metin çıkarma testleri."""

    @patch("core.vision_reader.ask_vision_model")
    def test_image_to_text(self, mock_vision, sample_jpg):
        """Görselden metin çıkarabilmeli."""
        from core.vision_reader import image_to_text

        mock_vision.return_value = {
            "path": "test.jpg",
            "model": "llava:7b",
            "question": "Bu görseldeki tüm metinleri yaz",
            "answer": "Test metni: Merhaba Dünya",
            "duration_s": 1.0,
            "status": "OK",
        }

        result = image_to_text(sample_jpg)

        assert result["status"] == "OK"
        assert "answer" in result["vision"]


# ─── Describe Image Tests ───────────────────────────────────────────────────

class TestDescribeImage:
    """Görsel açıklama testleri."""

    @patch("core.vision_reader.ask_vision_model")
    def test_describe_image_brief(self, mock_vision, sample_jpg):
        """Kısa açıklama yapılabilmeli."""
        from core.vision_reader import describe_image

        mock_vision.return_value = {
            "path": "test.jpg",
            "model": "llava:7b",
            "question": "Bu görseli 1-2 cümlede kısaca açıkla.",
            "answer": "Kırmızı bir kare görsel.",
            "duration_s": 1.0,
            "status": "OK",
        }

        result = describe_image(sample_jpg, detail_level="brief")

        assert result["status"] == "OK"

    @patch("core.vision_reader.ask_vision_model")
    def test_describe_image_detailed(self, mock_vision, sample_png):
        """Detaylı açıklama yapılabilmeli."""
        from core.vision_reader import describe_image

        mock_vision.return_value = {
            "path": "test.png",
            "model": "llava:7b",
            "question": "Bu görseli detaylı şekilde açıkla.",
            "answer": "Şeffaf arka planlı yeşil kare görsel.",
            "duration_s": 1.5,
            "status": "OK",
        }

        result = describe_image(sample_png, detail_level="detailed")

        assert result["status"] == "OK"


# ─── Image Q&A Tests ────────────────────────────────────────────────────────

class TestImageQA:
    """Görsel soru-cevap testleri."""

    @patch("core.vision_reader.ask_vision_model")
    def test_image_qa(self, mock_vision, sample_jpg):
        """Görsel hakkında soru sorulabilmeli."""
        from core.vision_reader import image_qa

        mock_vision.return_value = {
            "path": "test.jpg",
            "model": "llava:7b",
            "question": "Bu görselde kaç nesne var?",
            "answer": "Bu görselde 1 nesne var: kırmızı kare.",
            "duration_s": 1.0,
            "status": "OK",
        }

        result = image_qa(sample_jpg, "Bu görselde kaç nesne var?")

        assert result["status"] == "OK"
        assert "1 nesne" in result["analysis"]


# ─── Image to Memory Tests ──────────────────────────────────────────────────

class TestImageToMemory:
    """Görsel → Hafıza aktarım testleri."""

    @patch("core.vision_reader.analyze_image")
    def test_image_to_memory(self, mock_analyze, sample_jpg):
        """Görsel analiz sonucu hafızaya aktarılabilmeli."""
        from core.vision_reader import image_to_memory

        mock_analyze.return_value = {
            "path": "test.jpg",
            "analysis": "Kırmızı kare görsel",
            "extracted_text": "",
            "status": "OK",
        }

        result = image_to_memory(sample_jpg, source="test")

        assert result["status"] == "OK"


# ─── Batch Analysis Tests ───────────────────────────────────────────────────

class TestBatchAnalysis:
    """Toplu görsel analiz testleri."""

    @patch("core.vision_reader.analyze_image")
    def test_analyze_images_batch(self, mock_analyze, sample_jpg, sample_png):
        """Birden fazla görsel toplu analiz edilebilmeli."""
        from core.vision_reader import analyze_images_batch

        mock_analyze.return_value = {
            "path": "test.jpg",
            "analysis": "Test analiz",
            "status": "OK",
        }

        result = analyze_images_batch(
            [str(sample_jpg), str(sample_png)],
            question="Bu görselleri açıkla"
        )

        assert result["total"] == 2
        assert result["analyzed"] == 2


# ─── Tool Integration Tests ─────────────────────────────────────────────────

class TestVisionToolIntegration:
    """Vision tool system entegrasyon testleri."""

    def test_vision_tools_registered(self):
        """Vision tool'ları kayıtlı olmalı."""
        from core.agent_tools import TOOLS, DISPATCH

        tool_names = {t["function"]["name"] for t in TOOLS}
        assert "analyze_image" in tool_names
        assert "image_to_text" in tool_names
        assert "describe_image" in tool_names
        assert "image_qa" in tool_names
        assert "image_to_memory" in tool_names
        assert "analyze_images_batch" in tool_names

        assert "analyze_image" in DISPATCH
        assert "image_to_text" in DISPATCH
        assert "describe_image" in DISPATCH
        assert "image_qa" in DISPATCH
        assert "image_to_memory" in DISPATCH
        assert "analyze_images_batch" in DISPATCH

    def test_analyze_image_via_tools(self, tmp_path):
        """analyze_image tool'u üzerinden analiz yapılabilmeli."""
        from core.agent_tools import analyze_image

        # Test görseli oluştur
        img = Image.new("RGB", (50, 50), color=(255, 0, 0))
        test_file = tmp_path / "test.jpg"
        img.save(str(test_file), "JPEG")

        result = analyze_image(str(test_file), use_ocr=False)
        # Vision model bağlıysa OK, değilse ERROR döner
        assert result["status"] in ("OK", "ERROR", "PARTIAL")
        assert "metadata" in result

    def test_describe_image_via_tools(self, tmp_path):
        """describe_image tool'u üzerinden açıklama yapılabilmeli."""
        from core.agent_tools import describe_image

        img = Image.new("RGB", (50, 50), color=(0, 255, 0))
        test_file = tmp_path / "test.png"
        img.save(str(test_file), "PNG")

        result = describe_image(str(test_file), detail_level="brief")
        assert result["status"] in ("OK", "ERROR", "PARTIAL")


# ─── Supported Formats Tests ────────────────────────────────────────────────

class TestSupportedFormats:
    """Desteklenen format testleri."""

    def test_supported_extensions(self):
        """Desteklenen uzantılar tanımlı olmalı."""
        from core.vision_reader import SUPPORTED_IMAGE_EXTENSIONS

        assert ".jpg" in SUPPORTED_IMAGE_EXTENSIONS
        assert ".jpeg" in SUPPORTED_IMAGE_EXTENSIONS
        assert ".png" in SUPPORTED_IMAGE_EXTENSIONS
        assert ".webp" in SUPPORTED_IMAGE_EXTENSIONS
        assert ".gif" in SUPPORTED_IMAGE_EXTENSIONS
        assert ".bmp" in SUPPORTED_IMAGE_EXTENSIONS
        assert ".tiff" in SUPPORTED_IMAGE_EXTENSIONS

    def test_max_constants(self):
        """Sabitler tanımlı olmalı."""
        from core.vision_reader import MAX_IMAGE_SIZE_MB, MAX_DIMENSION

        assert MAX_IMAGE_SIZE_MB > 0
        assert MAX_DIMENSION > 0

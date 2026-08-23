# UMAY 9 — PANEL VISION & DOCUMENT FLOW

**Tarih:** 2026-08-23

---

## VISION PIPELINE

### Tam Akış

```
Kullanıcı resim yükler (Chat veya Telegram)
    ↓
[1] attachment_engine.py — classify_file()
    Extension kontrolü: .jpg, .png, .gif, .bmp, .tiff, .webp
    Sonuç: "image"
    ↓
[2] attachment_engine.py — process_image()
    Pillow ile metadata okuma (boyut, format, EXIF)
    base64'e dönüştürme
    _image_store'a kaydetme (hash → base64)
    ↓
[3] panel_server.py — chat_attach()
    _image_store[hash] = base64
    Response: {ok: true, is_vision: true, type: "image"}
    ↓
[4] panel_server.py — execute_chat_task()
    has_image = True
    resolve_model("vision") → gemma3:4b
    ↓
[5] panel_server.py — vision path
    vision_msgs = [
        {role: "system", content: UMAY_SYSTEM},
        {role: "user", content: att_context, images: [base64]}
    ]
    Ollama API: POST /api/chat
    payload: {model: "gemma3:4b", messages: vision_msgs, stream: false}
    ↓
[6] gemma3:4b → görsel analiz → cevap
    ↓
[7] cevap → conversation_store → Telegram/frontend
```

### Vision Roadblocks

| Sorun | Kök Neden | Durum |
|-------|-----------|-------|
| "Vision sonucu boş" | Eski: gemma3:4b tool desteklemiyordu | ✅ Çözüldü (tool kaldırıldı) |
| TOOL hatası | `gemma3:4b does not support tools` | ✅ Çözüldü (vision'da tool yok) |
| Çok yavaş | gemma3:4b ~65s | ⚠️ Kabul edilebilir |
| OCR sınırlı | Tesseract kurulu değil | ⚠️ Ollama vision ile telafi ediliyor |

### Vision Pipeline Kontrol Noktaları

1. ✅ **Dosya algılama** — classify_file() doğru çalışıyor
2. ✅ **base64 dönüşümü** — image_to_base64() çalışıyor
3. ✅ **Model seçimi** — gemma3:4b / llava:7b
4. ✅ **Ollama çağrısı** — /api/chat + images array
5. ✅ **Cevap dönme** — doğru formatta

### Eksik Olanlar
- ❌ Vision model seçimi (kullanıcı seçemiyor)
- ❌ OCR detaylı sonuç (sadece Ollama vision)
- ❌ Batch processing (tek tek yapılıyor)
- ❌ Vision sonuç kaydetme (memory'ye aktarım opsiyonel)

---

## DOCUMENT PIPELINE

### Tam Akış

```
Kullanıcı dosya yükler (.pdf, .docx, .xlsx, .csv)
    ↓
[1] attachment_engine.py — classify_file()
    Extension kontrolü
    Sonuç: "pdf" / "docx" / "xlsx" / "csv" / "text"
    ↓
[2] attachment_engine.py — process_document()
    PDF → pypdf: PdfReader ile text extraction
    DOCX → python-docx: Document ile text extraction
    XLSX → openpyxl: Workbook ile cell extraction
    CSV → csv.reader ile satır okuma
    TEXT →直接 read_text()
    ↓
[3] Content truncated (MAX_TEXT_CONTENT = 15000 chars)
    ↓
[4] panel_server.py — chat_attach()
    Response: {ok: true, content: "...", has_content: true}
    ↓
[5] panel_server.py — execute_chat_task()
    att_context = build_chat_context(attachments, soru)
    messages = [
        {role: "system", content: _system_prompt},
        *history,
        {role: "user", content: att_context}
    ]
    ↓
[6] engine.chat(messages, model=analysis_model)
    ↓
[7] Model: granite3.3:8b veya qwen3:8b → belge analizi → cevap
```

### Document Roadblocks

| Sorun | Kök Neden | Durum |
|-------|-----------|-------|
| PDF image-based | pypdf sadece text extraction | ⚠️ OCR gerekli |
| DOCX karmaşık | python-docx sınırlı | ⚠️ Tablo/image çıkarmıyor |
| XLSX büyük | openpyxl bellek kullanıyor | ⚠️ MAX_EXCEL_ROWS=500 |
| Encoding sorunu |latin-1 fallback | ✅ Çözüldü |
| Çok yavaş | granite3.3:8b ~260s | ❌ Çok uzun |

### Document Pipeline Kontrol Noktaları

1. ✅ **Dosya algılama** — doğru format tespiti
2. ✅ **Text extraction** — PDF, DOCX, XLSX, CSV
3. ✅ **Encoding handling** — chardet + latin-1 fallback
4. ✅ **Truncation** — 15000 karakter sınırı
5. ⚠️ **Model seçimi** — granite3.3:8b çok yavaş
6. ✅ **Cevap dönme** — doğru formatta

### Eksik Olanlar
- ❌ Image-based PDF OCR
- ❌ DOCX image/table extraction
- ❌ Document summary caching
- ❌ Document → memory aktarımı
- ❌ Large document chunking

---

## ATTACHMENT ENGINE DETAY

### Dosya Sınıflandırma

```python
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".csv",
    ".html", ".css", ".xml", ".yaml", ".yml", ".toml",
    ".log", ".sh", ".bat", ".ps1", ".sql", ".r", ".go", ".rs",
    ".java", ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift",
    ".kt", ".scala", ".ini", ".cfg", ".conf", ".env",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
XLSX_EXTENSIONS = {".xlsx", ".xls"}
UNSUPPORTED_EXTENSIONS = {".exe", ".dll", ".so", ".bin", ".zip", ".rar"}
```

### Boyut Sınırları
- MAX_FILE_SIZE = 20 MB
- MAX_TEXT_CONTENT = 15,000 chars
- MAX_TABLE_ROWS = 100
- MAX_IMAGE_DIMENSION = 2048 px

---

## TELEGRAM VISION FLOW

```
Telegram'dan resim gönderilir
    ↓
telegram_user_adapter.py — _handle_media()
    ↓
Dosya indirilir → /tmp/ veya uploads/
    ↓
attachment_engine.py — process_upload()
    ↓
_base64 → vision_msgs → Ollama API
    ↓
gemma3:4b → görsel analiz → cevap
    ↓
Telegram'a cevap gönderilir
```

---

## V2 İÇİN ÖNERİLER

### Vision
1. Model seçimi (gemma3:4b vs llava:7b)
2. OCR entegrasyonu (Tesseract opsiyonel)
3. Vision sonuç kaydetme (memory'ye)
4. Batch vision (çoklu görsel)

### Document
1. Hızlı model tercihi (granite3.3 yerine qwen3:8b)
2. Image-based PDF OCR
3. Document chunking (büyük dosyalar için)
4. Document summary caching
5. Document → memory aktarımı

### Genel
1. Attachment tip seçimini kullanıcıya bırakma
2. Processing status gösterme (backend'de)
3. Error recovery (model başarısız olursa fallback)

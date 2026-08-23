# UMAY 9 — PANEL MODEL MAP

**Tarih:** 2026-08-23

---

## MEVCUT MODELLER (11 adet)

| Model | Local | Chat | Coding | Tool Calling | Vision | Hız | RAM | Görev |
|-------|-------|------|--------|--------------|--------|-----|-----|-------|
| phi4-mini:latest | ✅ | ✅ İyi | ❌ | ✅ | ❌ | ⚡ Hızlı | ~2GB | Chat varsayılan |
| qwen3:8b | ✅ | ✅ | ✅ | ✅ | ❌ | Orta | ~5GB | Reasoning + Coding |
| qwen2.5-coder:7b | ✅ | ⚠️ | ✅ Çok İyi | ✅ | ❌ | Orta | ~4GB | Coding birincil |
| gemma3:4b | ✅ | ✅ | ⚠️ | ❌ | ✅ | ⚡ Hızlı | ~3GB | Vision birincil |
| gemma2:9b | ✅ | ✅ | ✅ | ✅ | ❌ | Orta | ~5GB | Genel amaçlı |
| deepseek-r1:8b | ✅ | ✅ | ✅ | ✅ | ❌ | Yavaş | ~5GB | Reasoning (chain-of-thought) |
| granite3.3:8b | ✅ | ✅ | ⚠️ | ❌ | ❌ | Yavaş | ~5GB | Document analysis |
| llava:7b | ✅ | ⚠️ | ❌ | ❌ | ✅ İyi | Yavaş | ~4GB | Vision (eski) |
| bge-m3:latest | ❌ | ❌ | ❌ | ❌ | ❌ | ⚡ | ~1GB | Embedding |
| nomic-embed-text:latest | ❌ | ❌ | ❌ | ❌ | ❌ | ⚡ | ~0.3GB | Embedding |
| gpt-oss:20b-cloud | ✅ | ✅ | ✅ | ✅ | ❌ | Yavaş | ~12GB | Genel amaçlı (büyük) |

---

## MODEL ROUTING (engine.py)

```python
MODEL_PREFERENCES = {
    "chat":      ["phi4-mini:latest", "qwen3:8b", "gemma2:9b", "gemma3:4b"],
    "agent":     ["qwen2.5-coder:7b", "qwen3:8b", "gemma2:9b"],
    "vision":    ["gemma3:4b", "llava:7b", "llava:latest"],
    "reasoning": ["deepseek-r1:8b", "qwen3:8b", "gemma2:9b"],
    "coding":    ["qwen2.5-coder:7b", "qwen3:8b", "deepseek-coder:6.7b", "gemma3:4b"],
    "analysis":  ["granite3.3:8b", "qwen3:8b", "gemma2:9b"],
    "embedding": ["bge-m3:latest", "nomic-embed-text:latest"],
    "backup":    ["gemma2:9b", "qwen3:8b", "gemma3:4b"],
}
```

---

## INTENT → MODEL ROUTING (intent_router.py + agent.py)

| Intent | Model Tercihi | Tool Kullanımı | Gerçek Kullanım |
|--------|---------------|----------------|-----------------|
| CHAT | chat (phi4-mini) | Tool yok | ✅ Doğal sohbet |
| KNOWLEDGE | chat (phi4-mini) | Tool yok | ✅ Bilgi soruları |
| TIME | chat (phi4-mini) | get_current_time, get_current_date | ✅ Gerçek saat |
| CALCULATOR | chat (phi4-mini) | evaluate_expression | ✅ Matematik |
| FILE | chat (phi4-mini) | list_directory, read_file, search_files... | ✅ Dosya işlemleri |
| DOCUMENT | analysis (granite3.3) | read_document, scan_directory... | ✅ PDF/Word okuma |
| VISION | vision (gemma3:4b) | analyze_image, image_to_text... | ✅ Görsel analiz |
| WEB | chat (phi4-mini) | web_search, browser_open... | ✅ Web araştırması |
| CODE | coding (qwen2.5-coder) | read_file, write_file, run_command... | ✅ Kod yazma |
| TERMINAL | agent (qwen2.5-coder) | run_command, get_system_info... | ✅ Komut çalıştırma |
| MEMORY | chat (phi4-mini) | Tool yok | ⚠️ Henüz pasif |
| COMPLEX | reasoning (deepseek-r1) | Tüm tool'lar | ⚠️ Agent loop |

---

## PROVIDER MİMARİSİ (model_providers.py)

```
User Request
    ↓
_get_provider_and_model(task, requested_model)
    ↓
1. PROVIDER_<TASK> env var kontrol → task-specific provider
2. PRIMARY_PROVIDER env var kontrol → genel provider
3. OllamaProvider fallback → local Ollama
    ↓
Provider.chat(messages, model, tools)
    ↓
OllamaProvider → http://host.docker.internal:11434/api/chat
    ↓
OpenAI-compatible → Generic provider (MiMo, DeepSeek, GPT, Claude)
```

### Provider Seçimi Sırası
1. **Task-specific:** `PROVIDER_VISION=gemma3`, `PROVIDER_CODING=qwen2.5-coder`
2. **Primary:** `PRIMARY_PROVIDER=OLLAMA` (env'de ayarlı)
3. **Fallback:** Ollama her zaman kullanılabilir

---

## CHAT FLOW (panel_server.py → engine.py)

```
User: "Merhaba"
    ↓
panel_server.py: chat_api()
    ↓
execute_chat_task()
    ↓
classify_intent("Merhaba") → Intent.CHAT
    ↓
CHAT_IDENTITY prompt seçimi
    ↓
use_tools = None (CHAT için tool yok)
    ↓
engine.chat(messages, model=phi4-mini, tools=None)
    ↓
OllamaProvider.chat() → Ollama API
    ↓
Cevap → conversation_store'a kaydet → Telegram'a dön
```

---

## TOOL CALLING FLOW

```
User: "Klasörü listele"
    ↓
classify_intent() → Intent.FILE
    ↓
get_available_tools(Intent.FILE) → ["list_directory", "read_file", ...]
    ↓
active_tools = [t for t in TOOLS if t["name"] in intent_tools_list]
    ↓
engine.chat(messages, model=phi4-mini, tools=active_tools)
    ↓
Ollama → tool_calls: [{name: "list_directory", args: {path: "."}}]
    ↓
DISPATCH["list_directory"](path=".") → gerçek dosya listesi
    ↓
Tool sonucu modele geri ver → Final cevap
```

---

## VISION FLOW

```
User: resim gönderir + "Bu resimde ne var?"
    ↓
panel_server.py: chat_attach() → process_upload()
    ↓
attachment_engine: classify_file() → "image"
    ↓
Image base64'e dönüştür → _image_store'a kaydet
    ↓
execute_chat_task(): has_image = True
    ↓
resolve_model("vision") → gemma3:4b
    ↓
Ollama API: /api/chat {model: "gemma3:4b", messages: [..., images: [base64]]}
    ↓
Vision model → görsel analiz → cevap
```

---

## DOCUMENT FLOW

```
User: .docx dosyası gönderir
    ↓
attachment_engine: classify_file() → "docx"
    ↓
docx → python-docx ile text extraction
    ↓
Metin content → soruyla birlikte modele gönderilir
    ↓
Model: granite3.3:8b (analysis task) → özet/analiz
```

---

## MODELLERİN GÜÇLÜ/ZAYIF YANLARI

### phi4-mini:latest (Chat Varsayılan)
- ✅ Hızlı, düşük kaynak
- ✅ Tool calling destekliyor
- ✅ Türkçe iyi
- ❌ Vision yok
- ❌ Kodda zayıf

### qwen3:8b (Reasoning)
- ✅ Güçlü reasoning
- ✅ Tool calling
- ✅ Coding iyi
- ❌ Yavaş
- ❌ Büyük (~5GB)

### qwen2.5-coder:7b (Coding)
- ✅ Kodda çok iyi
- ✅ Tool calling
- ❌ Doğal sohbet zayıf
- ❌ Vision yok

### gemma3:4b (Vision)
- ✅ Vision çalışıyor
- ✅ Hızlı
- ❌ Tool calling desteklemiyor
- ❌ Kodda zayıf

### deepseek-r1:8b (Reasoning)
- ✅ Chain-of-thought reasoning
- ❌ Çok yavaş
- ❌ Tool calling tartışmalı

### granite3.3:8b (Document)
- ✅ Document analysis iyi
- ❌ Çok yavaş (260s test edildi)
- ❌ Tool calling yok

### llava:7b (Vision - eski)
- ✅ Vision destekliyor
- ❌ Eski model, kalite düşük
- ❌ Yavaş

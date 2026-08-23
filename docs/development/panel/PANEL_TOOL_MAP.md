# UMAY 9 — PANEL TOOL MAP

**Tarih:** 2026-08-23

---

## TOPLAM: 62 TOOL

---

## FILESYSTEM TOOLS (6)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| list_directory | `list_directory()` | ✅ | ✅ | FILE | ❌ |
| read_file | `read_file()` | ✅ | ✅ | FILE | ❌ |
| search_files | `search_files()` | ✅ | ✅ | FILE | ❌ |
| write_file | `write_file()` | ✅ | ✅ | CODE | ❌ |
| open_file | `open_file()` | ✅ | ⚠️ | FILE | ❌ |
| open_folder | `open_folder()` | ✅ | ⚠️ | FILE | ❌ |

### Workflow
```
USER: "Klasörü listele"
    ↓
Intent: FILE
    ↓
Tools: [list_directory, read_file, search_files, open_file, open_folder, scan_directory]
    ↓
Model: list_directory(path=".") çağırır
    ↓
DISPATCH["list_directory"](path=".") → {workspace, count, entries}
    ↓
Sonuç kullanıcıya gösterilir
```

---

## TIME TOOLS (2)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| get_current_time | `get_current_time()` | ✅ | ✅ | TIME | ❌ |
| get_current_date | `get_current_date()` | ✅ | ✅ | TIME | ❌ |

### Workflow
```
USER: "Şu an saat kaç?"
    ↓
Intent: TIME
    ↓
Tools: [get_current_time, get_current_date]
    ↓
Model: get_current_time(timezone="Europe/Istanbul") çağırır
    ↓
DISPATCH → {time: "03:45:12", datetime: "2026-08-23 03:45:12", ...}
    ↓
Model: "Şu anda saat 03:45."
```

---

## CALCULATOR TOOL (1)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| evaluate_expression | `evaluate_expression()` | ✅ | ✅ | CALCULATOR | ❌ |

### Workflow
```
USER: "9/1*2-3+4"
    ↓
Intent: CALCULATOR
    ↓
Tools: [evaluate_expression]
    ↓
Model: evaluate_expression(expression="9/1*2-3+4") çağırır
    ↓
DISPATCH → {result: 19.0, formatted: "9/1*2-3+4 = 19.0"}
    ↓
Model: "Sonuç: 19"
```

---

## TERMINAL TOOLS (7)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| run_command | `run_command()` | ✅ | ✅ | TERMINAL | ❌ |
| run_terminal_command | `run_terminal_command()` | ✅ | ✅ | TERMINAL | ❌ |
| run_powershell | `run_powershell()` | ✅ | ⚠️ | TERMINAL | ❌ |
| get_system_info | `get_system_info()` | ✅ | ✅ | TERMINAL | ❌ |
| list_processes | `list_processes()` | ✅ | ⚠️ | TERMINAL | ❌ |
| find_process | `find_process()` | ✅ | ⚠️ | TERMINAL | ❌ |
| read_log_file | `read_log_file()` | ✅ | ⚠️ | TERMINAL | ❌ |

---

## DOCUMENT TOOLS (4)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| read_document | `read_document()` | ✅ | ✅ | DOCUMENT | ❌ |
| scan_directory | `scan_directory()` | ✅ | ⚠️ | DOCUMENT | ❌ |
| search_in_documents | `search_in_documents()` | ✅ | ⚠️ | DOCUMENT | ❌ |
| document_to_memory | `document_to_memory()` | ✅ | ⚠️ | DOCUMENT | ❌ |

---

## VISION TOOLS (6)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| analyze_image | `analyze_image()` | ✅ | ✅ | VISION | ❌ |
| image_to_text | `image_to_text()` | ✅ | ✅ | VISION | ❌ |
| describe_image | `describe_image()` | ✅ | ✅ | VISION | ❌ |
| image_qa | `image_qa()` | ✅ | ✅ | VISION | ❌ |
| image_to_memory | `image_to_memory()` | ✅ | ⚠️ | VISION | ❌ |
| analyze_images_batch | `analyze_images_batch()` | ✅ | ⚠️ | VISION | ❌ |

---

## WEB TOOLS (7)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| web_search | `web_search()` | ✅ | ✅ | WEB | ❌ |
| browser_open | `browser_open()` | ✅ | ⚠️ | WEB | ⚠️ |
| browser_read | `browser_read()` | ✅ | ⚠️ | WEB | ❌ |
| browser_click | `browser_click()` | ✅ | ⚠️ | WEB | ❌ |
| browser_type | `browser_type()` | ✅ | ⚠️ | WEB | ❌ |
| browser_screenshot | `browser_screenshot()` | ✅ | ⚠️ | WEB | ❌ |
| browser_close | `browser_close()` | ✅ | ⚠️ | WEB | ❌ |

---

## EMAIL TOOLS (8)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| gmail_list_emails | `_gmail_list_emails()` | ✅ | ⚠️ | EMAIL | ❌ |
| gmail_search | `_gmail_search()` | ✅ | ⚠️ | EMAIL | ❌ |
| gmail_get_email | `_gmail_get_email()` | ✅ | ⚠️ | EMAIL | ❌ |
| gmail_list_attachments | `_gmail_list_attachments()` | ✅ | ⚠️ | EMAIL | ❌ |
| gmail_summarize | `_gmail_summarize()` | ✅ | ⚠️ | EMAIL | ❌ |
| gmail_draft_reply | `_gmail_draft_reply()` | ✅ | ⚠️ | EMAIL | ❌ |
| gmail_folder_info | `_gmail_folder_info()` | ✅ | ⚠️ | EMAIL | ❌ |
| gmail_send_email | `_gmail_send_email()` | ✅ | ⚠️ | EMAIL | ❌ |

### Durum
- Gmail credential'ları `.env'de` ayarlı değil
- `GMAIL_USER` env var yok
- Tool'lar var ama çalışmıyor (credentials gerekli)

---

## CODE TOOLS (7)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| read_code | `read_code()` | ✅ | ⚠️ | CODE | ❌ |
| generate_code | `generate_code()` | ✅ | ⚠️ | CODE | ❌ |
| explain_code | `explain_code()` | ✅ | ⚠️ | CODE | ❌ |
| find_bugs | `find_bugs()` | ✅ | ⚠️ | CODE | ❌ |
| write_test | `write_test()` | ✅ | ⚠️ | CODE | ❌ |
| run_code_tests | `run_code_tests()` | ✅ | ⚠️ | CODE | ❌ |
| analyze_project_code | `analyze_project_code()` | ✅ | ⚠️ | CODE | ❌ |

---

## WEB RESEARCH TOOLS (5)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| research_topic | `_research_topic()` | ✅ | ⚠️ | WEB | ❌ |
| quick_research | `_quick_research()` | ✅ | ⚠️ | WEB | ❌ |
| research_with_queries | `_research_with_queries()` | ✅ | ⚠️ | WEB | ❌ |
| open_and_read_page | `_open_and_read_page()` | ✅ | ⚠️ | WEB | ❌ |
| search_web | `_search_web()` | ✅ | ⚠️ | WEB | ❌ |

---

## SYSTEM TOOLS (4)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| run_test_suite | `run_test_suite()` | ✅ | ✅ | TERMINAL | ❌ |
| git_diff_summary | `git_diff_summary()` | ✅ | ⚠️ | TERMINAL | ❌ |
| rollback_backup | `rollback_backup()` | ✅ | ⚠️ | CODE | ❌ |
| inspect_project | `inspect_project()` | ✅ | ⚠️ | COMPLEX | ❌ |

---

## URL/APP TOOLS (3)

| Tool | Fonksiyon | Çalışıyor | Test | Intent | Panel |
|------|-----------|-----------|------|--------|-------|
| open_url | `open_url()` | ✅ | ⚠️ | FILE | ❌ |
| open_with_app | `open_with_app()` | ✅ | ⚠️ | FILE | ❌ |
| extract_page_tables | `extract_page_tables()` | ✅ | ⚠️ | WEB | ❌ |

---

## TOOL KATEGORİ ÖZETİ

| Kategori | Tool Sayısı | Çalışan | Test Edilen | Panel'de Görünen |
|----------|------------|---------|-------------|------------------|
| Filesystem | 6 | 6 | 4 | 0 |
| Time | 2 | 2 | 2 | 0 |
| Calculator | 1 | 1 | 1 | 0 |
| Terminal | 7 | 7 | 3 | 0 |
| Document | 4 | 4 | 1 | 0 |
| Vision | 6 | 6 | 4 | 0 |
| Web | 7 | 7 | 1 | 1 (browser) |
| Email | 8 | 8 | 0 | 0 |
| Code | 7 | 7 | 0 | 0 |
| Web Research | 5 | 5 | 0 | 0 |
| System | 4 | 4 | 1 | 0 |
| URL/App | 3 | 3 | 0 | 0 |
| **Toplam** | **60** | **60** | **17** | **1** |

### Panel'de Tool Yönetimi
- Tool listesi: `/api/tools` → sadece name + description gösteriyor
- Tool detayı: ❌ Yok
- Tool çalıştırma: ❌ Yok
- Tool test: ❌ Yok
- Tool durumu: ❌ Yok

### Tool Security (APPROVAL_TOOLS)
```python
APPROVAL_TOOLS = {
    "write_file",
    "rollback_backup",
    "run_command",
    "run_terminal_command",
    "run_powershell",
    "browser_click",
    "browser_type",
    "gmail_send_email",
}
```

Bu tool'lar çalıştırılmadan önce kullanıcı onayı gerektirir.
Onay mekanizması: `approval_manager.py` → `needs_approval()`
Panel'de: ❌ Approvals sayfası boş

---

## V2 İÇİN ÖNERİLER

1. **Tool registry sayfası** — her tool'un detayı, parametreleri, örnekleri
2. **Tool test butonu** — panel'den tool'u test etme
3. **Tool durumu** — hangi tool'un çalıştığı
4. **Tool usage logs** — hangi tool ne zaman çağrıldı
5. **Tool permission management** — hangi tool'un onay gerektirdiğini değiştirme

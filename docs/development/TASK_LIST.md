# UMAY 9 — KAPSAMLI GÖREV LİSTESİ
**Tarih:** 2026-08-23 02:15
**Durum:** Araştırma tamamlandı, uygulama başlıyor

---

## MEVCUT TOOL SİSTEMİ

DISPATCH dictionary'sinde 55+ tool mevcut:

### Dosya Araçları
- list_directory, read_file, search_files, write_file
- scan_directory, search_in_documents
- open_file, open_folder, open_url, open_with_app

### Kod Araçları
- run_command, run_test_suite, run_terminal_command, run_powershell
- read_code, generate_code, explain_code, find_bugs, write_test
- run_code_tests, analyze_project_code, code_assist
- git_diff_summary, rollback_backup, inspect_project

### Vision Araçları
- analyze_image, image_to_text, describe_image, image_qa
- image_to_memory, analyze_images_batch

### Document Araçları
- read_document, document_to_memory

### Web/Browser Araçları
- web_search, browser_open, browser_read, browser_click
- browser_type, browser_screenshot, browser_close
- research_topic, quick_research, research_with_queries
- open_and_read_page, search_web, extract_page_tables

### Gmail Araçları
- gmail_list_emails, gmail_search, gmail_get_email
- gmail_list_attachments, gmail_summarize, gmail_draft_reply
- gmail_folder_info, gmail_send_email

### Sistem Araçları
- get_system_info, read_log_file, list_processes, find_process
- analyze_error

---

## GÖREV LİSTESİ

### FAZ 2: INTENT ROUTER (KRİTİK)

#### Görev 2.1: intent_router.py oluştur
- [ ] Intent classification fonksiyonu
- [ ] Keyword-based intent detection
- [ ] Tool selection matrix
- [ ] Model selection based on intent
- [ ] Network status check

#### Görev 2.2: agent.py'ye intent routing entegrasyonu
- [ ] run_agent fonksiyonunda intent classification
- [ ] Intent'e göre system prompt seçimi
- [ ] Intent'e göre tool selection
- [ ] Intent'e göre max_steps belirleme

#### Görev 2.3: Intent testleri
- [ ] Chat intent testleri (Merhaba, Sen kimsin, etc.)
- [ ] File intent testleri (Klasör listele, Dosya oku)
- [ ] Time intent testleri (Saat kaç, Bugün günlerden ne)
- [ ] Vision intent testleri (Bu resimde ne var)
- [ ] Web intent testleri (İnternette araştır)
- [ ] Mixed intent testleri

### FAZ 3: TOOL ROUTING (KRİTİK)

#### Görev 3.1: Tool selection based on intent
- [ ] Chat intent → 0 tools
- [ ] File intent → filesystem tools
- [ ] Time intent → time tool (yeni)
- [ ] Vision intent → vision tools
- [ ] Web intent → web tools
- [ ] Code intent → code tools
- [ ] Document intent → document tools

#### Görev 3.2: Tool permission sistemi
- [ ] Read-only tools →低风险
- [ ] Write tools → orta risk
- [ ] Delete/execute tools → yüksek risk

#### Görev 3.3: Tool routing testleri
- [ ] Her intent için doğru tool seçimi
- [ ] Permission testleri
- [ ] Error handling testleri

### FAZ 4: SYSTEM CLOCK/DATE (YÜKSEK)

#### Görev 4.1: time_tool.py oluştur
- [ ] get_current_time() fonksiyonu
- [ ] get_current_date() fonksiyonu
- [ ] get_day_of_week() fonksiyonu
- [ ] Timezone desteği
- [ ] Unix timestamp desteği

#### Görev 4.2: DISPATCH'e ekle
- [ ] "get_current_time" → time_tool.get_current_time
- [ ] "get_current_date" → time_tool.get_current_date

#### Görev 4.3: Time testleri
- [ ] "Şu an saat kaç?" → gerçek saat
- [ ] "Bugün günlerden ne?" → gerçek gün
- [ ] "Bugünün tarihi ne?" → gerçek tarih

### FAZ 5: VISION PIPELINE (YÜKSEK)

#### Görev 5.1: Vision model konfigürasyonu
- [ ] Hangi modeller tool destekliyor?
- [ ] Hangi modeller vision destekliyor?
- [ ] Tool-free vision pipeline

#### Görev 5.2: Vision pipeline fix
- [ ] Photo geldiğinde tool kullanmadan vision
- [ ] Vision sonucunu text olarak dön
- [ ] Opsiyonel: vision sonucu + tool

#### Görev 5.3: Vision testleri
- [ ] Basit fotoğraf analizi
- [ ] Ekran görüntüsü analizi
- [ ] Hata ekran görüntüsü
- [ ] PDF sayfa görüntüsü
- [ ] Resim + soru

### FAZ 6: DOCUMENT PIPELINE (ORTA)

#### Görev 6.1: Document pipeline iyileştirme
- [ ] PDF text extraction
- [ ] Image-based PDF OCR
- [ ] Document chunking
- [ ] Context window management

#### Görev 6.2: Document testleri
- [ ] PDF okuma
- [ ] Word okuma
- [ ] Excel okuma
- [ ] CSV okuma

### FAZ 7: OFFLINE/ONLINE DETECTION (ORTA)

#### Görev 7.1: Network detection
- [ ] check_network() fonksiyonu
- [ ] Online/offline/degraded durumları
- [ ] Network status caching

#### Görev 7.2: Offline fallback
- [ ] Online tool başarısızsa offline fallback
- [ ] "İnternet yok" mesajı
- [ ] Local alternatif kullanımı

### FAZ 8: ONLINE PROVIDER (ORTA)

#### Görev 8.1: Online provider abstraction
- [ ] OnlineProvider base class
- [ ] OpenAI-compatible provider
- [ ] MiMo provider (eğer API varsa)

#### Görev 8.2: Model switching
- [ ] Local → Online geçiş
- [ ] Online → Local fallback
- [ ] Kullanıcı kontrolü

### FAZ 9: HYBRID EXECUTION (ORTA)

#### Görev 9.1: Hybrid planner
- [ ] Görev analizi
- [ ] Local vs online ihtiyacı
- [ ] Hybrid execution planı

### FAZ 10: MEMORY PIPELINE (ORTA)

#### Görev 10.1: Context management
- [ ] Conversation history optimizasyonu
- [ ] Memory retrieval
- [ ] Context window yönetimi

### FAZ 11: RESPONSE QUALITY (ORTA)

#### Görev 11.1: Response validation
- [ ] Boş cevap kontrolü
- [ ] Alakasız cevap kontrolü
- [ ] Uydurma bilgi kontrolü

### FAZ 12: TELEGRAM E2E (YÜKSEK)

#### Görev 12.1: Telegram testleri
- [ ] Tüm intent'ler için Telegram testi
- [ ] Conversation history testi
- [ ] Error handling testi

---

## ÖNCELİK SIRASI

1. FAZ 2: Intent Router (EN KRİTİK)
2. FAZ 3: Tool Routing
3. FAZ 4: System Clock
4. FAZ 5: Vision Pipeline
5. FAZ 6: Document Pipeline
6. FAZ 7: Offline/Online
7. FAZ 8: Online Provider
8. FAZ 9: Hybrid Execution
9. FAZ 10: Memory
10. FAZ 11: Response Quality
11. FAZ 12: Telegram E2E

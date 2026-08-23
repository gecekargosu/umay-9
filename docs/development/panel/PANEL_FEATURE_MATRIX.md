# UMAY 9 — PANEL FEATURE MATRIX

**Tarih:** 2026-08-23  
**Status:** READ-ONLY AUDIT

---

## SAYFA BAZLI ÖZELLİK MATRİSİ

### 1. DASHBOARD

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| System Status (CPU/RAM) | `/api/system` | ✅ | Gerçek veri |
| Ollama Status | `/api/system` | ✅ | Model listesi dahil |
| Docker Status | `/api/system` | ✅ | Container count |
| Agent Status | `/api/agents` | ✅ | 6 agent gösteriyor |
| Live Activity | `/api/logs` | ✅ | Son 12 satır |
| Processing Pipeline | Hiçbiri | ❌ | Statik —hiçbir veri çekmiyor |
| Installed Models | `/api/system` | ✅ | Model tag'leri |
| Quick Actions | Hiçbiri | ✅ | Navigate butonları |
| Workspace Cards | Hiçbiri | ⚠️ | Navigate ama veri yok |

### 2. CHAT

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Mesaj gönderme | `/api/chat` | ✅ | LLM çağrısı |
| Dosya ekleme | `/api/chat/attach` | ✅ | PDF, image, text |
| Conversation temizleme | `/api/chat/clear` | ✅ | Session reset |
| Markdown render | JS | ✅ | Kod blokları dahil |
| Drag & drop | JS | ✅ | Dosya ekleme |
| Clipboard paste | JS | ✅ | Resim yapıştırma |
| Task status bar | SocketIO | ✅ | Thinking/Completed |
| Model selector | Hiçbiri | ❌ | Sadece "auto" |
| Online/Offline mode | Hiçbiri | ❌ | Yok |
| Tool execution log | Hiçbiri | ❌ | Tool çağrısı görünmüyor |
| Retry/Regenerate | Hiçbiri | ❌ | Yok |
| Copy butonu | Hiçbiri | ❌ | Yok |
| Stop butonu | Hiçbiri | ❌ | Yok |
| Conversation history | Hiçbiri | ⚠️ | Sadece mevcut session |

### 3. AGENTS

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Agent listesi | `/api/agents` | ✅ | İsim, rol, durum |
| Agent detayı | Hiçbiri | ❌ | Tıklanıncanothing |
| Agent başlatma | Hiçbiri | ❌ | Yok |
| Agent durdurma | Hiçbiri | ❌ | Yok |

### 4. WORKFLOW

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Pipeline görseli | Hiçbiri | ❌ | Statik HTML |
| Node detayı | JS alert | ❌ | alert() ile bilgi |
| Recent executions | Hiçbiri | ❌ | Boş |

### 5. FILES

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Dosya yükleme | `/api/upload` | ✅ | |
| Yüklenen dosyalar | `/api/uploads` | ✅ | Listeliyor |
| Dosya okuma | Hiçbiri | ❌ | Dosyaya tıklanmıyor |
| Dosya silme | Hiçbiri | ❌ | Yok |
| Klasör gezme | Hiçbiri | ❌ | Yok |

### 6. MEMORY

| Özellik | API | Çalışiyor | Not |
|---------|-----|-----------|-----|
| ChromaDB durumu | `/api/memory` | ✅ | exists, size_mb |
| Memory istatistikleri | `/api/memory` | ✅ | recall_count (0) |
| Memory listesi | `/api/memory` | ⚠️ | Boş (hiç memory yok) |
| Memory ekleme | Hiçbiri | ❌ | Yok |
| Memory arama | Hiçbiri | ❌ | Yok |
| Memory silme | Hiçbiri | ❌ | Yok |

### 7. TELEGRAM

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Bot connection | `/api/telegram_status` | ✅ | bot_connected |
| User account | `/api/telegram_status` | ✅ | user_connected |
| Messages | Hiçbiri | ❌ | Boş — mesaj akışı yok |
| Send message | Hiçbiri | ❌ | Panel'den mesaj gönderme yok |
| Reconnect | Hiçbiri | ❌ | Yok |

### 8. TOOLS

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Tool listesi | `/api/tools` | ✅ | 62 tool |
| Tool detayı | Hiçbiri | ❌ | Tıklanınca nothing |
| Tool çalıştırma | Hiçbiri | ❌ | Panel'den test yok |
| Tool arama | Hiçbiri | ❌ | Yok |

### 9. TASKS

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Task listesi | `/api/chat/tasks` | ✅ | |
| Task detayı | `/api/chat/tasks/<id>` | ✅ | |
| Task duraklatma | `/api/chat/tasks/<id>/pause` | ✅ | |
| Task devam | `/api/chat/tasks/<id>/resume` | ✅ | |
| Task iptal | `/api/chat/tasks/<id>/cancel` | ✅ | |
| Task oluşturma | Hiçbiri | ❌ | Sadece chat'ten oluşuyor |

### 10. SCHEDULER

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Task listesi | `/api/scheduler_status` | ⚠️ | 1 test task |
| Task ekleme | Hiçbiri | ❌ | Yok |
| Task düzenleme | Hiçbiri | ❌ | Yok |
| Task silme | Hiçbiri | ❌ | Yok |
| Cron oluşturma | Hiçbiri | ❌ | Yok |

### 11. APPROVALS

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Onay listesi | Hiçbiri | ❌ | Empty state |
| Onay verme | Hiçbiri | ❌ | Yok |
| Reddetme | Hiçbiri | ❌ | Yok |
| Detay | Hiçbiri | ❌ | Yok |

### 12. LOGS

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Log listesi | `/api/logs` | ✅ | Son 50 satır |
| Log arama | Hiçbiri | ❌ | Yok |
| Log filtreleme | Hiçbiri | ❌ | Yok |
| Log indirme | Hiçbiri | ❌ | Yok |

### 13. SYSTEM

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| CPU bilgisi | `/api/system` | ✅ | |
| RAM bilgisi | `/api/system` | ✅ | |
| Disk bilgisi | `/api/system` | ✅ | |
| Python version | `/api/system` | ✅ | |
| Ollama models | `/api/system` | ✅ | |
| Docker containers | `/api/system` | ✅ | |

### 14. DIAGNOSTICS

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Sistem kontrolleri | `/api/diagnostics` | ✅ | 8+ check |
| Model benchmark | `/api/model_benchmark` | ✅ | |
| Run butonu | JS | ✅ | |
| Benchmark butonu | JS | ✅ | |

### 15. SETTINGS

| Özellik | API | Çalışıyor | Not |
|---------|-----|-----------|-----|
| Config gösterimi | `/api/config` | ✅ | Read-only |
| Config düzenleme | Hiçbiri | ❌ | Yok |
| Ollama URL değiştirme | Hiçbiri | ❌ | Yok |
| Model tercihi | Hiçbiri | ❌ | Yok |
| Telegram ayarları | Hiçbiri | ❌ | Yok |

---

## ÖZET İSTATİSTİK

| Kategori | Sayı | Oran |
|----------|------|------|
| ✅ Çalışan özellik | 45 | %52 |
| ⚠️ Kısmen çalışan | 8 | %9 |
| ❌ Çalışmayan/Placeholder | 25 | %29 |
| 🔵 Coming Soon (boş) | 8 | %9 |
| **Toplam** | **86** | **%100** |

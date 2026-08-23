# UMAY 9 — PANEL PROBLEMS LIST

**Tarih:** 2026-08-23  
**Status:** READ-ONLY AUDIT

---

## 🔴 KRİTİK PROBLEMLER (P1)

### P1.1: Tek Dosya Mimarisi
- **Durum:** ~1100 satır HTML/CSS/JS tek `panel.html` dosyasında
- **Etki:** Bakım zor,őlçekleme imkansız,调试 zor
- **Öneri:** Component-based yapıya geç (React/Vue veya modular JS)

### P1.2: Authentication Yok
- **Durum:** Panel herkese açık,hiçbir auth mekanizması yok
- **Etki:** Güvenlik açığı — herkes tool/ları çağırabilir
- **Öneri:** Basit token/session auth ekle

### P1.3: Settings Salt Okunur
- **Durum:** Hiçbir ayar değiştirilemez
- **Etki:** Kullanıcı Ollama URL, model tercihi改变edemez
- **Öneri:** Düzenlenebilir form ekle

---

## 🟡 YÜKSEK ÖNCELİK (P2)

### P2.1: Chat'te Model Selector Yok
- **Durum:** Sadece "auto" mode
- **Etki:** Kullanıcı belirli bir model seçemiyor
- **Öneri:** Dropdown ile model seçimi (auto + tüm installed modeller)

### P2.2: Chat'te Tool Execution Log Yok
- **Durum:** Tool çağrısı arka planda oluyor,görünmüyor
- **Etki:** Kullanıcı ne olduğunu bilmiyor
- **Öneri:** Tool call → result akışını chat'te göster

### P2.3: Memory 0 Recall
- **Durum:** ChromaDB var amahiç memory yok
- **Etki:** Memory özelliği çalışmıyor
- **Öneri:** Conversation memory'yi aktifleştir

### P2.4: Approvals Empty State
- **Durum:** Onay mekanizması var ama panel'de gösterilmiyor
- **Etki:** Tool onayları sadece Telegram'dan yapılabiliyor
- **Öneri:** Pending approval'ları panel'de listele + approve/reject butonları

### P2.5: Online/Offline Mode Seçimi Yok
- **Durum:** Sadece "LOCAL"badge'i var,değiştirilemez
- **Etki:** Kullanıcı mod seçemiyor
- **Öneri:** Auto/Offline/Online dropdown

### P2.6: Browser Analiz Sınırlı
- **Durum:** Navigate var ama analiz çok basit
- **Etki:** Gerçek web araştırma yapılamıyor
- **Öneri:** Read/search/extract functionality

---

## 🟠 ORTA ÖNCELİK (P3)

### P3.1: 6 Sayfa "Coming Soon" — Boş
- **Durum:** CV Library, Job Search, Education, Patents + Projects, Workflow
- **Etki:** Sidebar'da gereksiz yer kaplıyor
- **Öneri:** Gizle veya kaldır

### P3.2: Projects Hardcoded
- **Durum:** 3 sabit proje (UMAY AI, UMAY Patent, CREWINTEL)
- **Etki:** Gerçek proje yönetimi yok
- **Öneri:** Gerçek workspace/project management

### P3.3: Workflow Statik
- **Durum:** Pipeline görselihiçbir veri çekmiyor
- **Etki:** Gerçek execution akışı görünmüyor
- **Öneri:** Real-time pipeline visualization veya kaldır

### P3.4: Scheduler Kısmen Çalışıyor
- **Durum:** Sadece 1 test task ("noop")
- **Etki:** Gerçek cron job yönetimi yok
- **Öneri:** CRUD interface for scheduled tasks

### P3.5: Tools Detail Yok
- **Durum:** 62 tool listeleniyor ama detay yok
- **Etki:** Tool params, examples görünmüyor
- **Öneri:** Tool detail modal/card

### P3.6: Dashboard Kalabalık
- **Durum:** 4 card + telemetry + agents + pipeline + live log + quick actions + workspace
- **Etki:** İlk 5 saniyede hangisi önemli belli değil
- **Öneri:** 6 card'a düşür,temizle

---

## 🔵 DÜŞÜK ÖNCELİK (P4)

### P4.1: Chat Copy/Retry/Stop Yok
- **Durum:** Mesaj kopyalama,tekrar gönderme,durdurma yok
- **Etki:** UX eksikliği
- **Öneri:** Her assistant mesajına copy + retry butonu

### P4.2: Chat Conversation History
- **Durum:** Sadece mevcut session
- **Etki:** Eski konuşmalara erişim yok
- **Öneri:** Conversation listesi + geçiş

### P4.3: Dosya Silme/Okuma
- **Durum:** Sadece yükleme ve listeleme
- **Etki:** Dosya yönetimi eksik
- **Öneri:** Read/delete/download

### P4.4: Telegram Send Message
- **Durum:** Panel'den Telegram'a mesaj gönderme yok
- **Etki:** Tek yönlü iletişim
- **Öneri:** Panel'den Telegram'a mesaj gönderme

### P4.5: Log Arama/Filtreleme
- **Durum:** Sadece son 50 satır
- **Etki:** Büyük log'larda arama yok
- **Öneri:** Search + filter + level filter

---

## 🔴 ÇALIŞMAYAN BUTONLAR

| Buton | Sayfa | Durum | Neden |
|-------|-------|-------|-------|
| Workflow node tıklama | Workflow | ❌ | alert() ile bilgi gösteriyor |
| Projects "New Project" | Projects | ❌ | Coming soon |
| Tools detail | Tools | ❌ | Nothing happens |
| Approvals approve/reject | Approvals | ❌ | Boş sayfa |
| Memory search | Memory | ❌ | Arama yok |
| Settings save | Settings | ❌ | Salt okunur |
| Chat stop | Chat | ❌ | Buton yok |
| Chat retry | Chat | ❌ | Buton yok |
| Chat copy | Chat | ❌ | Buton yok |

---

## ÖZET

| Öncelik | Problem Sayısı |
|---------|----------------|
| 🔴 KRİTİK (P1) | 3 |
| 🟡 YÜKSEK (P2) | 6 |
| 🟠 ORTA (P3) | 6 |
| 🔵 DÜŞÜK (P4) | 5 |
| **Toplam** | **20** |

### Çalışmayan Buton: 9
### Mock/Placeholder: 6 sayfa
### Eksik Ama Gerekli: 8 özellik

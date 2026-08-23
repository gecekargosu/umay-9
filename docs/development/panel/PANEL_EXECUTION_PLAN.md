# UMAY 9 — PANEL REDESIGN EXECUTION PLAN

**Tarih:** 2026-08-23  
**Status:** PLAN — Uygulanacak

---

## AŞAMA 1: TEMİZLEME (1 gün)

### 1.1 Coming Soon Sayfalarını Gizle
- [ ] CV Library → sidebar'dan gizle
- [ ] Job Search → sidebar'dan gizle
- [ ] Education → sidebar'dan gizle
- [ ] Patents → sidebar'dan gizle

### 1.2 Statik Sayfaları Gizle
- [ ] Projects → sidebar'dan gizle
- [ ] Workflow → sidebar'dan gizle

### 1.3 Sidebar Yeniden Yapılandırma
- [ ] Nav gruplarını yeniden düzenle
- [ ] "Career" grubunu kaldır
- [ ] "Knowledge" grubunu kaldır
- [ ] Toplam 14 item'a düşür

### 1.4 Test
- [ ] Sidebar navigation doğru çalışıyor mu?
- [ ] Gizlenen sayfalara erişim var mı?
- [ ] Mevcut sayfalar hâlâ çalışıyor mu?

---

## AŞAMA 2: DASHBOARD İYİLEŞTİRME (1 gün)

### 2.1 Pipeline Kaldır
- [ ] Processing Pipeline bölümünü kaldır
- [ ] Yerine Models listesini koy (compact)

### 2.2 Card Düzeni
- [ ] 4 card → 8 card (2 sıra)
- [ ] İlk sıra: UMAY, Ollama, Telegram, Web
- [ ] İkinci sıra: CPU, RAM, Disk, Memory

### 2.3 Quick Actions Temizle
- [ ] 6 buton → 4 buton (Chat, Files, Tools, Diagnostics)

### 2.4 Test
- [ ] Dashboard her 15s refresh ediyor mu?
- [ ] Tüm card'lar doğru veri gösteriyor mu?
- [ ] Quick actions doğru sayfaya gidiyor mu?

---

## AŞAMA 3: CHAT İYİLEŞTİRME (2 gün)

### 3.1 Model Selector
- [ ] Chat header'a dropdown ekle
- [ ] auto + tüm installed modeller listele
- [ ] Seçimi API'ye gönder

### 3.2 Tool Execution Log
- [ ] Tool call gösterimi ekle
- [ ] Tool result gösterimi ekle
- [ ] Folding/collapsible yap

### 3.3 Copy/Retry/Stop
- [ ] Her assistant mesajına Copy butonu
- [ ] Her assistant mesajına Retry butonu
- [ ] Chat input'a Stop butonu

### 3.4 Conversation History
- [ ] Conversation listesi (sol panel veya dropdown)
- [ ] Eski konuşmalara geçiş
- [ ] Conversation silme

### 3.5 Test
- [ ] Model seçimi çalışıyor mu?
- [ ] Tool log görünüyor mu?
- [ ] Copy çalışıyor mu?
- [ ] Retry çalışıyor mu?
- [ | Stop çalışıyor mu?
- [ ] History yükleniyor mu?

---

## AŞAMA 4: SETTINGS (1 gün)

### 4.1 Düzenlenebilir Form
- [ ] Ollama URL input
- [ ] Primary Provider dropdown
- [ ] Default Model dropdown
- [ ] Online Mode dropdown (Auto/Offline/Online)

### 4.2 Channel Configuration
- [ ] Telegram: token göster + configure butonu
- [ ] Gmail: credentials göster + configure butonu

### 4.3 Save Mekanizması
- [ ] Save butonu
- [ ] API endpoint: POST /api/config (yeni)
- [ ] Validation

### 4.4 Test
- [ ] Ayarlar okunabiliyor mu?
- [ ] Ayarlar değiştirilebiliyor mu?
- [ ] Save çalışıyor mu?
- [ ] Değişiklikler uygulanıyor mu?

---

## AŞAMA 5: YENİ SAYFALAR (2 gün)

### 5.1 Models Sayfası
- [ ] Installed models tablosu
- [ ] Model tipi (chat/coding/vision/reasoning)
- [ ] Model boyutu
- [ ] Model durumu
- [ ] Pull butonu
- [ ] Intent → Model mapping

### 5.2 Approvals Aktifleştirme
- [ ] Pending approval'ları listele
- [ ] Approve butonu
- [ ] Reject butonu
- [ ] Detail view

### 5.3 Memory Geliştirme
- [ ] Memory arama
- [ ] Memory ekleme
- [ ] Memory silme
- [ ] Memory detayı

### 5.4 Test
- [ ] Models listesi doğru mu?
- [ ] Approvals çalışıyor mu?
- [ ] Memory CRUD çalışıyor mu?

---

## AŞAMA 6: TEKNİK İYİLEŞTİRME (2 gün)

### 6.1 API Optimization
- [ ] Dashboard API'lerini birleştir
- [ ] Lazy loading ekle
- [ ] Caching

### 6.2 Error Handling
- [ ] Tüm API çağrılarına error handling
- [ ] User-friendly hata mesajları
- [ ] Retry mekanizması

### 6.3 Performance
- [ ] Large list virtualization
- [ ] Debounced search
- [ ] Optimistic updates

### 6.4 Test
- [ ] Hatalarda doğru mesaj görünüyor mu?
- [ ] Performance iyi mi?
- [ ] Memory leak yok mu?

---

## TOPLAM SÜRE

| Aşama | Süre | Bağımlılık |
|-------|------|------------|
| Aşama 1: Temizleme | 1 gün | Yok |
| Aşama 2: Dashboard | 1 gün | Aşama 1 |
| Aşama 3: Chat | 2 gün | Aşama 1 |
| Aşama 4: Settings | 1 gün | Aşama 1 |
| Aşama 5: Yeni Sayfalar | 2 gün | Aşama 1 |
| Aşama 6: Teknik | 2 gün | Aşama 2-5 |
| **Toplam** | **9 gün** | |

---

## BAŞARI KRİTERLERİ

- [ ] Sidebar 14 item'dan fazla değil
- [ ] Hiçbir "Coming Soon" görünür değil
- [ ] Dashboard 8 card gösteriyor
- [ ] Chat'te model selector var
- [ ] Chat'te tool log görünüyor
- [ ] Chat'te copy/retry/stop var
- [ ] Settings düzenlenebilir
- [ ] Models sayfası çalışıyor
- [ ] Approvals aktif
- [ ] Tüm mevcut testler hâlâ PASS
- [ ] UX skoru ≥ 8/10

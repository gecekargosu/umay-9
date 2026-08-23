# UMAY 9 — PANEL REDESIGN PROPOSAL

**Tarih:** 2026-08-23  
**Status:** PROPOSAL — Henüz uygulanmadı

---

## 1. HEDEF

Paneli mevcut durumdan:
- **21 sidebar item → 12-14**
- **6 empty/coming soon sayfa → kaldır/gizle**
- **Tek dosya → modular yapı**
- **Read-only settings → düzenlenebilir**
- **Chat model selector → ekle**

---

## 2. ÖNERİLEN SİDEBAR

```
UMAY 9
│
├── HOME
│   ├── ◉ Dashboard
│   └── 💬 Chat
│
├── AI
│   ├── 🤖 Agents
│   ├── 🔧 Tools
│   └── 📊 Models (yeni)
│
├── WORKSPACE
│   ├── 📁 Files
│   ├── 🧠 Memory
│   └── 📋 Tasks
│
├── CHANNELS
│   ├── 📱 Telegram
│   └── 📧 Gmail
│
├── SYSTEM
│   ├── ✅ Approvals
│   ├── ⏰ Scheduler
│   ├── 📜 Logs
│   ├── 🩺 Diagnostics
│   └── ⚙️ Settings
│
└── [DEVELOPER]
    └── 🌐 Browser
```

**Kaldırılacaklar:**
- Workflow (statik)
- Projects (hardcoded)
- CV Library (boş)
- Job Search (boş)
- Education (boş)
- Patents (boş)
- System (fazla — CPU/RAM zaten Dashboard'da)

**Eklenenler:**
- Models (model yönetimi)
- Gmail (channels altında)

---

## 3. ÖNERİLEN DASHBOARD

```
┌────────────────────────────────────────────────────────┐
│  UMAY 9 — Command Center                              │
│  🟢 ONLINE | 🤖 11 Model | 📱 Telegram Connected      │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 🟢 UMAY  │ │ 🤖 Ollama│ │ 📱 TG    │ │ 🌐 Web   │ │
│  │ Online   │ │ 11 model │ │ Connected│ │ Online   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 📊 CPU   │ │ 💾 RAM   │ │ 💿 Disk  │ │ 🧠 Memory│ │
│  │ 12%      │ │ 45%      │ │ 3.8%     │ │ 0 items  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                        │
│  ┌────────────────────────────┐ ┌────────────────────┐│
│  │ Quick Actions              │ │ Live Activity      ││
│  │ 💬 Chat | 📁 Files | 🔧   │ │ [son log satırları]││
│  │    Tools | 🩺 Diagnostics  │ │                    ││
│  └────────────────────────────┘ └────────────────────┘│
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Değişiklikler:**
- 4 card → 8 card (2 sıra)
- Pipeline kaldırıldı (statik olduğu için)
- Quick Actions basitleştirildi
- Live Activity korundu

---

## 4. ÖNERİLEN CHAT EKRANI

```
┌────────────────────────────────────────────────────────┐
│  💬 UMAY Chat     [Model: auto ▼] [🧹 New] [📋 History]│
├────────────────────────────────────────────────────────┤
│                                                        │
│  👤 Merhaba, nasılsın?                                │
│                                                        │
│  🤖 İyi günler! UMAY, yardıma hazırım. [0.5s]        │
│     ┌──────────────────────────────────────┐          │
│     │ 🔧 Tool: get_current_date            │          │
│     │ 📤 Result: Pazar, 23 Ağustos 2026    │          │
│     └──────────────────────────────────────┘          │
│                                                        │
│  👤 Bugün günlerden ne?                               │
│                                                        │
│  🤖 Bugün Pazar, 23 Ağustos 2026. [0.3s]            │
│     [📋 Copy] [🔄 Retry]                              │
│                                                        │
├────────────────────────────────────────────────────────┤
│  📎 [input...] [Gönder] [⏹ Stop]                     │
└────────────────────────────────────────────────────────┘
```

**Yeni Özellikler:**
- **Model Selector:** auto/phi4-mini/qwen3/gemma3/etc.
- **Tool Execution Log:** Tool call + result görünür
- **Copy Button:** Her assistant mesajında
- **Retry Button:** Tekrar gönder
- **Stop Button:** Uzun süren istekleri durdur
- **Conversation History:** Eski konuşmalara geçiş

---

## 5. ÖNERİLEN SETTINGS

```
┌────────────────────────────────────────────────────────┐
│  ⚙️ Settings                                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ General                                        │   │
│  │ Ollama URL: [http://host.docker.internal:11434]│   │
│  │ Primary Provider: [OLLAMA ▼]                   │   │
│  │ Default Model: [auto ▼]                        │   │
│  │ Theme: [Dark ▼]                                │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ Channels                                      │   │
│  │ Telegram: [CONFIGURED ✅] [Configure]          │   │
│  │ Gmail: [NOT SET ❌] [Configure]                │   │
│  │ Gemini: [NOT SET ❌] [Configure]               │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ AI Behavior                                   │   │
│  │ Online Mode: [AUTO ▼]                         │   │
│  │ Intent Router: [ENABLED ✅]                    │   │
│  │ Tool Auto-approve: [DISABLED ❌]               │   │
│  │ Memory: [ENABLED ✅]                           │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  [Save Settings]                                      │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Yeni Özellikler:**
- Düzenlenebilir form alanları
- Channel configuration
- AI behavior settings
- Save butonu

---

## 6. ÖNERİLEN MODELS SAYFASI

```
┌────────────────────────────────────────────────────────┐
│  📊 Models                                            │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Installed Models (11)                                 │
│  ┌─────────────┬──────────┬────────┬───────────────┐  │
│  │ Model       │ Type     │ Size   │ Status        │  │
│  ├─────────────┼──────────┼────────┼───────────────┤  │
│  │ phi4-mini   │ chat     │ 2.4GB  │ ✅ Ready      │  │
│  │ qwen3:8b    │ reasoning│ 4.7GB  │ ✅ Ready      │  │
│  │ gemma3:4b   │ vision   │ 3.2GB  │ ✅ Ready      │  │
│  │ llava:7b    │ vision   │ 4.1GB  │ ✅ Ready      │  │
│  │ ...         │          │        │               │  │
│  └─────────────┴──────────┴────────┴───────────────┘  │
│                                                        │
│  [Pull New Model]                                      │
│                                                        │
│  Intent → Model Mapping                                │
│  ┌─────────────┬──────────────────────────────────┐   │
│  │ chat        │ phi4-mini:latest                  │   │
│  │ coding      │ qwen2.5-coder:7b                 │   │
│  │ vision      │ gemma3:4b                         │   │
│  │ reasoning   │ qwen3:8b                          │   │
│  │ document    │ granite3.3:8b                     │   │
│  └─────────────┴──────────────────────────────────┘   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 7. UYGULAMA SIRASI

### Aşama 1: Temizleme (1 gün)
1. Coming Soon sayfalarını gizle (CV, Job, Education, Patents)
2. Projects sayfasını gizle
3. Workflow sayfasını gizle
4. Sidebar'ı 14 item'a düşür

### Aşama 2: Dashboard İyileştirme (1 gün)
1. Pipeline'ı kaldır
2. 8 card'a genişlet
3. Quick Actions'ı sadeleştir

### Aşama 3: Chat İyileştirme (2 gün)
1. Model selector ekle
2. Tool execution log ekle
3. Copy/Retry butonları ekle
4. Stop butonu ekle
5. Conversation history ekle

### Aşama 4: Settings (1 gün)
1. Düzenlenebilir form ekle
2. Ollama URL değiştirme
3. Model tercihi
4. Channel configuration

### Aşama 5: Yeni Sayfalar (2 gün)
1. Models sayfası
2. Approvals aktifleştirme
3. Memory geliştirme

### Aşama 6: Teknik İyileştirme (2 gün)
1. Component-based yapıya geçiş (hazırlık)
2. API optimization
3. Error handling

**Toplam:** ~9 gün

---

## 8. BEKLENEN SONUÇ

| Metrik | Mevcut | Hedef |
|--------|--------|-------|
| Sidebar item | 21 | 14 |
| Çalışan sayfa | 12 | 15 (yeni Models) |
| Empty/placeholder | 6 | 0 |
| Chat özelliği | 5 | 10 |
| Settings | Read-only | Düzenlenebilir |
| UX skoru | 6/10 | 8/10 |

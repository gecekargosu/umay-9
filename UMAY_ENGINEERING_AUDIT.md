# UMAY Engineering Audit

Tarih: 2026-08-13

## Kapsam
UMAY projesindeki mevcut Python/JSON/Markdown kaynakları ve giriş noktaları incelendi. Binary Chroma verisi içerik satırı olarak denetlenmedi.

## Bulgular

### CRITICAL
- **Tool-calling zinciri kopuktu.** Engine yalnızca metin cevabı döndürüyor, Ollama `tool_calls` verisi modele geri taşınamıyordu.

### HIGH
- **Gerçek workspace agent yoktu.** `run_umay.py` normal chat ile sınırlıydı.
- **Dosya sistemi araçları yoktu.** UMAY proje klasörünü keşfedemiyordu.
- **Terminal/test/build araçları yoktu.** UMAY'ın kendi başına doğrulama yapması mümkün değildi.
- **Canlı model bilgisi RAG tarafından gölgelenebiliyordu.** Bu yüzden eski Gemma/Qwen/LLaVA listesinin tekrar edilmesi mümkün oluyordu.

### MEDIUM
- **Kalıcı geliştirme günlüğü standardı yoktu.** `logs/DEVELOPMENT_LOG.md` eklendi.
- **Workspace sınırı yoktu.** Yeni tool katmanında path traversal engeli eklendi.
- **Yıkıcı komutlar için güvenlik katmanı yoktu.** Yeni terminal tool'unda temel deny-list eklendi.

## Uygulanan çözüm
1. Ollama tool-calling destekli agent katmanı eklendi.
2. Dosya listeleme/okuma/arama/yazma araçları eklendi.
3. Workspace içi terminal çalıştırma eklendi.
4. Agent görevi `run_umay.py` üzerinden otomatik seçiliyor.
5. Değişiklikler ve agent eylemleri loglanıyor.
6. İlk syntax doğrulaması yapıldı.

## Sonraki doğrulama
Windows makinede:

```powershell
cd C:\Users\isitm\Desktop\UMAY
python run_umay.py
```

Ardından:

```text
C:\CREWINTEL projesini baştan sona incele. Önce klasör ağacını çıkar, sonra backend/frontend/test/docker/config dosyalarını oku. Hataları ve eksikleri önem derecesine göre listele. Henüz dosya değiştirme; sadece ayrıntılı audit raporu oluştur.
```

Düzeltme yetkisi verilecekse ayrıca:

```text
Audit bulgularındaki hataları düzelt. Her değişiklikten sonra uygun test/lint/build çalıştır. Sonuçları logs/DEVELOPMENT_LOG.md dosyasına ekle.
```

## 2026-08-13 — Tool-loop ikinci düzeltme

Önceki testte model `list_directory` JSON'u üretti ancak tool sonucu modele geri
dönmeden normal chat'e düşüldü. Ayrıca tool katmanının workspace kökü UMAY
klasörüne sabitlenmiş olması C:\CREWINTEL gibi harici projelerin taranmasını
engelleyebilirdi.

### Uygulanan düzeltmeler
- `core/engine.py`: tools verildiğinde native tool-call veya normal mesajı
  standart `{"message": ...}` zarfında döndürüyor.
- `core/agent.py`: gerçek çok turlu tool loop, tool sonucu geri besleme,
  JSON-in-content compatibility parser ve Windows hedef workspace algılama eklendi.
- `core/agent_tools.py`: aktif workspace dinamik hale getirildi; path traversal
  koruması korunuyor.
- `UMAY_AGENT_TODO.md`: yeni görev/başarı listesi eklendi.

### Hedeflenen test
`C:\CREWINTEL` audit isteğinde en azından şu akışın görünmesi gerekir:
`[TOOL] list_directory` → `[TOOL RESULT] ...` → yeni model turu →
`[TOOL] read_file/search_files/run_command` ...

## 2026-08-13 — Windows Path Parser Regression Fix

The previous workspace extraction consumed the natural-language request after
`C:\CREWINTEL`. This caused a false "workspace folder not found" error.

Fixed by restricting extraction to a path token and added regression coverage
for the exact user command format.

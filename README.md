# UMAY — Local AI Assistant

Bu sürüm, mevcut UMAY kodunun hata giderilmiş ve sadeleştirilmiş çalışma sürümüdür.

## Düzeltilen kritik sorunlar

- Ollama model isimleri sabit kabul edilmiyor; kurulu modeller `/api/tags` üzerinden bulunuyor.
- Ollama kapalıysa veya model yoksa 300 saniye sessizce beklemek yerine açık hata veriliyor.
- Router artık olmayan bir model adını doğrudan çağırmıyor.
- Chroma hafızasında `collection.get()` sonucunu yanlış yorumlayan hata düzeltildi. Önceki kod yeni hafızaları yanlışlıkla eklemeyebiliyordu.
- Uzun süreli hafıza için tek aktif `rag.memory_manager` kaynağı kullanılıyor; eski `backup/update` dosyaları uyumluluk wrapper'ı olarak bırakıldı.
- Eski `ollama run qwen3:8b` subprocess yolu yerine ortak Ollama HTTP engine kullanılıyor.
- Coding agent geçici dosyayı `finally` ile temizliyor ve timeout uygulanıyor.
- Browser agent Google aramasında sorguyu iki kez yazma problemi düzeltildi.
- Browser agent başlatılmamışsa otomatik başlatılıyor.
- Panelde hard-coded secret kaldırıldı; `UMAY_SECRET_KEY` kullanılabiliyor.
- Gemini artık API anahtarı yok diye modülü import ederken programı kapatmıyor; opsiyonel adapter olarak çalışıyor.
- `requirements.txt` ve `.env.example` eklendi.
- `run_umay.py` tek giriş noktası eklendi.

## Kurulum

PowerShell:

```powershell
cd C:\UMAY
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Chromium gerekiyorsa:

```powershell
python -m playwright install chromium
```

## Ollama

Önce Ollama'nın çalıştığını kontrol et:

```powershell
ollama list
```

UMAY, kurulu modeller arasından görev tipine göre uygun modeli otomatik seçer. Kod içinde tek bir modele mahkum değildir.

Başlatmak için:

```powershell
python run_umay.py
```

## Online / Browser yetenekleri

Agent tool katmanında salt-okuma `web_search`, `browser_open`, `browser_read` ve `browser_screenshot` bulunur. Tarayıcıda tıklama/yazma işlemleri açık onay ister. Playwright + Chromium kurulumu gereklidir.

Örnek ortam ayarları:

```powershell
$env:UMAY_BROWSER_HEADLESS="true"
$env:UMAY_APPROVED="true"   # yalnızca kullanıcı açıkça web/command değişikliği istediğinde
```

## Kontrol paneli

```powershell
python ui/panel_server.py
```

Sonra:

`http://localhost:5001`

## Hafıza

Hafızaya bilgi eklemek için:

```powershell
python rag/teach_umay.py
```

> ChromaDB ilk kullanımda embedding altyapısına ihtiyaç duyabilir. Bu nedenle `chromadb` kurulumu tamamlanmadan hafıza testi yapılmamalıdır.

## Önemli güvenlik notu

`agents/coding_agent.py` tarafından üretilen Python kodu subprocess içinde çalıştırılır ancak gerçek bir güvenlik sandbox'ı değildir. Güvenilmeyen kodu çalıştırmak için kullanılmamalıdır. Gerçek autonomous coding için Docker sandbox gibi izole bir çalışma katmanı tercih edilmelidir.

## Gizli bilgiler

`.env` arşive dahil edilmemiştir. İhtiyaç varsa:

```powershell
Copy-Item .env.example .env
```

ve kendi API anahtarını `.env` içine ekle.

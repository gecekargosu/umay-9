# CALCULATOR ROUTING FIX — RAPOR

## Tarih: 2026-08-23

## Problem

Kullanıcı "127'nin karesini hesapla" dediğinde calculator tool'a yönlendirilmiyordu.
Yanlışlıkla CHAT intent'ine gidip LLM'den uydurma cevap üretiyordu.

## Kök Neden

**2 katmanlı sorun:**

### 1. Intent Router — Eksik Keywords

Intent Router'daki calculator keyword listesinde Türkçe doğal dil matematik
ifadeleri eksikti:

- Eksik: `karesi, karesini, küpü, küpünü, hesapla, hesaplama`
- Eksik: `toplamı, farkı, çarpımı, bölümü`

### 2. Panel Server — Eksik Türkçe → Math Dönüşümü

`panel_server.py`'deki CALCULATOR handler'ı sadece `9*8`, `3+5` gibi doğrudan
matematik ifadelerini regex ile tanıyordu.

Türkçe doğal dil ifadelerini matematik expression'a dönüştüren bir converter yoktu.

Örnek: `"127'nin karesini hesapla"` → regex eşleşmiyor → fallback stripping →
geçersiz expression → LLM'e gidiyor.

### 3. False Positive — "hesapla" Negation

"Bu işi hesaplamanın değil" gibi ifadeler "hesapla" keyword'ü yüzünden
yanlışlıkla calculator'a yönlendiriliyordu.

## Yapılan Düzeltmeler

### Dosya 1: `core/intent_router.py`

- Calculator keywords genişletildi: `karesi, karesini, küpü, kupu, hesapla, hesaplama`
- Negation filter eklendi: `hesaplamanı değil`, `hesapla istemiyorum` gibi
  ifadeler calculator'a gitmemeli

### Dosya 2: `ui/panel_server.py`

- Türkçe → Math dönüştürücü eklendi:
  - `"X'in karesi"` → `X**2`
  - `"X'in küpü"` → `X**3`
  - `"X ile Y topla"` → `X+Y`
  - `"X'den Y çıkar"` → `X-Y`
  - `"X ile Y çarp"` → `X*Y`
  - `"X ü Y böl"` → `X/Y`
- Apostrophe handling: `127'nin` → digit + `'` + suffix doğru eşleşiyor
- `"e bol"` pattern: `100 u 4 e bol` doğru eşleşiyor

## Test Sonuçları

### Intent Classification (14/14 PASS)

| Input | Expected Intent | Got |
|-------|----------------|-----|
| 127'nin karesini hesapla | calculator | calculator ✅ |
| 5'in kupunu hesapla | calculator | calculator ✅ |
| 10 ile 20 topla | calculator | calculator ✅ |
| 50 den 17 cikar | calculator | calculator ✅ |
| 8 ile 7 carp | calculator | calculator ✅ |
| 100 u 4 e bol | calculator | calculator ✅ |
| 9*8+7 | calculator | calculator ✅ |
| 127 * 127 | calculator | calculator ✅ |
| Bugun nasilsin? | chat | chat ✅ |
| Bu isi hesaplamanin degil... | chat | chat ✅ |
| Merhaba | chat | chat ✅ |
| Saat kac? | time | time ✅ |
| Masaustunu listele | file | file ✅ |
| Bu PDFi incele | document | document ✅ |

### Turkish → Math Conversion (6/6 PASS)

| Input | Expression | Result |
|-------|-----------|--------|
| 127'nin karesini hesapla | 127**2 | 16129 ✅ |
| 5'in kupunu hesapla | 5**3 | 125 ✅ |
| 10 ile 20 topla | 10+20 | 30 ✅ |
| 50 den 17 cikar | 50-17 | 33 ✅ |
| 8 ile 7 carp | 8*7 | 56 ✅ |
| 100 u 4 e bol | 100/4 | 25 ✅ |

### E2E Chat API (4/4 PASS)

| Mesaj | Cevap | Latency |
|-------|-------|---------|
| 127'nin karesini hesapla | 127**2 = 16129 | ~0.5s ✅ |
| 5'in kupunu hesapla | 5**3 = 125 | ~0.5s ✅ |
| 10 ile 20 topla | 10+20 = 30 | ~0.5s ✅ |
| 9*8+7 kac | 9*8+7 = 79 | ~0.5s ✅ |

### Regression

```
564 passed, 1 skipped, 0 failed ✅
```

### Negation Test

| Input | Expected | Got |
|-------|----------|-----|
| Bu isi hesaplamanin degil... | chat (not calculator) | chat ✅ |

## Değişen Dosyalar

1. `core/intent_router.py` — Keywords genişletme + negation filter
2. `ui/panel_server.py` — Türkçe → Math dönüştürücü

## Kalan Sınırlamalar

1. `"91'in karesi"` gibi karesi ifadesi蟾ponsuz_works — test edildi ✅
2. `"100'ün yüzde 20'si"` yüzdesi pattern'i intent router'da var ama
   panel_server'da henüz transform yok (intent correctly classified,
   falls through to direct math regex → strips → numbers only)
3. Karmaşık ifadeler: `"127 ile 345'ün toplamının karesi"` — multi-step
   henüz desteklenmiyor (P3 — düşük öncelik)

## Checkpoint

UMAY-V2-CALCULATOR-FIX-001

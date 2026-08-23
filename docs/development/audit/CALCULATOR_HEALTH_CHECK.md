# CALCULATOR HEALTH CHECK
**Date:** 2026-08-23 15:20

---

## Direct/Internal Test

| Input | Result | Status |
|-------|--------|--------|
| `2 + 2` | 4 | ✅ PASS |
| `127 * 127` | 16129 | ✅ PASS |
| `9*8+7` | 79 | ✅ PASS |
| `3+5*2-1` | 12 | ✅ PASS |
| `127**2` | 16129 | ✅ PASS |
| `127^2` | Error (BitXor) | ❌ FAIL |

## Chat → Tool Test

| Input | Intent | Model | Tool | Result |
|-------|--------|-------|------|--------|
| `9*8+7 kac?` | calculator | direct | evaluate_expression | ✅ 79 |
| `3+5` | calculator | direct | evaluate_expression | ✅ 8 |
| `127 * 127` | calculator | direct | evaluate_expression | ✅ 16129 |
| `127 nin karesini hesapla` | **chat** | phi4-mini | **none** | ⚠️ LLM'den geldi |

## Tool Schema

```json
{
  "name": "evaluate_expression",
  "description": "Matematiksel ifadeyi hesaplar...",
  "parameters": {
    "type": "object",
    "properties": {
      "expression": {
        "type": "string",
        "description": "Hesaplanacak matematiksel ifade (ör: '9/1*2-3+4')"
      }
    },
    "required": ["expression"]
  }
}
```

## Argument Flow

```
User: "127 nin karesini hesapla"
    ↓
Intent Router: classify_intent("127 nin karesini hesapla")
    ↓
Result: Intent.CHAT (NOT CALCULATOR!)
    ↓
Reason: No math operators (+,-,*,/,=) AND no math keywords (toplam, carp, bol)
    ↓
"karesini hesapla" NOT in calculator keywords
    ↓
Model: phi4-mini (chat model, NOT calculator)
    ↓
Tool: None (no tool calling)
    ↓
LLM responds: "127'nin karesi 16129'dur" (from training data)
```

## BOZULMANIN TAM OLDUĞU NOKTA

**Step 1: Intent Router**
- `classify_intent("127 nin karesini hesapla")` → `Intent.CHAT`
- Neden: "karesini hesapla" calculator keyword'lerinde yok

**Step 2: Model Selection**
- Intent=CHAT → model=phi4-mini (chat model)
- Calculator'a gitmesi gerekirken chat model'e gitti

**Step 3: Tool Calling**
- Intent=CHAT → tools=None
- Calculator tool hiç çağrılmadı

**Step 4: LLM Response**
- phi4-mini "127*127=16129" cevabını training data'dan verdi
- Doğru sonuç ama calculator tool kullanılmadı

## ROOT CAUSE

**Intent Router'daki calculator keywords eksik.**

Mevcut keywords:
```
+, -, *, /, =
toplam, topla, carp, bol
kac eder, sonuc
```

Eksik keywords:
```
karesi, karesini, kare
kuşkat, küpü, küp
toplamı, farkı, çarpımı, bölümü
kaç eder, kaçtır
hesapla, hesapla
matematik, sayı, rakam
```

"127 nin karesini hesapla" hiçbir mevcut keyword ile eşleşmiyor:

| Keyword | "127 nin karesini hesapla" içinde var mı? |
|---------|-------------------------------------------|
| `+` | ❌ |
| `-` | ❌ |
| `*` | ❌ |
| `/` | ❌ |
| `=` | ❌ |
| `toplam` | ❌ |
| `topla` | ❌ |
| `carp` | ❌ |
| `bol` | ❌ |
| `kac eder` | ❌ |
| `sonuc` | ❌ |

**Sonuç:** Intent CHAT olarak sınıflandırıldı → Calculator tool hiç kullanılmadı.

## SEVERITY

**P1 — High**

Neden P0 değil:
- LLM doğru sonucu verdi (16129)
- Ama calculator tool kullanılmadı
- LLM uydurabilir (hallucination riski)
- Tool kullanılmazsa:right result, wrong method

## ÖNERİLEN FIX

### Option 1: Intent Router'a yeni keywords ekle
```python
(Intent.CALCULATOR, [
    # Mevcut...
    "karesi", "karesini", "kare",
    "kusluk", "kupu", "kup",
    "toplami", "farki", "carpimi", "bolu",
    "kaçtır", "kactir",
    "hesapla", "hesapla",
    "matematik",
])
```

### Option 2: Daha geniş pattern matching
- "X'in karesi" pattern'i
- "X çarpı Y" pattern'i
- "X bölü Y" pattern'i

### Option 3: LLM-based intent classification
- Keyword matching yerine LLM'e sor
- Ama bu yavaş olur

**Önerilen:** Option 1 (en hızlı, en güvenli)

---

## E2E DOĞRULAMA

| Test | Eski Durum | Beklenen | Fix Sonrası |
|------|-----------|----------|-------------|
| "127 nin karesini hesapla" | CHAT → LLM | CALCULATOR → tool | Evaluate |
| "9*8+7 kac?" | CALCULATOR → tool ✅ | Aynı | Korunur |
| "3+5" | CALCULATOR → tool ✅ | Aynı | Korunur |
| "2+2 kac?" | CALCULATOR → tool ✅ | Aynı | Korunur |

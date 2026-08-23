# PHASE 2.5 — Intent Router Fix + Calculator + panel_server Entegrasyonu

**Tarih:** 2026-08-23 03:00  
**Durum:** ✅ TAMAMLANDI  
**Checkpoint:** UMAY-MELEZ-PHASE-02.5-001

---

## 1. PROBLEM

### Kök Neden (Kritik)
`ui/panel_server.py` → `execute_chat_task()` fonksiyonu **intent router'ı hiç kullanmıyordu!**
Eski `model_sec()` ile çalışıyor ve tool seçimini sadece `gorev in ("coding", "agent")` ile yapıyordu.

Sonuç:
- "Bugün günlerden ne?" → `get_system_info()` çağrılıyordu (yanlış tool)
- TIME intent'i → tool hiç verilmiyordu
- Calculator tool'u yoktu
- Matematik için LLM kullanılıyordu (yavaş + hatalı)

### Ek Problemler
1. Intent Router'da CALCULATOR intent'i yoktu
2. Calculator tool'u yoktu
3. CHAT_IDENTITY prompt'u panel_server'da kullanılmıyordu

---

## 2. YAPILAN DEĞİŞİKLİKLER

### `core/intent_router.py`
- CALCULATOR intent'i eklendi (matematik ifadelerini algılar)
- TIME intent keywords genişletildi ("hangi tarihteyiz", "bugün ne" vb.)
- classify_intent() fonksiyonuna regex bazlı calculator kontrolü eklendi
- TOOL_MAP'e CALCULATOR eklendi
- MODEL_MAP, STEP_MAP'e CALCULATOR eklendi

### `core/agent_tools.py`
- `evaluate_expression()` fonksiyonu eklendi — AST tabanlı güvenli matematik evaluator
- `_eval_node()` helper — recursive AST evaluation
- Tool definition: `evaluate_expression` → TOOLS listesine eklendi
- DISPATCH'e `evaluate_expression`, `get_current_time`, `get_current_date` eklendi

### `ui/panel_server.py`
- `execute_chat_task()` fonksiyonuna Intent Router entegrasyonu
- `from core.intent_router import classify_intent, get_available_tools, Intent` eklendi
- Intent sınıflandırması → tool seçimine bağlandı
- `active_tools` değişkeni — intent'e göre filtrelenmiş tool listesi
- CHAT/KNOWLEDGE intent'leri için `CHAT_IDENTITY` prompt'u kullanıldı
- `umay_chat(messages, model=model, tools=active_tools if use_tools else None)` olarak güncellendi

---

## 3. TEST SONUÇLARI

### Intent Classification (Host)
```
Merhaba                    → chat, tools=None           ✅
Sen kimsin?                → chat, tools=None           ✅
Bugun gunlerden ne?        → time, tools=[time, date]   ✅
Bugun gunlerden ne hangi tarihteyiz? → time, tools=[time, date] ✅ (EN KRİTİK FIX)
Saat kac?                  → time, tools=[time, date]   ✅
9/1*2-3+4                  → calculator, tools=[eval]    ✅
12 + 5 = ?                 → calculator, tools=[eval]    ✅
Klasoru listele            → file, tools=[list,read...]  ✅
Bu resimde ne var?         → vision, tools=[analyze...]  ✅
```

### Calculator
```
9/1*2-3+4 = 19.0   ✅
12 + 5 = 17         ✅
100 / 4 = 25.0      ✅
2**10 = 1024         ✅
(3+4)*2 = 14         ✅
```

### Container (Docker)
```
8/8 intent classification PASS ✅
2/2 calculator PASS ✅
```

### Full Regression
```
564 passed, 1 skipped, 0 failed ✅
```

---

## 4. DEĞİŞEN DOSYALAR

```
M  core/intent_router.py      — CALCULATOR intent, TIME keywords, regex check
M  core/agent_tools.py        — evaluate_expression(), DISPATCH updates
M  ui/panel_server.py         — Intent Router integration in execute_chat_task
```

---

## 5. CHECKPOINT

```
CHECKPOINT: UMAY-MELEZ-PHASE-02.5-001
DATE: 2026-08-23 03:00
STATUS: PASS
TESTS: 564 PASS, 0 FAIL
DOCKER: healthy
CONTAINER: 10/10 PASS
```

---

## 6. KALAN PROBLEMLER

| Problem | Öncelik | Durum |
|---------|---------|-------|
| "Python kodu yaz" → chat instead of code | DÜŞÜK | Edge case |
| "BMW mi Mercedes mi?" → chat instead of knowledge | DÜŞÜK | Edge case |
| Gmail tool integration (parametre eksikliği) | YÜKSEK | FAZ 3 |
| Telegram dosya gönderme | YÜKSEK | FAZ 3 |
| Offline/Online hybrid | YÜKSEK | FAZ 4 |
| Memory/context pipeline | ORTA | FAZ 5 |
| Response quality optimization | ORTA | FAZ 5 |

---

## 7. SONRAKI FAZ

FAZ 3: Tool Routing + Gmail/Email Integration + Telegram File Send

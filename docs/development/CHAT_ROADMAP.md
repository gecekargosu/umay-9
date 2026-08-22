# CHAT_ROADMAP — FAZ listesinden STEP sırasına

Bu dosya, kullanıcının gönderdiği "UMAY CHAT — GELİŞTİRME SIRASI (FAZ 1-10)"
listesini STEP'lere böler ve sırayı gerekçelendirir. Liste kendisi zaten
FAZ 1 → FAZ 10 önceliğini doğru veriyor (en zor/kritik önce); bu dosya onu
somut, tek-oturumda-bitebilecek STEP'lere ayırır ve FAZ içi sırayı belirler.

Kural: her STEP tek başına test edilebilir ve geri alınabilir olmalı. Bir
FAZ maddesi birden fazla STEP'e bölünebilir; bir STEP birden fazla FAZ
maddesini kapsayabilir (ör. "Conversation State Machine" + "Chat → Task
State entegrasyonu" tek STEP'te birleşti, çünkü bu repoda ikisi aynı
mekanizma).

---

## FAZ 1 — ÇEKİRDEK ALTYAPI

| STEP | Kapsar (FAZ 1 maddeleri) | Durum |
|---|---|---|
| STEP-01 | (ön koşul, FAZ 1'de yok ama hepsinin temeli) Persistent conversation storage | ✅ TAMAMLANDI |
| STEP-02 | Conversation State Machine + Chat → Task State entegrasyonu | ✅ TAMAMLANDI |
| STEP-03 | Task Manager entegrasyonu (chat mesajından görev oluşturma, task_id ↔ conversation ilişkisi — STEP-02 ile kısmen örtüşüyor, kalanı: birden fazla görev/konuşma başına görev listesi) | Sırada |
| STEP-04 | Live Task Progress (✓/⟳/○/❌ — SocketIO `task_status` zaten var, agentic turn'e `task_id` eklendi STEP-02'de; kalan: çok adımlı ilerleme, tek adımlı değil) | Sırada |
| STEP-05 | Pause / Resume (gerçek orta-görev durdurma — şu an chat_api() senkron, tek istekte baştan sona çalışıyor; bunun için görevin arka planda/streaming çalışması gerekir — **mimari olarak en zor madde**, kendi başına büyük STEP) | Sırada, büyük |
| STEP-06 | Checkpoint sistemi (task_state.py'nin `checkpoint()` fonksiyonu zaten var — chat_api()'ye bağlanmadı; STEP-05 ile birlikte yapılması daha mantıklı, çünkü checkpoint'in amacı yarım kalan görevi kurtarmak) | STEP-05 ile birlikte |
| STEP-07 | Crash / Restart Recovery (task_state.pending_tasks() zaten var; UI'da/chat_api()'de "kaldığı yerden devam" akışı yok) | STEP-05/06 sonrası |
| STEP-08 | Token / Context Budget Manager (Faz 0 denetiminde R17 — P0 olarak işaretlenmişti; gerçek kullanım varsa provider'dan al, yoksa ESTIMATE etiketle) | Bağımsız, istenirse STEP-03/04'ten önce de yapılabilir |
| STEP-09 | Context Manager (recent + summary + relevant + project + memory ayrımı — şu an sadece "recent" var) | Büyük, memory/RAG entegrasyonu gerektirir → FAZ 5 ile kesişir |

**Not:** FAZ 1'in "Task Planner entegrasyonu" maddesi kasıtlı olarak
STEP-03/04'ün *sonuna* alındı, çünkü `core/planner.py` (988 satır) Faz 0
denetiminde "CODE ONLY / doğrulanmamış" olarak işaretlenmişti — chat_api()
canlı olarak hiç çağırmıyor. Önce basit task_state döngüsünü sağlamlaştırıp
sonra planner'ı devreye almak, planner'daki olası bugları küçük/izole bir
yüzeyde test etmeyi sağlar (Rule 0: mevcut sistemi anla, sonra bağla).

## FAZ 2 — ORCHESTRATION
STEP-10: Chat → Orchestrator/Planner entegrasyonu, Tool/Agent/Model Router
sağlamlaştırma, Result Store, Result Synthesis, Error Recovery genişletme,
Permission/Approval entegrasyonu (approval_manager.py zaten var, bağlı
değil). FAZ 1 çekirdeği (state+checkpoint+budget) olmadan Orchestrator
entegrasyonu riskli — bu yüzden FAZ 1 tamamlanmadan başlanmaz.

## FAZ 3 — DOSYA / MULTIMODAL
STEP-11: **Mixed Attachment Bug düzeltmesi** (CHAT_ISSUES.md #1 — küçük,
izole, kendi başına bir STEP olabilir, FAZ 1'in ortasında bile araya
sıkıştırılabilir çünkü bağımsız). Sonra Attachment Manager kalıcı
ilişkileri (attachment ↔ message ↔ conversation — STEP-01'in şemasına
attachments tablosu eklenmesi gerekecek), Document/Vision/Code Reader
entegrasyonu, Multimodal Router.

## FAZ 4 — HISTORY & PROJECT
STEP-01 zaten temeli attı (persistent storage + `list_conversations()`
hazır ama route yok). Bu FAZ'da: History UI/route, search (archive.py'nin
zaten var olan `search_by_topic/date/keywords` fonksiyonlarını conversation
store'a bağlamak), auto-title, Project tablosu + conversation→project
ilişkisi, export/backup (R41, Faz 0'da P0 işaretliydi).

## FAZ 5 — MEMORY & ÖĞRENME
memory_bridge.py zaten var, chat_api()'ye bağlı değil (Faz 0 bulgusu).
Knowledge/Skill/Lesson/Decision/Feedback — hepsi yeni tablo/dosya
gerektirir, FAZ 1-4 oturduktan sonra.

## FAZ 6 — QUALITY
Evaluator/Verification/Observability/Confidence/Evaluation dataset — kod
değişikliği yapan görevler (coding/agent) FAZ 1-2'den sonra zaten
task_state ile izlenebilir hale geldiği için bu FAZ'ın gözlemlenebilirlik
kısmı ucuzlaşacak.

## FAZ 7-10
Kullanıcının kendi sıralaması korunuyor — UX, Ses, Computer Agent,
Sistemsel son dokunuşlar. Bunlar FAZ 1-6 olmadan test edilemez/anlamsız
(ör. Live Activity paneli göstereceği gerçek task ilerlemesi olmadan
dekorasyondan ibaret kalır).

---

## Sıradaki STEP

**STEP-03 (önerilen): Task Manager entegrasyonunun geri kalanı** — bir
conversation'ın birden fazla task_id'sini listeleyebilme
(`task_state.list_tasks()` zaten var, filtrelemesi yok) + basit bir görev
listesi görünümü. Küçük ve izole.

**Alternatif: STEP-05 (Pause/Resume)** doğrudan istenirse — ama bu,
listenin kendi de belirttiği gibi en zor/en büyük madde; kendi başına en
az 2-3 STEP'e bölünmesi gerekecek (mimari: chat_api()'nin senkron
istek-cevap modelinden, arka planda çalışan + kullanıcı araya girebilen bir
modele geçiş). Token bütçesi izin verdiği sürece STEP-03/04 gibi küçük
STEP'lerle ilerlemek, büyük mimari değişikliğe (Pause/Resume) daha güvenli
bir temelle girmeyi sağlar.

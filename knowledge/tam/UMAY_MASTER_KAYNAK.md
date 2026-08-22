# UMAY AI OS — Kapsamlı Proje Kaynak Dosyası (Master Reference)

> Bu doküman, UMAY AI OS projesinin **tam mimari, mühendislik ve vizyon kaynağıdır**. Bu dosyayı okuyan bir kişi ya da yapay zekâ ajanı (Antigravity vb.), UMAY AI OS'un ne olduğunu, neden var olduğunu, nasıl çalıştığını, hangi bileşenlerden oluştuğunu ve hangi sınırlar içinde geliştirileceğini eksiksiz anlamalıdır.
>
> Kaynaklar: UMAY AI OS Architecture Specification v1.0 (metin), UMAY AI OS v4.1 Mimari Şemaları (İşleyiş Şeması + Mimari Ağacı Tam Hâl), ve projenin önceki 00-10 arası detaylandırılmış dokümanları.
>
> **Not:** Ana ağaç kullanıcı tarafından 00_PROJECT_CORE → 19_RELEASES olarak belirlenmiştir ve buna sadıktır. Şemalarda (v4.1) yer alıp bu 19'lu ağaçta doğrudan bir eve sahip olmayan iki büyük katman vardı: **L0 – Donanım & Dünya Modeli** ve **L8 – Arayüz & Deneyim**. Bunları kaybetmemek için ağacın sonuna **20_HARDWARE_WORLD_MODEL** ve **21_INTERFACE_LAYER** olarak ekledim; bu iki klasör dışındaki her şey orijinal 19'lu yapının birebir aynısıdır. Bu ekleme dosyanın en altında ayrıca not edilmiştir.

---

## ANA AĞAÇ

```
UMAY/
│
├── 00_PROJECT_CORE/
├── 01_VISION/
├── 02_ARCHITECTURE/
├── 03_KERNEL/                    (L1)
├── 04_INFRASTRUCTURE/            (L2)
├── 05_TOOL_PLATFORM/             (L3)
├── 06_AGENT_MESH/                (L4)
├── 07_COGNITIVE_SYSTEM/          (L5)
├── 08_MEMORY_BRAIN/              (L6)
├── 09_EVOLUTION_CORE/            (L7)
├── 10_SECURITY/
├── 11_OBSERVABILITY/
├── 12_ENGINEERING/
├── 13_ROADMAP/
├── 14_DIAGRAMS/
├── 15_PATENTS/
├── 16_RESEARCH/
├── 17_MEETING_NOTES/
├── 18_ARCHIVE/
├── 19_RELEASES/
├── 20_HARDWARE_WORLD_MODEL/      (L0 — EKLENDİ, bkz. dosya sonu not)
└── 21_INTERFACE_LAYER/           (L8 — EKLENDİ, bkz. dosya sonu not)
```

Katman haritası (şemalardan): **L0 Donanım → L1 Kernel → L2 Altyapı → L3 Araç Platformu → L4 Ajan Mesh → L5 Bilişsel Sistem → L6 Hafıza Beyni → L7 Evrim Çekirdeği → L8 Arayüz.** Normal görevler bu sırayla akar (Slow Path); acil durumlar L0/Sensörler'den doğrudan L1 Interrupt Bus üzerinden Risk Engine'e sıçrar (Fast Path/Bypass).

---

## 00_PROJECT_CORE

### Amaç
Bu klasör UMAY AI OS'un **değişmeyen kimliğini** tutar: ne olduğu, neden var olduğu, hangi kurallara tabi olduğu. Diğer tüm dokümanlar buraya referans verir.

### 00.01 UMAY Manifesto
UMAY AI OS; donanım seviyesinden kullanıcı arayüzüne kadar uzanan, **otonom, modüler ve olay güdümlü (event-driven) bir Yapay Zekâ İşletim Sistemidir**. Klasik tek-modelli sohbet botlarının ve basit RAG sistemlerinin ötesine geçmeyi hedefler. Manifestonun özü: UMAY bir "chatbot" değil, yapay zekâ modellerini, hafızayı ve araçları birer **sistem kaynağı** olarak yöneten bir işletim sistemi çekirdeğidir.

### 00.02 Project Charter
- **Çözülen problem:** Günümüz AI uygulamaları monolitik, dış dünyaya kapalı, zayıf hafızalı ve çoklu alt görevleri koordine etmekte yetersiz.
- **Çözüm:** Karmaşık kullanıcı niyetlerini anlayan, bunları yönlü döngüsüz grafik (DAG) halinde planlayan, uzman ajanları görevlendiren, dış araçları güvenli kullanan bir altyapı.

### 00.03 Project Goals
- Otonom AI İşletim Sistemi oluşturmak
- Çok ajanlı (multi-agent) yapı kurmak
- Güçlü, çok katmanlı hafıza sistemi
- Zero Trust güvenlik
- Edge cihazlarda çalışabilme, IoT entegrasyonu
- Tamamen modüler, olay güdümlü mimari
- Sürekli kendi kendini geliştirebilen (Self-Evolving) sistem

### 00.04 Project Scope
- **Kapsamda:** Yerel çalışan (Ollama/vLLM tabanlı) çok ajanlı asistan; kod yazma, web'de gezinme, dosya/doküman anlama, sesli komut, uzaktan erişim, otomatik günlük görev yürütme.
- **Kapsam dışı / gelecek sürüm:** Swarm Intelligence (çoklu UMAY node ağı), fiziksel robotik aktüasyon, kuantum hesaplama entegrasyonu — bunlar mevcut mimariyi bozmadan üzerine inşa edilecek genişlemeler olarak MVP kapsamı dışında tutulur.

### 00.05 Project Principles
Single Responsibility, Loose Coupling & High Cohesion, Modularity & Extensibility, Fault Isolation, Stateless Services (durum yalnızca L6 Memory Brain + Redis/PostgreSQL'de tutulur), Security by Design & Zero Trust, Human-in-the-Loop, Dependency Inversion, Backward/Forward Compatibility.

### 00.06 Project Rules (Değiştirilemez Kurallar)
- Hiçbir bileşen varsayılan olarak güvenilir sayılmaz.
- Kernel iş mantığı taşımaz; sadece koordine eder.
- Evrim Çekirdeği (L7), Kernel/Permission Gate/Policy Engine kurallarına asla dokunamaz.
- Kritik silme/deploy/karar işlemleri mutlaka HITL onayından geçer.
- İzin kontrolü baypas edilemez; tek istisna donanım acil kesmeleridir (Interrupt Bus → doğrudan Risk Engine).

### 00.07 Project Glossary / 00.08 Terminology
Bu bölümler; **Agent, Kernel, IPC, DAG, Capability, Zero Trust, Sandbox, Shadow Mode, Fast Path/Slow Path, Digital Twin, Forgetting Curve** gibi dokümanlar boyunca geçen terimlerin sözlüğüdür. Her yeni bileşen eklendiğinde burası güncellenir.

### 00.09 Version Policy
Mimari sürümleri (v1.0, v4.1, ...) semantik olarak izlenir: küçük değişiklikler alt sürüm, katman ekleme/çıkarma gibi büyük kararlar ana sürüm artışı gerektirir. **Not:** Bu dosyanın hazırlandığı an itibarıyla metin spesifikasyonu v1.0 idi, şemalar v4.1'e ulaşmıştı; bu kaynak dosya iki tarafı senkronlamak için hazırlandı (bkz. dosya sonu "Şema-Metin Senkron Notları").

### 00.10 Project History
Proje; önce genel bir "yerel, hafızalı, kod yazabilen, tarayıcı kullanabilen" asistan fikri olarak başladı, ardından mimari L0-L8 katmanlı bir microkernel AI OS'a evrildi (v4.1). Süreç boyunca dokümantasyon da sadeleşti: ilk aşamada her alt konu için ayrı şablon dosyalar içeren dev bir 00-19 ağacı üretildi; bu dosya, o ağacın gerçek mimari içerikle doldurulmuş, tek-dosyalık halidir.

---

## 01_VISION

### Amaç
Teknik detaydan arındırılmış, UMAY'ın **neden var olduğunu ve gelecekte ne olmak istediğini** anlatır.

### 01.01-01.03 Purpose / Vision / Mission
- **Purpose:** Sadece yanıt üreten değil; donanım kesmelerini dinleyen, kendi performansını değerlendirip optimize edebilen, uzun vadeli kalıcı hafızaya sahip, Zero Trust prensibiyle çalışan bir işletim sistemi çekirdeği sunmak.
- **Mission (bugün):** Yerelde (kullanıcının kendi donanımında) çalışan, kod yazabilen, araştırma yapabilen, dosya/tarayıcı/ses ile etkileşebilen, hafızası kalıcı olan bir çok-ajanlı asistan inşa etmek.
- **Uzun vadeli vizyon:** UMAY AI OS'u akıllı afet yönetim ağlarından (UMAY Ağı), giyilebilir teknolojilere, kurumsal otonom karar destek sistemlerinden robotik kenar (edge) cihazlara kadar her platformda koşabilen evrensel bir bilişsel altyapı hâline getirmek.

### 01.04-01.05 Design & Engineering Philosophy
- **Neden Katmanlı Mimari?** Sorumlulukların kesin hatlarla ayrılması (Separation of Concerns) — donanım yönetimi ile bilişsel çıkarım birbirine karışmaz.
- **Neden Microkernel?** Çökmeleri izole etmek, çekirdeği minimumda tutmak. Kernel yalnızca izin/zamanlama/iletişim yönetir.
- **Neden Event-Driven?** Uzun süren AI işlemleri için klasik istek-yanıt döngüsü uygun değildir; bileşenler asenkron olaylarla haberleşir, sistem bloke olmaz.
- **Neden Agentic AI?** Tek modele her işi yaptırmak yerine dar-uzmanlıklı ajanların iş birliği, daha az halüsinasyon ve daha yüksek doğruluk sağlar.
- **Neden AI OS yaklaşımı?** Modelleri, hafızayı, araçları klasik bir OS'un kaynakları gibi orkestre etmek.

### 01.06-01.07 Core & System Principles
Bkz. 00.05 Project Principles — bu bölüm aynı ilkelerin vizyon diliyle, teknik olmayan anlatımıdır (yatırımcı/tanıtım metinlerinde kullanılacak versiyon).

### 01.08-01.09 Functional / Non-Functional Goals
- **Fonksiyonel:** Kod üretme, web araştırma, dosya/görsel anlama, sesli komut, çoklu ajan iş birliği, kalıcı hafıza, kendi kendini iyileştirme.
- **Fonksiyonel olmayan:** Düşük gecikme (Fast Path), yüksek kararlılık (fault isolation), ölçeklenebilirlik, %85+ test kapsamı, geriye/ileriye uyumluluk.

### 01.10 Future Vision
Swarm Intelligence (UMAY node'larının birbirine bağlanıp dağıtık ajan ağı kurması), fiziksel robotik entegrasyonu (drone/robot kol kontrolü, Digital Twin optimizasyonuyla), kuantum hazırlığı (L5 Reasoner için "Quantum Proxy" eklentileri) — mevcut mimariyi bozmadan üzerine inşa edilecek alanlar.

---

## 02_ARCHITECTURE

### Amaç
Katmanlar arası ilişkiyi, veri/kontrol akışını ve genişletilebilirlik modelini tanımlar. Bu klasör "büyük resmin" teknik özetidir.

### 02.01-02.02 Architecture Overview & Layered Architecture
UMAY AI OS **9 mantıksal katmandan (L0-L8)** oluşur, alt seviye fiziksel gerçekliklerden üst seviye soyut bilişsel/kullanıcı etkileşimine doğru sıralanır:

| Katman | Ad | Bu ağaçtaki karşılığı |
|---|---|---|
| L0 | Donanım & Dünya Modeli | 20_HARDWARE_WORLD_MODEL (ek) |
| L1 | UMAY Kernel (Microkernel) | 03_KERNEL |
| L2 | Altyapı & Servisler | 04_INFRASTRUCTURE |
| L3 | Yetenek & Araç Platformu | 05_TOOL_PLATFORM |
| L4 | Ajan Mesh & Yetenekler | 06_AGENT_MESH |
| L5 | Bilişsel Sistem | 07_COGNITIVE_SYSTEM |
| L6 | Hafıza Beyni | 08_MEMORY_BRAIN |
| L7 | Evrim Çekirdeği | 09_EVOLUTION_CORE |
| L8 | Arayüz & Deneyim | 21_INTERFACE_LAYER (ek) |

Bu katmanları **yatay olarak kesen** iki yapı vardır: **Güvenlik Kumaşı (Security Fabric — 10_SECURITY)** ve **Gözlemlenebilirlik (Observability — 11_OBSERVABILITY)**. Hiçbir katman bunların dışında bırakılmaz.

### 02.03-02.05 System Components / Relationships / Module Dependencies
Bağımlılık kuralı: üst katmanlar alt katmanların **somut implementasyonuna değil soyut arayüzlerine** bağlıdır (Dependency Inversion). Hiçbir servis doğrudan bir diğerine bağlanmaz — L4'teki bir ajan L2'deki veritabanına asla doğrudan erişemez; istek her zaman IPC üzerinden L1 Permission Gate'e gelir, oradan yetkilendirilir.

### 02.06-02.08 Data Flow / Control Flow / Request Lifecycle
**Slow Path (normal görev akışı):**
```
L8 İstek → L1 Kernel (doğrulama) → L5 Intent Engine (anlama)
→ L5 Planner (DAG'a bölme) → L4 Agent Mesh (görev dağıtımı)
→ L3 Tool Platform (çalıştırma) → L6 Memory (kaydetme) → L8 (yanıt)
```
**Fast Path (refleks yolu):** Basit komutlar veya L0 acil donanım kesmeleri, L5'in bilişsel parçalamasını atlayarak doğrudan ilgili Ajan/Araca (L4/L3) ya da motor kontrolüne gider. Düşük gecikme hedeflenir.

**İstek Yaşam Döngüsü (8 adım):** Oluşturulma (L8) → İşlenme/Admit (L1 kimlik doğrulama + Event Bus'a atma) → Parçalanma (L5 Planner → DAG) → Dağıtılma (L4 Agent Manager) → Araç Kullanımı (L3) → Sonuç Üretimi/Synthesis (L5 Reasoner) → Kaydedilme (L6 Working→Episodic Memory) → Öğrenmeye Aktarılma (L7).

**Öğrenme Döngüsü (arka planda asenkron):** L6 Stream Memory → L7 Analyzer → L6 Semantic Memory güncellemesi.

### 02.09 Event-Driven Model
"Her Şey Bir Olaydır": kullanıcı mesajı, donanım sensör verisi, bir ajanın görev tamamlaması — hepsi standartlaştırılmış bir Event olarak sisteme düşer ve **System Event Bus** üzerinden akar. Acil durumlar için ayrı bir **Hardware Interrupt Bus (Bypass)** vardır; bu, normal event akışını atlayıp doğrudan Risk Engine'e gider (öncelikli, anında müdahale).

### 02.10 Extensibility Model
- **Yeni Ajan:** L4'ün standart arayüzlerini implemente eder, Agent Registry'ye kaydolur.
- **Yeni Araç:** L3 MCP Gateway / Plugin Marketplace üzerinden tanımlanır, izinleri Kernel'e bildirilir.
- **Yeni Model:** L2 Model Runtime'a eklenir, L5 Model Router yapılandırmasına rotası girilir.
Çekirdek kod hiçbir yeni ekleme için değiştirilmez — bu, sistemin "Tak-Çalıştır" (Plug & Play) felsefesinin temelidir.

---

## 03_KERNEL (L1 — UMAY Kernel / Microkernel)

### Amaç
Kernel sistemin **çekirdeğidir ama beyni değildir**. Karar vermez, düşünmez, plan oluşturmaz, hafıza yönetmez, kod yazmaz, internete bağlanmaz. Görevi: sistemin güvenli, tutarlı ve kesintisiz çalışmasını sağlamak. Tüm modüller yalnızca Kernel üzerinden haberleşir.

**Neden Microkernel:** Modülerlik (servisler bağımsız, çekirdek büyümez), kararlılık (bir Agent çökerse Kernel çalışmaya devam eder), güvenlik (saldırı yüzeyi minimum), bakım kolaylığı (Agent/Model/DB değişirken Kernel sabit kalır).

### 03.01 UMAY Kernel — Genel
Kernel'in sorumlulukları: süreç yönetimi, mesajlaşma (IPC), yetkilendirme, görev zamanlama, kaynak yönetimi (CPU/RAM/GPU/Disk/Network/Model Runtime), durum yönetimi, güvenlik kapısı olma. Kernel'in **yapmadığı** şeyler: veritabanı işlemleri, kod üretimi, LLM cevabı, hafıza analizi, web taraması, karar verme — bunlar üst katmanlara aittir.

### 03.02 IPC Bus
Tüm bileşenlerin Kernel üzerinden güvenli haberleşmesini sağlayan ana damar. Mesajları alır, doğrular, ilgili modüle yönlendirir. Hiçbir servis birbirine doğrudan bağlanmaz.

### 03.03 Scheduler
Görev önceliklendirme ve zamanlama (resource-aware, preemptive). Kaynaklar kısıtlıysa arka plan işlerini bekletir; L5 Model Router ile birlikte çalışarak zorluk derecesine göre iş dağıtımını optimize eder.

### 03.04 Permission Gate
Zero Trust politikasının merkezi. Her istekte kimlik doğrulama (AuthN) ve yetkilendirme (AuthZ) burada yapılır; Capability-based kontrol uygular (bkz. 10_SECURITY).

### 03.05 Interrupt Bus
Acil durumlarda (yangın sensörü, batarya bitmesi, acil stop) standart akışı (L5 Planner) **bypass** ederek doğrudan L5 Risk & Priority Analyzer'a giden donanım kesme yolu. Öncelikli ve anında müdahale eder.

### 03.06 Watchdog
Ajanların/modüllerin sağlık durumunu (Heartbeat) dinler. Yanıt vermeyen bileşeni izole eder, gerekirse Sandbox içinde yeniden başlatır (Auto Restart, Timeout Detection, State Restore).

### 03.07 State Snapshot / 03.08 Graceful Teardown
Sistem kapanırken veya çökerken mevcut bellek durumunun fotoğrafı (Snapshot) alınır. Graceful Teardown ile işlemler yarım bırakılmadan güvenli şekilde kapatılır; çökme sonrası bu snapshot ile güvenli yeniden ayağa kalkış sağlanır.

### 03.09 Boot Sequence (UMAY-INIT)
1) Donanım/Sistem Kontrolü → 2) Altyapı (L2) Başlatma → 3) Kernel İzin Yükleme → 4) Hafıza (L6) Bağlantısı → 5) IPC Bus Başlatma → 6) Scheduler Başlatma → 7) Ajanları Uyandırma (L4) → 8) Sistem Hazır, kullanıcı isteklerini kabule başlar.

### 03.10 Kernel APIs
Diğer katmanların Kernel ile etkileşime girdiği standart, sürümlenmiş arayüzler (IPC mesaj şemaları, Permission Gate sorgu formatı). Bu API'ler geriye dönük uyumluluk kuralına tabidir (bkz. 00.09).

**Kernel felsefesi:** Minimal çekirdek, maksimum güvenlik, en düşük gecikme, yüksek kararlılık, olay güdümlü iletişim, hata izolasyonu. Çekirdek ne kadar küçük olursa sistem o kadar güvenli ve sürdürülebilir olur.

---

## 04_INFRASTRUCTURE (L2 — Altyapı & Servisler)

### Amaç
Veri depolama ve model çalışma zamanlarını barındıran arka plan katmanı. Tüm üst katmanların üzerine oturduğu temel servisler burada yaşar.

### 04.01 Infrastructure — Genel
L2, "Stateful" olan tek katmandır — üst katmanlardaki servisler Stateless çalışır, durum burada (ve L6'da) tutulur.

### 04.02 PostgreSQL
İlişkisel metadata deposu (kullanıcı bilgisi, görev kayıtları, yapılandırma).

### 04.03 Vector Database
ChromaDB / Qdrant — Semantic Memory'nin (L6) vektörel uzayda barındığı yer; embedding tabanlı arama.

### 04.04 Redis
Redis Stack — önbellekleme (Semantic Cache) ve hızlı Stream Memory (L6) desteği.

### 04.05 MinIO
Dosya/obje depolama (yüklenen dokümanlar, üretilen dosyalar, görseller).

### 04.06 Model Runtime
Ollama / vLLM — modelleri doğrudan çalıştıran, GPU Load Balancer'ı barındıran motor. GGUF/ONNX runtime desteği ve model yaşam döngüsü yönetimi burada olur.

### 04.07 Event Bus / 04.08 Message Bus
NATS tabanlı — hem sistem geneli olay akışı (System Event Bus) hem ajanlar arası yüksek hızlı iç iletişim (Agent Message Bus, L4) burada temellenir. Event Store, tüm olayların kalıcı kaydını tutar.

### 04.09 Storage Architecture
Hangi verinin nerede tutulacağının haritası: ilişkisel (Postgres), vektörel (Chroma/Qdrant), hızlı/geçici (Redis), dosya (MinIO), olay geçmişi (Event Store).

### 04.10 Deployment
Docker / Docker Compose tabanlı dağıtım (mantıksal mimari, gerçek üretimde Docker/Kubernetes üzerinde çalışır). Config Manager, Secret Manager (SOPS/Vault), Backup & Restore burada yönetilir.

---

## 05_TOOL_PLATFORM (L3 — Yetenek & Araç Platformu)

### Amaç
Ajanların (L4) dış dünya, donanım (L0) ve harici sistemlerle **güvenli** etkileşime girdiği soyutlama katmanı.

### 05.01 Tool Platform — Genel
Bu katman olmadan hiçbir ajan sistem dışına çıkamaz; her araç çağrısı buradan geçer ve izole/izlenebilir şekilde çalışır.

### 05.02 Sandbox
nsJail / gVisor / Docker Hardened tabanlı izolasyon. Kod çalıştıran veya dış komut yürüten tüm araçlar burada koşar; ana sisteme zarar (RCE riski) engellenir.

### 05.03 Job Orchestrator
Uzun süren işlerin (web kazıma, büyük veri analizi) kuyruğa alınması, ilerleme takibi, duraklatma/iptal. Retry, timeout ve **Saga Pattern** (birbirine bağlı işlemlerden biri çökerse öncekilerin telafi edilmesi) burada uygulanır.

### 05.04 Resource Governor
Bir aracın ne kadar CPU/RAM/bant genişliği kullanabileceğini sınırlar (cgroups-style limits).

### 05.05 Plugin System / Tool & Plugin Marketplace
Dış dünya entegrasyonları için pazar yeri; kur/güncelle/etkinleştir (Install-Update-Enable) akışı.

### 05.06 MCP Gateway
Model Context Protocol üzerinden standartlaştırılmış API araçlarının protokol müzakeresi ve şema/versiyon imzalama işini yapar.

### 05.07 Capability Registry
Hangi ajanın hangi aracı kullanabileceğinin haritası (ajan-yetenek eşleşmesi, yetkinlik seviyesi, performans skoru, kullanım geçmişi, bağımlılıklar). *(Not: bir şemada bu bileşen yanlışlıkla "Capafloty Registry" yazılmış — doğrusu Capability Registry'dir, düzeltildi.)*

### 05.08 Circuit Breaker
Dış bir API yavaşlar/çökerse ardışık hataları önlemek için bağlantıyı keser (Open state), sistemin geri kalanını korur.

### 05.09 Tool API
Araçların sisteme kayıt/çağrı sözleşmesi (Protobuf/JSON Schema tabanlı, katı tip kontrolü).

### 05.10 Tool Lifecycle
Bir aracın kaydı → izin ataması → kullanımı → izlenmesi → gerektiğinde devre dışı bırakılması sürecinin tamamı; tüm adımlar Audit Logger'a düşer.

---

## 06_AGENT_MESH (L4 — Ajan Mesh & Yetenekler)

### Amaç
Monolitik tek bir LLM yerine, dar-uzmanlıklı mikro-ajanların birlikte çalışarak kolektif zekâ oluşturduğu yatay mimari.

### 06.01 Agent Mesh — Genel
Bileşenler: Agent State Manager, Agent Registry, Health Monitor, Communication Bus.

### 06.02 Agent Manager
Görev geldiğinde ajanlar kendi güven skorlarına (Confidence Level) göre göreve talip olur; Agent Manager, DAG'daki görevleri boştaki ilgili ajanlara atar.

### 06.03 System Agent
Sistemin kendi iç işleyişi ve hafıza optimizasyonuyla ilgilenen ajan (bazı kaynaklarda System/Memory Agent olarak da geçer).

### 06.04 Coding Agent
Kod yazar, hata ayıklar.

### 06.05 Browser Agent
İnternette gezinir, dinamik içerik toplar.

### 06.06 Research Agent
Derinlemesine literatür/veri taraması yapar.

### 06.07 Vision Agent
Görüntü işler, donanımdan gelen kamera verisini anlamlandırır.

### 06.08 Security Agent
Üretilen çıktıların güvenlik standartlarına uyumunu test eder.

### 06.09 Skill Engine
Ajanlar doğuştan her şeyi bilmez — Skill Registry'den ihtiyaç duydukları yetenekleri (Skills) bir kütüphane gibi çekip (Skill Executor), görev anında birleştirirler (Skill Composer). Capability Mapper, yeteneği doğru ajanla eşleştirir.

### 06.10 Task Delegation & Collaboration
Ajanlar arası P2P veya Pub/Sub mantığıyla, NATS tabanlı **Agent Message Bus** üzerinden asenkron mesajlaşarak alt-çözümleri birleştirirler.

---

## 07_COGNITIVE_SYSTEM (L5 — Bilişsel Sistem)

### Amaç
Sistemin "System 2 Thinking" (yavaş, analitik düşünme) merkezi — kullanıcı isteklerinin niyetini çözer, planlar, mantıksal çıkarım yapar.

### 07.01 Cognitive System — Genel
Bu katman, Kernel'in (L1) aksine gerçekten "düşünen" kısımdır; ama Kernel'e ait yetkilendirme kararlarına müdahale etmez.

### 07.02 Intent Engine
Kullanıcının doğal dil isteğini yapılandırılmış bir amaca (Structured Goal) dönüştürür; bir güven skoru (Confidence Scorer) üretir.

### 07.03 Planner
Niyeti alır, bir **DAG (Directed Acyclic Graph)** modeliyle mantıksal alt görevlere ayırır, bağımlılıkları çıkarır (önce araştır, sonra kod yaz gibi).

### 07.04 Reasoner
Alt görevleri değerlendirir, çelişkileri bulur; sembolik + nöral akıl yürütme uygular; ajanlardan gelen parçalı sonuçları birleştirir (Synthesis).

### 07.05 Model Router
Görevin zorluğuna göre L2'deki doğru LLM/SLM modelini seçer (basit işler için küçük model örn. 8B, karmaşık işler için daha büyük model) — GPU maliyetini ve gecikmeyi düşürür.

### 07.06 Decision Engine / 07.07 Policy Engine
Planlanan görevin sistemin yasal ve etik kurallarına (Policy as Code) uyup uymadığını denetler; nihai karar burada oluşur.

### 07.08 Governance Engine
Ajanlar veya hedefler arası çatışmaları çözen nihai hakem (Arbiter) — Capability, Permission ve Conflict Resolution yetkisine sahiptir. İki ajan zıt kararlar verirse veya döngüye girerse süreci keser, kendi kararını dayatır.

### 07.09 Risk & Priority Analyzer
Gelen isteğin taşıdığı riski puanlar; Kernel'den gelen donanım kesmelerini (acil stop vb.) anında ön sıraya alır.

### 07.10 Simulator
"What-if" / Digital Twin üzerinden olası senaryoları test ederek en doğru yolu belirler ("Ne Olur?" tahmin motoru). *(Not: Bu bileşen aynı zamanda L0'daki Dünya Modeli/Digital Twin ile bağlantılıdır — L0 ham donanım/çevre durumunu tutar, L5 Simulator bu veriyi kullanarak senaryo simülasyonu yapar. Bu ayrım şemalardaki "Digital Twin Connector" belirsizliğini gidermek için netleştirilmiştir.)*

---

## 08_MEMORY_BRAIN (L6 — Hafıza Beyni)

### Amaç
Hafıza tek bir vektör veritabanı değildir; insan bilişinden ilham alan **4 katmanlı** bir yapıdır. "Hafıza canlı bir organizmadır" — veriler sadece diske yazılmaz, özetlenir, ağırlıklandırılır, unutulma eğrisiyle (Forgetting Curve) yönetilir.

### 08.01 Memory Brain — Genel
Tüm katmanlar Memory Bus (okuma/yazma arabirimi) üzerinden erişilir.

### 08.02 Stream Memory
Sistemdeki tüm olayların (log, metrik) saniyeler içindeki akışı (Redis Stream / Kafka tabanlı, Event Sourcing Log). Kısa ömürlüdür.

### 08.03 Working Memory
Planner ve ajanların üzerinde çalıştığı, bağlam penceresinde tutulan aktif görev belleği. Görev bitince silinir veya Episodic'e aktarılır.

### 08.04 Episodic Memory
Olayların kronolojik sırayla tutulduğu geçmiş anılar dizini ("Dün kullanıcı benden sunucu kurmamı istedi" gibi).

### 08.05 Semantic Memory
Anılardan süzülen, kalıcı bilgi ve kuralların (Knowledge DNA) tutulduğu yer; vektörel uzayda (ChromaDB/Qdrant) barınır.

### 08.06 Memory Manager
Bellek yaşam döngüsünü yönetir; Consolidation, Quality, Versioning, Forgetting işlevlerini koordine eder.

### 08.07 Memory Lifecycle / 08.09 Memory Optimization
**Consolidation & Compression:** Episodic hafızadaki yüzlerce satır konuşmayı tek bir Semantic bilgiye sıkıştırır (özetleme). **Forgetting:** Sık kullanılmayan veya güncelliğini yitiren (Decay Factor) anıları daha yavaş depolamaya (Archive) iter ve vektör uzayından çıkarır.

### 08.08 Memory Indexing
Semantic Memory'nin hızlı geri çağrılabilmesi için embedding tabanlı indeksleme (vektör DB üzerinden).

### 08.10 Memory API
Diğer katmanların (özellikle L5 Planner/Reasoner ve L7 Evolution Core) hafızaya okuma/yazma için kullandığı standart, sürümlü arayüz.

---

## 09_EVOLUTION_CORE (L7 — Evrim Çekirdeği)

### Amaç
Sistemin geçmiş işlemlerden öğrenerek kendi kendini iyileştirdiği geri bildirim döngüsü (Continuous Learning). **Evrim döngüsü:** İzle → Analiz Et → Öğren → Güncelle → Uygula.

### 09.01 Evolution Core — Genel
Bu katman en fazla dikkat gerektiren katmandır çünkü sistemin kendi kendini değiştirme yetkisini barındırır — bu yüzden sıkı sınırlarla çevrilidir (bkz. 09.08).

### 09.02 Performance Analyzer / 09.03 Model Evaluator
Tamamlanan görevlerin başarı oranını, geçen süreyi, kullanıcı tatminini ölçer; modellerin performansını değerlendirir.

### 09.04 Feedback Loop
Kullanıcı ve sistem geri bildirimlerinin toplanıp değerlendirme sürecine sokulması.

### 09.05 Knowledge Updater
Hatalı verilen yanıtları tespit ederse L6'daki Semantic Memory'yi günceller.

### 09.06 Self-Optimization
Sistem yeni bir kısa yol veya kural keşfettiğinde (prompt optimizasyonu, workflow iyileştirmesi) bunu uygular — ama önce Shadow Mode'da test eder.

### 09.07 Shadow Mode
Yeni optimizasyonlar önce "gölge modunda" çalıştırılır; canlı sistemi etkilemeden başarısı ölçülür (A/B Test & Benchmark ile karşılaştırma).

### 09.08 Evolution Boundaries [KRİTİK]
Evrim Çekirdeği; **L1 Kernel mimarisine, L5 Policy Engine kurallarına, L1 Permission Gate izinlerine ve Güvenlik/Zero Trust mekanizmalarına kesinlikle müdahale edemez, kural değiştiremez.** Çekirdek modüller sabittir (Immutable Core Policies). Bu seviyedeki değişiklikler yalnızca sistem mühendislerinin manuel onayı ve kod güncellemesiyle yapılabilir.

### 09.09 HITL (Human-in-the-Loop)
Kritik kararlar, silme işlemleri, üretim ortamına büyük kod dağıtımları mutlaka insan onayına tabidir. Şemalarda bu katmanda ayrıca şu bileşenler görünüyor — mevcut spesifikasyonda ayrıntılı tanımlı değildi, buraya şemadan aktarılmıştır:
- **Kod Üretim Motoru (Code Generation):** Sistemin kendi bileşenleri için kod önerisi/üretimi.
- **Sandbox Test Ortamı:** Üretilen kodun izole test edilmesi (gVisor/WASM/nsjail).
- **Güvenli Dağıtım (Blue-Green Deploy):** Yeni sürümün eskisiyle paralel, riske atmadan devreye alınması.
- **Geri Dönüş Yönetimi (Rollback Manager):** Sorun çıkarsa anında önceki sürüme dönme.
> Bu dört madde (kod üretimi + otomatik deploy + rollback), sistemin kendi kodunu yazıp canlıya alma kapasitesine işaret eder — bu, 09.08'deki sınırlarla birlikte **çok sıkı HITL onayı gerektiren** en kritik yetenek olarak işaretlenmelidir.

### 09.10 Continuous Learning
Arka planda sürekli çalışan, öğrenme döngüsünün (08.07 ile bağlantılı) sistemleştirilmiş hâli.

---

## 10_SECURITY

### Amaç
Güvenlik, sisteme sonradan eklenen bir katman değil; tüm katmanları **yatay olarak kesen bir "Security Fabric"tir**. Sistem içerisinde gerçekleşen her işlem doğrulanır, her erişim denetlenir, her kaynak korunur, her olay kayıt altına alınır — Agent, Kernel, Memory, Network, Tool ve kullanıcı seviyesinde eşzamanlı uygulanır.

### 10.01 Security Model
Güvenlik hedefleri: kimlik doğrulama, yetkilendirme, veri gizliliği/bütünlüğü, izlenebilirlik, minimum yetki, Zero Trust, savunma katmanları, saldırı yüzeyinin azaltılması, hata izolasyonu. Güvenlik katmanları sırayla: Kullanıcı Güvenliği → API Güvenliği → Permission Gate → Kernel Kontrolleri → Capability Kontrolleri → Tool Güvenliği → Memory Güvenliği → Audit Log → Monitoring. Bir katmanın başarısız olması diğerlerinin devreye girmesine engel değildir. Varsayılan: hiçbir erişime izin verilmez; her istek yeniden değerlendirilir.

### 10.02 Zero Trust
Hiçbir kullanıcı, Agent, Tool, API veya servis varsayılan olarak güvenilir kabul edilmez. Daha önce izin verilmiş olması gelecekte de izin verileceği anlamına gelmez — **her işlem yeniden doğrulanır.** İlkeler: her isteği doğrula, her kaynağı koru, her erişimi kaydet, en az yetkiyi ver, yetkiyi gerektiğinde geri al, davranışı sürekli izle, risk değişirse izinleri değiştir. Risk arttığında izinler azaltılabilir, Tool erişimi kaldırılabilir, internet erişimi kesilebilir, MCP bağlantıları sınırlandırılabilir, Agent tamamen izole edilebilir.

### 10.03 Authentication
Kimin gerçekten iddia ettiği kimliğe sahip olduğunu doğrular — kullanıcılar, ajanlar, LLM servisleri, Tool Platformu, MCP sunucuları, API Gateway, harici servisler bu kapsamdadır. Yöntemler: Parola, API Key, JWT, OAuth, OpenID Connect, X.509 sertifikaları, mTLS, Servis Kimlikleri. Her servisin benzersiz bir kimliği vardır (Memory Service, Planner, Reasoner, Vision/Browser/Coding Agent aynı kimliği paylaşamaz) — böylece hangi işlemi kimin yaptığı kesin belirlenir.

### 10.04 Authorization
Authentication "kim olduğunu", Authorization "ne yapabileceğini" belirler. Süreç: Kimlik doğrulanır → Permission Gate çalışır → Capability kontrol edilir → Politikalar değerlendirilir → Kaynak erişimi doğrulanır → Karar oluşturulur → İstek kabul/red. **Minimum yetki örneği:** Browser Agent internete erişebilir ama Memory Database'i silemez; Coding Agent kod yazabilir ama Kernel'i durduramaz. Yetki türleri: Okuma, Yazma, Çalıştırma, Silme, Güncelleme, Paylaşma, Yönetme, İzleme.

### 10.05 Capability Model
UMAY klasik RBAC yerine **Capability-Based Security** kullanır — bileşene rol değil, yapabileceği işlemler tanımlanır. Örnek: Coding Agent → Write Code, Execute Tests, Read Repository, Create Project. Avantajlar: daha güvenli, daha esnek, minimum yetki, servisler bağımsız yönetilebilir, dinamik güncellenebilir, ince ayrıntılı erişim kontrolü. Yaşam döngüsü: oluşturulur → atanır → doğrulanır → kullanılır → izlenir → gerektiğinde iptal edilir; tüm süreç Audit Log'a düşer.

### 10.06 Encryption / 10.07 Secrets Manager
API anahtarları L2'de Secret Manager (SOPS/Vault) içinde şifreli tutulur. Veriler diskte ve ağda (In-Transit/At-Rest) AES-256 ile şifrelenir; mTLS/TLS 1.3 ile servisler arası iletişim korunur.

### 10.08 Audit Log
İnsan veya sistem tarafından yapılan tüm kritik eylemler, değiştirilemez bir Log veritabanında (Event Store) saklanır — Immutable Audit Log.

### 10.09 Security Policies
Policy as Code yaklaşımıyla (L5 Policy Engine ile bağlantılı) tanımlanan, otomatik denetlenen kurallar bütünü.

### 10.10 Threat Model
Sandbox Isolation (her dış araç izole konteynerde çalışır), Circuit Breaker (dış API çökerse bağlantı kesilir), RCE (uzaktan kod çalıştırma) riskine karşı Sandbox Runner (nsJail/gVisor/Docker Hardened) — tehdit senaryoları ve karşı önlemler burada belgelenir.

---

## 11_OBSERVABILITY

### Amaç
Sistem kara kutu değildir, şeffaftır — ne olduğu her zaman izlenebilir olmalıdır.

### 11.01 Observability — Genel
OpenTelemetry yaklaşımı: her gelen istek L8'de bir Trace ID alır; L1'den geçerken, L5'te parçalanırken, L4'te ajanlara dağıtılırken her adıma bir Span ID atanır. Böylece "hata tam olarak hangi ajanın hangi aracında oldu?" sorusu saniyeler içinde bulunur.

### 11.02 Logging
Loki üzerinden yapılandırılmış (Structured JSON) uygulama logları toplanır.

### 11.03 Metrics
Prometheus ile sistem kaynakları (CPU, token kullanımı, ajan bekleme süreleri) izlenir.

### 11.04 Tracing
Dağıtık izleme (Distributed Tracing) — bir isteğin tüm katmanlar boyunca izini sürme.

### 11.05 Health Checks
L1 Watchdog ve L2 gözlemcileri üzerinden servislerin SLA/SLO takipleri.

### 11.06 Alerts
Alert Manager — eşik aşımlarında (kaynak, hata oranı, gecikme) bildirim üretir.

### 11.07-11.08 Diagnostics / Debugging
Sorun giderme için Trace/Span verisiyle birleştirilmiş tanı araçları.

### 11.09 Performance Monitoring
Model Router seçimleri, ajan bekleme süreleri, kaynak kullanım eğilimleri.

### 11.10 System Reports
Dashboards (Grafana) — periyodik sistem sağlığı ve kullanım raporları.

---

## 12_ENGINEERING

### Amaç
Kod geliştirme standartlarını tanımlar — mimari kararların koda nasıl yansıyacağını belirler.

### 12.01-12.02 Engineering Guide / Coding Standards
Clean Architecture ve Hexagonal Architecture kullanılır. Bağımlılıklar daima dış katmandan iç (Domain/Kernel) katmana doğru olmalıdır (Dependency Rule).

### 12.03 Project Structure
Fiziksel kod klasörlerinin bu mantıksal 00-21 dokümantasyon ağacıyla ilişkisi (örn. `/kernel`, `/agents`, `/memory` gibi kod klasörleri 03/06/08 dokümanlarına karşılık gelir).

### 12.04 API Standards
Modüller arası haberleşmede katı Protobuf veya JSON Schema tanımlamaları kullanılır.

### 12.05-12.06 Design Patterns / Clean Architecture
Servisler tamamen Stateless geliştirilir, veriler L2 veya L6'ya yazılır.

### 12.07 Testing Strategy
Her modül (özellikle L1 ve L5) için **%85+ Unit Test** kapsamı zorunludur. Ajanlar için TDD yaklaşımı; L7 Test Sandbox ortamında Integration & Behavior Testleri uygulanır.

### 12.08 Contribution Guide / 12.09 Release Process / 12.10 Best Practices
Katkı süreci, sürüm çıkarma disiplini (bkz. 19_RELEASES) ve genel iyi pratikler.

---

## 13_ROADMAP

### Amaç
Projenin aşamalı hayata geçiş planı.

### 13.01 Master Roadmap — Fazlar
- **Faz 1 – MVP:** Temel L1 Kernel, L2 Altyapı, L5 Intent/Planner ve tek bir L4 ajanı (System Agent). Hafıza sadece Stream ve Working Memory.
- **Faz 2 – Foundation:** L6 Episodic Memory ve L3 Tool Platform (Sandbox olmadan) entegrasyonu; ajan sayısının artırılması (Coding, Browser).
- **Faz 3 – Core:** Tüm hafıza katmanlarının, Sandbox güvenliğinin ve Zero Trust politikalarının tam aktivasyonu; L7 Performance Analyzer eklenmesi.
- **Faz 4 – Advanced:** Çoklu ajan haberleşmesi, gelişmiş DAG planlamaları, Edge donanım testleri, donanım kesmelerinin (L0→L1) uygulanması.
- **Faz 5 – Autonomous & Enterprise:** L7 Evolution Core'un tam devreye alınması (Shadow Mode ile kendi kendini iyileştirme), otonom yönetim, UMAY Ağlarına (Afet/Güvenlik) tam entegrasyon.

### 13.02 MVP
Bkz. Faz 1 — ilk çalışan Kernel, ilk çalışan Memory, ilk çalışan Agent, ilk çalışan Planner, ilk Tool, ilk Web Panel, ilk UMAY demo.

### 13.03-13.07 Phase 1-5
Yukarıdaki fazların ayrıntılı alt görev listeleri (bu doküman, kullanıcının ayrı tuttuğu FAZ 1-14 TODO listesiyle birlikte okunmalı — o liste operasyonel kontrol listesi, burası stratejik roadmap'tir).

### 13.08 Backlog / 13.09 TODO / 13.10 Changelog
Bekleyen fikirler, güncel yapılacaklar ve sürüm değişiklik kayıtları.

---

## 14_DIAGRAMS

### Amaç
Tüm görsel/şema varlıklarının deposu. Alt klasörler: Architecture, Engineering, UML, Sequence, Flowcharts, Dataflow, Network, Memory, AgentMesh, UI. Şu anki iki ana görsel (v4.1 İşleyiş Şeması ve Mimari Ağacı Tam Hâl) `Architecture/` altına konulmalıdır; gelecekte üretilecek Sequence diyagramları (istek yaşam döngüsü), Dataflow diyagramları (Slow/Fast Path) ve AgentMesh diyagramları (ajanlar arası mesajlaşma) da buraya eklenecektir.

---

## 15_PATENTS

### Amaç
Patent taslakları, çizimler, iddialar (Claims), referanslar ve hukuki belgeler için ayrılmıştır. UMAY'ın microkernel + event-driven + agentic + self-evolving kombinasyonu, özellikle **Evolution Boundaries (09.08)** ile **Interrupt Bus Bypass (03.05)** mekanizmaları, özgün mühendislik yaklaşımları olarak patent açısından değerlendirilebilir — ancak bu klasörün içeriği hukuki bir süreçtir ve bu teknik dokümanın kapsamı dışındadır.

---

## 16_RESEARCH

### Amaç
AI, LLM, Agentic AI literatürü, akademik makaleler, deneyler, benchmark sonuçları ve referanslar. UMAY'ın Model Router (07.05), Skill Engine (06.09) ve Evolution Core (09_) tasarımları geliştirilirken faydalanılacak/faydalanılan kaynaklar burada tutulur.

---

## 17_MEETING_NOTES

### Amaç
Kararlar, tartışmalar, beyin fırtınaları, gözden geçirmeler ve genel toplantı günlüğü (Meeting_Log.md). Mimarinin v1.0'dan v4.1'e evrildiği kararlar (örn. L7'ye Kod Üretim Motoru/Blue-Green Deploy eklenmesi gibi) buraya kaydedilmelidir ki gelecekte "neden böyle karar verildi" sorusu cevaplanabilsin.

---

## 18_ARCHIVE

### Amaç
Eski sürümler, kullanılmayan (deprecated) tasarımlar, eski mimari denemeler ve anlık görüntüler (snapshots). Örneğin Architecture Specification'ın v1.0 hâli, v4.1'e geçildikten sonra burada arşivlenmelidir — silinmemeli, referans olarak saklanmalıdır.

---

## 19_RELEASES

### Amaç
Sürüm bazlı çıktı deposu — v0.x (deneysel), v1.0, v1.1, v2.0 ve her sürüme ait Release Notes. 13_ROADMAP'teki fazlar tamamlandıkça buraya karşılık gelen sürümler düşer (örn. Faz 1/MVP tamamlanınca → v0.1; Faz 5/Autonomous tamamlanınca → v2.0 gibi bir eşleme önerilir, kesin numaralandırma proje ekibine aittir).

---

## 20_HARDWARE_WORLD_MODEL (L0 — EKLENDİ)

> Bu klasör orijinal 19'lu ağaçta yoktu; şemalarda L0 olarak ayrı ve önemli bir katman olduğu için eklendi.

### Amaç
Fiziksel dünya ile etkileşimin temelidir — sistemin "topraklandığı" (grounding) yer.

### Bileşenler
- **Sistem Kaynakları:** Üzerinde çalışılan donanımın CPU/GPU/RAM/Disk/Fan/Sıcaklık/Batarya bilgisi.
- **IoT & Edge Cihazlar:** Arduino, ESP32, PLC sensörleri, drone/robot telemetrisi.
- **Digital Twin (Environment Mirror):** Sistemin çalıştığı fiziksel çevrenin eşzamanlı dijital yansıması, kaynak kullanımı izlemesi, fiziksel durum senkronizasyonu.
- **Dünya Modeli (World Model):** Hava durumu, piyasa verileri, konum/zaman gibi dış dünya bağlamını (Context) tutan ontolojik yapı — sistemin halüsinasyon görmesini engelleyen "topraklama" noktası.
- **Sensor / Hardware Interrupts:** Aşırı ısınma, batarya düşük, yangın, deprem, acil stop gibi sensörler — bunlar 03.05 Interrupt Bus'a doğrudan bağlanır (Bypass kanalı).

### Sınırlar
L0 kendi başına karar vermez; yalnızca veri/durum sağlar. Karar L5 Risk & Priority Analyzer'da, yetkilendirme L1 Permission Gate'te verilir.

---

## 21_INTERFACE_LAYER (L8 — EKLENDİ)

> Bu klasör de orijinal 19'lu ağaçta yoktu; kullanıcının sistemle temas noktası olan L8 için eklendi.

### Amaç
Kullanıcının UMAY AI OS ile teması bu katmandan geçer; isteği alır, standart formata sokup L1'e iletir.

### Bileşenler
- **Web Dashboard** (React/Next.js)
- **Desktop App** (Electron/Tauri)
- **Mobil Uygulama** (Android/iOS)
- **Sesli Arayüz** (STT/TTS/Wake Word)
- **CLI** (Komut Satırı)
- **API Gateway** (Harici Erişim)
- **IDE Entegrasyonları** (VS Code / Cursor / JetBrains) — bu bileşen yalnızca en güncel şemada (v4.1 Mimari Ağacı) görünüyor, önceki metin spesifikasyonunda yoktu; geliştiricilerin UMAY'ı kendi IDE'lerinden çağırabilmesini sağlar.

### Sınırlar
L8 hiçbir işi kendisi çözmez; her isteği L1 Kernel'e yönlendirir. Kimlik doğrulama L8'de başlamaz, L1 Permission Gate'te tamamlanır.

---

## EK: Şema–Metin Senkron Notları

Bu bölüm, kaynakları birleştirirken tespit edilen ve bu dosyada **düzeltilmiş/netleştirilmiş** noktaların şeffaf kaydıdır — ileride "bunu ben mi yazmıştım" karışıklığı olmasın diye:

1. **Sürüm senkronu:** Metin spesifikasyonu v1.0 idi, şemalar v4.1'e ulaşmıştı. Bu dosya v4.1'i esas aldı; v1.0, 18_ARCHIVE'e kaldırılmalı.
2. **09_EVOLUTION_CORE'a eklenenler:** Kod Üretim Motoru, A/B Test & Benchmark, Blue-Green Deploy, Rollback Manager — sadece şemalarda vardı, metinde yoktu. 09.09 altına eklendi ve kritik risk notu düşüldü.
3. **21_INTERFACE_LAYER'a eklenen:** IDE Entegrasyonları — sadece en güncel şemada (Mimari Ağacı Tam Hâl) vardı.
4. **05.07 Capability Registry yazım hatası:** Bir şemada "Capafloty Registry" yazılmıştı, doğrusu Capability Registry olarak düzeltildi.
5. **Digital Twin belirsizliği çözüldü:** L0'daki "Digital Twin (Environment Mirror)" ham donanım/çevre durumunu tutan taraf; L5'teki "Simulator/Digital Twin Connector" (07.10) bu veriyi kullanarak senaryo simülasyonu yapan taraf olarak ayrıştırıldı.
6. **20_HARDWARE_WORLD_MODEL ve 21_INTERFACE_LAYER** tamamen yeni eklenen klasörlerdir (L0 ve L8 için) — orijinal 00-19 ağacında yoktu, şemalardaki iki büyük katmanı kaybetmemek için eklendi.

Bu notlar dışındaki her şey, kullanıcının sağladığı ana ağaca, iki mimari şemaya ve Architecture Specification v1.0 metnine sadık kalınarak yazılmıştır; hiçbir yeni özellik veya kavram icat edilmemiştir.

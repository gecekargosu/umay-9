# UMAY AI OS — Mimari Katmanlar (L0-L8)

Katman akışı: L0 Donanım → L1 Kernel → L2 Altyapı → L3 Araç Platformu → L4 Ajan Mesh → L5 Bilişsel Sistem → L6 Hafıza Beyni → L7 Evrim Çekirdeği → L8 Arayüz

## L0 — Donanım & Dünya Modeli
CPU/GPU/RAM/Disk, IoT & Edge (Arduino, ESP32), Digital Twin (çevrenin dijital yansıması), Dünya Modeli (hava durumu, konum, piyasa). Sensörler acil durumda L1 Interrupt Bus'a direkt bağlanır (Bypass).

## L1 — UMAY Kernel (Microkernel)
IPC Bus (bileşen iletişimi), Scheduler (görev önceliklendirme), Permission Gate (Zero Trust), Interrupt Bus (acil bypass), Watchdog (sağlık izleme), State Snapshot, Graceful Teardown, Boot Sequence (UMAY-INIT).

## L2 — Altyapı & Servisler
PostgreSQL (metadata), ChromaDB/Qdrant (vektör DB), Redis Stack (önbellek), MinIO (dosya deposu), Ollama/vLLM (model runtime), NATS (event/message bus), Prometheus/Loki/OpenTelemetry (gözlemlenebilirlik).

## L3 — Yetenek & Araç Platformu
Sandbox Runner (nsJail/gVisor), Job Orchestrator (kuyruk yönetimi), Resource Governor (CPU/RAM limitleri), MCP Gateway (Model Context Protocol), Plugin Marketplace, Capability Registry, Circuit Breaker.

## L4 — Ajan Mesh & Yetenekler
Coding Agent, Browser Agent, Research Agent, Vision Agent, Security Agent, System Agent. Skill Engine: Skill Registry + Skill Executor + Skill Composer. Agent Manager görevleri DAG ile dağıtır.

## L5 — Bilişsel Sistem
Intent Engine (niyet anlama), Planner (DAG'a bölme), Reasoner (sentez), Model Router (doğru modeli seç), Decision Engine, Policy Engine, Governance Engine (hakem), Risk & Priority Analyzer, Simulator (What-if).

## L6 — Hafıza Beyni (4 Katman)
1. Stream Memory (anlık olay akışı, Redis)
2. Working Memory (aktif görev belleği)
3. Episodic Memory (kronolojik anılar)
4. Semantic Memory (kalıcı bilgi, ChromaDB vektör uzayı)
Memory Manager: Consolidation, Forgetting Curve, Versioning.

## L7 — Evrim Çekirdeği
Performance Analyzer, Feedback Loop, Continuous Learning, Model Evaluator, Knowledge Updater, Self-Optimization (Shadow Mode ile test edilir), HITL onayı zorunlu. KRİTİK: L1 Kernel ve güvenlik kurallarına kesinlikle müdahale edemez.

## L8 — Arayüz & Deneyim
Web Dashboard (React/Next.js), Desktop App (Electron/Tauri), Mobil (Android/iOS), Sesli Arayüz (STT/TTS/Wake Word), CLI (Terminal), API Gateway, IDE Entegrasyonları (VS Code, Cursor).

## Çapraz Katman Yapılar
- Security Fabric (10_SECURITY): Her katmanı yatay keser
- Observability (11_OBSERVABILITY): Her işlem izlenebilir
- Normal Akış (Slow Path): L8→L1→L5→L4→L3→L6→L8
- Acil Akış (Fast Path): L0 sensör → L1 Interrupt Bus → L5 Risk Engine (bypass)

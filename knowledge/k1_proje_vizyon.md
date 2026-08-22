# UMAY AI OS — Proje Kimliği ve Vizyon

## Nedir?
UMAY AI OS; donanım seviyesinden kullanıcı arayüzüne kadar uzanan, otonom, modüler ve olay güdümlü (event-driven) bir Yapay Zekâ İşletim Sistemidir. Klasik sohbet botlarının ötesine geçer — yapay zeka modellerini, hafızayı ve araçları birer sistem kaynağı olarak yöneten bir işletim sistemi çekirdeğidir.

## Temel Hedefler
- Otonom çok ajanlı (multi-agent) sistem
- Güçlü 4 katmanlı hafıza (Stream/Working/Episodic/Semantic)
- Zero Trust güvenlik mimarisi
- Edge cihazlarda çalışabilme, IoT entegrasyonu
- Tamamen modüler, event-driven mimari
- Kendi kendini geliştirebilen (Self-Evolving) yapı

## Proje Kapsamı
- Yerel çalışan (Ollama tabanlı) çok ajanlı asistan
- Kod yazma, web gezinme, dosya/doküman anlama, sesli komut
- Uzaktan erişim, otomatik günlük görev yürütme
- Modüler yapı: yeni model eklemek için çekirdek kod değişmez

## Mimari Felsefe
- Microkernel: Kernel sadece koordine eder, karar vermez
- Event-Driven: Tüm bileşenler asenkron olaylarla haberleşir
- Agentic AI: Dar uzmanlıklı ajanlar iş birliği yapar
- Dependency Inversion: Üst katmanlar alt katmanların soyut arayüzlerine bağlıdır
- Zero Trust: Hiçbir bileşen varsayılan olarak güvenilir sayılmaz

## Proje Kuralları
- Kernel iş mantığı taşımaz; sadece koordine eder
- Evrim Çekirdeği (L7), Kernel kurallarına müdahale edemez
- Kritik işlemler mutlaka insan onayından (HITL) geçer

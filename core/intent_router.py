"""
UMAY Intent Router
===================
Kullanıcı mesajlarını intent kategorilerine sınıflandırır.
Bu sayede doğru tool, model ve davranış seçilir.

Intent Kategorileri:
- CHAT: Doğal sohbet, selamlama, soru-cevap
- KNOWLEDGE: Bilgi isteği, açıklama
- TIME: Saat, tarih, zaman bilgisi
- FILE: Dosya sistemi işlemleri
- DOCUMENT: PDF/Word/Excel okuma
- VISION: Görsel analiz
- WEB: İnternet araştırması
- CODE: Kod yazma/düzenleme
- TERMINAL: Komut çalıştırma
- MEMORY: Hafıza/bellek işlemleri
- COMPLEX: Karmaşık görevler (multi-step)
"""
from __future__ import annotations

import os
import re
from enum import Enum
from typing import Optional


class Intent(str, Enum):
    CHAT = "chat"
    KNOWLEDGE = "knowledge"
    TIME = "time"
    FILE = "file"
    DOCUMENT = "document"
    VISION = "vision"
    WEB = "web"
    CODE = "code"
    TERMINAL = "terminal"
    MEMORY = "memory"
    COMPLEX = "complex"
    CALCULATOR = "calculator"


# ─── Intent Kuralları ──────────────────────────────────────────────────────

INTENT_RULES = [
    # TIME — Saat/tarih istekleri (EN YÜKSEK ÖNCELİK — en spesifik kelimeler önce)
    (Intent.TIME, [
        "saat kaç", "saat kac", "şu an saat", "simdi saat", "şimdi saat",
        "saat kaç şimdi", "saat kac simdi", "saat kaçtayız", "saat kaçtayiz",
        "bugün günlerden", "bugun gunlerden", "bugünün tarihi", "bugunun tarihi",
        "bugün ne zaman", "bugun ne zaman", "hangi gün", "hangi tarih",
        "hangi gündeyiz", "hangi gundeyiz", "hangi tarihteyiz",
        "tarih bugün", "tarih bugun", "gün bugün", "gun bugun",
        "bugün ne", "bugun ne", "kaçıncı gün", "kaçinci gun",
        "ayın kaçı", "ayin kaci", "yıl", "yil", "tarih ne",
    ]),

    # CALCULATOR — Matematik işlemleri
    (Intent.CALCULATOR, [
        "+", "-", "*", "/", "=",
        "toplam", "topla", "çarp", "carp", "böl", "bol",
        "kaç eder", "kac eder", "sonuc", "sonuç",
    ]),

    # FILE — Dosya sistemi işlemleri
    (Intent.FILE, [
        "klasörü listele", "klasoru listele", "klasörleri listele",
        "dosyaları listele", "dosyalari listele",
        "klasördeki", "klasordaki", "klasörde ne var",
        "dosyayı oku", "dosyayi oku", "dosyanın içeriği", "dosyanin icerigi",
        "dosyayı aç", "dosyayi ac", "klasörü aç", "klasoru ac",
        "dosya ara", "dosyayi ara", "bul dosya", "dosyayı bul",
        "hangi klasörde", "hangi klasorde", "nerede bu dosya",
        "masaüstü", "masaustu", "masaüstündeki", "masaustundeki",
        "masaüstünü", "masaustunu", "masaüstünde", "masaustunde",
        "desktop", "downloads", "indirilenler",
        "belgeler", "belgeleri", "belgelerdeki", "belgeleri listele",
        "documents", "cv", "özgeçmiş", "ozgecmis",
        "dosyaları göster", "dosyalari goster",
        "klasör yapısını", "klapisini", "klasor yapisini",
        "bu klasörde", "bu klasorde", "şu klasörde", "su klasorde",
    ]),

    # DOCUMENT — PDF/Word/Excel
    (Intent.DOCUMENT, [
        "pdf", "word", "excel", "xlsx", "docx", "csv",
        "belgeyi oku", "belgeyi incele", "dosyayı analiz et",
        "cv'yi oku", "cv oku", "özgeçmişi oku",
        "belge içeriği", "belge icerigi",
        "sayfa", "tablo", "işaret", "imza",
    ]),

    # VISION — Görsel analiz
    (Intent.VISION, [
        "resim", "resmi", "fotoğraf", "görsel", "image", "photo",
        "ekran görüntüsü", "ekran goruntusu", "screenshot",
        "bu resimde", "bu görselde", "bu fotoğrafta",
        "resimde ne var", "görselde ne var",
        "hata ekranı", "hata ekrani", "error screen",
        "grafik", "tablo", "chart", "diyagram",
    ]),

    # WEB — İnternet araştırması
    (Intent.WEB, [
        "internette ara", "web'de ara", "webde ara", "internetten",
        "google'da", "google'da ara", "arama yap",
        "güncel", "guncel", "haber", "news",
        "fiyat", "price", "kur", "döviz",
        "hava", "weather", "sıcaklık",
        "github", "stackoverflow", "doküman", "documentation",
        "web sitesi", "web sitesi aç", "siteyi aç",
    ]),

    # CODE — Kod yazma/düzenleme
    (Intent.CODE, [
        "kod yaz", "kod oluştur", "kod olustur",
        "dosyayı yaz", "dosyayi yaz", "oluştur", "olustur",
        "düzelt", "duzelt", "hata düzelt",
        "test yaz", "test olustur", "pytest",
        "build", "compile", "çalıştır", "calistir",
        "git diff", "git status", "commit",
    ]),

    # TERMINAL — Komut çalıştırma
    (Intent.TERMINAL, [
        "komut çalıştır", "komut calistir", "terminal",
        "cmd", "powershell", "shell",
        "process", "task manager", "pid",
        "sistem bilgisi", "sistem bilgisi al",
        "log oku", "log dosyası",
    ]),

    # MEMORY — Hafıza/bellek
    (Intent.MEMORY, [
        "hatırla", "hatirla", "bellekte tut", "kaydet",
        "hafızana al", "hafizana al", "unutma",
        "daha önce", "onceki konusma", "önceki konuşma",
        "az önce", "az once", "geçen sefer", "gecen sefer",
        "ne söylemiştim", "ne soylemisti",
    ]),

    # COMPLEX — Karmaşık görevler (multi-step)
    (Intent.COMPLEX, [
        "incele", "araştır", "arastir", "analiz et",
        "proje", "audit", "rapor", "report",
        "test çalıştır", "test calistir",
        "deploy", "yayınla", "yayinla",
        "mimari", "architecture", "tasarım", "tasarim",
    ]),

    # KNOWLEDGE — Bilgi isteği (CHAT'ten sonra gelir)
    (Intent.KNOWLEDGE, [
        "nedir", "ne demek", "nasıl çalışır", "nasil calisir",
        "açıkla", "acikla", "anlat", "öyle mi",
        "hakkında bilgi", "hakkinda bilgi",
        "farkı ne", "farki ne", "karşılaştır", "karsilastir",
        "avantajları", "avantajlari", "dezavantajları",
        "öner", "oner", "tavsiye", "tavsiye et",
    ]),

    # CHAT — Doğal sohbet (en düşük öncelik, default)
    (Intent.CHAT, [
        "merhaba", "selam", "hey", "naber", "nasılsın", "nasilsin",
        "iyi misin", "kimsin", "sen kimsin", "kendini tanıt",
        "kendini tanit", "ne yapabilirsin", "neler yapabilirsin",
        "arkadaşım ol", "arkadasim ol", "sohbet et",
        "teşekkür", "tesekkur", "sağol", "sagol",
        "tamam", "olur", "yok", "evet", "hayır", "hayir",
    ]),
]


def classify_intent(text: str) -> Intent:
    """Kullanıcı mesajını intent kategorisine sınıflandır."""
    if not text or not text.strip():
        return Intent.CHAT

    text_lower = text.lower().strip()

    # ── CALCULATOR DETECTION (GENİŞLETİLMİŞ) ──
    import re as _re
    
    # 1. Matematik operatörleri varsa → CALCULATOR
    has_numbers = bool(_re.search(r'\d', text_lower))
    has_math_ops = any(op in text_lower for op in ['+', '-', '*', '/', '=', '^', '**', '×', '÷'])
    # 'x' harfi sadece sayilar arasindaysa carpma isareti sayilir: "125 x 48"
    if not has_math_ops:
        has_math_ops = bool(_re.search(r'\d\s*x\s*\d', text_lower))
    
    # 2. Türkçe matematik kelimeleri (SADECE kesin matematik bağlamında)
    # NOT: 'matematik', 'ortalama', 'işlem', 'hesapla' tek başına CALCULATOR tetiklemez
    # Çünkü "İnternette matematik haberleri" WEB olmalı
    has_math_words = any(w in text_lower for w in [
        # Kesin işlemler (sayı ile birlikte olmalı)
        'topla', 'çarp', 'carp', 'böl', 'bol',
        'kaç eder', 'kac eder', 'sonuç', 'sonuc', 'eşit', 'esit',
        # Üs alma (sayı ile birlikte)
        'karesi', 'karesini', 'kare', 'kaçın karesi', 'kaacin karesi',
        'küpü', 'küpünü', 'kupu', 'kupunu', 'kaçın küpü',
        # Sayı ile birlikte anlamlı olanlar
        'kaçtır', 'kactir', 'kaçtir', 'kaçıncı',
        'toplamı', 'toplami', 'farkı', 'farki',
        'çarpımı', 'carpimi', 'bölümü', 'bolumu',
        'yüzdesi', 'yuzdesi',
    ])
    # 'hesapla' SADECE sayı ile birlikteyse CALCULATOR
    has_hesapla_with_number = has_numbers and any(w in text_lower for w in ['hesapla', 'hesaplama', 'hesaplayalım'])
    if has_hesapla_with_number:
        has_math_words = True
    # 'ortalama' SADECE sayı ile birlikteyse CALCULATOR  
    has_ortalama_with_number = has_numbers and any(w in text_lower for w in ['ortalama', 'yüzde', 'yuzde'])
    if has_ortalama_with_number:
        has_math_words = True
    # 'matematik' ve 'işlem' SADECE sayı + matematik operatör varsa CALCULATOR
    # "125×48 matematik işlemi" → CALCULATOR
    # "İnternette matematik haberleri" → WEB (sayı yok)
    has_math_term_with_ops = has_numbers and has_math_ops and any(w in text_lower for w in ['matematik', 'işlem', 'islem'])
    if has_math_term_with_ops:
        has_math_words = True
    
    # 3. X ile Y topla / X'den Y çıkar / X'i Y'ye böl gibi pattern'lar
    has_turkish_math_pattern = bool(_re.search(
        r'(\d+\s*(ile|den|i|e|yi|yı|nin|nın|ün|ün|in|in)\s*\d+\s*(topla|carp|çarp|bol|böl|çıkart|cikart|çıkar|cikar))',
        text_lower
    ))
    
    # 4. X'in karesi / X'in küpü gibi pattern'lar
    has_power_pattern = bool(_re.search(
        r'(\d+\s*(nin|nın|ün|ün|in|in)\s*(karesi|karesini|küpü|küpünü|kupu|kupunu))',
        text_lower
    ))
    
    # 5. Yüzde hesaplama pattern'ı
    has_percentage_pattern = bool(_re.search(
        r'(\d+\s*(ün|ın|in|nin|nın)\s*%?\s*\d*\s*(yüzdesi|yuzdesi|kaç|kac))',
        text_lower
    ))
    
    # Negation detection: "hesaplamanı değil", "hesaplama istemiyorum" gibi ifadeler calculator'a gitmemeli
    has_negation_around_math = bool(_re.search(
        r'(hesapla\w*\s*(değil|degil|istemiyorum|istemez|yapma|olmaz|gerek|yok|mi\s+değil))',
        text_lower
    ))

    # Calculator karar mantığı
    is_calc = (has_numbers and has_math_ops) or has_math_words or has_turkish_math_pattern or has_power_pattern or has_percentage_pattern
    
    if is_calc:
        # Negation varsa calculator'a gitme
        if has_negation_around_math:
            return Intent.CHAT
        # Tek başına 'hesapla/hesaplama' ve sayı yoksa → CHAT
        if text_lower.strip() in ('hesapla', 'hesaplama', 'hesaplayalım'):
            return Intent.CHAT
        # "hesapla" var ama sayı yoksa → CHAT ("internette haberleri hesapla" gibi)
        if not has_numbers and any(w in text_lower for w in ['hesapla', 'hesaplama']):
            return Intent.CHAT
        return Intent.CALCULATOR

    # TERMINAL once check: cmd/terminal/powershell kelimesi varsa TERMINAL
    # Bu, CODE'daki 'calistir' keyword'unun_TERMINAL'i overrides etmesini engeller
    _terminal_keywords = ['cmd', 'terminal', 'powershell', 'ps ', 'komut calistir', 'komut çalıştır']
    if any(kw in text_lower for kw in _terminal_keywords):
        return Intent.TERMINAL

    # Her intent'i kontrol et (öncelik sırasına göre)
    for intent, keywords in INTENT_RULES:
        for keyword in keywords:
            if keyword in text_lower:
                return intent

    # Default: CHAT
    return Intent.CHAT


def get_available_tools(intent: Intent) -> list[str] | None:
    """Intent'e göre kullanılabilir tool listesini dön.

    None dönerse tool kullanılmaz (chat mode).
    """
    TOOL_MAP = {
        Intent.CHAT: None,  # Tool kullanma
        Intent.KNOWLEDGE: None,  # Tool kullanma, sadece LLM
        Intent.TIME: ["get_current_time", "get_current_date"],
        Intent.CALCULATOR: ["evaluate_expression"],
        Intent.FILE: ["list_directory", "read_file", "search_files",
                      "open_file", "open_folder", "scan_directory"],
        Intent.DOCUMENT: ["read_document", "scan_directory", "search_in_documents"],
        Intent.VISION: ["analyze_image", "image_to_text", "describe_image", "image_qa"],
        Intent.WEB: ["web_search", "browser_open", "browser_read",
                     "research_topic", "quick_research"],
        Intent.CODE: ["read_file", "write_file", "run_command", "run_test_suite",
                      "read_code", "generate_code"],
        Intent.TERMINAL: ["run_command", "run_terminal_command", "run_powershell",
                          "get_system_info", "list_processes"],
        Intent.MEMORY: None,  # Memory operations use conversation_store
        Intent.COMPLEX: None,  # Tüm tool'lar kullanılabilir (agent loop)
    }
    return TOOL_MAP.get(intent)


def get_max_steps(intent: Intent) -> int:
    """Intent'e göre maksimum adım sayısını dön."""
    STEP_MAP = {
        Intent.CHAT: 1,
        Intent.KNOWLEDGE: 1,
        Intent.TIME: 1,
        Intent.CALCULATOR: 1,
        Intent.FILE: 3,
        Intent.DOCUMENT: 3,
        Intent.VISION: 2,
        Intent.WEB: 5,
        Intent.CODE: 5,
        Intent.TERMINAL: 3,
        Intent.MEMORY: 2,
        Intent.COMPLEX: 20,
    }
    return STEP_MAP.get(intent, 1)


def get_model_preference(intent: Intent) -> str:
    """Intent'e göre tercih edilen model kategorisini dön."""
    MODEL_MAP = {
        Intent.CHAT: "chat",
        Intent.KNOWLEDGE: "chat",
        Intent.TIME: "chat",
        Intent.CALCULATOR: "chat",  # Calculator tool kullanır, model gerekmez
        Intent.FILE: "chat",
        Intent.DOCUMENT: "analysis",
        Intent.VISION: "vision",
        Intent.WEB: "chat",
        Intent.CODE: "coding",
        Intent.TERMINAL: "agent",
        Intent.MEMORY: "chat",
        Intent.COMPLEX: "reasoning",
    }
    return MODEL_MAP.get(intent, "chat")


def check_network() -> str:
    """İnternet bağlantısını kontrol et.

    Returns:
        "online", "offline", "degraded"
    """
    import socket
    try:
        # DNS lookup test
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return "online"
    except (socket.timeout, OSError):
        pass

    try:
        # HTTP test
        import urllib.request
        urllib.request.urlopen("http://www.google.com", timeout=3)
        return "online"
    except Exception:
        pass

    return "offline"


def get_intent_info(text: str) -> dict:
    """Mesaj hakkında kapsamlı bilgi dön."""
    intent = classify_intent(text)
    tools = get_available_tools(intent)
    max_steps = get_max_steps(intent)
    model_pref = get_model_preference(intent)
    network = check_network()

    return {
        "text": text,
        "intent": intent.value,
        "tools": tools,
        "max_steps": max_steps,
        "model_preference": model_pref,
        "network": network,
        "use_tools": tools is not None,
    }


# ─── CLI Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_messages = [
        "Merhaba",
        "Sen kimsin?",
        "Şu an saat kaç?",
        "Bugün günlerden ne?",
        "Klasörü listele",
        "CV dosyamı oku",
        "Bu resimde ne var?",
        "İnternette UMAY hakkında bilgi ara",
        "Python kodu yaz",
        "Komut çalıştır",
        "Hatırla beni",
        "Bu projeyi incele",
        "BMW mi Mercedes mi?",
        "Python'da decorator nedir?",
        "PDF dosyasını oku",
        "Saat kaç şimdi?",
    ]

    print("=== INTENT ROUTER TEST ===\n")
    for msg in test_messages:
        info = get_intent_info(msg)
        print(f"  \"{msg}\"")
        print(f"    Intent: {info['intent']}")
        print(f"    Tools: {info['tools']}")
        print(f"    Max Steps: {info['max_steps']}")
        print(f"    Model: {info['model_preference']}")
        print(f"    Network: {info['network']}")
        print()

"""UMAY task router.

The router chooses a task category; engine.resolve_model selects an installed
local model for that category, so stale model names no longer break UMAY.
"""
from core.engine import resolve_model

RULES = [
    ("vision", ["resim", "resmi", "fotoğraf", "görsel", "ekran görüntüsü", "image", "screenshot", "analyze_image"]),
    ("reasoning", ["neden", "nasıl çalışır", "analiz et", "karşılaştır", "strateji", "plan yap", "mimari", "derinlemesine", "araştır", "nedir", "açıkla", "hakkında bilgi"]),
    ("coding", ["kod", "javascript", "typescript", "html", "css", "script", "fonksiyon", "class", "bug", "debug", "düzelt", "çalıştır", "test yaz", "build"]),
    ("analysis", ["doküman", "rapor", "özetle", "çevir", "patent", "hukuk", "sözleşme", "belge"]),
    ("agent", ["dosya oku", "dosyayı oku", "satır", "içerik", "oku ve", "okuyup", "terminal", "komut", "web_search", "ara", "gmail", "github", "browser"]),
]


def model_sec(mesaj: str) -> tuple[str | None, str]:
    text = mesaj.lower()
    for task, keywords in RULES:
        if any(k in text for k in keywords):
            return resolve_model(task), task
    return resolve_model("chat"), "chat"


if __name__ == "__main__":
    for test in ["merhaba", "python kodu yaz", "bu resmi analiz et", "neden bu mimari", "dokümanı özetle"]:
        print(test, "->", model_sec(test))

"""Local Ollama model discovery for UMAY."""
from core.engine import MODEL_PREFERENCES, installed_models, resolve_model


def list_models() -> list[str]:
    available = installed_models()
    print("\nKurulu Ollama modelleri:")
    if not available:
        print("  [YOK] Ollama çalışmıyor veya model bulunamadı.")
        return []

    for name in available:
        print(f"  [OK] {name}")

    print("\nUMAY görev eşleşmeleri:")
    for task in MODEL_PREFERENCES:
        selected = resolve_model(task)
        print(f"  {task:10} -> {selected or '[YOK]'}")
    return available


def get_model(gorev: str) -> str | None:
    return resolve_model(gorev)


if __name__ == "__main__":
    list_models()

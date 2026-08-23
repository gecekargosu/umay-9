"""UMAY CLI entry point — system check, model listing, routing test.

SAFE TO IMPORT: This module performs NO side effects at import time.
All Ollama/network calls are inside __main__ guard.
"""
import sys
import os
from pathlib import Path


def main():
    """Run system check, list models, and test routing."""
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, os.path.dirname(__file__))

    from system.system_info import system_check
    from models.model_manager import list_models
    from utils.logger import log
    from router import model_sec

    print("\n========== UMAY AI OS ==========\n")

    log("Sistem Kontrolü")
    system_check()

    print()

    log("Kurulu Modeller")
    list_models()

    print()

    log("Model Yönlendirici")
    testler = [
        "merhaba",
        "python kodu yaz",
        "bu resmi analiz et",
        "neden bu mimari",
        "dokümanı özetle",
    ]
    for t in testler:
        model, gorev = model_sec(t)
        model_name = model.split(":")[0] if model else "N/A"
        print(f"  '{t[:25]}' -> {gorev} ({model_name})")

    print("\n========== UMAY READY ==========\n")


if __name__ == "__main__":
    main()

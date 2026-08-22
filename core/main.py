import sys
import os
from pathlib import Path

# Core klasörünü path'e ekle
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
    print(f"  '{t[:25]}' -> {gorev} ({model.split(':')[0]})")

print("\n========== UMAY READY ==========\n")
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = ROOT / "config" / "settings.json"


def load_config():
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get(key, default=None):
    config = load_config()
    return config.get(key, default)


def set(key, value):
    config = load_config()
    config[key] = value
    save_config(config)
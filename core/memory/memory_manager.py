import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STATUS_FILE = ROOT / "memory" / "status.json"
TODO_FILE = ROOT / "memory" / "todo.json"
HISTORY_FILE = ROOT / "memory" / "history.json"


def load_json(file_path, default):

    if not file_path.exists():
        return default

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(file_path, data):

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def get_status():
    return load_json(STATUS_FILE, {})


def save_status(data):
    save_json(STATUS_FILE, data)


def get_todo():
    return load_json(TODO_FILE, {})


def save_todo(data):
    save_json(TODO_FILE, data)


def get_history():
    return load_json(HISTORY_FILE, [])


def save_history(data):
    save_json(HISTORY_FILE, data)
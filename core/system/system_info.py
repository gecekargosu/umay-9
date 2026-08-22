import requests

from core.engine import OLLAMA_URL, installed_models


def system_check() -> dict:
    result = {"ollama": False, "docker": False, "models": []}
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).raise_for_status()
        result["ollama"] = True
        result["models"] = installed_models()
        print(f"Ollama : OK ({len(result['models'])} model)")
    except Exception as exc:
        print(f"Ollama : ERROR - {exc}")

    try:
        import subprocess
        subprocess.run(["docker", "ps"], check=True, capture_output=True, text=True, timeout=5)
        result["docker"] = True
        print("Docker : OK")
    except Exception as exc:
        print(f"Docker : unavailable - {exc}")

    return result

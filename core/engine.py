"""UMAY local LLM engine.

Multi-provider LLM engine with Ollama as default and OpenAI-compatible
providers (MiMo, DeepSeek, etc.) as alternatives.

Falls back gracefully when primary provider is unavailable.
"""
from __future__ import annotations

import os
import time

import requests

from core.utils.logger import log
from core.utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata

# ---------------------------------------------------------------------------
# Ollama URL resolution (backward compatible)
# ---------------------------------------------------------------------------

def _resolve_ollama_url() -> str:
    """Resolve Ollama URL with smart fallback."""
    for var in ("OLLAMA_URL", "OLLAMA_BASE_URL", "OLLAMA_HOST"):
        val = os.getenv(var, "").strip()
        if val and (val.startswith("http://") or val.startswith("https://")):
            return val.rstrip("/")
    return "http://localhost:11434"


OLLAMA_URL = _resolve_ollama_url()
REQUEST_TIMEOUT = 180

# ---------------------------------------------------------------------------
# Model preferences (per task category)
# ---------------------------------------------------------------------------

MODEL_PREFERENCES = {
    # Basit sohbet → local (hizli, ucretsiz, offline)
    "chat": ["phi4-mini:latest", "qwen3:8b", "gemma2:9b", "gemma3:4b"],
    # Agent → cloud oncelikli, local fallback
    "agent": ["gpt-oss:20b-cloud", "qwen2.5-coder:7b", "qwen3:8b"],
    # Vision → local
    "vision": ["gemma3:4b", "llava:7b", "llava:latest"],
    # Reasoning → cloud oncelikli (guclu dusunme)
    "reasoning": ["gpt-oss:20b-cloud", "deepseek-r1:8b", "qwen3:8b"],
    # Coding → cloud oncelikli (guclu kodlama)
    "coding": ["gpt-oss:20b-cloud", "qwen2.5-coder:7b", "qwen3:8b"],
    # Analysis → cloud oncelikli (kapsamli analiz)
    "analysis": ["gpt-oss:20b-cloud", "granite3.3:8b", "qwen3:8b"],
    # Embedding → local
    "embedding": ["bge-m3:latest", "nomic-embed-text:latest"],
    # Backup → local
    "backup": ["gemma2:9b", "qwen3:8b", "gemma3:4b"],
}

MODELS = {k: v[0] for k, v in MODEL_PREFERENCES.items()}
DEFAULT_MODEL = MODELS["chat"]

# ---------------------------------------------------------------------------
# Ollama helpers (backward compatible)
# ---------------------------------------------------------------------------

def ollama_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return r.ok
    except requests.RequestException:
        return False



# ---------------------------------------------------------------------------
# Cloud model availability check
# ---------------------------------------------------------------------------

def _cloud_model_available(model_name: str = "gpt-oss:20b-cloud") -> bool:
    """Check if a cloud model is reachable via Ollama."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if not r.ok:
            return False
        models = r.json().get("models", [])
        for m in models:
            if m.get("name", "") == model_name:
                return bool(m.get("remote_host"))
        return False
    except Exception:
        return False


def installed_models() -> list[str]:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except (requests.RequestException, ValueError) as exc:
        log(f"[ENGINE] Ollama model listesi alınamadı: {exc}")
        return []


def _model_matches(candidate: str, installed: str) -> bool:
    return candidate == installed or candidate.split(":", 1)[0] == installed.split(":", 1)[0]


# Intent value → MODEL_PREFERENCES key mapping
_INTENT_TO_TASK = {
    "code": "coding",
    "file": "chat",
    "web": "chat",
    "computer": "agent",
    "terminal": "agent",
    "knowledge": "chat",
    "time": "chat",
    "calculator": "chat",
    "memory": "chat",
    "complex": "reasoning",
    "document": "analysis",
    "vision": "vision",
}


def resolve_model(task: str = "chat", requested: str | None = None) -> str | None:
    """Resolve best available model for task.
    
    Cloud-first for coding/reasoning/analysis, local for chat/simple tasks.
    Falls back to local if cloud unavailable.
    """
    # Map intent values to MODEL_PREFERENCES keys
    task = _INTENT_TO_TASK.get(task, task)

    available = installed_models()
    if not available:
        return None

    # If user explicitly requested a model
    if requested:
        for name in available:
            if _model_matches(requested, name):
                return name

    # Cloud-priority tasks: coding, reasoning, analysis, agent
    cloud_tasks = {"coding", "reasoning", "analysis", "agent"}
    if task in cloud_tasks and _cloud_model_available():
        for candidate in MODEL_PREFERENCES.get(task, []):
            if "cloud" in candidate.lower():
                for name in available:
                    if _model_matches(candidate, name):
                        log(f"[ENGINE] Cloud model secildi: {name} (task={task})")
                        return name

    # Local fallback for cloud tasks, or direct for local tasks
    for candidate in MODEL_PREFERENCES.get(task, MODEL_PREFERENCES["chat"]):
        for name in available:
            if _model_matches(candidate, name):
                return name

    return available[0]


# ---------------------------------------------------------------------------
# Unified engine — provider abstraction with Ollama fallback
# ---------------------------------------------------------------------------

def _get_provider_and_model(task: str, requested_model: str | None = None, mode: str = "auto"):
    """Resolve provider and model for a task.

    Priority:
    1. If mode=="local", always use Ollama regardless of PRIMARY_PROVIDER
    2. If mode=="online", prefer cloud provider if configured
    3. Environment-configured primary provider (PRIMARY_PROVIDER env var)
    4. Task-specific provider (PROVIDER_<TASK> env var)
    5. Ollama (default fallback)
    """
    from core.model_providers import (
        get_primary_provider,
        get_provider,
        OllamaProvider,
    )

    # MODE-AWARE routing
    if mode == "local":
        # LOCAL: always use Ollama regardless of PRIMARY_PROVIDER
        ollama = OllamaProvider()
        if ollama.is_available():
            return ollama, requested_model
    elif mode == "online":
        # ONLINE: prefer cloud provider if configured and available
        primary = get_primary_provider()
        if primary.name != "ollama" and primary.is_available():
            return primary, requested_model
        # Cloud not available — fall through to Ollama below

    # AUTO or ONLINE fallback: check task-specific provider override
    task_provider_env = os.getenv(f"PROVIDER_{task.upper()}", "").strip().upper()
    if task_provider_env and task_provider_env != "OLLAMA":
        provider = get_provider(task_provider_env.lower())
        if provider.is_available():
            return provider, requested_model

    # Check primary provider
    primary = get_primary_provider()
    if primary.is_available():
        return primary, requested_model

    # Fallback to Ollama
    ollama = OllamaProvider()
    if ollama.is_available():
        return ollama, requested_model

    return primary, requested_model


def _post_json(endpoint: str, payload: dict, timeout: int = REQUEST_TIMEOUT) -> dict:
    """Direct Ollama HTTP call (backward compatible)."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}{endpoint}",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        raise RuntimeError(
            "Ollama'ya bağlanılamadı. Ollama çalışıyor mu? "
            f"Kontrol: {OLLAMA_URL}"
        )
    except requests.Timeout:
        raise RuntimeError(
            f"Ollama {timeout} saniye içinde cevap vermedi. Model çok büyük/yavaş olabilir."
        )
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", "")
        except Exception:
            pass
        raise RuntimeError(f"Ollama HTTP hatası: {detail or exc}")
    except ValueError as exc:
        raise RuntimeError(f"Ollama geçersiz JSON döndürdü: {exc}")


def ask(prompt: str, model: str | None = None, task: str = "chat") -> str:
    """Simple prompt → response. Uses best available provider."""
    try:
        provider, resolved_model = _get_provider_and_model(task, model)
        log(f"[ENGINE] {provider.name} provider kullanılıyor...")
        return provider.ask(prompt, model=resolved_model)
    except Exception as exc:
        log(f"[ENGINE] Provider hatası, Ollama fallback deneniyor: {exc}")
        # Direct Ollama fallback
        selected = resolve_model(task, model)
        if not selected:
            return "Hata: Hiçbir model çalışmıyor."
        try:
            result = _post_json("/api/generate", {"model": selected, "prompt": prompt, "stream": False})
            return result.get("response", "Cevap alınamadı.").strip()
        except Exception as exc2:
            return f"Hata: {exc2}"


def chat(
    messages: list[dict],
    model: str | None = None,
    ajan: str = "umay",
    task: str = "chat",
    tools: list[dict] | None = None,
    raw: bool = False,
    mode: str = "auto",
) -> str | dict:
    """Multi-provider chat with tool calling support.

    Tries configured provider first, falls back to Ollama.
    mode: 'local' forces Ollama, 'online' prefers cloud, 'auto' uses primary.
    """
    son_mesaj = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
        "?",
    )
    action_id = eylem_baslat(
        ajan=ajan,
        niyet=son_mesaj[:80],
        plan=f"Model chat çağrısı ({task})",
        model=model or "auto",
    )
    baslangic = time.time()

    # Try provider abstraction first
    try:
        provider, resolved_model = _get_provider_and_model(task, model, mode=mode)
        log(f"[ENGINE] {provider.name} ile sohbet başlatılıyor (mode={mode})...")
        result = provider.chat(
            messages=messages,
            model=resolved_model,
            tools=tools,
            timeout=REQUEST_TIMEOUT,
        )
        content = result.get("content", "")
        tool_calls = result.get("tool_calls")
        usage = result.get("usage")  # STEP-04.3: real token usage from provider

        if tools and tool_calls:
            eylem_tamamla(
                action_id,
                sonuc=f"{len(tool_calls)} tool call via {provider.name}",
                test_gecti=True,
                sure_sn=time.time() - baslangic,
            )
            resp = {"message": {"content": content, "tool_calls": tool_calls}}
            if usage:
                resp["usage"] = usage
            return resp

        if content:
            eylem_tamamla(action_id, sonuc=content[:100], test_gecti=True, sure_sn=time.time() - baslangic)
            # When tools are passed, always return dict format for backward compat
            resp = {"message": {"content": content}}
            if usage:
                resp["usage"] = usage
            if tools:
                return resp
            if raw:
                return resp
            return content

        raise RuntimeError("Model boş cevap döndürdü.")

    except Exception as provider_exc:
        log(f"[ENGINE] {provider.name if 'provider' in dir() else 'provider'} hatası: {provider_exc}")
        log("[ENGINE] Ollama fallback deneniyor...")

        # Direct Ollama fallback
        selected = resolve_model(task, model)
        if not selected:
            eylem_hata(action_id, hata="Hiçbir model çalışmıyor")
            return "Hata: Ollama çalışmıyor veya uygun model kurulu değil."

        try:
            log(f"[ENGINE] {selected} ile sohbet başlatılıyor (fallback)...")
            payload: dict = {"model": selected, "messages": messages, "stream": False}
            if tools:
                payload["tools"] = tools
            result = _post_json("/api/chat", payload)
            message = result.get("message", {})

            if tools and message.get("tool_calls"):
                eylem_tamamla(
                    action_id,
                    sonuc=f"{len(message['tool_calls'])} tool call (ollama fallback)",
                    test_gecti=True,
                    sure_sn=time.time() - baslangic,
                )
                return {"message": message}

            cevap = message.get("content", "").strip()
            if not cevap:
                raise RuntimeError("Model boş cevap döndürdü.")
            eylem_tamamla(action_id, sonuc=cevap[:100], test_gecti=True, sure_sn=time.time() - baslangic)
            # STEP-04.3: Extract real usage from Ollama fallback response
            from core.token_budget import usage_from_ollama_response
            fallback_usage = usage_from_ollama_response(result)
            resp = {"message": message}
            if fallback_usage:
                resp["usage"] = fallback_usage.as_dict()
            # When tools are passed, always return dict format for backward compat
            if tools:
                return resp
            if raw:
                return resp
            return cevap

        except Exception as ollama_exc:
            log(f"[ENGINE] Ollama fallback hatası: {ollama_exc}")
            eylem_hata(action_id, hata=str(ollama_exc))
            return f"Hata: {ollama_exc}"


if __name__ == "__main__":
    print(ask("Merhaba. Kısaca kendini tanıt.", task="chat"))

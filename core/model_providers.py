"""UMAY Model Provider Abstraction Layer.

Supports multiple LLM providers through a unified interface:
- Ollama (local, default)
- OpenAI-compatible APIs (MiMo, DeepSeek, GPT, Claude, etc.)

Each provider implements the same simple interface:
  provider.chat(messages, model, tools) -> response
  provider.is_available() -> bool
  provider.list_models() -> list[str]
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

from core.utils.logger import log

# ---------------------------------------------------------------------------
# Abstract Provider
# ---------------------------------------------------------------------------

class ModelProvider(ABC):
    """Base class for all model providers."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is reachable."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return list of available model names."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        tools: list[dict] | None = None,
        timeout: int = 180,
    ) -> dict:
        """Send a chat request. Returns {"content": str} or {"content": str, "tool_calls": list}."""

    def ask(self, prompt: str, model: str | None = None, timeout: int = 180) -> str:
        """Simple prompt → response convenience method."""
        result = self.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            timeout=timeout,
        )
        return result.get("content", "")


# ---------------------------------------------------------------------------
# Ollama Provider (local)
# ---------------------------------------------------------------------------

class OllamaProvider(ModelProvider):
    """Local Ollama LLM provider."""

    name = "ollama"

    def __init__(self, base_url: str | None = None):
        self._static_url = base_url

    @property
    def base_url(self) -> str:
        """Resolve URL dynamically — supports monkeypatching engine.OLLAMA_URL."""
        if self._static_url:
            return self._static_url
        try:
            from core.engine import OLLAMA_URL
            return OLLAMA_URL
        except ImportError:
            pass
        for var in ("OLLAMA_URL", "OLLAMA_BASE_URL", "OLLAMA_HOST"):
            val = os.getenv(var, "").strip()
            if val and (val.startswith("http://") or val.startswith("https://")):
                return val.rstrip("/")
        return "http://localhost:11434"

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.ok
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=10)
            r.raise_for_status()
            return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
        except Exception:
            return []

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        tools: list[dict] | None = None,
        timeout: int = 180,
    ) -> dict:
        payload: dict[str, Any] = {
            "model": model or "phi4-mini:latest",
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=timeout)
            r.raise_for_status()
            result = r.json()
            message = result.get("message", {})
            content = message.get("content", "").strip()
            tool_calls = message.get("tool_calls")

            # STEP-04.3: Extract real token usage from Ollama response.
            # Ollama includes prompt_eval_count (input) and eval_count
            # (output) in its non-streaming response — real provider-reported
            # usage, not an estimate. Previously these fields were discarded.
            from core.token_budget import usage_from_ollama_response
            usage = usage_from_ollama_response(result)

            resp = {"content": content}
            if tool_calls:
                resp["tool_calls"] = tool_calls
            if usage:
                resp["usage"] = usage.as_dict()
            return resp
        except requests.ConnectionError:
            raise RuntimeError(f"Ollama'ya bağlanılamadı: {self.base_url}")
        except requests.Timeout:
            raise RuntimeError(f"Ollama {timeout}s timeout")
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("error", "")
            except Exception:
                pass
            raise RuntimeError(f"Ollama HTTP: {detail or exc}")


# ---------------------------------------------------------------------------
# OpenAI-Compatible Provider (MiMo, DeepSeek, GPT, Claude, etc.)
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider(ModelProvider):
    """Provider for any OpenAI-compatible API (MiMo, DeepSeek, etc.).

    Environment variables:
      {PREFIX}_API_KEY    - API key
      {PREFIX}_BASE_URL   - API base URL (e.g. https://api.example.com/v1)
      {PREFIX}_MODEL      - Default model name

    Example for MiMo:
      MIMO_API_KEY=sk-...
      MIMO_BASE_URL=https://api.mimo.com/v1
      MIMO_MODEL=mimo-reasoning-7b
    """

    name: str = "openai_compatible"

    def __init__(
        self,
        prefix: str = "MIMO",
        provider_name: str | None = None,
    ):
        self.prefix = prefix
        self.name = provider_name or prefix.lower()
        self.api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
        self.base_url = os.getenv(f"{prefix}_BASE_URL", "").strip().rstrip("/")
        self.default_model = os.getenv(f"{prefix}_MODEL", "").strip()

    def is_available(self) -> bool:
        if not self.api_key or not self.base_url:
            return False
        try:
            r = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10)
            return r.ok
        except Exception:
            # Even if /models endpoint fails, try a simple request
            return bool(self.api_key and self.base_url)

    def list_models(self) -> list[str]:
        try:
            r = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10)
            r.raise_for_status()
            data = r.json()
            return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        except Exception:
            return [self.default_model] if self.default_model else []

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        tools: list[dict] | None = None,
        timeout: int = 180,
    ) -> dict:
        if not self.api_key or not self.base_url:
            raise RuntimeError(f"{self.name} yapılandırılmamış. API key ve base URL gerekli.")

        selected_model = model or self.default_model
        if not selected_model:
            raise RuntimeError(f"{self.name} model belirtilmedi. {self.prefix}_MODEL ayarla.")

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout)
            r.raise_for_status()
            result = r.json()
            choice = result.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "") or ""
            tool_calls_raw = message.get("tool_calls")

            tool_calls = None
            if tool_calls_raw:
                tool_calls = []
                for tc in tool_calls_raw:
                    func = tc.get("function", {})
                    args = func.get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"raw": args}
                    tool_calls.append({
                        "function": {
                            "name": func.get("name", ""),
                            "arguments": args,
                        }
                    })

            if tool_calls:
                return {"content": content, "tool_calls": tool_calls}
            return {"content": content.strip()}
        except requests.ConnectionError:
            raise RuntimeError(f"{self.name} API'ye bağlanılamadı: {self.base_url}")
        except requests.Timeout:
            raise RuntimeError(f"{self.name} {timeout}s timeout")
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            raise RuntimeError(f"{self.name} HTTP: {detail or exc}")


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------

# Global provider instances (lazy initialized)
_providers: dict[str, ModelProvider] = {}


def get_provider(name: str) -> ModelProvider:
    """Get a provider by name. Creates instance if needed."""
    if name not in _providers:
        if name == "ollama":
            _providers[name] = OllamaProvider()
        elif name.upper() == os.getenv("PRIMARY_PROVIDER", "OLLAMA").upper():
            # Check if there's a configured primary provider
            prefix = os.getenv("PRIMARY_PROVIDER", "OLLAMA")
            if prefix.upper() == "OLLAMA":
                _providers[name] = OllamaProvider()
            else:
                _providers[name] = OpenAICompatibleProvider(prefix=prefix, provider_name=name)
        else:
            # Try as OpenAI-compatible with prefix = name.upper()
            _providers[name] = OpenAICompatibleProvider(prefix=name.upper(), provider_name=name)
    return _providers[name]


def get_all_providers() -> list[ModelProvider]:
    """Return all configured providers."""
    providers = [OllamaProvider()]

    # Check for additional providers via env
    extra_prefixes = os.getenv("EXTRA_PROVIDERS", "").split(",")
    for prefix in extra_prefixes:
        prefix = prefix.strip().upper()
        if prefix and prefix != "OLLAMA":
            providers.append(OpenAICompatibleProvider(prefix=prefix, provider_name=prefix.lower()))

    return providers


def get_primary_provider() -> ModelProvider:
    """Get the primary (default) provider."""
    primary = os.getenv("PRIMARY_PROVIDER", "OLLAMA").strip().upper()
    if primary == "OLLAMA":
        return get_provider("ollama")
    else:
        return get_provider(primary.lower())


def resolve_provider_for_task(task: str) -> tuple[ModelProvider, str | None]:
    """Resolve which provider and model to use for a given task.

    Returns (provider, model_name_or_None).
    """
    # Check task-specific provider override
    task_provider = os.getenv(f"PROVIDER_{task.upper()}", "").strip().upper()
    if task_provider:
        provider = get_provider(task_provider.lower())
        if provider.is_available():
            return provider, None  # Let provider use its default model

    # Default: use primary provider
    primary = get_primary_provider()
    if primary.is_available():
        return primary, None

    # Fallback: try Ollama
    ollama = get_provider("ollama")
    if ollama.is_available():
        return ollama, None

    return primary, None

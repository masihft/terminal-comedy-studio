"""Shared implementation for every OpenAI-compatible chat endpoint."""

from __future__ import annotations

from typing import Any

from .http import get_json, model_ids, request_json, stream_text
from .provider import AIProvider, ProviderNotConfigured


class OpenAICompatibleProvider(AIProvider):
    """OmniRoute, OpenRouter, OpenAI and any local server all speak this."""

    def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.api_key}"}

    def _url(self) -> str:
        if not self.base_url:
            raise ProviderNotConfigured(f"{self.label}: set {self.base_url_env}.")
        if not self.api_key and self.needs_key:
            raise ProviderNotConfigured(f"{self.label}: set {self.key_env}.")
        return f"{self.base_url}/chat/completions"

    def list_models(self, timeout: float = 10.0) -> list[str]:
        if not self.base_url:
            raise ProviderNotConfigured(f"{self.label}: set {self.base_url_env}.")
        return model_ids(get_json(f"{self.base_url}/models", self._headers(), timeout))

    def _payload(self, messages: list[dict[str, str]], temperature: float, max_tokens: int) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    @staticmethod
    def _delta(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0] or {}
        delta = first.get("delta")
        if isinstance(delta, dict):
            return str(delta.get("content") or "")
        message = first.get("message")
        if isinstance(message, dict):
            return str(message.get("content") or "")
        return str(first.get("text") or "")

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.9,
        max_tokens: int = 400,
        on_delta=None,
    ) -> str:
        url = self._url()
        payload = self._payload(messages, temperature, max_tokens)
        headers = self._headers()
        if on_delta is None:
            return self._delta(request_json(url, payload, headers, self.settings.timeout))
        text = stream_text(url, payload, headers, self.settings.timeout, self._delta, on_delta)
        if not text:
            return self._delta(request_json(url, payload, headers, self.settings.timeout))
        return text

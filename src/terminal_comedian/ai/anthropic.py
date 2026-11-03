"""Anthropic's messages API."""

from __future__ import annotations

from typing import Any

from .http import request_json, stream_text
from .provider import AIProvider, ProviderNotConfigured, register


@register
class AnthropicProvider(AIProvider):
    id = "anthropic"
    label = "Anthropic"
    key_env = "ANTHROPIC_API_KEY"
    base_url_env = "ANTHROPIC_BASE_URL"
    model_env = "ANTHROPIC_MODEL"
    default_model = "claude-sonnet-4-5"
    default_base_url = "https://api.anthropic.com"
    docs_url = "https://console.anthropic.com/settings/keys"

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderNotConfigured(f"{self.label}: set {self.key_env}.")
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    def _split(self, messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        rest = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]
        return system, rest or [{"role": "user", "content": "Say hello."}]

    def _payload(self, messages, temperature, max_tokens) -> dict[str, Any]:
        system, rest = self._split(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": rest,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system
        return payload

    @staticmethod
    def _delta(data: dict[str, Any]) -> str:
        if data.get("type") == "content_block_delta":
            return str((data.get("delta") or {}).get("text") or "")
        content = data.get("content")
        if isinstance(content, list):
            return "".join(str(block.get("text") or "") for block in content if isinstance(block, dict))
        return ""

    def complete(self, messages, *, temperature=0.9, max_tokens=400, on_delta=None) -> str:
        url = f"{self.base_url}/v1/messages"
        payload = self._payload(messages, temperature, max_tokens)
        headers = self._headers()
        if on_delta is None:
            return self._delta(request_json(url, payload, headers, self.settings.timeout))
        text = stream_text(url, payload, headers, self.settings.timeout, self._delta, on_delta)
        return text or self._delta(request_json(url, payload, headers, self.settings.timeout))

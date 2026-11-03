"""OpenRouter: one key, many upstream models."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider
from .provider import register


@register
class OpenRouterProvider(OpenAICompatibleProvider):
    id = "openrouter"
    label = "OpenRouter"
    key_env = "OPENROUTER_API_KEY"
    base_url_env = "OPENROUTER_BASE_URL"
    model_env = "OPENROUTER_MODEL"
    default_model = "openai/gpt-4o-mini"
    default_base_url = "https://openrouter.ai/api/v1"
    docs_url = "https://openrouter.ai/keys"

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self.api_key}",
            "x-app-name": "Terminal Comedy Studio",
        }

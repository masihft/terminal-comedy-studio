"""OpenAI's own API."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider
from .provider import register


@register
class OpenAIProvider(OpenAICompatibleProvider):
    id = "openai"
    label = "OpenAI"
    key_env = "OPENAI_API_KEY"
    base_url_env = "OPENAI_BASE_URL"
    model_env = "OPENAI_MODEL"
    default_model = "gpt-4o-mini"
    default_base_url = "https://api.openai.com/v1"
    docs_url = "https://platform.openai.com/api-keys"

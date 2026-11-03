"""Any local server exposing /v1/chat/completions (llama.cpp, vLLM, LM Studio…)."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider
from .provider import register


@register
class LocalProvider(OpenAICompatibleProvider):
    id = "local"
    label = "Local server"
    key_env = "LOCAL_API_KEY"
    base_url_env = "LOCAL_BASE_URL"
    model_env = "LOCAL_MODEL"
    default_model = "local-model"
    default_base_url = ""
    needs_key = False
    docs_url = ""

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"authorization": f"Bearer {self.api_key}"}
        return {}

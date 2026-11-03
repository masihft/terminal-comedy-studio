"""OmniRoute: a local gateway that speaks the OpenAI dialect.

The base URL is never assumed — it comes from configuration, because this
provider must stay optional.
"""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider
from .provider import register


@register
class OmniRouteProvider(OpenAICompatibleProvider):
    id = "omniroute"
    label = "OmniRoute"
    key_env = "OMNIROUTE_API_KEY"
    base_url_env = "OMNIROUTE_BASE_URL"
    model_env = "OMNIROUTE_MODEL"
    default_model = ""
    default_base_url = ""
    docs_url = ""

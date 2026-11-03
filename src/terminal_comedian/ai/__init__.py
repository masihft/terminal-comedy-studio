"""Providers the comedian can talk to.

Each one declares the NAME of the environment variable holding its key; the
key value itself is never stored, printed or committed.
"""

from __future__ import annotations

from .anthropic import AnthropicProvider
from .local import LocalProvider
from .omniroute import OmniRouteProvider
from .openai import OpenAIProvider
from .openai_compatible import OpenAICompatibleProvider
from .openrouter import OpenRouterProvider
from .provider import (
    AIError,
    AIProvider,
    AIResponse,
    ProviderNotConfigured,
    ProviderUnavailable,
    create_provider,
    parse_comedy_response,
    provider_ids,
    register,
)

__all__ = [
    "AIError",
    "AIProvider",
    "AIResponse",
    "AnthropicProvider",
    "LocalProvider",
    "OmniRouteProvider",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "ProviderNotConfigured",
    "ProviderUnavailable",
    "create_provider",
    "parse_comedy_response",
    "provider_ids",
    "register",
]

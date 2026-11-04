"""The provider seam: one small interface, many interchangeable engines.

Nothing in the comedy or presentation layer may import a concrete provider.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..character.states import Emotion
from ..config.settings import Settings

DeltaCallback = Callable[[str], None]

DEFAULT_DURATION = 2.6
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_CONTROL_KEYS = {"emotion", "animation", "duration"}


class AIError(Exception):
    """Any failure while talking to a model, always safe to print."""


class ProviderNotConfigured(AIError):
    pass


class ProviderUnavailable(AIError):
    pass


@dataclass
class AIResponse:
    """What the comedian actually performs, not just what the model said."""

    text: str = ""
    emotion: Emotion = Emotion.NEUTRAL
    animation: str = "idle"
    duration: float = DEFAULT_DURATION
    provider: str = ""
    model: str = ""
    raw: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "emotion": self.emotion.value,
            "animation": self.animation,
            "duration": self.duration,
        }


def _balanced_object(text: str) -> str | None:
    """Return the first brace-balanced JSON object, ignoring anything after it."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    inside = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if inside:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                inside = False
            continue
        if char == '"':
            inside = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _candidates(text: str) -> list[str]:
    out = [block.strip() for block in _FENCE.findall(text)]
    leading = _balanced_object(text)
    if leading:
        out.append(leading)
    out.append(text.strip())
    return [c for c in out if c]


json_candidates = _candidates  # public name for the harness, which reads tool calls the same way


def _as_float(value: Any, fallback: float) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    return number if 0.25 <= number <= 20 else fallback


def parse_comedy_response(text: str) -> AIResponse:
    """Read the structured contract defensively.

    Models drift: they wrap JSON in prose, omit fields, or answer with plain
    text. Every one of those still has to produce a performance, so anything
    unusable falls back to the raw text instead of raising.
    """
    for candidate in _candidates(text):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        spoken = data.get("text") or data.get("joke") or data.get("line") or ""
        if not isinstance(spoken, str) or not spoken.strip():
            continue
        response = AIResponse(text=spoken.strip())
        emotion = str(data.get("emotion", "")).strip().lower()
        if emotion:
            try:
                response.emotion = Emotion(emotion)
            except ValueError:
                response.emotion = Emotion.NEUTRAL
        animation = str(data.get("animation", "")).strip().lower()
        if animation:
            response.animation = animation
        response.duration = _as_float(data.get("duration"), DEFAULT_DURATION)
        response.raw = text
        response.meta = {k: v for k, v in data.items() if k not in _CONTROL_KEYS}
        return response
    return AIResponse(text=text.strip(), raw=text)


class AIProvider(ABC):
    """Transport only: messages in, text out. No comedy knowledge."""

    id: str = ""
    label: str = ""
    key_env: str = ""
    base_url_env: str = ""
    model_env: str = ""
    default_model: str = ""
    default_base_url: str = ""
    needs_key: bool = True
    docs_url: str = ""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()

    @property
    def api_key(self) -> str:
        return self.settings.get(self.key_env) if self.key_env else ""

    @property
    def base_url(self) -> str:
        return (self.settings.get(self.base_url_env) or self.default_base_url).rstrip("/")

    @property
    def model(self) -> str:
        return (
            self.settings.get(self.model_env)
            or self.settings.model
            or self.default_model
        )

    @property
    def is_configured(self) -> bool:
        if self.needs_key and not self.api_key:
            return False
        return bool(self.base_url or self.default_base_url)

    def missing(self) -> str:
        """A one-line hint telling the user exactly what to set."""
        parts = []
        if self.needs_key and not self.api_key:
            parts.append(self.key_env)
        if self.base_url_env and not self.settings.get(self.base_url_env):
            parts.append(f"{self.base_url_env} (for example https://example.com/v1)")
        if self.model_env and not self.model:
            parts.append(self.model_env)
        return ", ".join(parts)

    def list_models(self, timeout: float = 10.0) -> list[str]:
        """Model ids the provider offers; empty when it cannot say."""
        return []

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.9,
        max_tokens: int = 400,
        on_delta: DeltaCallback | None = None,
    ) -> str:
        """Return the assistant text, calling on_delta for each chunk."""

    def generate(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """The interface shape promised in AGENTS.md: prompt in, structured dict out."""
        messages = list((context or {}).get("messages") or [])
        messages.append({"role": "user", "content": prompt})
        response = self.generate_messages(messages, context)
        return response.to_dict()

    def generate_messages(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any] | None = None,
    ) -> AIResponse:
        context = context or {}
        text = self.complete(
            messages,
            temperature=float(context.get("temperature", self.settings.temperature)),
            max_tokens=int(context.get("max_tokens", self.settings.max_tokens)),
            on_delta=context.get("on_delta"),
        )
        if not text.strip():
            raise AIError(f"{self.label} returned an empty reply.")
        response = parse_comedy_response(text)
        response.provider = self.id
        response.model = self.model
        return response

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} {self.id} model={self.model!r}>"


REGISTRY: dict[str, type[AIProvider]] = {}


def register(provider_cls: type[AIProvider]) -> type[AIProvider]:
    existing = REGISTRY.get(provider_cls.id)
    if existing is not None and existing is not provider_cls:
        raise ValueError(f"duplicate provider id: {provider_cls.id}")
    REGISTRY[provider_cls.id] = provider_cls
    return provider_cls


def provider_ids() -> list[str]:
    return sorted(REGISTRY)


def create_provider(settings: Settings) -> AIProvider | None:
    """Build the configured provider, or None for the offline stage."""
    from . import anthropic as _anthropic  # noqa: F401  (registers)
    from . import local as _local  # noqa: F401
    from . import omniroute as _omniroute  # noqa: F401
    from . import openai as _openai  # noqa: F401
    from . import openrouter as _openrouter  # noqa: F401

    wanted = settings.provider
    if wanted in {"", "none", "offline"}:
        return None
    provider_cls = REGISTRY.get(wanted)
    if provider_cls is None:
        raise ProviderNotConfigured(
            f"unknown AI_PROVIDER '{wanted}'. choose one of: {', '.join(provider_ids())}, offline"
        )
    return provider_cls(settings)

"""Minimal stdlib HTTP for OpenAI-compatible and Anthropic chat endpoints."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .provider import AIError, ProviderUnavailable

USER_AGENT = "terminal-comedy-studio"


def _describe(url: str, error: urllib.error.URLError) -> str:
    host = url.split("//", 1)[-1]
    if isinstance(error, urllib.error.HTTPError):
        return f"{host} answered HTTP {error.code}"
    reason = getattr(error, "reason", error)
    return f"{host} is unreachable ({reason})"


def request_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"content-type": "application/json", "user-agent": USER_AGENT, **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:400] if error.fp else ""
        raise _http_error(url, error, detail) from error
    except urllib.error.URLError as error:
        raise ProviderUnavailable(_describe(url, error)) from error
    except json.JSONDecodeError as error:
        raise AIError(f"{url.split('//', 1)[-1]} returned something that is not JSON") from error


def _http_error(url: str, error: urllib.error.HTTPError, detail: str) -> AIError:
    host = url.split("//", 1)[-1]
    if error.code in (401, 403):
        return ProviderUnavailable(f"{host} refused the key (HTTP {error.code}). Check the API key in .env.")
    if error.code == 429:
        return ProviderUnavailable(f"{host} is rate limited (HTTP 429). Try again in a moment.")
    if error.code == 404:
        return ProviderUnavailable(
            f"{host} has no such endpoint (HTTP 404). Check the base URL and model name."
        )
    if error.code >= 500:
        return ProviderUnavailable(f"{host} is having a bad day (HTTP {error.code}).")
    return AIError(f"{host} answered HTTP {error.code}: {detail.strip()}")


def stream_text(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    extract: Callable[[dict[str, Any]], str],
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """Read an SSE chat stream, forwarding deltas, and return the full text."""
    body = json.dumps({**payload, "stream": True}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "accept": "text/event-stream",
            "content-type": "application/json",
            "user-agent": USER_AGENT,
            **headers,
        },
        method="POST",
    )
    collected: list[str] = []
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if "event-stream" not in response.headers.get("content-type", ""):
                data = json.loads(response.read().decode("utf-8", "replace") or "{}")
                piece = extract(data)
                if piece:
                    collected.append(piece)
                    if on_delta:
                        on_delta(piece)
                return "".join(collected)
            for raw in response:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if not chunk or chunk == "[DONE]":
                    if chunk == "[DONE]":
                        break
                    continue
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                piece = extract(data)
                if not piece:
                    continue
                collected.append(piece)
                if on_delta:
                    on_delta(piece)
    except urllib.error.HTTPError as error:
        raise _http_error(url, error, error.read().decode("utf-8", "replace")[:400] if error.fp else "") from error
    except urllib.error.URLError as error:
        raise ProviderUnavailable(_describe(url, error)) from error
    return "".join(collected)

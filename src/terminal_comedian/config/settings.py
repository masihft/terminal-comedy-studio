"""Configuration loaded from the environment and an optional .env file."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .credentials import user_env_path

_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_env_file(path: Path) -> dict[str, str]:
    """Read KEY=value pairs, ignoring comments and blank lines."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        values[key] = value
    return values


def default_env_paths(start: Path | None = None) -> list[Path]:
    here = (start or Path.cwd()).resolve()
    paths = [here / ".env"]
    paths.append(user_env_path())
    paths.append(Path.home() / ".terminal-comedy-studio" / ".env")
    return paths


@dataclass
class Settings:
    """Everything the comedian needs to know, resolved once at start-up.

    Real environment variables always win over .env files, so a shell export
    is enough to try another provider without editing anything.
    """

    environ: dict[str, str] = field(default_factory=dict)
    provider: str = "offline"
    model: str = ""
    language: str = "en"
    character: str = "default"
    timeout: float = 30.0
    temperature: float = 0.9
    max_tokens: int = 400
    color: bool = True

    @classmethod
    def load(cls, cwd: Path | None = None, environ: dict[str, str] | None = None) -> "Settings":
        merged: dict[str, str] = {}
        for path in default_env_paths(cwd):
            merged.update(parse_env_file(path))
        merged.update(os.environ if environ is None else environ)
        number = _number
        return cls(
            environ=merged,
            provider=(merged.get("AI_PROVIDER") or "offline").strip().lower(),
            model=(merged.get("AI_MODEL") or "").strip(),
            language=(merged.get("LANGUAGE") or "en").strip().lower(),
            character=(merged.get("COMEDIAN_CHARACTER") or "default").strip().lower(),
            timeout=number(merged.get("COMEDIAN_TIMEOUT"), 30.0),
            temperature=number(merged.get("COMEDIAN_TEMPERATURE"), 0.9),
            max_tokens=int(number(merged.get("COMEDIAN_MAX_TOKENS"), 400)),
            color=not merged.get("NO_COLOR"),
        )

    def get(self, key: str, fallback: str = "") -> str:
        return (self.environ.get(key) or fallback).strip()

    def has_key(self, key: str) -> bool:
        return bool(self.get(key))


def _number(value: str | None, fallback: float) -> float:
    try:
        return float(value) if value else fallback
    except ValueError:
        return fallback

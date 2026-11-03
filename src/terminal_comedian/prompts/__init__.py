"""Roles: markdown files with front-matter, the way aichat ships its personas.

A mode is data, not code — adding a comedian or a new bit should not require
touching the engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_DIR = Path(__file__).parent
_METADATA = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FIELD = re.compile(r"^([a-z_]+):\s*(.*)$")

DEFAULT_MODE = "stage"
MODES = ("stage", "standup", "chat", "roast", "story", "random")


@dataclass(frozen=True)
class Role:
    name: str
    description: str
    prompt: str
    temperature: float = 0.95
    max_tokens: int = 400

    def render(self, variables: dict[str, str]) -> str:
        text = self.prompt
        for key, value in variables.items():
            text = text.replace(key, value)
        return text


def _parse(path: Path) -> Role:
    raw = path.read_text(encoding="utf-8")
    match = _METADATA.match(raw)
    fields: dict[str, str] = {}
    body = raw
    if match:
        body = raw[match.end() :]
        for line in match.group(1).splitlines():
            field = _FIELD.match(line.strip())
            if field:
                fields[field.group(1)] = field.group(2).strip()
    return Role(
        name=fields.get("name", path.stem),
        description=fields.get("description", ""),
        prompt=body.strip(),
        temperature=float(fields.get("temperature", "0.95")),
        max_tokens=int(fields.get("max_tokens", "400")),
    )


_CACHE: dict[str, Role] = {}


def load_role(mode: str) -> Role:
    if mode not in MODES:
        raise KeyError(f"unknown mode '{mode}'. choose: {', '.join(MODES)}")
    if mode not in _CACHE:
        _CACHE[mode] = _parse(_DIR / f"{mode}.md")
    return _CACHE[mode]


def load_system() -> str:
    return (_DIR / "system.md").read_text(encoding="utf-8").strip()


def mode_help() -> list[tuple[str, str]]:
    return [(mode, load_role(mode).description) for mode in MODES]

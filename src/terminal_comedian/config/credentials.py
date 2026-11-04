"""Write connection settings to the user's own config file, never the repository.

The file is the same per-user .env that Settings already reads, so a key saved
here works on the next start with no other step. It is created owner-only.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LINE_KEY = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def user_env_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "terminal-comedy-studio" / ".env"


def _quote(value: str) -> str:
    if any(char in value for char in "\r\n\x00"):
        raise ValueError("a value cannot contain a line break")
    if value and not re.search(r"[\s#'\"]", value):
        return value
    if '"' in value:
        return f"'{value}'"
    return f'"{value}"'


def save_values(values: dict[str, str | None], path: Path | None = None) -> Path:
    """Set (or, with None, remove) KEY=value lines, keeping every other line."""
    target = path or user_env_path()
    for key in values:
        if not _KEY.match(key):
            raise ValueError(f"not a valid variable name: {key!r}")
    lines = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
    pending = dict(values)
    kept: list[str] = []
    for line in lines:
        match = _LINE_KEY.match(line)
        if match and match.group(1) in values:
            value = pending.pop(match.group(1), None)
            if value is not None:
                kept.append(f"{match.group(1)}={_quote(value)}")
            continue
        kept.append(line)
    kept += [f"{key}={_quote(value)}" for key, value in pending.items() if value is not None]
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=target.parent, prefix=".env.")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write("\n".join(kept) + "\n")
        os.chmod(temp, 0o600)  # owner-only: this file holds API keys
        os.replace(temp, target)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
    return target

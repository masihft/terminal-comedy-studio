"""Every test runs against an empty home, so a developer's own /connect never leaks in."""

from __future__ import annotations

import os

import pytest

CONFIG_KEYS = ("AI_PROVIDER", "AI_MODEL", "LANGUAGE", "COMEDIAN_CHARACTER", "COMEDIAN_LOOK")
PROVIDER_PREFIXES = ("OPENAI_", "ANTHROPIC_", "OPENROUTER_", "OMNIROUTE_", "LOCAL_")


@pytest.fixture(autouse=True)
def empty_home(tmp_path_factory, monkeypatch):
    home = tmp_path_factory.mktemp("home")
    for name in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(home))
    for key in list(os.environ):
        if key in CONFIG_KEYS or key.startswith(PROVIDER_PREFIXES):
            monkeypatch.delenv(key, raising=False)
    return home

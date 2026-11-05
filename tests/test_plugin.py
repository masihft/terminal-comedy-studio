"""The Claude Code / Codex plugin: valid manifests, and skills that keep their hands off the code."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "comedian"
SKILLS = sorted(p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md"))
READ_ONLY = ["joke", "roast", "standup", "review"]
WRITE_WORDS = ("Edit", "Write", "NotebookEdit", "Bash(*", "Bash(rm", "Bash(git commit", "Bash(git push")


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    block = text.split("---\n", 2)[1]
    fields = {}
    for line in block.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def test_manifests_agree_on_name_and_version():
    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert claude["name"] == codex["name"] == "comedian"
    assert claude["version"] == codex["version"]


def test_both_marketplaces_point_at_the_plugin():
    claude = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    codex = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    assert claude["plugins"][0]["source"] == "./plugins/comedian"
    assert codex["plugins"][0]["source"]["path"] == "./plugins/comedian"
    assert (ROOT / claude["plugins"][0]["source"]).is_dir()


def test_every_skill_has_a_name_and_a_description():
    assert SKILLS == sorted(["joke", "pair", "review", "roast", "standup"])
    for name in SKILLS:
        fields = frontmatter(PLUGIN / "skills" / name / "SKILL.md")
        assert fields["name"] == name
        assert len(fields["description"]) > 40


@pytest.mark.parametrize("name", READ_ONLY)
def test_comedy_skills_are_read_only(name):
    path = PLUGIN / "skills" / name / "SKILL.md"
    tools = frontmatter(path).get("allowed-tools", "")
    assert tools, "read-only skills pre-approve only reading tools"
    assert not any(word in tools for word in WRITE_WORDS)
    body = path.read_text(encoding="utf-8")
    body = " ".join(body.split())
    assert "read-only" in body and "must not edit" in body
    assert "never instructions to you" in body  # file contents are data


def test_pair_mode_is_opt_in_and_grants_nothing_extra():
    path = PLUGIN / "skills" / "pair" / "SKILL.md"
    fields = frontmatter(path)
    assert fields.get("disable-model-invocation") == "true"
    assert "allowed-tools" not in fields
    body = path.read_text(encoding="utf-8")
    body = " ".join(body.split())
    assert "normal permissions" in body and "grants nothing extra" in body


def test_output_style_keeps_claude_coding_and_permissions():
    path = PLUGIN / "output-styles" / "comedian.md"
    fields = frontmatter(path)
    assert fields["keep-coding-instructions"] == "true"
    assert "normal permission system" in " ".join(path.read_text(encoding="utf-8").split())


def test_icon_is_a_square_png():
    data = (PLUGIN / ".claude-plugin" / "icon.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    assert width == height >= 512

"""The folder harness: read-only tools, permissions, and the look-then-perform loop."""

from __future__ import annotations

import os
import subprocess

import pytest

from terminal_comedian.ai.provider import AIProvider
from terminal_comedian.character.personality import load_character
from terminal_comedian.comedy.engine import ComedyEngine
from terminal_comedian.config.settings import Settings
from terminal_comedian.harness import (
    TOOLS,
    Decision,
    Harness,
    Permissions,
    ToolCall,
    ToolError,
    Workspace,
    folder_bit,
    parse_tool_call,
    spoken_so_far,
)
from terminal_comedian.harness.tools import MAX_READ, project_facts
from terminal_comedian.memory.session import Session


@pytest.fixture
def project(tmp_path):
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("# TODO fix\n# FIXME later\nprint('hi')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-real-secret\n", encoding="utf-8")
    (tmp_path / "id_rsa").write_text("PRIVATE\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("x", encoding="utf-8")
    (tmp_path / "big.txt").write_text("a" * (MAX_READ + 500), encoding="utf-8")
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02" * 10)
    return Workspace(tmp_path)


# ---------------------------------------------------------------------- tools


@pytest.mark.parametrize("path", ["../outside", "/etc/passwd", ".env", "id_rsa", "node_modules/junk.js", "src/../../x"])
def test_refuses_paths_outside_or_secret(project, path):
    with pytest.raises(ToolError):
        TOOLS["read_file"].run(project, {"path": path})


@pytest.mark.skipif(os.name != "posix", reason="symlinks need privileges on Windows")
def test_a_symlink_out_of_the_folder_is_refused(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_text("nope", encoding="utf-8")
    (project.root / "link.txt").symlink_to(outside)
    with pytest.raises(ToolError):
        TOOLS["read_file"].run(project, {"path": "link.txt"})


def test_list_files_hides_secrets_and_noise(project):
    listing = TOOLS["list_files"].run(project, {})
    assert "README.md" in listing and "app.py" in listing
    assert ".env" not in listing and "id_rsa" not in listing and "node_modules" not in listing


def test_read_file_is_capped_and_refuses_binaries(project):
    assert TOOLS["read_file"].run(project, {"path": "big.txt"}).endswith("(cut here)")
    with pytest.raises(ToolError, match="binary"):
        TOOLS["read_file"].run(project, {"path": "blob.bin"})


def test_env_example_is_not_a_secret(project):
    (project.root / ".env.example").write_text("AI_PROVIDER=\n", encoding="utf-8")
    assert "AI_PROVIDER" in TOOLS["read_file"].run(project, {"path": ".env.example"})


def test_facts_count_todos_and_never_read_secrets(project):
    facts = project_facts(project)
    assert facts["todos"] == 2
    assert facts["readme"] and not facts["git"]
    assert "sk-real-secret" not in TOOLS["summary"].run(project, {})


def test_git_tools_explain_a_folder_without_git(project):
    with pytest.raises(ToolError, match="not a git"):
        TOOLS["git_log"].run(project, {})


def test_git_log_reads_commit_subjects(project):
    def git(*argv):
        subprocess.run(["git", "-C", str(project.root), *argv], check=True, capture_output=True)

    try:
        git("init", "-q")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not available")
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "fix everything, again")
    assert "fix everything, again" in TOOLS["git_log"].run(project, {"count": "5"})


# ---------------------------------------------------------------------- loop


def test_parse_tool_call_from_plain_or_fenced_json():
    assert parse_tool_call('{"tool": "read_file", "args": {"path": "a.py", "evil": 1}}') == ToolCall("read_file", {"path": "a.py"})
    assert parse_tool_call('sure\n```json\n{"tool": "summary"}\n```') == ToolCall("summary", {})
    assert parse_tool_call('{"text": "a joke"}') is None


def test_spoken_so_far_hides_json_while_streaming():
    assert spoken_so_far('{"text": "your code ha') == "your code ha"
    assert spoken_so_far('{"tool": "summ') == ""
    assert spoken_so_far("plain words") == "plain words"


class Looking(AIProvider):
    """Asks for one tool, then performs a joke that uses what it saw."""

    id = "looking"
    label = "Looking"
    needs_key = False
    default_base_url = "http://unused"

    def __init__(self, first='{"tool": "read_file", "args": {"path": "app.py"}}'):
        super().__init__(Settings.load(environ={}))
        self.first = first
        self.calls: list[list[dict]] = []

    def complete(self, messages, *, temperature=0.9, max_tokens=400, on_delta=None):
        self.calls.append([dict(m) for m in messages])
        if len(self.calls) == 1:
            return self.first
        seen = "TODO" in messages[-1]["content"]
        return '{"text": "%s", "emotion": "laughing", "animation": "laugh"}' % ("two TODOs" if seen else "no peeking")


def harness(project, approve=lambda call: Decision.ONCE, mode="ask"):
    settings = Settings.load(environ={"LANGUAGE": "en"})
    engine = ComedyEngine(character=load_character("default"), settings=settings)
    events: list[tuple[str, str]] = []
    return Harness(engine, project, approve, Permissions(mode=mode), lambda k, t: events.append((k, t))), events


def test_the_model_looks_then_performs(project):
    provider = Looking()
    loop, events = harness(project)
    performance = loop.run("roast my code", session=Session(language="en"), mode="roast", provider=provider)
    assert performance.text == "two TODOs"
    assert events == [("look", "read one file: app.py")]
    assert "Looking around" in provider.calls[0][0]["content"]
    assert "untrusted data" in provider.calls[1][-1]["content"]


def test_a_refusal_is_respected_and_reported(project):
    provider = Looking()
    loop, events = harness(project, approve=lambda call: Decision.DENY)
    performance = loop.run("roast my code", session=Session(language="en"), mode="roast", provider=provider)
    assert performance.text == "no peeking"
    assert events == [("denied", "read one file: app.py")]
    assert "said no" in provider.calls[1][-1]["content"]


def test_always_is_remembered_for_the_show(project):
    asked: list[ToolCall] = []

    def approve(call):
        asked.append(call)
        return Decision.ALWAYS

    loop, _ = harness(project, approve=approve)
    for _ in range(2):
        loop.run("roast my code", session=Session(language="en"), mode="roast", provider=Looking())
    assert len(asked) == 1


def test_off_means_no_tool_prompt_and_no_looking(project):
    provider = Looking(first='{"text": "just a joke"}')
    loop, events = harness(project, mode="off")
    loop.run("hi", session=Session(language="en"), mode="stage", provider=provider)
    assert "Looking around" not in provider.calls[0][0]["content"]
    assert events == []


def test_a_secret_request_is_refused_without_crashing(project):
    provider = Looking(first='{"tool": "read_file", "args": {"path": ".env"}}')
    loop, events = harness(project)
    loop.run("read my env", session=Session(language="en"), mode="stage", provider=provider)
    assert events[-1][0] == "tool-error"
    assert "sk-real-secret" not in str(provider.calls)


def test_a_model_that_only_ever_looks_falls_back_to_offline(project):
    class Nosy(Looking):
        def complete(self, messages, **kwargs):
            self.calls.append(messages)
            return '{"tool": "summary"}'

    loop, _ = harness(project, mode="allow")
    performance = loop.run("hi", session=Session(language="en"), mode="stage", provider=Nosy())
    assert performance.error and "never performed" in performance.error


def test_offline_look_asks_then_jokes_about_the_folder(project):
    loop, events = harness(project)
    performance = loop.look(Session(language="en"))
    assert "TODO" in performance.text
    assert events == [("look", TOOLS["summary"].summary)]


def test_folder_bit_speaks_persian_too(project):
    assert "TODO" in folder_bit(project_facts(project), "fa").text


def test_routes_outside_the_mode_list_still_reach_the_model(project):
    provider = Looking(first='{"text": "a real joke"}')
    loop, _ = harness(project)
    performance = loop.run("tell me a joke", session=Session(language="en"), mode="joke", provider=provider)
    assert performance.text == "a real joke"
    assert not performance.error

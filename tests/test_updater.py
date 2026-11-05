"""`comedian update`: detect the install, compare commits, run only the fixed command."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from terminal_comedian import updater
from terminal_comedian.updater import Install, Status


@pytest.fixture
def no_checkout(monkeypatch):
    monkeypatch.setattr(updater, "_checkout_root", lambda: None)


@pytest.fixture
def git_install(monkeypatch):
    class Dist:
        def read_text(self, name):
            return json.dumps({"url": "https://github.com/x", "vcs_info": {"vcs": "git", "commit_id": "a" * 40}})

    monkeypatch.setattr(updater.metadata, "distribution", lambda name: Dist())


@pytest.mark.parametrize(
    "prefix, method",
    [
        ("/home/me/.local/share/uv/tools/terminal-comedy-studio", "uv"),
        ("C:\\Users\\me\\AppData\\Roaming\\uv\\tools\\terminal-comedy-studio", "uv"),
        ("/home/me/.local/share/pipx/venvs/terminal-comedy-studio", "pipx"),
        ("/usr/local", "pip"),
    ],
)
def test_detects_how_it_was_installed(no_checkout, git_install, prefix, method):
    install = updater.detect(prefix)
    assert install.method == method
    assert install.short == "aaaaaaa"


def test_a_clone_updates_with_a_fast_forward_pull(tmp_path):
    install = Install("checkout", "b" * 40, tmp_path)
    assert updater.command(install) == ["git", "-C", str(tmp_path), "pull", "--ff-only"]


def test_each_install_gets_one_fixed_command():
    assert updater.command(Install("uv"))[1:] == ["tool", "upgrade", "terminal-comedy-studio"]
    assert updater.command(Install("pipx"))[1:] == ["install", "--force", updater.GIT_URL]
    assert updater.command(Install("pip"))[1:] == ["-m", "pip", "install", "--upgrade", updater.GIT_URL]


def test_latest_reads_sha_and_subject(monkeypatch):
    body = json.dumps({"sha": "c" * 40, "commit": {"message": "Make it funnier\n\nlong body"}}).encode()
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda request, timeout: io.BytesIO(body))
    assert updater.latest() == ("c" * 40, "Make it funnier")


def test_latest_turns_network_trouble_into_a_message(monkeypatch):
    def offline(request, timeout):
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(updater.urllib.request, "urlopen", offline)
    with pytest.raises(updater.UpdateError, match="could not reach GitHub"):
        updater.latest()


def test_up_to_date_runs_nothing(monkeypatch):
    monkeypatch.setattr(updater, "check", lambda: Status(Install("uv", "d" * 40), "d" * 40, "same"))
    monkeypatch.setattr(updater, "run", lambda argv: pytest.fail("must not run"))
    said: list[str] = []
    assert updater.cli(answer=lambda q: "y", say=said.append) == 0
    assert "newest" in said[0]


def test_saying_no_runs_nothing(monkeypatch):
    monkeypatch.setattr(updater, "check", lambda: Status(Install("uv", "d" * 40), "e" * 40, "new jokes"))
    monkeypatch.setattr(updater, "run", lambda argv: pytest.fail("must not run"))
    said: list[str] = []
    assert updater.cli(answer=lambda q: "n", say=said.append) == 0
    assert "update available" in said[0] and said[-1] == "not updated."


def test_yes_runs_the_fixed_command_once(monkeypatch):
    ran: list[list[str]] = []

    def fake_run(argv):
        ran.append(argv)
        return True, "Updated"

    monkeypatch.setattr(updater, "check", lambda: Status(Install("uv", "d" * 40), "e" * 40, "new jokes"))
    monkeypatch.setattr(updater, "run", fake_run)
    said: list[str] = []
    assert updater.cli(answer=lambda q: "", say=said.append) == 0
    assert ran == [updater.command(Install("uv"))]
    assert "start comedian again" in said[-1]


def test_update_is_a_command_line_verb(monkeypatch):
    from terminal_comedian import cli

    monkeypatch.setattr(updater, "cli", lambda: 7)
    assert cli.main(["update"]) == 7

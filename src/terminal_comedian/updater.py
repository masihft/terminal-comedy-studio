"""`comedian update` and `/update`: get the newest comedian from GitHub.

The installed commit comes from the `direct_url.json` that uv and pip record for
a git install (or from `git rev-parse` in a development checkout). The newest
commit comes from GitHub's public API. Nothing is contacted until the user asks,
and the only commands ever run are the fixed ones below, never anything built
from a network reply.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

REPO = "masihft/terminal-comedy-studio"
GIT_URL = f"git+https://github.com/{REPO}"
DIST = "terminal-comedy-studio"
API = f"https://api.github.com/repos/{REPO}/commits/main"
TIMEOUT = 6.0


class UpdateError(Exception):
    pass


@dataclass(frozen=True)
class Install:
    method: str  # "uv", "pipx", "pip" or "checkout"
    commit: str = ""
    root: Path | None = None  # the checkout, for method == "checkout"

    @property
    def short(self) -> str:
        return self.commit[:7] if self.commit else "unknown"


def _checkout_root() -> Path | None:
    root = Path(__file__).resolve().parents[2]
    return root if (root / ".git").exists() and (root / "pyproject.toml").is_file() else None


def _git_head(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def detect(prefix: str | None = None) -> Install:
    """How this copy was installed, and at which commit."""
    prefix = (prefix or sys.prefix).replace("\\", "/").lower()
    try:
        raw = metadata.distribution(DIST).read_text("direct_url.json") or "{}"
        direct = json.loads(raw)
    except (metadata.PackageNotFoundError, json.JSONDecodeError):
        direct = {}
    editable = bool((direct.get("dir_info") or {}).get("editable"))
    root = _checkout_root()
    if root and (editable or not direct):  # running from a clone (pip install -e . or PYTHONPATH=src)
        return Install("checkout", _git_head(root), root)
    commit = (direct.get("vcs_info") or {}).get("commit_id", "")
    if "/uv/tools/" in prefix or "/uv/tool/" in prefix:
        return Install("uv", commit)
    if "/pipx/venvs/" in prefix:
        return Install("pipx", commit)
    return Install("pip", commit)


def latest(timeout: float = TIMEOUT) -> tuple[str, str]:
    """(sha, first line of the message) of the newest commit on main."""
    request = urllib.request.Request(
        API, headers={"accept": "application/vnd.github+json", "user-agent": "terminal-comedy-studio"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as error:
        raise UpdateError(f"GitHub answered HTTP {error.code}. Try again later.") from None
    except (urllib.error.URLError, OSError) as error:
        raise UpdateError(f"could not reach GitHub ({getattr(error, 'reason', error)}).") from None
    except json.JSONDecodeError:
        raise UpdateError("GitHub sent something that is not JSON.") from None
    sha = str(data.get("sha") or "")
    message = str(((data.get("commit") or {}).get("message") or "")).splitlines()
    if len(sha) < 7:
        raise UpdateError("GitHub did not say which commit is newest.")
    return sha, (message[0] if message else "")


def command(install: Install) -> list[str]:
    """The one fixed command that updates this kind of install."""
    if install.method == "uv":
        return [shutil.which("uv") or "uv", "tool", "upgrade", DIST]
    if install.method == "pipx":
        return [shutil.which("pipx") or "pipx", "install", "--force", GIT_URL]
    if install.method == "checkout" and install.root:
        return ["git", "-C", str(install.root), "pull", "--ff-only"]
    return [sys.executable, "-m", "pip", "install", "--upgrade", GIT_URL]


def describe(argv: list[str]) -> str:
    shown = [Path(argv[0]).name if os.path.isabs(argv[0]) else argv[0], *argv[1:]]
    return " ".join(shown)


def run(argv: list[str], timeout: float = 600.0) -> tuple[bool, str]:
    """Run the update command; return (ok, the last lines of its output)."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return False, f"{argv[0]} is not installed."
    except subprocess.TimeoutExpired:
        return False, "the update took too long and was stopped."
    output = (result.stdout + result.stderr).strip().splitlines()
    return result.returncode == 0, "\n".join(output[-6:])


@dataclass(frozen=True)
class Status:
    install: Install
    newest: str
    subject: str

    @property
    def current(self) -> bool:
        return bool(self.install.commit) and self.install.commit == self.newest

    def summary(self) -> str:
        if self.current:
            return f"you have the newest comedian ({self.install.short})."
        return f"update available: {self.install.short} → {self.newest[:7]} \"{self.subject}\""


def check(timeout: float = TIMEOUT) -> Status:
    install = detect()
    sha, subject = latest(timeout)
    return Status(install, sha, subject)


def cli(answer=input, say=print) -> int:
    """`comedian update` in a plain terminal."""
    try:
        status = check()
    except UpdateError as error:
        say(f"comedian update: {error}")
        return 1
    say(status.summary())
    if status.current:
        return 0
    argv = command(status.install)
    try:
        reply = answer(f"run `{describe(argv)}` now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        reply = "n"
    if reply not in {"", "y", "yes"}:
        say("not updated.")
        return 0
    ok, output = run(argv)
    if output:
        say(output)
    say("updated. start comedian again to use it." if ok else "the update failed; nothing else was changed.")
    return 0 if ok else 1

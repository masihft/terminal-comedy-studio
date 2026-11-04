"""Read-only tools that let the comedian look at the folder it was started in.

Every tool is a pure read: nothing here writes, deletes, runs a model-written
command, or leaves the folder. Paths are resolved and must stay inside the
root, so `../` and symlinks out of the project are refused. Files that usually
hold secrets are refused even when asked for by name.
"""

from __future__ import annotations

import fnmatch
import itertools
import os
import subprocess
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", "dist", "build", ".next", ".cache", "target", ".idea", ".vscode",
}
SECRET_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "id_ecdsa*",
    ".netrc", ".npmrc", ".pypirc", "*credential*", "*secret*", "*.keystore", ".git-credentials",
)
CODE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".php", ".c", ".cpp", ".h",
    ".md", ".swift", ".kt", ".cs", ".vue", ".svelte",
}
JUNK_FILES = {".ds_store", "thumbs.db", "desktop.ini"}
MAX_READ = 6000
MAX_LIST = 150
GIT_TIMEOUT = 5.0


class ToolError(Exception):
    """A refusal or failure the comedian can mention on stage."""


@dataclass(frozen=True)
class Tool:
    name: str
    summary: str  # what the permission prompt says it will do
    args: dict[str, str]  # argument name -> description, for the prompt to the model
    run: Callable[["Workspace", dict[str, Any]], str]


def is_secret(name: str) -> bool:
    lowered = name.lower()
    if lowered == ".env.example":
        return False
    return any(fnmatch.fnmatch(lowered, pattern) for pattern in SECRET_PATTERNS)


@dataclass
class Workspace:
    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()

    @property
    def name(self) -> str:
        return self.root.name or str(self.root)

    def resolve(self, relative: str) -> Path:
        candidate = (self.root / (relative or ".")).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ToolError(f"{relative} is outside this folder.")
        rel = candidate.relative_to(self.root)
        if any(part in SKIP_DIRS for part in rel.parts):
            raise ToolError(f"{relative} is in a folder the comedian does not open.")
        if any(is_secret(part) for part in rel.parts):
            raise ToolError(f"{relative} looks like it holds secrets. Not reading it.")
        return candidate

    def walk(self, start: Path | None = None, depth: int = 3):
        """Files under start (relative paths), skipping noise, hidden folders and secrets."""
        base = start or self.root
        for current, dirs, files in os.walk(base):
            here = Path(current)
            level = len(here.relative_to(self.root).parts)
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".") and not is_secret(d))
            if level >= depth:
                dirs[:] = []
            for name in sorted(files):
                path = here / name
                if is_secret(name) or name.lower() in JUNK_FILES or path.is_symlink():
                    continue
                yield path.relative_to(self.root)


def _size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1048576:.1f} MB"


def list_files(ws: Workspace, args: dict[str, Any]) -> str:
    start = ws.resolve(str(args.get("path") or "."))
    if not start.is_dir():
        raise ToolError(f"{args.get('path')} is not a folder.")
    rows = []
    for count, rel in enumerate(ws.walk(start), 1):
        if count > MAX_LIST:
            rows.append(f"… and more (showing the first {MAX_LIST})")
            break
        rows.append(f"{rel}  {_size((ws.root / rel).stat().st_size)}")
    return "\n".join(rows) or "(empty folder)"


def read_file(ws: Workspace, args: dict[str, Any]) -> str:
    path = ws.resolve(str(args.get("path") or ""))
    if not path.is_file():
        raise ToolError(f"{args.get('path')} is not a file.")
    with path.open("rb") as handle:
        data = handle.read(MAX_READ + 1)
    if b"\x00" in data[:1024]:
        raise ToolError(f"{args.get('path')} is a binary file.")
    text = data[:MAX_READ].decode("utf-8", "replace")
    return text + ("\n… (cut here)" if len(data) > MAX_READ else "")


def _git(ws: Workspace, *argv: str) -> str:
    if not (ws.root / ".git").exists():
        raise ToolError("this folder is not a git repository.")
    try:
        result = subprocess.run(  # fixed argv, no shell: nothing the model writes is executed
            ["git", "-C", str(ws.root), "--no-pager", *argv],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ToolError(f"git did not answer ({error.__class__.__name__}).") from None
    if result.returncode != 0:
        raise ToolError(((result.stderr or "git failed").strip().splitlines() or ["git failed"])[0])
    return result.stdout.strip()[:MAX_READ] or "(nothing)"


def git_log(ws: Workspace, args: dict[str, Any]) -> str:
    try:
        count = int(args.get("count") or 15)
    except (TypeError, ValueError):
        count = 15
    return _git(ws, "log", f"-n{max(1, min(count, 40))}", "--pretty=format:%h %ad %s", "--date=short")


def git_status(ws: Workspace, args: dict[str, Any]) -> str:
    return _git(ws, "status", "--short", "--branch")


def project_facts(ws: Workspace) -> dict[str, Any]:
    """Numbers worth a joke: size, file types, the biggest file, TODOs."""
    files = list(itertools.islice(ws.walk(depth=6), 5000))  # a home folder must not take minutes
    types = Counter((p.suffix.lower() or p.name) for p in files)
    biggest_size, biggest = 0, None
    todos = 0
    for rel in files:
        path = ws.root / rel
        size = path.stat().st_size
        if size > biggest_size:
            biggest_size, biggest = size, rel
        if path.suffix.lower() in CODE_SUFFIXES and size < 500_000:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            todos += text.count("TODO") + text.count("FIXME") + text.count("HACK")
    return {
        "folder": ws.name,
        "files": len(files),
        "top_types": types.most_common(4),
        "biggest": (str(biggest), _size(biggest_size)) if biggest else None,
        "todos": todos,
        "git": (ws.root / ".git").exists(),
        "readme": any(p.name.lower().startswith("readme") for p in files),
        "tests": any("test" in part.lower() for p in files for part in p.parts),
    }


def summary(ws: Workspace, args: dict[str, Any]) -> str:
    facts = project_facts(ws)
    types = ", ".join(f"{ext} ×{n}" for ext, n in facts["top_types"]) or "none"
    biggest = f"{facts['biggest'][0]} ({facts['biggest'][1]})" if facts["biggest"] else "none"
    yes = lambda flag: "yes" if flag else "no"  # noqa: E731
    return "\n".join(
        [
            f"folder: {facts['folder']}",
            f"files: {facts['files']} ({types})",
            f"biggest file: {biggest}",
            f"TODO/FIXME/HACK markers: {facts['todos']}",
            f"git: {yes(facts['git'])}; README: {yes(facts['readme'])}; tests: {yes(facts['tests'])}",
        ]
    )


TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in (
        Tool("summary", "count the files, file types and TODOs in this folder", {}, summary),
        Tool("list_files", "see the file names in this folder", {"path": "folder relative to the project, default ."}, list_files),
        Tool("read_file", "read one file", {"path": "file path relative to the project"}, read_file),
        Tool("git_log", "read the recent git commit messages", {"count": "how many commits, 1-40"}, git_log),
        Tool("git_status", "see which files are changed in git", {}, git_status),
    )
}


def describe(name: str, args: dict[str, Any]) -> str:
    """The plain sentence a permission prompt shows."""
    tool = TOOLS[name]
    target = args.get("path")
    return f"{tool.summary}: {target}" if target else tool.summary

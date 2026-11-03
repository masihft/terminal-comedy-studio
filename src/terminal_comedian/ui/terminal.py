"""What this terminal can actually do, measured instead of assumed."""

from __future__ import annotations

import os
import re
import shutil
import sys
import unicodedata
from dataclasses import dataclass

MIN_WIDTH = 60
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_LRE = "‭"
_PDF = "‬"
_ZERO_WIDTH = _LRE + _PDF + "‎‏؜"


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def sanitize(text: str) -> str:
    """Drop C0/C1 control characters from text before it reaches the screen.

    Provider replies and pasted input are untrusted. A bare escape sequence
    painted inside the stage box would still be interpreted by the terminal, so
    the only way to keep it data is to not emit the control bytes. Newlines and
    tabs survive; Persian ZWNJ (U+200C) is outside the stripped range.
    """
    return _CONTROL.sub("", text)


def is_rtl(text: str) -> bool:
    return any(unicodedata.bidirectional(char) in ("R", "AL") for char in text)


def ltr_row(text: str) -> str:
    """Pin a boxed line's left-to-right order while Persian runs inside it.

    Without this, a bidi-aware terminal can move the box walls to the wrong
    side of an RTL line.
    """
    return _LRE + text + _PDF if is_rtl(text) else text


@dataclass(frozen=True)
class Capabilities:
    width: int
    height: int
    tty: bool
    truecolor: bool
    unicode: bool

    @property
    def colour(self) -> bool:
        return self.truecolor and self.tty

    @property
    def block(self) -> bool:
        return self.unicode


def _truecolor(environ: dict[str, str]) -> bool:
    if environ.get("NO_COLOR"):
        return False
    colorterm = environ.get("COLORTERM", "").lower()
    if colorterm in ("truecolor", "24bit"):
        return True
    term = environ.get("TERM", "").lower()
    return "256color" in term or "truecolor" in term


def detect(environ: dict[str, str] | None = None, stream=None) -> Capabilities:
    environ = os.environ if environ is None else environ
    stream = sys.stdout if stream is None else stream
    columns, rows = shutil.get_terminal_size(fallback=(MIN_WIDTH, 24))
    tty = bool(getattr(stream, "isatty", lambda: False)())
    encoding = (getattr(stream, "encoding", "") or "").lower()
    return Capabilities(
        width=max(MIN_WIDTH, columns),
        height=max(12, rows),
        tty=tty,
        truecolor=_truecolor(environ),
        unicode="utf" in encoding,
    )


def size() -> tuple[int, int]:
    columns, rows = shutil.get_terminal_size(fallback=(MIN_WIDTH, 24))
    return max(MIN_WIDTH, columns), max(12, rows)


def char_width(char: str) -> int:
    """Cell width, so East Asian and combining marks do not break the stage box."""
    if char in _ZERO_WIDTH or unicodedata.combining(char):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def text_width(text: str) -> int:
    """Visible cells, ignoring ANSI colour codes and zero-width marks."""
    return sum(char_width(char) for char in strip_ansi(text))


def wrap(text: str, width: int) -> list[str]:
    """Wrap on display width. Persian is written as-is; the terminal applies bidi."""
    width = max(12, width)
    lines: list[str] = []
    for paragraph in sanitize(text).splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if text_width(candidate) <= width:
                current = candidate
                continue
            if current:
                lines.append(current)
            while text_width(word) > width:
                lines.append(word[: width - 1])
                word = word[width - 1 :]
            current = word
        lines.append(current)
    return lines or [""]

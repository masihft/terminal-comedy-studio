"""The stage: a small lit rectangle made of box-drawing characters.

AGENTS.md §15 — a comedy stage, not a dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..character.frames import FRAMES
from .renderer import PIXEL_WIDTH, to_ansi, to_ascii
from .terminal import Capabilities, ltr_row, text_width, wrap

PINK = (255, 79, 163)
PURPLE = (155, 106, 255)
WHITE = (240, 232, 240)
DIM = (139, 116, 133)

TITLE = "TERMINAL COMEDY"
LIVE = "LIVE FROM YOUR TERMINAL"
MIN_INNER = 58
MAX_INNER = 72


@dataclass(frozen=True)
class Palette:
    caps: Capabilities

    def paint(self, text: str, rgb: tuple[int, int, int]) -> str:
        if not self.caps.colour:
            return text
        return f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}\x1b[0m"


def center(text: str, width: int) -> str:
    pad = max(0, width - text_width(text))
    left = pad // 2
    return " " * left + text + " " * (pad - left)


def character_block(frame_name: str, caps: Capabilities, jacket: tuple[int, int, int] | None = None) -> list[str]:
    frame = FRAMES[frame_name]
    if caps.block:
        return to_ansi(frame, colour=caps.colour, jacket=jacket).split("\n")
    return [" " * PIXEL_WIDTH + row for row in to_ascii(frame)]


def _inner_width(caps: Capabilities) -> int:
    return min(MAX_INNER, max(MIN_INNER, caps.width - 4))


def _sides(caps: Capabilities) -> tuple[str, str, str, str, str, str]:
    if caps.block:
        return "╭", "╮", "│", "╰", "╯", "─"
    return "+", "+", "|", "+", "+", "-"


def stage_lines(
    *,
    comedian: str,
    speech: str,
    frame_name: str = "idle_01",
    caps: Capabilities,
    mode: str = "stage",
    note: str = "",
    jacket: tuple[int, int, int] | None = None,
) -> list[str]:
    """Everything between the top of the stage and the prompt, as text lines."""
    palette = Palette(caps)
    inner = _inner_width(caps)
    tl, tr, wall, bl, br, dash = _sides(caps)
    body = wrap(speech, inner - 4) if speech else [""]

    rows: list[str] = [center(palette.paint(TITLE, PINK), inner)]
    rows.append(center(palette.paint(f"~ {LIVE} ~", PURPLE), inner))
    rows.append("")
    rows.extend(center(block, inner) for block in character_block(frame_name, caps, jacket))
    rows.append("")
    rows.append(center(palette.paint(f"🎤  {comedian}", PINK), inner))
    rows.append("")
    rows.extend(body)
    if note:
        rows.append("")
        rows.append(center(palette.paint(note, DIM), inner))

    out = [tl + dash * inner + tr]
    out += [
        wall + ltr_row(row + " " * max(0, inner - text_width(row))) + wall for row in rows
    ]
    footer = f" {mode} "
    out.append(bl + dash * max(0, inner - text_width(footer)) + footer + br)
    return out


def banner(caps: Capabilities, comedian: str) -> list[str]:
    palette = Palette(caps)
    return [
        palette.paint("TERMINAL COMEDY STUDIO", PINK),
        palette.paint(f"{comedian} is on stage. Type anything, or /help.", DIM),
    ]

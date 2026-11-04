"""The mascot as half-block cells: two grid rows per terminal row, square pixels.

A terminal cell is about twice as tall as it is wide. Drawing each pixel two
cells wide and half a cell tall (an upper half block with a foreground and a
background colour) keeps the pixels square and the silhouette exact.
"""

from __future__ import annotations

from rich.style import Style
from rich.text import Text

from ..character.frames import PALETTE, TRANSPARENT, Frame

UPPER = "▀"
LOWER = "▄"


def _rgb(colour: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % colour


def frame_text(frame: Frame, jacket: tuple[int, int, int] | None = None) -> Text:
    palette = {**PALETTE, "P": jacket} if jacket else PALETTE
    text = Text(no_wrap=True, overflow="crop")
    rows = list(frame.pixels)
    if len(rows) % 2:
        rows.append(TRANSPARENT * frame.width)
    for y in range(0, len(rows), 2):
        top, bottom = rows[y], rows[y + 1]
        for x in range(frame.width):
            upper, lower = top[x], bottom[x]
            if upper == TRANSPARENT and lower == TRANSPARENT:
                text.append("  ")
            elif lower == TRANSPARENT:
                text.append(UPPER * 2, Style(color=_rgb(palette[upper])))
            elif upper == TRANSPARENT:
                text.append(LOWER * 2, Style(color=_rgb(palette[lower])))
            else:
                text.append(UPPER * 2, Style(color=_rgb(palette[upper]), bgcolor=_rgb(palette[lower])))
        if y + 2 < len(rows):
            text.append("\n")
    return text


def size(frame: Frame) -> tuple[int, int]:
    """(columns, rows) the frame occupies."""
    return frame.width * 2, (frame.height + 1) // 2

"""Pixel art in terminal cells: the mascot and the stage lettering.

A terminal cell is about twice as tall as it is wide, so one pixel drawn as one
cell column and half a cell row (an upper half block with a foreground and a
background colour) is square. Everything here renders a bitmap that way, with
an integer `scale` that turns each pixel into scale x scale square sub-pixels.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from rich.style import Style
from rich.text import Text

from ..character.frames import PALETTE, TRANSPARENT, Frame

UPPER = "▀"
LOWER = "▄"
FULL = "█"

RGB = tuple[int, int, int]
Bitmap = list[list[RGB | None]]


def _hex(colour: RGB) -> str:
    return "#%02x%02x%02x" % colour


def render(bitmap: Bitmap) -> Text:
    """Two bitmap rows per terminal row, one bitmap column per terminal column."""
    text = Text(no_wrap=True, overflow="crop", end="")
    rows = [list(row) for row in bitmap]
    width = max((len(row) for row in rows), default=0)
    for row in rows:
        row.extend([None] * (width - len(row)))
    if len(rows) % 2:
        rows.append([None] * width)
    for y in range(0, len(rows), 2):
        top, bottom = rows[y], rows[y + 1]
        for upper, lower in zip(top, bottom):
            if upper is None and lower is None:
                text.append(" ")
            elif lower is None:
                text.append(UPPER, Style(color=_hex(upper)))
            elif upper is None:
                text.append(LOWER, Style(color=_hex(lower)))
            elif upper == lower:
                text.append(FULL, Style(color=_hex(upper)))
            else:
                text.append(UPPER, Style(color=_hex(upper), bgcolor=_hex(lower)))
        if y + 2 < len(rows):
            text.append("\n")
    return text


def scaled(bitmap: Bitmap, scale: int) -> Bitmap:
    if scale <= 1:
        return bitmap
    out: Bitmap = []
    for row in bitmap:
        wide = [cell for cell in row for _ in range(scale)]
        out.extend(list(wide) for _ in range(scale))
    return out


# ------------------------------------------------------------------ mascot --


def frame_bitmap(frame: Frame, jacket: RGB | None = None) -> Bitmap:
    palette = {**PALETTE, "P": jacket} if jacket else PALETTE
    return [[None if key == TRANSPARENT else palette[key] for key in row] for row in frame.pixels]


def frame_text(frame: Frame, jacket: RGB | None = None, scale: int = 1) -> Text:
    return render(scaled(frame_bitmap(frame, jacket), scale))


def size(frame: Frame, scale: int = 1) -> tuple[int, int]:
    """(columns, rows) the frame occupies at this scale."""
    return frame.width * scale, (frame.height * scale + 1) // 2


# ------------------------------------------------------------------- fonts --

# 5x7: the stage title. Rows top to bottom, "#" is ink.
FONT_5X7: dict[str, tuple[str, ...]] = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "'": ("#", "#", ".", ".", ".", ".", "."),
    ".": (".", ".", ".", ".", ".", ".", "#"),
    "-": ("...", "...", "...", "###", "...", "...", "..."),
    " ": ("...", "...", "...", "...", "...", "...", "..."),
}

# 3x5: names, the LIVE badge, and narrow terminals.
FONT_3X5: dict[str, tuple[str, ...]] = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"),
    "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"),
    "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"),
    "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"),
    "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"),
    "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"),
    "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#"),
    "N": ("#..#", "##.#", "#.##", "#..#", "#..#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."),
    "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", "##.", ".##"),
    "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."),
    "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"),
    "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "Z": ("###", "..#", ".#.", "#..", "###"),
    "'": ("#", "#", ".", ".", "."),
    ".": (".", ".", ".", ".", "#"),
    "-": ("..", "..", "##", "..", ".."),
    " ": ("..", "..", "..", "..", ".."),
}

FONTS = {"big": FONT_5X7, "small": FONT_3X5}


def supported(text: str, font: str = "small") -> bool:
    glyphs = FONTS[font]
    return all(char.upper() in glyphs for char in text)


def text_bitmap(
    text: str,
    font: str = "big",
    colour: RGB | Callable[[int, int], RGB] = (255, 79, 163),
    gap: int = 1,
) -> Bitmap:
    """Lay glyphs side by side. `colour` may be a function of (row, height) for gradients."""
    glyphs = FONTS[font]
    height = len(next(iter(glyphs.values())))
    rows: list[list[bool]] = [[] for _ in range(height)]
    for index, char in enumerate(text.upper()):
        glyph = glyphs.get(char, glyphs[" "])
        for y in range(height):
            rows[y].extend(cell == "#" for cell in glyph[y])
            if index < len(text) - 1:
                rows[y].extend([False] * gap)
    paint = colour if callable(colour) else (lambda y, h, fixed=colour: fixed)
    return [[paint(y, height) if ink else None for ink in row] for y, row in enumerate(rows)]


def text_width(text: str, font: str = "big", gap: int = 1, scale: int = 1) -> int:
    glyphs = FONTS[font]
    columns = sum(len(glyphs.get(c.upper(), glyphs[" "])[0]) for c in text) + gap * max(0, len(text) - 1)
    return columns * scale


def gradient(top: RGB, bottom: RGB) -> Callable[[int, int], RGB]:
    def paint(y: int, height: int) -> RGB:
        t = y / max(1, height - 1)
        return tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))  # type: ignore[return-value]

    return paint


def pixel_text(
    text: str,
    font: str = "big",
    colour: RGB | Callable[[int, int], RGB] = (255, 79, 163),
    scale: int = 1,
) -> Text:
    return render(scaled(text_bitmap(text, font, colour), scale))


def side_by_side(bitmaps: Sequence[Bitmap], gap: int = 3) -> Bitmap:
    """Join bitmaps left to right, bottom-aligned, `gap` empty columns apart."""
    height = max(len(b) for b in bitmaps)
    out: Bitmap = [[] for _ in range(height)]
    for index, bitmap in enumerate(bitmaps):
        width = max((len(row) for row in bitmap), default=0)
        pad = height - len(bitmap)
        for y in range(height):
            source = bitmap[y - pad] if y >= pad else []
            out[y].extend(list(source) + [None] * (width - len(source)))
            if index < len(bitmaps) - 1:
                out[y].extend([None] * gap)
    return out

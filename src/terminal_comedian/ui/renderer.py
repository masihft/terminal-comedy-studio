"""Grid frames to terminal text, plain text, or SVG. No third-party dependency."""

from __future__ import annotations

from ..character.frames import PALETTE, TRANSPARENT, Frame

PIXEL_WIDTH = 2  # terminal cells per pixel: cells are tall, pixels are square
BLOCK = "█"


def to_plain(frame: Frame, empty: str = " ") -> list[str]:
    """Palette keys, one line per grid row. Used by tests and ASCII fallback."""
    return [
        "".join(empty if c == TRANSPARENT else c for c in row)
        for row in frame.pixels
    ]


def to_ascii(frame: Frame) -> list[str]:
    """A silhouette that survives terminals without Unicode."""
    return ["".join(" " if c == TRANSPARENT else "#" for c in row) for row in frame.pixels]


def _style(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m"


def to_ansi(frame: Frame, pixel_width: int = PIXEL_WIDTH, colour: bool = True) -> str:
    """One terminal line per grid row, `pixel_width` cells per pixel."""
    out = []
    for row in frame.pixels:
        parts = []
        for key in row:
            if key == TRANSPARENT:
                parts.append(" " * pixel_width)
                continue
            r, g, b = PALETTE[key]
            cells = BLOCK * pixel_width
            parts.append(f"{_style(r, g, b)}{cells}\x1b[0m" if colour else cells)
        out.append("".join(parts))
    return "\n".join(out)


def side_by_side(frames: list[Frame], gap: int = 3, **kwargs) -> str:
    """Frames laid out in a row, for animation strips in the terminal."""
    blocks = [to_ansi(f, **kwargs).split("\n") for f in frames]
    height = max(len(b) for b in blocks)
    for block in blocks:
        while len(block) < height:
            block.append("")
    pad = " " * gap
    return "\n".join(pad.join(line) for line in zip(*blocks))


def to_svg(frames: list[Frame], cell: int = 8, gap: int = 6, label: int = 14) -> str:
    """A contact sheet of frames, for checking the drawing with real eyes."""
    width = max(f.width for f in frames)
    height = max(f.height for f in frames)
    tile_w = width * cell + gap * 2
    tile_h = height * cell + label + gap
    cols = min(len(frames), 6)
    rows = (len(frames) + cols - 1) // cols
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cols * tile_w}" '
        f'height="{rows * tile_h}" viewBox="0 0 {cols * tile_w} {rows * tile_h}">',
        f'<rect width="100%" height="100%" fill="#120611"/>',
    ]
    for i, frame in enumerate(frames):
        ox = (i % cols) * tile_w + gap
        oy = (i // cols) * tile_h + gap
        for y, row in enumerate(frame.pixels):
            for x, key in enumerate(row):
                if key == TRANSPARENT:
                    continue
                r, g, b = PALETTE[key]
                out.append(
                    f'<rect x="{ox + x * cell}" y="{oy + y * cell}" width="{cell}" '
                    f'height="{cell}" fill="rgb({r},{g},{b})"/>'
                )
        out.append(
            f'<text x="{ox}" y="{oy + height * cell + label - 3}" '
            f'font-family="monospace" font-size="{label - 2}" fill="#ff8ec6">{frame.name}</text>'
        )
    out.append("</svg>")
    return "".join(out)

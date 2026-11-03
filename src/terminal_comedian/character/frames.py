"""The comedian's body: one shared pixel grid, measured from the Claw'd reference.

The mascot keeps the reference orange; it wears one flat pink jacket rectangle,
a white shirt rectangle and a black tie rectangle. Eyes and mouth are black
rectangles. No shading, no diagonals, no curves - four colours, squares only.

Measured from `clawd refference/images.png` (1 grid pixel = 19.2 source pixels):
  head/body  8 x 5.7 units  -> 16 x 12 pixels
  ears       2 x 2 units, flush at mid body height (31%-66%) -> 4 x 4 pixels
  eyes       1 x 1 units, inset 1 unit from top and sides    -> 2 x 2 pixels
  legs       1 x 2 units, outer legs flush with body edges   -> 2 x 4 pixels
"""

from __future__ import annotations

from dataclasses import dataclass

GRID_WIDTH = 27
GRID_HEIGHT = 18

BODY = (5, 1, 20, 12)
JACKET = (5, 8, 20, 12)
EAR_LEFT = (1, 5, 4, 8)
EAR_RIGHT = (21, 5, 24, 8)
EYE_LEFT = (7, 3, 8, 4)
EYE_RIGHT = (17, 3, 18, 4)
SHIRT = (10, 9, 15, 11)
TIE = (12, 9, 13, 11)
MOUTH = (11, 6, 14, 7)

# AGENTS.md section 5.1 asks for exactly three centered legs; the reference sheet
# draws four. Three is the default, LEGS_REFERENCE keeps the measured silhouette.
LEGS_STAND = ((5, 13, 6, 16), (12, 13, 13, 16), (19, 13, 20, 16))
LEGS_REFERENCE = ((5, 13, 6, 16), (9, 13, 10, 16), (15, 13, 16, 16), (19, 13, 20, 16))

PALETTE = {
    "O": (218, 119, 88),   # the mascot itself, measured off the reference
    "P": (255, 79, 163),   # pink jacket
    "W": (250, 246, 250),  # white shirt
    "K": (20, 6, 14),      # black tie, eyes, shoes
}

TRANSPARENT = "."

EYE_STYLES = ("open", "closed", "happy", "wide", "left", "right", "up")
MOUTH_STYLES = ("smile", "flat", "line", "small", "open", "wide", "laugh", "twitch")
ARM_POSES = ("normal", "up", "back", "wave_right", "wave_left")


class Canvas:
    """A grid of palette keys. Knows nothing about terminals or colours."""

    def __init__(self, width: int = GRID_WIDTH, height: int = GRID_HEIGHT) -> None:
        self.width = width
        self.height = height
        self._cells = [[TRANSPARENT] * width for _ in range(height)]

    def rect(self, x0: int, y0: int, x1: int, y1: int, key: str) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < self.width and 0 <= y < self.height:
                    self._cells[y][x] = key

    def boxes(self, boxes, key: str, dy: int = 0) -> None:
        for x0, y0, x1, y1 in boxes:
            self.rect(x0, y0 + dy, x1, y1 + dy, key)

    def cell(self, x: int, y: int) -> str:
        return self._cells[y][x]

    def rows(self) -> tuple[str, ...]:
        return tuple("".join(row) for row in self._cells)


@dataclass(frozen=True)
class Frame:
    name: str
    width: int
    height: int
    pixels: tuple[str, ...]

    def cell(self, x: int, y: int) -> str:
        return self.pixels[y][x]


def _shift(box, dx=0, dy=0):
    return (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)


# -------------------------------------------------------------------------- suit


def draw_body(canvas: Canvas, dy: int = 0) -> None:
    canvas.boxes([BODY], "O", dy)


def draw_jacket(canvas: Canvas, dy: int = 0) -> None:
    """The pink jacket is one rectangle over the shoulders and chest."""
    canvas.boxes([JACKET], "P", dy)


def draw_shirt(canvas: Canvas, dy: int = 0) -> None:
    canvas.boxes([SHIRT], "W", dy)


def draw_tie(canvas: Canvas, dy: int = 0) -> None:
    canvas.boxes([TIE], "K", dy)


def draw_arms(canvas: Canvas, pose: str = "normal", dy: int = 0) -> None:
    """The reference ears double as arms: flat tabs at mid body height."""
    boxes = {
        "normal": (EAR_LEFT, EAR_RIGHT),
        "up": ((1, 3, 4, 6), (21, 3, 24, 6)),
        "back": ((2, 8, 5, 11), (20, 8, 23, 11)),
        "wave_right": (EAR_LEFT, (21, 1, 25, 4)),
        "wave_left": ((0, 1, 4, 4), EAR_RIGHT),
    }[pose]
    canvas.boxes(boxes, "O", dy)


def draw_legs(canvas: Canvas, legs=LEGS_STAND, body_dy: int = 0) -> None:
    """Feet stay on the floor; a bobbing body stretches or compresses the legs."""
    for x0, y0, x1, y1 in legs:
        top = min(y0 + body_dy, y1 - 1)
        canvas.rect(x0, top, x1, y1 - 1, "O")
        canvas.rect(x0, y1, x1, y1, "K")


# ----------------------------------------------------------------- expressions


def draw_eye(canvas: Canvas, box, style: str) -> None:
    if style not in EYE_STYLES:
        raise ValueError(f"unknown eye style {style!r}")
    x0, y0, x1, y1 = box
    if style == "open":
        canvas.rect(x0, y0, x1, y1, "K")
    elif style == "closed":
        canvas.rect(x0, y1, x1, y1, "K")
    elif style == "happy":
        canvas.rect(x0, y0, x1, y0, "K")
    elif style == "wide":
        canvas.rect(x0, y0 - 1, x1, y1, "K")
    elif style == "left":
        canvas.rect(x0 - 1, y0, x1 - 1, y1, "K")
    elif style == "right":
        canvas.rect(x0 + 1, y0, x1 + 1, y1, "K")
    elif style == "up":
        canvas.rect(x0, y0 - 1, x1, y1 - 1, "K")


def draw_mouth(canvas: Canvas, style: str, dy: int = 0) -> None:
    if style not in MOUTH_STYLES:
        raise ValueError(f"unknown mouth style {style!r}")
    x0, y0, x1, y1 = _shift(MOUTH, dy=dy)
    if style == "smile":                    # bar with both ends raised
        canvas.rect(x0, y0, x1, y0, "K")
        canvas.rect(x0, y0 - 1, x0, y0 - 1, "K")
        canvas.rect(x1, y0 - 1, x1, y0 - 1, "K")
    elif style == "flat":
        canvas.rect(x0, y0, x1, y0, "K")
    elif style == "line":
        canvas.rect(x0 + 1, y0, x1 - 1, y0, "K")
    elif style == "small":
        canvas.rect(x0 + 1, y0, x1 - 1, y0, "K")
        canvas.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 1, "K")
    elif style == "open":
        canvas.rect(x0 + 1, y0, x1 - 1, y1, "K")
    elif style == "wide":
        canvas.rect(x0, y0, x1, y1, "K")
    elif style == "laugh":
        canvas.rect(x0 - 1, y0, x1 + 1, y1, "K")
    elif style == "twitch":
        canvas.rect(x0 + 1, y0, x1 - 1, y0, "K")
        canvas.rect(x1, y1, x1, y1, "K")


# --------------------------------------------------------------------- assembly


def build_frame(
    name: str,
    *,
    eyes: str | tuple[str, str] = "open",
    mouth: str = "smile",
    body_dy: int = 0,
    arms: str = "normal",
    legs=LEGS_STAND,
) -> Frame:
    canvas = Canvas()
    left, right = (eyes, eyes) if isinstance(eyes, str) else eyes
    draw_body(canvas, dy=body_dy)
    draw_jacket(canvas, dy=body_dy)
    draw_shirt(canvas, dy=body_dy)
    draw_tie(canvas, dy=body_dy)
    draw_arms(canvas, pose=arms, dy=body_dy)
    draw_eye(canvas, _shift(EYE_LEFT, dy=body_dy), left)
    draw_eye(canvas, _shift(EYE_RIGHT, dy=body_dy), right)
    draw_mouth(canvas, mouth, dy=body_dy)
    draw_legs(canvas, legs, body_dy=body_dy)
    return Frame(name, GRID_WIDTH, GRID_HEIGHT, canvas.rows())


def _f(name: str, **kwargs) -> Frame:
    return build_frame(name, **kwargs)


FRAMES: dict[str, Frame] = {
    f.name: f
    for f in [
        # idle - slow breathing
        _f("idle_01"),
        _f("idle_02", mouth="line", body_dy=1),
        _f("idle_03"),
        # blink
        _f("blink_01", eyes="closed", mouth="line"),
        _f("blink_02", eyes="closed", mouth="flat"),
        # talking
        _f("talk_01", mouth="open"),
        _f("talk_02", mouth="flat"),
        _f("talk_03", mouth="small"),
        _f("talk_04", mouth="wide", body_dy=1),
        # thinking
        _f("think_01", eyes="left", mouth="line"),
        _f("think_02", eyes="up", mouth="small", body_dy=1),
        # surprised
        _f("surprise_01", eyes="wide", mouth="open", arms="up"),
        _f("surprise_02", eyes="wide", mouth="wide", arms="up", body_dy=1),
        # laughing
        _f("laugh_01", eyes="happy", mouth="laugh", body_dy=1),
        _f("laugh_02", eyes="happy", mouth="wide"),
        # punchline
        _f("punchline_01", eyes="happy", mouth="flat", arms="wave_right"),
        _f("punchline_02", eyes="open", mouth="laugh", arms="wave_right", body_dy=1),
        # deadpan reaction
        _f("reaction_01", eyes=("closed", "open"), mouth="flat"),
        _f("reaction_02", eyes="open", mouth="twitch", body_dy=1),
        # states straight off the reference sheet
        _f(
            "bounce_01",
            mouth="line",
            body_dy=-1,
            legs=((5, 13, 6, 15), (12, 13, 13, 16), (19, 13, 20, 16)),
        ),
        _f("bounce_02", mouth="smile"),
        _f(
            "bounce_03",
            mouth="line",
            body_dy=1,
            legs=((5, 13, 6, 16), (12, 13, 13, 16), (19, 13, 20, 15)),
        ),
        _f("wave_01", eyes="happy", mouth="flat", arms="wave_right"),
        _f("wave_02", mouth="smile", arms="wave_right", body_dy=1),
        _f("wave_03", eyes=("open", "happy"), mouth="flat", arms="wave_left"),
        _f("look_01", eyes="right", mouth="line"),
        _f("look_02", eyes="left", mouth="flat"),
        _f("walk_01", mouth="line", legs=((5, 13, 6, 16), (11, 13, 12, 15), (19, 13, 20, 16))),
        _f("walk_02", mouth="line", body_dy=1, legs=((6, 13, 7, 15), (12, 13, 13, 16), (18, 13, 19, 16))),
        _f("walk_03", legs=((7, 13, 8, 16), (13, 13, 14, 15), (19, 13, 20, 16))),
        _f("walk_04", body_dy=1, legs=((5, 13, 6, 15), (12, 13, 13, 16), (17, 13, 18, 16))),
        _f("run_01", eyes="wide", mouth="open", arms="back", legs=((4, 13, 5, 15), (12, 13, 13, 16), (20, 13, 21, 15))),
        _f("run_02", eyes="wide", mouth="open", arms="back", body_dy=1, legs=((6, 13, 7, 16), (12, 13, 13, 14), (18, 13, 19, 16))),
        _f("run_03", eyes="wide", mouth="wide", arms="back", body_dy=-1, legs=((5, 13, 6, 16), (13, 13, 14, 15), (19, 13, 20, 14))),
        _f("run_04", eyes="wide", mouth="wide", arms="back", body_dy=1, legs=((7, 13, 8, 15), (11, 13, 12, 16), (17, 13, 18, 16))),
        # beats
        _f("proud_01", eyes="happy", mouth="flat", arms="up"),
        _f("sorry_01", eyes="closed", mouth="small", arms="back", body_dy=1),
    ]
}

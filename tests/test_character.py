"""The character must stay the same creature in every frame."""

from __future__ import annotations

import pytest

from terminal_comedian.character.frames import (
    BODY,
    EYE_LEFT,
    EYE_RIGHT,
    FRAMES,
    GRID_HEIGHT,
    GRID_WIDTH,
    LEGS_REFERENCE,
    MOUTH_STYLES,
    PALETTE,
    TRANSPARENT,
    EYE_STYLES,
    build_frame,
)
from terminal_comedian.character.states import (
    ANIMATIONS,
    EMOTION_ANIMATION,
    Emotion,
    Player,
    animation_for_emotion,
)
from terminal_comedian.ui.renderer import to_ansi, to_ascii, to_plain, to_svg

FACE_TOP, FACE_BOTTOM = BODY[1], BODY[3]
EYE_BAND = (2, 5)          # the eyes travel one row up or down with the body bob
LEFT_HALF = (0, 9)
RIGHT_HALF = (16, GRID_WIDTH - 1)
SHOE_BAND = (13, 16)


def eyes(frame) -> int:
    """One black blob on each side of the face, whatever the expression."""
    return (
        blobs(frame, EYE_BAND, cols=LEFT_HALF, keys="K")
        + blobs(frame, EYE_BAND, cols=RIGHT_HALF, keys="K")
    )


def shoes(frame) -> int:
    """One black shoe per leg, counted below the jacket so a bob cannot fool us."""
    return blobs(frame, SHOE_BAND, keys="K")


def blobs(frame, rows, cols=(0, GRID_WIDTH - 1), keys=None) -> int:
    """Count connected groups of painted cells inside a window of the grid."""
    y0, y1 = rows
    x0, x1 = cols
    seen = set()
    count = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            cell = frame.cell(x, y)
            if cell == TRANSPARENT or (keys and cell not in keys):
                continue
            if (x, y) in seen:
                continue
            count += 1
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in seen:
                    continue
                cell = frame.cell(cx, cy)
                if cell == TRANSPARENT or (keys and cell not in keys):
                    continue
                seen.add((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if x0 <= nx <= x1 and y0 <= ny <= y1:
                        stack.append((nx, ny))
    return count


def count_keys(frame, key: str) -> int:
    return sum(row.count(key) for row in frame.pixels)


# ------------------------------------------------------------------ geometry


def test_grid_is_shared_by_every_frame():
    assert len(FRAMES) >= 30
    for frame in FRAMES.values():
        assert (frame.width, frame.height) == (GRID_WIDTH, GRID_HEIGHT)
        assert len(frame.pixels) == GRID_HEIGHT
        assert all(len(row) == GRID_WIDTH for row in frame.pixels)


def test_frames_only_use_the_four_colour_palette():
    allowed = set(PALETTE) | {TRANSPARENT}
    for frame in FRAMES.values():
        assert set("".join(frame.pixels)) <= allowed


def test_exactly_two_side_arms_in_every_frame():
    for frame in FRAMES.values():
        outside = blobs(frame, (0, FACE_BOTTOM), cols=(0, BODY[0] - 1)) + blobs(
            frame, (0, FACE_BOTTOM), cols=(BODY[2] + 1, GRID_WIDTH - 1)
        )
        assert outside == 2, frame.name


def test_exactly_two_eyes_in_every_frame():
    for frame in FRAMES.values():
        assert eyes(frame) == 2, frame.name


def test_exactly_three_legs_in_every_frame():
    for frame in FRAMES.values():
        assert shoes(frame) == 3, frame.name


def test_reference_variant_draws_four_legs():
    frame = build_frame("four_legs", legs=LEGS_REFERENCE)
    assert shoes(frame) == 4


def test_eyes_sit_one_unit_in_from_the_top_and_sides():
    assert EYE_LEFT[1] - BODY[1] == 2 and EYE_LEFT[0] - BODY[0] == 2
    assert EYE_RIGHT[2] - BODY[2] == -2
    assert (EYE_LEFT[0], EYE_RIGHT[2]) == (7, 18)


def test_jacket_shirt_and_tie_are_worn_in_every_frame():
    for frame in FRAMES.values():
        assert count_keys(frame, "W") >= 12, frame.name        # white shirt
        blade = sum(
            1
            for y in range(FACE_TOP, FACE_BOTTOM + 1)
            for x in (12, 13)
            if frame.cell(x, y) == "K"
        )
        assert blade >= 6, frame.name                          # black tie


# ------------------------------------------------------------------ features


@pytest.mark.parametrize("style", MOUTH_STYLES)
def test_every_mouth_style_paints_a_mouth(style):
    frame = build_frame(f"mouth_{style}", mouth=style)
    painted = sum(
        1 for y in range(5, 9) for x in range(9, 17) if frame.cell(x, y) == "K"
    )
    assert painted >= 2, style


@pytest.mark.parametrize("style", EYE_STYLES)
def test_every_eye_style_keeps_two_eyes(style):
    frame = build_frame(f"eye_{style}", eyes=style)
    assert eyes(frame) == 2, style


# ----------------------------------------------------------------- animation


def test_animations_only_reference_real_frames():
    for animation in ANIMATIONS.values():
        for name in animation.frames:
            assert name in FRAMES, f"{animation.name} -> {name}"
        assert animation.fps > 0
        assert animation.loop in (True, False)


def test_required_animations_exist():
    for name in ("idle", "blink", "talk", "think", "surprise", "laugh", "punchline", "reaction"):
        assert name in ANIMATIONS


def test_every_emotion_maps_to_a_playable_animation():
    for emotion, name in EMOTION_ANIMATION.items():
        assert name in ANIMATIONS
        assert animation_for_emotion(emotion) == name
        assert animation_for_emotion(str(emotion.value)) == name


def test_player_loops_a_repeating_animation():
    player = Player("idle")
    names = []
    for _ in range(8):
        names.append(player.frame_name)
        player.advance(0.6)
    assert names[0] == "idle_01"
    assert len(set(names)) == 3
    assert not player.finished


def test_player_stops_on_a_one_shot():
    player = Player("blink")
    for _ in range(6):
        player.advance(0.2)
    assert player.finished
    assert player.frame_name == "blink_01"


def test_player_rejects_unknown_animation():
    with pytest.raises(ValueError):
        Player("cartwheel")


# ------------------------------------------------------------------- render


def test_plain_render_matches_the_grid():
    lines = to_plain(FRAMES["idle_01"])
    assert len(lines) == GRID_HEIGHT
    assert all(len(line) == GRID_WIDTH for line in lines)


def test_ascii_render_keeps_the_silhouette():
    frame = FRAMES["idle_01"]
    painted = sum(row.count(key) for row in frame.pixels for key in PALETTE)
    assert sum(line.count("#") for line in to_ascii(frame)) == painted


def test_ansi_render_colours_the_palette():
    text = to_ansi(FRAMES["idle_01"])
    assert "\x1b[38;2;218;119;88m" in text          # orange mascot
    assert "\x1b[38;2;255;79;163m" in text          # pink jacket
    assert text.count("\n") == GRID_HEIGHT - 1


def test_svg_sheet_has_one_label_per_frame():
    svg = to_svg([FRAMES["idle_01"], FRAMES["laugh_02"]])
    assert svg.count("<text") == 2
    assert "idle_01" in svg and "laugh_02" in svg

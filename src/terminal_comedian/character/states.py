"""Frame-based animations built from the shared grid."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .frames import FRAMES


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    LAUGHING = "laughing"
    SURPRISED = "surprised"
    THINKING = "thinking"
    SARCASTIC = "sarcastic"
    PROUD = "proud"
    SORRY = "sorry"

    def __str__(self) -> str:  # pragma: no cover - convenience for prompts
        return self.value


@dataclass(frozen=True)
class Animation:
    name: str
    frames: tuple[str, ...]
    fps: float
    loop: bool = True

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError(f"{self.name}: an animation needs at least one frame")
        missing = [f for f in self.frames if f not in FRAMES]
        if missing:
            raise ValueError(f"{self.name}: unknown frames {missing}")
        if self.fps <= 0:
            raise ValueError(f"{self.name}: fps must be positive")


def _a(name: str, frames: tuple[str, ...], fps: float, loop: bool = True) -> Animation:
    return Animation(name, frames, fps, loop)


ANIMATIONS: dict[str, Animation] = {
    a.name: a
    for a in [
        # standing on stage
        _a("idle", ("idle_01", "idle_02", "idle_03", "idle_02"), 2.0),
        _a("blink", ("blink_01", "blink_02", "blink_01"), 8.0, loop=False),
        _a("talk", ("talk_01", "talk_02", "talk_03", "talk_04", "talk_02"), 9.0),
        _a("think", ("think_01", "think_02", "think_01"), 2.0),
        _a("surprise", ("surprise_01", "surprise_02", "surprise_01"), 5.0, loop=False),
        _a("laugh", ("laugh_01", "laugh_02"), 7.0),
        _a("punchline", ("punchline_01", "punchline_02", "punchline_01"), 3.0),
        _a("reaction", ("reaction_01", "reaction_02", "reaction_01"), 3.0, loop=False),
        _a("proud", ("proud_01", "punchline_01", "proud_01"), 2.0),
        _a("sorry", ("sorry_01", "reaction_02", "sorry_01"), 2.0),
        # the states drawn on the reference sheet
        _a("bounce", ("bounce_01", "bounce_02", "bounce_03", "bounce_02"), 4.0),
        _a("wave", ("wave_01", "wave_02", "wave_03", "wave_02"), 4.0),
        _a("look", ("look_01", "look_02"), 1.5),
        _a("walk", ("walk_01", "walk_02", "walk_03", "walk_04"), 6.0),
        _a("run", ("run_01", "run_02", "run_03", "run_04"), 11.0),
    ]
}

EMOTION_ANIMATION: dict[Emotion, str] = {
    Emotion.NEUTRAL: "idle",
    Emotion.HAPPY: "punchline",
    Emotion.LAUGHING: "laugh",
    Emotion.SURPRISED: "surprise",
    Emotion.THINKING: "think",
    Emotion.SARCASTIC: "reaction",
    Emotion.PROUD: "proud",
    Emotion.SORRY: "sorry",
}


def animation_for_emotion(emotion: Emotion | str) -> str:
    key = emotion if isinstance(emotion, Emotion) else Emotion(str(emotion).lower())
    return EMOTION_ANIMATION[key]


class Player:
    """Time-based frame cursor: advance it from whatever clock the UI has."""

    def __init__(self, animation: str = "idle") -> None:
        self._elapsed = 0.0
        self.play(animation)

    def play(self, animation: str, restart: bool = True) -> None:
        if animation not in ANIMATIONS:
            raise ValueError(f"unknown animation {animation!r}")
        if restart or animation != self.animation.name:
            self._animation = ANIMATIONS[animation]
            self._index = 0
            self._elapsed = 0.0

    @property
    def animation(self) -> Animation:
        return self._animation

    @property
    def index(self) -> int:
        return self._index

    @property
    def frame_name(self) -> str:
        return self._animation.frames[self._index]

    @property
    def frame(self):
        return FRAMES[self.frame_name]

    @property
    def finished(self) -> bool:
        return not self._animation.loop and self._index >= len(self._animation.frames) - 1

    def advance(self, dt: float) -> bool:
        """Move the clock by `dt` seconds. True when the visible frame changed."""
        period = 1.0 / self._animation.fps
        self._elapsed += dt
        changed = False
        while self._elapsed >= period:
            self._elapsed -= period
            if self.finished:
                break
            self._index = (self._index + 1) % len(self._animation.frames)
            changed = True
        return changed

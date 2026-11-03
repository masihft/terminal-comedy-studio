"""The audience. Mostly silent, occasionally generous, sometimes brutal.

AGENTS.md §14: fake reactions must not be overused — silence is a punchline too.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..character.states import Emotion


@dataclass(frozen=True)
class Reaction:
    key: str
    text: str
    loud: bool = False

    def __str__(self) -> str:
        return self.text


LAUGH = Reaction("laugh", "...  😂  ha ha", True)
APPLAUSE = Reaction("applause", "...  👏  👏  👏", True)
AWKWARD = Reaction("awkward", "...", False)
BOO = Reaction("boo", "...  booo (from the back)", True)
SURPRISE = Reaction("surprise", "...  ohh", False)
SILENCE = Reaction("silence", "", False)

BIG_MODES = ("standup", "story", "random")


class Audience:
    """Decides whether the room makes a noise at all."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.last_loud = False
        self.landed = 0
        self.flopped = 0

    def react(self, text: str, *, emotion: Emotion = Emotion.NEUTRAL, mode: str = "stage") -> Reaction:
        if not text.strip():
            return SILENCE
        punchline = emotion in (Emotion.LAUGHING, Emotion.PROUD) or mode == "roast"
        roll = self.rng.random()
        if self.last_loud and roll < 0.72:
            self.last_loud = False
            self.flopped += 1
            return AWKWARD
        if punchline and roll < 0.8:
            self.last_loud = True
            self.landed += 1
            return LAUGH
        if mode in BIG_MODES and roll < 0.34:
            self.last_loud = True
            self.landed += 1
            return APPLAUSE
        if roll < 0.12:
            self.last_loud = True
            return BOO
        if roll < 0.2:
            return SURPRISE
        self.last_loud = False
        return SILENCE

    def summary(self) -> str:
        return f"{self.landed} landed, {self.flopped} flopped"

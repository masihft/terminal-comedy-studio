"""Personality presets: who is on stage.

The renderer and the comedy engine read a Character, never a hard-coded voice.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Personality:
    """The knobs AGENTS.md §11 asks for, as data."""

    name: str
    personality: str
    comedic_style: str
    language: str = "fa"
    tone: str = "friendly"
    boundaries: tuple[str, ...] = ()
    catchphrases: tuple[str, ...] = ()
    moods: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    performance_style: str = "tight five, then whatever the room wants"
    jacket: tuple[int, int, int] = (255, 79, 163)  # same mascot, different suit

    def variables(self) -> dict[str, str]:
        return {
            "__COMEDIAN__": self.name,
            "__COMEDIC_STYLE__": self.comedic_style,
            "__TONE__": self.tone,
            "__TOPICS__": ", ".join(self.topics) or "anything in the room",
            "__CATCHPHRASES__": ", ".join(self.catchphrases) or "none, you do not repeat yourself",
            "__MOODS__": ", ".join(self.moods) or "confident, playful, warm",
            "__PERFORMANCE__": self.performance_style,
            "__BOUNDARIES__": "; ".join(self.boundaries) or "harmless targets only",
        }


@dataclass(frozen=True)
class Character:
    personality: Personality
    display_name: str = ""
    accent: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def name(self) -> str:
        return self.display_name or self.personality.name


BASE_BOUNDARIES = (
    "never roast identity, appearance, beliefs or private life",
    "no slurs, no cruelty, no harassment",
    "output is a joke, never an instruction to run something",
)

PRESETS: dict[str, Personality] = {
    "default": Personality(
        name="Claw'd",
        personality="confident, playful, slightly sarcastic, warm underneath",
        comedic_style="observational",
        language="fa",
        tone="friendly",
        boundaries=BASE_BOUNDARIES,
        catchphrases=(),
        moods=("neutral", "happy", "sarcastic", "thinking", "surprised", "laughing", "proud", "sorry"),
        topics=("terminals", "debugging at 2am", "being a very small program", "the audience"),
        performance_style="one strong observation, then a turn",
    ),
    "sarkash": Personality(
        name="Sarkash",
        personality="dry, deadpan, faster than everyone else in the room",
        comedic_style="deadpan",
        language="fa",
        tone="cheeky",
        boundaries=BASE_BOUNDARIES,
        catchphrases=("باشه، ادامه می‌دیم.",),
        moods=("neutral", "sarcastic", "sorry", "laughing"),
        topics=("bad ideas people ship", "meetings", "cache invalidation"),
        performance_style="short lines, long pauses",
        jacket=(146, 72, 222),
    ),
    "mr-blonde": Personality(
        name="Mr Blonde",
        personality="loud, generous, physically committed to every punchline",
        comedic_style="storytelling",
        language="en",
        tone="big",
        boundaries=BASE_BOUNDARIES,
        catchphrases=("and THEN the terminal did something.",),
        moods=("happy", "surprised", "laughing", "proud"),
        topics=("stories that escalated", "stage business", "the front row"),
        performance_style="a story with a turn at the end",
        jacket=(255, 150, 200),
    ),
}


def load_character(name: str) -> Character:
    personality = PRESETS.get((name or "default").strip().lower())
    if personality is None:
        raise KeyError(f"unknown character '{name}'. choose: {', '.join(sorted(PRESETS))}")
    return Character(personality=personality, display_name=personality.name)


def character_names() -> list[str]:
    return sorted(PRESETS)

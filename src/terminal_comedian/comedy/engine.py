"""The comedy brain: turn what the user said into something performed.

A provider is an ingredient here, never the recipe. With no provider at all the
engine still opens the show, still does callbacks, still takes the bow.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..ai.provider import AIError, AIProvider, AIResponse
from ..character.personality import Character, load_character
from ..character.states import ANIMATIONS, Emotion, animation_for_emotion
from ..config.settings import Settings
from ..memory.session import Session
from ..prompts import DEFAULT_MODE, MODES, load_role, load_system
from . import jokes
from .reactions import Reaction

ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("standup", ("standup", "stand up", "tight five", "استندآپ", "استند اپ", "چند تا جوک", "ست کامل")),
    ("story", ("story", "tell me a story", "داستان", "قصه", "حکایت")),
    ("roast", ("roast", "بپیچ", "مسخره", "تند بگیر", "خورد بگیر")),
    ("joke", ("joke", "جوک", "بخندون", "شوخی", "بگو بخند")),
    ("random", ("random", "surprise", "هرچی", "هر چی", "سوپرایز", "هر کاری")),
)

MODE_ANIMATION = {
    "stage": "talk",
    "standup": "punchline",
    "chat": "talk",
    "roast": "reaction",
    "story": "bounce",
    "random": "wave",
}


@dataclass
class Performance:
    """One beat on stage: what is said, how it is said, how long it is held."""

    text: str = ""
    emotion: Emotion = Emotion.NEUTRAL
    animation: str = "idle"
    duration: float = 2.6
    source: str = "offline"
    error: str = ""
    reaction: Reaction | None = None

    @property
    def spoken(self) -> list[str]:
        return [line for line in self.text.splitlines() if line.strip()]


@dataclass
class ComedyEngine:
    character: Character
    settings: Settings
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self._counter = 0

    @property
    def language(self) -> str:
        return self.settings.language if self.settings.language in jokes.JOKES else "fa"

    def variables(self, session: Session) -> dict[str, str]:
        return {
            "__COMEDIAN__": self.character.name,
            "__LANGUAGE__": "Persian (فارسی)" if self.language == "fa" else "English",
            "__CALLBACKS__": session.context_block() or "- nothing yet, this is a fresh room",
        }

    def system_prompt(self, session: Session, mode: str) -> str:
        variables = self.variables(session)
        persona = self.character.personality
        voice = (
            f"Your style: {persona.comedic_style}. Tone: {persona.tone}. "
            f"Moods you can show: {', '.join(persona.moods)}. "
            f"Topics you like: {', '.join(persona.topics)}. "
            f"Signature: {persona.performance_style}. "
            f"Catchphrases, use at most once per show: {', '.join(persona.catchphrases) or 'none'}."
        )
        hard_boundaries = "Hard boundaries: " + "; ".join(persona.boundaries) + "."
        return "\n\n".join(
            [
                load_system().replace("__COMEDIAN__", variables["__COMEDIAN__"]).replace(
                    "__LANGUAGE__", variables["__LANGUAGE__"]
                ),
                voice,
                hard_boundaries,
                f"## Notes for this show\n{variables['__CALLBACKS__']}",
                load_role(mode).render(variables),
            ]
        )

    def messages(self, user_text: str, session: Session, mode: str) -> list[dict[str, str]]:
        turns = session.history()
        history = turns[-8:] if len(turns) > 8 else turns
        out: list[dict[str, str]] = [{"role": "system", "content": self.system_prompt(session, mode)}]
        out.extend({"role": turn["role"], "content": turn["content"]} for turn in history)
        out.append({"role": "user", "content": user_text or "Go on. Perform something."})
        return out

    def route(self, text: str, session: Session) -> str:
        """Natural language decides the mode; commands bypass this entirely."""
        lowered = (text or "").lower()
        for mode, needles in ROUTES:
            if any(needle in lowered for needle in needles):
                return mode
        return session.mode if session.mode in MODES else DEFAULT_MODE

    def perform(
        self,
        user_text: str = "",
        *,
        session: Session,
        mode: str | None = None,
        provider: AIProvider | None = None,
        on_delta=None,
    ) -> Performance:
        chosen = mode or self.route(user_text, session)
        if chosen not in MODES:
            chosen = DEFAULT_MODE
        if provider is not None:
            try:
                response = provider.generate_messages(
                    self.messages(user_text, session, chosen),
                    {
                        "temperature": load_role(chosen).temperature,
                        "max_tokens": load_role(chosen).max_tokens,
                        "on_delta": on_delta,
                    },
                )
                return self._from_response(response, chosen, provider)
            except AIError as error:
                performance = self.offline(chosen, session)
                performance.error = str(error)
                return performance
        return self.offline(chosen, session)

    def _from_response(self, response: AIResponse, mode: str, provider: AIProvider) -> Performance:
        animation = response.animation
        if animation not in ANIMATIONS:
            animation = animation_for_emotion(response.emotion)
        return Performance(
            text=response.text,
            emotion=response.emotion,
            animation=animation,
            duration=response.duration,
            source=f"ai:{provider.id}",
        )

    def offline(self, mode: str, session: Session | None = None) -> Performance:
        self._counter += 1
        language = self.language
        index = self._counter
        if mode == "story":
            return Performance(
                text=jokes.pick(jokes.STORIES, language, 0),
                emotion=Emotion.THINKING,
                animation="bounce",
                duration=9.0,
            )
        if mode == "roast":
            return Performance(
                text=jokes.pick(jokes.ROASTS, language, index),
                emotion=Emotion.SARCASTIC,
                animation="reaction",
                duration=4.0,
            )
        if mode == "standup":
            lines = jokes.JOKES.get(language, jokes.JOKES["en"])
            start = index % max(1, len(lines))
            picked = [lines[(start + offset) % len(lines)] for offset in range(3)]
            return Performance(
                text="\n\n".join(picked),
                emotion=Emotion.HAPPY,
                animation="punchline",
                duration=7.0,
            )
        if mode == "random":
            pool = [jokes.pick(jokes.JOKES, language, index), jokes.pick(jokes.ONE_LINERS, language, index)]
            return Performance(
                text=self.rng.choice([line for line in pool if line]),
                emotion=Emotion.HAPPY,
                animation="wave",
                duration=3.5,
            )
        if mode == "chat":
            text = jokes.pick(jokes.THINKING, language, index) if index % 3 == 0 else jokes.pick(jokes.JOKES, language, index)
            return Performance(text=text, emotion=Emotion.NEUTRAL, animation="talk", duration=3.2)
        return Performance(
            text=jokes.pick(jokes.JOKES, language, index),
            emotion=Emotion.HAPPY,
            animation=MODE_ANIMATION.get(mode, "talk"),
            duration=3.4,
        )

    def opener(self, session: Session) -> Performance:
        return Performance(
            text=jokes.pick(jokes.OPENERS, self.language, session.bits_told),
            emotion=Emotion.HAPPY,
            animation="wave",
            duration=3.0,
        )

    def closer(self, session: Session) -> Performance:
        text = jokes.pick(jokes.CLOSERS, self.language, session.bits_told)
        persona = self.character.personality
        catchphrases = persona.catchphrases if persona.language == self.language else ()
        if catchphrases:  # the one place a catchphrase belongs: the way off stage, in the show's language
            text = f"{text}\n{catchphrases[session.bits_told % len(catchphrases)]}"
        return Performance(
            text=text,
            emotion=Emotion.PROUD,
            animation="proud",
            duration=2.2,
        )

    def react_to_audience(self, reaction: Reaction, session: Session) -> Performance:
        if reaction.key == "boo":
            return Performance(
                text=jokes.pick(jokes.APOLOGY, self.language, session.bits_told),
                emotion=Emotion.SORRY,
                animation="sorry",
                duration=2.4,
            )
        if reaction.key == "silence":
            return Performance(text="", emotion=Emotion.THINKING, animation="look", duration=1.6)
        return Performance(
            text="..." if reaction.key == "awkward" else "",
            emotion=Emotion.HAPPY,
            animation="laugh" if reaction.loud else "idle",
            duration=1.4,
        )

    def applause_line(self, session: Session) -> Performance:
        return self.react_to_audience(Reaction("applause", ""), session)


def engine_for(settings: Settings | None = None, character_name: str = "") -> ComedyEngine:
    settings = settings or Settings.load()
    return ComedyEngine(
        character=load_character(character_name or settings.character),
        settings=settings,
    )

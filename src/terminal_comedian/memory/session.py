"""What the comedian knows about this show, kept in RAM.

AGENTS.md §21: lightweight session context. No database to remember a few
lines of comedy.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ..comedy.callbacks import CallbackEngine
from ..comedy.reactions import Audience

MAX_TURNS = 12


@dataclass
class Session:
    """One show: the mode, the transcript, the room and the memory."""

    mode: str = "stage"
    language: str = "fa"
    turns: deque = field(default_factory=lambda: deque(maxlen=MAX_TURNS))
    audience: Audience = field(default_factory=Audience)
    callbacks: CallbackEngine = field(default_factory=CallbackEngine)
    bits_told: int = 0
    provider_label: str = "offline"

    def record(self, role: str, content: str) -> None:
        if content.strip():
            self.turns.append({"role": role, "content": content.strip()})

    def history(self) -> list[dict[str, str]]:
        return [dict(turn) for turn in self.turns]

    def note_exchange(self, user_text: str, spoken: str) -> None:
        self.record("user", user_text)
        self.callbacks.note_user(user_text, self.language)
        if spoken:
            self.record("assistant", spoken)
            self.callbacks.note_bit(spoken)
            self.bits_told += 1

    def reset(self) -> None:
        self.turns.clear()
        self.callbacks.reset()
        self.bits_told = 0

    def context_block(self) -> str:
        """The stage notes injected into the prompt: room, callbacks, running order."""
        lines: list[str] = []
        topics = self.callbacks.suggest()
        if topics:
            lines.append(f"Topics the user has raised this session: {', '.join(topics)}.")
        if self.bits_told:
            lines.append(f"You have already performed {self.bits_told} bits in this show. Do not repeat them.")
        if self.audience.landed or self.audience.flopped:
            lines.append(f"Audience so far: {self.audience.summary()}.")
        recent = [turn["content"] for turn in list(self.turns)[-4:] if turn["role"] == "assistant"]
        if recent:
            lines.append("Your last lines (do not reuse these): " + " | ".join(recent[-2:]))
        return "\n".join(f"- {line}" for line in lines)

    def __len__(self) -> int:
        return len(self.turns)

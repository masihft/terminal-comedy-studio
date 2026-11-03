"""Callbacks: the comedian remembers the room, on purpose.

AGENTS.md §13: intentional callbacks only, never an echo chamber.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_STOP = {
    "fa": {"و", "به", "از", "که", "با", "برای", "این", "آن", "هست", "نیست", "خوب", "خیلی", "من", "تو", "شما", "را", "ی", "در"},
    "en": {"the", "and", "for", "that", "with", "this", "have", "has", "you", "are", "was", "not", "but", "get", "got", "a", "i", "to", "of", "in", "it", "my", "so", "an"},
}
_WORD = re.compile(r"[\w\u0600-\u06FF']{3,}", re.UNICODE)


@dataclass
class CallbackEngine:
    """Collects what the user actually talked about, and offers it back later."""

    topics: list[str] = field(default_factory=list)
    bits: list[str] = field(default_factory=list)
    offered: set[str] = field(default_factory=set)
    limit: int = 8
    per_message: int = 3

    def note_user(self, text: str, language: str = "en") -> list[str]:
        stop = _STOP.get(language, set()) | _STOP["en"]
        found: list[str] = []
        for word in _WORD.findall(text.lower()):
            if word in stop or word in self.topics:
                continue
            found.append(word)
        for word in found[: self.per_message]:
            self.topics.append(word)
        self.topics = self.topics[-self.limit :]
        return found[: self.per_message]

    def note_bit(self, text: str) -> None:
        first = text.strip().splitlines()[0] if text.strip() else ""
        if first and first not in self.bits:
            self.bits.append(first)
        self.bits = self.bits[-self.limit :]

    def suggest(self, count: int = 3) -> list[str]:
        """Offer the oldest unused topic first: a callback should be news again."""
        unused = [topic for topic in self.topics if topic not in self.offered]
        picked = unused[:count]
        if not picked:
            self.offered.clear()
            picked = self.topics[-count:]
        self.offered.update(picked)
        return picked

    def used_bit(self, text: str) -> bool:
        return text.strip() in self.bits

    def reset(self) -> None:
        self.topics.clear()
        self.bits.clear()
        self.offered.clear()

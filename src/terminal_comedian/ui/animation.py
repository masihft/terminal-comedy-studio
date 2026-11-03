"""Repainting the stage in place while the comedian talks.

The CLI owns the screen only for the stage block; everything else scrolls
normally, so the user's own terminal history stays readable.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from ..character.states import ANIMATIONS, Player
from .terminal import Capabilities

MAX_FPS = 20.0


class StagePainter:
    """Writes a block of lines, then overwrites exactly that block next time."""

    def __init__(self, caps: Capabilities, stream=None) -> None:
        self.caps = caps
        self.stream = stream
        self._written = 0

    def _write(self, text: str) -> None:
        import sys

        (self.stream or sys.stdout).write(text)
        (self.stream or sys.stdout).flush()

    def show(self, lines: Sequence[str]) -> None:
        if self.caps.tty and self._written:
            self._write(f"\x1b[{self._written}A\r\x1b[0J")
        self._write("\n".join(lines) + "\n")
        self._written = len(lines)

    def commit(self, lines: Sequence[str] | None = None) -> None:
        """Leave the block on screen and stop overwriting it."""
        if lines is not None:
            self.show(lines)
        self._written = 0

    def print(self, text: str) -> None:
        """Write below the live block, then bring the block back."""
        held = self._written
        self._written = 0
        self._write(text.rstrip("\n") + "\n")
        self._written = held


def animate(
    animation: str,
    seconds: float,
    render: Callable[[str], None],
    caps: Capabilities,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Run one animation for a while. Returns how many frames were drawn."""
    player = Player(animation if animation in ANIMATIONS else "idle")
    period = min(1.0 / player.animation.fps, 1.0 / MAX_FPS)
    deadline = clock() + max(0.0, seconds)
    drawn = 0
    render(player.frame_name)
    drawn += 1
    while clock() < deadline:
        start = clock()
        step = min(period, max(0.0, deadline - start))
        sleep(step)
        if player.advance(clock() - start):
            render(player.frame_name)
            drawn += 1
        elif not player.animation.loop and player.finished:
            break
    return drawn

"""Input: natural language first, commands second (AGENTS.md §20).

The command table is data, so help text and dispatch come from the same place.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    name: str
    help: str
    aliases: tuple[str, ...] = ()
    needs_argument: bool = False

    @property
    def keys(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


COMMANDS: tuple[Command, ...] = (
    Command("help", "what this is and what you can say"),
    Command("joke", "one joke, right now"),
    Command("standup", "a short set: several jokes with structure"),
    Command("story", "a short comedic story"),
    Command("roast", "roast something harmless — /roast your git workflow"),
    Command("random", "the comedian picks what to perform"),
    Command("mode", "show or set the default mode", needs_argument=False),
    Command("character", "show or switch the comedian on stage", needs_argument=False),
    Command("connect", "connect a model: browser sign-in or API key — /connect openrouter", ("login",)),
    Command("model", "pick the model — /model, or /model gpt-4o-mini"),
    Command("logout", "forget the saved key for this provider and go offline"),
    Command("provider", "show or switch the AI provider", needs_argument=False),
    Command("settings", "provider, language and what gets sent where"),
    Command("save", "write this set to a markdown file — /save my-set.md"),
    Command("reset", "forget this session and start a fresh show"),
    Command("exit", "leave the stage", ("quit",)),
)

_BY_KEY: dict[str, Command] = {key: command for command in COMMANDS for key in command.keys}


def parse(line: str) -> tuple[Command | None, str]:
    """Split a typed line into (command, argument). Non-commands return (None, text)."""
    text = (line or "").strip()
    if not text.startswith("/"):
        return None, text
    head, _, argument = text[1:].partition(" ")
    command = _BY_KEY.get(head.lower())
    if command is None:
        return None, text
    return command, argument.strip()


def help_lines(width: int = 60) -> list[str]:
    rows = []
    for command in COMMANDS:
        names = ", ".join("/" + key for key in command.keys)
        rows.append(f"  {names:<28} {command.help}")
    return rows


def unknown(name: str) -> str:
    known = " ".join("/" + command.name for command in COMMANDS)
    return f"unknown command '{name}'. try: {known}"

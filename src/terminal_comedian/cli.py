"""The `comedian` command: a line-based CLI, not a full-screen app.

Startup order matters (AGENTS.md §38): stage and character first, configuration
never before the comedian appears.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field

from . import __version__
from .ai.provider import AIProvider, ProviderNotConfigured, create_provider, provider_ids
from .character.personality import character_names, load_character
from .character.states import ANIMATIONS, Player
from .comedy.engine import ComedyEngine, Performance
from .comedy.reactions import Audience
from .config.credentials import save_values, user_env_path
from .config.settings import Settings
from .connect import Wizard
from .harness import Decision, Harness, Permissions, ToolCall, Workspace
from .memory.session import Session
from .prompts import MODES, mode_help
from .ui.animation import StagePainter, animate
from .ui.input import Command, help_lines, parse, unknown
from .ui.input import COMMANDS
from .ui.stage import banner, stage_lines
from .ui.terminal import Capabilities, detect, silent_terminal

PROMPT = "\x1b[38;2;255;79;163m>\x1b[0m "
PLAIN_PROMPT = "> "
PAINT_INTERVAL = 0.05


@dataclass
class Show:
    """Everything one running comedian needs."""

    settings: Settings
    caps: Capabilities
    engine: ComedyEngine
    session: Session
    provider: AIProvider | None = None
    painter: StagePainter = field(init=False)
    exit_code: int = 0
    _harness: Harness | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.painter = StagePainter(self.caps)
        self.session.provider_label = self.provider.id if self.provider else "offline"
        self.session.language = self.settings.language

    @property
    def comedian(self) -> str:
        return self.engine.character.name

    def note(self) -> str:
        if self.provider:
            return f"ai: {self.provider.id} · model: {self.provider.model or 'default'}"
        return "ai: offline · local material only"

    def render(self, speech: str, frame_name: str, mode: str | None = None) -> list[str]:
        return stage_lines(
            comedian=self.comedian,
            speech=speech,
            frame_name=frame_name,
            caps=self.caps,
            mode=mode or self.session.mode,
            note=self.note(),
            jacket=self.engine.character.personality.jacket,
        )

    def announce(self) -> None:
        for line in banner(self.caps, self.comedian):
            print(line)
        if self.provider:
            print(
                f"AI: {self.provider.label} at {self.provider.base_url} — "
                "only what you type here is sent to it. Nothing else. (/settings)"
            )
        else:
            print("AI: none configured. The comedian performs offline material. (/connect)")
        print()

    def speak(self, performance: Performance, *, live: bool = True) -> None:
        mode = self.session.mode
        if live and self.caps.tty:
            with silent_terminal():
                self.painter.show(self.render(performance.text, ANIMATIONS[performance.animation].frames[0], mode))
                if performance.duration > 0.15:
                    animate(
                        performance.animation,
                        min(performance.duration, 4.0),
                        lambda frame: self.painter.show(self.render(performance.text, frame, mode)),
                        self.caps,
                    )
        self.painter.commit(self.render(performance.text, ANIMATIONS[performance.animation].frames[-1], mode))
        reaction = self.session.audience.react(performance.text, emotion=performance.emotion, mode=mode)
        if reaction.text:
            print(f"   {reaction.text}")
        if performance.error:
            print(f"   (the provider did not answer: {performance.error})")

    def perform(self, text: str = "", mode: str | None = None) -> Performance:
        chosen = mode or self.engine.route(text, self.session)
        buffer = {"text": "", "painted": 0.0}
        player = Player("talk")

        def on_delta(piece: str) -> None:
            buffer["text"] += piece
            now = time.monotonic()
            if not self.caps.tty or now - buffer["painted"] < PAINT_INTERVAL:
                return
            step = now - buffer["painted"]
            buffer["painted"] = now
            player.advance(step)
            self.painter.show(self.render(buffer["text"], player.frame_name, chosen))

        with silent_terminal():
            performance = self.engine.perform(
                text,
                session=self.session,
                mode=chosen,
                provider=self.provider,
                on_delta=on_delta if self.caps.tty else None,
            )
        if buffer["text"] and performance.text == buffer["text"]:
            self.painter.commit(self.render(performance.text, ANIMATIONS[performance.animation].frames[-1], chosen))
            reaction = self.session.audience.react(performance.text, emotion=performance.emotion, mode=chosen)
            if reaction.text:
                print(f"   {reaction.text}")
        else:
            self.speak(performance)
        self.session.note_exchange(text, performance.text)
        return performance

    def set_mode(self, name: str) -> str:
        if name in MODES:
            self.session.mode = name
            return f"mode: {name}"
        return "modes: " + ", ".join(MODES)

    def set_character(self, name: str) -> str:
        try:
            self.engine.character = load_character(name or self.settings.character)
        except KeyError as error:
            return f"{error} — characters: {', '.join(character_names())}"
        self.session.reset()
        return f"{self.comedian} takes the mic."

    def apply(self, values: dict[str, str | None]) -> str:
        """Swap in new settings (None removes a key) and rebuild the provider."""
        environ = {**self.settings.environ, **{k: v for k, v in values.items() if v is not None}}
        for key, value in values.items():
            if value is None:
                environ.pop(key, None)
        settings = Settings.load(environ=environ)
        try:
            provider = create_provider(settings)
        except ProviderNotConfigured as error:
            return str(error)
        self.provider = provider
        self.settings = settings
        self.engine.settings = settings
        self.session.provider_label = provider.id if provider else "offline"
        if provider is None:
            return "provider: offline (local material only)"
        if not provider.is_configured:
            return f"{provider.label} needs: {provider.missing()} — try /connect {provider.id}"
        return f"{provider.label} at {provider.base_url}, model {provider.model or 'default'}."

    def set_provider(self, name: str) -> str:
        if name in {"", "none", "offline"}:
            name = "offline"
        return self.apply({"AI_PROVIDER": name})

    def wizard(self) -> Wizard:
        return Wizard(settings=self.settings)

    def connect(self, argument: str) -> str:
        values = self.wizard().connect(argument.lower())
        return self.apply(values) if values else ""

    def choose_model(self, argument: str) -> str:
        if not self.provider:
            return "no model on stage. /connect first."
        values = self.wizard().model(self.provider, argument)
        return self.apply(values) if values else ""

    def logout(self) -> str:
        if not self.provider:
            return "already offline."
        provider = self.provider
        forget: dict[str, str | None] = {"AI_PROVIDER": None}
        if provider.key_env:
            forget[provider.key_env] = None
        lines = []
        path = user_env_path()
        if path.is_file():
            save_values(forget, path)
            lines.append(f"forgot the {provider.label} key saved in {path}.")
        lines.append(self.apply({**forget, "AI_PROVIDER": "offline"}))
        if provider.key_env and provider.key_env in os.environ:
            lines.append(f"note: {provider.key_env} is still set in your shell.")
        return "\n".join(lines)

    def settings_lines(self) -> list[str]:
        rows = [
            f"provider   : {self.session.provider_label}",
            f"model      : {self.provider.model if self.provider else '(none — offline)'}",
            f"base url   : {self.provider.base_url if self.provider else '(no network calls)'}",
            f"language   : {self.settings.language}",
            f"character  : {self.comedian} ({self.engine.character.personality.comedic_style})",
            f"mode       : {self.session.mode}",
            f"terminal   : {self.caps.width}x{self.caps.height} "
            f"colour={'truecolor' if self.caps.colour else 'plain'} unicode={self.caps.unicode}",
            f"animations : {len(ANIMATIONS)}",
            "",
            "sent to the provider: your typed line, the last few turns of this session,",
            "and the persona prompt. Never: files, environment variables, or history.",
        ]
        if self.provider:
            missing = self.provider.missing()
            if missing:
                rows.append(f"missing configuration: {missing}")
        return rows

    def harness(self) -> Harness:
        if self._harness is None:
            self._harness = Harness(
                engine=self.engine,
                workspace=Workspace(Path.cwd()),
                approve=_ask_on_the_line,
                permissions=Permissions(mode=self.settings.get("COMEDIAN_LOOK", "ask").lower()),
                notify=lambda kind, text: print(f"   ({text})"),
            )
        return self._harness

    def look(self, argument: str) -> None:
        harness = self.harness()
        if self.provider is None:
            performance = harness.look(self.session)
        else:
            performance = harness.run(
                argument or "Look at my project folder and do a bit about it.",
                session=self.session,
                mode="roast",
                provider=self.provider,
            )
        self.speak(performance)
        self.session.note_exchange("/look", performance.text)

    def save_set(self, argument: str) -> str:
        if not self.session.script:
            return "nothing to save yet. say something first."
        path = Path(argument or time.strftime("set-%Y%m%d-%H%M%S.md")).expanduser()
        try:
            with path.open("x", encoding="utf-8") as handle:  # "x": never overwrite a file
                handle.write(self.session.as_markdown(self.comedian))
        except FileExistsError:
            return f"{path} already exists. pick another name."
        except OSError as error:
            return f"could not save: {error.strerror or error}"
        return f"saved the set to {path}"

    def run_command(self, command: Command, argument: str) -> bool:
        name = command.name
        if name == "help":
            print("\n".join(banner(self.caps, self.comedian)))
            print("say anything, or use a command:")
            print("\n".join(help_lines()))
            print("\nmodes:")
            for mode, description in mode_help():
                print(f"  /{mode:<9} {description}")
            print("\n/exit leaves the stage.")
            return True
        if name in {"joke", "standup", "story", "roast", "random"}:
            self.perform(argument or "", mode=name)
            return True
        if name == "mode":
            print(self.set_mode(argument.lower()))
            return True
        if name == "character":
            print(self.set_character(argument.lower()))
            return True
        if name == "look":
            self.look(argument)
            return True
        if name == "tools":
            choice = argument.lower()
            if choice in {"ask", "allow", "off"}:
                self.harness().permissions = Permissions(mode=choice)
            print(f"folder access: {self.harness().permissions.mode} (/tools ask | allow | off)")
            return True
        if name == "connect":
            result = self.connect(argument)
            if result:
                print(result)
            return True
        if name == "model":
            result = self.choose_model(argument)
            if result:
                print(result)
            return True
        if name == "logout":
            print(self.logout())
            return True
        if name == "provider":
            print(self.set_provider(argument.lower()))
            return True
        if name == "settings":
            print("\n".join(self.settings_lines()))
            return True
        if name == "save":
            print(self.save_set(argument))
            return True
        if name == "update":
            from .updater import cli as update

            update()
            return True
        if name == "reset":
            self.session.reset()
            print("fresh room. nothing remembered.")
            return True
        if name in {"exit", "quit"}:
            return False
        return True

    def repl(self) -> int:
        self.announce()
        self.speak(self.engine.opener(self.session))
        prompt = PROMPT if self.caps.colour else PLAIN_PROMPT
        while True:
            try:
                line = input(prompt)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                self.exit_code = 130
                break
            text = line.strip()
            if not text:
                continue
            command, argument = parse(text)
            if command is None:
                if text.startswith("/"):
                    print(unknown(text.split(maxsplit=1)[0]))
                    continue
                self.perform(text)
                continue
            if not self.run_command(command, argument):
                self.speak(self.engine.closer(self.session), live=False)
                break
        return self.exit_code

    def one_shot(self, mode: str, text: str) -> int:
        performance = self.perform(text, mode=mode)
        print(performance.text)
        return self.exit_code


def _ask_on_the_line(call: ToolCall) -> Decision:
    try:
        answer = input(f"   the comedian wants to {call.description}. allow? [y]es / [a]lways / [N]o: ")
    except (EOFError, KeyboardInterrupt):
        return Decision.DENY
    return {"y": Decision.ONCE, "yes": Decision.ONCE, "a": Decision.ALWAYS}.get(answer.strip().lower(), Decision.DENY)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comedian",
        description="An AI stand-up comedian living inside your terminal.",
        epilog="no arguments opens the stage: " + ", ".join("/" + c.name for c in COMMANDS),
    )
    parser.add_argument("--version", action="version", version=f"comedian {__version__}")
    parser.add_argument("--provider", metavar="ID", help=f"one of: {', '.join(provider_ids())}, offline")
    parser.add_argument("--model", metavar="NAME", help="model name for the chosen provider")
    parser.add_argument("--character", metavar="NAME", help=f"one of: {', '.join(character_names())}")
    parser.add_argument("--language", metavar="CODE", help="en (default) or fa (Persian)")
    parser.add_argument("--mode", metavar="NAME", help=f"default mode: {', '.join(MODES)}")
    parser.add_argument("--no-color", action="store_true", help="plain text, no ANSI")
    parser.add_argument("--plain", action="store_true", help="no colour and no Unicode blocks")
    parser.add_argument("--classic", action="store_true", help="the line-by-line stage instead of the full-screen app")
    parser.add_argument(
        "--look",
        choices=["ask", "allow", "off"],
        help="may the comedian look at this folder? ask (default), allow, off",
    )
    parser.add_argument(
        "bit",
        nargs="?",
        choices=["joke", "standup", "story", "roast", "random", "chat", "stage", "update"],
        help="perform one bit and exit, or `update` to get the newest comedian",
    )
    parser.add_argument("text", nargs="*", help="the topic for that bit")
    return parser


def make_show(argv: list[str] | None = None) -> Show:
    args = build_parser().parse_args(argv)
    environ_overrides: dict[str, str] = {}
    if args.provider:
        environ_overrides["AI_PROVIDER"] = args.provider
    if args.model:
        environ_overrides["AI_MODEL"] = args.model
    if args.character:
        environ_overrides["COMEDIAN_CHARACTER"] = args.character
    if args.language:
        environ_overrides["LANGUAGE"] = args.language
    settings = Settings.load(environ={**Settings.load().environ, **environ_overrides})
    caps = detect(environ=settings.environ)
    if args.no_color or args.plain:
        caps = Capabilities(
            width=caps.width, height=caps.height, tty=caps.tty, truecolor=False, unicode=not args.plain and caps.unicode
        )
    engine = ComedyEngine(character=load_character(settings.character), settings=settings)
    session = Session(mode=(args.mode or "stage").lower(), language=settings.language, audience=Audience())
    provider = create_provider(settings)
    return Show(settings=settings, caps=caps, engine=engine, session=session, provider=provider)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    if args.bit == "update":
        from .updater import cli as update

        return update()
    try:
        show = make_show(argv)
    except ProviderNotConfigured as error:
        print(f"comedian: {error}", file=sys.stderr)
        return 1
    if args.bit:
        mode = "stage" if args.bit in {"chat", "stage"} else args.bit
        return show.one_shot(mode, " ".join(args.text))
    if args.classic or args.plain or not (sys.stdin.isatty() and sys.stdout.isatty()):
        return show.repl()
    try:
        from .ui.app import run
    except ImportError:  # textual missing: the classic stage still works
        return show.repl()
    look = args.look or show.settings.get("COMEDIAN_LOOK", "ask").lower()
    return run(show, Path.cwd(), look if look in {"ask", "allow", "off"} else "ask")

"""The full-screen stage, built on Textual.

Layout, top to bottom: a lit stage with the mascot and its speech bubble, the
running transcript, a slash-command menu that opens above the input, the input
line, and a status bar. Model calls and folder looks run in worker threads, so
the mascot keeps animating while the comedian thinks.
"""

from __future__ import annotations

import functools
import random
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList, RichLog, Static
from textual.widgets.option_list import Option

from ..character.frames import FRAMES
from ..character.states import ANIMATIONS, Player
from ..comedy.engine import Performance
from ..connect import Wizard
from ..harness import Decision, Harness, Permissions, ToolCall, Workspace
from ..prompts import MODES, mode_help
from .input import COMMANDS, parse
from .pixels import frame_text
from .terminal import is_rtl, sanitize

PINK = "#ff4fa3"
PURPLE = "#9b6aff"
DIM = "#8b7485"
TICK = 0.08
BLINK_EVERY = (2.5, 6.0)


# ----------------------------------------------------------------- modals --


class PermissionScreen(ModalScreen[Decision]):
    """Claude Code style: the comedian asks before it looks."""

    BINDINGS = [
        Binding("y", "decide('once')", "yes"),
        Binding("a", "decide('always')", "always"),
        Binding("n,escape", "decide('deny')", "no"),
    ]

    def __init__(self, comedian: str, call: ToolCall) -> None:
        super().__init__()
        self.comedian = comedian
        self.call = call

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(Text(f"{self.comedian} wants to {self.call.description}."), id="question")
            yield Label("read-only · stays on this machine unless an AI provider is connected", classes="hint")
            yield OptionList(
                Option("yes, this once", id="once"),
                Option(Text(f"yes, and don't ask again for {self.call.name} this show"), id="always"),
                Option("no", id="deny"),
                id="choices",
            )

    def action_decide(self, choice: str) -> None:
        self.dismiss(Decision(choice))

    @on(OptionList.OptionSelected)
    def chosen(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(Decision(event.option.id))


class PickerScreen(ModalScreen[str | None]):
    """Arrow keys to move, type to search, Enter to pick, Esc to cancel."""

    BINDINGS = [Binding("escape", "cancel", "cancel")]
    LIMIT = 200

    def __init__(self, title: str, options: list[str], default: str = "", allow_custom: bool = False) -> None:
        super().__init__()
        self.title_text = title
        self.options = options
        self.default = default
        self.allow_custom = allow_custom

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(Text(self.title_text), id="question")
            searchable = self.allow_custom or len(self.options) > 8
            yield Input(
                placeholder="type to search, or a name of your own" if self.allow_custom else "type to search",
                id="search",
                classes="" if searchable else "hidden",
            )
            yield OptionList(id="choices")
            yield Label("↑↓ move · enter pick · esc cancel", classes="hint")

    def on_mount(self) -> None:
        self._fill("")
        if self.query_one("#search").has_class("hidden"):
            self.query_one("#choices").focus()
        else:
            self.query_one("#search").focus()

    def _fill(self, needle: str) -> None:
        listing = self.query_one("#choices", OptionList)
        listing.clear_options()
        matches = [o for o in self.options if needle.lower() in o.lower()][: self.LIMIT]
        for index, name in enumerate(matches):
            marker = "● " if name == self.default else "  "
            listing.add_option(Option(Text(marker + name), id=str(self.options.index(name))))
        if matches:
            highlight = matches.index(self.default) if self.default in matches else 0
            listing.highlighted = highlight

    @on(Input.Changed, "#search")
    def search(self, event: Input.Changed) -> None:
        self._fill(event.value)

    def on_key(self, event: events.Key) -> None:
        if event.key in ("up", "down") and isinstance(self.focused, Input):
            listing = self.query_one("#choices", OptionList)
            listing.action_cursor_down() if event.key == "down" else listing.action_cursor_up()
            event.stop()

    @on(Input.Submitted, "#search")
    def submit(self, event: Input.Submitted) -> None:
        listing = self.query_one("#choices", OptionList)
        typed = event.value.strip()
        if self.allow_custom and typed and typed in self.options:
            self.dismiss(typed)
        elif listing.highlighted is not None and listing.option_count:
            self.dismiss(self.options[int(listing.get_option_at_index(listing.highlighted).id)])
        elif self.allow_custom and typed:
            self.dismiss(typed)
        elif not typed and self.default:
            self.dismiss(self.default)

    @on(OptionList.OptionSelected, "#choices")
    def chosen(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(self.options[int(event.option.id)])

    def action_cancel(self) -> None:
        self.dismiss(None)


class PromptScreen(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def __init__(self, prompt: str, password: bool = False) -> None:
        super().__init__()
        self.prompt = prompt.rstrip(": ")
        self.password = password

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(Text(self.prompt), id="question")
            yield Input(password=self.password, id="answer")
            yield Label(
                "typed text is hidden · enter to confirm · esc cancel" if self.password else "enter to confirm · esc cancel",
                classes="hint",
            )

    def on_mount(self) -> None:
        self.query_one("#answer").focus()

    @on(Input.Submitted)
    def submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------- widgets --


class Mascot(Static):
    def __init__(self, jacket, **kwargs) -> None:
        super().__init__(**kwargs)
        self.jacket = jacket
        self.frame_name = "idle_01"

    def show(self, frame_name: str) -> None:
        if frame_name != self.frame_name:
            self.frame_name = frame_name
            self.refresh()

    def render(self) -> Text:
        return frame_text(FRAMES[self.frame_name], self.jacket)


class CommandInput(Input):
    """The input line: opens the slash menu, keeps a history like a shell."""

    BINDINGS = [
        Binding("up", "menu_or_history(-1)", show=False),
        Binding("down", "menu_or_history(1)", show=False),
        Binding("tab", "complete", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.history: list[str] = []
        self.cursor_in_history = 0

    def remember(self, line: str) -> None:
        if line and (not self.history or self.history[-1] != line):
            self.history.append(line)
        self.cursor_in_history = len(self.history)

    def action_menu_or_history(self, step: int) -> None:
        menu = self.app.query_one("#menu", OptionList)
        if menu.display:
            menu.action_cursor_down() if step > 0 else menu.action_cursor_up()
            return
        if not self.history:
            return
        self.cursor_in_history = max(0, min(len(self.history), self.cursor_in_history + step))
        self.value = self.history[self.cursor_in_history] if self.cursor_in_history < len(self.history) else ""
        self.cursor_position = len(self.value)

    def action_complete(self) -> None:
        self.app.complete_from_menu()  # type: ignore[attr-defined]


# -------------------------------------------------------------------- app --


class ComedianApp(App):
    """Terminal Comedy Studio, full screen."""

    TITLE = "Terminal Comedy Studio"
    CSS = f"""
    Screen {{ background: #0d0710; color: #f0e8f0; }}
    #stage {{ height: auto; border: round {PINK}; border-title-color: {PINK}; border-subtitle-color: {DIM};
              padding: 0 1; margin: 0 1; }}
    #stage-row {{ height: auto; align: center middle; }}
    #mascot-column {{ width: 56; height: auto; align: center top; }}
    #mascot {{ width: 54; height: 9; }}
    #nameplate {{ width: 54; text-align: center; color: {PINK}; text-style: bold; }}
    #bubble {{ width: 1fr; min-width: 24; height: auto; max-height: 14; border: round {PURPLE}; padding: 0 1;
               margin: 1 0 0 2; }}
    #bubble.rtl {{ text-align: right; }}
    #bubble.thinking {{ color: {DIM}; text-style: italic; }}
    #stage.narrow #stage-row {{ layout: vertical; }}
    #stage.narrow #bubble {{ margin: 0; width: 100%; }}
    #log {{ height: 1fr; margin: 0 1; padding: 0 1; scrollbar-size-vertical: 1; scrollbar-size-horizontal: 0; background: #0d0710; }}
    #menu {{ display: none; height: auto; max-height: 12; margin: 0 2; border: round {DIM}; background: #170b17; }}
    #prompt-row {{ height: 3; margin: 0 1; }}
    #prompt {{ border: round {PINK}; background: #0d0710; }}
    #prompt:focus {{ border: round {PINK}; }}
    #status {{ height: 1; padding: 0 2; color: {DIM}; background: #170b17; }}
    ModalScreen {{ align: center middle; background: #0d0710 70%; }}
    #dialog {{ width: 76; max-width: 95%; height: auto; border: round {PINK}; background: #170b17; padding: 1 2; }}
    #question {{ color: {PINK}; text-style: bold; margin-bottom: 1; width: 100%; }}
    .hint {{ color: {DIM}; margin-top: 1; }}
    .hidden {{ display: none; }}
    #choices {{ height: auto; max-height: 16; background: #170b17; border: none; }}
    """

    BINDINGS = [
        Binding("ctrl+c", "leave", "quit", priority=True, show=False),
        Binding("ctrl+d", "leave", "quit", show=False),
        Binding("escape", "close_menu", show=False),
        Binding("ctrl+l", "clear_log", show=False),
    ]

    def __init__(self, show, workspace: Path | None, look_mode: str = "ask") -> None:
        super().__init__()
        self.show = show  # the cli.Show: settings, engine, session, provider and its string commands
        self.player = Player("idle")
        self.hold = 0.0
        self.next_blink = random.uniform(*BLINK_EVERY)
        self.busy = False
        self.harness = Harness(
            engine=show.engine,
            workspace=Workspace(workspace) if workspace else None,
            approve=self.approve,
            permissions=Permissions(mode=look_mode),
            notify=lambda kind, text: self.call_from_thread(self.note_tool, kind, text),
        )

    # ------------------------------------------------------------ layout --
    def compose(self) -> ComposeResult:
        personality = self.show.engine.character.personality
        with Vertical(id="stage"):
            with Horizontal(id="stage-row"):
                with Vertical(id="mascot-column"):
                    yield Mascot(personality.jacket, id="mascot")
                    yield Label(Text(f"🎤 {self.show.comedian}"), id="nameplate")
                yield Static("", id="bubble")
        yield RichLog(id="log", wrap=True, markup=False, highlight=False)
        yield OptionList(id="menu")
        with Horizontal(id="prompt-row"):
            yield CommandInput(placeholder="say anything · / for commands", id="prompt")
        yield Static("", id="status")

    def on_mount(self) -> None:
        self.mascot = self.query_one(Mascot)
        stage = self.query_one("#stage")
        stage.border_title = "TERMINAL COMEDY"
        stage.border_subtitle = "live from your terminal"
        self.set_interval(TICK, self.tick)
        self.update_status()
        self.on_resize()
        self.query_one("#prompt").focus()
        intro = "you are the audience. type anything, or / for commands."
        if not self.show.provider:
            intro += " no AI connected: offline material. /connect to plug one in."
        self.log_line("·", intro, DIM)
        self.perform_now(self.show.engine.opener(self.show.session), record=False)

    def on_resize(self, event: events.Resize | None = None) -> None:
        self.query_one("#stage").set_class(self.size.width < 100, "narrow")

    # ------------------------------------------------------------ status --
    def update_status(self) -> None:
        provider = self.show.provider
        ai = f"{provider.id} · {provider.model or 'default'}" if provider else "offline"
        folder = self.harness.workspace.name if self.harness.workspace else "-"
        look = self.harness.permissions.mode
        self.query_one("#status", Static).update(
            Text.assemble(
                ("● ", PINK if provider else DIM),
                (ai, "bold"),
                f"  │  📁 {folder}  │  look: {look}  │  mode: {self.show.session.mode}  │  / commands · ctrl+c quit",
            )
        )

    # ---------------------------------------------------------- animation --
    def tick(self) -> None:
        self.player.advance(TICK)
        self.mascot.show(self.player.frame_name)  # held reference: a query can fail mid-teardown
        if self.busy:
            return
        if self.hold > 0:
            self.hold -= TICK
            if self.hold <= 0:
                self.player.play("idle")
            return
        self.next_blink -= TICK
        if self.next_blink <= 0:
            self.player.play("blink")
            self.next_blink = random.uniform(*BLINK_EVERY)
            self.hold = 0.4

    # --------------------------------------------------------- transcript --
    def log_line(self, who: str, text: str, colour: str = "#f0e8f0") -> None:
        line = Text()
        line.append(f"{who} ", style=f"bold {colour}")
        line.append(sanitize(text))
        self.query_one("#log", RichLog).write(line)

    def note_tool(self, kind: str, text: str) -> None:
        icon = {"look": "👀", "denied": "🙈", "tool-error": "⚠"}.get(kind, "·")
        self.log_line(icon, f"{self.show.comedian} {'looked: ' if kind == 'look' else ''}{text}", DIM)

    def set_bubble(self, text: str, thinking: bool = False) -> None:
        bubble = self.query_one("#bubble", Static)
        clean = sanitize(text)
        bubble.set_class(is_rtl(clean), "rtl")
        bubble.set_class(thinking, "thinking")
        bubble.update(Text(clean))  # plain Text: "[brackets]" from a model must not be read as markup

    # ----------------------------------------------------------- perform --
    def perform_now(self, performance: Performance, record: bool = True) -> None:
        self.set_bubble(performance.text)
        animation = performance.animation if performance.animation in ANIMATIONS else "talk"
        self.player.play(animation)
        self.hold = max(1.0, min(performance.duration, 6.0))
        self.log_line(f"{self.show.comedian} ›", performance.text, PINK)
        reaction = self.show.session.audience.react(
            performance.text, emotion=performance.emotion, mode=self.show.session.mode
        )
        if reaction.text:
            self.log_line("  ", reaction.text, DIM)
        if performance.error:
            self.log_line("⚠", f"the provider did not answer: {performance.error}", DIM)

    def start(self, job: Callable[[], Performance], user_text: str, thinking: str = "…") -> None:
        if self.busy:
            self.notify("one bit at a time. the comedian is mid-sentence.", severity="warning")
            return
        self.busy = True
        self.player.play("think")
        self.set_bubble(thinking, thinking=True)
        self.run_worker(functools.partial(self._run, job, user_text), thread=True, exclusive=True, group="bit")

    def _run(self, job: Callable[[], Performance], user_text: str) -> None:
        try:
            performance = job()
        except Exception as error:  # a crash in a bit must never take the stage down
            performance = self.show.engine.offline(self.show.session.mode, self.show.session)
            performance.error = f"{error.__class__.__name__}: {error}"
        self.call_from_thread(self._finish, performance, user_text)

    def _finish(self, performance: Performance, user_text: str) -> None:
        self.busy = False
        self.show.session.note_exchange(user_text, performance.text)
        self.perform_now(performance)

    def streaming(self, spoken: str) -> None:
        if spoken.strip():
            if self.player.animation.name != "talk":
                self.player.play("talk")
            self.set_bubble(spoken)

    def bit(self, text: str, mode: str | None = None) -> None:
        chosen = mode or self.show.engine.route(text, self.show.session)
        session = self.show.session

        def job() -> Performance:
            return self.harness.run(
                text,
                session=session,
                mode=chosen,
                provider=self.show.provider,
                on_delta=lambda spoken: self.call_from_thread(self.streaming, spoken),
            )

        self.start(job, text)

    # -------------------------------------------------------- permissions --
    def _wait_for(self, screen: ModalScreen) -> Any:
        """From a worker thread: show a modal and block until it is answered."""
        done = threading.Event()
        box: dict[str, Any] = {}

        def push() -> None:
            self.push_screen(screen, callback=lambda result: (box.update(result=result), done.set()))

        self.call_from_thread(push)
        done.wait()
        return box.get("result")

    def approve(self, call: ToolCall) -> Decision:
        return self._wait_for(PermissionScreen(self.show.comedian, call)) or Decision.DENY

    # -------------------------------------------------------------- input --
    @on(Input.Changed, "#prompt")
    def typing(self, event: Input.Changed) -> None:
        menu = self.query_one("#menu", OptionList)
        value = event.value
        if not value.startswith("/") or " " in value:
            menu.display = False
            return
        needle = value[1:].lower()
        menu.clear_options()
        for command in COMMANDS:
            if any(key.startswith(needle) for key in command.keys):
                menu.add_option(Option(Text.assemble((f"/{command.name:<11}", f"bold {PINK}"), (command.help, DIM)), id=command.name))
        menu.display = menu.option_count > 0
        if menu.display:
            menu.highlighted = 0

    def complete_from_menu(self) -> bool:
        menu = self.query_one("#menu", OptionList)
        if not menu.display or menu.highlighted is None:
            return False
        name = menu.get_option_at_index(menu.highlighted).id
        prompt = self.query_one("#prompt", CommandInput)
        prompt.value = f"/{name} "
        prompt.cursor_position = len(prompt.value)
        menu.display = False
        return True

    @on(OptionList.OptionSelected, "#menu")
    def menu_click(self, event: OptionList.OptionSelected) -> None:
        self.complete_from_menu()
        self.query_one("#prompt").focus()

    def action_close_menu(self) -> None:
        self.query_one("#menu").display = False

    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()

    @on(Input.Submitted, "#prompt")
    def submitted(self, event: Input.Submitted) -> None:
        prompt = self.query_one("#prompt", CommandInput)
        text = event.value.strip()
        menu = self.query_one("#menu", OptionList)
        if menu.display and text.startswith("/") and parse(text)[0] is None:
            self.complete_from_menu()  # "/jo" + Enter means the highlighted command
            text = prompt.value.strip()
        menu.display = False
        prompt.value = ""
        if not text:
            return
        prompt.remember(text)
        command, argument = parse(text)
        if command is None:
            if text.startswith("/"):
                self.log_line("·", f"unknown command {text.split()[0]}. type / to see them all.", DIM)
                return
            self.log_line("you ›", text, PURPLE)
            self.bit(text)
            return
        self.log_line("you ›", text, PURPLE)
        self.run_command(command.name, argument)

    # ----------------------------------------------------------- commands --
    def say(self, text: str) -> None:
        for line in text.splitlines() or [""]:
            self.log_line("·", line, DIM)

    def run_command(self, name: str, argument: str) -> None:
        show = self.show
        if name in {"exit", "quit"}:
            self.action_leave()
        elif name == "help":
            for command in COMMANDS:
                self.say(f"/{', /'.join(command.keys):<18} {command.help}")
            self.say("modes: " + " · ".join(f"/{mode} {about}" for mode, about in mode_help()))
        elif name in {"joke", "standup", "story", "roast", "random"}:
            self.bit(argument, mode=name)
        elif name == "look":
            if show.provider:
                self.bit(argument or "Look at my project folder and do a bit about it.", mode="roast")
            else:
                self.start(lambda: self.harness.look(show.session), "/look", "👀")
        elif name == "tools":
            choice = argument.lower()
            if choice in {"ask", "allow", "off"}:
                self.harness.permissions = Permissions(mode=choice)
                self.say(f"folder access: {choice}")
            else:
                self.say(f"folder access is '{self.harness.permissions.mode}'. /tools ask | allow | off")
            self.update_status()
        elif name == "mode":
            self.say(show.set_mode(argument.lower()) if argument else f"mode: {show.session.mode} · " + ", ".join(MODES))
            self.update_status()
        elif name == "character":
            message = show.set_character(argument.lower())
            self.query_one(Mascot).jacket = show.engine.character.personality.jacket
            self.query_one("#nameplate", Label).update(Text(f"🎤 {show.comedian}"))
            self.harness.engine = show.engine
            self.say(message)
            self.query_one(Mascot).refresh()
        elif name == "provider":
            self.say(show.set_provider(argument.lower()) if argument else f"provider: {show.session.provider_label}")
            self.update_status()
        elif name == "connect":
            self.wizard_job(lambda wizard: wizard.connect(argument.lower()))
        elif name == "model":
            if not show.provider:
                self.say("no model on stage. /connect first.")
            else:
                provider = show.provider
                self.wizard_job(lambda wizard: wizard.model(provider, argument))
        elif name == "logout":
            self.say(show.logout())
            self.update_status()
        elif name == "settings":
            self.say("\n".join(show.settings_lines()))
            folder = self.harness.workspace.root if self.harness.workspace else "(none)"
            self.say(f"folder     : {folder} (look: {self.harness.permissions.mode})")
        elif name == "save":
            self.say(show.save_set(argument))
        elif name == "reset":
            show.session.reset()
            self.say("fresh room. nothing remembered.")

    def wizard_job(self, step: Callable[[Wizard], dict | None]) -> None:
        if self.busy:
            self.notify("wait for the punchline first.", severity="warning")
            return
        self.busy = True
        self.player.play("look")

        def ask(prompt: str) -> str:
            answer = self._wait_for(PromptScreen(prompt))
            if answer is None:
                raise EOFError
            return answer

        def ask_secret(prompt: str) -> str:
            answer = self._wait_for(PromptScreen(prompt, password=True))
            if answer is None:
                raise EOFError
            return answer

        def choose(title: str, options: list[str], default: str, allow_custom: bool) -> str | None:
            return self._wait_for(PickerScreen(title, options, default, allow_custom))

        wizard = Wizard(
            settings=self.show.settings,
            ask=ask,
            ask_secret=ask_secret,
            say=lambda line: self.call_from_thread(self.say, line),
            open_browser=webbrowser.open,
            choose=choose,
        )

        def work() -> None:
            try:
                values = step(wizard)
                message = self.show.apply(values) if values else ""
            except Exception as error:  # keep the stage alive whatever the network does
                message = f"could not connect: {error}"
            self.call_from_thread(self._wizard_done, message)

        self.run_worker(work, thread=True, exclusive=True, group="bit")

    def _wizard_done(self, message: str) -> None:
        self.busy = False
        self.player.play("idle")
        if message:
            self.say(message)
        self.harness.engine = self.show.engine
        self.update_status()

    # ------------------------------------------------------------- leave --
    def action_leave(self) -> None:
        if getattr(self, "_leaving", False):
            self.exit()
            return
        self._leaving = True
        closer = self.show.engine.closer(self.show.session)
        self.perform_now(closer, record=False)
        self.player.play("wave")
        self.set_timer(1.6, self.exit)


def run(show, workspace: Path | None, look_mode: str = "ask") -> int:
    ComedianApp(show, workspace, look_mode).run()
    return 0

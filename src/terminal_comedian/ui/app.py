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

from rich.markup import escape
from rich.padding import Padding
from rich.table import Table
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
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
from .pixels import frame_text, gradient, pixel_text, side_by_side, supported, text_bitmap
from .pixels import render as render_bitmap
from .terminal import is_rtl, sanitize

PINK = "#ff4fa3"
PINK_RGB = (255, 79, 163)
PURPLE_RGB = (155, 106, 255)
DIM_RGB = (92, 60, 86)
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
        self.scale = 1

    def set_scale(self, scale: int) -> None:
        if scale != self.scale:
            self.scale = scale
            self.refresh(layout=True)

    def show(self, frame_name: str) -> None:
        if frame_name != self.frame_name:
            self.frame_name = frame_name
            self.refresh()

    def render(self) -> Text:
        return frame_text(FRAMES[self.frame_name], self.jacket, self.scale)


class Marquee(Static):
    """LIVE light and the show's name, in pixel letters."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lit = True
        self.font = "big"
        self.badge = True  # the pixel LIVE light; narrow stages put it in the border instead

    def render(self) -> Text:
        light = PINK_RGB if self.lit else DIM_RGB
        dot = [[None, light, light, None], [light, light, light, light], [light, light, light, light], [None, light, light, None]]
        live = text_bitmap("LIVE", "small", (240, 232, 240) if self.lit else DIM_RGB)
        badge = side_by_side([dot, live], gap=1)
        title = text_bitmap("TERMINAL COMEDY", self.font, gradient(PINK_RGB, PURPLE_RGB))
        return render_bitmap(side_by_side([badge, title], gap=4) if self.badge else title)


class Nameplate(Static):
    """The comedian's name in small pixel letters, or plain text if the font lacks a glyph."""

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name_text = name

    def render(self) -> Text:
        if supported(self.name_text):
            return pixel_text(self.name_text, "small", PINK_RGB)
        return Text(f"🎤 {self.name_text}", style=f"bold {PINK}")


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


# ------------------------------------------------------------------- help --

KEYS = (
    ("enter", "send the line, or run the highlighted command"),
    ("/", "open the command menu; ↑↓ to choose, tab to complete"),
    ("↑ ↓", "earlier lines you typed"),
    ("esc", "close the menu, skip the typing, or cancel a bit in progress"),
    ("f1", "this help"),
    ("ctrl+l", "clear the transcript"),
    ("ctrl+c", "take a bow and leave"),
)


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape,f1,q,enter", "dismiss_help", "close")]

    def compose(self) -> ComposeResult:
        commands = Table.grid(padding=(0, 2))
        commands.add_column(style=f"bold {PINK}", no_wrap=True)
        commands.add_column()
        for command in COMMANDS:
            commands.add_row("/" + ", /".join(command.keys), command.help)
        keys = Table.grid(padding=(0, 2))
        keys.add_column(style=f"bold {PURPLE}", no_wrap=True)
        keys.add_column()
        for key, about in KEYS:
            keys.add_row(key, about)
        modes = Table.grid(padding=(0, 2))
        modes.add_column(style=f"bold {PINK}", no_wrap=True)
        modes.add_column(style=DIM)
        for mode, about in mode_help():
            modes.add_row(mode, about)
        with VerticalScroll(id="dialog", classes="wide"):
            yield Label(Text("Terminal Comedy Studio · help"), id="question")
            yield Static(Text("Just type to talk. Commands are the side door.", style=DIM))
            yield Static(Text("commands", style=f"bold {DIM}"), classes="section")
            yield Static(commands)
            yield Static(Text("keys", style=f"bold {DIM}"), classes="section")
            yield Static(keys)
            yield Static(Text("modes (/mode <name>)", style=f"bold {DIM}"), classes="section")
            yield Static(modes)
            yield Label("esc to close", classes="hint")

    def action_dismiss_help(self) -> None:
        self.dismiss(None)


# -------------------------------------------------------------------- app --


class Floor(Static):
    """The stage floor: a lit plank under the comedian's feet."""

    def render(self) -> Text:
        width = max(0, self.size.width)
        middle = min(width, 60)
        side = (width - middle) // 2
        return Text.assemble(("▔" * side, "#2a1427"), ("▔" * middle, "#5c2a4f"), ("▔" * (width - side - middle), "#2a1427"))


class ComedianApp(App):
    """Terminal Comedy Studio, full screen."""

    TITLE = "Terminal Comedy Studio"
    CSS = f"""
    Screen {{ background: #0d0710; color: #f0e8f0; }}
    #stage {{ height: auto; border: round {PINK}; border-title-color: {PINK}; border-subtitle-color: {DIM};
              border-title-align: center; padding: 0 1; margin: 0 1; background: #120914; }}
    #marquee {{ width: 100%; height: auto; content-align: center top; margin-top: 1; }}
    #stage.compact #marquee {{ display: none; }}
    #stage.compact #nameplate {{ display: none; }}
    #stage.compact #stage-row {{ margin-top: 0; }}
    #stage.compact #bubble {{ margin-top: 1; max-height: 8; }}
    #stage.tiny #mascot-column, #stage.tiny #tail, #stage.tiny #floor {{ display: none; }}
    #stage.tiny #speech {{ width: 100%; max-width: 100%; min-width: 0; }}
    #stage.tiny #bubble {{ margin-top: 0; max-height: 6; }}
    #stage-row {{ height: auto; align: center top; margin-top: 1; }}
    #mascot-column {{ width: auto; min-width: 30; height: auto; align: center top; }}
    #mascot {{ width: auto; height: auto; }}
    #nameplate {{ width: auto; height: auto; margin-top: 1; }}
    #tail {{ width: 3; height: 3; color: {PURPLE}; margin-top: 2; }}
    #speech {{ width: 1fr; max-width: 64; min-width: 26; height: auto; }}
    #bubble {{ width: 100%; height: auto; min-height: 3; max-height: 14; border: round {PURPLE};
               padding: 0 1; margin-top: 2; }}
    #bubble.rtl {{ text-align: right; }}
    #bubble.thinking {{ color: {DIM}; border: round {DIM}; }}
    #reaction {{ width: 100%; height: 1; color: {DIM}; text-style: italic; padding: 0 1; }}
    #floor {{ height: 1; }}
    #stage.narrow #stage-row {{ layout: vertical; align: center top; }}
    #stage.narrow #mascot-column {{ width: 100%; align: center top; }}
    #stage.narrow #nameplate {{ margin-bottom: 1; }}
    #stage.narrow #tail {{ display: none; }}
    #stage.narrow #speech {{ width: 100%; max-width: 100%; }}
    #stage.narrow #bubble {{ margin-top: 0; }}
    #log {{ height: 1fr; min-height: 3; margin: 0 1; padding: 0 1; scrollbar-size-vertical: 1; scrollbar-size-horizontal: 0;
            background: #0d0710; }}
    #menu {{ display: none; height: auto; max-height: 12; margin: 0 2; border: round {DIM}; background: #170b17; }}
    #prompt-row {{ height: 3; margin: 0 1; }}
    #prompt {{ border: round {PINK}; background: #0d0710; }}
    #prompt.busy {{ border: round {DIM}; }}
    #statusbar {{ height: 1; background: #170b17; padding: 0 2; }}
    #status {{ width: 1fr; color: {DIM}; }}
    #hints {{ width: auto; color: {DIM}; }}
    ModalScreen {{ align: center middle; background: #0d0710 70%; }}
    #dialog {{ width: 76; max-width: 95%; height: auto; max-height: 90%; border: round {PINK}; background: #170b17;
               padding: 1 2; }}
    #dialog.wide {{ width: 96; }}
    .section {{ margin-top: 1; }}
    #question {{ color: {PINK}; text-style: bold; margin-bottom: 1; width: 100%; }}
    .hint {{ color: {DIM}; margin-top: 1; }}
    .hidden {{ display: none; }}
    #choices {{ height: auto; max-height: 16; background: #170b17; border: none; }}
    """

    BINDINGS = [
        Binding("ctrl+c", "leave", "quit", priority=True, show=False),
        Binding("ctrl+d", "leave", "quit", show=False),
        Binding("escape", "dismiss_or_cancel", show=False),
        Binding("ctrl+l", "clear_log", show=False),
        Binding("f1", "help", show=False),
    ]

    REVEAL_CPS = 55.0  # typewriter speed; long sets speed up so no line takes more than MAX_REVEAL
    MAX_REVEAL = 3.0

    def __init__(self, show, workspace: Path | None, look_mode: str = "ask", typewriter: bool = True) -> None:
        super().__init__()
        self.show = show  # the cli.Show: settings, engine, session, provider and its string commands
        self.typewriter = typewriter
        self.player = Player("idle")
        self.hold = 0.0
        self.next_blink = random.uniform(*BLINK_EVERY)
        self.busy = False
        self.bit_id = 0
        self.streamed = False
        self.thinking_for = 0.0
        self.queued: str | None = None
        self.reveal: dict[str, Any] | None = None  # the line being typed into the bubble
        self.reaction_left = 0.0
        self.live_phase = 0.0
        self.thinking_label = ""
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
            yield Marquee(id="marquee")
            with Horizontal(id="stage-row"):
                with Vertical(id="mascot-column"):
                    yield Mascot(personality.jacket, id="mascot")
                    yield Nameplate(self.show.comedian, id="nameplate")
                yield Static(Text("\n ◀━"), id="tail")
                with Vertical(id="speech"):
                    yield Static("", id="bubble")
                    yield Static("", id="reaction")
            yield Floor(id="floor")
        yield RichLog(id="log", wrap=True, markup=False, highlight=False, min_width=20)  # default 78 clips small terminals
        yield OptionList(id="menu")
        with Horizontal(id="prompt-row"):
            yield CommandInput(placeholder="say anything · / for commands · f1 help", id="prompt")
        with Horizontal(id="statusbar"):
            yield Static("", id="status")
            yield Static("", id="hints")

    def on_mount(self) -> None:
        self.mascot = self.query_one(Mascot)
        stage = self.query_one("#stage")
        stage.border_subtitle = "live from your terminal"
        self.paint_title(True)
        self.set_interval(TICK, self.tick)
        self.update_status()
        self.on_resize()
        self.query_one("#prompt").focus()
        self.info("you are the audience. just type, or press / for commands.")
        tips = "try: tell me a joke · roast my code · /look · /standup"
        if not self.show.provider:
            tips += " · /connect to plug in an AI"
        self.info(tips)
        self.perform_now(self.show.engine.opener(self.show.session))

    def on_resize(self, event: events.Resize | None = None) -> None:
        width, height = self.size.width, self.size.height
        self._laid_out_for = self.size
        stage = self.query_one("#stage")
        tiny = height < 24 or width < 46 or (width < 64 and height < 30)
        stage.set_class(tiny, "tiny")  # no room for the mascot: the bubble alone holds the stage
        stage.set_class(width < 64 and not tiny, "narrow")
        stage.set_class(height < 34 or width < 70, "compact")
        stage.border_subtitle = "" if tiny else "live from your terminal"
        marquee = self.query_one(Marquee)
        marquee.font = "big" if width >= 100 else "small"
        marquee.badge = width >= 110
        marquee.refresh(layout=True)
        self.query_one(Mascot).set_scale(2 if width >= 120 and height >= 50 else 1)
        self.paint_title(getattr(self, "_lit", True))
        self.update_hints()

    def paint_title(self, lit: bool) -> None:
        stage = self.query_one("#stage")
        marquee = self.query_one(Marquee)
        marquee.lit = lit
        marquee.refresh()
        if stage.has_class("compact") or not marquee.badge:  # no room for the pixel light: say it in the border
            dot = f"[{PINK}]●[/]" if lit else f"[{DIM}]●[/]"
            name = f" · {escape(self.show.comedian)}" if stage.has_class("compact") else ""
            stage.border_title = f"{dot} LIVE · TERMINAL COMEDY{name}"
        else:
            stage.border_title = ""

    # ------------------------------------------------------------ status --
    def update_status(self) -> None:
        provider = self.show.provider
        ai = f"{provider.id} · {provider.model or 'default'}" if provider else "offline"
        folder = self.harness.workspace.name if self.harness.workspace else "-"
        self.query_one("#status", Static).update(
            Text.assemble(
                ("● ", PINK if provider else DIM),
                (ai, "bold #f0e8f0"),
                ("  ▸ ", DIM),
                (folder, "#f0e8f0"),
                ("  ▸ look ", DIM),
                (self.harness.permissions.mode, "#f0e8f0"),
                ("  ▸ mode ", DIM),
                (self.show.session.mode, "#f0e8f0"),
                no_wrap=True,
                overflow="ellipsis",
            )
        )
        self.update_hints()

    def update_hints(self) -> None:
        menu = self.query_one("#menu", OptionList)
        if menu.display:
            hints = "↑↓ choose · tab complete · enter run · esc close"
        elif self.busy:
            hints = "esc cancel"
        elif self.reveal:
            hints = "esc skip"
        else:
            hints = "/ commands · f1 help · ctrl+c quit" if self.size.width >= 100 else "f1 help"
        self.query_one("#hints", Static).update(Text(hints, style=DIM))
        self.query_one("#prompt").set_class(self.busy, "busy")

    # ---------------------------------------------------------- animation --
    def tick(self) -> None:
        if self.size != getattr(self, "_laid_out_for", None):  # every resize path, not only App Resize events
            self.on_resize()
        self.player.advance(TICK)
        self.mascot.show(self.player.frame_name)  # held reference: a query can fail mid-teardown
        self.live_phase += TICK
        if self.live_phase >= 0.9:
            self.live_phase = 0.0
            self.paint_title(not getattr(self, "_lit", True))
            self._lit = not getattr(self, "_lit", True)
        if self.reaction_left > 0:
            self.reaction_left -= TICK
            if self.reaction_left <= 0:
                self.query_one("#reaction", Static).update("")
        if self.reveal:
            self.advance_reveal()
            return
        if self.busy:
            if not self.streamed:
                self.thinking_for += TICK
                self.paint_thinking()
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

    SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def paint_thinking(self) -> None:
        frame = self.SPINNER[int(self.thinking_for / TICK) % len(self.SPINNER)]
        seconds = f" {int(self.thinking_for)}s" if self.thinking_for >= 3 else ""
        self.set_bubble(f"{frame} {self.thinking_label}{seconds}", thinking=True)

    # --------------------------------------------------------- transcript --
    def _row(self, badge: Text, body: Text) -> None:
        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(no_wrap=True, width=max(9, len(self.show.comedian) + 2))
        grid.add_column(ratio=1)
        grid.add_row(badge, Padding(body, (0, 2, 0, 0)))  # breathing room: some terminals draw RTL a cell wider
        self.query_one("#log", RichLog).write(grid)

    def _body(self, text: str, style: str = "") -> Text:
        clean = sanitize(text)
        return Text(clean, style=style, justify="right" if is_rtl(clean) else "left")

    def log_comedian(self, text: str) -> None:
        self._row(Text(f" {self.show.comedian} ", style=f"bold #0d0710 on {PINK}"), self._body(text))

    def log_user(self, text: str) -> None:
        self.query_one("#log", RichLog).write(Text(""))
        self._row(Text(" you ", style=f"bold #0d0710 on {PURPLE}"), self._body(text, "#e6dcff"))

    def info(self, text: str, icon: str = "·") -> None:
        self._row(Text(f" {icon}", style=DIM), self._body(text, DIM))

    def log_line(self, who: str, text: str, colour: str = "#f0e8f0") -> None:
        """Kept for callers outside the app: one dim line with a label."""
        self.info(f"{who} {text}".strip())

    def note_tool(self, kind: str, text: str) -> None:
        if kind == "look":
            self.info(f"{self.show.comedian} looked: {text}", "◉")
            self.player.play("look")
        elif kind == "denied":
            self.info(f"not allowed: {text}", "✕")
        else:
            self.info(text, "!")

    def set_bubble(self, text: str, thinking: bool = False) -> None:
        bubble = self.query_one("#bubble", Static)
        clean = sanitize(text)
        bubble.set_class(is_rtl(clean), "rtl")
        bubble.set_class(thinking, "thinking")
        bubble.update(Text(clean))  # plain Text: "[brackets]" from a model must not be read as markup

    def show_reaction(self, text: str) -> None:
        self.query_one("#reaction", Static).update(Text(sanitize(text)))
        self.reaction_left = 3.0

    # ----------------------------------------------------------- perform --
    def perform_now(self, performance: Performance) -> None:
        """Type the line into the bubble while talking, then land it with the bit's animation."""
        text = sanitize(performance.text)
        already_shown = self.streamed and str(self.query_one("#bubble", Static).render()) == text
        self.reveal = {"text": text, "shown": 0.0, "performance": performance}
        speed = max(self.REVEAL_CPS, len(text) / self.MAX_REVEAL)
        self.reveal["speed"] = speed
        if not self.typewriter or already_shown:
            self.reveal["shown"] = len(text)
        else:
            self.player.play("talk")
            self.set_bubble("")
        self.update_hints()
        self.advance_reveal(0.0)

    def advance_reveal(self, dt: float = TICK) -> None:
        reveal = self.reveal
        if not reveal:
            return
        reveal["shown"] = min(len(reveal["text"]), reveal["shown"] + reveal["speed"] * dt)
        self.set_bubble(reveal["text"][: int(reveal["shown"])])
        if reveal["shown"] >= len(reveal["text"]):
            self.reveal = None
            self.land(reveal["performance"])

    def land(self, performance: Performance) -> None:
        animation = performance.animation if performance.animation in ANIMATIONS else "talk"
        self.player.play(animation)
        self.hold = max(1.2, min(performance.duration, 6.0))
        self.log_comedian(performance.text)
        reaction = self.show.session.audience.react(
            performance.text, emotion=performance.emotion, mode=self.show.session.mode
        )
        if reaction.text:
            self.show_reaction(reaction.text)
        if performance.error:
            self.info(f"the AI did not answer, so this was offline material: {performance.error}", "!")
        self.update_hints()
        if self.queued and not self.busy:
            line, self.queued = self.queued, None
            self.handle_line(line)

    def start(self, job: Callable[[], Performance], user_text: str, label: str = "") -> None:
        self.busy = True
        self.bit_id += 1
        self.streamed = False
        self.thinking_for = 0.0
        self.thinking_label = label or f"{self.show.comedian} is thinking"
        self.player.play("think")
        self.paint_thinking()
        self.update_hints()
        self.run_worker(functools.partial(self._run, job, user_text, self.bit_id), thread=True, group="bit")

    def _run(self, job: Callable[[], Performance], user_text: str, bit_id: int) -> None:
        try:
            performance = job()
        except Exception as error:  # a crash in a bit must never take the stage down
            performance = self.show.engine.offline(self.show.session.mode, self.show.session)
            performance.error = f"{error.__class__.__name__}: {error}"
        try:
            self.call_from_thread(self._finish, performance, user_text, bit_id)
        except RuntimeError:  # the app closed while the model was still talking
            pass

    def _finish(self, performance: Performance, user_text: str, bit_id: int) -> None:
        if bit_id != self.bit_id:
            return  # cancelled with esc: the late answer is dropped
        self.busy = False
        self.show.session.note_exchange(user_text, performance.text)
        self.perform_now(performance)

    def streaming(self, spoken: str, bit_id: int) -> None:
        if bit_id != self.bit_id or not spoken.strip():
            return
        if not self.streamed:
            self.streamed = True
            self.player.play("talk")
        self.set_bubble(spoken)

    def bit(self, text: str, mode: str | None = None) -> None:
        chosen = mode or self.show.engine.route(text, self.show.session)
        session = self.show.session
        bit_id = self.bit_id + 1

        def job() -> Performance:
            return self.harness.run(
                text,
                session=session,
                mode=chosen,
                provider=self.show.provider,
                on_delta=lambda spoken: self.call_from_thread(self.streaming, spoken, bit_id),
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
            if menu.display:
                menu.display = False
                self.update_hints()
            return
        needle = value[1:].lower()
        menu.clear_options()
        for command in COMMANDS:
            if any(key.startswith(needle) for key in command.keys):
                menu.add_option(
                    Option(Text.assemble((f"/{command.name:<11}", f"bold {PINK}"), (command.help, DIM)), id=command.name)
                )
        menu.display = menu.option_count > 0
        if menu.display:
            menu.highlighted = 0
        self.update_hints()

    def complete_from_menu(self) -> bool:
        menu = self.query_one("#menu", OptionList)
        if not menu.display or menu.highlighted is None:
            return False
        name = menu.get_option_at_index(menu.highlighted).id
        prompt = self.query_one("#prompt", CommandInput)
        prompt.value = f"/{name} "
        prompt.cursor_position = len(prompt.value)
        menu.display = False
        self.update_hints()
        return True

    @on(OptionList.OptionSelected, "#menu")
    def menu_click(self, event: OptionList.OptionSelected) -> None:
        self.complete_from_menu()
        self.query_one("#prompt").focus()

    def action_dismiss_or_cancel(self) -> None:
        menu = self.query_one("#menu", OptionList)
        if menu.display:
            menu.display = False
        elif self.reveal:
            self.reveal["shown"] = len(self.reveal["text"])
            self.advance_reveal(0.0)
        elif self.busy:
            self.bit_id += 1  # whatever comes back from the old bit is ignored
            self.busy = False
            self.queued = None
            self.player.play("sorry")
            self.hold = 1.2
            self.set_bubble("…never mind.")
            self.info("cancelled.")
        self.update_hints()

    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

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
            self.update_hints()
            return
        prompt.remember(text)
        if self.reveal:  # typing again skips the rest of the current line
            self.reveal["shown"] = len(self.reveal["text"])
            self.advance_reveal(0.0)
        if self.busy:
            self.queued = text
            self.info("queued: up next after this bit.")
            return
        self.handle_line(text)

    def handle_line(self, text: str) -> None:
        command, argument = parse(text)
        if command is None:
            if text.startswith("/"):
                self.info(f"unknown command {text.split()[0]}. press / to see them all.", "!")
                return
            self.log_user(text)
            self.bit(text)
            return
        self.log_user(text)
        self.run_command(command.name, argument)
        self.update_hints()

    # ----------------------------------------------------------- commands --
    def say(self, text: str) -> None:
        for line in text.splitlines() or [""]:
            self.info(line)

    def run_command(self, name: str, argument: str) -> None:
        show = self.show
        if name in {"exit", "quit"}:
            self.action_leave()
        elif name == "help":
            self.action_help()
        elif name in {"joke", "standup", "story", "roast", "random"}:
            self.bit(argument, mode=name)
        elif name == "look":
            if show.provider:
                self.bit(argument or "Look at my project folder and do a bit about it.", mode="roast")
            else:
                self.start(lambda: self.harness.look(show.session), "/look", f"{show.comedian} is looking around")
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
            self.mascot.jacket = show.engine.character.personality.jacket
            plate = self.query_one(Nameplate)
            plate.name_text = show.comedian
            plate.refresh(layout=True)
            self.harness.engine = show.engine
            self.say(message)
            self.mascot.refresh()
            self.player.play("wave")
            self.hold = 1.5
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
        elif name == "update":
            self.update_job()
        elif name == "reset":
            show.session.reset()
            self.action_clear_log()
            self.say("fresh room. nothing remembered.")

    def wizard_job(self, step: Callable[[Wizard], dict | None]) -> None:
        self.busy = True
        self.bit_id += 1
        self.streamed = False
        self.thinking_for = 0.0
        self.thinking_label = "setting up the microphone"
        self.player.play("look")
        self.update_hints()

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

        self.run_worker(work, thread=True, group="bit")

    def update_job(self) -> None:
        """/update: check GitHub, ask, then run the one fixed update command."""
        from .. import updater

        self.busy = True
        self.bit_id += 1
        self.streamed = False
        self.thinking_for = 0.0
        self.thinking_label = "checking GitHub for a newer me"
        self.player.play("look")
        self.update_hints()

        def work() -> None:
            try:
                status = updater.check()
            except updater.UpdateError as error:
                self.call_from_thread(self._wizard_done, f"could not check for updates: {error}")
                return
            self.call_from_thread(self.say, status.summary())
            if status.current:
                self.call_from_thread(self._wizard_done, "")
                return
            argv = updater.command(status.install)
            yes = f"update now (runs: {updater.describe(argv)})"
            choice = self._wait_for(PickerScreen("A newer comedian is on GitHub.", [yes, "not now"], yes))
            if choice != yes:
                self.call_from_thread(self._wizard_done, "not updated.")
                return
            self.call_from_thread(self.say, f"running: {updater.describe(argv)}")
            ok, output = updater.run(argv)
            if output:
                self.call_from_thread(self.say, output)
            message = "updated. leave with ctrl+c and start comedian again to use it." if ok else "the update failed; nothing else changed."
            self.call_from_thread(self._wizard_done, message)

        self.run_worker(work, thread=True, group="bit")

    def _wizard_done(self, message: str) -> None:
        self.busy = False
        self.player.play("idle")
        self.set_bubble("")
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
        self.bit_id += 1
        self.busy = False
        closer = self.show.engine.closer(self.show.session)
        self.typewriter = False
        self.perform_now(closer)
        self.player.play("wave")
        self.set_timer(1.6, self.exit)


def run(show, workspace: Path | None, look_mode: str = "ask") -> int:
    ComedianApp(show, workspace, look_mode).run()
    return 0

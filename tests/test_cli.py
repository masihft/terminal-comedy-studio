"""The CLI surface: commands, stage layout, exit codes. Nothing touches a network."""

from __future__ import annotations

import pytest

from terminal_comedian.ai.provider import AIProvider
from terminal_comedian.character.personality import load_character
from terminal_comedian.cli import Show, make_show
from terminal_comedian.comedy.engine import ComedyEngine
from terminal_comedian.config.settings import Settings
from terminal_comedian.memory.session import Session
from terminal_comedian.ui.input import COMMANDS, help_lines, parse, unknown
from terminal_comedian.ui.stage import stage_lines
from terminal_comedian.ui.terminal import Capabilities, strip_ansi, text_width, wrap
from terminal_comedian.comedy.reactions import Audience

PLAIN = Capabilities(width=100, height=40, tty=False, truecolor=False, unicode=True)
COLOURED = Capabilities(width=100, height=40, tty=True, truecolor=True, unicode=True)
MONOCHROME = Capabilities(width=100, height=40, tty=True, truecolor=False, unicode=True)
ASCII_ONLY = Capabilities(width=100, height=40, tty=True, truecolor=True, unicode=False)


class Scripted(AIProvider):
    id = "scripted"
    label = "Scripted"
    needs_key = False
    default_base_url = "http://unused"

    def __init__(self, reply='{"text": "a scripted line", "emotion": "happy", "animation": "talk"}'):
        super().__init__(Settings.load(cwd=None, environ={}))
        self.reply = reply
        self.deltas: list[str] = []

    def complete(self, messages, *, temperature=0.9, max_tokens=400, on_delta=None):
        if on_delta:
            for word in self.reply.split():
                on_delta(word + " ")
                self.deltas.append(word)
        return self.reply


def build_show(provider=None, language="fa", character="default", caps=PLAIN):
    settings = Settings.load(cwd=None, environ={"LANGUAGE": language, "COMEDIAN_CHARACTER": character})
    engine = ComedyEngine(character=load_character(character), settings=settings)
    room = Session(mode="stage", language=language, audience=Audience())
    return Show(settings=settings, caps=caps, engine=engine, session=room, provider=provider)


# ------------------------------------------------------------------ commands


def test_every_command_is_documented_from_the_table():
    documented = "\n".join(help_lines())
    for command in COMMANDS:
        assert f"/{command.name}" in documented


def test_command_parsing_splits_the_argument():
    command, argument = parse("/roast my dockerfile")
    assert command is not None and command.name == "roast"
    assert argument == "my dockerfile"


def test_plain_speech_is_not_a_command():
    command, text = parse("tell me something about go")
    assert command is None
    assert text == "tell me something about go"


def test_aliases_resolve_to_the_same_command():
    assert parse("/quit")[0].name == "exit"
    assert parse("/EXIT")[0].name == "exit"


def test_unknown_command_lists_the_real_ones():
    message = unknown("/teleport")
    assert "teleport" in message
    assert "/joke" in message


def test_help_command_lists_the_commands(capsys):
    show = build_show()
    assert show.run_command(*parse("/help")) is True
    printed = capsys.readouterr().out.lower()
    assert "use a command" in printed
    assert "/standup" in printed


# ------------------------------------------------------------------- layout


def test_stage_box_is_square_for_every_terminal_profile():
    for caps in (PLAIN, COLOURED, MONOCHROME, ASCII_ONLY):
        rows = stage_lines(comedian="Claw'd", speech="hello", caps=caps)
        widths = {text_width(row) for row in rows}
        assert len(widths) == 1, widths
        assert text_width(rows[0]) <= caps.width


def test_persian_speech_stays_inside_the_box():
    rows = stage_lines(comedian="Claw'd", speech="کد من کار می‌کنه. نمی‌دونم چرا. این ترسناک‌ترین قسمته.", caps=COLOURED)
    widths = {text_width(row) for row in rows}
    assert len(widths) == 1


def test_long_speech_wraps_instead_of_overflowing():
    lines = wrap("word " * 90, 40)
    assert all(text_width(line) <= 40 for line in lines)
    assert len(lines) > 3


def test_control_sequences_in_a_reply_never_reach_the_screen():
    hostile = "\x1b[2J\x1b]0;pwned\x07bye\x1b[31mred"
    rows = stage_lines(comedian="Claw'd", speech=hostile, caps=COLOURED)
    body = "".join(strip_ansi(row) for row in rows)
    assert "\x1b" not in body
    assert "\x07" not in body
    assert "bye" in body and "red" in body


def test_wrapping_keeps_persian_zwnj():
    assert wrap("کار می‌کند", 40) == ["کار می‌کند"]


def test_colour_only_rows_survive_a_dumb_terminal():
    rows = stage_lines(comedian="Claw'd", speech="hi", caps=PLAIN)
    assert "\x1b" not in "".join(rows)


def test_ascii_fallback_has_no_unicode_blocks():
    rows = stage_lines(comedian="Claw'd", speech="hi", caps=ASCII_ONLY)
    joined = "".join(rows)
    assert "█" not in joined
    assert "#" in joined


def test_the_stage_shows_the_comedian_the_line_and_the_provider():
    rows = "\n".join(stage_lines(comedian="Claw'd", speech="a line", caps=PLAIN, mode="roast", note="ai: offline"))
    assert "TERMINAL COMEDY" in rows
    assert "Claw'd" in rows
    assert "a line" in rows
    assert "roast" in rows
    assert "ai: offline" in rows


# ---------------------------------------------------------------------- show


def test_one_shot_offline_performance_prints_a_joke(capsys):
    show = build_show()
    code = show.one_shot("joke", "")
    assert code == 0
    assert capsys.readouterr().out.strip()


def test_provider_reply_is_printed_and_remembered(capsys):
    show = build_show(provider=Scripted())
    show.perform("how are you", mode="chat")
    out = capsys.readouterr().out
    assert "a scripted line" in out
    assert len(show.session) == 2


def test_streaming_deltas_are_painted_as_they_arrive():
    provider = Scripted()
    show = build_show(provider=provider, caps=COLOURED)
    show.perform("go on", mode="chat")
    assert provider.deltas


def test_privacy_is_stated_before_the_user_types_anything(capsys):
    show = build_show(provider=Scripted())
    show.provider.label = "Scripted"
    show.announce()
    printed = capsys.readouterr().out
    assert "only what you type" in printed


def test_offline_says_so_instead_of_pretending(capsys):
    show = build_show()
    show.announce()
    assert "offline" in capsys.readouterr().out


def test_settings_lists_what_is_sent_where(capsys):
    show = build_show()
    show.run_command(*parse("/settings"))
    printed = capsys.readouterr().out
    assert "provider   : offline" in printed
    assert "Never: files, environment variables, or history." in printed


def test_mode_command_changes_the_default_mode(capsys):
    show = build_show()
    show.run_command(*parse("/mode story"))
    assert show.session.mode == "story"
    show.run_command(*parse("/mode nonsense"))
    assert "modes:" in capsys.readouterr().out


def test_character_command_switches_the_voice(capsys):
    show = build_show()
    show.run_command(*parse("/character sarkash"))
    assert show.comedian == "Sarkash"
    show.run_command(*parse("/character nobody"))
    assert "characters:" in capsys.readouterr().out


def test_provider_command_can_go_offline_and_reports_missing_keys(capsys):
    show = build_show()
    show.run_command(*parse("/provider omniroute"))
    assert "OMNIROUTE_BASE_URL" in capsys.readouterr().out
    show.run_command(*parse("/provider offline"))
    assert show.provider is None
    assert show.session.provider_label == "offline"


def test_reset_clears_the_memory(capsys):
    show = build_show()
    show.perform("my docker build is slow", mode="chat")
    capsys.readouterr()
    show.run_command(*parse("/reset"))
    assert len(show.session) == 0
    assert "fresh room" in capsys.readouterr().out


def test_exit_command_stops_the_loop():
    show = build_show()
    assert show.run_command(*parse("/exit")) is False


def test_roast_command_targets_the_argument(capsys):
    provider = Scripted('{"text": "your Makefile is a museum", "emotion": "sarcastic", "animation": "reaction"}')
    show = build_show(provider=provider)
    show.run_command(*parse("/roast my Makefile"))
    assert "museum" in capsys.readouterr().out
    assert show.session.history()[-2]["content"] == "my Makefile"


# ------------------------------------------------------------------- wiring


def test_make_show_defaults_to_offline_without_any_env():
    show = make_show([])
    assert show.provider is None
    assert show.settings.language in ("fa", "en")


def test_argument_flags_override_the_environment():
    show = make_show(["--provider", "offline", "--language", "en", "--character", "mr-blonde"])
    assert show.settings.language == "en"
    assert show.comedian == "Mr Blonde"


def test_no_color_flag_strips_ansi_from_the_stage(capsys):
    show = make_show(["--no-color", "joke"])
    show.one_shot("joke", "")
    assert "\x1b" not in capsys.readouterr().out


def test_version_exits_cleanly():
    with pytest.raises(SystemExit) as stop:
        make_show(["--version"])
    assert stop.value.code == 0

"""The full-screen app, driven headless with Textual's pilot. No network, no real config."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from textual.widgets import Label, OptionList, RichLog, Static

from terminal_comedian.cli import make_show
from terminal_comedian.character.frames import FRAMES
from terminal_comedian.ui.app import ComedianApp, HelpScreen, PermissionScreen, PickerScreen
from terminal_comedian.ui.pixels import frame_text, size


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("AI_PROVIDER", "offline")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text("# TODO everything\n", encoding="utf-8")
    return tmp_path


def drive(script, language="en", typewriter=False):
    """Run the app headless, hand the pilot to `script`, return what it returns."""

    async def main():
        app = ComedianApp(make_show(["--language", language]), workspace=Path.cwd(), typewriter=typewriter)
        async with app.run_test(size=(110, 38)) as pilot:
            await pilot.pause(0.2)
            return await script(app, pilot)

    return asyncio.run(main())


def log_text(app) -> str:
    return "\n".join(line.text for line in app.query_one("#log", RichLog).lines)


async def type_line(pilot, text):
    for char in text:
        await pilot.press(char if char != " " else "space")


# ------------------------------------------------------------------ pixels


def test_half_blocks_keep_the_mascot_square_and_complete():
    text = frame_text(FRAMES["idle_01"])
    rows = text.plain.split("\n")
    columns, height = size(FRAMES["idle_01"])
    assert len(rows) == height == 9
    assert all(len(row) <= columns for row in rows)
    for frame in FRAMES.values():  # every frame keeps the same footprint
        assert size(frame) == (columns, height)


# --------------------------------------------------------------------- app


def test_the_comedian_opens_the_show_before_any_configuration():
    async def script(app, pilot):
        return log_text(app), str(app.query_one("#status", Static).render()) + str(app.query_one("#hints", Static).render())

    log, status = drive(script)
    assert "Claw'd   Hello" in log or "Claw'd " in log.split("\n")[-1]
    assert "/connect" in log
    assert "offline" in status and "look ask" in status and "f1 help" in status


def test_slash_opens_a_filtered_menu_and_tab_completes():
    async def script(app, pilot):
        await type_line(pilot, "/lo")
        menu = app.query_one("#menu", OptionList)
        shown = menu.display
        names = [menu.get_option_at_index(i).id for i in range(menu.option_count)]
        await pilot.press("tab")
        return shown, names, app.query_one("#prompt").value

    shown, names, value = drive(script)
    assert shown is True
    assert names == ["look", "connect", "logout"]  # /login is an alias of connect
    assert value == "/look "


def test_look_asks_permission_and_a_no_is_a_no():
    async def script(app, pilot):
        await type_line(pilot, "/look")
        await pilot.press("enter")
        await pilot.pause(0.3)
        modal = type(app.screen)
        await pilot.press("n")
        await pilot.pause(0.5)
        return modal, log_text(app)

    modal, log = drive(script)
    assert modal is PermissionScreen
    assert "won't look" in log


def test_look_with_permission_jokes_about_the_folder():
    async def script(app, pilot):
        await type_line(pilot, "/look")
        await pilot.press("enter")
        await pilot.pause(0.3)
        await pilot.press("y")
        await pilot.pause(0.6)
        return log_text(app)

    log = drive(script)
    assert "looked: count the files" in log
    assert "TODO" in log


def test_connect_opens_an_arrow_key_picker_and_escape_changes_nothing():
    async def script(app, pilot):
        await type_line(pilot, "/connect")
        await pilot.press("enter")
        await pilot.pause(0.3)
        modal = app.screen
        options = modal.options if isinstance(modal, PickerScreen) else []
        await pilot.press("escape")
        await pilot.pause(0.3)
        return type(modal), options, log_text(app), app.show.provider

    modal, options, log, provider = drive(script)
    assert modal is PickerScreen
    assert any(option.startswith("OpenRouter") for option in options)
    assert "nothing changed" in log
    assert provider is None


def test_up_arrow_brings_back_the_last_line():
    async def script(app, pilot):
        await type_line(pilot, "/mode")
        await pilot.press("enter")
        await pilot.press("up")
        return app.query_one("#prompt").value

    assert drive(script) == "/mode"


def test_switching_character_changes_the_nameplate_and_jacket():
    async def script(app, pilot):
        await type_line(pilot, "/character sarkash")
        await pilot.press("enter")
        await pilot.pause(0.1)
        return str(app.query_one("#nameplate", Label).render()), app.query_one("#mascot").jacket

    name, jacket = drive(script)
    assert "Sarkash" in name
    assert jacket == (146, 72, 222)


def test_unknown_command_is_explained_not_performed():
    async def script(app, pilot):
        await type_line(pilot, "/nope")
        await pilot.press("escape")
        await pilot.press("enter")
        return log_text(app)

    assert "unknown command /nope" in drive(script)


def test_brackets_from_a_model_are_shown_not_eaten_as_markup():
    async def script(app, pilot):
        app.set_bubble("[stub-funny] a [b]bold[/b] claim")
        await pilot.pause(0.05)
        return str(app.query_one("#bubble", Static).render())

    assert drive(script) == "[stub-funny] a [b]bold[/b] claim"


def test_help_opens_as_a_screen_from_the_command_and_f1():
    async def script(app, pilot):
        await type_line(pilot, "/help")
        await pilot.press("enter")
        await pilot.pause(0.1)
        first = type(app.screen)
        await pilot.press("escape")
        await pilot.press("f1")
        await pilot.pause(0.1)
        return first, type(app.screen)

    assert drive(script) == (HelpScreen, HelpScreen)


def test_the_typewriter_reveals_the_line_then_logs_it():
    async def script(app, pilot):
        await pilot.pause(0.05)
        early = str(app.query_one("#bubble", Static).render())
        await pilot.pause(3.5)
        late = str(app.query_one("#bubble", Static).render())
        return early, late, log_text(app)

    early, late, log = drive(script, typewriter=True)
    assert len(early) < len(late)
    assert late in log


def test_escape_cancels_a_slow_bit_and_drops_the_late_answer():
    import threading

    gate = threading.Event()

    async def script(app, pilot):
        def slow():
            gate.wait(5)
            return app.show.engine.offline("stage", app.show.session)

        app.start(slow, "slow one")
        await pilot.pause(0.2)
        busy_before = app.busy
        await pilot.press("escape")
        gate.set()
        await pilot.pause(0.4)
        return busy_before, app.busy, str(app.query_one("#bubble", Static).render())

    busy_before, busy_after, bubble = drive(script)
    assert busy_before is True and busy_after is False
    assert bubble == "…never mind."


def test_a_line_typed_during_a_bit_is_queued_not_lost():
    import threading

    gate = threading.Event()

    async def script(app, pilot):
        def slow():
            gate.wait(5)
            return app.show.engine.offline("stage", app.show.session)

        app.start(slow, "slow one")
        await type_line(pilot, "/mode")
        await pilot.press("enter")
        queued = app.queued
        gate.set()
        await pilot.pause(0.6)
        return queued, app.queued, log_text(app)

    queued, after, log = drive(script)
    assert queued == "/mode" and after is None
    assert "mode: stage" in log

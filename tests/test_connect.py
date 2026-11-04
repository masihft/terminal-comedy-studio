"""/connect, /model, /logout and the OpenRouter browser login. No real network."""

from __future__ import annotations

import base64
import hashlib
import os
import stat
import threading
import urllib.parse
import urllib.request

import pytest

from terminal_comedian.ai import oauth
from terminal_comedian.ai.openai import OpenAIProvider
from terminal_comedian.ai.openrouter import OpenRouterProvider
from terminal_comedian.ai.provider import ProviderUnavailable
from terminal_comedian.config.credentials import save_values, user_env_path
from terminal_comedian.config.settings import Settings, parse_env_file
from terminal_comedian.connect import Wizard, mask
from terminal_comedian.ui.input import parse

from test_cli import build_show


@pytest.fixture(autouse=True)
def config_home(tmp_path, monkeypatch):
    """Every test gets its own ~/.config so no real key is read or written."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    for key in ("AI_PROVIDER", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_MODEL", "OPENROUTER_MODEL"):
        monkeypatch.delenv(key, raising=False)
    return tmp_path


def scripted(answers):
    queue = list(answers)

    def ask(prompt):
        if not queue:
            raise EOFError
        return queue.pop(0)

    return ask


def wizard(answers, secrets=(), **overrides):
    said: list[str] = []
    saved: list[dict] = []
    options = dict(
        settings=Settings.load(environ={}),
        ask=scripted(answers),
        ask_secret=scripted(secrets),
        say=said.append,
        open_browser=lambda url: True,
        save=lambda values: saved.append(dict(values)),
        shell={},
    )
    options.update(overrides)
    return Wizard(**options), said, saved


# --------------------------------------------------------------- credentials


def test_save_values_updates_in_place_and_keeps_other_lines(config_home):
    path = user_env_path()
    assert path == config_home / "terminal-comedy-studio" / ".env"
    path.parent.mkdir(parents=True)
    path.write_text("# mine\nLANGUAGE=en\nOPENAI_API_KEY=old\n", encoding="utf-8")
    save_values({"OPENAI_API_KEY": "sk-new value", "AI_PROVIDER": "openai"})
    assert path.read_text(encoding="utf-8").startswith("# mine\nLANGUAGE=en\n")
    assert parse_env_file(path) == {"LANGUAGE": "en", "OPENAI_API_KEY": "sk-new value", "AI_PROVIDER": "openai"}
    save_values({"OPENAI_API_KEY": None})
    assert "OPENAI_API_KEY" not in parse_env_file(path)
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_save_values_refuses_line_breaks_and_bad_names():
    with pytest.raises(ValueError):
        save_values({"OPENAI_API_KEY": "sk\nAI_PROVIDER=evil"})
    with pytest.raises(ValueError):
        save_values({"BAD NAME": "x"})


def test_saved_values_are_read_back_by_settings():
    save_values({"AI_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "sk-or-test-1234"})
    settings = Settings.load(environ={})
    assert settings.provider == "openrouter"
    assert settings.get("OPENROUTER_API_KEY") == "sk-or-test-1234"


def test_mask_never_shows_the_whole_key():
    assert mask("sk-or-abcdefgh1234") == "…1234"
    assert mask("short") == "(set)"


# ---------------------------------------------------------------------- oauth


def test_pkce_challenge_is_s256_of_the_verifier():
    verifier, challenge = oauth.pkce_pair()
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected
    assert 43 <= len(verifier) <= 128


def test_auth_url_carries_challenge_callback_and_state():
    url = oauth.auth_url("abc", "http://localhost:5000/callback", "xyz")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert url.startswith(oauth.AUTH_URL)
    assert query["code_challenge"] == ["abc"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["callback_url"] == ["http://localhost:5000/callback"]
    assert query["state"] == ["xyz"]


def _visit(url: str) -> None:
    with urllib.request.urlopen(url.replace("localhost", "127.0.0.1"), timeout=5) as response:
        response.read()


def test_browser_login_round_trip_through_the_local_callback():
    seen = {}

    def fake_browser(url):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        callback, state = query["callback_url"][0], query["state"][0]
        seen["challenge"] = query["code_challenge"][0]

        def browser():
            _visit(f"{callback}?code=wrong&state=not-mine")  # ignored: someone else's redirect
            _visit(f"{callback}?code=the-code&state={state}")

        threading.Thread(target=browser, daemon=True).start()
        return True

    def fake_exchange(code, verifier):
        seen["code"] = code
        digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        assert digest == seen["challenge"]
        return "sk-or-from-oauth-9999"

    key = oauth.browser_login(fake_browser, lambda line: None, timeout=10, exchange_code=fake_exchange)
    assert key == "sk-or-from-oauth-9999"
    assert seen["code"] == "the-code"


def test_browser_login_reports_a_cancelled_sign_in():
    def fake_browser(url):
        callback = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["callback_url"][0]
        threading.Thread(target=_visit, args=(callback,), daemon=True).start()
        return True

    with pytest.raises(oauth.LoginFailed, match="cancelled"):
        oauth.browser_login(fake_browser, lambda line: None, timeout=10, exchange_code=lambda c, v: "never")


def test_browser_login_times_out_cleanly():
    with pytest.raises(oauth.LoginFailed, match="in time"):
        oauth.browser_login(lambda url: False, lambda line: None, timeout=0.3, exchange_code=lambda c, v: "never")


def test_pasted_code_login_exchanges_what_the_user_pastes():
    said: list[str] = []
    key = oauth.pasted_code_login(lambda prompt: " pasted ", said.append, exchange_code=lambda c, v: f"key-for-{c}")
    assert key == "key-for-pasted"
    links = [line for line in said if line.startswith(oauth.AUTH_URL)]
    assert links and "callback_url" not in links[0]


# --------------------------------------------------------------------- wizard


def test_connect_openai_with_a_pasted_key_and_a_listed_model(monkeypatch):
    monkeypatch.setattr(OpenAIProvider, "list_models", lambda self, timeout=10.0: ["gpt-4o", "gpt-4o-mini"])
    flow, said, saved = wizard(["2", "1", ""], secrets=["sk-test-abcdefgh"])
    values = flow.connect()
    assert values == {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test-abcdefgh", "OPENAI_MODEL": "gpt-4o"}
    assert saved == [values]
    assert not any("sk-test-abcdefgh" in line for line in said), "the key must never be printed"


def test_connect_openrouter_by_browser_and_search_the_model_list(monkeypatch):
    models = [f"vendor/model-{n}" for n in range(30)] + ["anthropic/claude-sonnet-4.5"]
    monkeypatch.setattr(OpenRouterProvider, "list_models", lambda self, timeout=10.0: models)
    flow, said, saved = wizard(
        ["1", "", "claude", "1", "n"],
        login=lambda open_browser, say: "sk-or-oauth-key-1234",
    )
    values = flow.connect()
    assert values["OPENROUTER_API_KEY"] == "sk-or-oauth-key-1234"
    assert values["OPENROUTER_MODEL"] == "anthropic/claude-sonnet-4.5"
    assert saved == [], "declined: nothing written"
    assert any("more. type part of a name" in line for line in said)


def test_empty_key_opens_the_key_page_first(monkeypatch):
    monkeypatch.setattr(OpenAIProvider, "list_models", lambda self, timeout=10.0: [])
    opened: list[str] = []
    flow, _, _ = wizard(["openai", "gpt-4o-mini", "y"], secrets=["", "sk-second-try-1"], open_browser=opened.append)
    values = flow.connect()
    assert opened == [OpenAIProvider.docs_url]
    assert values["OPENAI_API_KEY"] == "sk-second-try-1"


def test_local_server_needs_an_http_url():
    flow, said, saved = wizard(["5", "ftp://nope"])
    assert flow.connect() is None
    assert saved == []
    assert any("http://" in line for line in said)


def test_cancel_anywhere_changes_nothing():
    flow, said, saved = wizard([])
    assert flow.connect() is None
    assert saved == []
    assert said[-1] == "cancelled. nothing changed."


def test_a_model_list_failure_still_lets_you_type_a_name(monkeypatch):
    def refuse(self, timeout=10.0):
        raise ProviderUnavailable("api.openai.com refused the key (HTTP 401).")

    monkeypatch.setattr(OpenAIProvider, "list_models", refuse)
    flow, said, _ = wizard(["openai", "my-model", "n"], secrets=["sk-test-abcdefgh"])
    assert flow.connect()["OPENAI_MODEL"] == "my-model"
    assert any("could not list models" in line for line in said)


def test_shell_variables_that_will_win_are_pointed_out(monkeypatch):
    monkeypatch.setattr(OpenAIProvider, "list_models", lambda self, timeout=10.0: [])
    flow, said, _ = wizard(["openai", "gpt-4o-mini", ""], secrets=["sk-new-abcdefgh"], shell={"OPENAI_API_KEY": "other"})
    flow.connect()
    assert any("shell also sets OPENAI_API_KEY" in line for line in said)


# ------------------------------------------------------------------ the show


def test_connect_login_model_logout_commands_exist():
    assert parse("/connect openrouter")[0].name == "connect"
    assert parse("/login")[0].name == "connect"
    assert parse("/model gpt-4o")[0].name == "model"
    assert parse("/logout")[0].name == "logout"


def test_show_switches_live_after_connect_and_forgets_on_logout(monkeypatch):
    show = build_show()
    values = {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-live-abcdefgh", "OPENAI_MODEL": "gpt-4o"}
    save_values(values)
    monkeypatch.setattr(Wizard, "connect", lambda self, wanted="": values)
    assert "OpenAI" in show.connect("")
    assert show.provider.id == "openai" and show.provider.model == "gpt-4o"

    assert "gpt-4o-mini" in show.choose_model("gpt-4o-mini")
    assert parse_env_file(user_env_path())["OPENAI_MODEL"] == "gpt-4o-mini"

    message = show.logout()
    assert "forgot the OpenAI key" in message
    assert show.provider is None
    assert "OPENAI_API_KEY" not in parse_env_file(user_env_path())
    assert "sk-live-abcdefgh" not in message


def test_model_needs_a_provider_on_stage():
    assert "/connect" in build_show().choose_model("")

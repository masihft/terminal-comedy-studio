"""Provider abstraction: no network, no credentials, no excuses."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from terminal_comedian.ai.anthropic import AnthropicProvider
from terminal_comedian.ai.local import LocalProvider
from terminal_comedian.ai.omniroute import OmniRouteProvider
from terminal_comedian.ai.openai import OpenAIProvider
from terminal_comedian.ai.openrouter import OpenRouterProvider
from terminal_comedian.ai.provider import (
    AIError,
    AIProvider,
    ProviderNotConfigured,
    create_provider,
    parse_comedy_response,
    provider_ids,
    register,
)
from terminal_comedian.character.states import ANIMATIONS, Emotion
from terminal_comedian.config.settings import Settings, parse_env_file

ALL_PROVIDERS = ("anthropic", "local", "omniroute", "openai", "openrouter")
_SANDBOX = tempfile.mkdtemp(prefix="terminal-comedy-test-")


class FakeProvider(AIProvider):
    id = "fake"
    label = "Fake"
    key_env = ""
    base_url_env = ""
    needs_key = False
    default_base_url = "http://fake"

    def __init__(self, settings=None, reply="ok", calls=None):
        super().__init__(settings or Settings.load(environ={}))
        self.reply = reply
        self.calls = calls if calls is not None else []

    def complete(self, messages, *, temperature=0.9, max_tokens=400, on_delta=None):
        self.calls.append(messages)
        if on_delta:
            for char in self.reply:
                on_delta(char)
        return self.reply


register(FakeProvider)


def settings(**environ):
    """Isolated settings: never reads a developer's real .env or home config."""
    merged = {
        "PATH": "/usr/bin",
        "HOME": _SANDBOX,
        "XDG_CONFIG_HOME": _SANDBOX,
        **environ,
    }
    return Settings.load(cwd=Path(os.devnull), environ=merged)


# ------------------------------------------------------------------- parsing


def test_parses_plain_json_contract():
    response = parse_comedy_response('{"text": "hi", "emotion": "laughing", "animation": "laugh", "duration": 1.5}')
    assert response.text == "hi"
    assert response.emotion is Emotion.LAUGHING
    assert response.animation == "laugh"
    assert response.duration == 1.5


def test_parses_json_wrapped_in_prose_and_fences():
    for raw in (
        'Here you go:\n```json\n{"text": "one"}\n```\nHope that lands!',
        'preamble {"text": "two", "emotion": "sorry"} trailing',
    ):
        response = parse_comedy_response(raw)
        assert response.text.split()[0] in ("one", "two")


def test_unknown_emotion_and_missing_fields_still_perform():
    response = parse_comedy_response('{"text": "three", "emotion": "furious", "duration": "banana"}')
    assert response.emotion is Emotion.NEUTRAL
    assert response.duration == pytest.approx(2.6)


def test_plain_text_without_json_is_never_lost():
    response = parse_comedy_response("just a line, no braces at all")
    assert response.text == "just a line, no braces at all"
    assert response.animation == "idle"


def test_json_without_text_is_not_a_performance():
    assert parse_comedy_response('{"emotion": "happy"}').text == '{"emotion": "happy"}'


def test_duration_is_clamped_to_sane_stage_times():
    assert parse_comedy_response('{"text": "x", "duration": 900}').duration == pytest.approx(2.6)


# ------------------------------------------------------------------ registry


def test_every_documented_provider_is_registered():
    assert set(ALL_PROVIDERS) <= set(provider_ids())


def test_no_provider_is_assumed_available_without_configuration():
    for provider_id in ("openai", "openrouter", "anthropic", "omniroute"):
        provider = create_provider(settings(AI_PROVIDER=provider_id))
        assert not provider.is_configured
        assert provider.missing()


def test_omniroute_is_optional_and_has_no_hard_coded_host():
    provider = create_provider(settings(AI_PROVIDER="omniroute", OMNIROUTE_API_KEY="x"))
    assert provider.base_url == ""
    assert "OMNIROUTE_BASE_URL" in provider.missing()
    assert "localhost" not in repr(provider)


def test_offline_is_the_default_and_builds_no_provider():
    assert create_provider(settings()) is None
    assert create_provider(settings(AI_PROVIDER="offline")) is None


def test_unknown_provider_names_the_choices():
    with pytest.raises(ProviderNotConfigured) as error:
        create_provider(settings(AI_PROVIDER="telepathy"))
    assert "omniroute" in str(error.value)


def test_local_provider_needs_no_key():
    provider = create_provider(settings(AI_PROVIDER="local", LOCAL_BASE_URL="http://127.0.0.1:9/v1"))
    assert isinstance(provider, LocalProvider)
    assert provider.is_configured


def test_base_urls_are_used_as_configured():
    openai = OpenAIProvider(settings())
    assert openai.base_url == "https://api.openai.com/v1"
    assert OpenRouterProvider(settings()).base_url == "https://openrouter.ai/api/v1"
    pointed = OpenAIProvider(settings(OPENAI_BASE_URL="http://127.0.0.1:1234/v1/"))
    assert pointed.base_url == "http://127.0.0.1:1234/v1"
    assert AnthropicProvider(settings()).default_base_url == "https://api.anthropic.com"
    assert OmniRouteProvider(settings()).default_base_url == ""


def test_keys_are_named_not_stored():
    provider = AnthropicProvider(settings(ANTHROPIC_API_KEY="secret-value"))
    assert provider.key_env == "ANTHROPIC_API_KEY"
    assert "secret-value" not in repr(provider)
    assert "secret-value" not in provider.missing()


# ---------------------------------------------------------------- transport


def test_generate_messages_returns_a_performance_shaped_response():
    provider = FakeProvider(reply='{"text": "boom", "emotion": "happy", "animation": "punchline", "duration": 2}')
    response = provider.generate_messages([{"role": "user", "content": "hi"}])
    assert response.text == "boom"
    assert response.animation in ANIMATIONS
    assert response.provider == "fake"


def test_generate_matches_the_documented_interface():
    provider = FakeProvider(reply='{"text": "as dict"}')
    result = provider.generate("tell me a joke", {"messages": [{"role": "system", "content": "be funny"}]})
    assert set(result) == {"text", "emotion", "animation", "duration"}
    assert result["text"] == "as dict"
    assert provider.calls[-1][0]["content"] == "be funny"


def test_deltas_are_forwarded_while_streaming():
    seen = []
    provider = FakeProvider(reply="abc", calls=[])
    provider.complete([{"role": "user", "content": "x"}], on_delta=seen.append)
    assert seen == ["a", "b", "c"]


def test_empty_reply_is_an_error_not_a_crash():
    provider = FakeProvider(reply="")
    with pytest.raises(AIError):
        provider.generate_messages([{"role": "user", "content": "hi"}])


def test_duplicate_provider_ids_are_rejected():
    class Clone(FakeProvider):
        id = "fake"

    with pytest.raises(ValueError):
        register(Clone)


# ------------------------------------------------------------------ settings


def test_env_file_parsing_ignores_comments_and_quotes(tmp_path):
    path = tmp_path / ".env"
    path.write_text('# comment\nAI_PROVIDER=omniroute\nLANGUAGE="fa"\nOMNIROUTE_BASE_URL="https://gw.local/v1" \n\n', encoding="utf-8")
    values = parse_env_file(path)
    assert values == {
        "AI_PROVIDER": "omniroute",
        "LANGUAGE": "fa",
        "OMNIROUTE_BASE_URL": "https://gw.local/v1",
    }


def test_real_environment_beats_the_env_file(tmp_path):
    (tmp_path / ".env").write_text("AI_PROVIDER=openai\n", encoding="utf-8")
    settings_ = Settings.load(cwd=tmp_path, environ={"AI_PROVIDER": "omniroute"})
    assert settings_.provider == "omniroute"


def test_persian_is_the_default_language():
    assert Settings.load(cwd=None, environ={}).language == "fa"


def test_missing_env_file_is_not_an_error(tmp_path):
    assert Settings.load(cwd=tmp_path, environ={}).provider == "offline"

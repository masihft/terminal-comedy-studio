"""The comedy brain: persona, modes, callbacks and the room. No network."""

from __future__ import annotations

import pytest

from terminal_comedian.ai.provider import AIProvider
from terminal_comedian.character.personality import PRESETS, character_names, load_character
from terminal_comedian.character.states import ANIMATIONS, Emotion
from terminal_comedian.comedy.callbacks import CallbackEngine
from terminal_comedian.comedy.engine import ComedyEngine, Performance
from terminal_comedian.comedy.jokes import JOKES, PROVIDER_DOWN, pick
from terminal_comedian.comedy.reactions import Audience
from terminal_comedian.config.settings import Settings
from terminal_comedian.memory.session import Session
from terminal_comedian.prompts import MODES, load_role, load_system


class Scripted(AIProvider):
    id = "scripted"
    label = "Scripted"
    needs_key = False
    default_base_url = "http://unused"

    def __init__(self, reply, settings=None):
        super().__init__(settings or Settings.load(cwd=None, environ={}))
        self.reply = reply
        self.sent: list[list[dict[str, str]]] = []

    def complete(self, messages, *, temperature=0.9, max_tokens=400, on_delta=None):
        self.sent.append(messages)
        return self.reply


def engine(language="fa", character="default"):
    settings = Settings.load(cwd=None, environ={"LANGUAGE": language, "COMEDIAN_CHARACTER": character})
    return ComedyEngine(character=load_character(character), settings=settings)


def session(language="fa", mode="stage"):
    return Session(mode=mode, language=language)


# ------------------------------------------------------------------- persona


def test_persona_prompt_carries_identity_language_and_contract():
    system = load_system()
    for needle in ("stand-up", "JSON", "Persian", "never", "duration"):
        assert needle.lower() in system.lower()
    assert "__COMEDIAN__" not in system.replace("__COMEDIAN__", "")


def test_every_mode_has_a_role_and_a_description():
    for mode in MODES:
        role = load_role(mode)
        assert role.prompt.strip()
        assert role.description.strip()
        assert 0 < role.temperature <= 2
        assert role.max_tokens >= 64


def test_role_variables_are_substituted_not_left_in_the_prompt():
    role = load_role("stage")
    rendered = role.render({"__LANGUAGE__": "Persian (فارسی)", "__COMEDIAN__": "Claw'd"})
    assert "__" not in rendered


def test_character_presets_are_loadable_and_unknown_names_raise():
    assert set(character_names()) >= set(PRESETS)
    for name in character_names():
        character = load_character(name)
        assert character.personality.boundaries
    with pytest.raises(KeyError):
        load_character("nobody-on-this-stage")


# ---------------------------------------------------------------- offline


@pytest.mark.parametrize("mode", MODES)
def test_offline_performs_in_every_mode_with_valid_animation(mode):
    performance = engine().offline(mode, session())
    assert performance.text.strip()
    assert performance.animation in ANIMATIONS
    assert isinstance(performance.emotion, Emotion)
    assert 0 < performance.duration <= 20


def test_offline_material_rotates_instead_of_repeating():
    comedy = engine()
    seen = {comedy.offline("stage", session()).text for _ in range(4)}
    assert len(seen) == 4


def test_persian_and_english_banks_are_both_populated():
    for language in ("fa", "en"):
        assert len(JOKES[language]) >= 8
        assert all(joke.strip() for joke in JOKES[language])


def test_pick_falls_back_to_english_for_unknown_language():
    assert pick(JOKES, "de", 0) == JOKES["en"][0]


# --------------------------------------------------------------------- ai


def test_provider_reply_becomes_a_performance():
    provider = Scripted('{"text": "green tests, red flags", "emotion": "sarcastic", "animation": "reaction", "duration": 2}')
    show = engine().perform("how is it going", session=session(), provider=provider)
    assert show.text == "green tests, red flags"
    assert show.emotion is Emotion.SARCASTIC
    assert show.animation == "reaction"
    assert show.source == "ai:scripted"


def test_made_up_animation_names_fall_back_to_the_emotion():
    provider = Scripted('{"text": "hi", "emotion": "laughing", "animation": "interpretive-dance"}')
    show = engine().perform("", session=session(), provider=provider)
    assert show.animation in ANIMATIONS
    assert show.animation == "laugh"


def test_system_prompt_includes_the_persona_the_mode_and_show_notes():
    provider = Scripted('{"text": "ok"}')
    room = session()
    room.callbacks.note_user("my docker build is slow", "en")
    engine().perform("hello", session=room, mode="roast", provider=provider)
    system = provider.sent[-1][0]["content"]
    assert "roast" in system.lower()
    assert "docker" in system
    assert "Hard boundaries" in system


def test_history_is_sent_but_capped():
    provider = Scripted('{"text": "ok"}')
    room = session()
    for index in range(30):
        room.note_exchange(f"line {index}", f"reply {index}")
    engine().perform("now", session=room, provider=provider)
    assert len(provider.sent[-1]) <= 10


def test_provider_failure_still_opens_the_mic():
    class Broken(Scripted):
        def complete(self, messages, *, temperature=0.9, max_tokens=400, on_delta=None):
            from terminal_comedian.ai.provider import ProviderUnavailable

            raise ProviderUnavailable("127.0.0.1:1 is unreachable")

    show = engine().perform("tell me a joke", session=session(), provider=Broken('{"text": "x"}'))
    assert show.text.strip()
    assert show.source == "offline"
    assert "unreachable" in show.error


def test_offline_note_about_a_down_provider_is_in_the_local_language():
    assert len(PROVIDER_DOWN["fa"]) >= 2 and len(PROVIDER_DOWN["en"]) >= 2


# ------------------------------------------------------------------ routing


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("tell me a joke", "joke"),
        ("یه جوک بگو", "joke"),
        ("do a standup set", "standup"),
        ("استندآپ اجرا کن", "standup"),
        ("tell me a story", "story"),
        ("داستان بگو", "story"),
        ("roast my vim config", "roast"),
        ("surprise me", "random"),
        ("hi there", "stage"),
    ],
)
def test_natural_language_routes_to_a_mode(text, mode):
    assert engine().route(text, session()) == mode


def test_routing_respects_the_current_mode_for_plain_conversation():
    assert engine().route("and then?", session(mode="chat")) == "chat"


# --------------------------------------------------------------- callbacks


def test_callbacks_collect_topics_and_offer_them_back():
    memory = CallbackEngine()
    memory.note_user("my docker build is slow again", "en")
    memory.note_user("the tests keep failing", "en")
    first = " ".join(memory.suggest()).lower()
    assert "docker" in first
    assert "the" not in first
    second = " ".join(memory.suggest()).lower()
    assert "tests" in second
    assert "docker" not in second


def test_callbacks_do_not_grow_without_bound():
    memory = CallbackEngine()
    for index in range(40):
        memory.note_user(f"topic{index} extra", "en")
    assert len(memory.topics) <= memory.limit


def test_told_bits_are_recorded_and_detectable():
    memory = CallbackEngine()
    memory.note_bit("a joke about caches")
    assert memory.used_bit("a joke about caches")
    assert not memory.used_bit("a different joke")


def test_session_context_block_mentions_the_room_and_the_run():
    room = session()
    room.callbacks.note_user("kubernetes", "en")
    room.note_exchange("kubernetes", "a joke about pods")
    block = room.context_block()
    assert "kubernetes" in block
    assert "1 bits" in block


def test_session_forgets_on_reset():
    room = session()
    room.note_exchange("hello", "hi")
    room.reset()
    assert len(room) == 0
    assert room.bits_told == 0


# ---------------------------------------------------------------- audience


def test_audience_is_not_always_loud():
    room = Audience()
    reactions = [room.react("a line", emotion=Emotion.NEUTRAL, mode="chat") for _ in range(60)]
    quiet = sum(1 for reaction in reactions if not reaction.loud)
    assert quiet >= 20


def test_two_loud_moments_in_a_row_are_followed_by_an_awkward_beat():
    room = Audience()
    room.last_loud = True
    reaction = room.react("line", emotion=Emotion.NEUTRAL, mode="chat")
    assert reaction.key == "awkward"


def test_audience_keeps_score_for_the_prompt():
    room = Audience()
    room.landed = 3
    room.flopped = 1
    assert "3 landed, 1 flopped" in room.summary()


def test_performance_lines_are_split_for_the_stage():
    show = Performance(text="first\n\nsecond\n")
    assert show.spoken == ["first", "second"]

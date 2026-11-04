"""/connect and /model: hook the comedian up to a model without editing files.

Keys are read with getpass (never echoed), never printed back in full, and only
written to the user's own config file when they say yes.
"""

from __future__ import annotations

import getpass
import os
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .ai.oauth import LoginFailed, browser_login, pasted_code_login
from .ai.provider import REGISTRY, AIError, AIProvider, create_provider
from .config.credentials import save_values, user_env_path
from .config.settings import Settings

CHOICES: tuple[tuple[str, str], ...] = (
    ("openrouter", "OpenRouter   — sign in with your browser, or paste a key"),
    ("openai", "OpenAI       — paste an API key"),
    ("anthropic", "Anthropic    — paste an API key"),
    ("omniroute", "OmniRoute    — your own gateway URL"),
    ("local", "Local server — LM Studio, Ollama, llama.cpp, vLLM"),
    ("offline", "Offline      — no AI, the built-in material"),
)
SHOWN_MODELS = 12


def mask(secret: str) -> str:
    return "…" + secret[-4:] if len(secret) > 8 else "(set)"


class Cancelled(Exception):
    pass


@dataclass
class Wizard:
    settings: Settings
    ask: Callable[[str], str] = input
    ask_secret: Callable[[str], str] = getpass.getpass
    say: Callable[[str], None] = print
    open_browser: Callable[[str], bool] = webbrowser.open
    save: Callable[[dict[str, str | None]], Path] = save_values
    login: Callable[..., str] = browser_login
    paste_login: Callable[..., str] = pasted_code_login
    shell: dict[str, str] = field(default_factory=lambda: dict(os.environ))
    # A full-screen UI passes a picker: (title, options, default, allow_custom) -> choice or None.
    choose: Callable[[str, list[str], str, bool], str | None] | None = None

    def _pick(self, title: str, options: list[str], default: str = "", allow_custom: bool = False) -> str:
        assert self.choose is not None
        picked = self.choose(title, options, default, allow_custom)
        if not picked:
            raise Cancelled
        return picked

    # ------------------------------------------------------------- helpers --
    def _ask(self, prompt: str) -> str:
        try:
            return self.ask(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            raise Cancelled from None

    def _secret(self, prompt: str) -> str:
        try:
            return self.ask_secret(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            raise Cancelled from None

    def _provider(self, values: dict[str, str]) -> AIProvider:
        create_provider(Settings())  # offline: returns None, but registers every provider
        settings = Settings.load(environ={**self.settings.environ, **values})
        return REGISTRY[values["AI_PROVIDER"]](settings)

    # ---------------------------------------------------------------- steps --
    def pick_provider(self, wanted: str = "") -> str:
        ids = [pid for pid, _ in CHOICES]
        if wanted in ids:
            return wanted
        if wanted:
            self.say(f"unknown provider '{wanted}'.")
        if self.choose:
            labels = [label for _, label in CHOICES]
            return CHOICES[labels.index(self._pick("connect the comedian to a model", labels))][0]
        self.say("connect the comedian to a model:")
        for number, (_, label) in enumerate(CHOICES, 1):
            self.say(f"  {number}. {label}")
        answer = self._ask(f"pick 1-{len(CHOICES)} (Enter cancels): ").lower()
        if answer.isdigit() and 1 <= int(answer) <= len(CHOICES):
            return CHOICES[int(answer) - 1][0]
        if answer in ids:
            return answer
        raise Cancelled

    def key_for(self, provider: AIProvider) -> str:
        current = provider.api_key
        hint = f"Enter keeps {mask(current)}" if current else "Enter opens the page that makes one"
        key = self._secret(f"{provider.label} API key ({hint}): ")
        if key or current:
            return key or current
        if provider.docs_url:
            self.open_browser(provider.docs_url)
            self.say(f"opened {provider.docs_url} — create a key there, then paste it here.")
        key = self._secret(f"{provider.label} API key: ")
        if not key:
            raise Cancelled
        return key

    def credentials(self, pid: str) -> dict[str, str]:
        provider = self._provider({"AI_PROVIDER": pid})
        values: dict[str, str] = {}
        if pid == "openrouter":
            ways = [
                "sign in with the browser (recommended)",
                "sign in on another device and paste a code (SSH)",
                "paste an API key",
            ]
            if self.choose:
                how = str(ways.index(self._pick("OpenRouter: how do you want to sign in?", ways, ways[0])) + 1)
            else:
                for number, way in enumerate(ways, 1):
                    self.say(f"  {number}. {way}")
                how = self._ask("how? [1]: ") or "1"
            try:
                if how == "1":
                    key = self.login(self.open_browser, self.say)
                elif how == "2":
                    key = self.paste_login(self._ask, self.say)
                elif how == "3":
                    key = self.key_for(provider)
                else:
                    raise Cancelled
            except (LoginFailed, AIError) as error:
                self.say(f"login failed: {error}")
                raise Cancelled from None
            values[provider.key_env] = key
            self.say(f"connected. key {mask(key)} is billed to your own OpenRouter account.")
        elif pid in {"openai", "anthropic"}:
            values[provider.key_env] = self.key_for(provider)
        else:
            current = provider.settings.get(provider.base_url_env)
            example = "http://localhost:1234/v1" if pid == "local" else "https://your-gateway/v1"
            url = self._ask(f"base URL [{current or example}]: ") or current
            if not url:
                raise Cancelled
            if not url.startswith(("http://", "https://")):
                self.say("the base URL must start with http:// or https://")
                raise Cancelled
            values[provider.base_url_env] = url.rstrip("/")
            key = self._secret("API key (Enter for none): ")
            if key:
                values[provider.key_env] = key
        return values

    def choose_model(self, provider: AIProvider, wanted: str = "") -> str:
        if wanted:
            return wanted
        default = provider.model
        try:
            models = provider.list_models()
        except AIError as error:
            self.say(f"could not list models: {error}")
            models = []
        if self.choose:
            return self._pick(f"{provider.label}: pick a model (type to search)", models, default, True)
        shown = models
        while True:
            for number, name in enumerate(shown[:SHOWN_MODELS], 1):
                marker = "*" if name == default else " "
                self.say(f" {marker}{number:>2}. {name}")
            if len(shown) > SHOWN_MODELS:
                self.say(f"     … {len(shown) - SHOWN_MODELS} more. type part of a name to search.")
            answer = self._ask(f"model [{default or 'type a name'}]: ")
            if not answer:
                if default:
                    return default
                continue
            if answer.isdigit() and 1 <= int(answer) <= min(len(shown), SHOWN_MODELS):
                return shown[int(answer) - 1]
            if not models or answer in models:
                return answer
            matches = [name for name in models if answer.lower() in name.lower()]
            if not matches:
                self.say(f"no model matches '{answer}'. using it as typed.")
                return answer
            shown = matches

    def offer_save(self, values: dict[str, str]) -> bool:
        if self.choose:
            keep = ["yes, remember it", "no, only for this show"]
            answer = "y" if self._pick(f"remember this in {user_env_path()}?", keep, keep[0]) == keep[0] else "n"
        else:
            answer = self._ask(f"remember this in {user_env_path()}? [Y/n]: ").lower()
        if answer not in {"", "y", "yes"}:
            self.say("kept for this show only.")
            return False
        self.save(values)
        self.say("saved in an owner-only file. /logout forgets it.")
        shadowed = sorted(key for key in values if self.shell.get(key, values[key]) != values[key])
        if shadowed:
            self.say(f"note: your shell also sets {', '.join(shadowed)}; the shell wins on the next start.")
        return True

    # ----------------------------------------------------------- entry points --
    def connect(self, wanted: str = "") -> dict[str, str] | None:
        """Run the whole flow. Returns the values to apply, or None if cancelled."""
        try:
            pid = self.pick_provider(wanted)
            if pid == "offline":
                return {"AI_PROVIDER": "offline"}
            values = {"AI_PROVIDER": pid, **self.credentials(pid)}
            values[REGISTRY[pid].model_env] = self.choose_model(self._provider(values))
            self.offer_save(values)
            return values
        except Cancelled:
            self.say("cancelled. nothing changed.")
            return None

    def model(self, provider: AIProvider, wanted: str = "") -> dict[str, str] | None:
        """Pick a model for the provider already on stage; remembered if /connect saved it."""
        try:
            name = self.choose_model(provider, wanted)
        except Cancelled:
            self.say("cancelled. nothing changed.")
            return None
        values = {provider.model_env: name}
        if user_env_path().is_file():
            self.save(values)
        return values

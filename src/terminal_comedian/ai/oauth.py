"""Browser login for OpenRouter: OAuth with PKCE, no client secret, no password.

OpenRouter documents this flow for CLI tools: the user signs in on
openrouter.ai, the browser is sent back to a one-shot server on this machine,
and the code it carries is exchanged for an API key billed to the user's own
account. Over SSH, where the browser cannot reach this machine, the page shows
the code instead and the user pastes it.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import urllib.parse
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer

from .http import request_json
from .provider import AIError

AUTH_URL = "https://openrouter.ai/auth"
EXCHANGE_URL = "https://openrouter.ai/api/v1/auth/keys"
KEY_LABEL = "Terminal Comedy Studio"

_PAGE = (
    "<!doctype html><meta charset='utf-8'><title>Terminal Comedy Studio</title>"
    "<body style='background:#111;color:#ff4fa3;font:20px monospace;text-align:center;padding-top:20vh'>"
    "<p>{message}</p><p style='color:#ccc'>You can close this tab and go back to the terminal.</p>"
)


class LoginFailed(AIError):
    pass


def pkce_pair() -> tuple[str, str]:
    """A random verifier and its S256 challenge (RFC 7636)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def auth_url(challenge: str, callback_url: str | None = None, state: str | None = None) -> str:
    query = {"code_challenge": challenge, "code_challenge_method": "S256", "key_label": KEY_LABEL}
    if callback_url:
        query["callback_url"] = callback_url
    if state:
        query["state"] = state
    return f"{AUTH_URL}?{urllib.parse.urlencode(query)}"


def exchange(code: str, verifier: str, timeout: float = 30.0) -> str:
    data = request_json(
        EXCHANGE_URL,
        {"code": code.strip(), "code_verifier": verifier, "code_challenge_method": "S256"},
        {},
        timeout,
    )
    key = data.get("key") if isinstance(data, dict) else None
    if not isinstance(key, str) or not key.strip():
        raise LoginFailed("OpenRouter did not return a key.")
    return key.strip()


class Callback:
    """A server on 127.0.0.1 that waits for one matching ?code=…&state=… redirect."""

    def __init__(self, state: str) -> None:
        self.state = state
        self.code = ""
        self.error = ""
        self.done = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                url = urllib.parse.urlsplit(self.path)
                if url.path != "/callback":
                    self.send_error(404)
                    return
                query = urllib.parse.parse_qs(url.query)
                code = (query.get("code") or [""])[0]
                if not code:
                    owner.error = "login was cancelled in the browser."
                    message = "Login cancelled."
                elif (query.get("state") or [""])[0] != owner.state:
                    message = "That login link was not started from this terminal."  # keep waiting
                else:
                    owner.code = code
                    message = "Connected. The comedian has a microphone now."
                body = _PAGE.format(message=message).encode("utf-8")
                self.send_response(200)
                self.send_header("content-type", "text/html; charset=utf-8")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                if owner.code or owner.error:
                    owner.done.set()

            def log_message(self, *args) -> None:  # keep the stage clean
                return

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/callback"

    def wait(self, timeout: float) -> str:
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
        thread.start()
        try:
            finished = self.done.wait(timeout)
        finally:
            self.server.shutdown()
            self.server.server_close()
        if not finished:
            raise LoginFailed("no answer from the browser in time.")
        if self.error:
            raise LoginFailed(self.error)
        return self.code


def browser_login(
    open_browser: Callable[[str], bool],
    say: Callable[[str], None],
    timeout: float = 180.0,
    exchange_code: Callable[[str, str], str] = exchange,
) -> str:
    """Open the browser, wait for the redirect, return the new API key."""
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)
    callback = Callback(state)
    url = auth_url(challenge, callback.url, state)
    try:
        opened = bool(open_browser(url))
    except Exception:  # a missing browser is not a crash
        opened = False
    say("opened your browser. sign in to OpenRouter there." if opened else "open this link in a browser:")
    say(url)
    say(f"waiting up to {int(timeout)}s… (Ctrl-C to give up)")
    try:
        code = callback.wait(timeout)
    except KeyboardInterrupt:
        raise LoginFailed("login cancelled.") from None
    return exchange_code(code, verifier)


def pasted_code_login(
    ask: Callable[[str], str],
    say: Callable[[str], None],
    exchange_code: Callable[[str, str], str] = exchange,
) -> str:
    """Headless flow (SSH, containers): the page shows a code, the user pastes it."""
    verifier, challenge = pkce_pair()
    say("open this link on any device, sign in, then paste the code it shows:")
    say(auth_url(challenge))
    code = ask("code: ").strip()
    if not code:
        raise LoginFailed("no code entered.")
    return exchange_code(code, verifier)

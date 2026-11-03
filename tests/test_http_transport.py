"""Real sockets, fake gateway.

Proves the OpenAI-compatible transport (OmniRoute, OpenRouter, OpenAI and any
local server) works end to end without a single real credential: the test
starts its own throwaway gateway on localhost.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from terminal_comedian.ai.local import LocalProvider
from terminal_comedian.ai.omniroute import OmniRouteProvider
from terminal_comedian.ai.openai import OpenAIProvider
from terminal_comedian.ai.provider import ProviderUnavailable
from terminal_comedian.config.settings import Settings

REPLY = '{"text": "your cache has opinions", "emotion": "sarcastic", "animation": "reaction", "duration": 2.5}'


class Gateway(BaseHTTPRequestHandler):
    status = 200
    seen: list[dict] = []

    def log_message(self, *args):  # keep pytest output clean
        pass

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        Gateway.seen.append({"path": self.path, "auth": self.headers.get("authorization", ""), "body": body})
        if Gateway.status != 200:
            self.send_response(Gateway.status)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"nope"}}')
            return
        if body.get("stream"):
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.end_headers()
            for piece in ("your cache ", "has opinions"):
                chunk = {"choices": [{"delta": {"content": piece}}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.end_headers()
            return
        payload = {"choices": [{"message": {"content": REPLY}}], "usage": {"total_tokens": 42}}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture(name="gateway")
def _gateway():
    Gateway.seen = []
    Gateway.status = 200
    server = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    server.shutdown()
    server.server_close()


def settings(**environ):
    return Settings.load(
        cwd=None,
        environ={"HOME": "/nonexistent-tcs", "XDG_CONFIG_HOME": "/nonexistent-tcs", **environ},
    )


def test_local_server_without_a_key_performs_a_bit(gateway):
    provider = LocalProvider(settings(AI_PROVIDER="local", LOCAL_BASE_URL=gateway, LOCAL_MODEL="tiny-comic"))
    response = provider.generate_messages([{"role": "user", "content": "joke"}])
    assert response.text == "your cache has opinions"
    assert response.animation == "reaction"
    assert response.duration == 2.5
    assert Gateway.seen[-1]["path"] == "/v1/chat/completions"
    assert Gateway.seen[-1]["auth"] == ""


def test_omniroute_uses_the_configured_base_url_and_sends_the_key(gateway):
    provider = OmniRouteProvider(
        settings(AI_PROVIDER="omniroute", OMNIROUTE_BASE_URL=gateway, OMNIROUTE_API_KEY="test-token", OMNIROUTE_MODEL="m")
    )
    provider.generate_messages([{"role": "user", "content": "joke"}])
    assert Gateway.seen[-1]["auth"] == "Bearer test-token"
    assert Gateway.seen[-1]["body"]["model"] == "m"


def test_streaming_forwards_deltas_as_they_arrive(gateway):
    provider = OpenAIProvider(settings(AI_PROVIDER="openai", OPENAI_API_KEY="k", OPENAI_BASE_URL=gateway))
    pieces: list[str] = []
    text = provider.complete([{"role": "user", "content": "joke"}], on_delta=pieces.append)
    assert pieces == ["your cache ", "has opinions"]
    assert text == "your cache has opinions"


def test_authentication_failure_is_a_message_not_a_traceback(gateway):
    Gateway.status = 401
    provider = OpenAIProvider(settings(AI_PROVIDER="openai", OPENAI_API_KEY="k", OPENAI_BASE_URL=gateway))
    with pytest.raises(ProviderUnavailable) as error:
        provider.complete([{"role": "user", "content": "joke"}])
    assert "Check the API key" in str(error.value)


def test_a_dead_gateway_is_reported_as_unreachable():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    dead = f"http://127.0.0.1:{probe.getsockname()[1]}/v1"
    probe.close()
    provider = LocalProvider(settings(AI_PROVIDER="local", LOCAL_BASE_URL=dead))
    with pytest.raises(ProviderUnavailable) as error:
        provider.complete([{"role": "user", "content": "joke"}])
    assert "unreachable" in str(error.value)


def test_the_key_never_appears_in_the_error_output(gateway):
    Gateway.status = 500
    provider = OmniRouteProvider(
        settings(AI_PROVIDER="omniroute", OMNIROUTE_BASE_URL=gateway, OMNIROUTE_API_KEY="super-secret-token")
    )
    with pytest.raises(ProviderUnavailable) as error:
        provider.complete([{"role": "user", "content": "joke"}])
    assert "super-secret-token" not in str(error.value)

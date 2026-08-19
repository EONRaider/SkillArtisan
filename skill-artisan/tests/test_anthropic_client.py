#!/usr/bin/env python3
"""Tests for anthropic_client.py — the stdlib Messages API wrapper used by
gha_audit.py. All network calls are mocked (urllib.request.urlopen is
monkeypatched); this suite makes zero real HTTP requests.

Run: python3 -m unittest skill-artisan/tests/test_anthropic_client.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)
"""
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import anthropic_client  # noqa: E402


def fake_response(body: dict, status: int = 200):
    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(body).encode("utf-8")

    return FakeHTTPResponse()


class TestCreateMessage(unittest.TestCase):
    def test_returns_concatenated_text_blocks(self):
        payload = {"content": [{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}]}
        with patch("urllib.request.urlopen", return_value=fake_response(payload)):
            result = anthropic_client.create_message("prompt", api_key="key")
        self.assertEqual(result, "hello world")

    def test_ignores_non_text_blocks(self):
        payload = {"content": [{"type": "tool_use", "text": "ignored"}, {"type": "text", "text": "kept"}]}
        with patch("urllib.request.urlopen", return_value=fake_response(payload)):
            result = anthropic_client.create_message("prompt", api_key="key")
        self.assertEqual(result, "kept")

    def test_sends_expected_request_shape(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = {k.lower(): v for k, v in request.headers.items()}
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return fake_response({"content": [{"type": "text", "text": "ok"}]})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            anthropic_client.create_message("hi", api_key="sk-test", model="claude-sonnet-5", max_tokens=100)

        self.assertEqual(captured["url"], anthropic_client.API_URL)
        self.assertEqual(captured["headers"]["x-api-key"], "sk-test")
        self.assertEqual(captured["headers"]["anthropic-version"], anthropic_client.API_VERSION)
        self.assertEqual(captured["body"]["model"], "claude-sonnet-5")
        self.assertEqual(captured["body"]["max_tokens"], 100)
        self.assertEqual(captured["body"]["messages"], [{"role": "user", "content": "hi"}])

    def test_non_retryable_error_raises_immediately(self):
        error = urllib.error.HTTPError("url", 401, "unauthorized", {}, io.BytesIO(b"bad key"))
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(1)
            raise error

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(anthropic_client.AnthropicAPIError) as ctx:
                anthropic_client.create_message("hi", api_key="key")
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(len(calls), 1, "a 401 must not be retried")

    def test_retries_on_429_then_succeeds(self):
        attempts = {"n": 0}

        def fake_urlopen(request, timeout):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise urllib.error.HTTPError("url", 429, "rate limited", {}, io.BytesIO(b"slow down"))
            return fake_response({"content": [{"type": "text", "text": "done"}]})

        sleeps = []
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = anthropic_client.create_message("hi", api_key="key", sleep_fn=sleeps.append)

        self.assertEqual(result, "done")
        self.assertEqual(attempts["n"], 3)
        self.assertEqual(len(sleeps), 2, "should sleep once per retry")

    def test_gives_up_after_max_retries(self):
        def fake_urlopen(request, timeout):
            raise urllib.error.HTTPError("url", 503, "unavailable", {}, io.BytesIO(b"down"))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(anthropic_client.AnthropicAPIError) as ctx:
                anthropic_client.create_message("hi", api_key="key", sleep_fn=lambda s: None)
        self.assertEqual(ctx.exception.status, 503)

    def test_transport_failure_raises_api_error(self):
        def fake_urlopen(request, timeout):
            raise urllib.error.URLError("no route to host")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(anthropic_client.AnthropicAPIError):
                anthropic_client.create_message("hi", api_key="key")


if __name__ == "__main__":
    unittest.main()

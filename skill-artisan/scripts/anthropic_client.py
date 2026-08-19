#!/usr/bin/env python3
"""Minimal stdlib client for the Claude Messages API — a single POST, no
dependencies. Not a script itself (no CLI) — used by gha_audit.py to author
additive fixes for skills the mechanical audit flagged as broken.

Kept deliberately small (one endpoint, one method) so the rest of the
codebase's "dependency-free (stdlib only)" convention (see
references/script-design.md) doesn't need an exception just for this: urllib
is enough for a single JSON POST with a couple of headers.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_MAX_TOKENS = 8192
RETRY_STATUSES = {429, 500, 502, 503, 529}
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2


class AnthropicAPIError(RuntimeError):
    """Raised when the API returns an error response or the request fails
    after retries. Carries the HTTP status (or None for transport-level
    failures) so callers can decide whether to skip-and-continue."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _post(payload: dict, api_key: str, timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise AnthropicAPIError(f"HTTP {e.code}: {detail}", status=e.code) from e
    except urllib.error.URLError as e:
        raise AnthropicAPIError(f"request failed: {e.reason}") from e


def create_message(
    prompt: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = 120.0,
    sleep_fn=time.sleep,
) -> str:
    """Send a single-turn message and return the concatenated text of the
    response's content blocks. Retries transient failures (429/5xx) with a
    short exponential backoff; non-retryable errors (4xx other than 429)
    raise immediately."""
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    last_error: AnthropicAPIError | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = _post(payload, api_key, timeout)
        except AnthropicAPIError as e:
            last_error = e
            if e.status not in RETRY_STATUSES or attempt == MAX_RETRIES - 1:
                raise
            sleep_fn(RETRY_BASE_DELAY_SECONDS * (2 ** attempt))
            continue
        blocks = response.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    # Unreachable in practice (the loop always returns or raises), kept for
    # type-checkers and as a defensive fallback.
    raise last_error or AnthropicAPIError("request failed after retries")

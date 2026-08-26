"""Redact Bearer tokens from strings that may be logged or raised."""

from __future__ import annotations

import re

_BEARER = re.compile(r"(Bearer\s+)\S+", re.IGNORECASE)
_QUERY_TOKEN = re.compile(r"([?&]token=)[^&\s#]+", re.IGNORECASE)

ALLOWED_MDNS_TXT = frozenset(
    {"id", "api", "path", "series", "model", "auth", "scheme"}
)
FORBIDDEN_SECRET_KEYS = frozenset(
    {"token", "authorization", "password", "secret", "bearer"}
)


def redact_text(text: str, token: str = "") -> str:
    """Return text with Bearer values, query tokens, and the known token removed."""
    if not text:
        return text
    if token:
        text = text.replace(token, "<redacted>")
    text = _BEARER.sub(r"\1<redacted>", text)
    text = _QUERY_TOKEN.sub(r"\1<redacted>", text)
    return text


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

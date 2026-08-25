"""Typed errors for the LOIP HTTP/WebSocket client.

Messages must never include a Bearer token or a URL query token.
"""

from __future__ import annotations

from typing import Any


class LanbonError(Exception):
    """Base error for the LOIP client."""


class LanbonAuthError(LanbonError):
    """HTTP 401 / unauthorized."""


class LanbonConnectionError(LanbonError):
    """Transport failure (DNS, reset, refused)."""


class LanbonTimeoutError(LanbonError):
    """Connect or total request timeout."""


class LanbonRateLimitError(LanbonError):
    """HTTP 429 / rate_limited."""

    def __init__(self, message: str = "rate_limited", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LanbonEventsUnsupportedError(LanbonError):
    """Gateway declared polling or WS upgrade returned 404/501."""


class LanbonApiError(LanbonError):
    """LOIP application error with a standard `error.code`."""

    def __init__(
        self,
        code: str,
        message: str = "",
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.error_message = message
        self.details = details or {}
        self.request_id = request_id
        self.http_status = http_status


# Backward-compatible alias used by the Mesh-era 0.1.0 client.
LanbonCommandError = LanbonApiError

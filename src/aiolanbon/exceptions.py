"""Exceptions for aiolanbon."""


class LanbonError(Exception):
    """Base error for LANBON local API."""


class LanbonAuthError(LanbonError):
    """Authentication failed (invalid token)."""


class LanbonConnectionError(LanbonError):
    """Could not connect to the LANBON host."""


class LanbonCommandError(LanbonError):
    """Device rejected a command (`ok: false`)."""

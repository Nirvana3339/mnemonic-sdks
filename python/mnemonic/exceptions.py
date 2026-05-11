class MnemoError(Exception):
    """Base exception."""


class AuthError(MnemoError):
    """401 — invalid or missing API key."""


class RateLimitError(MnemoError):
    """429 — too many requests."""


class NotFoundError(MnemoError):
    """404 — referenced resource missing."""

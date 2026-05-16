"""Mnemonic SDK exceptions."""


class MnemonicError(Exception):
    """Base exception for all Mnemonic SDK errors."""
    pass

# Backwards compat alias
MnemoError = MnemonicError


class AuthError(MnemonicError):
    """Invalid or missing API key."""
    pass


class NotFoundError(MnemonicError):
    """Resource not found."""
    pass


class RateLimitError(MnemonicError):
    """Rate limit exceeded."""
    pass


class ValidationError(MnemonicError):
    """Request validation failed."""
    pass

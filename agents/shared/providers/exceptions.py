class ProviderError(Exception):
    """Base exception for all provider-related errors."""

    pass


class ProviderNotAvailableError(ProviderError):
    """Raised when a provider is not available or healthy."""

    pass


class ProviderExecutionError(ProviderError):
    """Raised when an error occurs during provider execution."""

    pass

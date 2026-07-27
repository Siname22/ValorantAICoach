from backend.providers.base.exceptions import (
    AuthenticationError,
    NotFoundError,
    ProviderError,
    RateLimitError,
)


class RiotError(ProviderError):
    """Base exception for Riot API provider errors."""

    pass


class RiotAuthenticationError(RiotError, AuthenticationError):
    """Raised when Riot API authentication fails."""

    pass


class RiotRateLimitError(RiotError, RateLimitError):
    """Raised when Riot API rate limit is exceeded."""

    pass


class RiotNotFoundError(RiotError, NotFoundError):
    """Raised when a resource is not found in Riot API."""

    pass

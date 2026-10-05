from backend.providers.base.exceptions import (
    AuthenticationError,
    HTTPProviderError,
    InvalidResponseError,
    NotFoundError,
    RateLimitError,
)


class RiotError(HTTPProviderError):
    """Base exception for Riot API provider errors."""

    pass


class RiotAuthenticationError(RiotError, AuthenticationError):
    """Raised when Riot API authentication fails."""

    pass


class RiotResponseError(RiotError, InvalidResponseError):
    """Riot returned malformed data rather than an availability error."""


class RiotRateLimitError(RiotError, RateLimitError):
    """Raised when Riot API rate limit is exceeded."""

    retry_after: float | None = None


class RiotNotFoundError(RiotError, NotFoundError):
    """Raised when a resource is not found in Riot API."""

    pass

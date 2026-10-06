from backend.providers.base.exceptions import (
    AuthenticationError,
    HTTPProviderError,
    InvalidResponseError,
    NotFoundError,
    RateLimitError,
)


class HenrikError(HTTPProviderError):
    """Base exception for HenrikDev provider errors."""

    pass


class HenrikAuthenticationError(HenrikError, AuthenticationError):
    """Raised when HenrikDev authentication fails."""

    pass


class HenrikResponseError(HenrikError, InvalidResponseError):
    """Henrik returned malformed data rather than an availability error."""


class HenrikRateLimitError(HenrikError, RateLimitError):
    """Raised when HenrikDev rate limit is exceeded."""

    pass


class HenrikNotFoundError(HenrikError, NotFoundError):
    """Raised when a resource is not found in HenrikDev."""

    pass

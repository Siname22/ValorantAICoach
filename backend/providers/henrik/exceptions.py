from backend.providers.base.exceptions import (
    AuthenticationError,
    NotFoundError,
    ProviderError,
    RateLimitError,
)


class HenrikError(ProviderError):
    """Base exception for HenrikDev provider errors."""

    pass


class HenrikAuthenticationError(HenrikError, AuthenticationError):
    """Raised when HenrikDev authentication fails."""

    pass


class HenrikRateLimitError(HenrikError, RateLimitError):
    """Raised when HenrikDev rate limit is exceeded."""

    pass


class HenrikNotFoundError(HenrikError, NotFoundError):
    """Raised when a resource is not found in HenrikDev."""

    pass

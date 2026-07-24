from backend.providers.base.exceptions import (
    AuthenticationError,
    NotFoundError,
    ProviderError,
    RateLimitError,
)


class TrackerError(ProviderError):
    """Base exception for Tracker.gg provider errors."""

    pass


class TrackerAuthenticationError(TrackerError, AuthenticationError):
    """Raised when Tracker.gg authentication fails."""

    pass


class TrackerRateLimit(TrackerError, RateLimitError):
    """Raised when Tracker.gg rate limit is exceeded."""

    pass


class TrackerNotFound(TrackerError, NotFoundError):
    """Raised when a player or resource is not found in Tracker.gg."""

    pass

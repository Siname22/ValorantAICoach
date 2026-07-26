from backend.providers.base.exceptions import (
    AuthenticationError,
    NotFoundError,
    ProviderError,
    RateLimitError,
    ServerError,
)


class TrackerError(ProviderError):
    """Base exception for Tracker.gg provider errors."""


class TrackerAuthenticationError(TrackerError, AuthenticationError):
    """Raised when Tracker.gg authentication fails (401/403)."""


class TrackerRateLimitError(TrackerError, RateLimitError):
    """
    Raised when the Tracker.gg rate limit is exceeded (429).

    Carries the ``Retry-After`` value (in seconds) when the API provides it,
    so callers can schedule a retry precisely.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.retry_after = retry_after


# Backwards-compatible alias kept for existing imports and tests.
TrackerRateLimit = TrackerRateLimitError


class TrackerNotFound(TrackerError, NotFoundError):
    """Raised when a player or resource is not found in Tracker.gg (404)."""


class TrackerServerError(TrackerError, ServerError):
    """Raised when Tracker.gg returns a server-side error (5xx)."""

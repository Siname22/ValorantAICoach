class ProviderError(Exception):
    """Base exception for all provider-related errors."""

    pass


class ConfigurationError(ProviderError):
    """Raised when a provider is misconfigured."""

    pass


class HTTPProviderError(ProviderError):
    """Base exception for HTTP-related provider errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AuthenticationError(HTTPProviderError):
    """Raised when authentication fails (401/403)."""

    pass


class RateLimitError(HTTPProviderError):
    """Raised when the provider rate limit is exceeded (429)."""

    pass


class NotFoundError(HTTPProviderError):
    """Raised when a resource is not found (404)."""

    pass


class TimeoutError(HTTPProviderError):
    """Raised when a request to the provider times out."""

    pass


class ServerError(HTTPProviderError):
    """Raised when the provider returns a server error (5xx)."""

    pass

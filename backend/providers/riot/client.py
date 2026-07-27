import httpx

from backend.providers.base.client import BaseHTTPClient

from .exceptions import (
    RiotAuthenticationError,
    RiotError,
    RiotNotFoundError,
    RiotRateLimitError,
)


class RiotHTTPClient(BaseHTTPClient):
    """
    HTTP client for the Riot API.
    Overrides _handle_error_response to map generic provider exceptions to
    Riot-specific ones.
    """

    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Maps HTTP status codes to Riot-specific exceptions.
        """
        status_code = response.status_code
        message = f"HTTP Error {status_code}: {response.text}"

        if status_code == 401 or status_code == 403:
            raise RiotAuthenticationError(message, status_code, response.text)
        elif status_code == 404:
            raise RiotNotFoundError(message, status_code, response.text)
        elif status_code == 429:
            raise RiotRateLimitError(message, status_code, response.text)
        elif status_code >= 500:
            # We can use a generic RiotError or create a RiotServerError if needed
            # For now, let's keep it consistent with the test expectations
            raise RiotError(
                f"Riot Server Error {status_code}: {response.text}",
                status_code,
                response.text,
            )
        else:
            raise RiotError(message, status_code, response.text)

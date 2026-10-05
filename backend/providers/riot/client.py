from math import isfinite
from typing import Any

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

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth_type: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        request_headers = dict(headers or {})
        if auth_type == "api_key":
            if self.config.api_key:
                request_headers["X-Riot-Token"] = self.config.api_key
            auth_type = None
        return await super().request(
            method,
            endpoint,
            params=params,
            json=json,
            headers=request_headers,
            auth_type=auth_type,
            **kwargs,
        )

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
            error = RiotRateLimitError(message, status_code, response.text)
            try:
                retry_after = float(response.headers["Retry-After"])
            except (KeyError, ValueError):
                pass
            else:
                if isfinite(retry_after) and retry_after >= 0:
                    error.retry_after = retry_after
            raise error
        elif status_code >= 500:
            raise RiotError(
                f"Riot Server Error {status_code}: {response.text}",
                status_code,
                response.text,
            )
        else:
            raise RiotError(message, status_code, response.text)

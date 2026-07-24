import asyncio
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from .config import ProviderConfig
from .exceptions import (
    AuthenticationError,
    HTTPProviderError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)

logger = logging.getLogger(__name__)


class BaseHTTPClient:
    """
    A reusable, typed, and robust HTTP client based on httpx.AsyncClient.
    Supports retries, exponential backoff, logging, and error handling.
    """

    def __init__(self, config: ProviderConfig, provider_name: str) -> None:
        self.config = config
        self.provider_name = provider_name
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        """Lazily initializes and returns the httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self.config.default_headers,
            )
        return self._client

    async def close(self) -> None:
        """Closes the underlying httpx.AsyncClient."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth_type: str | None = None,  # 'api_key' or 'bearer'
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Performs an HTTP request with retries and error handling.
        """
        client = await self.get_client()

        normalized_endpoint = self._normalize_endpoint(endpoint)

        # Prepare headers with auth
        request_headers = headers or {}
        if auth_type == "api_key" and self.config.api_key:
            request_headers["X-API-Key"] = self.config.api_key
        elif auth_type == "bearer" and self.config.api_key:
            request_headers["Authorization"] = f"Bearer {self.config.api_key}"

        last_exception = None
        for attempt in range(self.config.retries + 1):
            start_time = time.perf_counter()
            try:
                response = await client.request(
                    method=method,
                    url=normalized_endpoint,
                    params=params,
                    json=json,
                    headers=request_headers,
                    **kwargs,
                )
                duration_ms = (time.perf_counter() - start_time) * 1000

                self._log_request(method, endpoint, response.status_code, duration_ms)

                # Check for errors
                if response.is_success:
                    return response

                self._handle_error_response(response)

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.warning(
                    "%s Request failed (attempt %s/%s): %s",
                    self.provider_name,
                    attempt + 1,
                    self.config.retries + 1,
                    e,
                )
                if attempt < self.config.retries:
                    wait_time = self.config.backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                else:
                    raise TimeoutError(
                        f"Request timed out after {self.config.retries} retries"
                    ) from e

            except HTTPProviderError as e:
                # For 4xx/5xx errors, we might not want to retry unless it's a
                # 5xx or 429.
                if attempt < self.config.retries and (
                    e.status_code >= 500 or e.status_code == 429
                ):
                    wait_time = self.config.backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue
                raise e

        raise last_exception or HTTPProviderError(
            f"Request failed for {self.provider_name}"
        )

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint paths to preserve compatibility with mocked URLs."""
        if not endpoint:
            return endpoint

        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint

        if endpoint.startswith("/"):
            endpoint = endpoint[1:]

        parts = endpoint.split("/")
        normalized_parts = []
        for part in parts:
            if not part:
                continue
            if part.startswith(":"):
                normalized_parts.append(part)
            else:
                normalized_parts.append(quote(part, safe="-_.~"))

        return "/" + "/".join(normalized_parts)

    def _log_request(
        self, method: str, endpoint: str, status_code: int, duration_ms: float
    ) -> None:
        """Logs the request metadata to the observability system."""
        logger.info(
            "Provider: %s | Method: %s | Endpoint: %s | Status: %s | "
            "Duration: %.2fms",
            self.provider_name,
            method,
            endpoint,
            status_code,
            duration_ms,
        )

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Maps HTTP status codes to specific provider exceptions."""
        status_code = response.status_code
        message = f"HTTP Error {status_code}: {response.text}"

        if status_code == 401 or status_code == 403:
            raise AuthenticationError(message, status_code, response.text)
        elif status_code == 404:
            raise NotFoundError(message, status_code, response.text)
        elif status_code == 429:
            raise RateLimitError(message, status_code, response.text)
        elif status_code >= 500:
            raise ServerError(message, status_code, response.text)
        else:
            raise HTTPProviderError(message, status_code, response.text)

    # Convenience methods
    async def get(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", endpoint, **kwargs)

    async def patch(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PATCH", endpoint, **kwargs)

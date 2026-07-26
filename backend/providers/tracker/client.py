import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from backend.providers.base.client import BaseHTTPClient
from backend.providers.base.exceptions import ServerError

from .config import TrackerConfig
from .exceptions import TrackerRateLimitError

logger = logging.getLogger(__name__)

MAX_RETRY_AFTER_SECONDS = 30.0


def parse_retry_after(raw_value: str | None) -> float | None:
    """
    Parses a ``Retry-After`` header value.

    Supports both delta-seconds (``"2"``) and HTTP-date formats, returning
    the wait time in seconds, capped at ``MAX_RETRY_AFTER_SECONDS``.
    Returns ``None`` when the header is missing or unparseable.
    """
    if raw_value is None:
        return None

    try:
        seconds = float(raw_value)
    except ValueError:
        try:
            target = parsedate_to_datetime(raw_value)
        except (TypeError, ValueError):
            return None
        seconds = (target - datetime.now(UTC)).total_seconds()

    if seconds < 0:
        return None
    return min(seconds, MAX_RETRY_AFTER_SECONDS)


class TrackerHTTPClient(BaseHTTPClient):
    """
    HTTP client for the Tracker.gg API.

    Extends :class:`BaseHTTPClient`, reusing its session management, retry
    loop with exponential backoff, timeout handling and request logging.
    It adds only the Tracker-specific concerns:

    - Authentication via the ``TRN-Api-Key`` header required by Tracker.gg.
    - HTTP 429 handling that honours the ``Retry-After`` header: the wait
      time is attached to the raised :class:`TrackerRateLimitError` so the
      base retry loop (which retries 429s) and upstream callers can use it.
    """

    def __init__(self, config: TrackerConfig) -> None:
        super().__init__(config, provider_name="tracker")
        self.config: TrackerConfig = config

    async def get_json(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Performs an authenticated GET request and returns the parsed JSON body.
        """
        response = await self.request(
            "GET",
            endpoint,
            params=params,
            headers=self._auth_headers(),
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise ServerError(
                "Tracker.gg returned an unexpected JSON payload",
                response.status_code,
                response.text,
            )
        return payload

    def _auth_headers(self) -> dict[str, str]:
        """Builds the authentication headers required by Tracker.gg."""
        return {"TRN-Api-Key": self.config.api_key}

    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Maps HTTP status codes to provider exceptions.

        For 429 responses, raises :class:`TrackerRateLimitError` carrying the
        parsed ``Retry-After`` value. Because ``TrackerRateLimitError`` is a
        subclass of the base ``RateLimitError``/``HTTPProviderError``, the
        retry loop in :class:`BaseHTTPClient` still retries it transparently.
        """
        if response.status_code == 429:
            retry_after = parse_retry_after(response.headers.get("Retry-After"))
            if retry_after is not None:
                logger.warning(
                    "tracker rate limited, Retry-After=%.2fs",
                    retry_after,
                )
            raise TrackerRateLimitError(
                f"HTTP Error 429: {response.text}",
                status_code=429,
                response_body=response.text,
                retry_after=retry_after,
            )
        super()._handle_error_response(response)

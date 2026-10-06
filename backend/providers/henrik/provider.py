from time import perf_counter
from typing import NoReturn
from urllib.parse import quote

import httpx

from backend.providers.base.exceptions import (
    AuthenticationError,
    HTTPProviderError,
    NotFoundError,
    RateLimitError,
)
from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.base.provider import BaseProvider

from .config import HenrikConfig
from .exceptions import (
    HenrikAuthenticationError,
    HenrikError,
    HenrikNotFoundError,
    HenrikRateLimitError,
    HenrikResponseError,
)
from .models import HenrikMatch, HenrikMMRData, HenrikPlayer, HenrikRank, HenrikResponse


class HenrikProvider(BaseProvider):
    """
    Implementation of HenrikDev provider for Valorant player data.
    Inherits from BaseProvider and utilizes BaseHTTPClient for communication.
    """

    def __init__(self, config: HenrikConfig) -> None:
        super().__init__(config)
        self.config: HenrikConfig = config

    @property
    def name(self) -> str:
        return "henrik"

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": self.config.api_key} if self.config.api_key else {}

    async def health_check(self) -> ProviderHealth:
        """
        Performs a health check on the HenrikDev API.
        """
        started = perf_counter()
        try:
            response = await self.client.get(
                f"/status/{quote(self.config.health_region, safe='')}",
                headers=self._auth_headers,
            )
            if response.status_code == 200:
                return ProviderHealth(
                    status=ProviderStatus.HEALTHY,
                    message="HenrikDev API is reachable",
                    latency_ms=(perf_counter() - started) * 1000,
                )
            return ProviderHealth(
                status=ProviderStatus.DEGRADED,
                message=f"Unexpected status: {response.status_code}",
                latency_ms=(perf_counter() - started) * 1000,
            )
        except Exception as error:
            message = "HenrikDev health check failed"
            if isinstance(error, HTTPProviderError) and error.status_code is not None:
                message += f" (HTTP {error.status_code})"
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                message=message,
                latency_ms=(perf_counter() - started) * 1000,
            )

    async def get_account(self, name: str, tag: str) -> HenrikPlayer:
        """
        Fetches account information by name and tag.
        """
        endpoint = f"/account/{quote(name, safe='')}/{quote(tag, safe='')}"
        try:
            response = await self.client.get(endpoint, headers=self._auth_headers)
            return (
                HenrikResponse[HenrikPlayer]
                .model_validate(response.json(), strict=True)
                .data
            )
        except Exception as e:
            self._handle_henrik_error(e)

    async def get_matches(self, region: str, name: str, tag: str) -> list[HenrikMatch]:
        """
        Fetches stored lifetime summaries for a player; history may be incomplete.
        """
        endpoint = (
            f"/stored-matches/{quote(region, safe='')}/"
            f"{quote(name, safe='')}/{quote(tag, safe='')}"
        )
        try:
            response = await self.client.get(endpoint, headers=self._auth_headers)
            return (
                HenrikResponse[list[HenrikMatch]]
                .model_validate(response.json(), strict=True)
                .data
            )
        except Exception as e:
            self._handle_henrik_error(e)

    async def get_rank(self, region: str, name: str, tag: str) -> HenrikRank:
        """Fetch current rank and RR, rather than ELO or the last-match RR change."""
        base_url = httpx.URL(self.config.base_url.rstrip("/") + "/")
        endpoint = str(
            base_url.join(
                f"../v2/mmr/{quote(region, safe='')}/"
                f"{quote(name, safe='')}/{quote(tag, safe='')}"
            )
        )
        try:
            response = await self.client.get(endpoint, headers=self._auth_headers)
            current = (
                HenrikResponse[HenrikMMRData]
                .model_validate(response.json(), strict=True)
                .data.current_data
            )
            return HenrikRank(
                tier_name=current.currenttierpatched,
                points=current.ranking_in_tier,
                rank_icon_url=current.images.small if current.images else None,
            )
        except Exception as e:
            self._handle_henrik_error(e)

    def _handle_henrik_error(self, error: Exception) -> NoReturn:
        """Maps generic provider errors to Henrik-specific exceptions."""
        if isinstance(error, HenrikError):
            raise error
        if isinstance(error, HTTPProviderError):
            error_type: type[HenrikError] = HenrikError
            if isinstance(error, AuthenticationError):
                error_type = HenrikAuthenticationError
            elif isinstance(error, NotFoundError):
                error_type = HenrikNotFoundError
            elif isinstance(error, RateLimitError):
                error_type = HenrikRateLimitError
            message = "HenrikDev request failed"
            if error.status_code is not None:
                message += f" (HTTP {error.status_code})"
            raise error_type(message, status_code=error.status_code) from error
        if isinstance(error, (ValueError, TypeError)):
            raise HenrikResponseError(
                "HenrikDev returned invalid response data"
            ) from error
        raise HenrikError("HenrikDev request failed") from error

from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.base.provider import BaseProvider

from .config import HenrikConfig
from .exceptions import (
    HenrikAuthenticationError,
    HenrikError,
    HenrikNotFoundError,
    HenrikRateLimitError,
)
from .models import HenrikMatch, HenrikPlayer


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

    async def health_check(self) -> ProviderHealth:
        """
        Performs a health check on the HenrikDev API.
        """
        try:
            # HenrikDev status endpoint (v1 status)
            response = await self.client.get("/status/eu", auth_type="api_key")
            if response.status_code == 200:
                return ProviderHealth(
                    status=ProviderStatus.HEALTHY, message="HenrikDev API is reachable"
                )
            return ProviderHealth(
                status=ProviderStatus.DEGRADED,
                message=f"Unexpected status: {response.status_code}",
            )
        except Exception as e:
            return ProviderHealth(status=ProviderStatus.UNHEALTHY, message=str(e))

    async def get_account(self, name: str, tag: str) -> HenrikPlayer:
        """
        Fetches account information by name and tag.
        """
        endpoint = f"/account/{name}/{tag}"
        try:
            response = await self.client.get(endpoint, auth_type="api_key")
            data = response.json().get("data", {})
            return HenrikPlayer(**data)
        except Exception as e:
            self._handle_henrik_error(e)
            raise

    async def get_matches(self, region: str, name: str, tag: str) -> list[HenrikMatch]:
        """
        Fetches recent matches for a player.
        """
        endpoint = f"/lifetime/matches/{region}/{name}/{tag}"
        try:
            response = await self.client.get(endpoint, auth_type="api_key")
            matches_data = response.json().get("data", [])
            return [HenrikMatch(**m) for m in matches_data]
        except Exception as e:
            self._handle_henrik_error(e)
            raise

    def _handle_henrik_error(self, error: Exception) -> None:
        """Maps generic provider errors to Henrik-specific exceptions."""
        from backend.providers.base.exceptions import (
            AuthenticationError,
            NotFoundError,
            RateLimitError,
        )

        if isinstance(error, AuthenticationError):
            raise HenrikAuthenticationError(str(error)) from error
        elif isinstance(error, NotFoundError):
            raise HenrikNotFoundError(str(error)) from error
        elif isinstance(error, RateLimitError):
            raise HenrikRateLimitError(str(error)) from error
        elif not isinstance(error, HenrikError):
            raise HenrikError(
                f"An unexpected error occurred in HenrikProvider: {error}"
            ) from error

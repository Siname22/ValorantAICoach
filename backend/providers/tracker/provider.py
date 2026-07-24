from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.base.provider import BaseProvider

from .config import TrackerConfig
from .exceptions import (
    TrackerAuthenticationError,
    TrackerError,
    TrackerNotFound,
    TrackerRateLimit,
)
from .models import MatchSummary, PlayerIdentity, PlayerStats


class TrackerProvider(BaseProvider):
    """
    Implementation of Tracker.gg provider for Valorant player data.
    Inherits from BaseProvider and utilizes BaseHTTPClient for communication.
    """

    def __init__(self, config: TrackerConfig) -> None:
        super().__init__(config)
        self.config: TrackerConfig = config

    @property
    def name(self) -> str:
        return "tracker"

    async def health_check(self) -> ProviderHealth:
        """
        Performs a health check by calling a basic endpoint.
        """
        try:
            # Using a simple endpoint for health check, e.g., fetching a known
            # public profile or just a ping if available.
            # For Tracker.gg, we might just try to hit the base URL or a
            # simple metadata endpoint.
            response = await self.client.get("/", auth_type="api_key")
            if response.status_code == 200:
                return ProviderHealth(
                    status=ProviderStatus.HEALTHY, message="Tracker.gg API is reachable"
                )
            return ProviderHealth(
                status=ProviderStatus.DEGRADED,
                message=f"Unexpected status: {response.status_code}",
            )
        except Exception as e:
            return ProviderHealth(status=ProviderStatus.UNHEALTHY, message=str(e))

    async def get_player(self, platform: str, identifier: str) -> PlayerIdentity:
        """
        Fetches basic player identity information.

        Args:
            platform: The platform (e.g., 'riot').
            identifier: The player identifier (e.g., 'Name#Tag').
        """
        endpoint = f"/profile/{platform}/{identifier}"
        try:
            response = await self.client.get(endpoint, auth_type="api_key")
            data = response.json().get("data", {})
            return PlayerIdentity(**data.get("platformInfo", {}))
        except Exception as e:
            self._handle_tracker_error(e)
            raise

    async def get_player_stats(self, platform: str, identifier: str) -> PlayerStats:
        """
        Fetches aggregated player stats.
        """
        endpoint = f"/profile/{platform}/{identifier}"
        try:
            response = await self.client.get(endpoint, auth_type="api_key")
            data = (
                response.json()
                .get("data", {})
                .get("segments", [{}])[0]
                .get("stats", {})
            )
            return PlayerStats(**data)
        except Exception as e:
            self._handle_tracker_error(e)
            raise

    async def get_recent_matches(
        self, platform: str, identifier: str
    ) -> list[MatchSummary]:
        """
        Fetches a list of recent matches for the player.
        """
        endpoint = f"/profile/{platform}/{identifier}/matches"
        try:
            response = await self.client.get(endpoint, auth_type="api_key")
            matches_data = response.json().get("data", {}).get("matches", [])

            # Mapping raw match data to MatchSummary model.
            # TODO: Refine mapping once exact Tracker.gg v2 schema is
            # confirmed for matches.
            summaries = []
            for m in matches_data:
                # This is a simplified mapping for the scaffold
                summaries.append(
                    MatchSummary(
                        matchId=m.get("attributes", {}).get("matchId", "unknown"),
                        mapName=m.get("metadata", {}).get("mapName", "unknown"),
                        agentName=m.get("metadata", {}).get("agentName", "unknown"),
                        result=m.get("metadata", {}).get("result", "unknown"),
                        kills=m.get("stats", {}).get("kills", {}).get("value", 0),
                        deaths=m.get("stats", {}).get("deaths", {}).get("value", 0),
                        assists=m.get("stats", {}).get("assists", {}).get("value", 0),
                        score=m.get("stats", {}).get("score", {}).get("value", 0),
                        timestamp=m.get("metadata", {}).get("timestamp", "unknown"),
                    )
                )
            return summaries
        except Exception as e:
            self._handle_tracker_error(e)
            raise

    def _handle_tracker_error(self, error: Exception) -> None:
        """Maps generic provider errors to Tracker-specific exceptions."""
        from backend.providers.base.exceptions import (
            AuthenticationError,
            NotFoundError,
            RateLimitError,
        )

        if isinstance(error, AuthenticationError):
            raise TrackerAuthenticationError(str(error)) from error
        elif isinstance(error, NotFoundError):
            raise TrackerNotFound(str(error)) from error
        elif isinstance(error, RateLimitError):
            raise TrackerRateLimit(str(error)) from error
        elif not isinstance(error, TrackerError):
            raise TrackerError(
                f"An unexpected error occurred in TrackerProvider: {error}"
            ) from error

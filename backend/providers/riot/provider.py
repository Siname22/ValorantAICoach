from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.base.provider import BaseProvider

from .client import RiotHTTPClient
from .config import RiotConfig
from .exceptions import (
    RiotAuthenticationError,
    RiotError,
    RiotNotFoundError,
    RiotRateLimitError,
)
from .models import Match, Player, Rank


class RiotProvider(BaseProvider):
    """
    Implementation of Riot API provider for Valorant player data.
    Inherits from BaseProvider and utilizes BaseHTTPClient for communication.
    """

    def __init__(self, config: RiotConfig) -> None:
        super().__init__(config)
        self.config: RiotConfig = config

    @property
    def name(self) -> str:
        return "riot"

    @property
    def client(self) -> RiotHTTPClient:
        """Lazily initializes and returns the RiotHTTPClient."""
        if self._client is None:
            self._client = RiotHTTPClient(self.config, self.name)
        return self._client

    async def health_check(self) -> ProviderHealth:
        """
        Performs a health check on the Riot API.
        This typically involves hitting a simple, unauthenticated endpoint.
        For Valorant API, a common approach is to check status or a public endpoint.
        """
        try:
            # Riot API status endpoint
            # (example, actual endpoint might vary or require region)
            # For simplicity, we'll hit the base URL,
            # assuming it returns 200 for healthy
            response = await self.client.get(
                "/", auth_type="api_key"
            )  # API Key is often required even for status
            if response.status_code == 200:
                return ProviderHealth(
                    status=ProviderStatus.HEALTHY, message="Riot API is reachable"
                )
            return ProviderHealth(
                status=ProviderStatus.DEGRADED,
                message=f"Unexpected status: {response.status_code}",
            )
        except Exception as e:
            return ProviderHealth(status=ProviderStatus.UNHEALTHY, message=str(e))

    async def get_player_by_riot_id(self, game_name: str, tag_line: str) -> Player:
        """
        Fetches player information by Riot ID (gameName and tagLine).

        NOTE: The Riot API typically requires using the Account-V1 API
        to get PUUID from Riot ID,
        and then using the PUUID with the Valorant Match-V1 API.
        This method will simulate that
        by returning a dummy Player object for now,
        as per "No implementar llamadas reales todavía".
        """
        # TODO: Implement actual call to Riot Account-V1 API to get PUUID,
        # then Valorant Match-V1 API
        # For now, return a mocked player object.
        return Player(
            puuid="mock-puuid-123",
            gameName=game_name,
            tagLine=tag_line,
            region=self.config.region,
            accountLevel=100,
        )

    async def get_player_match_history(self, puuid: str) -> list[Match]:
        """
        Fetches a list of recent matches for a player using their PUUID.

        NOTE: This method will simulate API response by returning dummy Match objects.
        """
        # TODO: Implement actual call to Valorant Match-V1 API
        # For now, return mocked match data.
        return [
            Match(
                matchId="mock-match-1",
                mapId="Ascent",
                gameMode="Competitive",
                gameStartTimeMillis=1672531200000,  # Jan 1, 2023 00:00:00 GMT
                result="Victory",
                player_stats={
                    "kills": 20,
                    "deaths": 10,
                    "assists": 5,
                    "score": 5000,
                    "averageCombatScore": 250.5,
                    "character": "Jett",
                },
            ),
            Match(
                matchId="mock-match-2",
                mapId="Bind",
                gameMode="Competitive",
                gameStartTimeMillis=1672617600000,  # Jan 2, 2023 00:00:00 GMT
                result="Defeat",
                player_stats={
                    "kills": 15,
                    "deaths": 18,
                    "assists": 3,
                    "score": 3500,
                    "averageCombatScore": 180.0,
                    "character": "Raze",
                },
            ),
        ]

    async def get_player_rank(self, puuid: str) -> Rank:
        """
        Fetches a player's current competitive rank.

        NOTE: This method will simulate API response by returning a dummy Rank object.
        """
        # TODO: Implement actual call to Valorant Match-V1 API
        # or a dedicated endpoint if available
        # For now, return a mocked rank object.
        return Rank(tier="Immortal", rank="Immortal 3", rankedRating=800)

    def _handle_riot_error(self, error: Exception) -> None:
        """
        Maps generic provider errors to Riot-specific exceptions.
        """
        from backend.providers.base.exceptions import (
            AuthenticationError,
            NotFoundError,
            RateLimitError,
        )

        if isinstance(error, AuthenticationError):
            raise RiotAuthenticationError(str(error)) from error
        elif isinstance(error, NotFoundError):
            raise RiotNotFoundError(str(error)) from error
        elif isinstance(error, RateLimitError):
            raise RiotRateLimitError(str(error)) from error
        elif not isinstance(error, RiotError):
            raise RiotError(
                f"An unexpected error occurred in RiotProvider: {error}"
            ) from error

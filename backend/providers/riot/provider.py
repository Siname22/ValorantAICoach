import logging
from typing import Any
from urllib.parse import quote

from pydantic import ValidationError

from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.base.provider import BaseProvider

from .client import RiotHTTPClient
from .config import RiotConfig
from .exceptions import RiotError, RiotResponseError
from .models import Match, MatchPlayerStats, Player, Rank

logger = logging.getLogger(__name__)


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
        """Check the official VALORANT status endpoint on the configured shard."""
        try:
            response = await self.client.get(
                "/val/status/v1/platform-data", auth_type="api_key"
            )
            if response.status_code == 200:
                return ProviderHealth(
                    status=ProviderStatus.HEALTHY, message="Riot API is reachable"
                )
            return ProviderHealth(
                status=ProviderStatus.DEGRADED,
                message=f"Unexpected status: {response.status_code}",
            )
        except Exception as error:
            message = "Riot API is unavailable"
            if isinstance(error, RiotError) and error.status_code is not None:
                message = f"Riot API returned HTTP {error.status_code}"
            return ProviderHealth(status=ProviderStatus.UNHEALTHY, message=message)

    async def get_player_by_riot_id(self, game_name: str, tag_line: str) -> Player:
        """Resolve a Riot ID on the continental account-v1 cluster."""
        account = await self._get_json(
            f"{self.config.account_base_url.rstrip('/')}"
            f"/riot/account/v1/accounts/by-riot-id/"
            f"{quote(game_name, safe='')}/{quote(tag_line, safe='')}",
        )
        if not isinstance(account.get("puuid"), str) or not account["puuid"]:
            raise RiotResponseError("Incomplete Riot account response: missing PUUID")
        try:
            return Player(
                puuid=account["puuid"],
                gameName=account.get("gameName") or game_name,
                tagLine=account.get("tagLine") or tag_line,
                region=self.config.region,
            )
        except ValidationError as error:
            raise RiotResponseError("Invalid Riot account identity") from error

    async def _get_json(self, endpoint: str) -> dict[str, Any]:
        response = await self.client.get(endpoint, auth_type="api_key")
        try:
            data = response.json()
        except ValueError as error:
            raise RiotResponseError("Invalid JSON response from Riot API") from error
        if not isinstance(data, dict):
            raise RiotResponseError(
                f"Invalid Riot response for {endpoint}: expected an object"
            )
        return data

    async def get_player_match_history(
        self, puuid: str, *, limit: int | None = None
    ) -> list[Match]:
        """Fetch a bounded matchlist and summarize official details for this PUUID."""
        history_limit = self.config.match_history_limit if limit is None else limit
        if not 1 <= history_limit <= 20:
            raise ValueError("Riot match history limit must be between 1 and 20")
        matchlist = await self._get_json(
            f"/val/match/v1/matchlists/by-puuid/{quote(puuid, safe='')}"
        )
        history = matchlist.get("history")
        if not isinstance(history, list):
            raise RiotResponseError("Invalid Riot match history: expected a list")
        matches: list[Match] = []
        for entry in history[:history_limit]:
            if not isinstance(entry, dict):
                continue
            match_id = entry.get("matchId")
            if not isinstance(match_id, str) or not match_id:
                continue
            try:
                detail = await self.get_match(match_id)
            except RiotError as error:
                if error.status_code is not None:
                    raise
                logger.warning("Skipping invalid Riot match detail")
                continue
            match = self._summarize_match(detail, puuid)
            if match is not None:
                matches.append(match)
        if history and not matches:
            raise RiotResponseError(
                "Riot match history contained no usable player match details"
            )
        return matches

    @staticmethod
    def _summarize_match(detail: dict[str, Any], puuid: str) -> Match | None:
        try:
            info = detail["matchInfo"]
            if not isinstance(info, dict):
                return None
            player = next(
                (
                    p
                    for p in detail.get("players") or []
                    if isinstance(p, dict) and p.get("puuid") == puuid
                ),
                None,
            )
            if player is None or not isinstance(player.get("stats"), dict):
                logger.warning("Skipping Riot match without player stats")
                return None
            if (
                not isinstance(player.get("characterId"), str)
                or not player["characterId"]
            ):
                logger.warning("Skipping Riot match without a character ID")
                return None
            stats = player["stats"]
            rounds = stats.get("roundsPlayed", 0)
            if not all(
                field in stats for field in ("kills", "deaths", "assists", "score")
            ) and (not isinstance(rounds, int) or rounds <= 0):
                logger.warning("Skipping Riot match with incomplete numeric stats")
                return None
            # Riot may omit zero-valued numeric fields from otherwise valid stats.
            player_stats = MatchPlayerStats(
                kills=stats.get("kills", 0),
                deaths=stats.get("deaths", 0),
                assists=stats.get("assists", 0),
                score=stats.get("score", 0),
                character=player["characterId"],
            )
            if isinstance(rounds, int) and rounds > 0:
                player_stats.acs = player_stats.score / rounds

            teams = [t for t in detail.get("teams") or [] if isinstance(t, dict)]
            team_id = player.get("teamId")
            team = next(
                (
                    t
                    for t in teams
                    if isinstance(team_id, str)
                    and team_id
                    and t.get("teamId") == team_id
                ),
                {},
            )
            result = "Unknown"
            if team.get("won") is True:
                result = "Victory"
            elif team.get("won") is False:
                if any(t.get("won") is True for t in teams):
                    result = "Defeat"
                elif (
                    info.get("isCompleted") is True
                    and len(teams) > 1
                    and all(t.get("won") is False for t in teams)
                ):
                    result = "Draw"
            return Match(
                matchId=info["matchId"],
                mapId=info["mapId"],
                gameMode=info["gameMode"],
                gameStartTimeMillis=info["gameStartMillis"],
                result=result,
                player_stats=player_stats,
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping incomplete Riot match detail")
            return None

    async def get_match(self, match_id: str) -> dict[str, Any]:
        """Return an official match detail from the configured VALORANT shard."""
        detail = await self._get_json(
            f"/val/match/v1/matches/{quote(match_id, safe='')}"
        )
        info = detail.get("matchInfo")
        if (
            not isinstance(info, dict)
            or not isinstance(info.get("matchId"), str)
            or not info["matchId"]
        ):
            raise RiotResponseError(
                "Invalid Riot match detail: missing matchInfo.matchId"
            )
        return detail

    async def get_player_rank(self, puuid: str) -> Rank:
        """The official API exposes leaderboards, but no current rank by PUUID."""
        raise NotImplementedError(
            "The official Riot API does not support current player rank or RR by PUUID"
        )

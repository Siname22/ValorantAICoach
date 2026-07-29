import logging
from typing import Any

from backend.providers.base.exceptions import NotFoundError
from backend.providers.base.models import ProviderStatus
from backend.providers.henrik.provider import HenrikProvider
from backend.providers.riot.provider import RiotProvider
from backend.providers.tracker.provider import TrackerProvider
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# --- Unified Domain Models ---


class PlayerProfile(BaseModel):
    """Unified domain model for a player profile."""

    puuid: str | None = None
    game_name: str
    tag_line: str
    region: str | None = None
    account_level: int | None = None
    avatar_url: str | None = None
    rank_name: str | None = None
    rank_tier: str | None = None
    rank_icon_url: str | None = None


class PlayerRank(BaseModel):
    """Unified domain model for a player's rank."""

    tier_name: str
    rank_name: str | None = None
    rank_icon_url: str | None = None
    points: int | None = None


class PlayerMatch(BaseModel):
    """Unified domain model for a player's match."""

    match_id: str
    map_name: str
    mode: str
    timestamp: Any  # Can be int or str depending on provider
    result: str
    kills: int
    deaths: int
    assists: int
    score: int
    agent_name: str


class PlayerServiceError(Exception):
    """Base exception for PlayerService."""

    pass


class PlayerNotFoundError(PlayerServiceError):
    """Raised when a player is not found across all providers."""

    pass


# --- Service Implementation ---


class PlayerService:
    """
    Service layer to coordinate data from different providers (Tracker, Henrik, Riot).
    Implements a fallback strategy: Tracker -> Henrik -> Riot.
    """

    def __init__(
        self,
        riot_provider: RiotProvider,
        henrik_provider: HenrikProvider,
        tracker_provider: TrackerProvider,
    ) -> None:
        self.riot = riot_provider
        self.henrik = henrik_provider
        self.tracker = tracker_provider
        # Order of priority for fallback
        self._providers = [self.tracker, self.henrik, self.riot]

    async def get_complete_player_profile(
        self, game_name: str, tag_line: str
    ) -> PlayerProfile:
        """
        Aggregates player profile data with full enrichment.
        Attempts to get basic info from any provider and then enrich it.
        """
        # 1. Get basic identity and profile
        profile = await self.get_player(game_name, tag_line)

        # 2. Try to enrich with rank info if not already present
        if not profile.rank_name:
            try:
                rank = await self.get_rank(game_name, tag_line, puuid=profile.puuid)
                profile.rank_name = rank.tier_name
                profile.rank_icon_url = rank.rank_icon_url
            except Exception as e:
                logger.warning(
                    "Failed to enrich profile with rank for %s#%s: %s",
                    game_name,
                    tag_line,
                    e,
                )

        return profile

    async def get_player(self, game_name: str, tag_line: str) -> PlayerProfile:
        """
        Fetches basic player information using fallback strategy.
        """
        errors = []

        # Try Tracker first (most data)
        try:
            tracker_data = await self.tracker.get_player_profile(
                "riot", f"{game_name}#{tag_line}"
            )
            # Try to get stats for rank enrichment
            try:
                stats = await self.tracker.get_lifetime_stats(
                    "riot", f"{game_name}#{tag_line}"
                )
                rank_name = stats.rank.tier_name if stats.rank else None
                rank_icon = stats.rank.icon_url if stats.rank else None
            except Exception:
                rank_name, rank_icon = None, None

            return PlayerProfile(
                game_name=game_name,
                tag_line=tag_line,
                avatar_url=tracker_data.identity.avatar_url,
                rank_name=rank_name,
                rank_icon_url=rank_icon,
            )
        except NotFoundError:
            errors.append("Tracker: Player not found")
        except Exception as e:
            logger.error("Tracker failed for %s#%s: %s", game_name, tag_line, e)
            errors.append(f"Tracker: {str(e)}")

        # Try Henrik second
        try:
            henrik_data = await self.henrik.get_account(game_name, tag_line)
            return PlayerProfile(
                puuid=henrik_data.puuid,
                game_name=henrik_data.name,
                tag_line=henrik_data.tag,
                region=henrik_data.region,
                account_level=henrik_data.account_level,
            )
        except NotFoundError:
            errors.append("Henrik: Player not found")
        except Exception as e:
            logger.error("Henrik failed for %s#%s: %s", game_name, tag_line, e)
            errors.append(f"Henrik: {str(e)}")

        # Try Riot last
        try:
            riot_data = await self.riot.get_player_by_riot_id(game_name, tag_line)
            return PlayerProfile(
                puuid=riot_data.puuid,
                game_name=riot_data.game_name,
                tag_line=riot_data.tag_line,
                region=riot_data.region,
                account_level=riot_data.account_level,
            )
        except NotFoundError as e:
            errors.append("Riot: Player not found")
            raise PlayerNotFoundError(
                f"Player {game_name}#{tag_line} not found across providers: {errors}"
            ) from e
        except Exception as e:
            logger.error("Riot failed for %s#%s: %s", game_name, tag_line, e)
            errors.append(f"Riot: {str(e)}")
            raise PlayerServiceError(
                f"Failed to fetch player {game_name}#{tag_line}: {errors}"
            ) from e

    async def get_rank(
        self, game_name: str, tag_line: str, puuid: str | None = None
    ) -> PlayerRank:
        """
        Fetches player rank using fallback strategy.
        """
        # 1. Try Tracker
        try:
            stats = await self.tracker.get_lifetime_stats(
                "riot", f"{game_name}#{tag_line}"
            )
            if stats.rank:
                return PlayerRank(
                    tier_name=stats.rank.tier_name,
                    rank_icon_url=stats.rank.icon_url,
                    points=stats.rank.points,
                )
        except Exception as e:
            logger.debug(f"Tracker rank failed for {game_name}#{tag_line}: {e}")

        # 2. Try Riot (needs PUUID)
        if not puuid:
            try:
                player = await self.riot.get_player_by_riot_id(game_name, tag_line)
                puuid = player.puuid
            except Exception:
                pass

        if puuid:
            try:
                riot_rank = await self.riot.get_player_rank(puuid)
                return PlayerRank(
                    tier_name=riot_rank.tier,
                    rank_name=riot_rank.rank,
                    points=riot_rank.ranked_rating,
                )
            except Exception as e:
                logger.debug(f"Riot rank failed for {puuid}: {e}")

        raise PlayerNotFoundError(f"Rank not found for {game_name}#{tag_line}")

    async def get_recent_matches(
        self, game_name: str, tag_line: str, puuid: str | None = None
    ) -> list[PlayerMatch]:
        """
        Fetches recent matches using fallback strategy.
        """
        # 1. Try Tracker
        try:
            tracker_matches = await self.tracker.get_recent_matches(
                "riot", f"{game_name}#{tag_line}"
            )
            return [
                PlayerMatch(
                    match_id=m.match_id,
                    map_name=m.map_name,
                    mode=m.mode_name or "Unknown",
                    timestamp=m.timestamp,
                    result=m.result,
                    kills=m.kills,
                    deaths=m.deaths,
                    assists=m.assists,
                    score=m.score,
                    agent_name=m.agent_name,
                )
                for m in tracker_matches
            ]
        except Exception as e:
            logger.debug(f"Tracker matches failed for {game_name}#{tag_line}: {e}")

        # 2. Try Henrik
        try:
            # We need region for Henrik, try to guess or use a default if not known
            region = "na"  # Defaulting to na if unknown
            henrik_matches = await self.henrik.get_matches(region, game_name, tag_line)
            return [
                PlayerMatch(
                    match_id="unknown",
                    map_name=m.metadata.map,
                    mode=m.metadata.mode,
                    timestamp=m.metadata.game_start,
                    result="Unknown",
                    kills=0,
                    deaths=0,
                    assists=0,
                    score=0,
                    agent_name="Unknown",
                )
                for m in henrik_matches
            ]
        except Exception as e:
            logger.debug(f"Henrik matches failed for {game_name}#{tag_line}: {e}")

        # 3. Try Riot
        if not puuid:
            try:
                player = await self.riot.get_player_by_riot_id(game_name, tag_line)
                puuid = player.puuid
            except Exception:
                pass

        if puuid:
            try:
                riot_matches = await self.riot.get_player_match_history(puuid)
                return [
                    PlayerMatch(
                        match_id=m.match_id,
                        map_name=m.map_id,
                        mode=m.game_mode,
                        timestamp=m.game_start_time,
                        result=m.result,
                        kills=m.player_stats.kills,
                        deaths=m.player_stats.deaths,
                        assists=m.player_stats.assists,
                        score=m.player_stats.score,
                        agent_name=m.player_stats.agent_name,
                    )
                    for m in riot_matches
                ]
            except Exception as e:
                logger.debug(f"Riot matches failed for {puuid}: {e}")

        return []

    async def get_match(self, match_id: str) -> Any:
        """
        Fetches specific match details.
        Note: Currently providers have limited direct match fetch by ID.
        """
        # Placeholder for future implementation
        raise NotImplementedError("get_match is not yet implemented in providers")

    async def health(self) -> dict:
        """
        Checks the health of all providers.
        """
        results = {}
        for provider in self._providers:
            health = await provider.health_check()
            results[provider.name] = {
                "status": health.status,
                "message": health.message,
                "latency_ms": health.latency_ms,
            }

        # Overall status
        all_healthy = all(
            r["status"] == ProviderStatus.HEALTHY for r in results.values()
        )
        any_healthy = any(
            r["status"] == ProviderStatus.HEALTHY for r in results.values()
        )

        return {
            "status": (
                "healthy"
                if all_healthy
                else ("degraded" if any_healthy else "unhealthy")
            ),
            "providers": results,
        }

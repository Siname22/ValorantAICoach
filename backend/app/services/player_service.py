"""
Player service layer for Valorant AI Coach.

This service orchestrates data from multiple providers (Riot, Henrik, Tracker)
to provide a unified, high-level API for the application. It follows Clean
Architecture principles by defining its own domain models and using Dependency
Injection to interact with providers.
"""

import logging
from typing import Any, List, Optional, TypeVar, Callable, Awaitable

from pydantic import BaseModel, Field

from backend.providers.riot.provider import RiotProvider
from backend.providers.henrik.provider import HenrikProvider
from backend.providers.tracker.provider import TrackerProvider
from backend.providers.base.exceptions import NotFoundError, RateLimitError, AuthenticationError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# --- Domain Models (Provider-Agnostic) ---

class PlayerIdentity(BaseModel):
    """Unified player identity across all providers."""
    puuid: Optional[str] = None
    game_name: str
    tag_line: str
    region: Optional[str] = None
    account_level: Optional[int] = None
    avatar_url: Optional[str] = None
    source: str = Field(..., description="Provider that supplied the data")

class PlayerRank(BaseModel):
    """Unified rank information."""
    tier_name: str
    rank_name: Optional[str] = None
    rank_icon_url: Optional[str] = None
    points: Optional[int] = None
    source: str

class PlayerStatsOverview(BaseModel):
    """Unified lifetime stats overview."""
    kills: int
    deaths: int
    assists: int
    kd_ratio: float
    win_pct: float
    headshot_pct: float
    matches_played: Optional[int] = None
    damage_per_round: Optional[float] = None
    source: str

class UnifiedMatch(BaseModel):
    """Unified match summary."""
    match_id: str
    map_name: str
    mode: str
    timestamp: Any
    result: str
    kills: int
    deaths: int
    assists: int
    score: int
    agent_name: str
    source: str

class CompletePlayerProfile(BaseModel):
    """Fully aggregated player profile."""
    identity: PlayerIdentity
    rank: Optional[PlayerRank] = None
    stats: Optional[PlayerStatsOverview] = None
    recent_matches: List[UnifiedMatch] = Field(default_factory=list)

# --- Service Exceptions ---

class PlayerServiceError(Exception):
    """Base exception for PlayerService."""
    pass

class PlayerNotFoundError(PlayerServiceError):
    """Raised when a player is not found across all providers."""
    pass

# --- Service Implementation ---

class PlayerService:
    """
    Orchestrates player data retrieval with fallback logic.
    Priority: Tracker (Rich Data) -> Henrik -> Riot (Source of Truth).
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

    async def get_complete_player_profile(self, game_name: str, tag_line: str) -> CompletePlayerProfile:
        """
        Builds a complete profile by aggregating data from all providers.
        Fails if identity cannot be resolved, but other parts degrade gracefully.
        """
        identity = await self.get_player_identity(game_name, tag_line)
        
        rank = None
        try:
            rank = await self.get_rank(game_name, tag_line, puuid=identity.puuid)
        except Exception as e:
            logger.warning(f"Failed to fetch rank for {game_name}#{tag_line}: {e}")

        stats = None
        try:
            stats = await self.get_stats_overview(game_name, tag_line)
        except Exception as e:
            logger.warning(f"Failed to fetch stats for {game_name}#{tag_line}: {e}")

        matches = []
        try:
            matches = await self.get_recent_matches(game_name, tag_line, puuid=identity.puuid)
        except Exception as e:
            logger.warning(f"Failed to fetch matches for {game_name}#{tag_line}: {e}")

        return CompletePlayerProfile(
            identity=identity,
            rank=rank,
            stats=stats,
            recent_matches=matches
        )

    async def get_player_identity(self, game_name: str, tag_line: str) -> PlayerIdentity:
        """Resolves player identity with fallback: Tracker -> Henrik -> Riot."""
        return await self._execute_with_fallback(
            "get_player_identity",
            [
                lambda: self._get_identity_from_tracker(game_name, tag_line),
                lambda: self._get_identity_from_henrik(game_name, tag_line),
                lambda: self._get_identity_from_riot(game_name, tag_line)
            ]
        )

    async def get_rank(self, game_name: str, tag_line: str, puuid: Optional[str] = None) -> PlayerRank:
        """Resolves rank with fallback: Tracker -> Riot."""
        return await self._execute_with_fallback(
            "get_rank",
            [
                lambda: self._get_rank_from_tracker(game_name, tag_line),
                lambda: self._get_rank_from_riot(game_name, tag_line, puuid)
            ]
        )

    async def get_stats_overview(self, game_name: str, tag_line: str) -> PlayerStatsOverview:
        """Resolves stats: Tracker is currently the only provider for this."""
        return await self._execute_with_fallback(
            "get_stats_overview",
            [lambda: self._get_stats_from_tracker(game_name, tag_line)]
        )

    async def get_recent_matches(self, game_name: str, tag_line: str, puuid: Optional[str] = None) -> List[UnifiedMatch]:
        """Resolves recent matches with fallback: Tracker -> Riot -> Henrik."""
        return await self._execute_with_fallback(
            "get_recent_matches",
            [
                lambda: self._get_matches_from_tracker(game_name, tag_line),
                lambda: self._get_matches_from_riot(game_name, tag_line, puuid),
                lambda: self._get_matches_from_henrik(game_name, tag_line)
            ]
        )

    # --- Fallback Engine ---

    async def _execute_with_fallback(self, operation: str, actions: List[Callable[[], Awaitable[T]]]) -> T:
        """Executes a list of async actions until one succeeds."""
        last_error = None
        for action in actions:
            try:
                return await action()
            except (NotFoundError, PlayerNotFoundError):
                continue
            except Exception as e:
                logger.error(f"Provider failed during {operation}: {e}")
                last_error = e
                continue
        
        if last_error:
            raise PlayerServiceError(f"All providers failed for {operation}: {last_error}")
        raise PlayerNotFoundError(f"Data not found for {operation}")

    # --- Provider Adapters ---

    async def _get_identity_from_tracker(self, game_name: str, tag_line: str) -> PlayerIdentity:
        profile = await self.tracker.get_player_profile("riot", f"{game_name}#{tag_line}")
        return PlayerIdentity(
            game_name=game_name,
            tag_line=tag_line,
            avatar_url=profile.identity.avatar_url,
            source="tracker"
        )

    async def _get_identity_from_henrik(self, game_name: str, tag_line: str) -> PlayerIdentity:
        account = await self.henrik.get_account(game_name, tag_line)
        return PlayerIdentity(
            puuid=account.puuid,
            game_name=account.name,
            tag_line=account.tag,
            region=account.region,
            account_level=account.account_level,
            source="henrik"
        )

    async def _get_identity_from_riot(self, game_name: str, tag_line: str) -> PlayerIdentity:
        player = await self.riot.get_player_by_riot_id(game_name, tag_line)
        return PlayerIdentity(
            puuid=player.puuid,
            game_name=player.game_name,
            tag_line=player.tag_line,
            region=player.region,
            account_level=player.account_level,
            source="riot"
        )

    async def _get_rank_from_tracker(self, game_name: str, tag_line: str) -> PlayerRank:
        stats = await self.tracker.get_lifetime_stats("riot", f"{game_name}#{tag_line}")
        if not stats.rank:
            raise PlayerNotFoundError("Rank not available in Tracker")
        return PlayerRank(
            tier_name=stats.rank.tier_name,
            rank_icon_url=stats.rank.icon_url,
            points=stats.rank.points,
            source="tracker"
        )

    async def _get_rank_from_riot(self, game_name: str, tag_line: str, puuid: Optional[str]) -> PlayerRank:
        if not puuid:
            player = await self.riot.get_player_by_riot_id(game_name, tag_line)
            puuid = player.puuid
        rank = await self.riot.get_player_rank(puuid)
        return PlayerRank(
            tier_name=rank.tier,
            rank_name=rank.rank,
            points=rank.ranked_rating,
            source="riot"
        )

    async def _get_stats_from_tracker(self, game_name: str, tag_line: str) -> PlayerStatsOverview:
        stats = await self.tracker.get_lifetime_stats("riot", f"{game_name}#{tag_line}")
        return PlayerStatsOverview(
            kills=int(stats.kills.value),
            deaths=int(stats.deaths.value),
            assists=int(stats.assists.value),
            kd_ratio=stats.kd_ratio.value,
            win_pct=stats.win_pct.value,
            headshot_pct=stats.headshot_pct.value,
            matches_played=int(stats.matches_played.value) if stats.matches_played else None,
            damage_per_round=stats.damage_per_round.value if stats.damage_per_round else None,
            source="tracker"
        )

    async def _get_matches_from_tracker(self, game_name: str, tag_line: str) -> List[UnifiedMatch]:
        matches = await self.tracker.get_recent_matches("riot", f"{game_name}#{tag_line}")
        return [
            UnifiedMatch(
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
                source="tracker"
            ) for m in matches
        ]

    async def _get_matches_from_riot(self, game_name: str, tag_line: str, puuid: Optional[str]) -> List[UnifiedMatch]:
        if not puuid:
            player = await self.riot.get_player_by_riot_id(game_name, tag_line)
            puuid = player.puuid
        matches = await self.riot.get_player_match_history(puuid)
        return [
            UnifiedMatch(
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
                source="riot"
            ) for m in matches
        ]

    async def _get_matches_from_henrik(self, game_name: str, tag_line: str) -> List[UnifiedMatch]:
        # Henrik needs region, defaulting to 'na' for lookup
        matches = await self.henrik.get_matches("na", game_name, tag_line)
        return [
            UnifiedMatch(
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
                source="henrik"
            ) for m in matches
        ]

    async def close(self) -> None:
        """Closes all underlying provider clients."""
        await self.riot.close()
        await self.henrik.close()
        await self.tracker.close()

import asyncio
import logging
from typing import Any, Literal, NoReturn

from backend.providers.base.exceptions import InvalidResponseError, NotFoundError
from backend.providers.base.models import ProviderStatus
from backend.providers.henrik.provider import HenrikProvider
from backend.providers.riot.provider import RiotProvider
from backend.providers.tracker.provider import TrackerProvider
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, ValidationError

logger = logging.getLogger(__name__)


class PlayerIdentity(BaseModel):
    """Provider-backed identity, shared by flat and aggregated profiles."""

    puuid: str | None = None
    game_name: str
    tag_line: str
    region: str | None = None
    account_level: int | None = None
    avatar_url: str | None = None
    source: Literal["tracker", "henrik", "riot"] | None = None


class PlayerProfile(PlayerIdentity):
    """Flat player profile used by the existing REST endpoint."""

    rank_name: str | None = None
    rank_tier: str | None = None
    rank_icon_url: str | None = None


class PlayerRank(BaseModel):
    """Unified domain model for a player's rank."""

    tier_name: str
    rank_name: str | None = None
    rank_icon_url: str | None = None
    points: int | None = None
    source: Literal["tracker", "henrik"] | None = None


class PlayerStatsOverview(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    kills: NonNegativeInt
    deaths: NonNegativeInt
    assists: NonNegativeInt
    kd_ratio: float = Field(ge=0)
    win_pct: float = Field(ge=0, le=100)
    headshot_pct: float = Field(ge=0, le=100)
    matches_played: NonNegativeInt | None = None
    damage_per_round: float | None = Field(default=None, ge=0)
    source: Literal["tracker"] = "tracker"


class PlayerMatch(BaseModel):
    """Unified domain model for a player's match."""

    match_id: str
    map_name: str
    mode: str
    timestamp: int | str
    result: str
    kills: int
    deaths: int
    assists: int
    score: int | None = None
    agent_name: str
    provider: Literal["tracker", "henrik", "riot"] | None = None
    provider_score: int | None = None


class PlayerServiceError(Exception):
    """Base exception for player data retrieval."""


class CompletePlayerProfile(BaseModel):
    identity: PlayerIdentity
    rank: PlayerRank | None = None
    stats: PlayerStatsOverview | None = None
    recent_matches: list[PlayerMatch] | None = None
    unavailable_sections: list[str] = Field(default_factory=list)


class PlayerNotFoundError(PlayerServiceError):
    """Every applicable provider confirmed that the resource was not found."""


class PlayerServiceUnavailableError(PlayerServiceError):
    """No configured provider could reliably serve the requested data."""


class PlayerService:
    """Coordinate configured providers with Tracker -> Henrik -> Riot fallback."""

    def __init__(
        self,
        riot_provider: RiotProvider | None = None,
        henrik_provider: HenrikProvider | None = None,
        tracker_provider: TrackerProvider | None = None,
        *,
        disabled_providers: dict[str, str] | None = None,
    ) -> None:
        self.riot = riot_provider
        self.henrik = henrik_provider
        self.tracker = tracker_provider
        self._providers = [
            provider
            for provider in (self.tracker, self.henrik, self.riot)
            if provider is not None
        ]
        self._disabled_providers = {
            name: (disabled_providers or {}).get(name, "disabled")
            for name, provider in (
                ("riot", self.riot),
                ("henrik", self.henrik),
                ("tracker", self.tracker),
            )
            if provider is None
        }

    @staticmethod
    def _record_failure(name: str, error: Exception, errors: list[Exception]) -> None:
        errors.append(error)
        # Provider exceptions may contain response bodies or credentials.
        logger.warning("%s provider failed: %s", name, type(error).__name__)

    @staticmethod
    def _raise_failure(errors: list[Exception], resource: str) -> NoReturn:
        if errors and all(isinstance(error, NotFoundError) for error in errors):
            raise PlayerNotFoundError(f"{resource} not found.")
        if any(
            isinstance(error, (InvalidResponseError, ValidationError))
            for error in errors
        ):
            raise PlayerServiceError(f"{resource} data could not be processed.")
        raise PlayerServiceUnavailableError(
            f"{resource} is unavailable. Configure a supported data provider "
            "or retry when its API is available."
        )

    async def get_complete_player_profile(
        self, game_name: str, tag_line: str
    ) -> PlayerProfile:
        profile = await self.get_player(game_name, tag_line)
        if not profile.rank_name:
            try:
                rank = await self.get_rank(
                    game_name, tag_line, puuid=profile.puuid, region=profile.region
                )
                profile.rank_name = rank.tier_name
                profile.rank_icon_url = rank.rank_icon_url
            except PlayerServiceError:
                logger.debug("Rank enrichment unavailable")
        return profile

    async def get_player(self, game_name: str, tag_line: str) -> PlayerProfile:
        errors: list[Exception] = []
        if self.tracker is not None:
            try:
                data = await self.tracker.get_player_profile(
                    "riot", f"{game_name}#{tag_line}"
                )
                rank_name, rank_icon = None, None
                try:
                    stats = await self.tracker.get_lifetime_stats(
                        "riot", f"{game_name}#{tag_line}"
                    )
                    if stats.rank:
                        rank_name, rank_icon = stats.rank.tier_name, stats.rank.icon_url
                except Exception as error:
                    logger.debug("Tracker enrichment failed: %s", type(error).__name__)
                return PlayerProfile(
                    game_name=game_name,
                    tag_line=tag_line,
                    avatar_url=data.identity.avatar_url,
                    rank_name=rank_name,
                    rank_icon_url=rank_icon,
                    source="tracker",
                )
            except Exception as error:
                self._record_failure("tracker", error, errors)

        if self.henrik is not None:
            try:
                data = await self.henrik.get_account(game_name, tag_line)
                return PlayerProfile(
                    puuid=data.puuid,
                    game_name=data.name,
                    tag_line=data.tag,
                    region=data.region,
                    account_level=data.account_level,
                    source="henrik",
                )
            except Exception as error:
                self._record_failure("henrik", error, errors)

        if self.riot is not None:
            try:
                data = await self.riot.get_player_by_riot_id(game_name, tag_line)
                return PlayerProfile(
                    puuid=data.puuid,
                    game_name=data.game_name,
                    tag_line=data.tag_line,
                    region=data.region,
                    account_level=data.account_level,
                    source="riot",
                )
            except Exception as error:
                self._record_failure("riot", error, errors)

        self._raise_failure(errors, "Player")

    async def get_player_identity(
        self, game_name: str, tag_line: str
    ) -> PlayerIdentity:
        profile = await self.get_player(game_name, tag_line)
        return PlayerIdentity.model_validate(profile.model_dump())

    async def get_stats_overview(
        self, game_name: str, tag_line: str
    ) -> PlayerStatsOverview:
        errors: list[Exception] = []
        if self.tracker is not None:
            try:
                stats = await self.tracker.get_lifetime_stats(
                    "riot", f"{game_name}#{tag_line}"
                )
                return PlayerStatsOverview(
                    kills=stats.kills.value,
                    deaths=stats.deaths.value,
                    assists=stats.assists.value,
                    kd_ratio=stats.kd_ratio.value,
                    win_pct=stats.win_pct.value,
                    headshot_pct=stats.headshot_pct.value,
                    matches_played=(
                        stats.matches_played.value
                        if stats.matches_played is not None
                        else None
                    ),
                    damage_per_round=(
                        stats.damage_per_round.value
                        if stats.damage_per_round is not None
                        else None
                    ),
                )
            except Exception as error:
                self._record_failure("tracker", error, errors)
        self._raise_failure(errors, "Lifetime statistics")

    async def get_player_overview(
        self, game_name: str, tag_line: str, *, limit: int = 10
    ) -> CompletePlayerProfile:
        identity = await self.get_player_identity(game_name, tag_line)
        results = await asyncio.gather(
            self.get_rank(game_name, tag_line, region=identity.region),
            self.get_stats_overview(game_name, tag_line),
            self.get_recent_matches(
                game_name,
                tag_line,
                puuid=identity.puuid,
                region=identity.region,
                limit=limit,
            ),
            return_exceptions=True,
        )
        sections = {}
        unavailable = []
        for name, result in zip(
            ("rank", "stats", "recent_matches"), results, strict=True
        ):
            if isinstance(result, PlayerServiceError):
                unavailable.append(name)
            elif isinstance(result, BaseException):
                raise result
            else:
                sections[name] = result
        return CompletePlayerProfile(
            identity=identity, unavailable_sections=unavailable, **sections
        )

    async def _henrik_region(
        self, game_name: str, tag_line: str, region: str | None
    ) -> str:
        if region:
            return region
        account = await self.henrik.get_account(game_name, tag_line)
        return account.region

    async def get_rank(
        self,
        game_name: str,
        tag_line: str,
        puuid: str | None = None,
        *,
        region: str | None = None,
    ) -> PlayerRank:
        errors: list[Exception] = []
        if self.tracker is not None:
            try:
                stats = await self.tracker.get_lifetime_stats(
                    "riot", f"{game_name}#{tag_line}"
                )
                if stats.rank:
                    return PlayerRank(
                        tier_name=stats.rank.tier_name,
                        rank_icon_url=stats.rank.icon_url,
                        points=stats.rank.points,
                        source="tracker",
                    )
                errors.append(NotFoundError("Rank not present"))
            except Exception as error:
                self._record_failure("tracker", error, errors)

        # Riot's official API does not expose a player's current rank or RR.
        if self.henrik is not None:
            try:
                account_region = await self._henrik_region(game_name, tag_line, region)
                rank = await self.henrik.get_rank(account_region, game_name, tag_line)
                return PlayerRank(
                    tier_name=rank.tier_name,
                    rank_name=rank.tier_name,
                    rank_icon_url=rank.rank_icon_url,
                    points=rank.points,
                    source="henrik",
                )
            except Exception as error:
                self._record_failure("henrik", error, errors)

        self._raise_failure(errors, "Rank")

    async def get_recent_matches(
        self,
        game_name: str,
        tag_line: str,
        puuid: str | None = None,
        *,
        region: str | None = None,
        limit: int = 10,
    ) -> list[PlayerMatch]:
        matches, _ = await self._get_recent_matches_with_source(
            game_name, tag_line, puuid=puuid, region=region, limit=limit
        )
        return matches

    async def _get_recent_matches_with_source(
        self,
        game_name: str,
        tag_line: str,
        puuid: str | None = None,
        *,
        region: str | None = None,
        limit: int = 10,
    ) -> tuple[list[PlayerMatch], str]:
        if not 1 <= limit <= 20:
            raise ValueError("Match limit must be between 1 and 20")
        errors: list[Exception] = []
        if self.tracker is not None:
            try:
                matches = await self.tracker.get_recent_matches(
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
                        provider="tracker",
                        agent_name=m.agent_name,
                    )
                    for m in matches[:limit]
                ], "tracker"
            except Exception as error:
                self._record_failure("tracker", error, errors)

        if self.henrik is not None:
            try:
                account_region = await self._henrik_region(game_name, tag_line, region)
                matches = await self.henrik.get_matches(
                    account_region, game_name, tag_line
                )
                summaries = []
                for match in matches[:limit]:
                    result = "Unknown"
                    if match.stats.team.lower() in ("red", "blue"):
                        own, other = (
                            (match.teams.red, match.teams.blue)
                            if match.stats.team.lower() == "red"
                            else (match.teams.blue, match.teams.red)
                        )
                        if own is not None and other is not None:
                            result = (
                                "Victory"
                                if own > other
                                else "Defeat" if own < other else "Draw"
                            )
                    summaries.append(
                        PlayerMatch(
                            match_id=match.metadata.id,
                            map_name=match.metadata.map.name,
                            mode=match.metadata.mode,
                            timestamp=match.metadata.time,
                            result=result,
                            kills=match.stats.kills,
                            deaths=match.stats.deaths,
                            assists=match.stats.assists,
                            score=None,
                            provider="henrik",
                            provider_score=match.stats.score,
                            agent_name=match.stats.character.name,
                        )
                    )
                return summaries, "henrik"
            except Exception as error:
                self._record_failure("henrik", error, errors)

        if self.riot is not None:
            try:
                if not puuid:
                    player = await self.riot.get_player_by_riot_id(game_name, tag_line)
                    puuid = player.puuid
                matches = await self.riot.get_player_match_history(puuid, limit=limit)
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
                        provider="riot",
                        agent_name=m.player_stats.agent_name,
                    )
                    for m in matches[:limit]
                ], "riot"
            except Exception as error:
                self._record_failure("riot", error, errors)

        self._raise_failure(errors, "Match history")

    async def get_match(self, match_id: str) -> dict[str, Any]:
        errors: list[Exception] = []
        if self.riot is not None:
            try:
                return await self.riot.get_match(match_id)
            except Exception as error:
                self._record_failure("riot", error, errors)
        self._raise_failure(errors, "Match details")

    async def health(self) -> dict[str, Any]:
        results = {
            name: {"status": reason, "message": "Provider is not configured"}
            for name, reason in self._disabled_providers.items()
        }
        checks = await asyncio.gather(
            *(provider.health_check() for provider in self._providers),
            return_exceptions=True,
        )
        statuses = []
        for provider, health in zip(self._providers, checks, strict=True):
            if isinstance(health, Exception):
                results[provider.name] = {
                    "status": ProviderStatus.UNHEALTHY,
                    "message": "Provider health check failed",
                }
            else:
                results[provider.name] = {
                    "status": health.status,
                    "message": health.message,
                    "latency_ms": health.latency_ms,
                }
            statuses.append(results[provider.name]["status"])
        overall = "degraded"
        if statuses:
            if all(status == ProviderStatus.HEALTHY for status in statuses):
                overall = "healthy"
            elif not any(
                status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED)
                for status in statuses
            ):
                overall = "unhealthy"
        return {"status": overall, "providers": results}

    async def close(self) -> None:
        results = await asyncio.gather(
            *(provider.close() for provider in self._providers), return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Provider cleanup failed: %s", type(result).__name__)

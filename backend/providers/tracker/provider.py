import logging
import time
from typing import Any

from backend.providers.base.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from backend.providers.base.models import ProviderHealth, ProviderStatus
from backend.providers.base.provider import BaseProvider

from .client import TrackerHTTPClient
from .config import TrackerConfig
from .exceptions import (
    TrackerAuthenticationError,
    TrackerError,
    TrackerNotFound,
    TrackerRateLimitError,
    TrackerServerError,
)
from .models import (
    AgentStats,
    LifetimeStats,
    MatchHistory,
    MatchSummary,
    Player,
    PlayerIdentity,
    Rank,
    SeasonStats,
    StatValue,
    WeaponStats,
)

logger = logging.getLogger(__name__)

_LIFETIME_STAT_KEYS = (
    "kills",
    "deaths",
    "assists",
    "kdRatio",
    "winPct",
    "headshotPct",
)


class TrackerProvider(BaseProvider):
    """
    Tracker.gg provider for Valorant player data.

    Encapsulates the Tracker.gg v2 API endpoints (player profile, match
    history and lifetime stats) behind typed methods, using a dedicated
    :class:`TrackerHTTPClient` for authenticated, rate-limit-aware HTTP
    communication.
    """

    def __init__(self, config: TrackerConfig) -> None:
        super().__init__(config)
        self.config: TrackerConfig = config

    @property
    def name(self) -> str:
        return "tracker"

    @property
    def client(self) -> TrackerHTTPClient:
        """Lazily initializes and returns the Tracker-specific HTTP client."""
        if self._client is None:
            self._client = TrackerHTTPClient(self.config)
        return self._client  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    async def health_check(self) -> ProviderHealth:
        """Checks whether the Tracker.gg API is reachable."""
        start = time.perf_counter()
        try:
            response = await self.client.get("/", headers=self.client._auth_headers())
            latency_ms = (time.perf_counter() - start) * 1000
            if response.status_code == 200:
                return ProviderHealth(
                    status=ProviderStatus.HEALTHY,
                    message="Tracker.gg API is reachable",
                    latency_ms=latency_ms,
                )
            return ProviderHealth(
                status=ProviderStatus.DEGRADED,
                message=f"Unexpected status: {response.status_code}",
                latency_ms=latency_ms,
            )
        except Exception as error:  # noqa: BLE001 - health must never raise
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                message=str(error),
            )

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------
    async def get_player(self, platform: str, identifier: str) -> PlayerIdentity:
        """
        Fetches the identity information of a player.

        Args:
            platform: Platform slug (e.g. ``"riot"``).
            identifier: Player identifier (e.g. ``"Name#Tag"``).
        """
        payload = await self._get_profile(platform, identifier)
        platform_info = payload.get("data", {}).get("platformInfo", {})
        return PlayerIdentity.model_validate(platform_info)

    async def get_player_profile(self, platform: str, identifier: str) -> Player:
        """
        Fetches the full player profile (identity + profile metadata).
        """
        payload = await self._get_profile(platform, identifier)
        data = payload.get("data", {})
        user_info = data.get("userInfo", {})
        return Player(
            identity=PlayerIdentity.model_validate(data.get("platformInfo", {})),
            country_code=user_info.get("countryCode"),
            is_premium=bool(user_info.get("isPremium", False)),
            is_verified=bool(user_info.get("isVerified", False)),
        )

    async def get_player_stats(self, platform: str, identifier: str) -> LifetimeStats:
        """
        Fetches the aggregated lifetime stats of a player.
        """
        payload = await self._get_profile(platform, identifier)
        segment = self._find_segment(payload, "overview")
        return self._parse_lifetime_stats(segment)

    async def get_lifetime_stats(self, platform: str, identifier: str) -> LifetimeStats:
        """Alias of :meth:`get_player_stats` with the domain naming."""
        return await self.get_player_stats(platform, identifier)

    async def get_season_stats(
        self, platform: str, identifier: str, season_id: str
    ) -> SeasonStats:
        """
        Fetches the stats of a player for a specific season (act).
        """
        try:
            payload = await self.client.get_json(
                f"/profile/{platform}/{identifier}/segments/season",
                params={"seasonId": season_id},
            )
        except Exception as error:
            self._raise_tracker_error(error)
            raise
        segments = payload.get("data", [])
        segment = segments[0] if segments else {}
        metadata = segment.get("metadata", {})
        return SeasonStats(
            season_id=metadata.get("seasonId", season_id),
            season_name=metadata.get("seasonName", "Unknown"),
            stats=self._parse_lifetime_stats(segment),
        )

    async def get_recent_matches(
        self, platform: str, identifier: str
    ) -> list[MatchSummary]:
        """
        Fetches the list of recent matches of a player.
        """
        history = await self.get_match_history(platform, identifier)
        return history.matches

    async def get_match_history(self, platform: str, identifier: str) -> MatchHistory:
        """
        Fetches a page of the match history of a player.
        """
        try:
            payload = await self.client.get_json(
                f"/profile/{platform}/{identifier}/matches"
            )
        except Exception as error:
            self._raise_tracker_error(error)
            raise
        raw_matches = payload.get("data", {}).get("matches", [])
        matches = [self._parse_match(raw) for raw in raw_matches]
        return MatchHistory(matches=matches, total=len(matches))

    async def get_weapon_stats(
        self, platform: str, identifier: str
    ) -> list[WeaponStats]:
        """
        Fetches per-weapon stats of a player.
        """
        payload = await self._get_profile(platform, identifier)
        segments = self._find_segments(payload, "weapon")
        return [self._parse_weapon(segment) for segment in segments]

    async def get_agent_stats(self, platform: str, identifier: str) -> list[AgentStats]:
        """
        Fetches per-agent (character) stats of a player.
        """
        payload = await self._get_profile(platform, identifier)
        segments = self._find_segments(payload, "agent")
        return [self._parse_agent(segment) for segment in segments]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _get_profile(self, platform: str, identifier: str) -> dict[str, Any]:
        """Fetches the raw profile payload, translating errors."""
        try:
            return await self.client.get_json(f"/profile/{platform}/{identifier}")
        except Exception as error:
            self._raise_tracker_error(error)
            raise

    def _find_segment(
        self, payload: dict[str, Any], segment_type: str
    ) -> dict[str, Any]:
        """Returns the first segment of the given type, or an empty dict."""
        segments = self._find_segments(payload, segment_type)
        return segments[0] if segments else {}

    def _find_segments(
        self, payload: dict[str, Any], segment_type: str
    ) -> list[dict[str, Any]]:
        """Returns every segment matching the given type."""
        data = payload.get("data", {})
        segments = data.get("segments", [])
        matching = [s for s in segments if s.get("type") == segment_type]
        if not matching and segment_type == "overview" and segments:
            # Some responses omit the segment type for the overview block.
            return [segments[0]]
        return matching

    def _parse_lifetime_stats(self, segment: dict[str, Any]) -> LifetimeStats:
        """Builds a LifetimeStats model from an overview segment."""
        stats = segment.get("stats", {})
        parsed: dict[str, StatValue] = {}
        for key in _LIFETIME_STAT_KEYS:
            raw = stats.get(key)
            if raw is None:
                raise TrackerError(f"Tracker.gg response is missing the '{key}' stat")
            parsed[key] = StatValue.model_validate(raw)

        optional: dict[str, StatValue | None] = {}
        for key, alias in (
            ("matchesPlayed", "matchesPlayed"),
            ("damagePerRound", "damagePerRound"),
        ):
            raw = stats.get(key)
            optional[alias] = StatValue.model_validate(raw) if raw else None

        rank_raw = stats.get("rank", {}).get("metadata") if stats.get("rank") else None
        rank = (
            Rank(
                tier_name=rank_raw.get("tierName", "Unranked"),
                icon_url=rank_raw.get("iconUrl"),
                points=rank_raw.get("points"),
            )
            if rank_raw
            else None
        )

        return LifetimeStats(
            kills=parsed["kills"],
            deaths=parsed["deaths"],
            assists=parsed["assists"],
            kd_ratio=parsed["kdRatio"],
            win_pct=parsed["winPct"],
            headshot_pct=parsed["headshotPct"],
            matches_played=optional["matchesPlayed"],
            damage_per_round=optional["damagePerRound"],
            rank=rank,
        )

    def _parse_match(self, raw: dict[str, Any]) -> MatchSummary:
        """Builds a MatchSummary model from a raw match payload."""
        attributes = raw.get("attributes", {})
        metadata = raw.get("metadata", {})
        stats = raw.get("stats", {})

        def stat_value(key: str) -> int:
            return int(stats.get(key, {}).get("value", 0))

        return MatchSummary(
            match_id=attributes.get("matchId") or attributes.get("id", "unknown"),
            map_name=metadata.get("mapName", "unknown"),
            agent_name=metadata.get("agentName", "unknown"),
            mode_name=metadata.get("modeName"),
            result=metadata.get("result", "unknown"),
            kills=stat_value("kills"),
            deaths=stat_value("deaths"),
            assists=stat_value("assists"),
            score=stat_value("score"),
            timestamp=metadata.get("timestamp", "unknown"),
        )

    def _parse_weapon(self, segment: dict[str, Any]) -> WeaponStats:
        """Builds a WeaponStats model from a weapon segment."""
        metadata = segment.get("metadata", {})
        stats = segment.get("stats", {})
        return WeaponStats(
            name=metadata.get("name", "unknown"),
            kills=int(stats.get("kills", {}).get("value", 0)),
            headshot_pct=float(stats.get("headshotPct", {}).get("value", 0.0)),
            damage_per_round=float(stats.get("damagePerRound", {}).get("value", 0.0)),
        )

    def _parse_agent(self, segment: dict[str, Any]) -> AgentStats:
        """Builds an AgentStats model from an agent segment."""
        metadata = segment.get("metadata", {})
        stats = segment.get("stats", {})
        return AgentStats(
            name=metadata.get("name", "unknown"),
            matches_played=int(stats.get("matchesPlayed", {}).get("value", 0)),
            win_rate=float(stats.get("winRate", {}).get("value", 0.0)),
            kd_ratio=float(stats.get("kdRatio", {}).get("value", 0.0)),
            playtime_hours=(
                float(stats["playtime"]["value"]) / 3600.0
                if stats.get("playtime", {}).get("value")
                else None
            ),
        )

    def _raise_tracker_error(self, error: Exception) -> None:
        """Translates base provider errors into Tracker-specific exceptions."""
        if isinstance(
            error,
            TrackerAuthenticationError
            | TrackerRateLimitError
            | TrackerNotFound
            | TrackerServerError,
        ):
            raise error
        if isinstance(error, AuthenticationError):
            raise TrackerAuthenticationError(
                str(error), error.status_code, error.response_body
            ) from error
        if isinstance(error, NotFoundError):
            raise TrackerNotFound(
                str(error), error.status_code, error.response_body
            ) from error
        if isinstance(error, RateLimitError):
            raise TrackerRateLimitError(
                str(error),
                status_code=error.status_code,
                response_body=error.response_body,
                retry_after=getattr(error, "retry_after", None),
            ) from error
        if isinstance(error, ServerError):
            raise TrackerServerError(
                str(error), error.status_code, error.response_body
            ) from error
        if not isinstance(error, TrackerError):
            raise TrackerError(
                f"An unexpected error occurred in TrackerProvider: {error}"
            ) from error

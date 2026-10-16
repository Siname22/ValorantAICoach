"""Pure domain entities and models representing player and match concepts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt


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
    """Flat player profile used by the player domain and REST endpoints."""

    rank_name: str | None = None
    rank_tier: str | None = None
    rank_icon_url: str | None = None


class PlayerRank(BaseModel):
    """Unified domain model for a player's competitive rank."""

    tier_name: str
    rank_name: str | None = None
    rank_icon_url: str | None = None
    points: int | None = None
    source: Literal["tracker", "henrik"] | None = None


class PlayerStatsOverview(BaseModel):
    """Overview of lifetime player performance statistics."""

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
    """Unified domain model for an individual player match."""

    match_id: str
    map_name: str
    mode: str
    timestamp: int | str
    result: str
    kills: int
    deaths: int
    assists: int
    score: int | None = None
    round_score: str | None = None
    agent_name: str
    provider: Literal["tracker", "henrik", "riot", "vision"] | None = None
    provider_score: int | None = None


class CompletePlayerProfile(BaseModel):
    """Aggregated player profile across identity, rank, stats, and matches."""

    identity: PlayerIdentity
    rank: PlayerRank | None = None
    stats: PlayerStatsOverview | None = None
    recent_matches: list[PlayerMatch] | None = None
    unavailable_sections: list[str] = Field(default_factory=list)


class PlayerServiceError(Exception):
    """Base exception for player domain data retrieval."""


class PlayerNotFoundError(PlayerServiceError):
    """Every applicable provider confirmed that the resource was not found."""


class PlayerServiceUnavailableError(PlayerServiceError):
    """No configured provider could reliably serve the requested data."""

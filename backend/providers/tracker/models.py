from typing import Any

from pydantic import BaseModel, Field


class PlayerIdentity(BaseModel):
    """Model for player identity information."""

    platform_id: str = Field(..., alias="platformId")
    platform_user_handle: str = Field(..., alias="platformUserHandle")
    platform_user_identifier: str = Field(..., alias="platformUserIdentifier")
    avatar_url: str | None = Field(None, alias="avatarUrl")


class StatValue(BaseModel):
    """Model for a single stat value from Tracker.gg."""

    value: float
    display_value: str = Field(..., alias="displayValue")
    percentile: float | None = None


class CompetitiveStats(BaseModel):
    """Model for competitive specific stats."""

    rank: str
    rank_url: str = Field(..., alias="rankUrl")
    matches_played: int = Field(..., alias="matchesPlayed")
    win_rate: float = Field(..., alias="winRate")


class WeaponStats(BaseModel):
    """Model for weapon specific stats."""

    name: str
    kills: int
    headshot_pct: float = Field(..., alias="headshotPct")
    damage_per_round: float = Field(..., alias="damagePerRound")


class MapStats(BaseModel):
    """Model for map specific stats."""

    name: str
    matches_played: int = Field(..., alias="matchesPlayed")
    win_rate: float = Field(..., alias="winRate")


class PlayerStats(BaseModel):
    """Model for aggregated player stats."""

    kills: StatValue
    deaths: StatValue
    assists: StatValue
    kd_ratio: StatValue = Field(..., alias="kdRatio")
    win_pct: StatValue = Field(..., alias="winPct")
    headshot_pct: StatValue = Field(..., alias="headshotPct")


class MatchSummary(BaseModel):
    """Model for a summary of a single match."""

    match_id: str = Field(..., alias="matchId")
    map_name: str = Field(..., alias="mapName")
    agent_name: str = Field(..., alias="agentName")
    result: str  # "Win", "Loss", "Draw"
    kills: int
    deaths: int
    assists: int
    score: int
    timestamp: str


class TrackerResponse(BaseModel):
    """Generic wrapper for Tracker.gg API responses."""

    data: dict[str, Any]
    status: str = "success"

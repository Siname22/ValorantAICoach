from typing import Any

from pydantic import BaseModel, Field


class PlayerProfileResponse(BaseModel):
    """Unified player profile information."""

    puuid: str | None = Field(None, description="Riot's unique player identifier")
    game_name: str = Field(..., description="Player's in-game name", example="Player")
    tag_line: str = Field(..., description="Player's tag line", example="NA1")
    region: str | None = Field(None, description="Account region (e.g., na, eu, latam)")
    account_level: int | None = Field(None, description="Player's account level")
    avatar_url: str | None = Field(None, description="URL to the player's avatar image")
    rank_name: str | None = Field(None, description="Current rank tier name")
    rank_tier: str | None = Field(None, description="Internal rank tier value")
    rank_icon_url: str | None = Field(None, description="URL to the rank icon image")


class PlayerRankResponse(BaseModel):
    """Player's competitive rank details."""

    tier_name: str = Field(
        ..., description="Name of the rank tier", example="Diamond 1"
    )
    rank_name: str | None = Field(None, description="Detailed rank name")
    rank_icon_url: str | None = Field(None, description="URL to the rank icon image")
    points: int | None = Field(None, description="Ranked rating points")


class PlayerMatchResponse(BaseModel):
    """Summary of a single player match."""

    match_id: str = Field(..., description="Unique match identifier")
    map_name: str = Field(..., description="Name of the map played")
    mode: str = Field(..., description="Game mode (e.g., Competitive)")
    timestamp: Any = Field(..., description="When the match was played")
    result: str = Field(..., description="Match outcome (e.g., Victory, Defeat)")
    kills: int = Field(..., description="Number of kills")
    deaths: int = Field(..., description="Number of deaths")
    assists: int = Field(..., description="Number of assists")
    score: int = Field(..., description="Total match score")
    agent_name: str = Field(..., description="Agent played in this match")


class PlayerMatchesResponse(BaseModel):
    """List of recent matches for a player."""

    matches: list[PlayerMatchResponse] = Field(
        ..., description="List of recent match summaries"
    )
    count: int = Field(..., description="Total number of matches returned")


class HealthResponse(BaseModel):
    """Application health status."""

    status: str = Field(..., description="Overall health status", example="ok")
    version: str = Field(..., description="Application version", example="0.3.0")
    providers: dict[str, str] | None = Field(
        None, description="Status of individual data providers"
    )

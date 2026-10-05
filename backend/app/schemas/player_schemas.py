from typing import Literal

from pydantic import BaseModel, Field


class PlayerProfileResponse(BaseModel):
    """Unified player profile information."""

    puuid: str | None = Field(None, description="Riot's unique player identifier")
    game_name: str = Field(
        ..., description="Player's in-game name", examples=["Player"]
    )
    tag_line: str = Field(..., description="Player's tag line", examples=["EU1"])
    region: str | None = Field(None, description="Account region (e.g., na, eu, latam)")
    account_level: int | None = Field(None, description="Player's account level")
    avatar_url: str | None = Field(None, description="URL to the player's avatar image")
    source: Literal["tracker", "henrik", "riot"] | None = None
    rank_name: str | None = Field(None, description="Current rank tier name")
    rank_tier: str | None = Field(None, description="Internal rank tier value")
    rank_icon_url: str | None = Field(None, description="URL to the rank icon image")


class PlayerRankResponse(BaseModel):
    """Player's competitive rank details."""

    tier_name: str = Field(
        ..., description="Name of the rank tier", examples=["Diamond 1"]
    )
    rank_name: str | None = Field(None, description="Detailed rank name")
    rank_icon_url: str | None = Field(None, description="URL to the rank icon image")
    points: int | None = Field(None, description="Ranked rating points")
    source: Literal["tracker", "henrik"] | None = None


class PlayerMatchResponse(BaseModel):
    """Summary of a single player match."""

    match_id: str = Field(..., description="Unique match identifier")
    map_name: str = Field(..., description="Name of the map played")
    mode: str = Field(..., description="Game mode (e.g., Competitive)")
    timestamp: int | str = Field(
        ..., description="Provider timestamp: Riot milliseconds or ISO date"
    )
    result: str = Field(..., description="Match outcome (e.g., Victory, Defeat)")
    kills: int = Field(..., description="Number of kills")
    deaths: int = Field(..., description="Number of deaths")
    assists: int = Field(..., description="Number of assists")
    score: int | None = Field(
        None, description="Total match score, when its meaning is confirmed"
    )
    agent_name: str = Field(..., description="Agent played in this match")
    provider: Literal["tracker", "henrik", "riot"] | None = Field(
        None, description="Source of the match summary"
    )
    provider_score: int | None = Field(
        None,
        description="Original provider score when it cannot be treated as total score",
    )


class PlayerMatchesResponse(BaseModel):
    """List of recent matches for a player."""

    matches: list[PlayerMatchResponse] = Field(
        ..., description="List of recent match summaries"
    )
    count: int = Field(..., description="Total number of matches returned")


class HealthResponse(BaseModel):
    """Application health status."""

    status: str = Field(..., description="Overall health status", examples=["ok"])
    version: str = Field(..., description="Application version", examples=["0.4.0"])
    providers: dict[str, str] | None = Field(
        None, description="Status of individual data providers"
    )

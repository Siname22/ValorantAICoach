from typing import Any

from pydantic import BaseModel, Field


class Player(BaseModel):
    """Model for a Valorant player from Riot API."""

    puuid: str
    game_name: str = Field(..., alias="gameName")
    tag_line: str = Field(..., alias="tagLine")
    region: str
    account_level: int | None = Field(None, alias="accountLevel")


class Rank(BaseModel):
    """Model for a player's competitive rank."""

    tier: str
    rank: str
    ranked_rating: int | None = Field(None, alias="rankedRating")


class MatchPlayerStats(BaseModel):
    """Model for player-specific stats within a match."""

    kills: int
    deaths: int
    assists: int
    score: int
    acs: float | None = Field(None, alias="averageCombatScore")
    agent_name: str = Field(..., alias="character")


class Match(BaseModel):
    """Model for a Valorant match summary."""

    match_id: str = Field(..., alias="matchId")
    map_id: str = Field(..., alias="mapId")
    game_mode: str = Field(..., alias="gameMode")
    game_start_time: int = Field(..., alias="gameStartTimeMillis")
    # Simplified result for now, could be more detailed later
    result: str  # e.g., "Victory", "Defeat"
    player_stats: MatchPlayerStats  # Stats for the specific player in this match


class RiotAPIResponse(BaseModel):
    """Generic wrapper for Riot API responses."""

    data: Any  # Use Any for now as Riot API responses are highly varied

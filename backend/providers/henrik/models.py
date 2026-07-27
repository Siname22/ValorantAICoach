from typing import Any

from pydantic import BaseModel, Field


class HenrikPlayer(BaseModel):
    """Model for a Valorant player from HenrikDev API."""

    puuid: str
    name: str
    tag: str
    region: str
    account_level: int = Field(..., alias="account_level")


class HenrikMatchMetadata(BaseModel):
    """Metadata for a match from HenrikDev."""

    map: str
    game_version: str = Field(..., alias="game_version")
    game_length: int = Field(..., alias="game_length")
    game_start: int = Field(..., alias="game_start")
    mode: str


class HenrikMatch(BaseModel):
    """Model for a Valorant match from HenrikDev."""

    metadata: HenrikMatchMetadata
    players: list[Any]  # Placeholder for detailed player data in match
    teams: Any  # Placeholder for team data
    rounds: Any  # Placeholder for round data


class HenrikResponse(BaseModel):
    """Generic wrapper for HenrikDev API responses."""

    status: int
    data: Any

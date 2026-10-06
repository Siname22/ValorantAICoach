from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator


class HenrikPlayer(BaseModel):
    """Model for a Valorant player from HenrikDev API."""

    puuid: str
    name: str
    tag: str
    region: str
    account_level: int


class HenrikMap(BaseModel):
    id: str
    name: str


class HenrikCharacter(BaseModel):
    id: str
    name: str


class HenrikMatchMetadata(BaseModel):
    """Metadata for a compact lifetime match summary."""

    id: str
    map: HenrikMap
    mode: str
    time: str = Field(validation_alias=AliasChoices("time", "started_at"))

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None:
            raise ValueError("Match time must include a timezone")
        return value


class HenrikMatchStats(BaseModel):
    kills: int = Field(ge=0)
    deaths: int = Field(ge=0)
    assists: int = Field(ge=0)
    score: int
    character: HenrikCharacter
    team: str


class HenrikMatchTeams(BaseModel):
    red: int = Field(ge=0)
    blue: int = Field(ge=0)


class HenrikMatch(BaseModel):
    """Compact per-player summary, not a full match-detail response."""

    metadata: HenrikMatchMetadata = Field(
        validation_alias=AliasChoices("metadata", "meta")
    )
    stats: HenrikMatchStats
    teams: HenrikMatchTeams


class HenrikRank(BaseModel):
    tier_name: str
    points: int
    rank_icon_url: str | None = None


class HenrikMMRImages(BaseModel):
    small: str | None = None


class HenrikMMRCurrentData(BaseModel):
    currenttierpatched: str
    ranking_in_tier: int
    images: HenrikMMRImages | None = None


class HenrikMMRData(BaseModel):
    current_data: HenrikMMRCurrentData


class HenrikResponse[T](BaseModel):
    """Generic wrapper for HenrikDev API responses."""

    status: Literal[200]
    data: T

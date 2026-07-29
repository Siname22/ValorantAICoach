from typing import Any

from pydantic import BaseModel


class PlayerProfileResponse(BaseModel):
    puuid: str | None = None
    game_name: str
    tag_line: str
    region: str | None = None
    account_level: int | None = None
    avatar_url: str | None = None
    rank_name: str | None = None
    rank_tier: str | None = None
    rank_icon_url: str | None = None


class PlayerRankResponse(BaseModel):
    tier_name: str
    rank_name: str | None = None
    rank_icon_url: str | None = None
    points: int | None = None


class PlayerMatchResponse(BaseModel):
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


class PlayerMatchesResponse(BaseModel):
    matches: list[PlayerMatchResponse]
    count: int

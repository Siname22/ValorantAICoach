from pydantic import BaseModel, ConfigDict, Field

_ALIAS_CONFIG = ConfigDict(populate_by_name=True)


class StatValue(BaseModel):
    """A single stat value as returned by Tracker.gg (value + display)."""

    model_config = _ALIAS_CONFIG

    value: float
    display_value: str = Field(..., alias="displayValue")
    display_name: str | None = Field(None, alias="displayName")
    percentile: float | None = None


class Rank(BaseModel):
    """Competitive rank information for a player."""

    model_config = _ALIAS_CONFIG

    tier_name: str = Field(..., alias="tierName")
    icon_url: str | None = Field(None, alias="iconUrl")
    points: int | None = None


class PlayerIdentity(BaseModel):
    """Identity information of a player on a given platform."""

    model_config = _ALIAS_CONFIG

    platform_id: str = Field(..., alias="platformId")
    platform_user_handle: str = Field(..., alias="platformUserHandle")
    platform_user_identifier: str = Field(..., alias="platformUserIdentifier")
    avatar_url: str | None = Field(None, alias="avatarUrl")


class Player(BaseModel):
    """A player profile: identity plus profile-level metadata."""

    model_config = _ALIAS_CONFIG

    identity: PlayerIdentity
    country_code: str | None = Field(None, alias="countryCode")
    is_premium: bool = Field(False, alias="isPremium")
    is_verified: bool = Field(False, alias="isVerified")


class LifetimeStats(BaseModel):
    """Aggregated lifetime stats for a player."""

    model_config = _ALIAS_CONFIG

    kills: StatValue
    deaths: StatValue
    assists: StatValue
    kd_ratio: StatValue = Field(..., alias="kdRatio")
    win_pct: StatValue = Field(..., alias="winPct")
    headshot_pct: StatValue = Field(..., alias="headshotPct")
    matches_played: StatValue | None = Field(None, alias="matchesPlayed")
    damage_per_round: StatValue | None = Field(None, alias="damagePerRound")
    rank: Rank | None = None


# Backwards-compatible alias kept for existing imports and tests.
PlayerStats = LifetimeStats


class SeasonStats(BaseModel):
    """Stats for a player within a specific competitive season (act)."""

    model_config = _ALIAS_CONFIG

    season_id: str = Field(..., alias="seasonId")
    season_name: str = Field(..., alias="seasonName")
    stats: LifetimeStats


class WeaponStats(BaseModel):
    """Per-weapon performance stats."""

    model_config = _ALIAS_CONFIG

    name: str
    kills: int
    headshot_pct: float = Field(..., alias="headshotPct")
    damage_per_round: float = Field(..., alias="damagePerRound")


class AgentStats(BaseModel):
    """Per-agent (character) performance stats."""

    model_config = _ALIAS_CONFIG

    name: str
    matches_played: int = Field(..., alias="matchesPlayed")
    win_rate: float = Field(..., alias="winRate")
    kd_ratio: float = Field(..., alias="kdRatio")
    playtime_hours: float | None = Field(None, alias="playtimeHours")


class MapStats(BaseModel):
    """Per-map performance stats."""

    model_config = _ALIAS_CONFIG

    name: str
    matches_played: int = Field(..., alias="matchesPlayed")
    win_rate: float = Field(..., alias="winRate")


class CompetitiveStats(BaseModel):
    """Competitive playlist summary stats."""

    model_config = _ALIAS_CONFIG

    rank: str
    rank_url: str = Field(..., alias="rankUrl")
    matches_played: int = Field(..., alias="matchesPlayed")
    win_rate: float = Field(..., alias="winRate")


class MatchSummary(BaseModel):
    """Summary of a single played match."""

    model_config = _ALIAS_CONFIG

    match_id: str = Field(..., alias="matchId")
    map_name: str = Field(..., alias="mapName")
    agent_name: str = Field(..., alias="agentName")
    mode_name: str | None = Field(None, alias="modeName")
    result: str
    kills: int
    deaths: int
    assists: int
    score: int
    timestamp: str


class MatchHistory(BaseModel):
    """A page of a player's match history."""

    model_config = _ALIAS_CONFIG

    matches: list[MatchSummary]
    total: int

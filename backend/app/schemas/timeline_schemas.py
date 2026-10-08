"""Schemas for round-by-round replay timeline analysis and tactical metrics."""

from typing import Literal

from pydantic import BaseModel, Field

EconomyCategory = Literal["eco", "semi-eco", "semi-buy", "full-buy", "bonus"]
WinType = Literal[
    "Eliminated",
    "Bomb defused",
    "Bomb detonated",
    "Time out",
    "Surrender",
    "Unknown",
]
Side = Literal["attack", "defense", "unknown"]


class PlayerRoundEconomy(BaseModel):
    """Economic state of a player in a specific round."""

    puuid: str | None = None
    player_name: str | None = None
    loadout_value: int = Field(ge=0, default=0)
    weapon: str | None = None
    armor: str | None = None
    remaining_credits: int = Field(ge=0, default=0)
    category: EconomyCategory = "eco"


class KillEvent(BaseModel):
    """Chronological kill event in a round."""

    kill_index: int = Field(ge=0)
    round_time_millis: int = Field(ge=0)
    game_time_millis: int | None = None
    killer_puuid: str | None = None
    killer_name: str
    killer_team: str  # e.g., "Red" or "Blue"
    victim_puuid: str | None = None
    victim_name: str
    victim_team: str
    assistants: list[str] = Field(default_factory=list)
    weapon: str | None = None
    is_headshot: bool = False
    is_trade_kill: bool = False
    traded_killer_name: str | None = None
    trade_window_millis: int | None = None


class SpikeEvent(BaseModel):
    """Spike plant or defusal event in a round."""

    event_type: Literal["plant", "defuse"]
    round_time_millis: int = Field(ge=0)
    site: str | None = None  # "A", "B", "C"
    player_puuid: str | None = None
    player_name: str | None = None
    player_team: str | None = None
    success: bool = True


class RoundTimeline(BaseModel):
    """Structured breakdown of events and economy for a single round."""

    round_num: int = Field(ge=1)
    winning_team: str  # "Red" or "Blue"
    winning_side: Side
    win_type: WinType
    friendly_won: bool | None = None
    ceremony: str | None = None
    is_clutch: bool = False
    clutch_player: str | None = None
    clutch_opponents: int = 0
    clutch_won: bool = False
    is_thrifty: bool = False
    is_anti_eco_loss: bool = False
    first_blood: KillEvent | None = None
    first_death: KillEvent | None = None
    spike_plant: SpikeEvent | None = None
    spike_defuse: SpikeEvent | None = None
    retake_situation: bool = False
    retake_successful: bool = False
    kills: list[KillEvent] = Field(default_factory=list)
    player_economies: dict[str, PlayerRoundEconomy] = Field(default_factory=dict)
    team_loadouts: dict[str, int] = Field(default_factory=dict)
    friendly_score_after: int = 0
    enemy_score_after: int = 0


class TimelineTacticalSummary(BaseModel):
    """Aggregated tactical metrics derived from the match timeline."""

    total_rounds: int = Field(ge=0)
    attack_rounds_won: int = Field(ge=0, default=0)
    attack_rounds_total: int = Field(ge=0, default=0)
    attack_win_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    defense_rounds_won: int = Field(ge=0, default=0)
    defense_rounds_total: int = Field(ge=0, default=0)
    defense_win_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    first_bloods_count: int = Field(ge=0, default=0)
    first_deaths_count: int = Field(ge=0, default=0)
    first_blood_conversion_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    trade_kills_count: int = Field(ge=0, default=0)
    trade_efficiency_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    clutch_attempts: int = Field(ge=0, default=0)
    clutch_wins: int = Field(ge=0, default=0)
    clutch_win_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    anti_eco_losses: int = Field(ge=0, default=0)
    thrifty_wins: int = Field(ge=0, default=0)
    retake_attempts: int = Field(ge=0, default=0)
    retake_successes: int = Field(ge=0, default=0)
    retake_success_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    tactical_takeaways: list[str] = Field(default_factory=list)


class MatchTimelineResponse(BaseModel):
    """Full round-by-round timeline and tactical analysis of a match."""

    match_id: str
    map_name: str
    game_mode: str = "Standard"
    friendly_team: str | None = None
    rounds: list[RoundTimeline] = Field(default_factory=list)
    summary: TimelineTacticalSummary


class PlayerTimelineAnalyticsResponse(BaseModel):
    """Cross-match timeline analysis identifying tactical trends and leaks."""

    game_name: str
    tag_line: str
    matches_analyzed: int = Field(ge=0)
    total_rounds_analyzed: int = Field(ge=0)
    overall_attack_win_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    overall_defense_win_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    overall_trade_efficiency: float = Field(ge=0.0, le=100.0, default=0.0)
    overall_clutch_win_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    clutches_won_breakdown: dict[str, int] = Field(default_factory=dict)
    anti_eco_losses_total: int = Field(ge=0, default=0)
    retake_success_rate: float = Field(ge=0.0, le=100.0, default=0.0)
    identified_tactical_leaks: list[str] = Field(default_factory=list)

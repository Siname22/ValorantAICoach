from typing import Any, Literal

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


class CoachingReportResponse(BaseModel):
    """Grounded AI coaching report for a player."""

    id: str = Field(..., description="Unique report identifier")
    player_id: str | None = Field(None, description="Internal player identifier")
    schema_version: int = Field(1, description="Schema format version")
    provider: str = Field("orchestrator", description="Generating agent or provider")
    payload: dict[str, Any] = Field(..., description="Full structured coaching plan")
    evidence: list[dict[str, Any]] = Field(
        default_factory=list, description="Grounding evidence"
    )
    created_at: str | None = Field(None, description="Report generation timestamp")


class CoachingReportsListResponse(BaseModel):
    """List of historical coaching reports for a player."""

    reports: list[CoachingReportResponse] = Field(
        ..., description="List of saved coaching reports"
    )
    count: int = Field(..., description="Total reports returned")


class ReadinessResponse(BaseModel):
    """Application readiness status."""

    status: str = Field(
        ...,
        description="Readiness status (ready, degraded, unhealthy)",
        examples=["ready"],
    )
    database: str = Field(
        ...,
        description="Database connection status",
        examples=["connected"],
    )
    providers_configured: int = Field(
        ...,
        description="Number of configured upstream providers",
        examples=[3],
    )


class CachePruneResponse(BaseModel):
    """Result of cache pruning operation."""

    pruned_count: int = Field(
        ...,
        description="Number of expired cache records removed",
        examples=[0],
    )


class MetricDataPoint(BaseModel):
    """Single historical metric measurement."""

    timestamp: int | str = Field(..., description="Match timestamp")
    value: float = Field(..., description="Metric value at this point in time")


class PlayerProgressionMetric(BaseModel):
    """Trajectory tracking for a key performance indicator."""

    name: str = Field(..., description="Metric label")
    current: float = Field(..., description="Current value from recent matches")
    historical_avg: float = Field(
        ..., description="Historical average across all analyzed matches"
    )
    trend: Literal["improving", "declining", "stable"] = Field(
        ..., description="Directional trend"
    )
    change_pct: float = Field(
        ..., description="Percentage change from baseline to recent"
    )
    data_points: list[MetricDataPoint] = Field(
        default_factory=list, description="Historical data points for plotting"
    )


class AgentPerformanceSummary(BaseModel):
    """Aggregated performance for a specific agent."""

    matches_played: int = Field(..., description="Matches played with this agent")
    win_pct: float = Field(..., description="Win rate percentage")
    avg_kd: float = Field(..., description="Average K/D ratio")


class PlayerProgressionResponse(BaseModel):
    """Long-term trajectory and progression analysis for a player."""

    game_name: str = Field(..., description="Player in-game name")
    tag_line: str = Field(..., description="Player tag line")
    total_matches_analyzed: int = Field(..., description="Number of matches analyzed")
    total_reports_generated: int = Field(
        ..., description="Historical coaching reports count"
    )
    kd_metric: PlayerProgressionMetric
    headshot_metric: PlayerProgressionMetric
    win_rate_metric: PlayerProgressionMetric
    resolved_focus_areas: list[str] = Field(
        default_factory=list,
        description="Weaknesses from previous reports that show measurable improvement",
    )
    active_focus_areas: list[str] = Field(
        default_factory=list,
        description="Current areas requiring coaching intervention",
    )
    agent_trends: dict[str, AgentPerformanceSummary] = Field(
        default_factory=dict,
        description="Per-agent performance breakdowns",
    )
    trajectory_narrative: str = Field(
        ..., description="Executive summary of the player's long-term evolution"
    )


class PlayerSyncResponse(BaseModel):
    """Result of an on-demand or scheduled coaching sync."""

    synced: bool = Field(..., description="Whether sync completed successfully")
    game_name: str = Field(..., description="Player name")
    tag_line: str = Field(..., description="Player tag")
    new_report_generated: bool = Field(
        ..., description="Whether a new coaching report was generated"
    )
    report_id: str | None = Field(None, description="Generated report ID if applicable")
    matches_synced: int = Field(..., description="Number of matches refreshed")
    synced_at: str = Field(..., description="Timestamp of sync in ISO 8601 UTC format")

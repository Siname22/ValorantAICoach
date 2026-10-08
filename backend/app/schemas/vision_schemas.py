from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScoreboardPlayerRow(BaseModel):
    """Extracted row representing a player in the match scoreboard."""

    player_name: str = Field(..., description="Player in-game display name")
    tag_line: str | None = Field(None, description="Tagline if visible or extracted")
    agent: str = Field(..., description="Agent name played")
    team: Literal["friendly", "enemy", "blue", "red", "unknown"] = Field(
        "unknown", description="Team assignment on scoreboard"
    )
    score: int = Field(0, description="Average Combat Score (ACS) or total score")
    kills: int = Field(..., description="Kills count")
    deaths: int = Field(..., description="Deaths count")
    assists: int = Field(..., description="Assists count")
    damage_per_round: float | None = Field(
        None, description="Average damage per round (ADR)"
    )
    first_bloods: int | None = Field(None, description="First bloods count")
    plants: int | None = Field(None, description="Spike plants count")
    defuses: int | None = Field(None, description="Spike defuses count")


class ScoreboardIngestRequest(BaseModel):
    """Payload to analyze a match scoreboard image."""

    image_base64: str = Field(
        ...,
        description="Base64-encoded image string or data URL (PNG, JPEG, WebP)",
    )
    game_name: str | None = Field(
        None, description="Optional target player name to highlight"
    )
    tag_line: str | None = Field(
        None, description="Optional target player tag to highlight"
    )
    save_to_history: bool = Field(
        True,
        description="Whether to persist the extracted match into database history",
    )


class ScoreboardAnalysisResponse(BaseModel):
    """Structured extraction of a Valorant match scoreboard."""

    match_id: str = Field(..., description="Generated or synthetic match ID")
    map_name: str = Field(..., description="Map played (e.g., Ascent, Bind, Haven)")
    game_mode: str = Field("Competitive", description="Game mode played")
    result: Literal["Victory", "Defeat", "Draw", "Unknown"] = Field(
        ..., description="Match outcome"
    )
    rounds_won: int = Field(..., description="Rounds won by target player team")
    rounds_lost: int = Field(..., description="Rounds lost by target player team")
    target_player_stats: ScoreboardPlayerRow | None = Field(
        None, description="Extracted stats for the target player"
    )
    scoreboard_rows: list[ScoreboardPlayerRow] = Field(
        default_factory=list, description="All parsed player rows on the scoreboard"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Extraction confidence score"
    )
    extractor_engine: str = Field(
        ..., description="Engine used (e.g., gemini-multimodal, heuristic-ocr)"
    )
    tactical_takeaways: list[str] = Field(
        default_factory=list,
        description="Quick tactical takeaways derived from the scoreboard",
    )
    persisted_as_match: bool = Field(
        False, description="Whether the match was saved into player match history"
    )

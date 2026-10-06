from typing import Any

from pydantic import Field

from agents.shared.models import AgentModel


class MatchAnalystInput(AgentModel):
    """Input data for the Match Analyst agent."""

    match_id: str
    player_id: str
    match_data: dict[str, Any] | None = None
    player_stats: dict[str, Any] | None = None


class MatchAnalystOutput(AgentModel):
    """Output data from the Match Analyst agent with grounded evidence and diagnosis."""

    analysis_summary: str
    metrics: dict[str, Any]
    diagnosis: str | None = None
    main_mistake: str | None = None
    practical_change: str | None = None
    drill: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)

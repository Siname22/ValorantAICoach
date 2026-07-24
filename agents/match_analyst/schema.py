from typing import Any

from agents.shared.models import AgentModel


class MatchAnalystInput(AgentModel):
    """Input data for the Match Analyst agent."""

    match_id: str
    player_id: str


class MatchAnalystOutput(AgentModel):
    """Output data from the Match Analyst agent."""

    analysis_summary: str
    metrics: dict[str, Any]

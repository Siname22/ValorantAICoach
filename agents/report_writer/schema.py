from typing import Any

from agents.shared.models import AgentModel


class ReportWriterInput(AgentModel):
    """Input for synthesizing all specialist outputs into a final report."""

    player_name: str
    player_tag: str
    rank: str | None = None
    match_analysis: dict[str, Any] | None = None
    economy_analysis: dict[str, Any] | None = None
    role_analysis: dict[str, Any] | None = None


class ReportWriterOutput(AgentModel):
    """Structured comprehensive coaching report ready for persistence."""

    report_id: str
    title: str
    executive_summary: str
    key_strengths: list[str]
    critical_flaws: list[str]
    training_plan: list[str]
    evidence: list[dict[str, Any]]

from typing import Any

from agents.shared.models import AgentModel


class RoleCoachInput(AgentModel):
    """Input parameters for the Role Coach Agent."""

    agent_name: str
    role: str | None = None
    match_data: dict[str, Any]
    player_stats: dict[str, Any] | None = None


class RoleCoachOutput(AgentModel):
    """Structured coaching output for agent role execution."""

    agent_name: str
    role: str
    role_score: float
    main_mistake: str
    tactical_adaptation: str
    drill: str
    evidence: list[dict[str, Any]]

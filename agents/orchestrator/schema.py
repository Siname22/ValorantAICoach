from typing import Any

from agents.shared.models import AgentModel


class OrchestratorInput(AgentModel):
    """Input for the orchestrator coordinator."""

    user_message: str = ""
    game_name: str | None = None
    tag_line: str | None = None
    rank: str | None = None
    matches: list[dict[str, Any]] = []
    player_stats: dict[str, Any] | None = None


class OrchestratorOutput(AgentModel):
    """Output from the orchestrator coordinator."""

    requested_agents: list[str]
    reasoning: str
    report: dict[str, Any] | None = None

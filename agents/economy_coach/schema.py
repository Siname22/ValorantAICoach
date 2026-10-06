from typing import Any

from agents.shared.models import AgentModel


class EconomyCoachInput(AgentModel):
    """Input parameters for the Economy Coach Agent."""

    match_data: dict[str, Any]
    player_stats: dict[str, Any] | None = None


class EconomyCoachOutput(AgentModel):
    """Structured coaching output for economic performance."""

    economy_rating: float
    buy_discipline_score: float
    main_mistake: str
    practical_rule: str
    drill: str
    evidence: list[dict[str, Any]]

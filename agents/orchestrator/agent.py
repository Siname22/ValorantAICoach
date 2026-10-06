from typing import Any

from agents.economy_coach.agent import EconomyCoachAgent
from agents.economy_coach.schema import EconomyCoachInput
from agents.match_analyst.agent import MatchAnalystAgent
from agents.match_analyst.schema import MatchAnalystInput
from agents.report_writer.agent import ReportWriterAgent
from agents.report_writer.schema import ReportWriterInput
from agents.role_coach.agent import RoleCoachAgent
from agents.role_coach.schema import RoleCoachInput
from agents.shared.base_agent import BaseAgent
from agents.shared.context import AgentContext
from agents.shared.registry import AgentRegistry

from .schema import OrchestratorInput, OrchestratorOutput


class OrchestratorAgent(BaseAgent[OrchestratorInput, OrchestratorOutput]):
    """Main orchestrator agent that delegates tasks to specialized agents."""

    def __init__(self) -> None:
        super().__init__(name="AI Orchestrator")

    async def run(
        self, data: OrchestratorInput, context: AgentContext
    ) -> OrchestratorOutput:
        available_agents = AgentRegistry.list()
        requested = [name for name in available_agents if name != "orchestrator"]

        if data.game_name or data.matches:
            # Multi-agent coordination flow
            primary_match: dict[str, Any] = data.matches[0] if data.matches else {}
            player_stats = data.player_stats or {}
            agent_name = primary_match.get("agent_name", "Unknown")

            match_analyst = MatchAnalystAgent()
            economy_coach = EconomyCoachAgent()
            role_coach = RoleCoachAgent()
            report_writer = ReportWriterAgent()

            # Execute specialist analysis
            match_res = await match_analyst.run(
                MatchAnalystInput(
                    match_id=str(primary_match.get("match_id", "match-0")),
                    player_id=f"{data.game_name or 'Player'}#{data.tag_line or '000'}",
                    match_data=primary_match,
                    player_stats=player_stats,
                ),
                context,
            )

            econ_res = await economy_coach.run(
                EconomyCoachInput(
                    match_data=primary_match,
                    player_stats=player_stats,
                ),
                context,
            )

            role_res = await role_coach.run(
                RoleCoachInput(
                    agent_name=agent_name,
                    match_data=primary_match,
                    player_stats=player_stats,
                ),
                context,
            )

            # Synthesize into final coaching report
            final_report = await report_writer.run(
                ReportWriterInput(
                    player_name=data.game_name or "Player",
                    player_tag=data.tag_line or "000",
                    rank=data.rank,
                    match_analysis=match_res.model_dump(),
                    economy_analysis=econ_res.model_dump(),
                    role_analysis=role_res.model_dump(),
                ),
                context,
            )

            return OrchestratorOutput(
                requested_agents=[
                    "match_analyst",
                    "economy_coach",
                    "role_coach",
                    "report_writer",
                ],
                reasoning=(
                    "Orchestrated tactical analysis across combat, economy, and "
                    f"role execution for {data.game_name}#{data.tag_line}."
                ),
                report=final_report.model_dump(),
            )

        return OrchestratorOutput(
            requested_agents=requested,
            reasoning=f"Orchestrator initialized. Found agents: {', '.join(requested)}",
        )


if "orchestrator" not in AgentRegistry.list():
    AgentRegistry.register("orchestrator", OrchestratorAgent)

from agents.shared.base_agent import BaseAgent
from agents.shared.context import AgentContext
from agents.shared.registry import AgentRegistry

from .schema import OrchestratorInput, OrchestratorOutput


class OrchestratorAgent(BaseAgent[OrchestratorInput, OrchestratorOutput]):
    """
    Main orchestrator agent that delegates tasks to specialized agents.
    """

    def __init__(self) -> None:
        super().__init__(name="AI Orchestrator")

    async def run(
        self, data: OrchestratorInput, context: AgentContext
    ) -> OrchestratorOutput:
        """
        Executes the orchestrator logic.
        Uses AgentRegistry to identify available agents without hardcoding.
        """
        # In a real implementation, the LLM would decide which agents to call.
        # For the scaffold, we just list all available agents from the registry.
        available_agents = AgentRegistry.list()

        # Ensure we don't request ourselves to avoid infinite loops
        requested = [name for name in available_agents if name != "orchestrator"]

        return OrchestratorOutput(
            requested_agents=requested,
            reasoning=f"Orchestrator initialized. Found agents: {', '.join(requested)}",
        )


# Register the agent
AgentRegistry.register("orchestrator", OrchestratorAgent)

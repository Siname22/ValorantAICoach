from agents.shared.models import AgentModel


class OrchestratorInput(AgentModel):
    user_message: str


class OrchestratorOutput(AgentModel):
    requested_agents: list[str]
    reasoning: str

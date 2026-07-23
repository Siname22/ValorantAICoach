from pydantic import BaseModel


class OrchestratorInput(BaseModel):
    user_message: str


class OrchestratorOutput(BaseModel):
    requested_agents: list[str]
    reasoning: str

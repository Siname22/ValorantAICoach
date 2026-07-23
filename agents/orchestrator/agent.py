from pathlib import Path

from .schema import (
    OrchestratorInput,
    OrchestratorOutput,
)


class OrchestratorAgent:

    def __init__(self) -> None:

        self.name = "AI Orchestrator"

        self.prompt = Path(__file__).with_name("prompt.md").read_text(encoding="utf-8")

    async def run(
        self,
        data: OrchestratorInput,
    ) -> OrchestratorOutput:

        return OrchestratorOutput(
            requested_agents=[], reasoning="Orchestrator initialized."
        )

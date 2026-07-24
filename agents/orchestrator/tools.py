from typing import Any

from agents.shared.base_tool import BaseTool, ToolSchema


class OrchestratorToolInput(ToolSchema):
    """Schema for OrchestratorTool input."""

    command: str


class OrchestratorTool(BaseTool):
    name: str = "orchestrator_tool"
    description: str = "A dummy tool for orchestrator commands."
    schema: type[OrchestratorToolInput] = OrchestratorToolInput

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "result": f"Executed OrchestratorTool with command: {kwargs.get("command")}"
        }


def available_tools() -> list[BaseTool]:
    """
    Returns a list of available tools for the Orchestrator agent.
    """
    return [OrchestratorTool()]

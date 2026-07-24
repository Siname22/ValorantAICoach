from typing import Any

from agents.shared.base_tool import BaseTool, ToolSchema


class MatchAnalystToolInput(ToolSchema):
    """Schema for MatchAnalystTool input."""

    query: str


class MatchAnalystTool(BaseTool):
    name: str = "match_analyst_tool"
    description: str = "A dummy tool for match analysis."
    schema: type[MatchAnalystToolInput] = MatchAnalystToolInput

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "result": f"Executed MatchAnalystTool with query: {kwargs.get("query")}"
        }


def available_tools() -> list[BaseTool]:
    """
    Returns a list of available tools for the Match Analyst agent.
    """
    return [MatchAnalystTool()]

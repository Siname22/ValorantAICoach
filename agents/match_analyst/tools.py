from typing import Any

from backend.providers.riot.exceptions import RiotError, RiotNotFoundError
from backend.providers.riot.models import Match, Player, Rank
from backend.providers.riot.provider import RiotProvider

from agents.shared.base_tool import BaseTool, ToolSchema
from agents.shared.container import container


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


class RiotPlayerStatsToolInput(ToolSchema):
    """Schema for RiotPlayerStatsTool input."""

    game_name: str
    tag_line: str


class RiotPlayerStatsTool(BaseTool):
    name: str = "riot_player_stats_tool"
    description: str = (
        "Retrieves player information,rank,"
        "and recent match history from Riot API"
        " via HenrikDev."
    )
    schema: type[RiotPlayerStatsToolInput] = RiotPlayerStatsToolInput

    async def execute(
        self, game_name: str, tag_line: str, **kwargs: Any
    ) -> dict[str, Any]:
        riot_provider: RiotProvider = container.resolve(RiotProvider)

        try:
            player: Player = await riot_provider.get_player_by_riot_id(
                game_name, tag_line
            )
            rank: Rank = await riot_provider.get_player_rank(player.puuid)
            matches: list[Match] = await riot_provider.get_player_match_history(
                player.puuid
            )

            return {
                "player": player.model_dump(),
                "rank": rank.model_dump(),
                "recent_matches": [m.model_dump() for m in matches],
            }
        except RiotNotFoundError:
            return {"error": f"Player {game_name}#{tag_line} not found."}
        except RiotError as e:
            return {"error": f"An error occurred while fetching Riot player stats: {e}"}


def available_tools() -> list[BaseTool]:
    """
    Returns a list of available tools for the Match Analyst agent.
    """
    return [MatchAnalystTool(), RiotPlayerStatsTool()]

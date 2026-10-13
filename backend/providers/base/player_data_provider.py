"""Abstract Base Data Provider interface for player statistics and match history."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from backend.providers.base.provider import BaseProvider

if TYPE_CHECKING:
    from backend.providers.riot.models import Match, Player, Rank


class BasePlayerDataProvider(BaseProvider, ABC):
    """Abstract interface for external player data providers."""

    @abstractmethod
    async def get_player_by_riot_id(self, game_name: str, tag_line: str) -> Player:
        """Fetch player identity and puuid by game name and tag line."""

    @abstractmethod
    async def get_player_rank(self, puuid: str) -> Rank:
        """Fetch player rank details by player UUID."""

    @abstractmethod
    async def get_player_match_history(self, puuid: str) -> list[Match]:
        """Fetch recent match history list for player UUID."""

from agents.shared.memory.base import BaseMemory
from agents.shared.memory.models import MemoryEntry


class InMemoryMemory(BaseMemory):
    """
    An in-memory implementation of BaseMemory that stores entries in a list.
    Designed for efficiency by avoiding full list copies on each addition.
    """

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []

    async def add(self, entry: MemoryEntry) -> None:
        """
        Adds a single memory entry to the in-memory list.
        """
        self._entries.append(entry)

    async def get_all(self) -> list[MemoryEntry]:
        """
        Retrieves all memory entries from the in-memory list.
        Returns a copy to prevent external modification of the internal state.
        """
        return list(self._entries)

    async def clear(self) -> None:
        """
        Clears all memory entries from the in-memory list.
        """
        self._entries.clear()

from abc import ABC, abstractmethod

from agents.shared.memory.models import MemoryEntry


class BaseMemory(ABC):
    """
    Abstract base class for all memory implementations.
    Defines the contract for adding, retrieving, and clearing memory entries.
    """

    @abstractmethod
    async def add(self, entry: MemoryEntry) -> None:
        """
        Adds a single memory entry.
        """
        pass

    @abstractmethod
    async def get_all(self) -> list[MemoryEntry]:
        """
        Retrieves all memory entries.
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """
        Clears all memory entries.
        """
        pass

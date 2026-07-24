from typing import Any

from pydantic import Field

from .models import AgentModel


class MemoryEntry(AgentModel):
    """Represents a single entry in the agent's temporary memory."""

    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMemory(AgentModel):
    """
    Temporary, non-persistent memory for a single agent execution.
    """

    entries: list[MemoryEntry] = Field(default_factory=list)

    def add_entry(
        self, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> "AgentMemory":
        """
        Adds a new entry to the memory and returns a new instance
        (since AgentModel is frozen).
        """
        new_entry = MemoryEntry(role=role, content=content, metadata=metadata or {})
        return AgentMemory(entries=self.entries + [new_entry])

    def get_all(self) -> list[MemoryEntry]:
        """Returns all memory entries."""
        return self.entries

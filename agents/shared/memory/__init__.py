from typing import Any

from pydantic import Field

from agents.shared.models import AgentModel

from .base import BaseMemory
from .in_memory import InMemoryMemory
from .models import MemoryEntry


class AgentMemory(AgentModel):
    """Compatibility wrapper for the legacy in-memory agent memory API."""

    entries: list[MemoryEntry] = Field(default_factory=list)

    def add_entry(
        self, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> "AgentMemory":
        new_entry = MemoryEntry(role=role, content=content, metadata=metadata or {})
        return AgentMemory(entries=self.entries + [new_entry])

    def get_all(self) -> list[MemoryEntry]:
        return self.entries


__all__ = ["AgentMemory", "BaseMemory", "InMemoryMemory", "MemoryEntry"]

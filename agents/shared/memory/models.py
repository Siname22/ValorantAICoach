from typing import Any

from pydantic import Field

from agents.shared.models import AgentModel


class MemoryEntry(AgentModel):
    """Represents a single entry in the agent's memory."""

    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)

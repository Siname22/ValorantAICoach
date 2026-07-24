import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from .models import AgentModel
from .types import Metadata


class AgentContext(AgentModel):
    """
    Shared object containing the execution context for an agent run.
    """

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider: str = Field(default="default")

    # Placeholder for future logger injection
    logger: Any | None = Field(default=None, exclude=True)

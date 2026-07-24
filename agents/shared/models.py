from pydantic import BaseModel, ConfigDict


class AgentModel(BaseModel):
    """
    Base model for all agent-related Pydantic schemas.
    Provides common configuration for immutability and strict typing.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

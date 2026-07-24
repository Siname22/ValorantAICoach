from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolSchema(BaseModel):
    """Base schema for tool input, used for LLM function calling."""

    pass


class BaseTool(ABC):
    """
    Abstract base class for all tools that agents can use.
    Designed to be compatible with LLM function calling mechanisms.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "execute" in cls.__dict__:
            original_execute = cls.__dict__["execute"]

            async def wrapped_execute(
                self: "BaseTool", **kwargs: Any
            ) -> dict[str, Any]:
                if self.schema is None:
                    return await original_execute(self, **kwargs)
                validated = self.schema.model_validate(kwargs)
                return await original_execute(self, **validated.model_dump())

            cls.execute = wrapped_execute

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the tool does."""
        pass

    @property
    @abstractmethod
    def schema(self) -> type[ToolSchema] | None:
        """The Pydantic schema for the tool's input parameters."""
        pass

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Executes the tool with the given parameters.

        Args:
            **kwargs: Parameters for the tool, validated against its schema.

        Returns:
            A dictionary representing the result of the tool's execution.
        """
        if self.schema is None:
            return {}

        validated = self.schema.model_validate(kwargs)
        return {"validated": validated.model_dump()}

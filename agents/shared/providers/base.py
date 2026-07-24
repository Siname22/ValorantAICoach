from abc import ABC, abstractmethod
from typing import Any

from agents.shared.context import AgentContext
from agents.shared.providers.models import ProviderHealth


class BaseProvider(ABC):
    """
    Abstract base class for all external service providers (LLMs, Tools, etc.).
    Defines a common interface for provider management and interaction.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the provider."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """The version of the provider implementation."""
        pass

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Performs a health check on the provider.

        Returns:
            A ProviderHealth object indicating the status.
        """
        pass

    @abstractmethod
    async def execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        """
        Executes a specific operation with the provider.

        Args:
            context: The AgentContext for the current execution.
            **kwargs: Arbitrary keyword arguments for the provider operation.

        Returns:
            A dictionary containing the results of the operation.
        """
        pass

from typing import Any, TypeVar

from agents.shared.base_tool import BaseTool
from agents.shared.memory.base import BaseMemory
from agents.shared.providers import BaseProvider as FrameworkBaseProvider

T = TypeVar("T")


class DependencyContainer:
    """
    A lightweight dependency injection container for managing core framework components.
    Avoids external DI frameworks to maintain simplicity and control.
    Supports resolution by name and by type.
    """

    def __init__(self) -> None:
        self._providers: dict[str, FrameworkBaseProvider] = {}
        self._memory_instances: dict[str, BaseMemory] = {}
        self._tools: dict[str, BaseTool] = {}
        self._instances: dict[type, Any] = {}

    def register_provider(self, name: str, provider: FrameworkBaseProvider) -> None:
        self._providers[name] = provider
        self._instances[type(provider)] = provider

    def get_provider(self, name: str) -> FrameworkBaseProvider:
        return self._providers[name]

    def register_memory(self, name: str, memory: BaseMemory) -> None:
        self._memory_instances[name] = memory
        self._instances[type(memory)] = memory

    def get_memory(self, name: str) -> BaseMemory:
        return self._memory_instances[name]

    def register_tool(self, name: str, tool: BaseTool) -> None:
        self._tools[name] = tool
        self._instances[type(tool)] = tool

    def get_tool(self, name: str) -> BaseTool:
        return self._tools[name]

    def get_all_tools(self) -> dict[str, BaseTool]:
        return self._tools

    def register_instance(self, cls: type[T], instance: T) -> None:
        """Registers an arbitrary instance by its class type."""
        self._instances[cls] = instance

    def resolve(self, cls: type[T]) -> T:
        """
        Resolves a dependency by its class type.

        Args:
            cls: The class type to resolve.

        Returns:
            The registered instance of the class.

        Raises:
            KeyError: If no instance of the class is registered.
        """
        if cls in self._instances:
            return self._instances[cls]

        # Fallback: check if any registered instance is a subclass of cls
        for instance in self._instances.values():
            if isinstance(instance, cls):
                return instance

        raise KeyError(
            f"No instance of type {cls.__name__} is registered in the container."
        )

    def reset(self) -> None:
        """Clears all registered dependencies. Useful for testing."""
        self._providers.clear()
        self._memory_instances.clear()
        self._tools.clear()
        self._instances.clear()


# Global instance of the container
container = DependencyContainer()

from .base_agent import BaseAgent
from .exceptions import AgentError


class AgentRegistry:
    """
    Dynamic registry for managing available agents in the system.
    Follows an explicit registration pattern to avoid magic imports.
    Version 2 includes enhanced management methods for testing and clarity.
    """

    _agents: dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: type[BaseAgent]) -> None:
        """
        Registers an agent class under a specific name.

        Args:
            name: The unique identifier for the agent.
            agent_class: The class of the agent to register.
        """
        if name in cls._agents:
            raise AgentError(f"Agent '{name}' is already registered.")
        cls._agents[name] = agent_class

    @classmethod
    def remove_agent(cls, name: str) -> None:
        """
        Removes an agent by its name from the registry.

        Args:
            name: The unique identifier for the agent.
        """
        if name not in cls._agents:
            raise AgentError(f"Agent '{name}' is not registered.")
        del cls._agents[name]

    @classmethod
    def get_agent(cls, name: str) -> type[BaseAgent]:
        """
        Retrieves an agent class by its name.

        Args:
            name: The unique identifier for the agent.

        Returns:
            The registered agent class.

        Raises:
            AgentError: If the agent is not found in the registry.
        """
        if name not in cls._agents:
            raise AgentError(f"Agent '{name}' not found in registry.")
        return cls._agents[name]

    @classmethod
    def list_agents(cls) -> list[str]:
        """
        Lists all registered agent names.

        Returns:
            A list of registered agent names.
        """
        return list(cls._agents.keys())

    @classmethod
    def unregister(cls, name: str) -> None:
        """Backward-compatible alias for removing an agent by name."""
        cls.remove_agent(name)

    @classmethod
    def get(cls, name: str) -> type[BaseAgent]:
        """Backward-compatible alias for retrieving an agent class."""
        return cls.get_agent(name)

    @classmethod
    def list(cls) -> list[str]:
        """Backward-compatible alias for listing registered agent names."""
        return cls.list_agents()

    @classmethod
    def reset(cls) -> None:
        """
        Clears all registered agents from the registry. Useful for testing.
        """
        cls._agents.clear()

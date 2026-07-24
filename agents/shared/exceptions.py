class AgentError(Exception):
    """Base exception for all agent-related errors."""

    pass


class PromptNotFound(AgentError):
    """Raised when an agent's prompt file cannot be found or loaded."""

    pass


class InvalidContext(AgentError):
    """Raised when the agent context is invalid or missing required data."""

    pass


class ToolExecutionError(AgentError):
    """Raised when a tool execution fails during agent operation."""

    pass

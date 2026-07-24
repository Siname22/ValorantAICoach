from abc import ABC
from typing import Any, cast

from .base_tool import BaseTool
from .context import AgentContext
from .exceptions import AgentError, PromptNotFound
from .memory.base import BaseMemory
from .prompts import PromptLoader
from .providers import BaseProvider


class BaseAgent[TInput, TOutput](ABC):  # noqa: B024
    """
    Abstract base class for all AI agents in the framework.
    Enforces a common interface and shared behavior (e.g., prompt loading).
    Includes optional lifecycle hooks and dependency injection support.
    """

    def __init__(
        self,
        name: str,
        llm_provider: BaseProvider | None = None,
        memory: BaseMemory | None = None,
        tools: list[BaseTool] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the agent with optional injected dependencies.

        Args:
            name: The display name or identifier for the agent.
            llm_provider: An optional LLM provider instance.
            memory: An optional memory instance.
            tools: An optional list of tools.
        """
        self.name = name
        try:
            self.prompt = PromptLoader.load_prompt(self.__class__)
        except PromptNotFound:
            self.prompt = ""
        self.llm_provider = llm_provider
        self.memory = memory
        self.tools = tools if tools is not None else []

    async def run(self, data: TInput, context: AgentContext) -> TOutput:
        """
        Orchestrates the agent's execution, including lifecycle hooks and
        error handling.

        Args:
            data: The input data model for the agent.
            context: The execution context containing metadata and shared state.

        Returns:
            The output data model produced by the agent.
        """
        try:
            await self.before_run(data, context)
            result = await self.execute(data, context)
            await self.after_run(data, context, result)
            return result
        except Exception as e:
            await self.on_error(data, context, e)
            raise AgentError(f"Agent '{self.name}' failed during execution: {e}") from e

    async def execute(self, data: TInput, context: AgentContext) -> TOutput:
        """
        Executes the agent's core logic.

        Subclasses may override this method. The default implementation returns
        the input as-is for compatibility with scaffold-based agents.
        """
        return cast(TOutput, data)

    async def before_run(
        self, data: TInput, context: AgentContext
    ) -> None:  # noqa: B027
        """
        Optional hook executed before the agent's execute method.
        Can be overridden by subclasses for pre-processing or setup.
        """
        return None

    async def after_run(  # noqa: B027
        self, data: TInput, context: AgentContext, result: TOutput
    ) -> None:
        """
        Optional hook executed after the agent's execute method completes successfully.
        Can be overridden by subclasses for post-processing or cleanup.
        """
        return None

    async def on_error(  # noqa: B027
        self, data: TInput, context: AgentContext, error: Exception
    ) -> None:
        """
        Optional hook executed if an error occurs during the agent's execute method.
        Can be overridden by subclasses for error handling or logging.
        """
        return None

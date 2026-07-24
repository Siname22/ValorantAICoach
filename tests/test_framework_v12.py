from typing import Any

import pytest
from agents.shared.base_agent import BaseAgent
from agents.shared.base_tool import BaseTool, ToolSchema
from agents.shared.container import DependencyContainer
from agents.shared.context import AgentContext
from agents.shared.exceptions import AgentError
from agents.shared.memory.base import BaseMemory
from agents.shared.memory.in_memory import InMemoryMemory
from agents.shared.memory.models import MemoryEntry
from agents.shared.models import AgentModel
from agents.shared.providers.base import BaseProvider
from agents.shared.providers.models import ProviderHealth
from agents.shared.registry import AgentRegistry

# --- Shared Test Utilities ---


class DummyAgentInput(AgentModel):
    fail: bool = False


class DummyAgentOutput(AgentModel):
    success: bool = True


class DummyLLMProvider(BaseProvider):
    name: str = "dummy_llm"
    version: str = "1.0"

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(status="healthy", timestamp="now")

    async def execute(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        return {"response": "LLM response"}


class DummyToolInput(ToolSchema):
    value: str


class DummyTool(BaseTool):
    name: str = "dummy_tool"
    description: str = "A dummy tool for testing."
    schema: type[DummyToolInput] = DummyToolInput

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return {"processed_value": kwargs.get("value").upper()}


class DummyTestAgent(BaseAgent[DummyAgentInput, DummyAgentOutput]):
    def __init__(
        self,
        name: str = "Test Agent",
        llm_provider: BaseProvider | None = None,
        memory: BaseMemory | None = None,
        tools: list[BaseTool] | None = None,
    ) -> None:
        super().__init__(name, llm_provider, memory, tools)
        self.before_run_called = False
        self.after_run_called = False
        self.on_error_called = False
        self.execute_called = False

    async def execute(
        self, data: DummyAgentInput, context: AgentContext
    ) -> DummyAgentOutput:
        self.execute_called = True
        if data.fail:
            raise ValueError("Simulated failure in execute")
        return DummyAgentOutput(success=True)

    async def before_run(self, data: DummyAgentInput, context: AgentContext) -> None:
        self.before_run_called = True

    async def after_run(
        self, data: DummyAgentInput, context: AgentContext, result: DummyAgentOutput
    ) -> None:
        self.after_run_called = True

    async def on_error(
        self, data: DummyAgentInput, context: AgentContext, error: Exception
    ) -> None:
        self.on_error_called = True


# --- Provider Layer Tests ---


@pytest.mark.asyncio
async def test_base_provider_health_check():
    provider = DummyLLMProvider()
    health = await provider.health_check()
    assert health.status == "healthy"


@pytest.mark.asyncio
async def test_base_provider_execute():
    provider = DummyLLMProvider()
    context = AgentContext()
    result = await provider.execute(context, prompt="hello")
    assert result == {"response": "LLM response"}


# --- Dependency Injection Tests ---


def test_dependency_container_registration_and_retrieval():
    container = DependencyContainer()
    container.reset()  # Ensure clean state

    llm_provider = DummyLLMProvider()
    memory = InMemoryMemory()
    tool = DummyTool()

    container.register_provider("llm", llm_provider)
    container.register_memory("session_memory", memory)
    container.register_tool("test_tool", tool)

    assert container.get_provider("llm") == llm_provider
    assert container.get_memory("session_memory") == memory
    assert container.get_tool("test_tool") == tool
    assert "test_tool" in container.get_all_tools()

    container.reset()
    assert not container._providers
    assert not container._memory_instances
    assert not container._tools


# --- AgentMemory Refactor Tests ---


@pytest.mark.asyncio
async def test_in_memory_memory_efficiency():
    memory = InMemoryMemory()
    assert await memory.get_all() == []

    entry1 = MemoryEntry(role="user", content="hello")
    await memory.add(entry1)
    assert len(await memory.get_all()) == 1

    entry2 = MemoryEntry(role="agent", content="hi")
    await memory.add(entry2)
    assert len(await memory.get_all()) == 2

    # Ensure no full list copy on add, internal list grows
    assert memory._entries[0] == entry1
    assert memory._entries[1] == entry2

    await memory.clear()
    assert await memory.get_all() == []


# --- Agent Registry v2 Tests ---


def test_agent_registry_v2_methods():
    AgentRegistry.reset()  # Ensure clean state

    class AgentA(BaseAgent[DummyAgentInput, DummyAgentOutput]):
        async def execute(
            self, data: DummyAgentInput, context: AgentContext
        ) -> DummyAgentOutput:
            return DummyAgentOutput()

    class AgentB(BaseAgent[DummyAgentInput, DummyAgentOutput]):
        async def execute(
            self, data: DummyAgentInput, context: AgentContext
        ) -> DummyAgentOutput:
            return DummyAgentOutput()

    AgentRegistry.register("agent_a", AgentA)
    AgentRegistry.register("agent_b", AgentB)

    assert "agent_a" in AgentRegistry.list_agents()
    assert AgentRegistry.get_agent("agent_a") == AgentA

    AgentRegistry.remove_agent("agent_a")
    assert "agent_a" not in AgentRegistry.list_agents()
    with pytest.raises(AgentError):
        AgentRegistry.get_agent("agent_a")

    AgentRegistry.reset()
    assert not AgentRegistry.list_agents()


# --- Improved BaseAgent Tests ---


@pytest.mark.asyncio
async def test_base_agent_with_injected_dependencies():
    llm_provider = DummyLLMProvider()
    memory = InMemoryMemory()
    tool = DummyTool()

    agent = DummyTestAgent(llm_provider=llm_provider, memory=memory, tools=[tool])

    assert agent.llm_provider == llm_provider
    assert agent.memory == memory
    assert agent.tools == [tool]


@pytest.mark.asyncio
async def test_base_agent_lifecycle_hooks_orchestration_success():
    agent = DummyTestAgent()
    context = AgentContext()
    data = DummyAgentInput(fail=False)

    result = await agent.run(data, context)

    assert agent.before_run_called
    assert agent.execute_called
    assert agent.after_run_called
    assert not agent.on_error_called
    assert result.success is True


@pytest.mark.asyncio
async def test_base_agent_lifecycle_hooks_orchestration_failure():
    agent = DummyTestAgent()
    context = AgentContext()
    data = DummyAgentInput(fail=True)

    with pytest.raises(AgentError, match="Simulated failure in execute"):
        await agent.run(data, context)

    assert agent.before_run_called
    assert agent.execute_called
    assert not agent.after_run_called
    assert agent.on_error_called


# --- PromptLoader compatibility test (ensure it still works with new BaseAgent) ---


class AgentWithPromptForV12(BaseAgent[DummyAgentInput, DummyAgentOutput]):
    def __init__(
        self,
        name: str = "Agent With Prompt V12",
        llm_provider: BaseProvider | None = None,
        memory: BaseMemory | None = None,
        tools: list[BaseTool] | None = None,
    ) -> None:
        super().__init__(name, llm_provider, memory, tools)

    async def execute(
        self, data: DummyAgentInput, context: AgentContext
    ) -> DummyAgentOutput:
        return DummyAgentOutput()


def test_prompt_loader_compatibility_v12():
    # This test relies on a prompt.md existing in the same package as
    # AgentWithPromptForV12. For a proper isolated test, a mock for
    # importlib.resources.files would be ideal, but for integration/
    # compatibility we assume the file structure is correct.
    # The actual prompt.md for this agent would be in
    # agents/shared/test_framework_v12/prompt.md. For now, we rely on the
    # existing prompt.md in agents/orchestrator or agents/match_analyst for a
    # successful load, or mock it if a dedicated test prompt is not created.

    # For this test, we will temporarily create a dummy prompt.md for
    # AgentWithPromptForV12 in a way that importlib.resources can find it.

    # Determine the path for the dummy prompt.md. This assumes
    # tests/test_framework_v12.py is in the agents/shared/ directory structure
    # for importlib, which is not strictly true. A better approach is to
    # create a temporary package.

    # Let's mock importlib.resources.files for this test to make it isolated
    from unittest.mock import patch

    with patch("importlib.resources.files") as mock_files:
        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            "Mocked Prompt Content V12"
        )
        agent = AgentWithPromptForV12()
        assert agent.prompt == "Mocked Prompt Content V12"
        mock_files.assert_called_once_with(AgentWithPromptForV12.__module__)


# --- Existing Agent Scaffold Tests (ensure compatibility) ---


@pytest.mark.asyncio
async def test_orchestrator_agent_scaffold_compatibility():
    from agents.orchestrator.agent import OrchestratorAgent
    from agents.orchestrator.schema import OrchestratorInput

    # Instantiate with default (None) dependencies for compatibility
    agent = OrchestratorAgent()
    context = AgentContext()
    data = OrchestratorInput(user_message="test")

    result = await agent.run(data, context)
    assert isinstance(result.requested_agents, list)
    assert isinstance(result.reasoning, str)


@pytest.mark.asyncio
async def test_match_analyst_agent_scaffold_compatibility():
    from agents.match_analyst.agent import MatchAnalystAgent
    from agents.match_analyst.schema import MatchAnalystInput

    # Instantiate with default (None) dependencies for compatibility
    agent = MatchAnalystAgent()
    context = AgentContext()
    data = MatchAnalystInput(match_id="123", player_id="456")

    result = await agent.run(data, context)
    assert result.analysis_summary is not None
    assert isinstance(result.metrics, dict)

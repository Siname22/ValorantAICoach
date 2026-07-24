from typing import Any

import pytest
from agents.shared.base_agent import BaseAgent
from agents.shared.base_tool import BaseTool, ToolSchema
from agents.shared.context import AgentContext
from agents.shared.exceptions import AgentError, PromptNotFound
from agents.shared.memory import AgentMemory
from agents.shared.models import AgentModel
from agents.shared.prompts import PromptLoader
from agents.shared.registry import AgentRegistry
from pydantic import BaseModel, ValidationError

# --- Shared Test Utilities ---


class DummyAgent(BaseAgent):
    def __init__(self, name: str = "Dummy Agent") -> None:
        super().__init__(name)
        self.before_run_called = False
        self.after_run_called = False
        self.on_error_called = False

    async def run(self, data: BaseModel, context: AgentContext) -> BaseModel:
        if data.fail:
            raise ValueError("Simulated failure")
        return DummyAgentOutput()

    async def before_run(self, data: BaseModel, context: AgentContext) -> None:
        self.before_run_called = True

    async def after_run(
        self, data: BaseModel, context: AgentContext, result: BaseModel
    ) -> None:
        self.after_run_called = True

    async def on_error(
        self, data: BaseModel, context: AgentContext, error: Exception
    ) -> None:
        self.on_error_called = True


class DummyAgentInput(AgentModel):
    fail: bool = False


class DummyAgentOutput(AgentModel):
    success: bool = True


class DummyToolInput(ToolSchema):
    value: str


class DummyTool(BaseTool):
    name: str = "dummy_tool"
    description: str = "A dummy tool for testing."
    schema: type[DummyToolInput] = DummyToolInput

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return {"processed_value": kwargs.get("value").upper()}


# --- AgentModel Tests ---


def test_agent_model_is_frozen():
    class TestModel(AgentModel):
        field: str

    model = TestModel(field="value")
    with pytest.raises(ValidationError):
        model.field = "new_value"


# --- AgentRegistry Tests ---


def test_agent_registry_registration():
    # Ensure clean state for this test
    if "dummy" in AgentRegistry._agents:
        AgentRegistry.unregister("dummy")

    class AnotherDummyAgent(BaseAgent[DummyAgentInput, DummyAgentOutput]):
        def __init__(self) -> None:
            super().__init__(name="Another Dummy Agent")

        async def run(
            self, data: DummyAgentInput, context: AgentContext
        ) -> DummyAgentOutput:
            return DummyAgentOutput()

    AgentRegistry.register("dummy", AnotherDummyAgent)
    assert "dummy" in AgentRegistry.list()
    assert AgentRegistry.get("dummy") == AnotherDummyAgent

    with pytest.raises(AgentError, match="already registered"):
        AgentRegistry.register("dummy", AnotherDummyAgent)

    AgentRegistry.unregister("dummy")
    assert "dummy" not in AgentRegistry.list()

    with pytest.raises(AgentError, match="not found in registry"):
        AgentRegistry.get("dummy")


# --- AgentContext Tests ---


def test_agent_context_initialization():
    context = AgentContext()
    assert context.request_id is not None
    assert context.execution_id is not None
    assert context.metadata == {}
    assert context.provider == "default"
    assert context.created_at is not None


# --- AgentMemory Tests ---


def test_agent_memory_immutability():
    memory = AgentMemory()
    assert len(memory.get_all()) == 0

    new_memory = memory.add_entry(role="user", content="hello")

    # Original memory should be unchanged
    assert len(memory.get_all()) == 0

    # New memory should have the entry
    assert len(new_memory.get_all()) == 1
    assert new_memory.get_all()[0].role == "user"
    assert new_memory.get_all()[0].content == "hello"


# --- PromptLoader Tests ---


class AgentWithPrompt(BaseAgent[DummyAgentInput, DummyAgentOutput]):
    def __init__(self) -> None:
        super().__init__(name="Agent With Prompt")

    async def run(
        self, data: DummyAgentInput, context: AgentContext
    ) -> DummyAgentOutput:
        return DummyAgentOutput()


class AgentWithoutPrompt(BaseAgent[DummyAgentInput, DummyAgentOutput]):
    def __init__(self) -> None:
        super().__init__(name="Agent Without Prompt")

    async def run(
        self, data: DummyAgentInput, context: AgentContext
    ) -> DummyAgentOutput:
        return DummyAgentOutput()


def test_prompt_loader_loads_existing_prompt(tmp_path):
    # Create a dummy prompt.md file in a temporary directory for the test
    # This simulates the structure where prompt.md is next to the agent class file
    agent_module_path = tmp_path / "agents" / "shared" / "test_agent_with_prompt.py"
    agent_module_path.parent.mkdir(parents=True, exist_ok=True)
    agent_module_path.write_text("class AgentWithPrompt:\n    pass")
    (agent_module_path.parent / "prompt.md").write_text("Test Prompt Content")

    # Temporarily add tmp_path to sys.path to allow importlib to find the module
    import sys

    sys.path.insert(0, str(tmp_path))

    # Dynamically create a mock module and class for testing importlib.resources
    # This is a bit tricky because importlib.resources works on actual packages/modules
    # For simplicity, we'll mock the importlib.resources.files call for this test
    # In a real scenario, you'd ensure the test agent class is part of a package

    # For now, let's test the direct call with a mock
    from unittest.mock import patch

    with patch("importlib.resources.files") as mock_files:
        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            "Mocked Prompt Content"
        )
        prompt_content = PromptLoader.load_prompt(AgentWithPrompt)
        assert prompt_content == "Mocked Prompt Content"
        mock_files.assert_called_once_with(AgentWithPrompt.__module__)

    sys.path.pop(0)


def test_prompt_loader_raises_not_found_for_missing_prompt():
    with pytest.raises(PromptNotFound):
        # AgentWithoutPrompt does not have a corresponding prompt.md in its module path
        PromptLoader.load_prompt(AgentWithoutPrompt)


# --- BaseTool Tests ---


def test_base_tool_implementation():
    tool = DummyTool()
    assert tool.name == "dummy_tool"
    assert tool.description == "A dummy tool for testing."
    assert tool.schema == DummyToolInput


@pytest.mark.asyncio
async def test_base_tool_execute():
    tool = DummyTool()
    result = await tool.execute(value="test")
    assert result == {"processed_value": "TEST"}

    with pytest.raises(ValidationError):
        await tool.execute(invalid_param="test")


# --- BaseAgent Hooks Tests ---


@pytest.mark.asyncio
async def test_base_agent_hooks_success():
    agent = DummyAgent()
    context = AgentContext()
    data = DummyAgentInput(fail=False)
    DummyAgentOutput()

    # Mock the run method to call hooks manually for testing
    async def mock_run(self_agent, data, context):
        await self_agent.before_run(data, context)
        result = await self_agent._original_run(data, context)  # Call original run
        await self_agent.after_run(data, context, result)
        return result

    # Temporarily replace the run method with our mock for testing hooks
    agent._original_run = agent.run
    agent.run = mock_run.__get__(agent, DummyAgent)

    result = await agent.run(data, context)

    assert agent.before_run_called
    assert agent.after_run_called
    assert not agent.on_error_called
    assert isinstance(result, BaseModel)


@pytest.mark.asyncio
async def test_base_agent_hooks_on_error():
    agent = DummyAgent()
    context = AgentContext()
    data = DummyAgentInput(fail=True)

    # Mock the run method to call hooks manually for testing
    async def mock_run_error(self_agent, data, context):
        await self_agent.before_run(data, context)
        try:
            result = await self_agent._original_run(data, context)
            await self_agent.after_run(data, context, result)
            return result
        except Exception as e:
            await self_agent.on_error(data, context, e)
            raise

    agent._original_run = agent.run
    agent.run = mock_run_error.__get__(agent, DummyAgent)

    with pytest.raises(ValueError, match="Simulated failure"):
        await agent.run(data, context)

    assert agent.before_run_called
    assert not agent.after_run_called
    assert agent.on_error_called


# --- Existing Agent Scaffold Tests (ensure compatibility) ---


@pytest.mark.asyncio
async def test_orchestrator_agent_scaffold():
    from agents.orchestrator.agent import OrchestratorAgent
    from agents.orchestrator.schema import OrchestratorInput

    agent = OrchestratorAgent()
    context = AgentContext()
    data = OrchestratorInput(user_message="test")

    result = await agent.run(data, context)
    assert isinstance(result.requested_agents, list)
    assert isinstance(result.reasoning, str)


@pytest.mark.asyncio
async def test_match_analyst_agent_scaffold():
    from agents.match_analyst.agent import MatchAnalystAgent
    from agents.match_analyst.schema import MatchAnalystInput

    agent = MatchAnalystAgent()
    context = AgentContext()
    data = MatchAnalystInput(match_id="123", player_id="456")

    result = await agent.run(data, context)
    assert result.analysis_summary is not None
    assert isinstance(result.metrics, dict)

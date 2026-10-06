import pytest
from agents.match_analyst.agent import MatchAnalystAgent
from agents.match_analyst.schema import MatchAnalystInput
from agents.shared.context import AgentContext


@pytest.fixture
def agent():
    return MatchAnalystAgent()


@pytest.fixture
def context():
    return AgentContext(request_id="test-req-001")


@pytest.mark.asyncio
async def test_match_analyst_low_kd_identifies_trade_mistakes(agent, context):
    input_data = MatchAnalystInput(
        match_id="m-123",
        player_id="p-456",
        player_stats={
            "kills": 6,
            "deaths": 16,
            "assists": 2,
            "score": 1400,
            "rounds_played": 20,
        },
        match_data={"result": "Defeat"},
    )
    result = await agent.run(input_data, context)

    assert result.metrics["kd_ratio"] == 0.38
    assert result.metrics["kda_ratio"] == 0.50
    assert "Diagnóstico:" in result.analysis_summary
    assert "Error principal:" in result.analysis_summary
    assert "Cambio práctico:" in result.analysis_summary
    assert "Ejercicio:" in result.analysis_summary
    assert "tradeo" in result.diagnosis.lower()
    assert len(result.evidence) >= 3


@pytest.mark.asyncio
async def test_match_analyst_high_kd_defeat_identifies_round_conversion(agent, context):
    input_data = MatchAnalystInput(
        match_id="m-124",
        player_id="p-456",
        player_stats={
            "kills": 26,
            "deaths": 12,
            "assists": 4,
            "score": 5800,
            "rounds_played": 22,
        },
        match_data={"result": "Defeat"},
    )
    result = await agent.run(input_data, context)

    assert result.metrics["kd_ratio"] == 2.17
    assert result.metrics["acs"] == 263.6
    assert "conversión de rondas" in result.diagnosis.lower()
    assert "exit frags" in result.main_mistake.lower()
    assert "post-plant" in result.drill.lower()


@pytest.mark.asyncio
async def test_match_analyst_balanced_performance(agent, context):
    input_data = MatchAnalystInput(
        match_id="m-125",
        player_id="p-456",
        player_stats={
            "kills": 15,
            "deaths": 14,
            "assists": 7,
            "score": 3200,
            "rounds_played": 21,
        },
        match_data={"result": "Victory"},
    )
    result = await agent.run(input_data, context)

    assert result.metrics["kd_ratio"] == 1.07
    assert result.metrics["kda_ratio"] == 1.57
    assert "equilibrado" in result.diagnosis.lower()


@pytest.mark.asyncio
async def test_match_analyst_empty_stats_graceful_fallback(agent, context):
    input_data = MatchAnalystInput(match_id="m-empty", player_id="p-456")
    result = await agent.run(input_data, context)

    assert result.metrics["status"] == "no_stats"
    assert "Diagnóstico:" in result.analysis_summary
    assert result.diagnosis is not None

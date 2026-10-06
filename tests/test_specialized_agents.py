import pytest
from agents.economy_coach.agent import EconomyCoachAgent
from agents.economy_coach.schema import EconomyCoachInput
from agents.orchestrator.agent import OrchestratorAgent
from agents.orchestrator.schema import OrchestratorInput
from agents.report_writer.agent import ReportWriterAgent
from agents.report_writer.schema import ReportWriterInput
from agents.role_coach.agent import RoleCoachAgent
from agents.role_coach.schema import RoleCoachInput
from agents.shared.context import AgentContext


@pytest.fixture
def agent_context():
    return AgentContext()


@pytest.mark.asyncio
async def test_economy_coach_with_rounds(agent_context):
    coach = EconomyCoachAgent()
    input_data = EconomyCoachInput(
        match_data={
            "rounds": [
                {"buy_type": "eco", "loadout_value": 800, "remaining_credits": 2400},
                {
                    "buy_type": "force",
                    "loadout_value": 3100,
                    "remaining_credits": 100,
                },
                {"buy_type": "full", "loadout_value": 4100, "remaining_credits": 600},
                {"buy_type": "full", "loadout_value": 4500, "remaining_credits": 1200},
            ]
        }
    )
    result = await coach.run(input_data, agent_context)

    assert result.economy_rating > 0
    assert result.buy_discipline_score > 0
    assert "créditos" in result.practical_rule or "3.900" in result.practical_rule
    assert len(result.evidence) >= 1


@pytest.mark.asyncio
async def test_economy_coach_fallback_stats(agent_context):
    coach = EconomyCoachAgent()
    input_data = EconomyCoachInput(
        match_data={},
        player_stats={"win_pct": 55.0},
    )
    result = await coach.run(input_data, agent_context)

    assert 30.0 <= result.buy_discipline_score <= 100.0
    assert result.main_mistake != ""
    assert result.drill != ""


@pytest.mark.asyncio
async def test_role_coach_duelist(agent_context):
    coach = RoleCoachAgent()
    input_data = RoleCoachInput(
        agent_name="Jett",
        match_data={"kills": 20, "deaths": 12, "assists": 3},
    )
    result = await coach.run(input_data, agent_context)

    assert result.agent_name == "Jett"
    assert result.role == "Duelist"
    assert result.role_score >= 60.0
    assert "Entry" in result.drill or "pre-fire" in result.drill


@pytest.mark.asyncio
async def test_role_coach_controller_from_uuid(agent_context):
    coach = RoleCoachAgent()
    # Omen UUID: 8e253930-4c05-31dd-1b6c-968525494517
    input_data = RoleCoachInput(
        agent_name="8e253930-4c05-31dd-1b6c-968525494517",
        match_data={"kills": 12, "deaths": 11, "assists": 8},
    )
    result = await coach.run(input_data, agent_context)

    assert result.agent_name == "Omen"
    assert result.role == "Controller"
    assert "humos" in result.main_mistake.lower()


@pytest.mark.asyncio
async def test_role_coach_sentinel(agent_context):
    coach = RoleCoachAgent()
    input_data = RoleCoachInput(
        agent_name="Cypher",
        match_data={"kills": 14, "deaths": 8, "assists": 5},
    )
    result = await coach.run(input_data, agent_context)

    assert result.agent_name == "Cypher"
    assert result.role == "Sentinel"
    assert "trampas" in result.main_mistake or "defensa" in result.main_mistake


@pytest.mark.asyncio
async def test_report_writer_synthesis(agent_context):
    writer = ReportWriterAgent()
    input_data = ReportWriterInput(
        player_name="AcePlayer",
        player_tag="VAL",
        rank="Platinum 2",
        match_analysis={
            "kd_ratio": 1.45,
            "main_mistake": "Sobre-extender tras la primera baja.",
            "drill": "Drill de retroceso táctico tras baja.",
            "evidence": [{"kd": 1.45}],
        },
        economy_analysis={
            "economy_rating": 82.5,
            "main_mistake": "Comprar en rondas semi-eco.",
            "drill": "Revisar banco de equipo antes de comprar.",
            "evidence": [{"econ_rating": 82.5}],
        },
        role_analysis={
            "role": "Duelist",
            "role_score": 78.0,
            "main_mistake": "Entrar sin pedir flash.",
            "drill": "Cuenta de 3 segundos para el entry.",
            "evidence": [{"role_score": 78.0}],
        },
    )
    result = await writer.run(input_data, agent_context)

    assert result.report_id != ""
    assert "AcePlayer#VAL" in result.title
    assert "Platinum 2" in result.title
    assert len(result.key_strengths) >= 1
    assert len(result.critical_flaws) >= 3
    assert len(result.training_plan) >= 3
    assert len(result.evidence) >= 3


@pytest.mark.asyncio
async def test_orchestrator_multi_agent_flow(agent_context):
    orchestrator = OrchestratorAgent()
    input_data = OrchestratorInput(
        game_name="TenZ",
        tag_line="NA1",
        rank="Immortal 1",
        matches=[
            {
                "match_id": "match-test-1",
                "agent_name": "Jett",
                "kills": 24,
                "deaths": 14,
                "assists": 5,
                "score": 310,
                "rounds": [
                    {"buy_type": "full", "loadout_value": 4300},
                    {"buy_type": "full", "loadout_value": 4400},
                ],
            }
        ],
        player_stats={"win_pct": 60.0},
    )
    result = await orchestrator.run(input_data, agent_context)

    assert "match_analyst" in result.requested_agents
    assert "economy_coach" in result.requested_agents
    assert "role_coach" in result.requested_agents
    assert "report_writer" in result.requested_agents
    assert result.report is not None
    assert "TenZ#NA1" in result.report["title"]
    assert len(result.report["training_plan"]) >= 1


@pytest.mark.asyncio
async def test_orchestrator_legacy_message(agent_context):
    orchestrator = OrchestratorAgent()
    input_data = OrchestratorInput(user_message="Hello coach")
    result = await orchestrator.run(input_data, agent_context)

    assert isinstance(result.requested_agents, list)
    assert "Orchestrator initialized" in result.reasoning
    assert result.report is None

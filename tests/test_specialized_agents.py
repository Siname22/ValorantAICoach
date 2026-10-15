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

    # Must NOT fabricate buy_discipline_score or economy_rating from win_pct
    assert result.buy_discipline_score is None
    assert result.economy_rating is None
    assert "no disponible" in result.main_mistake.lower()
    assert result.evidence[0]["status"] == "insufficient_data"


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


@pytest.mark.asyncio
async def test_match_analyst_and_report_writer_grounding_accuracy(agent_context):
    """Test that match-specific stats (e.g. K/D 0.25) take priority over global stats
    (K/D 2.0), and that the report writer accurately extracts the calculated K/D
    rather than falling back to 1.0.
    """
    from agents.match_analyst.agent import MatchAnalystAgent
    from agents.match_analyst.schema import MatchAnalystInput

    analyst = MatchAnalystAgent()
    # Match data: 2 kills, 8 deaths -> K/D 0.25
    # Player stats (career/global): 20 kills, 10 deaths -> K/D 2.0
    input_data = MatchAnalystInput(
        match_id="match-low-kd",
        player_id="Player#001",
        match_data={"kills": 2, "deaths": 8, "assists": 1, "result": "Defeat"},
        player_stats={"kills": 20, "deaths": 10, "kd_ratio": 2.0},
    )
    res = await analyst.run(input_data, agent_context)

    # 1. Analyst metrics and evidence must be 0.25, NOT 2.0
    assert res.metrics["kd_ratio"] == 0.25
    assert "0.25" in res.diagnosis
    kd_evidence = [e for e in res.evidence if e["metric"] == "kd_ratio"][0]
    assert kd_evidence["value"] == 0.25

    # 2. Report writer must incorporate 0.25 into executive summary,
    # not fallback 1.0 or global 2.0
    writer = ReportWriterAgent()
    writer_input = ReportWriterInput(
        player_name="Player",
        player_tag="001",
        rank="Gold 1",
        match_analysis=res.model_dump(),
        economy_analysis={
            "economy_rating": 65.0,
            "main_mistake": "Fuerzas innecesarias",
        },
        role_analysis={"role": "Initiator", "role_score": 60.0},
    )
    report = await writer.run(writer_input, agent_context)

    assert "0.25" in report.executive_summary
    assert "1.0" not in report.executive_summary
    assert "2.0" not in report.executive_summary
    rep_evidence = [e for e in report.evidence if e.get("metric") == "kd_ratio"][0]
    assert rep_evidence["value"] == 0.25


@pytest.mark.asyncio
async def test_report_writer_zero_kd_not_fallback_to_one(agent_context):
    """Verify that an explicit K/D of 0.0 is preserved and not overwritten to 1.0."""
    from agents.report_writer.agent import ReportWriterAgent
    from agents.report_writer.schema import ReportWriterInput

    writer = ReportWriterAgent()
    # Explicit 0.0 K/D without additional evidence
    writer_input = ReportWriterInput(
        player_name="Player",
        player_tag="001",
        rank="Silver 2",
        match_analysis={"metrics": {"kd_ratio": 0.0}},
        economy_analysis={"economy_rating": 50.0},
        role_analysis={"role": "Duelist", "role_score": 40.0},
    )
    report = await writer.run(writer_input, agent_context)

    assert "0.0" in report.executive_summary
    assert "1.0" not in report.executive_summary


@pytest.mark.asyncio
async def test_role_coach_missing_stats_returns_insufficient_data(agent_context):
    """Verify that RoleCoachAgent does not invent 12/10/4 stats when data is missing."""
    coach = RoleCoachAgent()
    input_data = RoleCoachInput(
        agent_name="Jett",
        match_data={},
        player_stats={},
    )
    result = await coach.run(input_data, agent_context)

    assert result.role_score is None
    assert "insuficientes" in result.main_mistake.lower()
    assert result.evidence[0]["status"] == "insufficient_data"


@pytest.mark.asyncio
async def test_report_writer_grounded_missing_ratings_and_flaws(agent_context):
    """Verify ReportWriter does not fabricate 70.0 ratings or default flaws."""
    writer = ReportWriterAgent()
    input_data = ReportWriterInput(
        player_name="AcePlayer",
        player_tag="VAL",
        rank="Silver 1",
        match_analysis={
            "metrics": {"status": "no_stats"},
            "main_mistake": "Datos insuficientes para aislar errores específicos.",
            "drill": "Completar una partida competitiva adicional.",
        },
        economy_analysis={
            "economy_rating": None,
            "main_mistake": (
                "Información económica de rondas no disponible en los datos "
                "de la partida."
            ),
            "drill": "Revisar los créditos de tu equipo en el menú de compra.",
            "evidence": [{"status": "insufficient_data"}],
        },
        role_analysis={
            "role": "Duelist",
            "role_score": None,
            "main_mistake": (
                "Estadísticas de agente insuficientes para evaluar " "desempeño de rol."
            ),
            "drill": (
                "Completar una partida competitiva registrando bajas y " "asistencias."
            ),
            "evidence": [{"status": "insufficient_data"}],
        },
    )
    report = await writer.run(input_data, agent_context)

    # 1. Executive summary must not have fake 70.0 numbers
    assert "70.0" not in report.executive_summary
    assert "sin datos económicos suficientes" in report.executive_summary
    assert "sin métricas detalladas" in report.executive_summary

    # 2. Critical flaws must not include "insuficientes" as a gameplay mistake
    assert (
        "No se detectaron fallos críticos con la información disponible."
        in report.critical_flaws
    )
    assert (
        "Tendencia a tomar duelos sin soporte de utilidad de equipo."
        not in report.critical_flaws
    )

    # 3. Strengths must not invent fake praise
    assert "Capacidad para generar asistencias" not in report.key_strengths[0]
    assert "Sin fortalezas estadísticas destacadas" in report.key_strengths[0]

import uuid
from typing import Any

from agents.shared.base_agent import BaseAgent
from agents.shared.context import AgentContext
from agents.shared.registry import AgentRegistry

from .schema import ReportWriterInput, ReportWriterOutput


class ReportWriterAgent(BaseAgent[ReportWriterInput, ReportWriterOutput]):
    """Synthesizes specialist analyses into an executive coaching report.

    Consolidates quantitative combat, economy discipline, and role execution
    into an actionable training plan with evidence grounding.
    """

    def __init__(self) -> None:
        super().__init__(name="Report Writer")

    async def run(
        self, data: ReportWriterInput, context: AgentContext
    ) -> ReportWriterOutput:
        player_name = data.player_name
        player_tag = data.player_tag
        rank = data.rank or "Unranked"

        match_an = data.match_analysis or {}
        econ_an = data.economy_analysis or {}
        role_an = data.role_analysis or {}

        report_id = str(uuid.uuid4())
        title = f"Informe de Rendimiento Táctico: {player_name}#{player_tag} ({rank})"

        kd = match_an.get("kd_ratio", 1.0)
        econ_rating = econ_an.get("economy_rating", 70.0)
        role_name = role_an.get("role", "Flex")
        role_score = role_an.get("role_score", 70.0)

        # Executive summary
        summary = (
            f"Análisis de rendimiento para {player_name}#{player_tag} en rango {rank}. "
            f"El jugador muestra un ratio K/D de {kd}, con una valoración económica "
            f"de {econ_rating}/100 y una efectividad en su rol de {role_name} "
            f"de {role_score}/100."
        )

        strengths: list[str] = []
        if kd >= 1.0:
            strengths.append(f"Solvencia en duelos individuales con K/D de {kd}.")
        else:
            strengths.append("Capacidad para generar asistencias y apoyo al equipo.")

        if econ_rating >= 70.0:
            strengths.append("Buena disciplina en rondas de compra completa y eco.")
        else:
            strengths.append("Conciencia del valor de la utilidad en rondas clave.")

        flaws: list[str] = []
        if match_an.get("main_mistake"):
            flaws.append(f"Combate: {match_an['main_mistake']}")
        if econ_an.get("main_mistake"):
            flaws.append(f"Economía: {econ_an['main_mistake']}")
        if role_an.get("main_mistake"):
            flaws.append(f"Rol ({role_name}): {role_an['main_mistake']}")

        if not flaws:
            flaws.append("Tendencia a tomar duelos sin soporte de utilidad de equipo.")

        training_plan: list[str] = []
        if match_an.get("drill"):
            training_plan.append(f"Mecánica: {match_an['drill']}")
        if econ_an.get("drill"):
            training_plan.append(f"Finanzas: {econ_an['drill']}")
        if role_an.get("drill"):
            training_plan.append(f"Rol {role_name}: {role_an['drill']}")

        if not training_plan:
            training_plan.append(
                "Dedicar 15 minutos de calentamiento en The Range antes de rankeds."
            )

        # Consolidate evidence
        evidence: list[dict[str, Any]] = []
        if "evidence" in match_an and isinstance(match_an["evidence"], list):
            evidence.extend(match_an["evidence"])
        if "evidence" in econ_an and isinstance(econ_an["evidence"], list):
            evidence.extend(econ_an["evidence"])
        if "evidence" in role_an and isinstance(role_an["evidence"], list):
            evidence.extend(role_an["evidence"])

        return ReportWriterOutput(
            report_id=report_id,
            title=title,
            executive_summary=summary,
            key_strengths=strengths,
            critical_flaws=flaws,
            training_plan=training_plan,
            evidence=evidence,
        )


if "report_writer" not in AgentRegistry.list():
    AgentRegistry.register("report_writer", ReportWriterAgent)

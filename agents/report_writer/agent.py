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

        match_metrics = match_an.get("metrics") or {}
        kd: float | None = None
        if "kd_ratio" in match_metrics and match_metrics["kd_ratio"] is not None:
            kd = float(match_metrics["kd_ratio"])
        elif "kd_ratio" in match_an and match_an["kd_ratio"] is not None:
            kd = float(match_an["kd_ratio"])
        else:
            for ev in match_an.get("evidence", []):
                if ev.get("metric") == "kd_ratio" and ev.get("value") is not None:
                    kd = float(ev["value"])
                    break

        econ_raw = econ_an.get("economy_rating")
        econ_rating = float(econ_raw) if econ_raw is not None else None

        role_name = role_an.get("role", "Flex")
        role_raw = role_an.get("role_score")
        role_score = float(role_raw) if role_raw is not None else None

        # Executive summary
        if kd is not None:
            kd_phrase = f"un ratio K/D de {kd}"
        else:
            kd_phrase = "rendimiento táctico sin ratio K/D registrado"

        econ_phrase = (
            f"una valoración económica de {econ_rating}/100"
            if econ_rating is not None
            else "sin datos económicos suficientes"
        )
        role_phrase = (
            f"una efectividad en su rol de {role_name} de {role_score}/100"
            if role_score is not None
            else f"desempeño de rol ({role_name}) sin métricas detalladas"
        )

        summary = (
            f"Análisis de rendimiento para {player_name}#{player_tag} en rango {rank}. "
            f"El jugador muestra {kd_phrase}, con {econ_phrase} y {role_phrase}."
        )

        strengths: list[str] = []
        if kd is not None and kd >= 1.0:
            strengths.append(f"Solvencia en duelos individuales con K/D de {kd}.")
        else:
            assists_val = match_metrics.get("assists")
            if assists_val is None:
                for ev in match_an.get("evidence", []):
                    if ev.get("metric") == "assists" and ev.get("value") is not None:
                        assists_val = ev["value"]
                        break
            if assists_val is not None and int(assists_val) >= 3:
                strengths.append(
                    "Capacidad para generar asistencias y apoyo al equipo "
                    f"({assists_val} asistencias)."
                )

        if econ_rating is not None:
            if econ_rating >= 70.0:
                strengths.append("Buena disciplina en rondas de compra completa y eco.")
            elif econ_rating >= 50.0:
                strengths.append("Conciencia del valor de la utilidad en rondas clave.")

        if role_score is not None and role_score >= 70.0:
            strengths.append(
                f"Alineación efectiva con las funciones del rol de {role_name}."
            )

        if not strengths:
            strengths.append(
                "Sin fortalezas estadísticas destacadas en la muestra analizada; "
                "se recomienda consolidar fundamentos."
            )

        flaws: list[str] = []
        match_err = match_an.get("main_mistake")
        if match_err and "insuficientes" not in match_err.lower():
            flaws.append(f"Combate: {match_err}")

        econ_err = econ_an.get("main_mistake")
        if (
            econ_err
            and "no disponible" not in econ_err.lower()
            and "insuficientes" not in econ_err.lower()
        ):
            flaws.append(f"Economía: {econ_err}")

        role_err = role_an.get("main_mistake")
        if (
            role_err
            and "no disponible" not in role_err.lower()
            and "insuficientes" not in role_err.lower()
        ):
            flaws.append(f"Rol ({role_name}): {role_err}")

        if not flaws:
            flaws.append(
                "No se detectaron fallos críticos con la información disponible."
            )

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

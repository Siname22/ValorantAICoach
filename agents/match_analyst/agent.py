"""Match Analyst Agent for evaluating Valorant match performance."""

from __future__ import annotations

from typing import Any

from agents.shared.base_agent import BaseAgent
from agents.shared.context import AgentContext
from agents.shared.registry import AgentRegistry

from .schema import MatchAnalystInput, MatchAnalystOutput


class MatchAnalystAgent(BaseAgent[MatchAnalystInput, MatchAnalystOutput]):
    """Agent for analyzing Valorant match data and producing grounded diagnostics.

    Computes performance metrics (K/D, KDA, ACS, Trade efficiency) and produces
    the four-block coaching structure: Diagnóstico, Error principal, Cambio práctico,
    Ejercicio.
    """

    def __init__(self) -> None:
        super().__init__(name="Match Analyst")

    async def run(
        self, data: MatchAnalystInput, context: AgentContext
    ) -> MatchAnalystOutput:
        """Executes match analysis logic and generates actionable feedback."""
        stats: dict[str, Any] = data.player_stats or {}
        match_info: dict[str, Any] = data.match_data or {}

        kills = int(stats.get("kills", 0))
        deaths = int(stats.get("deaths", 0))
        assists = int(stats.get("assists", 0))
        score = int(stats.get("score", 0))
        rounds = int(stats.get("rounds_played") or match_info.get("rounds_played") or 0)
        result = str(match_info.get("result") or stats.get("result") or "Unknown")

        if not stats and not match_info:
            return MatchAnalystOutput(
                analysis_summary=(
                    "**Diagnóstico:**\n"
                    "Partida registrada sin estadísticas numéricas detalladas.\n\n"
                    "**Error principal:**\n"
                    "Datos insuficientes para aislar errores específicos.\n\n"
                    "**Cambio práctico:**\n"
                    "Asegurar la sincronización de datos con el proveedor.\n\n"
                    "**Ejercicio:**\n"
                    "Completar una partida competitiva adicional."
                ),
                metrics={"status": "no_stats", "match_id": data.match_id},
                diagnosis="Partida registrada sin estadísticas numéricas detalladas.",
                main_mistake="Datos insuficientes para aislar errores específicos.",
                practical_change=(
                    "Asegurar la sincronización de datos con el proveedor."
                ),
                drill="Completar una partida competitiva adicional.",
                evidence=[],
            )

        safe_deaths = max(deaths, 1)
        kd_ratio = round(kills / safe_deaths, 2)
        kda_ratio = round((kills + assists) / safe_deaths, 2)
        acs = round(score / max(rounds, 1), 1) if rounds > 0 and score > 0 else None
        trade_rate = round(assists / safe_deaths, 2)

        computed_metrics: dict[str, Any] = {
            "match_id": data.match_id,
            "player_id": data.player_id,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kd_ratio": kd_ratio,
            "kda_ratio": kda_ratio,
            "trade_rate": trade_rate,
            "acs": acs,
            "result": result,
        }

        evidence: list[dict[str, Any]] = [
            {"metric": "kd_ratio", "value": kd_ratio, "benchmark": 1.0},
            {"metric": "kda_ratio", "value": kda_ratio, "benchmark": 1.3},
            {"metric": "trade_rate", "value": trade_rate, "benchmark": 0.35},
        ]

        if kd_ratio < 0.9:
            diagnosis = (
                f"Dificultad en duelos de apertura y baja tasa de tradeo "
                f"(K/D {kd_ratio}, trade rate {trade_rate}). "
                "Se pierden rondas por desventaja numérica temprana."
            )
            main_mistake = (
                "Tomar duelos aislados en ángulos abiertos sin utilidad de "
                "cobertura o sin un compañero listo para re-fraguear."
            )
            practical_change = (
                "Jugar en contacto con el segundo jugador del sitio. "
                "Si tu compañero toma contacto, asómate de inmediato dentro "
                "de los primeros 2 segundos."
            )
            drill = (
                "Entrenamiento de tradeos 2v2 en partidas personalizadas o "
                "Deathmatch con disciplina: disparar solo tras el primer contacto."
            )
        elif kd_ratio >= 1.2 and result.lower() == "defeat":
            diagnosis = (
                f"Alto rendimiento en combate individual (K/D {kd_ratio}, "
                f"{kills} bajas), pero baja conversión de rondas ganadas "
                "(derrota). Impacto disperso."
            )
            main_mistake = (
                "Bajas conseguidas tarde en la ronda ('exit frags') o exceso "
                "de agresividad en situaciones de ventaja numérica "
                "(sobre-extensión tras plantar la Spike)."
            )
            practical_change = (
                "Priorizar el control de mapa y el tiempo de la Spike en post-plant "
                "en lugar de buscar duelos finales en solitario."
            )
            drill = (
                "Revisión de rondas post-plant: comprobar posición cruzada con el "
                "equipo en al menos el 80% de las situaciones con Spike plantada."
            )
        else:
            diagnosis = (
                f"Rendimiento sólido y equilibrado (K/D {kd_ratio}, "
                f"KDA {kda_ratio}). Fundamentos consistentes en combate."
            )
            main_mistake = (
                "Pequeños fallos de disciplina económica y uso de utilidad "
                "en rondas de transición."
            )
            practical_change = (
                "Mantener la disciplina de compra en equipo (respetar compras "
                "eco y semi-buy) para garantizar compra completa en rondas clave."
            )
            drill = (
                "Práctica de rutinas de utilidad en servidor vacío en los primeros "
                "10 segundos de ronda en el mapa jugado."
            )

        summary = (
            f"**Diagnóstico:**\n{diagnosis}\n\n"
            f"**Error principal:**\n{main_mistake}\n\n"
            f"**Cambio práctico:**\n{practical_change}\n\n"
            f"**Ejercicio:**\n{drill}"
        )

        return MatchAnalystOutput(
            analysis_summary=summary,
            metrics=computed_metrics,
            diagnosis=diagnosis,
            main_mistake=main_mistake,
            practical_change=practical_change,
            drill=drill,
            evidence=evidence,
        )


# Register the agent
AgentRegistry.register("match_analyst", MatchAnalystAgent)

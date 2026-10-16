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

        # Prioritize match-level statistics over career aggregate player_stats
        kills = int(
            match_info.get("kills")
            if match_info.get("kills") is not None
            else stats.get("kills", 0)
        )
        deaths = int(
            match_info.get("deaths")
            if match_info.get("deaths") is not None
            else stats.get("deaths", 0)
        )
        assists = int(
            match_info.get("assists")
            if match_info.get("assists") is not None
            else stats.get("assists", 0)
        )
        score = int(
            match_info.get("score")
            if match_info.get("score") is not None
            else stats.get("score", 0)
        )
        rounds = int(match_info.get("rounds_played") or stats.get("rounds_played") or 0)
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
        assist_death_ratio = round(assists / safe_deaths, 2)

        computed_metrics: dict[str, Any] = {
            "match_id": data.match_id,
            "player_id": data.player_id,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kd_ratio": kd_ratio,
            "kda_ratio": kda_ratio,
            "assist_death_ratio": assist_death_ratio,
            "acs": acs,
            "result": result,
        }

        evidence: list[dict[str, Any]] = [
            {"metric": "kd_ratio", "value": kd_ratio, "benchmark": 1.0},
            {"metric": "kda_ratio", "value": kda_ratio, "benchmark": 1.3},
            {
                "metric": "assist_death_ratio",
                "value": assist_death_ratio,
                "benchmark": 0.35,
            },
        ]

        if kd_ratio < 0.9:
            diagnosis = (
                f"Dificultad en balance de duelos individuales y bajo ratio de "
                f"asistencias/tradeo (K/D {kd_ratio}, "
                f"ratio de asistencias {assist_death_ratio})."
            )
            main_mistake = (
                f"Déficit en el balance de bajas/muertes ({kills} bajas frente a "
                f"{deaths} muertes). Sin telemetría de eventos por ronda, no se "
                "registra si se debió a duelos aislados o falta de soporte del equipo."
            )
            practical_change = (
                "Sugerencia: Jugar en contacto con el segundo jugador del sitio. "
                "Si tu compañero toma contacto, asómate de inmediato dentro "
                "de los primeros 2 segundos para asegurar el re-frag."
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
                "Baja conversión de eliminaciones a rondas ganadas. Sin telemetría de "
                "eventos por ronda, no es posible confirmar si las bajas generaron "
                "ventaja temprana o si ocurrieron tarde en la ronda ('exit frags') o "
                "tras plantar la Spike (post-plant)."
            )
            practical_change = (
                "Sugerencia: Priorizar el control de mapa y el tiempo de la Spike en "
                "post-plant en lugar de buscar duelos finales en solitario."
            )
            drill = (
                "Revisión de rondas post-plant: comprobar posición cruzada con el "
                "equipo en situaciones con Spike plantada."
            )
        else:
            diagnosis = (
                f"Rendimiento sólido y equilibrado (K/D {kd_ratio}, "
                f"KDA {kda_ratio}). Fundamentos consistentes en combate."
            )
            main_mistake = (
                "Sin errores críticos de combate evidentes únicamente a partir del "
                "marcador global."
            )
            practical_change = (
                "Sugerencia: Mantener la disciplina en duelos de apertura y "
                "coordinar utilidad en rondas clave."
            )
            drill = (
                "Práctica de rutinas de calentamiento de 10-15 minutos en The Range "
                "enfocada en colocación de mira a primer disparo."
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

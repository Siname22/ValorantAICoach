from typing import Any

from agents.shared.base_agent import BaseAgent
from agents.shared.context import AgentContext
from agents.shared.registry import AgentRegistry

from .schema import EconomyCoachInput, EconomyCoachOutput


class EconomyCoachAgent(BaseAgent[EconomyCoachInput, EconomyCoachOutput]):
    """Specialized agent analyzing team economy and buy discipline.

    Focuses on Gold/Platinum financial habits: avoiding force-buying on eco
    rounds, aligning with team economy, and guaranteeing 3900+ credits for
    full-buy rounds.
    """

    def __init__(self) -> None:
        super().__init__(name="Economy Coach")

    async def run(
        self, data: EconomyCoachInput, context: AgentContext
    ) -> EconomyCoachOutput:
        match_data = data.match_data
        player_stats = data.player_stats or {}

        rounds: list[dict[str, Any]] = (
            match_data.get("round_results") or match_data.get("rounds") or []
        )

        eco_rounds_detected = 0
        force_buys_detected = 0
        full_buys_detected = 0
        evidence: list[dict[str, Any]] = []

        if rounds:
            for round_idx, r in enumerate(rounds, start=1):
                loadout_val = r.get("loadout_value", 0)
                remaining_cred = r.get("remaining_credits", 0)
                buy_type = r.get("buy_type")

                if buy_type == "eco" or (loadout_val > 0 and loadout_val < 2000):
                    eco_rounds_detected += 1
                elif buy_type == "force" or (
                    loadout_val >= 2000 and loadout_val < 3900
                ):
                    force_buys_detected += 1
                    if remaining_cred < 500:
                        evidence.append(
                            {
                                "round": round_idx,
                                "type": "force_buy_risk",
                                "loadout": loadout_val,
                                "remaining": remaining_cred,
                            }
                        )
                elif buy_type == "full" or loadout_val >= 3900:
                    full_buys_detected += 1

        total_analyzed = eco_rounds_detected + force_buys_detected + full_buys_detected

        if total_analyzed > 0:
            force_ratio = force_buys_detected / total_analyzed
            buy_discipline = round(max(10.0, 100.0 - (force_ratio * 70.0)), 1)
            economy_rating = round(min(98.0, 60.0 + (buy_discipline * 0.35)), 1)
        else:
            win_pct = float(player_stats.get("win_pct", 50.0))
            buy_discipline = round(max(30.0, min(95.0, win_pct * 1.4)), 1)
            economy_rating = round(max(40.0, min(90.0, 50.0 + (win_pct * 0.4))), 1)

        if buy_discipline < 60.0 or force_buys_detected > 3:
            main_mistake = (
                "Comprar individualmente en rondas donde tu equipo necesita ahorrar, "
                "rompiendo la sincronía económica."
            )
            practical_rule = (
                "Si la media de créditos de tu equipo es menor a 3.300, ahorra "
                "(pistola base o Sheriff) para asegurar Vandal/Phantom + escudo "
                "completo en la siguiente."
            )
            drill = (
                "Regla de los 3 segundos en Menú B: Antes de comprar, mira la columna "
                "derecha de créditos de tu equipo. Si 2 o más compañeros están en eco, "
                "no compres."
            )
        else:
            main_mistake = (
                "Invertir en exceso de habilidades o escudos pesados en rondas bonus, "
                "sacrificando el banco para la ronda armada."
            )
            practical_rule = (
                "Mantén un remanente mínimo de 3.900 créditos proyectados para la "
                "siguiente ronda si tu equipo planea compra completa."
            )
            drill = (
                "Monitoreo de 'Mínimo próxima ronda': Revisa siempre el número debajo "
                "de tus créditos en el menú de compra antes de cerrar tu loadout."
            )

        evidence.append(
            {
                "buy_discipline": buy_discipline,
                "economy_rating": economy_rating,
                "eco_rounds": eco_rounds_detected,
                "force_buys": force_buys_detected,
                "full_buys": full_buys_detected,
            }
        )

        return EconomyCoachOutput(
            economy_rating=economy_rating,
            buy_discipline_score=buy_discipline,
            main_mistake=main_mistake,
            practical_rule=practical_rule,
            drill=drill,
            evidence=evidence,
        )


if "economy_coach" not in AgentRegistry.list():
    AgentRegistry.register("economy_coach", EconomyCoachAgent)

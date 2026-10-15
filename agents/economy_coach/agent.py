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

        rounds: list[dict[str, Any]] = (
            match_data.get("round_results") or match_data.get("rounds") or []
        )

        eco_rounds_detected = 0
        force_buys_detected = 0
        semi_buys_detected = 0
        full_buys_detected = 0
        force_buy_remainings: list[int] = []
        semi_buy_remainings: list[int] = []
        evidence: list[dict[str, Any]] = []

        if rounds:
            for round_idx, r in enumerate(rounds, start=1):
                loadout_val = r.get("loadout_value", 0)
                remaining_cred = r.get("remaining_credits", 0)
                buy_type = r.get("buy_type")

                if buy_type == "eco" or (loadout_val > 0 and loadout_val < 2000):
                    eco_rounds_detected += 1
                elif buy_type == "full" or loadout_val >= 3900:
                    full_buys_detected += 1
                elif buy_type == "force" or (
                    loadout_val >= 2000 and loadout_val < 3900 and remaining_cred < 1000
                ):
                    force_buys_detected += 1
                    force_buy_remainings.append(remaining_cred)
                    if remaining_cred < 500:
                        evidence.append(
                            {
                                "round": round_idx,
                                "type": "force_buy_risk",
                                "loadout": loadout_val,
                                "remaining": remaining_cred,
                            }
                        )
                elif loadout_val >= 2000 and loadout_val < 3900:
                    semi_buys_detected += 1
                    semi_buy_remainings.append(remaining_cred)

        total_analyzed = (
            eco_rounds_detected
            + force_buys_detected
            + semi_buys_detected
            + full_buys_detected
        )

        if total_analyzed >= 2:
            force_ratio = force_buys_detected / total_analyzed
            buy_discipline = round(max(10.0, 100.0 - (force_ratio * 70.0)), 1)
            economy_rating = round(min(98.0, 60.0 + (buy_discipline * 0.35)), 1)

            if force_buys_detected > 0 and (
                buy_discipline < 60.0 or force_buys_detected > 2
            ):
                avg_rem = round(sum(force_buy_remainings) / len(force_buy_remainings))
                main_mistake = (
                    f"Compras forzadas detectadas en {force_buys_detected} rondas "
                    f"con loadout intermedio y bajo remanente de créditos "
                    f"(media de {avg_rem} créditos restantes)."
                )
                practical_rule = (
                    "Si la media de créditos de tu equipo es menor a 3.300, ahorra "
                    "(pistola base o Sheriff) para asegurar Vandal/Phantom + escudo "
                    "completo en la siguiente."
                )
                drill = (
                    "Regla de los 3 segundos en Menú B: Antes de comprar, mira "
                    "la columna derecha de créditos de tu equipo. Si 2 o más "
                    "compañeros están en eco, no compres."
                )
            elif force_buys_detected == 0 and semi_buys_detected > 0:
                avg_rem = round(sum(semi_buy_remainings) / len(semi_buy_remainings))
                main_mistake = (
                    "Sin compras forzadas con saldo comprometido; se registraron "
                    f"{semi_buys_detected} compras intermedias conservando reservas "
                    f"(media de {avg_rem} créditos restantes)."
                )
                practical_rule = (
                    "Con reservas altas (3.900+ créditos), priorizar compra "
                    "completa (Vandal/Phantom + escudo) si el equipo compra completo."
                )
                drill = (
                    "Alinear loadout con el equipo: si dispones de más de 3.900 "
                    "créditos tras comprar, equipa rifle principal en rondas armadas."
                )
            elif force_buys_detected > 0:
                avg_rem = round(sum(force_buy_remainings) / len(force_buy_remainings))
                main_mistake = (
                    f"Compra forzada aislada en {force_buys_detected} ronda(s) "
                    f"({avg_rem} créditos restantes); en general buena disciplina."
                )
                practical_rule = (
                    "Mantén un remanente mínimo de 3.900 créditos proyectados para la "
                    "siguiente ronda si tu equipo planea compra completa."
                )
                drill = (
                    "Revisar los créditos de tu equipo en el menú de compra antes "
                    "de decidir el loadout."
                )
            else:
                main_mistake = (
                    "Sin compras forzadas recurrentes en el loadout analizado; "
                    "como sugerencia: vigilar la inversión en rondas bonus para "
                    "no comprometer la compra completa."
                )
                practical_rule = (
                    "Mantén un remanente mínimo de 3.900 créditos proyectados para la "
                    "siguiente ronda si tu equipo planea compra completa."
                )
                drill = (
                    "Monitoreo de 'Mínimo próxima ronda': Revisa siempre el "
                    "número debajo de tus créditos en el menú de compra antes "
                    "de cerrar tu loadout."
                )

            evidence_summary: dict[str, Any] = {
                "buy_discipline": buy_discipline,
                "economy_rating": economy_rating,
                "eco_rounds": eco_rounds_detected,
                "force_buys": force_buys_detected,
                "semi_buys": semi_buys_detected,
                "full_buys": full_buys_detected,
            }
            if force_buy_remainings:
                evidence_summary["avg_force_buy_remaining"] = round(
                    sum(force_buy_remainings) / len(force_buy_remainings), 1
                )
            if semi_buy_remainings:
                evidence_summary["avg_semi_buy_remaining"] = round(
                    sum(semi_buy_remainings) / len(semi_buy_remainings), 1
                )
            evidence.append(evidence_summary)
        else:
            buy_discipline = None
            economy_rating = None
            main_mistake = (
                "Muestra de una sola ronda; insuficiente para evaluar la "
                "disciplina económica global de la partida."
                if total_analyzed == 1
                else (
                    "Información económica de rondas no disponible en los "
                    "datos de la partida."
                )
            )
            practical_rule = (
                "Mantén un remanente mínimo de 3.900 créditos proyectados para "
                "asegurar compra completa con tu equipo."
            )
            drill = (
                "Revisar el menú de compra al inicio de cada ronda para "
                "coordinar compras completas y rondas de ahorro con el equipo."
            )
            evidence.append(
                {
                    "status": "insufficient_data",
                    "reason": (
                        f"Muestra insuficiente ({total_analyzed} ronda(s)); se "
                        "requieren múltiples rondas para evaluar sincronía económica."
                        if total_analyzed == 1
                        else "No round-by-round economy data recorded for this match."
                    ),
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

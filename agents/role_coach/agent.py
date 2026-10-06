from typing import Any

from backend.app.content.catalog import get_agent_info, resolve_agent_name

from agents.shared.base_agent import BaseAgent
from agents.shared.context import AgentContext
from agents.shared.registry import AgentRegistry

from .schema import RoleCoachInput, RoleCoachOutput

ROLE_FEEDBACK: dict[str, dict[str, str]] = {
    "Duelist": {
        "main_mistake": (
            "Buscar duelos de entrada de forma aislada sin coordinar trades ni "
            "esperar la utilidad de tu iniciador."
        ),
        "tactical_adaptation": (
            "Sé el primero en traspasar el humo o cuello de botella tras el flash, "
            "comunicando tu ruta para que tu equipo tradee tu muerte de inmediato."
        ),
        "drill": (
            "Práctica de Entry en Partida Personalizada: Entra al punto A/B "
            "limpiando únicamente los dos ángulos primarios con pre-fire."
        ),
    },
    "Controller": {
        "main_mistake": (
            "Colocar humos demasiado temprano al inicio de ronda o morir primero, "
            "dejando a tu equipo sin control de visión."
        ),
        "tactical_adaptation": (
            "Guarda al menos un humo para el momento exacto del plantado o "
            "para retrasar el retake rival. Juega en posiciones de segundo contacto."
        ),
        "drill": (
            "Sincronización de humos: Espera la confirmación de contacto o dron "
            "antes de quemar tus habilidades principales."
        ),
    },
    "Initiator": {
        "main_mistake": (
            "Gastar la utilidad de reconocimiento sin compañeros posicionados para "
            "capitalizar la información obtenida."
        ),
        "tactical_adaptation": (
            "Coordina con tu duelista con una cuenta regresiva de 3 segundos antes "
            "de lanzar tu flecha, flash o perro."
        ),
        "drill": (
            "Práctica de Recon + Trade: Lanza tu habilidad y mantente listo a 5 metros "
            "de tu entry para conseguir la baja asistida."
        ),
    },
    "Sentinel": {
        "main_mistake": (
            "Pikear agresivamente en defensa antes de que los atacantes activen "
            "tus trampas o cables, regalando la primera sangre."
        ),
        "tactical_adaptation": (
            "Ancla el sitio pacientemente y juega exclusivamente tras el sonido o "
            "activación de tu utilidad defensiva."
        ),
        "drill": (
            "Ejercicio de Retención: Mantente vivo en el sitio hasta que tus "
            "compañeros de rotación lleguen al cuello de botella."
        ),
    },
}

DEFAULT_FEEDBACK = {
    "main_mistake": (
        "Falta de sincronización táctica entre tus habilidades y tu posicionamiento."
    ),
    "tactical_adaptation": (
        "Utiliza tu utilidad para ganar ventaja antes de tomar duelos directos."
    ),
    "drill": (
        "Revisa tus repeticiones para verificar si moriste con habilidades sin usar."
    ),
}


class RoleCoachAgent(BaseAgent[RoleCoachInput, RoleCoachOutput]):
    """Specialized agent analyzing agent-specific mastery and role fulfillment.

    Tailors tactical guidance to the 4 canonical roles (Duelist, Controller,
    Initiator, Sentinel).
    """

    def __init__(self) -> None:
        super().__init__(name="Role Coach")

    async def run(self, data: RoleCoachInput, context: AgentContext) -> RoleCoachOutput:
        agent_raw = data.agent_name
        info = get_agent_info(agent_raw)
        if info:
            resolved_name = info.name
            detected_role = info.role
        else:
            resolved_name = resolve_agent_name(agent_raw)
            detected_role = None

        role = data.role or detected_role or "Flex"
        match_data = data.match_data
        player_stats = data.player_stats or {}

        kills = int(match_data.get("kills", player_stats.get("kills", 12)))
        deaths = int(match_data.get("deaths", player_stats.get("deaths", 10)))
        assists = int(match_data.get("assists", player_stats.get("assists", 4)))

        # Calculate a baseline role performance metric
        if role == "Duelist":
            # Duelists reward high kill involvement and positive combat impact
            ratio = kills / max(1, deaths)
            role_score = round(min(95.0, max(25.0, 50.0 + (ratio * 25.0))), 1)
        elif role in ("Initiator", "Controller"):
            # Utility roles reward assist ratio and longevity
            assist_rate = assists / max(1, (kills + assists))
            role_score = round(min(95.0, max(30.0, 55.0 + (assist_rate * 50.0))), 1)
        else:  # Sentinel
            # Sentinels reward stability and low deaths
            death_impact = max(0, 15 - deaths)
            role_score = round(min(95.0, max(35.0, 50.0 + (death_impact * 2.5))), 1)

        feedback = ROLE_FEEDBACK.get(role, DEFAULT_FEEDBACK)

        evidence: list[dict[str, Any]] = [
            {
                "agent": resolved_name,
                "role": role,
                "role_score": role_score,
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
            }
        ]

        return RoleCoachOutput(
            agent_name=resolved_name,
            role=role,
            role_score=role_score,
            main_mistake=feedback["main_mistake"],
            tactical_adaptation=feedback["tactical_adaptation"],
            drill=feedback["drill"],
            evidence=evidence,
        )


if "role_coach" not in AgentRegistry.list():
    AgentRegistry.register("role_coach", RoleCoachAgent)

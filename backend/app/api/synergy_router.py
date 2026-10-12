from __future__ import annotations

import logging
from typing import Annotated

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.synergy_schemas import (
    CompositionSynergyRequest,
    CompositionSynergyResponse,
    CounterPickRequest,
    CounterPickResponse,
)
from backend.app.services.player_service import PlayerService
from backend.app.services.synergy_service import SynergyService
from fastapi import APIRouter, Depends, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recommendations"])


def get_synergy_service() -> SynergyService:
    """Dependency provider for SynergyService."""
    return SynergyService()


SynergyServiceDep = Annotated[SynergyService, Depends(get_synergy_service)]
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]


@router.post(
    "/recommendations/composition/synergy",
    response_model=CompositionSynergyResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate team composition synergy",
    description=(
        "Analyze role balance, utility coverage, and map affinity for a "
        "1-5 agent composition."
    ),
)
async def evaluate_composition_synergy_endpoint(
    payload: CompositionSynergyRequest,
    service: SynergyServiceDep,
) -> CompositionSynergyResponse:
    return service.evaluate_composition_synergy(
        map_name=payload.map_name,
        allied_agents=payload.allied_agents,
        enemy_agents=payload.enemy_agents,
    )


@router.post(
    "/recommendations/counter-picks",
    response_model=CounterPickResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend agent counter-picks",
    description=(
        "Rank agent selections based on ability to counter enemy picks "
        "and map suitability."
    ),
)
async def recommend_counter_picks_endpoint(
    payload: CounterPickRequest,
    service: SynergyServiceDep,
) -> CounterPickResponse:
    return service.recommend_counter_picks(
        map_name=payload.map_name,
        enemy_agents=payload.enemy_agents,
        allied_agents=payload.allied_agents,
    )


MapNameQuery = Annotated[str, Query(description="Map name (e.g. Ascent, Bind)")]
EnemyAgentsQuery = Annotated[
    list[str], Query(description="List of enemy agents to counter")
]
AlliedAgentsQuery = Annotated[
    list[str], Query(description="List of agents already picked by allies")
]


@router.get(
    "/players/{game_name}/{tag_line}/counter-picks",
    response_model=CounterPickResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personalized agent counter-pick recommendations",
    description=(
        "Recommend counter-picks personalized with the player's historical "
        "mastery on each agent."
    ),
)
async def get_player_counter_picks_endpoint(
    game_name: str,
    tag_line: str,
    map_name: MapNameQuery,
    service: SynergyServiceDep,
    player_service: PlayerServiceDep,
    enemy_agents: EnemyAgentsQuery = (),
    allied_agents: AlliedAgentsQuery = (),
) -> CounterPickResponse:
    history_matches: list[dict] = []
    try:
        matches = await player_service.get_recent_matches(game_name, tag_line, limit=15)
        history_matches = [m.model_dump(mode="json") for m in matches]
    except Exception as exc:
        logger.warning(
            "Could not fetch match history for player %s#%s: %s",
            game_name,
            tag_line,
            exc,
        )

    return service.recommend_counter_picks(
        map_name=map_name,
        enemy_agents=list(enemy_agents),
        allied_agents=list(allied_agents),
        player_history_matches=history_matches,
    )

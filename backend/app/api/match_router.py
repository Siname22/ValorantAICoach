from typing import Annotated, Any

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.timeline_schemas import MatchTimelineResponse
from backend.app.services.player_service import PlayerService
from fastapi import APIRouter, Depends, Path, Query

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get(
    "/{match_id}",
    summary="Get Riot match details",
    description="Returns the full Riot match payload, using the configured Riot shard.",
    responses={
        404: {"description": "Match not found"},
        503: {"description": "Riot provider is not configured or available"},
    },
)
async def get_match_details(
    match_id: Annotated[str, Path(min_length=1, max_length=128, pattern=r".*\S.*")],
    service: Annotated[PlayerService, Depends(get_player_service)],
) -> dict[str, Any]:
    return await service.get_match(match_id)


@router.get(
    "/{match_id}/timeline",
    response_model=MatchTimelineResponse,
    summary="Get match round-by-round replay timeline",
    description=(
        "Analyzes the match round-by-round: kill events, trade kills, "
        "Spike plants/defuses, economies, clutches, anti-eco throws, "
        "and tactical takeaways."
    ),
    responses={
        404: {"description": "Match not found"},
        503: {"description": "Riot provider or storage is not configured or available"},
    },
)
async def get_match_timeline(
    match_id: Annotated[str, Path(min_length=1, max_length=128, pattern=r".*\S.*")],
    service: Annotated[PlayerService, Depends(get_player_service)],
    player: Annotated[
        str | None,
        Query(description="Player PUUID or name to orient friendly team analysis"),
    ] = None,
) -> MatchTimelineResponse:
    return await service.get_match_timeline(match_id, player_identifier=player)

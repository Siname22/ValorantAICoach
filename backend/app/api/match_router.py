from typing import Annotated, Any

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.services.player_service import PlayerService
from fastapi import APIRouter, Depends, Path

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

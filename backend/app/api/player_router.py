from typing import Annotated, Literal

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.player_schemas import (
    PlayerMatchesResponse,
    PlayerMatchResponse,
    PlayerProfileResponse,
    PlayerRankResponse,
)
from backend.app.services.player_service import PlayerService
from fastapi import APIRouter, Depends, Path, Query

router = APIRouter(prefix="/players", tags=["players"])

GameName = Annotated[str, Path(min_length=1, max_length=64, pattern=r".*\S.*")]
TagLine = Annotated[str, Path(min_length=1, max_length=16, pattern=r".*\S.*")]
Region = Literal["eu", "na", "ap", "kr", "br", "latam"]
Service = Annotated[PlayerService, Depends(get_player_service)]
RegionQuery = Annotated[
    Region | None,
    Query(description="Henrik region override; otherwise resolved from the account"),
]
ERROR_RESPONSES = {
    404: {"description": "Resource not found by all applicable providers"},
    502: {"description": "Player data could not be processed"},
    503: {"description": "No supported provider is configured or available"},
}


@router.get(
    "/{game_name}/{tag_line}",
    response_model=PlayerProfileResponse,
    summary="Get complete player profile",
    responses=ERROR_RESPONSES,
)
async def get_player_profile(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
) -> PlayerProfileResponse:
    profile = await service.get_complete_player_profile(game_name, tag_line)
    return PlayerProfileResponse(**profile.model_dump())


@router.get(
    "/{game_name}/{tag_line}/rank",
    response_model=PlayerRankResponse,
    summary="Get player rank",
    description="Current rank from Tracker or Henrik; Riot does not expose player RR.",
    responses=ERROR_RESPONSES,
)
async def get_player_rank(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    region: RegionQuery = None,
) -> PlayerRankResponse:
    rank = await service.get_rank(game_name, tag_line, region=region)
    return PlayerRankResponse(**rank.model_dump())


@router.get(
    "/{game_name}/{tag_line}/matches",
    response_model=PlayerMatchesResponse,
    summary="Get recent matches",
    responses=ERROR_RESPONSES,
)
async def get_player_matches(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    region: RegionQuery = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> PlayerMatchesResponse:
    matches = await service.get_recent_matches(
        game_name, tag_line, region=region, limit=limit
    )
    return PlayerMatchesResponse(
        matches=[PlayerMatchResponse(**match.model_dump()) for match in matches],
        count=len(matches),
    )

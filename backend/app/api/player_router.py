from typing import Annotated

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.player_schemas import (
    PlayerMatchesResponse,
    PlayerMatchResponse,
    PlayerProfileResponse,
    PlayerRankResponse,
)
from backend.app.services.player_service import (
    PlayerNotFoundError,
    PlayerService,
    PlayerServiceError,
)
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/players", tags=["players"])


@router.get(
    "/{game_name}/{tag_line}",
    response_model=PlayerProfileResponse,
    summary="Get complete player profile",
    description=(
        "Fetches a unified player profile including identity, level, and rank "
        "by aggregating data from multiple providers."
    ),
    response_description="The enriched player profile data",
    responses={
        200: {"description": "Player profile found and returned"},
        404: {"description": "Player not found across any provider"},
        500: {"description": "Internal error while processing player data"},
    },
)
async def get_player_profile(
    game_name: str,
    tag_line: str,
    service: Annotated[PlayerService, Depends(get_player_service)],
):
    """
    Get complete player profile including rank and identity.
    """
    try:
        profile = await service.get_complete_player_profile(game_name, tag_line)
        return PlayerProfileResponse(**profile.model_dump())
    except PlayerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PlayerServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get(
    "/{game_name}/{tag_line}/rank",
    response_model=PlayerRankResponse,
    summary="Get player rank",
    description=(
        "Retrieves the current competitive rank for a player, "
        "using fallback strategy between providers."
    ),
    response_description="The player's current rank information",
    responses={
        200: {"description": "Player rank found and returned"},
        404: {"description": "Rank information not found for the player"},
        500: {"description": "Internal error while fetching rank"},
    },
)
async def get_player_rank(
    game_name: str,
    tag_line: str,
    service: Annotated[PlayerService, Depends(get_player_service)],
):
    """
    Get player's current competitive rank.
    """
    try:
        rank = await service.get_rank(game_name, tag_line)
        return PlayerRankResponse(**rank.model_dump())
    except PlayerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PlayerServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rank: {str(e)}",
        ) from e


@router.get(
    "/{game_name}/{tag_line}/matches",
    response_model=PlayerMatchesResponse,
    summary="Get recent matches",
    description=(
        "Fetches a list of recent matches for the player, "
        "normalized across different providers."
    ),
    response_description="A list of recent match summaries",
    responses={
        200: {"description": "Match history retrieved successfully"},
        500: {"description": "Internal error while fetching match history"},
    },
)
async def get_player_matches(
    game_name: str,
    tag_line: str,
    service: Annotated[PlayerService, Depends(get_player_service)],
):
    """
    Get player's recent match history.
    """
    try:
        matches = await service.get_recent_matches(game_name, tag_line)
        return PlayerMatchesResponse(
            matches=[PlayerMatchResponse(**m.model_dump()) for m in matches],
            count=len(matches),
        )
    except PlayerServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch matches: {str(e)}",
        ) from e

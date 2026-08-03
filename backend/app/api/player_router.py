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


@router.get("/{game_name}/{tag_line}", response_model=PlayerProfileResponse)
async def get_player_profile(
    game_name: str,
    tag_line: str,
    service: Annotated[PlayerService, Depends(get_player_service)],
):
    """
    Get complete player profile including rank and identity.
    """
    try:
        return await service.get_complete_player_profile(game_name, tag_line)
    except PlayerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PlayerServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/{game_name}/{tag_line}/rank", response_model=PlayerRankResponse)
async def get_player_rank(
    game_name: str,
    tag_line: str,
    service: Annotated[PlayerService, Depends(get_player_service)],
):
    """
    Get player's current competitive rank.
    """
    try:
        return await service.get_rank(game_name, tag_line)
    except PlayerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rank: {str(e)}",
        ) from e


@router.get("/{game_name}/{tag_line}/matches", response_model=PlayerMatchesResponse)
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch matches: {str(e)}",
        ) from e

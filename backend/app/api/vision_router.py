from __future__ import annotations

import logging
from typing import Annotated

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.vision_schemas import (
    ScoreboardAnalysisResponse,
    ScoreboardIngestRequest,
)
from backend.app.services.player_service import PlayerService
from backend.app.services.vision_service import (
    InvalidImageError,
    ScoreboardVisionService,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vision"])


def get_vision_service() -> ScoreboardVisionService:
    """Dependency provider for ScoreboardVisionService."""
    return ScoreboardVisionService()


VisionServiceDep = Annotated[ScoreboardVisionService, Depends(get_vision_service)]
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]


@router.post(
    "/vision/scoreboard/analyze",
    response_model=ScoreboardAnalysisResponse,
    summary="Analyze match scoreboard screenshot via Computer Vision / OCR",
    description=(
        "Extracts structured match results, round counts, player rows, and "
        "tactical takeaways from a Valorant match scoreboard image."
    ),
)
async def analyze_scoreboard(
    request: ScoreboardIngestRequest,
    vision_service: VisionServiceDep,
    player_service: PlayerServiceDep,
) -> ScoreboardAnalysisResponse:
    try:
        analysis = await vision_service.extract_scoreboard(
            request.image_base64,
            target_game_name=request.game_name,
            target_tag_line=request.tag_line,
        )
    except InvalidImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from None
    except Exception as err:
        logger.warning("Scoreboard extraction failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scoreboard analysis failed: {err}",
        ) from None

    if request.save_to_history and request.game_name and request.tag_line:
        player_match = vision_service.convert_to_player_match(
            analysis, request.game_name, request.tag_line
        )
        saved = await player_service.ingest_vision_match(
            player_match, request.game_name, request.tag_line
        )
        analysis.persisted_as_match = saved

    return analysis


@router.post(
    "/vision/scoreboard/upload",
    response_model=ScoreboardAnalysisResponse,
    summary="Upload match scoreboard image file directly",
)
async def upload_scoreboard_file(
    file: Annotated[UploadFile, File(description="Scoreboard image file")],
    vision_service: VisionServiceDep,
    player_service: PlayerServiceDep,
    game_name: Annotated[str | None, Form()] = None,
    tag_line: Annotated[str | None, Form()] = None,
    save_to_history: Annotated[bool, Form()] = True,
) -> ScoreboardAnalysisResponse:
    try:
        file_bytes = await file.read()
        analysis = await vision_service.extract_scoreboard(
            file_bytes,
            target_game_name=game_name,
            target_tag_line=tag_line,
        )
    except InvalidImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from None
    except Exception as err:
        logger.warning("File scoreboard extraction failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scoreboard analysis failed: {err}",
        ) from None

    if save_to_history and game_name and tag_line:
        player_match = vision_service.convert_to_player_match(
            analysis, game_name, tag_line
        )
        saved = await player_service.ingest_vision_match(
            player_match, game_name, tag_line
        )
        analysis.persisted_as_match = saved

    return analysis


@router.post(
    "/players/{game_name}/{tag_line}/scoreboard",
    response_model=ScoreboardAnalysisResponse,
    summary="Analyze and ingest scoreboard screenshot for a specific player",
)
async def ingest_player_scoreboard(
    game_name: str,
    tag_line: str,
    request: ScoreboardIngestRequest,
    vision_service: VisionServiceDep,
    player_service: PlayerServiceDep,
) -> ScoreboardAnalysisResponse:
    # Ensure target player is bound from route parameters
    request.game_name = game_name
    request.tag_line = tag_line
    return await analyze_scoreboard(
        request=request,
        vision_service=vision_service,
        player_service=player_service,
    )

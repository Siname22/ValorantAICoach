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
    VisionExtractionError,
    VisionUnavailableError,
)
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    UploadFile,
    status,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vision"])

GameName = Annotated[str, Path(min_length=1, max_length=64, pattern=r".*\S.*")]
TagLine = Annotated[str, Path(min_length=1, max_length=16, pattern=r".*\S.*")]

VISION_RESPONSES = {
    400: {"description": "Invalid or unsupported image"},
    422: {"description": "The image could not be read as a complete scoreboard"},
    503: {"description": "No vision model is configured or reachable"},
}


def get_vision_service() -> ScoreboardVisionService:
    """Dependency provider for ScoreboardVisionService."""
    return ScoreboardVisionService()


VisionServiceDep = Annotated[ScoreboardVisionService, Depends(get_vision_service)]
PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]


async def _analyze_and_maybe_save(
    image: str | bytes,
    vision_service: ScoreboardVisionService,
    player_service: PlayerService,
    *,
    game_name: str | None,
    tag_line: str | None,
    save_to_history: bool,
) -> ScoreboardAnalysisResponse:
    try:
        analysis = await vision_service.extract_scoreboard(
            image, target_game_name=game_name, target_tag_line=tag_line
        )
    except InvalidImageError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(err)) from None
    except VisionUnavailableError as err:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err)
        ) from None
    except VisionExtractionError as err:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err)
        ) from None
    except Exception as err:
        logger.warning("Scoreboard extraction failed: %s", type(err).__name__)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scoreboard analysis failed unexpectedly.",
        ) from None

    if not save_to_history:
        return analysis
    if not (game_name and tag_line):
        analysis.persistence_note = "A player name and tag are required to save."
        return analysis
    try:
        player_match = vision_service.convert_to_player_match(
            analysis, game_name, tag_line
        )
    except VisionExtractionError as err:
        analysis.persistence_note = str(err)
        return analysis

    saved = await player_service.ingest_vision_match(player_match, game_name, tag_line)
    analysis.persisted_as_match = saved
    if not saved:
        analysis.persistence_note = "Persistent storage is not enabled."
    return analysis


@router.post(
    "/vision/scoreboard/analyze",
    response_model=ScoreboardAnalysisResponse,
    summary="Read a match scoreboard screenshot with a vision model",
    description=(
        "Extracts match result, rounds and visible player rows from a VALORANT "
        "scoreboard image. Fails explicitly when the image cannot be read; no "
        "values are estimated."
    ),
    responses=VISION_RESPONSES,
)
async def analyze_scoreboard(
    request: ScoreboardIngestRequest,
    vision_service: VisionServiceDep,
    player_service: PlayerServiceDep,
) -> ScoreboardAnalysisResponse:
    return await _analyze_and_maybe_save(
        request.image_base64,
        vision_service,
        player_service,
        game_name=request.game_name,
        tag_line=request.tag_line,
        save_to_history=request.save_to_history,
    )


@router.post(
    "/vision/scoreboard/upload",
    response_model=ScoreboardAnalysisResponse,
    summary="Upload match scoreboard image file directly",
    responses=VISION_RESPONSES,
)
async def upload_scoreboard_file(
    file: Annotated[UploadFile, File(description="Scoreboard image file")],
    vision_service: VisionServiceDep,
    player_service: PlayerServiceDep,
    game_name: Annotated[str | None, Form()] = None,
    tag_line: Annotated[str | None, Form()] = None,
    save_to_history: Annotated[bool, Form()] = True,
) -> ScoreboardAnalysisResponse:
    file_bytes = await file.read()
    return await _analyze_and_maybe_save(
        file_bytes,
        vision_service,
        player_service,
        game_name=game_name,
        tag_line=tag_line,
        save_to_history=save_to_history,
    )


@router.post(
    "/players/{game_name}/{tag_line}/scoreboard",
    response_model=ScoreboardAnalysisResponse,
    summary="Read and ingest a scoreboard screenshot for a specific player",
    responses=VISION_RESPONSES,
)
async def ingest_player_scoreboard(
    game_name: GameName,
    tag_line: TagLine,
    request: ScoreboardIngestRequest,
    vision_service: VisionServiceDep,
    player_service: PlayerServiceDep,
) -> ScoreboardAnalysisResponse:
    return await _analyze_and_maybe_save(
        request.image_base64,
        vision_service,
        player_service,
        game_name=game_name,
        tag_line=tag_line,
        save_to_history=request.save_to_history,
    )

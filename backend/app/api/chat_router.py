"""Authenticated conversational coaching endpoint."""

from typing import Annotated, Any

from backend.app.dependencies.auth_deps import get_current_user
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.chat_schemas import ChatRequest, ChatResponse
from backend.app.services.chat_service import (
    ChatProviderError,
    ChatService,
    ChatTemporaryError,
    ChatUnavailableError,
    get_chat_service,
)
from backend.app.services.player_service import PlayerService
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _user: Annotated[dict[str, Any], Depends(get_current_user)],
    players: Annotated[PlayerService, Depends(get_player_service)],
    coach: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    context = None
    if request.player is not None:
        selected = request.player
        profile = await players.get_complete_player_profile(
            selected.game_name, selected.tag_line, region=selected.region
        )
        if profile.region is None or profile.region.lower() != selected.region:
            raise HTTPException(status_code=404, detail="Player not found in region.")
        matches = await players.get_recent_matches(
            selected.game_name,
            selected.tag_line,
            puuid=profile.puuid,
            region=selected.region,
            limit=5,
        )
        recent = "; ".join(
            f"{item.map_name}: {item.result}, K/D/A "
            f"{item.kills}/{item.deaths}/{item.assists}"
            for item in matches
        )
        context = (
            f"Jugador verificado en {selected.region}: "
            f"{profile.game_name}#{profile.tag_line}. "
            f"Rango: {profile.rank_name or 'no disponible'}. "
            f"Partidas recientes: {recent or 'sin partidas disponibles'}."
        )
    try:
        result = await coach.reply(request.message, request.history, context)
    except ChatUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except ChatTemporaryError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except ChatProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    return ChatResponse(
        reply=result.reply, model=result.model, fallback_used=result.fallback_used
    )

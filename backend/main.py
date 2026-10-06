import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from backend import __version__
from backend.app.api.match_router import router as match_router
from backend.app.api.player_router import router as player_router
from backend.app.core.config import get_settings
from backend.app.dependencies.provider_deps import (
    create_player_service,
    get_player_service,
)
from backend.app.schemas.player_schemas import HealthResponse
from backend.app.services.player_service import (
    PlayerNotFoundError,
    PlayerService,
    PlayerServiceError,
    PlayerServiceUnavailableError,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    service = await asyncio.to_thread(create_player_service)
    application.state.player_service = service
    try:
        yield
    finally:
        await service.close()
        application.state.player_service = None


tags_metadata = [
    {"name": "matches", "description": "Full match details from the Riot API."},
    {
        "name": "players",
        "description": (
            "Operations with Valorant players, including profiles, "
            "ranks, and match history."
        ),
    },
    {
        "name": "system",
        "description": "System health and status operations.",
    },
]

app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    description=(
        "Professional Valorant AI Coach API providing aggregated data from "
        "multiple providers (Riot, Henrik, Tracker)."
    ),
    version=__version__,
    contact={
        "name": "Valorant AI Coach Team",
        "url": "https://github.com/Siname22/ValorantAICoach",
    },
    license_info={
        "name": "Proprietary",
    },
    openapi_tags=tags_metadata,
)

# Register routers
app.include_router(player_router)
app.include_router(match_router)


@app.exception_handler(PlayerServiceError)
async def handle_player_service_error(
    request: Request, error: PlayerServiceError
) -> JSONResponse:
    if isinstance(error, PlayerNotFoundError):
        status_code, detail = 404, str(error)
    elif isinstance(error, PlayerServiceUnavailableError):
        status_code, detail = 503, str(error)
    else:
        status_code, detail = 502, "Unable to retrieve player data."
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.get(
    "/",
    tags=["system"],
    summary="Root endpoint",
    description="Returns basic application information.",
)
def read_root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running"}


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
    description="Returns the health status of the application and its data providers.",
)
async def health_check(
    service: Annotated[PlayerService, Depends(get_player_service)],
) -> HealthResponse:
    """
    Checks the health of the application and all configured providers.
    """
    health_data = await service.health()
    return HealthResponse(
        status=health_data["status"],
        version=__version__,
        providers={
            name: info["status"] for name, info in health_data["providers"].items()
        },
    )


@app.get("/health/live", response_model=HealthResponse, tags=["system"])
async def liveness_check() -> HealthResponse:
    """Check the application process without querying external providers."""
    return HealthResponse(status="ok", version=__version__)

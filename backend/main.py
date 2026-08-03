from typing import Annotated

from fastapi import Depends, FastAPI

from backend.app.api.player_router import router as player_router
from backend.app.core.config import get_settings
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.player_schemas import HealthResponse
from backend.app.services.player_service import PlayerService

settings = get_settings()

tags_metadata = [
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
    title=settings.app_name,
    description=(
        "Professional Valorant AI Coach API providing aggregated data from "
        "multiple providers (Riot, Henrik, Tracker)."
    ),
    version="0.3.0",
    contact={
        "name": "Valorant AI Coach Team",
        "url": "https://github.com/Siname22/ValorantAICoach",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=tags_metadata,
)

# Register routers
app.include_router(player_router)


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
        version="0.3.0",
        providers={
            name: info["status"] for name, info in health_data["providers"].items()
        },
    )

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from backend import __version__
from backend.app.api.auth_router import router as auth_router
from backend.app.api.match_router import router as match_router
from backend.app.api.player_router import router as player_router
from backend.app.core.config import get_settings
from backend.app.dependencies.provider_deps import (
    create_player_service,
    get_player_service,
)
from backend.app.schemas.player_schemas import (
    CachePruneResponse,
    HealthResponse,
    ReadinessResponse,
)
from backend.app.services.player_service import (
    PlayerNotFoundError,
    PlayerService,
    PlayerServiceError,
    PlayerServiceUnavailableError,
)

settings = get_settings()
logger = logging.getLogger(__name__)


async def _run_cache_prune_worker(
    service: PlayerService, interval_seconds: int
) -> None:
    logger.info(
        "Starting background cache prune worker (interval=%ds)", interval_seconds
    )
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            pruned = await service.prune_expired_cache()
            if pruned > 0:
                logger.info(
                    "Background cache prune worker pruned %d expired snapshots",
                    pruned,
                )
        except asyncio.CancelledError:
            break
        except Exception:
            logger.warning("Background cache prune encountered an error", exc_info=True)


async def _run_coaching_sync_worker(
    service: PlayerService, interval_seconds: int
) -> None:
    logger.info(
        "Starting background scheduled coaching sync worker (interval=%ds)",
        interval_seconds,
    )
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            sync_result = await service.sync_all_tracked_accounts()
            count = sync_result.get("synced_accounts_count", 0)
            if count > 0:
                logger.info(
                    "Scheduled coaching worker synced %d tracked accounts", count
                )
        except asyncio.CancelledError:
            break
        except Exception:
            logger.warning(
                "Scheduled coaching sync worker encountered an error",
                exc_info=True,
            )


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    app_settings = get_settings()
    service = await asyncio.to_thread(create_player_service)
    application.state.player_service = service
    prune_task: asyncio.Task[None] | None = None
    sync_task: asyncio.Task[None] | None = None
    if (
        app_settings.database_enabled
        and app_settings.database_auto_prune_interval_seconds > 0
    ):
        prune_task = asyncio.create_task(
            _run_cache_prune_worker(
                service, app_settings.database_auto_prune_interval_seconds
            )
        )
    if (
        app_settings.database_enabled
        and app_settings.database_auto_sync_interval_seconds > 0
    ):
        sync_task = asyncio.create_task(
            _run_coaching_sync_worker(
                service, app_settings.database_auto_sync_interval_seconds
            )
        )
    try:
        yield
    finally:
        if sync_task is not None:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task
        if prune_task is not None:
            prune_task.cancel()
            with suppress(asyncio.CancelledError):
                await prune_task
        await service.close()
        application.state.player_service = None


tags_metadata = [
    {
        "name": "auth",
        "description": "User authentication, JWT tokens, and player account linking.",
    },
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
app.include_router(auth_router)
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


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["system"],
    summary="Readiness check",
    description="Returns readiness status of database and upstream providers.",
)
async def readiness_check(
    service: Annotated[PlayerService, Depends(get_player_service)],
) -> JSONResponse:
    ready_data = await service.ready()
    status_code = 200 if ready_data.get("status") in ("ready", "degraded") else 503
    return JSONResponse(status_code=status_code, content=ready_data)


@app.post(
    "/system/cache/prune",
    response_model=CachePruneResponse,
    tags=["system"],
    summary="Prune expired cache",
    description="Deletes expired snapshot cache entries from persistence.",
)
async def prune_cache(
    service: Annotated[PlayerService, Depends(get_player_service)],
) -> CachePruneResponse:
    count = await service.prune_expired_cache()
    return CachePruneResponse(pruned_count=count)


@app.post(
    "/system/coaching/sync-tracked",
    tags=["system"],
    summary="Synchronize all tracked player accounts",
    description=(
        "Forces a coaching sync across all active primary linked player accounts."
    ),
)
async def sync_tracked_coaching(
    service: Annotated[PlayerService, Depends(get_player_service)],
) -> dict[str, Any]:
    return await service.sync_all_tracked_accounts()

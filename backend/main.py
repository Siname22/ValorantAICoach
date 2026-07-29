from fastapi import FastAPI

from backend.app.api.player_router import router as player_router
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

# Register routers
app.include_router(player_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running"}

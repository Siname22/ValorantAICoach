from fastapi import FastAPI

from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running"}

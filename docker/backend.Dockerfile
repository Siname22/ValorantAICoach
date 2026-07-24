FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

# Install dependencies first (cached layer, invalidated only on lockfile change)
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-cache --no-dev

COPY alembic.ini ./
COPY backend ./backend
COPY database ./database

# Run as a non-root user (least privilege)
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

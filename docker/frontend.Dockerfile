FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

# Install frontend-only dependencies
COPY frontend/streamlit_app/requirements.txt ./requirements.txt
RUN uv venv /app/.venv && uv pip install --no-cache -r requirements.txt

COPY frontend ./frontend

# Run as a non-root user (least privilege)
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"]

CMD ["/app/.venv/bin/streamlit", "run", "frontend/streamlit_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

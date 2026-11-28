from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from backend.app.core.config import Settings
from backend.app.dependencies.auth_deps import get_current_user
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.services.chat_service import (
    ChatService,
    ChatTemporaryError,
    ChatUnavailableError,
    get_chat_service,
)
from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    player = AsyncMock()
    player.get_complete_player_profile.return_value = SimpleNamespace(
        game_name="Player", tag_line="TAG", region="eu", puuid="p", rank_name="Gold"
    )
    player.get_recent_matches.return_value = []
    app.dependency_overrides[get_player_service] = lambda: player
    try:
        with TestClient(app) as test_client:
            yield test_client, player
    finally:
        app.dependency_overrides.clear()


def test_chat_requires_authentication_and_validates_limits(client):
    http, _ = client
    assert http.post("/coach/chat", json={"message": "Hola"}).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-a"}
    assert http.post("/coach/chat", json={"message": "x" * 4001}).status_code == 422
    assert http.post("/coach/chat", json={"message": "   "}).status_code == 422
    history = [{"role": "user", "content": "hola"}] * 41
    assert (
        http.post(
            "/coach/chat", json={"message": "hola", "history": history}
        ).status_code
        == 422
    )


def test_chat_uses_server_verified_player_context(client):
    http, player = client
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-a"}
    gateway = AsyncMock()
    gateway.generate.return_value = "Consejo fundamentado"
    app.dependency_overrides[get_chat_service] = lambda: ChatService(
        gateway, models=("primary",), sleep=AsyncMock()
    )

    response = http.post(
        "/coach/chat",
        json={
            "message": "¿Qué mejorar?",
            "player": {"game_name": "Player", "tag_line": "TAG", "region": "eu"},
        },
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Consejo fundamentado"
    player.get_complete_player_profile.assert_awaited_once_with(
        "Player", "TAG", region="eu"
    )
    player.get_recent_matches.assert_awaited_once_with(
        "Player", "TAG", puuid="p", region="eu", limit=5
    )
    assert "Gold" in gateway.generate.await_args.kwargs["system_prompt"]


def test_chat_rejects_wrong_region_before_contacting_gemini(client):
    http, player = client
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-a"}
    player.get_complete_player_profile.return_value.region = "na"
    gateway = AsyncMock()
    app.dependency_overrides[get_chat_service] = lambda: ChatService(gateway)

    response = http.post(
        "/coach/chat",
        json={
            "message": "¿Qué mejorar?",
            "player": {"game_name": "Player", "tag_line": "TAG", "region": "eu"},
        },
    )
    assert response.status_code == 404
    gateway.generate.assert_not_called()
    player.get_recent_matches.assert_not_called()


def test_chat_missing_key_returns_safe_error(client):
    http, _ = client
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-a"}
    app.dependency_overrides[get_chat_service] = lambda: ChatService.from_settings(
        api_key=None
    )
    response = http.post("/coach/chat", json={"message": "Hola"})
    assert response.status_code == 503
    assert "API_KEY" not in response.text


def test_default_model_chain_avoids_retired_model_for_new_accounts(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    settings = Settings(_env_file=None)
    models = ChatService.from_settings(
        "local-placeholder", settings.gemini_model
    ).models
    assert models[0] == "gemini-3.1-flash-lite"
    assert "gemini-2.5-flash" not in models


@pytest.mark.asyncio
async def test_chat_retries_and_falls_back_without_leaking_provider_error():
    gateway = AsyncMock()
    gateway.generate.side_effect = [RuntimeError("503 private upstream body")] * 3 + [
        "Respuesta"
    ]
    service = ChatService(gateway, models=("primary", "backup"), sleep=AsyncMock())
    result = await service.reply("Hola", [], None)
    assert result.reply == "Respuesta"
    assert result.model == "backup"
    assert result.fallback_used is True
    assert gateway.generate.await_count == 4


@pytest.mark.asyncio
async def test_chat_exhaustion_and_missing_key_are_sanitized():
    gateway = AsyncMock()
    gateway.generate.side_effect = RuntimeError("503 private upstream body")
    service = ChatService(gateway, models=("primary",), sleep=AsyncMock())
    with pytest.raises(ChatTemporaryError) as error:
        await service.reply("Hola", [], None)
    assert "private upstream body" not in str(error.value)
    with pytest.raises(ChatUnavailableError):
        await ChatService.from_settings(api_key=None).reply("Hola", [], None)


@pytest.mark.asyncio
async def test_chat_auth_failure_stops_without_retry_or_secret_leak():
    gateway = AsyncMock()
    gateway.generate.side_effect = RuntimeError("401 private credential detail")
    service = ChatService(gateway, models=("primary", "backup"), sleep=AsyncMock())
    with pytest.raises(ChatUnavailableError) as error:
        await service.reply("Hola", [], None)
    assert gateway.generate.await_count == 1
    assert "private credential detail" not in str(error.value)

from unittest.mock import AsyncMock

import pytest
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.services.player_service import (
    PlayerMatch,
    PlayerNotFoundError,
    PlayerProfile,
    PlayerRank,
)
from backend.main import app
from fastapi.testclient import TestClient

# We override the dependency at the app level to avoid instantiating real providers
# which would fail due to missing environment variables/config validation.


@pytest.fixture
def mock_player_service():
    service = AsyncMock()
    app.dependency_overrides[get_player_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_get_player_profile_success(client, mock_player_service):
    # Setup
    mock_player_service.get_complete_player_profile.return_value = PlayerProfile(
        game_name="Test", tag_line="NA1", puuid="p-123", rank_name="Diamond 1"
    )

    # Execute
    response = client.get("/players/Test/NA1")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["game_name"] == "Test"
    assert data["rank_name"] == "Diamond 1"


def test_get_player_profile_not_found(client, mock_player_service):
    # Setup
    mock_player_service.get_complete_player_profile.side_effect = PlayerNotFoundError(
        "Player not found"
    )

    # Execute
    response = client.get("/players/Unknown/000")

    # Assert
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]


def test_get_player_rank_success(client, mock_player_service):
    # Setup
    mock_player_service.get_rank.return_value = PlayerRank(
        tier_name="Immortal", points=100
    )

    # Execute
    response = client.get("/players/Test/NA1/rank")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["tier_name"] == "Immortal"
    assert data["points"] == 100


def test_get_player_matches_success(client, mock_player_service):
    # Setup
    mock_player_service.get_recent_matches.return_value = [
        PlayerMatch(
            match_id="m-1",
            map_name="Ascent",
            mode="Competitive",
            timestamp=123456789,
            result="Victory",
            kills=20,
            deaths=10,
            assists=5,
            score=5000,
            agent_name="Jett",
        )
    ]

    # Execute
    response = client.get("/players/Test/NA1/matches")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["matches"][0]["match_id"] == "m-1"
    assert data["matches"][0]["agent_name"] == "Jett"

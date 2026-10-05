from unittest.mock import AsyncMock

import pytest
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.services.player_service import (
    PlayerMatch,
    PlayerNotFoundError,
    PlayerProfile,
    PlayerRank,
    PlayerServiceError,
    PlayerServiceUnavailableError,
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


def test_health_check_success(client, mock_player_service):
    # Setup
    mock_player_service.health.return_value = {
        "status": "healthy",
        "providers": {
            "tracker": {"status": "healthy"},
            "henrik": {"status": "healthy"},
            "riot": {"status": "healthy"},
        },
    }

    # Execute
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.4.0"
    assert data["providers"]["riot"] == "healthy"


@pytest.mark.parametrize("suffix", ["", "/rank", "/matches"])
def test_upstream_failure_returns_503(client, mock_player_service, suffix):
    for method in ("get_complete_player_profile", "get_rank", "get_recent_matches"):
        getattr(mock_player_service, method).side_effect = (
            PlayerServiceUnavailableError("Data provider unavailable")
        )
    response = client.get(f"/players/Test/EU1{suffix}")
    assert response.status_code == 503


def test_service_errors_do_not_expose_upstream_body(client, mock_player_service):
    mock_player_service.get_rank.side_effect = PlayerServiceError("private-api-key")
    response = client.get("/players/Test/EU1/rank")
    assert response.status_code == 502
    assert "private-api-key" not in response.text


@pytest.mark.parametrize("query", ["limit=0", "limit=21", "region=unknown"])
def test_invalid_match_query_is_rejected(client, mock_player_service, query):
    response = client.get(f"/players/Test/EU1/matches?{query}")
    assert response.status_code == 422
    mock_player_service.get_recent_matches.assert_not_awaited()


def test_match_query_reaches_service(client, mock_player_service):
    mock_player_service.get_recent_matches.return_value = []
    response = client.get("/players/Test/EU1/matches?region=eu&limit=3")
    assert response.status_code == 200
    assert response.json() == {"matches": [], "count": 0}
    mock_player_service.get_recent_matches.assert_awaited_once_with(
        "Test", "EU1", region="eu", limit=3
    )


def test_match_details_endpoint(client, mock_player_service):
    payload = {"matchInfo": {"matchId": "m-1"}, "players": [], "teams": []}
    mock_player_service.get_match.return_value = payload
    response = client.get("/matches/m-1")
    assert response.status_code == 200
    assert response.json() == payload
    mock_player_service.get_match.assert_awaited_once_with("m-1")


def test_match_details_not_found(client, mock_player_service):
    mock_player_service.get_match.side_effect = PlayerNotFoundError("Match not found")
    response = client.get("/matches/missing")
    assert response.status_code == 404


def test_blank_player_name_is_rejected(client, mock_player_service):
    mock_player_service.get_complete_player_profile.return_value = PlayerProfile(
        game_name="Test", tag_line="EU1"
    )
    response = client.get("/players/%20/EU1")
    assert response.status_code == 422
    mock_player_service.get_complete_player_profile.assert_not_awaited()

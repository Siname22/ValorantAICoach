from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.services.player_service import PlayerService
from backend.main import app
from backend.providers.base.exceptions import (
    InvalidResponseError,
    NotFoundError,
    ServerError,
)
from backend.providers.henrik.models import HenrikPlayer
from backend.providers.tracker.models import LifetimeStats, StatValue
from fastapi.testclient import TestClient


@pytest.fixture
def client_for_service():
    def build(service):
        app.dependency_overrides[get_player_service] = lambda: service
        return TestClient(app, raise_server_exceptions=False)

    yield build
    app.dependency_overrides.pop(get_player_service, None)


def test_stats_endpoint_preserves_develop_lifetime_capability(client_for_service):
    def stat(value):
        return StatValue(value=value, displayValue=str(value))

    tracker = SimpleNamespace(
        get_lifetime_stats=AsyncMock(
            return_value=LifetimeStats(
                kills=stat(100),
                deaths=stat(50),
                assists=stat(25),
                kdRatio=stat(2),
                winPct=stat(60),
                headshotPct=stat(25),
                matchesPlayed=stat(10),
                damagePerRound=stat(0),
            )
        )
    )
    with client_for_service(PlayerService(tracker_provider=tracker)) as client:
        response = client.get("/players/Test/EU1/stats")
    assert response.status_code == 200
    assert response.json() == {
        "kills": 100,
        "deaths": 50,
        "assists": 25,
        "kd_ratio": 2.0,
        "win_pct": 60.0,
        "headshot_pct": 25.0,
        "matches_played": 10,
        "damage_per_round": 0.0,
        "source": "tracker",
    }


def test_overview_keeps_identity_when_optional_data_fails(client_for_service):
    henrik = SimpleNamespace(
        get_account=AsyncMock(
            return_value=HenrikPlayer(
                puuid="h-123",
                name="Test",
                tag="EU1",
                region="eu",
                account_level=20,
            )
        ),
        get_rank=AsyncMock(side_effect=ServerError("private upstream body")),
        get_matches=AsyncMock(side_effect=ServerError("private upstream body")),
    )
    with client_for_service(PlayerService(henrik_provider=henrik)) as client:
        response = client.get("/players/Test/EU1/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["identity"]["puuid"] == "h-123"
    assert data["identity"]["source"] == "henrik"
    assert data["rank"] is None
    assert data["stats"] is None
    assert data["recent_matches"] is None
    assert set(data["unavailable_sections"]) == {"rank", "stats", "recent_matches"}
    assert "private upstream body" not in response.text


def test_stats_without_tracker_is_unavailable(client_for_service):
    with client_for_service(PlayerService()) as client:
        response = client.get("/players/Test/EU1/stats")
    assert response.status_code == 503


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kd_ratio", float("nan")),
        ("win_pct", float("inf")),
        ("kills", 12.5),
        ("kills", -1),
        ("matches_played", 1.5),
        ("kd_ratio", -1),
        ("win_pct", -1),
        ("win_pct", 101),
        ("headshot_pct", 101),
        ("damage_per_round", -1),
    ],
)
def test_invalid_stats_are_rejected_not_truncated_or_serialized(
    client_for_service, field, value
):
    stats = LifetimeStats(
        kills=StatValue(value=100, displayValue="100"),
        deaths=StatValue(value=50, displayValue="50"),
        assists=StatValue(value=25, displayValue="25"),
        kdRatio=StatValue(value=2, displayValue="2"),
        winPct=StatValue(value=60, displayValue="60"),
        headshotPct=StatValue(value=25, displayValue="25"),
    )
    setattr(stats, field, StatValue(value=value, displayValue="private input"))
    tracker = SimpleNamespace(get_lifetime_stats=AsyncMock(return_value=stats))
    with client_for_service(PlayerService(tracker_provider=tracker)) as client:
        response = client.get("/players/Test/EU1/stats")
    assert response.status_code == 502
    assert "private input" not in response.text


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (NotFoundError("private body"), 404),
        (InvalidResponseError("private body"), 502),
        (ServerError("private body"), 503),
    ],
)
def test_stats_errors_preserve_failure_class(client_for_service, failure, status):
    tracker = SimpleNamespace(get_lifetime_stats=AsyncMock(side_effect=failure))
    with client_for_service(PlayerService(tracker_provider=tracker)) as client:
        response = client.get("/players/Test/EU1/stats")
    assert response.status_code == status
    assert "private body" not in response.text


def test_overview_distinguishes_confirmed_empty_history_from_outage(client_for_service):
    henrik = SimpleNamespace(
        get_account=AsyncMock(
            return_value=HenrikPlayer(
                puuid="h-123",
                name="Test",
                tag="EU1",
                region="eu",
                account_level=20,
            )
        ),
        get_rank=AsyncMock(
            return_value=SimpleNamespace(
                tier_name="Gold 1",
                rank_icon_url=None,
                points=0,
            )
        ),
        get_matches=AsyncMock(return_value=[]),
    )
    with client_for_service(PlayerService(henrik_provider=henrik)) as client:
        response = client.get("/players/Test/EU1/overview?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["rank"]["points"] == 0
    assert data["rank"]["source"] == "henrik"
    assert data["recent_matches"] == []
    assert data["unavailable_sections"] == ["stats"]


def test_overview_not_found_does_not_fetch_optional_sections(client_for_service):
    henrik = SimpleNamespace(
        get_account=AsyncMock(side_effect=NotFoundError("private body")),
        get_rank=AsyncMock(),
        get_matches=AsyncMock(),
    )
    with client_for_service(PlayerService(henrik_provider=henrik)) as client:
        response = client.get("/players/Test/EU1/overview")
    assert response.status_code == 404
    henrik.get_rank.assert_not_awaited()
    henrik.get_matches.assert_not_awaited()
    assert "private body" not in response.text

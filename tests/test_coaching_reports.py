from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import get_settings
from backend.app.services.player_service import (
    PlayerMatch,
    PlayerService,
    PlayerServiceUnavailableError,
)
from backend.app.storage.player_service import PersistentPlayerService
from backend.app.storage.repository import SQLPlayerStore
from backend.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine


@pytest.fixture
def storage_database(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    url = f"sqlite+pysqlite:///{(tmp_path / 'coach_reports.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "database/migrations"))
    engine = create_engine(url)
    command.upgrade(config, "head")
    try:
        yield url, engine
    finally:
        engine.dispose()
        get_settings.cache_clear()


def test_sql_player_store_report_crud(storage_database):
    url, _ = storage_database
    store = SQLPlayerStore(url, ttl_seconds=300, test_mode=True)

    try:
        player_id = "test-player-id-123"
        identity = {"game_name": "Asuna", "tag_line": "100T"}
        payload = {
            "title": "Tactical Report",
            "executive_summary": "Great play",
            "training_plan": ["Drill 1"],
        }
        evidence = [{"stat": "kd", "value": 1.3}]

        # 1. Save report
        report_id = store.save_coaching_report(
            player_id,
            payload,
            evidence,
            provider="orchestrator",
            identity=identity,
        )
        assert report_id != ""

        # 2. Get report
        retrieved = store.get_coaching_report(report_id)
        assert retrieved is not None
        assert retrieved["id"] == report_id
        assert retrieved["player_id"] == player_id
        assert retrieved["provider"] == "orchestrator"
        assert retrieved["payload"]["title"] == "Tactical Report"
        assert len(retrieved["evidence"]) == 1

        # 3. List reports
        reports = store.list_coaching_reports(player_id, limit=5)
        assert len(reports) == 1
        assert reports[0]["id"] == report_id

        # 4. Non-existent report
        assert store.get_coaching_report("non-existent-id") is None
    finally:
        store.close()


@pytest.mark.asyncio
async def test_persistent_player_service_generate_and_list_reports(storage_database):
    url, _ = storage_database
    store = SQLPlayerStore(url, ttl_seconds=300, test_mode=True)

    mock_service = PersistentPlayerService(store=store)
    # Mock recent matches
    mock_matches = [
        PlayerMatch(
            match_id="match-rep-1",
            map_name="Ascent",
            mode="Competitive",
            timestamp="2026-10-06T10:00:00Z",
            result="Victory",
            kills=18,
            deaths=12,
            assists=4,
            agent_name="Jett",
            provider="riot",
        )
    ]
    mock_service.get_recent_matches = AsyncMock(return_value=mock_matches)
    mock_service.get_rank = AsyncMock(side_effect=Exception("No rank"))
    mock_service.get_stats_overview = AsyncMock(side_effect=Exception("No stats"))

    try:
        # Generate report
        report = await mock_service.generate_coaching_report("Derke", "FNC")
        assert report["id"] != ""
        assert "payload" in report
        assert "Derke#FNC" in report["payload"]["title"]

        # List reports
        history = await mock_service.list_coaching_reports("Derke", "FNC")
        assert len(history) == 1
        assert history[0]["id"] == report["id"]

        # Retrieve report by ID with correct player
        found = await mock_service.get_coaching_report(
            report["id"], game_name="Derke", tag_line="FNC"
        )
        assert found is not None
        assert found["id"] == report["id"]

        # Retrieving report with different casing succeeds (case-insensitive)
        case_insensitive = await mock_service.get_coaching_report(
            report["id"], game_name="derke", tag_line="fnc"
        )
        assert case_insensitive is not None
        assert case_insensitive["id"] == report["id"]

        # Attempting to retrieve report under another player's identity returns None
        wrong_player = await mock_service.get_coaching_report(
            report["id"], game_name="Bob", tag_line="NA1"
        )
        assert wrong_player is None
    finally:
        await mock_service.close()


def test_api_report_endpoints():
    mock_service = PlayerService()
    mock_matches = [
        PlayerMatch(
            match_id="match-api-1",
            map_name="Bind",
            mode="Competitive",
            timestamp="2026-10-06T11:00:00Z",
            result="Victory",
            kills=22,
            deaths=14,
            assists=6,
            agent_name="Raze",
            provider="riot",
        )
    ]
    mock_service.get_recent_matches = AsyncMock(return_value=mock_matches)
    mock_service.get_rank = AsyncMock(side_effect=Exception("No rank"))
    mock_service.get_stats_overview = AsyncMock(side_effect=Exception("No stats"))

    from backend.app.dependencies.auth_deps import get_current_user

    app.state.player_service = mock_service
    client = TestClient(app)

    # 1. POST /players/Boaster/FNC/reports without authentication -> 401
    unauth_resp = client.post("/players/Boaster/FNC/reports")
    assert unauth_resp.status_code == 401

    # 2. Authenticated POST /players/Boaster/FNC/reports -> 200
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "mock-user-1",
        "email": "coach@test.com",
        "is_active": True,
        "is_admin": False,
    }
    try:
        resp = client.post("/players/Boaster/FNC/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "payload" in data
        assert "Boaster#FNC" in data["payload"]["title"]
        assert len(data["payload"]["training_plan"]) >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # 3. GET /players/Boaster/FNC/reports (in base service returns empty list)
    list_resp = client.get("/players/Boaster/FNC/reports")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert "reports" in list_data
    assert list_data["count"] == 0

    # 4. GET /players/Boaster/FNC/reports/unknown-id -> 404
    get_resp = client.get("/players/Boaster/FNC/reports/unknown-id")
    assert get_resp.status_code == 404

    # 5. Report belonging to Alice is not returned under Bob's URL -> 404
    async def mock_get_report(rep_id, *, game_name=None, tag_line=None):
        if rep_id == "alice-rep-1" and game_name == "Alice" and tag_line == "EU1":
            return {
                "id": "alice-rep-1",
                "player_id": "pid-alice",
                "schema_version": 1,
                "provider": "orchestrator",
                "payload": {"title": "Alice Report"},
                "evidence": [],
                "created_at": "2026-10-06T12:00:00Z",
            }
        return None

    mock_service.get_coaching_report = mock_get_report

    # Alice URL succeeds
    alice_resp = client.get("/players/Alice/EU1/reports/alice-rep-1")
    assert alice_resp.status_code == 200
    assert alice_resp.json()["id"] == "alice-rep-1"

    # Bob URL for Alice's report returns 404!
    bob_resp = client.get("/players/Bob/NA1/reports/alice-rep-1")
    assert bob_resp.status_code == 404
    assert "not found" in bob_resp.json()["detail"].lower()


def test_complete_coaching_report_lifecycle_api(storage_database):
    url, _ = storage_database
    store = SQLPlayerStore(url, ttl_seconds=300, test_mode=True)
    persistent_service = PersistentPlayerService(store=store)

    mock_matches = [
        PlayerMatch(
            match_id="match-e2e-1",
            map_name="Ascent",
            mode="Competitive",
            timestamp="2026-10-06T10:00:00Z",
            result="Victory",
            kills=20,
            deaths=10,
            assists=5,
            agent_name="Sova",
            provider="riot",
        )
    ]
    persistent_service.get_recent_matches = AsyncMock(return_value=mock_matches)
    persistent_service.get_rank = AsyncMock(side_effect=Exception("No rank available"))
    persistent_service.get_stats_overview = AsyncMock(
        side_effect=Exception("No stats available")
    )

    from backend.app.dependencies.auth_deps import get_current_user

    app.state.player_service = persistent_service
    client = TestClient(app)

    app.dependency_overrides[get_current_user] = lambda: {
        "id": "e2e-user",
        "email": "e2e@test.com",
        "is_active": True,
        "is_admin": False,
    }

    try:
        # 1. Generate report via POST endpoint (orchestrator -> persistent storage)
        post_resp = client.post("/players/Chronicle/FNC/reports")
        assert post_resp.status_code == 200
        report_data = post_resp.json()
        rep_id = report_data["id"]
        post_created_at = report_data["created_at"]
        assert rep_id != ""
        assert report_data["provider"] == "orchestrator"
        assert "Chronicle#FNC" in report_data["payload"]["title"]
        assert post_created_at is not None
        # Strict validation of ISO format and contemporary generation date
        parsed_dt = datetime.fromisoformat(post_created_at)
        assert parsed_dt.year >= 2026

        # 2. List reports via GET endpoint -> finds persisted report
        list_resp = client.get("/players/Chronicle/FNC/reports")
        assert list_resp.status_code == 200
        reports_list = list_resp.json()
        assert reports_list["count"] == 1
        assert reports_list["reports"][0]["id"] == rep_id
        # Strict exact match of created_at between POST generation and list endpoint
        assert reports_list["reports"][0]["created_at"] == post_created_at
        assert (
            reports_list["reports"][0]["payload"]["title"]
            == report_data["payload"]["title"]
        )

        # 3. Get specific report via GET endpoint
        get_resp = client.get(f"/players/Chronicle/FNC/reports/{rep_id}")
        assert get_resp.status_code == 200
        single_rep = get_resp.json()
        assert single_rep["id"] == rep_id
        # Strict exact match of created_at between POST, list, and individual endpoint
        assert single_rep["created_at"] == post_created_at
        assert single_rep["payload"] == report_data["payload"]

        # 4. Identity isolation: retrieving report under another player's URL -> 404
        cross_resp = client.get(f"/players/Boaster/FNC/reports/{rep_id}")
        assert cross_resp.status_code == 404

        # 5. Progression endpoint integrates the persisted report
        prog_resp = client.get("/players/Chronicle/FNC/progression")
        assert prog_resp.status_code == 200
        prog_data = prog_resp.json()
        assert prog_data["total_reports_generated"] >= 1

        # 6. Provider failure during generation returns 503
        persistent_service.get_recent_matches = AsyncMock(
            side_effect=PlayerServiceUnavailableError("Upstream match provider offline")
        )
        fail_resp = client.post("/players/Chronicle/FNC/reports")
        assert fail_resp.status_code == 503
        assert "upstream" in fail_resp.json()["detail"].lower()

        # 7. Zero matches scenario (matches=[]) -> generates grounded report cleanly
        persistent_service.get_recent_matches = AsyncMock(return_value=[])
        zero_matches_resp = client.post("/players/Chronicle/FNC/reports")
        assert zero_matches_resp.status_code == 200
        zero_data = zero_matches_resp.json()
        assert zero_data["id"] != ""
        assert "Chronicle#FNC" in zero_data["payload"]["title"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        store.close()

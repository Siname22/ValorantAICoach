from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import get_settings
from backend.app.services.player_service import PlayerMatch, PlayerService
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

        # Retrieve report by ID
        found = await mock_service.get_coaching_report(report["id"])
        assert found is not None
        assert found["id"] == report["id"]
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

    app.state.player_service = mock_service
    client = TestClient(app)

    # 1. POST /players/Boaster/FNC/reports
    resp = client.post("/players/Boaster/FNC/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "payload" in data
    assert "Boaster#FNC" in data["payload"]["title"]
    assert len(data["payload"]["training_plan"]) >= 1

    # 2. GET /players/Boaster/FNC/reports (in base service returns empty list)
    list_resp = client.get("/players/Boaster/FNC/reports")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert "reports" in list_data
    assert list_data["count"] == 0

    # 3. GET /players/Boaster/FNC/reports/unknown-id -> 404
    get_resp = client.get("/players/Boaster/FNC/reports/unknown-id")
    assert get_resp.status_code == 404

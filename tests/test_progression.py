from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import get_settings
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.services.player_service import (
    PlayerMatch,
    PlayerNotFoundError,
    PlayerService,
    PlayerServiceUnavailableError,
    PlayerStatsOverview,
)
from backend.app.storage.models import LinkedAccountRecord
from backend.app.storage.player_service import PersistentPlayerService
from backend.app.storage.repository import SQLPlayerStore
from backend.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture
def storage_database(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    url = f"sqlite+pysqlite:///{(tmp_path / 'coach.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "database/migrations"))
    engine = create_engine(url)
    try:
        yield config, engine, url
    finally:
        engine.dispose()
        get_settings.cache_clear()


def _sample_matches(trend: str = "improving") -> list[PlayerMatch]:
    if trend == "improving":
        return [
            PlayerMatch(
                match_id="m1",
                map_name="Ascent",
                mode="Competitive",
                timestamp=1000,
                result="Defeat",
                kills=5,
                deaths=15,
                assists=2,
                agent_name="Jett",
            ),
            PlayerMatch(
                match_id="m2",
                map_name="Bind",
                mode="Competitive",
                timestamp=2000,
                result="Defeat",
                kills=6,
                deaths=14,
                assists=3,
                agent_name="Jett",
            ),
            PlayerMatch(
                match_id="m3",
                map_name="Haven",
                mode="Competitive",
                timestamp=3000,
                result="Victory",
                kills=22,
                deaths=8,
                assists=5,
                agent_name="Omen",
            ),
            PlayerMatch(
                match_id="m4",
                map_name="Sunset",
                mode="Competitive",
                timestamp=4000,
                result="Victory",
                kills=20,
                deaths=5,
                assists=4,
                agent_name="Omen",
            ),
        ]
    return [
        PlayerMatch(
            match_id="m1",
            map_name="Haven",
            mode="Competitive",
            timestamp=1000,
            result="Victory",
            kills=25,
            deaths=5,
            assists=4,
            agent_name="Reyna",
        ),
        PlayerMatch(
            match_id="m2",
            map_name="Ascent",
            mode="Competitive",
            timestamp=2000,
            result="Victory",
            kills=20,
            deaths=6,
            assists=3,
            agent_name="Reyna",
        ),
        PlayerMatch(
            match_id="m3",
            map_name="Bind",
            mode="Competitive",
            timestamp=3000,
            result="Defeat",
            kills=4,
            deaths=18,
            assists=1,
            agent_name="Reyna",
        ),
        PlayerMatch(
            match_id="m4",
            map_name="Sunset",
            mode="Competitive",
            timestamp=4000,
            result="Defeat",
            kills=5,
            deaths=17,
            assists=2,
            agent_name="Reyna",
        ),
    ]


@pytest.fixture
def mock_isolated_service():
    service = PlayerService(AsyncMock(), AsyncMock(), AsyncMock())
    return service


@pytest.mark.asyncio
async def test_get_player_progression_empty_matches(mock_isolated_service):
    mock_isolated_service.get_recent_matches = AsyncMock(return_value=[])
    mock_isolated_service.list_coaching_reports = AsyncMock(return_value=[])

    res = await mock_isolated_service.get_player_progression("TenZ", "SEN")
    assert res["game_name"] == "TenZ"
    assert res["tag_line"] == "SEN"
    assert res["total_matches_analyzed"] == 0
    assert res["total_reports_generated"] == 0
    assert res["kd_metric"]["trend"] == "stable"
    assert res["win_rate_metric"]["trend"] == "stable"
    assert "No recent matches recorded" in res["trajectory_narrative"]


@pytest.mark.asyncio
async def test_get_player_progression_improving_trend(mock_isolated_service):
    matches = _sample_matches("improving")
    mock_isolated_service.get_recent_matches = AsyncMock(return_value=matches)
    mock_isolated_service.list_coaching_reports = AsyncMock(return_value=[])
    mock_isolated_service.get_stats_overview = AsyncMock(
        return_value=PlayerStatsOverview(
            kills=53,
            deaths=42,
            assists=14,
            kd_ratio=1.26,
            win_pct=50.0,
            headshot_pct=26.5,
        )
    )

    res = await mock_isolated_service.get_player_progression("TenZ", "SEN")
    assert res["total_matches_analyzed"] == 4
    assert res["kd_metric"]["trend"] == "improving"
    assert res["kd_metric"]["change_pct"] > 0
    assert res["win_rate_metric"]["trend"] == "improving"
    assert res["headshot_metric"]["current"] == 26.5
    assert "Omen" in res["agent_trends"]
    assert res["agent_trends"]["Omen"]["win_pct"] == 100.0


@pytest.mark.asyncio
async def test_get_player_progression_declining_trend(mock_isolated_service):
    matches = _sample_matches("declining")
    mock_isolated_service.get_recent_matches = AsyncMock(return_value=matches)
    mock_isolated_service.list_coaching_reports = AsyncMock(return_value=[])
    mock_isolated_service.get_stats_overview = AsyncMock(
        return_value=PlayerStatsOverview(
            kills=54,
            deaths=46,
            assists=10,
            kd_ratio=1.17,
            win_pct=50.0,
            headshot_pct=18.0,
        )
    )

    res = await mock_isolated_service.get_player_progression("Chronicle", "FNC")
    assert res["kd_metric"]["trend"] == "declining"
    assert res["win_rate_metric"]["trend"] == "declining"
    assert res["kd_metric"]["change_pct"] < 0


@pytest.mark.asyncio
async def test_get_player_progression_resolves_historical_weaknesses(
    mock_isolated_service,
):
    matches = _sample_matches("improving")
    mock_isolated_service.get_recent_matches = AsyncMock(return_value=matches)
    mock_isolated_service.get_stats_overview = AsyncMock(
        return_value=PlayerStatsOverview(
            kills=53,
            deaths=42,
            assists=14,
            kd_ratio=1.26,
            win_pct=50.0,
            headshot_pct=25.0,
        )
    )
    mock_isolated_service.list_coaching_reports = AsyncMock(
        return_value=[
            {
                "id": "rep-latest",
                "payload": {
                    "critical_weaknesses": ["Crosshair Placement"],
                },
            },
            {
                "id": "rep-older",
                "payload": {
                    "critical_weaknesses": [
                        "Crosshair Placement",
                        "Ultimate Economy",
                    ],
                },
            },
        ]
    )

    res = await mock_isolated_service.get_player_progression("Boaster", "FNC")
    assert "Crosshair Placement" in res["active_focus_areas"]
    assert "Ultimate Economy" in res["resolved_focus_areas"]


def test_get_player_progression_api_endpoint():
    mock_svc = AsyncMock()
    mock_svc.get_player_progression.return_value = {
        "game_name": "Derke",
        "tag_line": "VITALITY",
        "total_matches_analyzed": 5,
        "total_reports_generated": 2,
        "kd_metric": {
            "name": "K/D Ratio",
            "current": 1.45,
            "historical_avg": 1.20,
            "trend": "improving",
            "change_pct": 20.8,
            "data_points": [{"timestamp": 12345, "value": 1.45}],
        },
        "headshot_metric": {
            "name": "Headshot %",
            "current": 32.0,
            "historical_avg": 32.0,
            "trend": "stable",
            "change_pct": 0.0,
            "data_points": [{"timestamp": 12345, "value": 32.0}],
        },
        "win_rate_metric": {
            "name": "Win Rate %",
            "current": 60.0,
            "historical_avg": 50.0,
            "trend": "improving",
            "change_pct": 10.0,
            "data_points": [{"timestamp": 12345, "value": 100.0}],
        },
        "resolved_focus_areas": ["First Bullet Accuracy"],
        "active_focus_areas": ["Post-Plant Positioning"],
        "agent_trends": {
            "Jett": {"matches_played": 5, "win_pct": 60.0, "avg_kd": 1.45}
        },
        "trajectory_narrative": "Derke is trending positively.",
    }

    app.dependency_overrides[get_player_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.get("/players/Derke/VITALITY/progression")
            assert res.status_code == 200
            data = res.json()
            assert data["game_name"] == "Derke"
            assert data["kd_metric"]["trend"] == "improving"
            assert data["resolved_focus_areas"] == ["First Bullet Accuracy"]
    finally:
        app.dependency_overrides.clear()


def test_get_player_progression_api_error_mappings():
    mock_svc = AsyncMock()
    mock_svc.get_player_progression.side_effect = PlayerNotFoundError(
        "Player not found"
    )
    app.dependency_overrides[get_player_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.get("/players/Unknown/000/progression")
            assert res.status_code == 404

        mock_svc.get_player_progression.side_effect = PlayerServiceUnavailableError(
            "Service down"
        )
        with TestClient(app) as client:
            res = client.get("/players/Unknown/000/progression")
            assert res.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_sync_player_api_endpoint():
    mock_svc = AsyncMock()
    mock_svc.sync_player_coaching.return_value = {
        "synced": True,
        "game_name": "TenZ",
        "tag_line": "SEN",
        "new_report_generated": True,
        "report_id": "rep-xyz",
        "matches_synced": 5,
        "synced_at": "2026-10-08T10:00:00Z",
    }
    app.dependency_overrides[get_player_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.post("/players/TenZ/SEN/sync?region=na")
            assert res.status_code == 200
            data = res.json()
            assert data["synced"] is True
            assert data["new_report_generated"] is True
            assert data["report_id"] == "rep-xyz"
    finally:
        app.dependency_overrides.clear()


def test_system_sync_tracked_accounts_endpoint():
    mock_svc = AsyncMock()
    mock_svc.sync_all_tracked_accounts.return_value = {
        "synced_accounts_count": 2,
        "details": [{"game_name": "A", "tag_line": "1", "synced": True}],
    }
    app.dependency_overrides[get_player_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.post("/system/coaching/sync-tracked")
            assert res.status_code == 200
            data = res.json()
            assert data["synced_accounts_count"] == 2
            assert len(data["details"]) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_persistent_sync_tracked_accounts_flow(storage_database):
    config, engine, url = storage_database
    command.upgrade(config, "head")

    store = SQLPlayerStore(url, ttl_seconds=300, test_mode=True)
    try:
        # Create users and link accounts
        user1 = store.create_user("test1@example.com", "hashed_pwd1")
        user2 = store.create_user("test2@example.com", "hashed_pwd2")
        acc1 = store.link_player_account(
            user1["id"], "PlayerOne", "EU1", region="eu", is_primary=True
        )
        store.link_player_account(
            user2["id"], "PlayerTwo", "NA1", region="na", is_primary=True
        )

        assert acc1["last_synced_at"] is None

        # Verify get_tracked_accounts
        tracked = store.get_tracked_accounts()
        assert len(tracked) == 2
        names = {t["game_name"] for t in tracked}
        assert names == {"PlayerOne", "PlayerTwo"}

        # Update sync time
        updated = store.update_account_sync_time("PlayerOne", "EU1")
        assert updated is True

        # Check DB that last_synced_at is recorded
        with Session(engine) as session:
            record = session.scalar(
                select(LinkedAccountRecord).where(
                    LinkedAccountRecord.game_name == "PlayerOne"
                )
            )
            assert record is not None
            assert record.last_synced_at is not None

        # Test PersistentPlayerService.sync_all_tracked_accounts
        service = PersistentPlayerService(
            store=store,
            riot_provider=AsyncMock(),
            henrik_provider=AsyncMock(),
            tracker_provider=AsyncMock(),
        )
        service.get_recent_matches = AsyncMock(return_value=[])
        service.list_coaching_reports = AsyncMock(return_value=[])

        sync_summary = await service.sync_all_tracked_accounts()
        assert sync_summary["synced_accounts_count"] == 2
        assert len(sync_summary["details"]) == 2
    finally:
        store.close()

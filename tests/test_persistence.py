import asyncio
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import respx
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from backend.app.core.config import get_settings
from backend.app.dependencies.provider_deps import create_player_service
from backend.app.storage.models import (
    Base,
    MatchRecord,
    PlayerMatchHistory,
    PlayerRecord,
    PlayerSnapshot,
)
from backend.app.storage.repository import SQLPlayerStore, request_key
from backend.main import app, lifespan
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

TABLES = {
    "players",
    "player_snapshots",
    "matches",
    "player_match_history",
    "coaching_reports",
}


@pytest.fixture
def storage_database(monkeypatch, tmp_path):
    # Every migration targets a new temporary SQLite file, never operator settings.
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


def test_real_migration_creates_storage_tables(storage_database):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) >= TABLES
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert not TABLES.intersection(inspect(engine).get_table_names())
    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) >= TABLES


@pytest.fixture
def storage_providers(monkeypatch):
    for provider in ("RIOT", "HENRIK", "TRACKER"):
        monkeypatch.setenv(f"{provider}_API_KEY", "")
        monkeypatch.setenv(f"{provider}_ENABLED", "true")
        monkeypatch.setenv(f"{provider}_RETRIES", "0")
    monkeypatch.setenv("HENRIK_API_KEY", "synthetic-storage-test")
    monkeypatch.setenv("HENRIK_BASE_URL", "https://api.henrikdev.xyz/valorant/v1")


@respx.mock
def test_profile_cache_survives_application_restart(
    storage_database, storage_providers
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    account = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/account/Test/EU1"
    ).respond(
        200,
        json={
            "status": 200,
            "data": {
                "puuid": "player-storage-1",
                "name": "Test",
                "tag": "EU1",
                "region": "eu",
                "account_level": 20,
            },
        },
    )
    respx.get("https://api.henrikdev.xyz/valorant/v2/mmr/eu/Test/EU1").respond(
        404, json={"status": 404}
    )
    with TestClient(app) as client:
        first = client.get("/players/Test/EU1")
        assert app.state.player_service.henrik is not None
        assert first.status_code == 200, first.text
    with TestClient(app) as client:
        second = client.get("/players/Test/EU1")
    assert second.status_code == 200
    assert second.json() == first.json()
    assert account.call_count == 1


def test_enabled_storage_requires_explicit_migration(
    storage_database, storage_providers
):
    _, engine, _ = storage_database
    with pytest.raises(RuntimeError, match="storage"), TestClient(app):
        pass
    assert inspect(engine).get_table_names() == []


@pytest.mark.parametrize("operation", ["rank", "matches", "stats", "match_detail"])
@respx.mock
def test_successful_section_reads_are_cached_with_provenance(
    storage_database, storage_providers, monkeypatch, operation
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    if operation == "rank":
        provider, path = "henrik", "/players/Test/EU1/rank?region=eu"
        route = respx.get(
            "https://api.henrikdev.xyz/valorant/v2/mmr/eu/Test/EU1"
        ).respond(
            200,
            json={
                "status": 200,
                "data": {
                    "current_data": {
                        "currenttierpatched": "Gold 1",
                        "ranking_in_tier": 0,
                    }
                },
            },
        )
    elif operation == "matches":
        provider, path = "henrik", "/players/Test/EU1/matches?region=eu&limit=1"
        route = respx.get(
            "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Test/EU1"
        ).respond(200, json={"status": 200, "data": []})
    elif operation == "stats":
        provider, path = "tracker", "/players/Test/EU1/stats"
        monkeypatch.setenv("TRACKER_API_KEY", "synthetic-storage-test")
        monkeypatch.setenv("TRACKER_BASE_URL", "https://tracker-storage.test")
        route = respx.get(
            "https://tracker-storage.test/profile/riot/Test%23EU1"
        ).respond(
            200,
            json={
                "data": {
                    "platformInfo": {
                        "platformId": "riot",
                        "platformUserHandle": "Test#EU1",
                        "platformUserIdentifier": "test-player",
                    },
                    "userInfo": {},
                    "segments": [
                        {
                            "type": "overview",
                            "stats": {
                                "kills": {"value": 100, "displayValue": "100"},
                                "deaths": {"value": 50, "displayValue": "50"},
                                "assists": {"value": 25, "displayValue": "25"},
                                "kdRatio": {"value": 2, "displayValue": "2"},
                                "winPct": {"value": 60, "displayValue": "60"},
                                "headshotPct": {"value": 25, "displayValue": "25"},
                            },
                        }
                    ],
                }
            },
        )
    else:
        provider, path = "riot", "/matches/match-one"
        monkeypatch.setenv("RIOT_API_KEY", "synthetic-storage-test")
        monkeypatch.setenv("RIOT_BASE_URL", "https://riot-storage.test")
        route = respx.get(
            "https://riot-storage.test/val/match/v1/matches/match-one"
        ).respond(200, json={"matchInfo": {"matchId": "match-one"}, "players": []})
    with TestClient(app) as client:
        first = client.get(path)
        assert first.status_code == 200, first.text
        second = client.get(path)
    assert second.status_code == 200
    assert first.json() == second.json()
    assert route.call_count == 1
    with Session(engine) as session:
        saved = session.scalars(select(PlayerSnapshot)).all()
        assert len(saved) == 1
        assert saved[0].providers == [provider]
        assert saved[0].observed_at.tzinfo is not None


def test_migration_matches_declared_models(storage_database):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )


def test_partial_schema_is_rejected_at_startup(storage_database, storage_providers):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE matches"))
    with pytest.raises(RuntimeError, match="storage"), TestClient(app):
        pass


def test_disabled_storage_never_connects(
    storage_database, storage_providers, monkeypatch
):
    from sqlalchemy.engine import Engine

    monkeypatch.setenv("DATABASE_ENABLED", "false")

    def forbid_connect(*args, **kwargs):
        pytest.fail("Disabled persistence must not open a database connection")

    monkeypatch.setattr(Engine, "connect", forbid_connect)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200


def test_sqlite_is_not_accepted_for_production(storage_database):
    _, _, url = storage_database
    with pytest.raises(RuntimeError, match="test-only"):
        SQLPlayerStore(url, ttl_seconds=300)


def _mock_rank(points=5):
    return respx.get("https://api.henrikdev.xyz/valorant/v2/mmr/eu/Test/EU1").respond(
        200,
        json={
            "status": 200,
            "data": {
                "current_data": {
                    "currenttierpatched": "Gold 1",
                    "ranking_in_tier": points,
                }
            },
        },
    )


@pytest.mark.parametrize("corrupt", [False, True], ids=["expired", "corrupt"])
@respx.mock
def test_expired_or_invalid_cache_is_refreshed(
    storage_database, storage_providers, corrupt
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    route = _mock_rank(5)
    with TestClient(app) as client:
        assert client.get("/players/Test/EU1/rank?region=eu").json()["points"] == 5
        with Session(engine) as session, session.begin():
            snapshot = session.scalars(select(PlayerSnapshot)).one()
            if corrupt:
                snapshot.payload = {"unusable": True}
            else:
                snapshot.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        _mock_rank(9)
        refreshed = client.get("/players/Test/EU1/rank?region=eu")
        assert refreshed.status_code == 200
        assert refreshed.json()["points"] == 9
    assert route.call_count == 2


@respx.mock
def test_invalid_cached_match_detail_is_refreshed(
    storage_database, storage_providers, monkeypatch
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    monkeypatch.setenv("RIOT_API_KEY", "synthetic-storage-test")
    monkeypatch.setenv("RIOT_BASE_URL", "https://riot-storage.test")
    route = respx.get(
        "https://riot-storage.test/val/match/v1/matches/match-one"
    ).respond(200, json={"matchInfo": {"matchId": "match-one"}, "players": []})
    with TestClient(app) as client:
        assert client.get("/matches/match-one").status_code == 200
        with Session(engine) as session, session.begin():
            snapshot = session.scalars(select(PlayerSnapshot)).one()
            snapshot.payload = {"matchInfo": {"matchId": ""}}
        refreshed = client.get("/matches/match-one")
        assert refreshed.status_code == 200
        assert refreshed.json()["matchInfo"]["matchId"] == "match-one"
    assert route.call_count == 2


@pytest.mark.parametrize("status", [404, 503])
@respx.mock
def test_failed_provider_results_are_not_cached(
    storage_database, storage_providers, status
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    respx.get("https://api.henrikdev.xyz/valorant/v2/mmr/eu/Test/EU1").respond(
        status, json={"status": status}
    )
    with TestClient(app) as client:
        assert client.get("/players/Test/EU1/rank?region=eu").status_code == status
        _mock_rank(9)
        assert client.get("/players/Test/EU1/rank?region=eu").json()["points"] == 9
    with Session(engine) as session:
        assert len(session.scalars(select(PlayerSnapshot)).all()) == 1


@pytest.mark.parametrize("failure", ["read", "write"])
@respx.mock
def test_storage_failure_is_sanitized_and_rolls_back(
    storage_database, storage_providers, caplog, failure
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    if failure == "write":
        _mock_rank()
    with TestClient(app) as client:
        with engine.begin() as connection:
            if failure == "read":
                connection.execute(text("DROP TABLE player_snapshots"))
            else:
                connection.execute(
                    text(
                        "CREATE TRIGGER reject_snapshot BEFORE INSERT "
                        "ON player_snapshots BEGIN SELECT "
                        "RAISE(ABORT, 'synthetic-private-storage-detail'); END"
                    )
                )
        response = client.get("/players/Test/EU1/rank?region=eu")
        assert response.status_code == 503
    assert "synthetic-private-storage-detail" not in response.text + caplog.text
    assert "coach.db" not in response.text + caplog.text
    with Session(engine) as session:
        assert session.scalars(select(PlayerRecord)).all() == []


@respx.mock
def test_cache_isolates_history_region_limit_and_identity(
    storage_database, storage_providers
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    eu = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Test/EU1"
    ).respond(200, json={"status": 200, "data": []})
    na = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/na/Test/EU1"
    ).respond(200, json={"status": 200, "data": []})
    other = respx.get(
        "https://api.henrikdev.xyz/valorant/v1/stored-matches/eu/Other/EU1"
    ).respond(200, json={"status": 200, "data": []})
    paths = [
        "/players/Test/EU1/matches?region=eu&limit=1",
        "/players/Test/EU1/matches?region=eu&limit=2",
        "/players/Test/EU1/matches?region=na&limit=1",
        "/players/Other/EU1/matches?region=eu&limit=1",
    ]
    with TestClient(app) as client:
        for path in paths + paths:
            response = client.get(path)
            assert response.status_code == 200
            assert response.json() == {"matches": [], "count": 0}
    assert (eu.call_count, na.call_count, other.call_count) == (2, 1, 1)
    with Session(engine) as session:
        assert len(session.scalars(select(PlayerSnapshot)).all()) == 4


def test_match_upserts_preserve_player_stats_raw_dates_and_detail(storage_database):
    config, engine, url = storage_database
    command.upgrade(config, "head")
    store = SQLPlayerStore(url, ttl_seconds=300, test_mode=True)
    try:
        for name, provider, kills in [
            ("Test", "riot", 3),
            ("Other", "riot", 9),
            ("Test", "tracker", 6),
        ]:
            params = {"game_name": name, "tag_line": "EU1", "limit": 1}
            match = {
                "match_id": "same-id",
                "map_name": "Ascent",
                "mode": "ranked",
                "timestamp": "2026-10-06T08:30:00+02:00",
                "provider": provider,
                "kills": kills,
            }
            for _ in range(2):
                store.put(
                    request_key("matches", params),
                    "matches",
                    params,
                    [match],
                    [provider],
                )
        params = {"match_id": "same-id"}
        detail = {"matchInfo": {"matchId": "same-id"}, "players": []}
        store.put(
            request_key("match_detail", params),
            "match_detail",
            params,
            detail,
            ["riot"],
        )
        with Session(engine) as session:
            matches = session.scalars(select(MatchRecord)).all()
            assert len(matches) == 2
            riot = session.get(MatchRecord, ("riot", "same-id"))
            assert riot.detail == detail
            assert riot.provider_timestamp == "2026-10-06T08:30:00+02:00"
            assert riot.started_at == datetime(2026, 10, 6, 6, 30, tzinfo=UTC)
            histories = session.scalars(select(PlayerMatchHistory)).all()
            assert len(histories) == 3
            assert sorted(row.payload["kills"] for row in histories) == [3, 6, 9]
    finally:
        store.close()


@pytest.mark.asyncio
@respx.mock
async def test_concurrent_cache_misses_share_one_provider_fetch(
    storage_database, storage_providers
):
    config, _, _ = storage_database
    command.upgrade(config, "head")
    route = _mock_rank(5)
    service = create_player_service()
    try:
        ranks = await asyncio.gather(
            *(service.get_rank("Test", "EU1", region="eu") for _ in range(8))
        )
        assert [rank.points for rank in ranks] == [5] * 8
        assert route.call_count == 1
    finally:
        await service.close()


@respx.mock
def test_provider_json_serialization_matches_cached_response(
    storage_database, storage_providers, monkeypatch
):
    config, engine, _ = storage_database
    command.upgrade(config, "head")
    monkeypatch.setenv("RIOT_API_KEY", "synthetic-storage-test")
    monkeypatch.setenv("RIOT_BASE_URL", "https://riot-storage.test")
    route = respx.get(
        "https://riot-storage.test/val/match/v1/matches/match-one"
    ).respond(
        200,
        content=b'{"matchInfo":{"matchId":"match-one"},"invalid":NaN}',
        headers={"Content-Type": "application/json"},
    )
    with TestClient(app) as client:
        first = client.get("/matches/match-one")
        cached = client.get("/matches/match-one")
        assert first.status_code == cached.status_code == 200
        assert (
            first.json()
            == cached.json()
            == {"matchInfo": {"matchId": "match-one"}, "invalid": None}
        )
    assert route.call_count == 1
    with Session(engine) as session:
        assert session.scalars(select(PlayerSnapshot)).one().payload["invalid"] is None


@pytest.mark.asyncio
async def test_storage_startup_queries_run_outside_event_loop_thread(
    storage_database, storage_providers
):
    config, _, _ = storage_database
    command.upgrade(config, "head")
    event_loop_thread = threading.get_ident()
    query_threads = []

    def record_query(connection, cursor, statement, parameters, context, executemany):
        query_threads.append(threading.get_ident())

    event.listen(Engine, "before_cursor_execute", record_query)
    try:
        async with lifespan(app):
            assert len(query_threads) == 5
            assert all(thread != event_loop_thread for thread in query_threads)
    finally:
        event.remove(Engine, "before_cursor_execute", record_query)


def test_shared_match_writes_have_stable_lock_order_without_reordering_history(
    storage_database,
):
    config, _, url = storage_database
    command.upgrade(config, "head")
    store = SQLPlayerStore(url, ttl_seconds=300, test_mode=True)
    writes = []

    def record_query(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO matches "):
            writes.append(parameters[:2])

    event.listen(store.engine, "before_cursor_execute", record_query)
    try:
        for name, identifiers in [("Test", ["b", "a"]), ("Other", ["a", "b"])]:
            params = {"game_name": name, "tag_line": "EU1"}
            history = [
                {
                    "provider": "riot",
                    "match_id": identifier,
                    "map_name": "Ascent",
                    "mode": "ranked",
                    "timestamp": 0,
                }
                for identifier in identifiers
            ]
            key = request_key("matches", params)
            store.put(key, "matches", params, history, ["riot"])
            assert store.get(key) == history
        assert writes == [("riot", "a"), ("riot", "b")] * 2
    finally:
        event.remove(store.engine, "before_cursor_execute", record_query)
        store.close()

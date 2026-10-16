"""Explicit PostgreSQL proof; TEST_POSTGRES_URL must grant CREATE DATABASE.

Each database test creates and drops its own UUID-named database. The control
database must contain a test marker in its name; DATABASE_URL is never an input.
Run with pytest integration_tests/test_postgres_storage.py (no automatic skips).
"""

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import respx
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from backend.app.core.config import get_settings
from backend.app.storage.models import (
    Base,
    CoachingReportRecord,
    MatchRecord,
    PlayerMatchHistory,
    PlayerRecord,
    PlayerSnapshot,
)
from backend.app.storage.repository import SQLPlayerStore, request_key
from fastapi.testclient import TestClient
from sqlalchemy import DateTime, create_engine, func, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool


def _test_postgres_url() -> URL:
    raw = os.environ.get("TEST_POSTGRES_URL", "")
    if not raw.strip():
        raise ValueError(
            "TEST_POSTGRES_URL is required for explicit PostgreSQL tests; "
            "DATABASE_URL is never used as a fallback."
        )
    try:
        url = make_url(raw)
        port = url.port
    except (ArgumentError, ValueError):
        raise ValueError("TEST_POSTGRES_URL must be a valid PostgreSQL URL.") from None
    if (
        url.drivername != "postgresql+psycopg"
        or not url.host
        or not url.username
        or not url.database
        or not re.search(r"(?:^test_|_test(?:_|$))", url.database)
        or url.query
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError(
            "TEST_POSTGRES_URL requires postgresql+psycopg, an explicit host/user, "
            "a database named test_* or *_test[_*], and no query overrides."
        )
    return url.set(port=port or 5432)


@pytest.mark.parametrize(
    "target",
    [
        None,
        "",
        " ",
        "not-a-url",
        "sqlite+pysqlite:///coach_test.db",
        "postgresql://test:test@127.0.0.1/coach_test",
        "postgresql+psycopg://test:test@127.0.0.1/valorant_ai_coach",
        "postgresql+psycopg://test:test@127.0.0.1/postgres",
        "postgresql+psycopg://test:test@127.0.0.1/template1",
        "postgresql+psycopg://test:test@/coach_test",
        "postgresql+psycopg://127.0.0.1/coach_test",
        "postgresql+psycopg://test:test@127.0.0.1:0/coach_test",
        "postgresql+psycopg://test:test@127.0.0.1:bad/coach_test",
        "postgresql+psycopg://test:test@127.0.0.1/coach_test?dbname=production",
        "postgresql+psycopg://test:test@127.0.0.1/coach_test?service=operator",
    ],
)
def test_guard_rejects_unsafe_targets_without_operator_fallback(monkeypatch, target):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://operator:secret@operator.invalid/production",
    )
    if target is None:
        monkeypatch.delenv("TEST_POSTGRES_URL", raising=False)
    else:
        monkeypatch.setenv("TEST_POSTGRES_URL", target)
    with pytest.raises(ValueError, match="TEST_POSTGRES_URL"):
        _test_postgres_url()


def test_guard_uses_only_the_explicit_test_target(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///operator.db")
    monkeypatch.setenv(
        "TEST_POSTGRES_URL",
        "postgresql+psycopg://coach_test:synthetic%25only@127.0.0.1:5432/"
        "coach_storage_test_control",
    )
    url = _test_postgres_url()
    assert url.database == "coach_storage_test_control"
    assert url.username == "coach_test"
    assert url.password == "synthetic%only"
    assert url.host == "127.0.0.1"
    assert url.port == 5432


@pytest.fixture
def postgres_database(monkeypatch, tmp_path):
    control_url = _test_postgres_url()
    database_name = f"coach_storage_test_{uuid4().hex}"
    owned_url = control_url.set(database=database_name)
    control = create_engine(
        control_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        connect_args={"connect_timeout": 10},
    )
    quoted_name = control.dialect.identifier_preparer.quote_identifier(database_name)
    engine = None
    created = False
    try:
        with control.connect() as connection:
            connection.execute(
                text(f"CREATE DATABASE {quoted_name} TEMPLATE template0")
            )
        created = True
        engine = create_engine(owned_url, connect_args={"connect_timeout": 10})
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT current_database()")) == database_name
        assert inspect(engine).get_table_names() == []

        # Neither Alembic nor provider settings may read an operator's .env file.
        monkeypatch.chdir(tmp_path)
        url = owned_url.render_as_string(hide_password=False)
        monkeypatch.setenv("DATABASE_URL", url)
        monkeypatch.setenv("DATABASE_ENABLED", "true")
        monkeypatch.setenv("DATABASE_CACHE_TTL_SECONDS", "3600")
        monkeypatch.setenv("APP_ENV", "test")
        for provider in ("RIOT", "HENRIK", "TRACKER"):
            monkeypatch.setenv(f"{provider}_API_KEY", "")
            monkeypatch.setenv(f"{provider}_ENABLED", "false")
            monkeypatch.setenv(f"{provider}_RETRIES", "0")
            monkeypatch.setenv(f"{provider}_TIMEOUT", "1")
            monkeypatch.setenv(f"{provider}_DEFAULT_HEADERS", "{}")
        get_settings.cache_clear()
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "database/migrations"))
        yield config, engine, url
    finally:
        get_settings.cache_clear()
        if engine is not None:
            engine.dispose()
        try:
            if created:
                with control.connect() as connection:
                    connection.execute(
                        text(f"DROP DATABASE {quoted_name} WITH (FORCE)")
                    )
        finally:
            control.dispose()


def _assert_metadata_parity(config, engine):
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {
        "alembic_version"
    }
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True},
        )
        assert compare_metadata(context, Base.metadata) == []
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            ScriptDirectory.from_config(config).get_current_head()
        )
    for table in Base.metadata.sorted_tables:
        columns = {
            column["name"]: column for column in inspector.get_columns(table.name)
        }
        assert set(columns) == set(table.columns.keys())
        assert inspector.get_pk_constraint(table.name)["constrained_columns"] == [
            column.name for column in table.primary_key
        ]
        for column in table.columns:
            assert columns[column.name]["nullable"] == column.nullable
            column_type = getattr(column.type, "impl", column.type)
            if isinstance(column_type, DateTime):
                assert columns[column.name]["type"].timezone is True


def _assert_utc(value, earliest, latest):
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)
    assert earliest <= value <= latest


def test_real_upgrade_repeat_downgrade_reupgrade_matches_orm(postgres_database):
    config, engine, url = postgres_database
    # Storage must not create tables implicitly when migrations have not run.
    with pytest.raises(RuntimeError, match="storage"):
        SQLPlayerStore(url, ttl_seconds=3600)
    assert inspect(engine).get_table_names() == []
    command.upgrade(config, "head")
    _assert_metadata_parity(config, engine)

    payload = {
        "game_name": "Migration",
        "tag_line": "EU1",
        "puuid": "migration-player",
        "region": "eu",
        "source": "henrik",
    }
    parameters = {"game_name": "Migration", "tag_line": "EU1"}
    key = request_key("profile", parameters)
    store = SQLPlayerStore(url, ttl_seconds=3600)
    try:
        store.put(key, "profile", parameters, payload, ["henrik"])
        command.upgrade(config, "head")
        _assert_metadata_parity(config, engine)
        assert store.get(key) == payload
    finally:
        store.close()

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM alembic_version")) == 0
    command.upgrade(config, "head")
    _assert_metadata_parity(config, engine)
    with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            assert connection.scalar(select(func.count()).select_from(table)) == 0


def test_real_rest_profile_survives_restart_with_utc_provenance(
    postgres_database, monkeypatch
):
    from backend.main import app

    config, engine, _ = postgres_database
    command.upgrade(config, "head")
    monkeypatch.setenv("HENRIK_ENABLED", "true")
    monkeypatch.setenv("HENRIK_API_KEY", "synthetic-postgres-test")
    monkeypatch.setenv("HENRIK_BASE_URL", "https://henrik-postgres.test/valorant/v1")
    get_settings.cache_clear()
    earliest = datetime.now(UTC)
    with respx.mock(assert_all_called=True, assert_all_mocked=True) as router:
        account = router.get(
            "https://henrik-postgres.test/valorant/v1/account/Test/EU1"
        ).respond(
            200,
            json={
                "status": 200,
                "data": {
                    "puuid": "postgres-player-one",
                    "name": "Test",
                    "tag": "EU1",
                    "region": "eu",
                    "account_level": 20,
                },
            },
        )
        rank = router.get(
            "https://henrik-postgres.test/valorant/v2/mmr/eu/Test/EU1"
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
        with TestClient(app) as client:
            first_service = app.state.player_service
            first = client.get("/players/Test/EU1")
            assert first.status_code == 200, first.text
            assert first.json() == {
                "puuid": "postgres-player-one",
                "game_name": "Test",
                "tag_line": "EU1",
                "region": "eu",
                "account_level": 20,
                "avatar_url": None,
                "source": "henrik",
                "rank_name": "Gold 1",
                "rank_tier": None,
                "rank_icon_url": None,
            }
        # A cache miss after restart now produces a provider failure.
        account.respond(503, json={"status": 503})
        rank.respond(503, json={"status": 503})
        with TestClient(app) as client:
            assert app.state.player_service is not first_service
            assert app.state.player_service.store is not first_service.store
            second = client.get("/players/Test/EU1")
            assert second.status_code == 200, second.text
            assert second.json() == first.json()
        assert account.call_count == 1
        assert rank.call_count == 1
    latest = datetime.now(UTC)
    with Session(engine) as session:
        players = session.scalars(select(PlayerRecord)).all()
        assert len(players) == 1
        player = players[0]
        assert (player.game_name, player.tag_line, player.puuid, player.source) == (
            "Test",
            "EU1",
            "postgres-player-one",
            "henrik",
        )
        _assert_utc(player.observed_at, earliest, latest)
        snapshots = session.scalars(select(PlayerSnapshot)).all()
        assert len(snapshots) == 2
        assert {snapshot.operation for snapshot in snapshots} == {"profile", "rank"}
        for snapshot in snapshots:
            assert snapshot.player_id == player.id
            assert snapshot.providers == ["henrik"]
            _assert_utc(snapshot.observed_at, earliest, latest)
            assert snapshot.expires_at - snapshot.observed_at == timedelta(hours=1)
            assert snapshot.expires_at.utcoffset() == timedelta(0)
        profile = next(row for row in snapshots if row.operation == "profile")
        rank_snapshot = next(row for row in snapshots if row.operation == "rank")
        assert profile.payload["puuid"] == "postgres-player-one"
        assert profile.payload["source"] == "henrik"
        assert rank_snapshot.payload["tier_name"] == "Gold 1"
        assert rank_snapshot.payload["points"] == 0


def test_real_match_upserts_isolate_players_and_providers(postgres_database):
    config, engine, url = postgres_database
    command.upgrade(config, "head")
    ada_parameters = {"game_name": "Ada", "tag_line": "EU1", "region": "eu"}
    bob_parameters = {"game_name": "Bob", "tag_line": "EU1", "region": "eu"}
    ada_key = request_key("matches", ada_parameters)
    bob_key = request_key("matches", bob_parameters)
    henrik_match = {
        "provider": "henrik",
        "match_id": "shared-match",
        "map_name": "Ascent",
        "mode": "competitive",
        "timestamp": "2024-01-01T02:00:00+02:00",
        "result": "Victory",
        "kills": 10,
        "deaths": 5,
        "assists": 3,
        "agent_name": "Sage",
    }
    riot_match = {
        **henrik_match,
        "provider": "riot",
        "map_name": "Haven",
        "timestamp": 1704067200000,
        "kills": 30,
    }
    bob_match = {**henrik_match, "kills": 2, "deaths": 12, "result": "Defeat"}
    updated_ada = [{**henrik_match, "kills": 17}, riot_match]
    detail_parameters = {"match_id": "shared-match"}
    detail_key = request_key("match_detail", detail_parameters)
    detail = {
        "matchInfo": {
            "matchId": "shared-match",
            "mapId": "Haven",
            "gameStartMillis": 1704067200000,
        },
        "players": [{"puuid": "detail-player"}],
    }
    earliest = datetime.now(UTC)
    store = SQLPlayerStore(url, ttl_seconds=3600)
    try:
        store.put(
            ada_key,
            "matches",
            ada_parameters,
            [henrik_match, riot_match],
            ["henrik", "riot"],
        )
        store.put(bob_key, "matches", bob_parameters, [bob_match], ["henrik"])
        for _ in range(2):
            store.put(
                ada_key, "matches", ada_parameters, updated_ada, ["henrik", "riot"]
            )
        store.put(
            detail_key,
            "match_detail",
            detail_parameters,
            {**detail, "players": []},
            ["riot"],
        )
        store.put(detail_key, "match_detail", detail_parameters, detail, ["riot"])
        assert store.get(ada_key) == updated_ada
        assert store.get(bob_key) == [bob_match]
        assert store.get(detail_key) == detail
    finally:
        store.close()
    latest = datetime.now(UTC)
    with Session(engine) as session:
        players = session.scalars(select(PlayerRecord)).all()
        assert len(players) == 2
        players_by_name = {player.game_name: player for player in players}
        matches = session.scalars(select(MatchRecord)).all()
        assert len(matches) == 2
        matches_by_provider = {match.provider: match for match in matches}
        assert set(matches_by_provider) == {"henrik", "riot"}
        assert matches_by_provider["henrik"].provider_timestamp == (
            "2024-01-01T02:00:00+02:00"
        )
        assert matches_by_provider["henrik"].detail is None
        assert matches_by_provider["henrik"].map_name == "Ascent"
        assert matches_by_provider["riot"].provider_timestamp == 1704067200000
        assert matches_by_provider["riot"].detail == detail
        assert matches_by_provider["riot"].map_name == "Haven"
        for match in matches:
            assert match.match_id == "shared-match"
            assert match.started_at == datetime(2024, 1, 1, tzinfo=UTC)
            _assert_utc(match.observed_at, earliest, latest)
        histories = session.scalars(select(PlayerMatchHistory)).all()
        assert len(histories) == 3
        history = {(row.player_id, row.provider): row for row in histories}
        assert history[(players_by_name["Ada"].id, "henrik")].payload == updated_ada[0]
        assert history[(players_by_name["Ada"].id, "riot")].payload == riot_match
        assert history[(players_by_name["Bob"].id, "henrik")].payload == bob_match
        for row in histories:
            assert row.match_id == "shared-match"
            _assert_utc(row.observed_at, earliest, latest)
        snapshots = session.scalars(select(PlayerSnapshot)).all()
        assert len(snapshots) == 3
        snapshots_by_key = {snapshot.key: snapshot for snapshot in snapshots}
        assert snapshots_by_key[ada_key].providers == ["henrik", "riot"]
        assert snapshots_by_key[bob_key].providers == ["henrik"]
        assert snapshots_by_key[detail_key].providers == ["riot"]
        assert snapshots_by_key[detail_key].player_id is None
        for player in players:
            _assert_utc(player.observed_at, earliest, latest)
        for snapshot in snapshots:
            _assert_utc(snapshot.observed_at, earliest, latest)


def test_real_coaching_report_storage_timestamp_normalization(postgres_database):
    config, engine, url = postgres_database
    command.upgrade(config, "head")

    identity = {"game_name": "Chronicle", "tag_line": "FNC"}
    player_id = request_key("identity", identity)
    earliest = datetime.now(UTC)
    store = SQLPlayerStore(url, ttl_seconds=3600)
    try:
        # 1. Naive ISO string (no timezone)
        naive_payload = {"title": "Naive Report", "created_at": "2026-10-16T10:00:00"}
        id_naive = store.save_coaching_report(
            player_id, naive_payload, [], identity=identity
        )
        rec_naive = store.get_coaching_report(id_naive)
        assert rec_naive is not None
        assert rec_naive["created_at"] == "2026-10-16T10:00:00+00:00"
        assert rec_naive["payload"]["created_at"] == "2026-10-16T10:00:00+00:00"
        assert naive_payload["created_at"] == "2026-10-16T10:00:00+00:00"

        # 2. Offset string (+02:00)
        offset_payload = {
            "title": "Offset Report",
            "created_at": "2026-10-16T12:00:00+02:00",
        }
        id_offset = store.save_coaching_report(
            player_id, offset_payload, [], identity=identity
        )
        rec_offset = store.get_coaching_report(id_offset)
        assert rec_offset is not None
        assert rec_offset["created_at"] == "2026-10-16T10:00:00+00:00"
        assert rec_offset["payload"]["created_at"] == "2026-10-16T10:00:00+00:00"
        assert offset_payload["created_at"] == "2026-10-16T10:00:00+00:00"

        # 3. Zulu string (Z suffix)
        zulu_payload = {"title": "Zulu Report", "created_at": "2026-10-16T10:00:00Z"}
        id_zulu = store.save_coaching_report(
            player_id, zulu_payload, [], identity=identity
        )
        rec_zulu = store.get_coaching_report(id_zulu)
        assert rec_zulu is not None
        assert rec_zulu["created_at"] == "2026-10-16T10:00:00+00:00"
        assert rec_zulu["payload"]["created_at"] == "2026-10-16T10:00:00+00:00"
        assert zulu_payload["created_at"] == "2026-10-16T10:00:00+00:00"

        # 4. Auto-generated timestamp when created_at omitted
        auto_payload = {"title": "Auto Report"}
        id_auto = store.save_coaching_report(
            player_id, auto_payload, [], identity=identity
        )
        rec_auto = store.get_coaching_report(id_auto)
        assert rec_auto is not None
        assert rec_auto["created_at"] == rec_auto["payload"]["created_at"]
        assert auto_payload["created_at"] == rec_auto["created_at"]
        parsed_auto = datetime.fromisoformat(rec_auto["created_at"])
        assert parsed_auto.tzinfo is not None
        assert parsed_auto.utcoffset() == timedelta(0)

        # 5. Direct PostgreSQL session query confirms all rows are UTC TIMESTAMPTZ
        latest = datetime.now(UTC)
        with Session(engine) as session:
            for rep_id in (id_naive, id_offset, id_zulu):
                row = session.get(CoachingReportRecord, rep_id)
                assert row is not None
                assert row.created_at.tzinfo is not None
                assert row.created_at.utcoffset() == timedelta(0)
                assert row.created_at == datetime(2026, 10, 16, 10, 0, 0, tzinfo=UTC)
                assert row.created_at.isoformat() == "2026-10-16T10:00:00+00:00"
                assert row.payload["created_at"] == "2026-10-16T10:00:00+00:00"
            row_auto = session.get(CoachingReportRecord, id_auto)
            assert row_auto is not None
            _assert_utc(row_auto.created_at, earliest, latest)
            assert row_auto.created_at.isoformat() == rec_auto["created_at"]
            assert row_auto.payload["created_at"] == rec_auto["created_at"]

        # 6. Listing reports preserves exact normalized timestamps
        reports = store.list_coaching_reports(player_id)
        assert len(reports) == 4
        reports_by_id = {r["id"]: r for r in reports}
        for rep_id in (id_naive, id_offset, id_zulu):
            assert reports_by_id[rep_id]["created_at"] == "2026-10-16T10:00:00+00:00"
        assert reports_by_id[id_auto]["created_at"] == rec_auto["created_at"]
    finally:
        store.close()


def test_real_coaching_report_storage_atomic_rollback(postgres_database):
    config, engine, url = postgres_database
    command.upgrade(config, "head")

    rollback_identity = {"game_name": "RollbackPlayer", "tag_line": "TEST"}
    rollback_player_id = request_key("identity", rollback_identity)
    store = SQLPlayerStore(url, ttl_seconds=3600)
    failed_id = "fail-rep-postgres-1"

    original_upsert = store._upsert

    def failing_upsert(session, model, values):
        original_upsert(session, model, values)
        if model is CoachingReportRecord:
            raise SQLAlchemyError("Simulated database failure before commit")

    store._upsert = failing_upsert
    try:
        with pytest.raises(
            SQLAlchemyError, match="Simulated database failure before commit"
        ):
            store.save_coaching_report(
                rollback_player_id,
                {"title": "Aborted Report"},
                [],
                report_id=failed_id,
                identity=rollback_identity,
            )
        assert store.get_coaching_report(failed_id) is None
        assert store.list_coaching_reports(rollback_player_id) == []
    finally:
        store._upsert = original_upsert
        store.close()

    # Query from an independent session on engine to verify transaction rollback
    with Session(engine) as verify_session:
        assert verify_session.get(PlayerRecord, rollback_player_id) is None
        assert verify_session.get(CoachingReportRecord, failed_id) is None
        reports = (
            verify_session.execute(
                select(CoachingReportRecord).where(
                    CoachingReportRecord.player_id == rollback_player_id
                )
            )
            .scalars()
            .all()
        )
        assert len(reports) == 0


def test_real_coaching_report_read_back_fallback_and_rest(
    postgres_database, monkeypatch
):
    from backend.app.dependencies.auth_deps import get_current_user
    from backend.main import app

    config, engine, _ = postgres_database
    command.upgrade(config, "head")

    earliest = datetime.now(UTC)
    with TestClient(app) as client:
        service = app.state.player_service
        assert service is not None
        assert service.store is not None

        service.get_recent_matches = AsyncMock(return_value=[])
        service.get_rank = AsyncMock(side_effect=Exception("No rank available"))
        service.get_stats_overview = AsyncMock(
            side_effect=Exception("No stats available")
        )

        app.dependency_overrides[get_current_user] = lambda: {
            "id": "postgres-user-1",
            "email": "coach@test.com",
            "is_active": True,
            "is_admin": False,
        }
        try:
            # 1. Normal report generation on real PostgreSQL
            post_resp = client.post("/players/Chronicle/FNC/reports")
            assert post_resp.status_code == 200, post_resp.text
            post_data = post_resp.json()
            rep_id = post_data["id"]
            post_created_at = post_data["created_at"]
            assert rep_id != ""
            assert post_created_at is not None

            # 2. Storage failure on read-back -> returns 200 with fallback state
            original_get = service.store.get_coaching_report

            def failing_get(*args, **kwargs):
                raise SQLAlchemyError("Transient connection drop during read-back")

            service.store.get_coaching_report = failing_get
            try:
                fallback_resp = client.post("/players/Chronicle/FNC/reports")
                assert fallback_resp.status_code == 200, fallback_resp.text
                fallback_data = fallback_resp.json()
                fallback_id = fallback_data["id"]
                fallback_created_at = fallback_data["created_at"]
                assert fallback_id != ""
                assert fallback_created_at is not None
                assert fallback_id != rep_id
            finally:
                service.store.get_coaching_report = original_get

            # 3. Consistency between HTTP response and real persisted PostgreSQL record
            latest = datetime.now(UTC)
            persisted = service.store.get_coaching_report(fallback_id)
            assert persisted is not None
            assert persisted["id"] == fallback_id
            assert persisted["created_at"] == fallback_created_at
            assert persisted["payload"]["title"] == fallback_data["payload"]["title"]

            # 4. Direct session query confirms UTC timestamp and row persistence
            with Session(engine) as session:
                row = session.get(CoachingReportRecord, fallback_id)
                assert row is not None
                assert row.player_id == fallback_data["player_id"]
                _assert_utc(row.created_at, earliest, latest)
                assert row.created_at.isoformat() == fallback_created_at
                assert row.payload["created_at"] == fallback_created_at

            # 5. List endpoint finds both reports in PostgreSQL
            list_resp = client.get("/players/Chronicle/FNC/reports")
            assert list_resp.status_code == 200, list_resp.text
            list_data = list_resp.json()
            assert list_data["count"] == 2
            ids = [r["id"] for r in list_data["reports"]]
            assert rep_id in ids
            assert fallback_id in ids

            # 6. Single report endpoint retrieves fallback report with exact date
            get_resp = client.get(f"/players/Chronicle/FNC/reports/{fallback_id}")
            assert get_resp.status_code == 200, get_resp.text
            assert get_resp.json()["created_at"] == fallback_created_at
            assert (
                get_resp.json()["payload"]["title"] == fallback_data["payload"]["title"]
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

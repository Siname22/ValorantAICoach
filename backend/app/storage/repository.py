import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, delete, event, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .models import (
    Base,
    CoachingReportRecord,
    LinkedAccountRecord,
    MatchRecord,
    PlayerMatchHistory,
    PlayerRecord,
    PlayerSnapshot,
    UserRecord,
)


def request_key(operation: str, parameters: dict[str, Any]) -> str:
    encoded = json.dumps([operation, parameters], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def provider_datetime(value: int | str | None) -> datetime | None:
    try:
        if isinstance(value, int) and not isinstance(value, bool):
            return datetime.fromtimestamp(value / 1000, UTC)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value)
            return parsed.astimezone(UTC) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        pass
    return None


class SQLPlayerStore:
    def __init__(self, url: str, *, ttl_seconds: int, test_mode: bool = False) -> None:
        parsed = make_url(url)
        if parsed.drivername == "sqlite+pysqlite" and test_mode:
            options = {"connect_args": {"check_same_thread": False}}
            self._insert = sqlite_insert
        elif parsed.drivername == "postgresql+psycopg":
            options = {"connect_args": {"connect_timeout": 10}}
            self._insert = postgres_insert
        else:
            raise RuntimeError(
                "Player storage requires PostgreSQL (SQLite is test-only)."
            )
        self.engine = create_engine(parsed, pool_pre_ping=True, **options)
        self.ttl_seconds = ttl_seconds
        if parsed.drivername == "sqlite+pysqlite":
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        try:
            with Session(self.engine) as session:
                for table in Base.metadata.sorted_tables:
                    session.execute(select(table).limit(0))
        except SQLAlchemyError:
            self.close()
            raise RuntimeError(
                "Player storage is unavailable. Run the explicit Alembic migration "
                "and verify database access."
            ) from None

    @staticmethod
    def _enable_sqlite_foreign_keys(connection, connection_record) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    def _upsert(self, session: Session, model, values: dict[str, Any]) -> None:
        keys = [column.name for column in model.__table__.primary_key]
        statement = self._insert(model).values(**values)
        session.execute(
            statement.on_conflict_do_update(
                index_elements=keys,
                set_={key: value for key, value in values.items() if key not in keys},
            )
        )

    def get(self, key: str) -> Any | None:
        with Session(self.engine) as session:
            snapshot = session.get(PlayerSnapshot, key)
            if snapshot is None or snapshot.expires_at <= datetime.now(UTC):
                return None
            return snapshot.payload

    def put(
        self,
        key: str,
        operation: str,
        parameters: dict[str, Any],
        payload: Any,
        providers: list[str],
    ) -> None:
        json.dumps(payload, allow_nan=False)
        now = datetime.now(UTC)
        identity = {
            name: parameters[name]
            for name in ("game_name", "tag_line")
            if name in parameters
        }
        player_id = request_key("identity", identity) if len(identity) == 2 else None
        with Session(self.engine) as session, session.begin():
            if player_id is not None:
                player_values = {
                    "id": player_id,
                    **identity,
                    "observed_at": now,
                }
                if operation == "profile":
                    player_values.update(
                        {
                            name: payload.get(name)
                            for name in (
                                "game_name",
                                "tag_line",
                                "puuid",
                                "region",
                                "source",
                            )
                        }
                    )
                    self._upsert(session, PlayerRecord, player_values)
                else:
                    session.execute(
                        self._insert(PlayerRecord)
                        .values(**player_values)
                        .on_conflict_do_nothing(index_elements=["id"])
                    )
            if operation == "matches":
                # Shared match rows must acquire locks in the same order across players.
                for match in sorted(
                    payload, key=lambda item: (item["provider"], item["match_id"])
                ):
                    provider = match["provider"]
                    self._upsert(
                        session,
                        MatchRecord,
                        {
                            "provider": provider,
                            "match_id": match["match_id"],
                            "map_name": match["map_name"],
                            "mode": match["mode"],
                            "provider_timestamp": match["timestamp"],
                            "started_at": provider_datetime(match["timestamp"]),
                            "observed_at": now,
                        },
                    )
                    self._upsert(
                        session,
                        PlayerMatchHistory,
                        {
                            "player_id": player_id,
                            "provider": provider,
                            "match_id": match["match_id"],
                            "payload": match,
                            "observed_at": now,
                        },
                    )
            elif operation == "match_detail":
                info = payload["matchInfo"]
                values = {
                    "provider": "riot",
                    "match_id": info["matchId"],
                    "detail": payload,
                    "observed_at": now,
                }
                if "gameStartMillis" in info:
                    values.update(
                        {
                            "provider_timestamp": info["gameStartMillis"],
                            "started_at": provider_datetime(info["gameStartMillis"]),
                        }
                    )
                if "mapId" in info:
                    values["map_name"] = info["mapId"]
                self._upsert(session, MatchRecord, values)
            self._upsert(
                session,
                PlayerSnapshot,
                {
                    "key": key,
                    "operation": operation,
                    "player_id": player_id,
                    "payload": payload,
                    "providers": providers,
                    "observed_at": now,
                    "expires_at": now + timedelta(seconds=self.ttl_seconds),
                },
            )

    def save_coaching_report(
        self,
        player_id: str,
        payload: dict[str, Any],
        evidence: list[dict[str, Any]],
        provider: str = "orchestrator",
        report_id: str | None = None,
        identity: dict[str, str] | None = None,
    ) -> str:
        rep_id = report_id or str(uuid.uuid4())
        json.dumps(payload, allow_nan=False)
        json.dumps(evidence, allow_nan=False)
        now = datetime.now(UTC)
        with Session(self.engine) as session, session.begin():
            if identity:
                session.execute(
                    self._insert(PlayerRecord)
                    .values(
                        id=player_id,
                        game_name=identity.get("game_name", "Player"),
                        tag_line=identity.get("tag_line", "000"),
                        observed_at=now,
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
            self._upsert(
                session,
                CoachingReportRecord,
                {
                    "id": rep_id,
                    "player_id": player_id,
                    "schema_version": 1,
                    "provider": provider,
                    "payload": payload,
                    "evidence": evidence,
                    "created_at": now,
                },
            )
        return rep_id

    def get_coaching_report(self, report_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            record = session.get(CoachingReportRecord, report_id)
            if record is None:
                return None
            return {
                "id": record.id,
                "player_id": record.player_id,
                "schema_version": record.schema_version,
                "provider": record.provider,
                "payload": record.payload,
                "evidence": record.evidence,
                "created_at": record.created_at.isoformat(),
            }

    def get_match_record(
        self, match_id: str, provider: str = "riot"
    ) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            record = session.get(MatchRecord, (provider, match_id))
            if record is None or record.detail is None:
                return None
            return record.detail

    def list_player_match_details(
        self, player_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        with Session(self.engine) as session:
            statement = (
                select(MatchRecord)
                .join(
                    PlayerMatchHistory,
                    (PlayerMatchHistory.provider == MatchRecord.provider)
                    & (PlayerMatchHistory.match_id == MatchRecord.match_id),
                )
                .where(
                    PlayerMatchHistory.player_id == player_id,
                    MatchRecord.detail.isnot(None),
                )
                .order_by(PlayerMatchHistory.observed_at.desc())
                .limit(limit)
            )
            records = session.execute(statement).scalars().all()
            return [r.detail for r in records if r.detail is not None]

    def list_coaching_reports(
        self, player_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        with Session(self.engine) as session:
            statement = (
                select(CoachingReportRecord)
                .where(CoachingReportRecord.player_id == player_id)
                .order_by(CoachingReportRecord.created_at.desc())
                .limit(limit)
            )
            records = session.execute(statement).scalars().all()
            return [
                {
                    "id": record.id,
                    "player_id": record.player_id,
                    "schema_version": record.schema_version,
                    "provider": record.provider,
                    "payload": record.payload,
                    "evidence": record.evidence,
                    "created_at": record.created_at.isoformat(),
                }
                for record in records
            ]

    def ping(self) -> bool:
        try:
            with Session(self.engine) as session:
                session.execute(select(1))
            return True
        except Exception:
            return False

    def prune_expired_snapshots(self) -> int:
        now = datetime.now(UTC)
        with Session(self.engine) as session, session.begin():
            statement = delete(PlayerSnapshot).where(PlayerSnapshot.expires_at <= now)
            result = session.execute(statement)
            return int(result.rowcount or 0)

    def invalidate_player_cache(self, player_id: str) -> int:
        with Session(self.engine) as session, session.begin():
            statement = delete(PlayerSnapshot).where(
                PlayerSnapshot.player_id == player_id
            )
            result = session.execute(statement)
            return int(result.rowcount or 0)

    def create_user(self, email: str, hashed_password: str) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        now = datetime.now(UTC)
        user_id = str(uuid.uuid4())
        with Session(self.engine) as session, session.begin():
            existing = session.execute(
                select(UserRecord).where(UserRecord.email == normalized_email)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError("User with this email already exists")
            user = UserRecord(
                id=user_id,
                email=normalized_email,
                hashed_password=hashed_password,
                is_active=True,
                created_at=now,
            )
            session.add(user)
        return {
            "id": user_id,
            "email": normalized_email,
            "is_active": True,
            "created_at": now.isoformat(),
        }

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        normalized_email = email.strip().lower()
        with Session(self.engine) as session:
            user = session.execute(
                select(UserRecord).where(UserRecord.email == normalized_email)
            ).scalar_one_or_none()
            if user is None:
                return None
            return {
                "id": user.id,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            }

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            user = session.get(UserRecord, user_id)
            if user is None:
                return None
            return {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            }

    def link_player_account(
        self,
        user_id: str,
        game_name: str,
        tag_line: str,
        puuid: str | None = None,
        region: str | None = None,
        is_primary: bool = False,
    ) -> dict[str, Any]:
        link_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        with Session(self.engine) as session, session.begin():
            if is_primary:
                session.execute(
                    update(LinkedAccountRecord)
                    .where(LinkedAccountRecord.user_id == user_id)
                    .values(is_primary=False)
                )
            account = LinkedAccountRecord(
                id=link_id,
                user_id=user_id,
                game_name=game_name,
                tag_line=tag_line,
                puuid=puuid,
                region=region,
                is_primary=is_primary,
                linked_at=now,
            )
            session.add(account)
        return {
            "id": link_id,
            "user_id": user_id,
            "game_name": game_name,
            "tag_line": tag_line,
            "puuid": puuid,
            "region": region,
            "is_primary": is_primary,
            "linked_at": now.isoformat(),
            "last_synced_at": None,
        }

    def list_linked_accounts(self, user_id: str) -> list[dict[str, Any]]:
        with Session(self.engine) as session:
            accounts = (
                session.execute(
                    select(LinkedAccountRecord)
                    .where(LinkedAccountRecord.user_id == user_id)
                    .order_by(LinkedAccountRecord.linked_at.desc())
                )
                .scalars()
                .all()
            )
            return [
                {
                    "id": acc.id,
                    "user_id": acc.user_id,
                    "game_name": acc.game_name,
                    "tag_line": acc.tag_line,
                    "puuid": acc.puuid,
                    "region": acc.region,
                    "is_primary": acc.is_primary,
                    "linked_at": acc.linked_at.isoformat(),
                    "last_synced_at": (
                        acc.last_synced_at.isoformat() if acc.last_synced_at else None
                    ),
                }
                for acc in accounts
            ]

    def get_linked_account(
        self, account_id: str, user_id: str
    ) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            acc = session.execute(
                select(LinkedAccountRecord).where(
                    LinkedAccountRecord.id == account_id,
                    LinkedAccountRecord.user_id == user_id,
                )
            ).scalar_one_or_none()
            if acc is None:
                return None
            return {
                "id": acc.id,
                "user_id": acc.user_id,
                "game_name": acc.game_name,
                "tag_line": acc.tag_line,
                "puuid": acc.puuid,
                "region": acc.region,
                "is_primary": acc.is_primary,
                "linked_at": acc.linked_at.isoformat(),
                "last_synced_at": (
                    acc.last_synced_at.isoformat() if acc.last_synced_at else None
                ),
            }

    def delete_linked_account(self, account_id: str, user_id: str) -> bool:
        with Session(self.engine) as session, session.begin():
            result = session.execute(
                delete(LinkedAccountRecord).where(
                    LinkedAccountRecord.id == account_id,
                    LinkedAccountRecord.user_id == user_id,
                )
            )
            return bool(result.rowcount and result.rowcount > 0)

    def get_tracked_accounts(self) -> list[dict[str, Any]]:
        with Session(self.engine) as session:
            accounts = (
                session.execute(
                    select(LinkedAccountRecord)
                    .where(LinkedAccountRecord.is_primary.is_(True))
                    .order_by(LinkedAccountRecord.linked_at.desc())
                )
                .scalars()
                .all()
            )
            return [
                {
                    "id": acc.id,
                    "user_id": acc.user_id,
                    "game_name": acc.game_name,
                    "tag_line": acc.tag_line,
                    "puuid": acc.puuid,
                    "region": acc.region,
                    "is_primary": acc.is_primary,
                    "linked_at": acc.linked_at.isoformat(),
                    "last_synced_at": (
                        acc.last_synced_at.isoformat() if acc.last_synced_at else None
                    ),
                }
                for acc in accounts
            ]

    def update_account_sync_time(self, game_name: str, tag_line: str) -> bool:
        now = datetime.now(UTC)
        with Session(self.engine) as session, session.begin():
            result = session.execute(
                update(LinkedAccountRecord)
                .where(
                    LinkedAccountRecord.game_name == game_name,
                    LinkedAccountRecord.tag_line == tag_line,
                )
                .values(last_synced_at=now)
            )
            return bool(result.rowcount and result.rowcount > 0)

    def close(self) -> None:
        self.engine.dispose()

import asyncio
import logging
from typing import Annotated, Any
from weakref import WeakValueDictionary

from pydantic import AfterValidator, TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.app.services.player_service import (
    PlayerMatch,
    PlayerProfile,
    PlayerRank,
    PlayerService,
    PlayerServiceUnavailableError,
    PlayerStatsOverview,
)

from .repository import SQLPlayerStore, request_key

logger = logging.getLogger(__name__)


def _validate_match_detail(value: dict[str, Any]) -> dict[str, Any]:
    info = value.get("matchInfo")
    if (
        not isinstance(info, dict)
        or not isinstance(info.get("matchId"), str)
        or not info["matchId"]
    ):
        raise ValueError("Match detail must contain matchInfo.matchId")
    return value


MatchDetail = Annotated[dict[str, Any], AfterValidator(_validate_match_detail)]


class PersistentPlayerService(PlayerService):
    def __init__(self, *, store: SQLPlayerStore, **providers) -> None:
        super().__init__(**providers)
        self.store = store
        self._locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()

    async def _storage_call(self, operation, *args):
        try:
            return await asyncio.to_thread(operation, *args)
        except SQLAlchemyError as error:
            logger.warning("Player storage failed: %s", type(error).__name__)
            raise PlayerServiceUnavailableError(
                "Player storage is unavailable."
            ) from None

    @staticmethod
    async def _model_result(fetch):
        value = await fetch()
        return value, [value.source] if value.source else []

    async def _cached(self, operation, parameters, adapter, fetch):
        key = request_key(operation, parameters)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = await self._storage_call(self.store.get, key)
            if cached is not None:
                try:
                    return adapter.validate_python(cached)
                except ValidationError:
                    logger.warning("Invalid cached player data; refreshing")
            value, providers = await fetch()
            await self._storage_call(
                self.store.put,
                key,
                operation,
                parameters,
                adapter.dump_python(value, mode="json"),
                providers,
            )
            return value

    async def get_player(self, game_name: str, tag_line: str) -> PlayerProfile:
        fetch = super().get_player
        return await self._cached(
            "profile",
            {"game_name": game_name, "tag_line": tag_line},
            TypeAdapter(PlayerProfile),
            lambda: self._model_result(lambda: fetch(game_name, tag_line)),
        )

    async def get_rank(
        self,
        game_name: str,
        tag_line: str,
        puuid: str | None = None,
        *,
        region: str | None = None,
    ) -> PlayerRank:
        fetch = super().get_rank
        return await self._cached(
            "rank",
            {
                "game_name": game_name,
                "tag_line": tag_line,
                "puuid": puuid,
                "region": region,
            },
            TypeAdapter(PlayerRank),
            lambda: self._model_result(
                lambda: fetch(game_name, tag_line, puuid, region=region)
            ),
        )

    async def get_stats_overview(
        self, game_name: str, tag_line: str
    ) -> PlayerStatsOverview:
        fetch = super().get_stats_overview
        return await self._cached(
            "stats",
            {"game_name": game_name, "tag_line": tag_line},
            TypeAdapter(PlayerStatsOverview),
            lambda: self._model_result(lambda: fetch(game_name, tag_line)),
        )

    async def get_recent_matches(
        self,
        game_name: str,
        tag_line: str,
        puuid: str | None = None,
        *,
        region: str | None = None,
        limit: int = 10,
    ) -> list[PlayerMatch]:
        if not 1 <= limit <= 20:
            raise ValueError("Match limit must be between 1 and 20")

        async def fetch():
            matches, provider = await self._get_recent_matches_with_source(
                game_name, tag_line, puuid, region=region, limit=limit
            )
            return matches, [provider]

        return await self._cached(
            "matches",
            {
                "game_name": game_name,
                "tag_line": tag_line,
                "puuid": puuid,
                "region": region,
                "limit": limit,
            },
            TypeAdapter(list[PlayerMatch]),
            fetch,
        )

    async def get_match(self, match_id: str) -> dict[str, Any]:
        original = super().get_match

        async def fetch():
            return await original(match_id), ["riot"]

        return await self._cached(
            "match_detail", {"match_id": match_id}, TypeAdapter(MatchDetail), fetch
        )

    async def generate_coaching_report(
        self,
        game_name: str,
        tag_line: str,
        *,
        region: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        report = await super().generate_coaching_report(
            game_name, tag_line, region=region, limit=limit
        )
        player_id = request_key(
            "identity", {"game_name": game_name, "tag_line": tag_line}
        )
        report_id = report.get("report_id")
        evidence = report.get("evidence", [])
        saved_id = await self._storage_call(
            self.store.save_coaching_report,
            player_id,
            report,
            evidence,
            "orchestrator",
            report_id,
            {"game_name": game_name, "tag_line": tag_line},
        )
        return {
            "id": saved_id,
            "player_id": player_id,
            "schema_version": 1,
            "provider": "orchestrator",
            "payload": report,
            "evidence": evidence,
            "created_at": report.get("created_at") or "",
        }

    async def get_coaching_report(self, report_id: str) -> dict[str, Any] | None:
        return await self._storage_call(self.store.get_coaching_report, report_id)

    async def list_coaching_reports(
        self, game_name: str, tag_line: str, *, limit: int = 10
    ) -> list[dict[str, Any]]:
        player_id = request_key(
            "identity", {"game_name": game_name, "tag_line": tag_line}
        )
        return await self._storage_call(
            self.store.list_coaching_reports, player_id, limit
        )

    async def ready(self) -> dict[str, Any]:
        db_ok = await self._storage_call(self.store.ping)
        configured = any(p is not None for p in self._providers)
        if not db_ok:
            status = "unhealthy"
        elif configured:
            status = "ready"
        else:
            status = "degraded"
        return {
            "status": status,
            "database": "connected" if db_ok else "disconnected",
            "providers_configured": len(self._providers),
        }

    async def prune_expired_cache(self) -> int:
        return await self._storage_call(self.store.prune_expired_snapshots)

    async def invalidate_player_cache(self, game_name: str, tag_line: str) -> int:
        player_id = request_key(
            "identity", {"game_name": game_name, "tag_line": tag_line}
        )
        return await self._storage_call(self.store.invalidate_player_cache, player_id)

    async def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        return await self._storage_call(self.store.create_user, email, password_hash)

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._storage_call(self.store.get_user_by_email, email)

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await self._storage_call(self.store.get_user_by_id, user_id)

    async def link_player_account(
        self,
        user_id: str,
        game_name: str,
        tag_line: str,
        puuid: str | None = None,
        region: str | None = None,
        is_primary: bool = False,
    ) -> dict[str, Any]:
        return await self._storage_call(
            self.store.link_player_account,
            user_id,
            game_name,
            tag_line,
            puuid,
            region,
            is_primary,
        )

    async def list_linked_accounts(self, user_id: str) -> list[dict[str, Any]]:
        return await self._storage_call(self.store.list_linked_accounts, user_id)

    async def delete_linked_account(self, account_id: str, user_id: str) -> bool:
        return await self._storage_call(
            self.store.delete_linked_account, account_id, user_id
        )

    async def close(self) -> None:
        try:
            await super().close()
        finally:
            await asyncio.to_thread(self.store.close)

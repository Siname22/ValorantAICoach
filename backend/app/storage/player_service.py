import asyncio
import logging
from typing import Annotated, Any
from weakref import WeakValueDictionary

from pydantic import AfterValidator, TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.timeline_schemas import PlayerTimelineAnalyticsResponse
from backend.app.services.player_service import (
    PlayerMatch,
    PlayerProfile,
    PlayerRank,
    PlayerService,
    PlayerServiceUnavailableError,
    PlayerStatsOverview,
)
from backend.app.services.timeline_service import TimelineService

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

    async def get_player(
        self, game_name: str, tag_line: str, *, region: str | None = None
    ) -> PlayerProfile:
        fetch = super().get_player
        return await self._cached(
            "profile",
            {"game_name": game_name, "tag_line": tag_line, "region": region},
            TypeAdapter(PlayerProfile),
            lambda: self._model_result(
                lambda: fetch(game_name, tag_line, region=region)
            ),
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
            try:
                return await original(match_id), ["riot"]
            except PlayerServiceUnavailableError:
                stored = await self._storage_call(self.store.get_match_record, match_id)
                if stored is not None:
                    return stored, ["stored"]
                raise

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
        saved_record = None
        try:
            saved_record = await self.get_coaching_report(
                saved_id, game_name=game_name, tag_line=tag_line
            )
        except PlayerServiceUnavailableError:
            logger.warning(
                "Coaching report %s saved, but read-back failed; returning payload",
                saved_id,
            )
        if saved_record is not None:
            return saved_record
        return {
            "id": saved_id,
            "player_id": player_id,
            "schema_version": 1,
            "provider": "orchestrator",
            "payload": report,
            "evidence": evidence,
            "created_at": report.get("created_at") or "",
        }

    async def get_coaching_report(
        self,
        report_id: str,
        *,
        game_name: str | None = None,
        tag_line: str | None = None,
    ) -> dict[str, Any] | None:
        report = await self._storage_call(self.store.get_coaching_report, report_id)
        if report is None:
            return None
        if game_name and tag_line:
            payload = report.get("payload") or {}
            rep_name = report.get("player_name") or payload.get("player_name")
            rep_tag = report.get("player_tag") or payload.get("player_tag")
            if not rep_name or not rep_tag:
                title = payload.get("title", "")
                if ":" in title and "#" in title:
                    try:
                        name_tag_part = title.split(":", 1)[1].strip().split()[0]
                        if "#" in name_tag_part:
                            t_name, t_tag = name_tag_part.split("#", 1)
                            rep_name = rep_name or t_name
                            rep_tag = rep_tag or t_tag
                    except Exception:
                        pass
            if rep_name and rep_tag:
                if (
                    rep_name.casefold() != game_name.casefold()
                    or rep_tag.casefold() != tag_line.casefold()
                ):
                    return None
            else:
                expected_player_id = request_key(
                    "identity", {"game_name": game_name, "tag_line": tag_line}
                )
                rep_player_id = report.get("player_id")
                if rep_player_id and rep_player_id != expected_player_id:
                    return None
        return report

    async def list_coaching_reports(
        self, game_name: str, tag_line: str, *, limit: int = 10
    ) -> list[dict[str, Any]]:
        player_id = request_key(
            "identity", {"game_name": game_name, "tag_line": tag_line}
        )
        return await self._storage_call(
            self.store.list_coaching_reports,
            player_id,
            limit,
            game_name,
            tag_line,
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

    async def create_user(
        self, email: str, password_hash: str, is_admin: bool = False
    ) -> dict[str, Any]:
        return await self._storage_call(
            self.store.create_user, email, password_hash, is_admin
        )

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._storage_call(self.store.get_user_by_email, email)

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await self._storage_call(self.store.get_user_by_id, user_id)

    async def update_password_hash(self, user_id: str, password_hash: str) -> bool:
        return await self._storage_call(
            self.store.update_password_hash, user_id, password_hash
        )

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

    async def sync_player_coaching(
        self, game_name: str, tag_line: str, *, region: str | None = None
    ) -> dict[str, Any]:
        result = await super().sync_player_coaching(game_name, tag_line, region=region)
        await self._storage_call(
            self.store.update_account_sync_time, game_name, tag_line
        )
        return result

    async def sync_all_tracked_accounts(self) -> dict[str, Any]:
        tracked = await self._storage_call(self.store.get_tracked_accounts)
        details = []
        for account in tracked:
            try:
                res = await self.sync_player_coaching(
                    account["game_name"],
                    account["tag_line"],
                    region=account.get("region"),
                )
                details.append(res)
            except Exception as err:
                details.append(
                    {
                        "synced": False,
                        "game_name": account["game_name"],
                        "tag_line": account["tag_line"],
                        "error": str(err),
                    }
                )
        return {
            "synced_accounts_count": len(tracked),
            "details": details,
        }

    async def ingest_vision_match(
        self,
        match: PlayerMatch,
        game_name: str,
        tag_line: str,
    ) -> bool:
        params = {"game_name": game_name, "tag_line": tag_line}
        key = request_key("matches", params)
        await self._storage_call(
            self.store.put,
            key,
            "matches",
            params,
            [match.model_dump()],
            ["vision"],
        )
        return True

    async def get_player_timeline_analytics(
        self,
        game_name: str,
        tag_line: str,
        *,
        region: str | None = None,
        limit: int = 5,
    ) -> PlayerTimelineAnalyticsResponse:
        player_key = request_key(
            "identity", {"game_name": game_name, "tag_line": tag_line}
        )
        stored_details = await self._storage_call(
            self.store.list_player_match_details, player_key, limit
        )
        if stored_details:
            player_ident = None
            try:
                profile = await self.get_player(game_name, tag_line, region=region)
                player_ident = profile.puuid
            except Exception:
                pass

            if not player_ident:
                stored_puuid = await self._storage_call(
                    self.store.get_player_puuid, player_key
                )
                if stored_puuid:
                    player_ident = stored_puuid

            match_summaries = await self._storage_call(
                self.store.get_player_match_summaries, player_key, limit
            )

            resolved_puuid = None
            for detail in stored_details:
                info = detail.get("matchInfo", {})
                mid = info.get("matchId")
                summary = match_summaries.get(mid)
                players = detail.get("players", [])

                if not player_ident and summary:
                    target_agent = summary.get("agent_name")
                    target_result = summary.get("result")
                    for p in players:
                        char = p.get("characterId") or ""
                        if target_agent and (
                            char == target_agent or target_agent.lower() in char.lower()
                        ):
                            detail["friendlyTeam"] = p.get("teamId")
                            resolved_puuid = p.get("puuid")
                            break
                        if target_result:
                            teams = detail.get("teams", [])
                            winning_team = next(
                                (
                                    t.get("teamId")
                                    for t in teams
                                    if t.get("won") is True
                                ),
                                None,
                            )
                            if winning_team and target_result == "Victory":
                                detail["friendlyTeam"] = winning_team
                            elif winning_team and target_result == "Defeat":
                                detail["friendlyTeam"] = (
                                    "Blue" if winning_team == "Red" else "Red"
                                )

            if not player_ident:
                player_ident = resolved_puuid or f"{game_name}#{tag_line}"

            return TimelineService.aggregate_player_timeline_analytics(
                stored_details,
                player_identifier=player_ident,
                game_name=game_name,
                tag_line=tag_line,
            )
        return await super().get_player_timeline_analytics(
            game_name, tag_line, region=region, limit=limit
        )

    async def close(self) -> None:
        try:
            await super().close()
        finally:
            await asyncio.to_thread(self.store.close)

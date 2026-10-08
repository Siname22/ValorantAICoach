from typing import Annotated, Any, Literal

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.player_schemas import (
    CoachingReportResponse,
    CoachingReportsListResponse,
    PlayerMatchesResponse,
    PlayerMatchResponse,
    PlayerProfileResponse,
    PlayerProgressionResponse,
    PlayerRankResponse,
    PlayerSyncResponse,
)
from backend.app.services.player_service import (
    CompletePlayerProfile,
    PlayerService,
    PlayerStatsOverview,
)
from fastapi import APIRouter, Depends, HTTPException, Path, Query

router = APIRouter(prefix="/players", tags=["players"])

GameName = Annotated[str, Path(min_length=1, max_length=64, pattern=r".*\S.*")]
TagLine = Annotated[str, Path(min_length=1, max_length=16, pattern=r".*\S.*")]
Region = Literal["eu", "na", "ap", "kr", "br", "latam"]
Service = Annotated[PlayerService, Depends(get_player_service)]
RegionQuery = Annotated[
    Region | None,
    Query(description="Henrik region override; otherwise resolved from the account"),
]
ERROR_RESPONSES = {
    404: {"description": "Resource not found by all applicable providers"},
    502: {"description": "Player data could not be processed"},
    503: {"description": "No supported provider is configured or available"},
}


@router.get(
    "/{game_name}/{tag_line}",
    response_model=PlayerProfileResponse,
    summary="Get complete player profile",
    responses=ERROR_RESPONSES,
)
async def get_player_profile(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
) -> PlayerProfileResponse:
    profile = await service.get_complete_player_profile(game_name, tag_line)
    return PlayerProfileResponse(**profile.model_dump())


@router.get(
    "/{game_name}/{tag_line}/rank",
    response_model=PlayerRankResponse,
    summary="Get player rank",
    description="Current rank from Tracker or Henrik; Riot does not expose player RR.",
    responses=ERROR_RESPONSES,
)
async def get_player_rank(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    region: RegionQuery = None,
) -> PlayerRankResponse:
    rank = await service.get_rank(game_name, tag_line, region=region)
    return PlayerRankResponse(**rank.model_dump())


@router.get(
    "/{game_name}/{tag_line}/matches",
    response_model=PlayerMatchesResponse,
    summary="Get recent matches",
    responses=ERROR_RESPONSES,
)
async def get_player_matches(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    region: RegionQuery = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> PlayerMatchesResponse:
    matches = await service.get_recent_matches(
        game_name, tag_line, region=region, limit=limit
    )
    return PlayerMatchesResponse(
        matches=[PlayerMatchResponse(**match.model_dump()) for match in matches],
        count=len(matches),
    )


@router.get(
    "/{game_name}/{tag_line}/stats",
    response_model=PlayerStatsOverview,
    responses=ERROR_RESPONSES,
)
async def get_player_stats(
    game_name: GameName, tag_line: TagLine, service: Service
) -> PlayerStatsOverview:
    return await service.get_stats_overview(game_name, tag_line)


@router.get(
    "/{game_name}/{tag_line}/overview",
    response_model=CompletePlayerProfile,
    responses=ERROR_RESPONSES,
)
async def get_player_overview(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> CompletePlayerProfile:
    return await service.get_player_overview(game_name, tag_line, limit=limit)


@router.post(
    "/{game_name}/{tag_line}/reports",
    response_model=CoachingReportResponse,
    summary="Generate grounded AI coaching report",
    description=(
        "Analyzes recent matches across combat, economy, and role execution "
        "using the specialized multi-agent orchestrator."
    ),
    responses=ERROR_RESPONSES,
)
async def generate_coaching_report(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    region: RegionQuery = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> CoachingReportResponse:
    report = await service.generate_coaching_report(
        game_name, tag_line, region=region, limit=limit
    )
    rep_id = report.get("id") or report.get("report_id") or "report-gen"
    payload = report.get("payload") or report
    evidence = report.get("evidence") or payload.get("evidence", [])
    created_at = report.get("created_at") or None
    return CoachingReportResponse(
        id=rep_id,
        player_id=report.get("player_id"),
        schema_version=report.get("schema_version", 1),
        provider=report.get("provider", "orchestrator"),
        payload=payload,
        evidence=evidence,
        created_at=created_at,
    )


@router.get(
    "/{game_name}/{tag_line}/reports",
    response_model=CoachingReportsListResponse,
    summary="List saved coaching reports",
    responses=ERROR_RESPONSES,
)
async def list_coaching_reports(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> CoachingReportsListResponse:
    reports = await service.list_coaching_reports(game_name, tag_line, limit=limit)
    return CoachingReportsListResponse(
        reports=[CoachingReportResponse(**r) for r in reports],
        count=len(reports),
    )


@router.get(
    "/{game_name}/{tag_line}/reports/{report_id}",
    response_model=CoachingReportResponse,
    summary="Get specific coaching report",
    responses={**ERROR_RESPONSES, 404: {"description": "Report not found"}},
)
async def get_coaching_report(
    game_name: GameName,
    tag_line: TagLine,
    report_id: Annotated[str, Path(min_length=1, max_length=64)],
    service: Service,
) -> CoachingReportResponse:
    report = await service.get_coaching_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Coaching report not found.")
    return CoachingReportResponse(**report)


@router.delete(
    "/{game_name}/{tag_line}/cache",
    summary="Invalidate player cached data",
    description=(
        "Clears stored snapshots for the specified player, forcing subsequent "
        "queries to fetch fresh data."
    ),
    responses=ERROR_RESPONSES,
)
async def invalidate_player_cache(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
) -> dict[str, Any]:
    count = await service.invalidate_player_cache(game_name, tag_line)
    return {"status": "ok", "invalidated_snapshots": count}


@router.get(
    "/{game_name}/{tag_line}/progression",
    response_model=PlayerProgressionResponse,
    summary="Get long-term player progression and trajectory",
    description=(
        "Analyzes rolling trends across match history, evaluates previous coaching "
        "reports to distinguish resolved weaknesses from current bottlenecks, and "
        "provides per-agent performance trajectories."
    ),
    responses=ERROR_RESPONSES,
)
async def get_player_progression(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
) -> PlayerProgressionResponse:
    progression = await service.get_player_progression(game_name, tag_line)
    return PlayerProgressionResponse(**progression)


@router.post(
    "/{game_name}/{tag_line}/sync",
    response_model=PlayerSyncResponse,
    summary="Synchronize latest matches and coaching reports",
    description=(
        "Forces a fresh fetch of matches for the player and automatically generates "
        "a new multi-agent coaching report if new matches were recorded."
    ),
    responses=ERROR_RESPONSES,
)
async def sync_player(
    game_name: GameName,
    tag_line: TagLine,
    service: Service,
    region: RegionQuery = None,
) -> PlayerSyncResponse:
    sync_result = await service.sync_player_coaching(game_name, tag_line, region=region)
    return PlayerSyncResponse(**sync_result)

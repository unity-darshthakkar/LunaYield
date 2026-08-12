"""Mission history API endpoints for durable run queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query, Request

from app.db.repository import (
    AuditEventRepository,
    MissionRunRepository,
    MissionSnapshotRepository,
)
from app.schemas import (
    AuditEventHistoryItem,
    AuditEventListResponse,
    MissionRunDetailResponse,
    MissionRunHistoryItem,
    MissionRunListResponse,
    MissionSnapshotHistoryItem,
    MissionSnapshotListResponse,
)

if TYPE_CHECKING:
    pass


router = APIRouter(prefix="/api", tags=["history"])


def _get_persistence_service(request: Request):
    """Get MissionPersistenceService from app state."""
    return request.app.state.persistence_service


def _get_session_factory(request: Request):
    """Get database session factory from app state."""
    return request.app.state.db_session_factory


@router.get("/missions/{mission_id}/runs", response_model=MissionRunListResponse)
async def list_mission_runs(
    mission_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> MissionRunListResponse:
    """List all mission runs for a given mission."""
    with _get_session_factory(request)() as session:
        run_repo = MissionRunRepository(session)
        runs = run_repo.list_for_mission(mission_id, limit=limit)

    return MissionRunListResponse(
        mission_id=mission_id,
        runs=[
            MissionRunHistoryItem(
                run_id=r.run_id,
                mission_id=r.mission_id,
                label=r.label,
                seed_mission_id=r.seed_mission_id,
                started_at=r.started_at,
                ended_at=r.ended_at,
                final_status=r.final_status,
            )
            for r in runs
        ],
        limit=limit,
    )


@router.get("/runs/{run_id}", response_model=MissionRunDetailResponse)
async def get_mission_run(run_id: str, request: Request) -> MissionRunDetailResponse:
    """Get a specific mission run by ID."""
    with _get_session_factory(request)() as session:
        run_repo = MissionRunRepository(session)
        run = run_repo.get(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Mission run {run_id} not found",
        )

    return MissionRunDetailResponse(
        run_id=run.run_id,
        mission_id=run.mission_id,
        label=run.label,
        seed_mission_id=run.seed_mission_id,
        started_at=run.started_at,
        ended_at=run.ended_at,
        final_status=run.final_status,
    )


@router.get("/runs/{run_id}/snapshots", response_model=MissionSnapshotListResponse)
async def list_run_snapshots(
    run_id: str,
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> MissionSnapshotListResponse:
    """List snapshots for a mission run, ordered by sequence."""
    with _get_session_factory(request)() as session:
        run_repo = MissionRunRepository(session)
        run = run_repo.get(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"Mission run {run_id} not found",
            )
        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)
        # Apply limit and offset manually
        sliced = snapshots[offset : offset + limit]

        # Convert to history items - parse resources once per snapshot
        snapshot_items = []
        for s in sliced:
            resources = s.to_resources_dict()
            snapshot_items.append(
                MissionSnapshotHistoryItem(
                    snapshot_id=s.snapshot_id,
                    sequence=s.sequence,
                    status=s.status,
                    elapsed_s=s.elapsed_s,
                    created_at=s.created_at,
                    battery_pct=resources.get("battery_pct"),
                    temperature_c=resources.get("temperature_c"),
                    storage_pct=resources.get("storage_pct"),
                    anomaly_active=s.anomaly_active,
                )
            )

    return MissionSnapshotListResponse(
        run_id=run_id,
        snapshots=snapshot_items,
        limit=limit,
        offset=offset,
        total_snapshots_available=len(snapshots),
    )


@router.get("/runs/{run_id}/audit", response_model=AuditEventListResponse)
async def list_run_audit_events(
    run_id: str,
    request: Request,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> AuditEventListResponse:
    """List audit events for a mission run, ordered by sequence."""
    with _get_session_factory(request)() as session:
        run_repo = MissionRunRepository(session)
        run = run_repo.get(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"Mission run {run_id} not found",
            )
        audit_repo = AuditEventRepository(session)
        events = audit_repo.list_for_run(run_id)
        # Apply limit and offset manually
        sliced = events[offset : offset + limit]

        audit_items = [
            AuditEventHistoryItem(
                audit_id=e.event_id,
                event_type=e.event_type,
                description=e.description,
                timestamp=e.timestamp,
                sequence=e.sequence,
            )
            for e in sliced
        ]

    return AuditEventListResponse(
        run_id=run_id,
        audit_events=audit_items,
        limit=limit,
        offset=offset,
        total_audit_events_available=len(events),
    )

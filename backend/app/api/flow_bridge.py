"""Flow Bridge API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.flow_bridge import FlowBridge, FlowTaskType, FlowTaskStatus
from app.models.google_account import GoogleAccount
from app.schemas.flow_bridge import FlowBridgeCreate, FlowBridgeUpdate, FlowBridgeRead, FlowBridgeList, FlowExport, FlowImport
from app.services.flow_account_fallback import (
    AllGoogleAccountsFailed,
    GoogleUnreachable,
    run_fallback_for_task,
)
from app.services.flow_browser_execution import (
    AllBrowserAccountsFailed,
    BrowserUnreachable,
    run_browser_execution,
)
import uuid

router = APIRouter(prefix="/flow", tags=["flow-bridge"])

# Task statuses from which an account (re)resolution may run. Completed /
# imported / in-progress tasks must not be re-bound to another account.
_EXECUTABLE_STATUSES = {
    FlowTaskStatus.PENDING,
    FlowTaskStatus.READY_FOR_FLOW,
    FlowTaskStatus.FAILED,
}


async def _get_flow_task_or_404(db: AsyncSession, project_id: str, task_id: str) -> FlowBridge:
    result = await db.execute(
        select(FlowBridge).where(
            FlowBridge.id == uuid.UUID(task_id),
            FlowBridge.project_id == uuid.UUID(project_id),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Flow task not found")
    return task


async def _run_account_fallback(
    db: AsyncSession, user_id: str, task: FlowBridge
) -> FlowBridge:
    """Resolve a working Google account for the task (with fallback).

    On success returns the task (status READY_FOR_FLOW, bound to the working
    account). When every account fails the task is already persisted as
    FAILED with a per-account error_message — the 502 only makes the
    failure loud at the HTTP layer instead of a silent 200.
    """
    try:
        return await run_fallback_for_task(db, uuid.UUID(user_id), task)
    except AllGoogleAccountsFailed as e:
        raise HTTPException(status_code=502, detail=str(e))
    except GoogleUnreachable as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("", response_model=FlowBridgeRead, status_code=status.HTTP_201_CREATED)
async def create_flow_task(
    task_data: FlowBridgeCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a Flow Bridge task"""
    await _verify_project_access(str(task_data.project_id), user_id, db)
    user_uuid = uuid.UUID(user_id)

    # Verify google account if provided
    if task_data.google_account_id:
        result = await db.execute(
            select(GoogleAccount).where(
                GoogleAccount.id == task_data.google_account_id,
                GoogleAccount.user_id == user_uuid,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Google account not found")

    task = FlowBridge(**task_data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{project_id}", response_model=FlowBridgeList)
async def list_flow_tasks(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: FlowTaskStatus | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
):
    """List Flow Bridge tasks for a project"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    query = select(FlowBridge).where(FlowBridge.project_id == project_uuid)

    if status:
        query = query.where(FlowBridge.status == status)
    if episode_id:
        query = query.where(FlowBridge.episode_id == uuid.UUID(episode_id))
    if scene_id:
        query = query.where(FlowBridge.scene_id == uuid.UUID(scene_id))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(FlowBridge.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return FlowBridgeList(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{project_id}/{task_id}", response_model=FlowBridgeRead)
async def get_flow_task(
    project_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific Flow Bridge task"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    task_uuid = uuid.UUID(task_id)

    result = await db.execute(
        select(FlowBridge).where(FlowBridge.id == task_uuid, FlowBridge.project_id == project_uuid)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Flow task not found")
    return task


@router.patch("/{project_id}/{task_id}", response_model=FlowBridgeRead)
async def update_flow_task(
    project_id: str,
    task_id: str,
    task_data: FlowBridgeUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a Flow Bridge task"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    task_uuid = uuid.UUID(task_id)
    user_uuid = uuid.UUID(user_id)

    result = await db.execute(
        select(FlowBridge).where(FlowBridge.id == task_uuid, FlowBridge.project_id == project_uuid)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Flow task not found")

    # Verify google account if changed
    if task_data.google_account_id:
        acct_result = await db.execute(
            select(GoogleAccount).where(
                GoogleAccount.id == task_data.google_account_id,
                GoogleAccount.user_id == user_uuid,
            )
        )
        if not acct_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Google account not found")

    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    # Set completed_at if status changed to completed
    if task_data.status == FlowTaskStatus.COMPLETED and not task.completed_at:
        from datetime import datetime, timezone
        task.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{project_id}/{task_id}/execute", response_model=FlowBridgeRead)
async def execute_flow_task(
    project_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a usable Google account for the task and mark it ready for Flow.

    Tries the task's pinned account first, then the user's other enabled
    accounts (by account_index). An account is skipped when its quota is
    exhausted (429), its token is invalid, or its refresh fails; the first
    account whose token verifies against Google wins and is bound to the
    task. When every account fails the task is persisted as FAILED with a
    per-account error_message and this endpoint answers 502.
    """
    await _verify_project_access(project_id, user_id, db)
    task = await _get_flow_task_or_404(db, project_id, task_id)
    if task.status not in _EXECUTABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute a task with status '{task.status.value}'",
        )
    return await _run_account_fallback(db, user_id, task)


@router.post("/{project_id}/{task_id}/retry", response_model=FlowBridgeRead)
async def retry_flow_task(
    project_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manual retry: re-run Google-account fallback for a failed task.

    Same resolution as /execute (pinned account first, then other enabled
    accounts); clears the previous error so a fresh attempt is recorded.
    Only allowed from FAILED or PENDING — a completed/imported task is
    never re-bound to another account.
    """
    await _verify_project_access(project_id, user_id, db)
    task = await _get_flow_task_or_404(db, project_id, task_id)
    if task.status not in {FlowTaskStatus.FAILED, FlowTaskStatus.PENDING}:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry a task with status '{task.status.value}'",
        )
    task.error_message = None
    await db.commit()
    return await _run_account_fallback(db, user_id, task)


@router.post("/{project_id}/{task_id}/execute-browser", response_model=FlowBridgeRead)
async def execute_browser_flow_task(
    project_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    headless: bool = True,
):
    """Run the task in Google Flow via a real browser session (no Console).

    Signs in with the account's own browser profile (email + password
    from the encrypted DB) and submits the task's prompt to Flow. If one
    account's login / quota / session fails, the next enabled account of
    the same user is tried automatically; every attempt is recorded in
    fallback_history (mode "browser"). On success the task is
    IN_PROGRESS with the Flow URL — the result is imported later via
    /import, same as the manual path. When every account fails the task
    is persisted as FAILED and this endpoint answers 502; manual export
    (/flow/export) still works.

    This path never touches Google Cloud Console credentials: no
    client_id/secret, no OAuth exchange. OAuth login/callback is
    untouched and still available for token-based accounts.
    """
    await _verify_project_access(project_id, user_id, db)
    task = await _get_flow_task_or_404(db, project_id, task_id)
    if task.status not in _EXECUTABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute a task with status '{task.status.value}'",
        )
    try:
        return await run_browser_execution(
            db, uuid.UUID(user_id), task, headless=headless
        )
    except AllBrowserAccountsFailed as e:
        raise HTTPException(status_code=502, detail=str(e))
    except BrowserUnreachable as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/{project_id}/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow_task(
    project_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a Flow Bridge task"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    task_uuid = uuid.UUID(task_id)

    result = await db.execute(
        select(FlowBridge).where(FlowBridge.id == task_uuid, FlowBridge.project_id == project_uuid)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Flow task not found")

    await db.delete(task)
    await db.commit()


@router.post("/export", response_model=dict)
async def export_for_flow(
    export_data: FlowExport,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Export prompts and assets for manual Flow processing"""
    await _verify_project_access(str(export_data.project_id), user_id, db)

    # In production, fetch actual prompts and assets
    # For MVP, return the provided data with metadata
    return {
        "export_id": str(export_data.project_id),
        "project_id": str(export_data.project_id),
        "episode_id": str(export_data.episode_id) if export_data.episode_id else None,
        "scene_id": str(export_data.scene_id) if export_data.scene_id else None,
        "task_type": export_data.task_type,
        "prompts": export_data.prompts,
        "reference_assets": export_data.reference_assets,
        "metadata": export_data.metadata,
        "mode": "manual",
        "instructions": "Manual export: import this data into Google Flow manually. After generation, use the import endpoint.",
    }


@router.post("/import", response_model=FlowBridgeRead)
async def import_from_flow(
    import_data: FlowImport,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Import results from manual Flow processing"""
    # FlowImport.flow_task_id is already a uuid.UUID (Pydantic parses it);
    # calling uuid.UUID() on it again raised AttributeError (audit F-H8).
    task_uuid = import_data.flow_task_id
    result = await db.execute(select(FlowBridge).where(FlowBridge.id == task_uuid))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Flow task not found")

    # Verify project access
    await _verify_project_access(str(task.project_id), user_id, db)

    task.output_assets = str(import_data.output_assets)  # Store as JSON string
    task.notes = import_data.notes
    task.status = FlowTaskStatus.IMPORTED
    from datetime import datetime, timezone
    task.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{project_id}/{task_id}/deeplink")
async def get_flow_deeplink(
    project_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a deep link to Google Flow for this task"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    task_uuid = uuid.UUID(task_id)

    result = await db.execute(
        select(FlowBridge).where(FlowBridge.id == task_uuid, FlowBridge.project_id == project_uuid)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Flow task not found")

    # Google Flow deep link format (UNVERIFIED placeholder — the real Flow
    # URL scheme has not been confirmed against flow.google.com, audit
    # F-M4. Do not present this as a verified working link in the UI.)
    deeplink = f"https://flow.google.com/task/{task.id}?project={project_id}"

    task.flow_url = deeplink
    await db.commit()

    return {
        "deeplink": deeplink,
        "task_id": str(task.id),
        "verified": False,
        "note": "Deeplink format is a placeholder and has not been verified against Google Flow.",
    }
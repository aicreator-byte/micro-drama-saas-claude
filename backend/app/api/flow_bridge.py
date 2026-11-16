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
import uuid

router = APIRouter(prefix="/flow", tags=["flow-bridge"])


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
        "instructions": "Import this data into Google Flow manually. After generation, use the import endpoint.",
    }


@router.post("/import", response_model=FlowBridgeRead)
async def import_from_flow(
    import_data: FlowImport,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Import results from manual Flow processing"""
    task_uuid = uuid.UUID(import_data.flow_task_id)
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

    # Google Flow deep link format (placeholder)
    # Actual format depends on Flow's URL scheme
    deeplink = f"https://flow.google.com/task/{task.id}?project={project_id}"

    task.flow_url = deeplink
    await db.commit()

    return {"deeplink": deeplink, "task_id": str(task.id)}
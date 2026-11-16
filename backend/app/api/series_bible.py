"""Series Bible API router"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.models.project import Project
from app.models.series_bible import SeriesBible
from app.schemas.series_bible import SeriesBibleCreate, SeriesBibleUpdate, SeriesBibleRead
import uuid

router = APIRouter(prefix="/series-bible", tags=["series-bible"])


async def _verify_project_access(project_id: str, user_id: str, db: AsyncSession) -> Project:
    """Verify user owns the project"""
    result = await db.execute(
        select(Project).where(
            Project.id == uuid.UUID(project_id),
            Project.owner_id == uuid.UUID(user_id),
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}", response_model=SeriesBibleRead, status_code=status.HTTP_201_CREATED)
async def create_series_bible(
    project_id: str,
    bible_data: SeriesBibleCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create or update series bible for a project"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    # Check if already exists
    result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project_uuid))
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        update_data = bible_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create new
    bible = SeriesBible(project_id=project_uuid, **bible_data.model_dump())
    db.add(bible)
    await db.commit()
    await db.refresh(bible)
    return bible


@router.get("/{project_id}", response_model=SeriesBibleRead)
async def get_series_bible(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get series bible for a project"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project_uuid))
    bible = result.scalar_one_or_none()
    if not bible:
        raise HTTPException(status_code=404, detail="Series bible not found")
    return bible


@router.patch("/{project_id}", response_model=SeriesBibleRead)
async def update_series_bible(
    project_id: str,
    bible_data: SeriesBibleUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update series bible"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project_uuid))
    bible = result.scalar_one_or_none()
    if not bible:
        raise HTTPException(status_code=404, detail="Series bible not found")

    update_data = bible_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bible, field, value)

    await db.commit()
    await db.refresh(bible)
    return bible


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series_bible(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete series bible"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project_uuid))
    bible = result.scalar_one_or_none()
    if not bible:
        raise HTTPException(status_code=404, detail="Series bible not found")

    await db.delete(bible)
    await db.commit()
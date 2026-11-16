"""Episodes API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.episode import Episode, EpisodeStatus
from app.models.project import Project
from app.schemas.episode import EpisodeCreate, EpisodeUpdate, EpisodeRead, EpisodeList, EpisodeReorder
import uuid

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.post("/{project_id}", response_model=EpisodeRead, status_code=status.HTTP_201_CREATED)
async def create_episode(
    project_id: str,
    episode_data: EpisodeCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create an episode for a project"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    # Check if episode number already exists
    result = await db.execute(
        select(Episode).where(
            Episode.project_id == project_uuid,
            Episode.episode_number == episode_data.episode_number,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Episode number already exists")

    episode = Episode(
        project_id=project_uuid,
        **episode_data.model_dump(),
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)
    return episode


@router.get("/{project_id}", response_model=EpisodeList)
async def list_episodes(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: EpisodeStatus | None = None,
):
    """List episodes for a project with pagination"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    query = select(Episode).where(Episode.project_id == project_uuid, Episode.deleted_at.is_(None))

    if status:
        query = query.where(Episode.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(Episode.episode_number).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    episodes = result.scalars().all()

    return EpisodeList(
        items=episodes,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{project_id}/{episode_id}", response_model=EpisodeRead)
async def get_episode(
    project_id: str,
    episode_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific episode"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    episode_uuid = uuid.UUID(episode_id)

    result = await db.execute(
        select(Episode).where(
            Episode.id == episode_uuid,
            Episode.project_id == project_uuid,
            Episode.deleted_at.is_(None),
        )
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.patch("/{project_id}/{episode_id}", response_model=EpisodeRead)
async def update_episode(
    project_id: str,
    episode_id: str,
    episode_data: EpisodeUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update an episode"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    episode_uuid = uuid.UUID(episode_id)

    result = await db.execute(
        select(Episode).where(
            Episode.id == episode_uuid,
            Episode.project_id == project_uuid,
            Episode.deleted_at.is_(None),
        )
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Check episode number uniqueness if changed
    if episode_data.episode_number and episode_data.episode_number != episode.episode_number:
        existing = await db.execute(
            select(Episode).where(
                Episode.project_id == project_uuid,
                Episode.episode_number == episode_data.episode_number,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Episode number already exists")

    update_data = episode_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(episode, field, value)

    await db.commit()
    await db.refresh(episode)
    return episode


@router.delete("/{project_id}/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    project_id: str,
    episode_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an episode"""
    from datetime import datetime, timezone
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    episode_uuid = uuid.UUID(episode_id)

    result = await db.execute(
        select(Episode).where(
            Episode.id == episode_uuid,
            Episode.project_id == project_uuid,
            Episode.deleted_at.is_(None),
        )
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    episode.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/{project_id}/reorder", response_model=List[EpisodeRead])
async def reorder_episodes(
    project_id: str,
    reorder_data: EpisodeReorder,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reorder episodes"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    for index, ep_id in enumerate(reorder_data.episode_ids):
        ep_uuid = uuid.UUID(str(ep_id))
        result = await db.execute(
            select(Episode).where(
                Episode.id == ep_uuid,
                Episode.project_id == project_uuid,
            )
        )
        episode = result.scalar_one_or_none()
        if episode:
            episode.episode_number = index + 1

    await db.commit()

    result = await db.execute(
        select(Episode)
        .where(Episode.project_id == project_uuid, Episode.deleted_at.is_(None))
        .order_by(Episode.episode_number)
    )
    return result.scalars().all()
"""Dashboard stats API (future-dev 2f)."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.core.database import get_db
from app.models.character import Character
from app.models.episode import Episode
from app.models.location import Location
from app.models.project import Project
from app.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Counts across all of the current user's (non-deleted) projects."""
    user_uuid = uuid.UUID(user_id)
    project_ids = (
        select(Project.id)
        .where(Project.owner_id == user_uuid, Project.deleted_at.is_(None))
    )
    projects = await db.scalar(
        select(func.count()).select_from(Project).where(
            Project.owner_id == user_uuid, Project.deleted_at.is_(None)
        )
    ) or 0
    characters = await db.scalar(
        select(func.count()).select_from(Character).where(
            Character.project_id.in_(project_ids)
        )
    ) or 0
    locations = await db.scalar(
        select(func.count()).select_from(Location).where(
            Location.project_id.in_(project_ids)
        )
    ) or 0
    episodes = await db.scalar(
        select(func.count()).select_from(Episode).where(
            Episode.project_id.in_(project_ids)
        )
    ) or 0
    return DashboardStats(
        projects=projects,
        characters=characters,
        locations=locations,
        episodes=episodes,
    )

"""Projects API router"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList

router = APIRouter(prefix="/projects", tags=["projects"])


async def _verify_project_access(project_id: str, user_id: str, db: AsyncSession) -> Project:
    """Verify user owns the project"""
    import uuid
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


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project"""
    import uuid
    project = Project(
        owner_id=uuid.UUID(user_id),
        title=project_data.title,
        description=project_data.description,
        genre=project_data.genre,
        themes=project_data.themes,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=ProjectList)
async def list_projects(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ProjectStatus | None = None,
):
    """List user's projects with pagination"""
    import uuid
    query = select(Project).where(Project.owner_id == uuid.UUID(user_id), Project.deleted_at.is_(None))

    if status:
        query = query.where(Project.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectList(
        items=projects,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific project"""
    import uuid
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


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a project"""
    import uuid
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

    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a project"""
    from datetime import datetime, timezone
    import uuid
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

    project.deleted_at = datetime.now(timezone.utc)
    await db.commit()
"""Locations API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.location import Location
from app.models.project import Project
from app.schemas.location import LocationCreate, LocationUpdate, LocationRead, LocationReorder

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post("/{project_id}", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    project_id: str,
    location_data: LocationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a location for a project"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    location = Location(
        project_id=uuid.UUID(project_id),
        **location_data.model_dump(),
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


@router.get("/{project_id}", response_model=List[LocationRead])
async def list_locations(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all locations for a project"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Location)
        .where(Location.project_id == uuid.UUID(project_id), Location.deleted_at.is_(None))
        .order_by(Location.display_order, Location.created_at)
    )
    return result.scalars().all()


@router.get("/{project_id}/{location_id}", response_model=LocationRead)
async def get_location(
    project_id: str,
    location_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific location"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Location).where(
            Location.id == uuid.UUID(location_id),
            Location.project_id == uuid.UUID(project_id),
            Location.deleted_at.is_(None),
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.patch("/{project_id}/{location_id}", response_model=LocationRead)
async def update_location(
    project_id: str,
    location_id: str,
    location_data: LocationUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a location"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Location).where(
            Location.id == uuid.UUID(location_id),
            Location.project_id == uuid.UUID(project_id),
            Location.deleted_at.is_(None),
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = location_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    await db.commit()
    await db.refresh(location)
    return location


@router.delete("/{project_id}/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    project_id: str,
    location_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a location"""
    from datetime import datetime, timezone
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Location).where(
            Location.id == uuid.UUID(location_id),
            Location.project_id == uuid.UUID(project_id),
            Location.deleted_at.is_(None),
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    location.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/{project_id}/reorder", response_model=List[LocationRead])
async def reorder_locations(
    project_id: str,
    reorder_data: LocationReorder,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reorder locations"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    for index, loc_id in enumerate(reorder_data.location_ids):
        result = await db.execute(
            select(Location).where(
                Location.id == uuid.UUID(loc_id),
                Location.project_id == uuid.UUID(project_id),
            )
        )
        location = result.scalar_one_or_none()
        if location:
            location.display_order = index

    await db.commit()

    result = await db.execute(
        select(Location)
        .where(Location.project_id == uuid.UUID(project_id), Location.deleted_at.is_(None))
        .order_by(Location.display_order)
    )
    return result.scalars().all()
"""Shots API router.

Audit ronde 2 P1-18: the Shot model existed (table `shots`, relationship
Scene.shots) but had no API/router/UI at all. This is the minimal CRUD
router for shots belonging to a scene; project access is verified
through scene -> episode -> project, like the other scene-child routers.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.scenes import _verify_episode_access
from app.models.scene import Scene
from app.models.shot import Shot
from app.schemas.shot import ShotCreate, ShotUpdate, ShotRead
import uuid

router = APIRouter(prefix="/shots", tags=["shots"])


async def _verify_scene_access(scene_id: str, user_id: str, db: AsyncSession) -> Scene:
    """Verify the user owns the project that contains this scene."""
    scene_uuid = uuid.UUID(scene_id)
    result = await db.execute(select(Scene).where(Scene.id == scene_uuid))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    await _verify_episode_access(str(scene.episode_id), user_id, db)
    return scene


@router.post("/{scene_id}", response_model=ShotRead, status_code=status.HTTP_201_CREATED)
async def create_shot(
    scene_id: str,
    shot_data: ShotCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a shot for a scene"""
    scene = await _verify_scene_access(scene_id, user_id, db)

    existing = await db.execute(
        select(Shot).where(
            Shot.scene_id == scene.id,
            Shot.shot_number == shot_data.shot_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Shot number already exists in this scene")

    shot = Shot(scene_id=scene.id, **shot_data.model_dump())
    db.add(shot)
    await db.commit()
    await db.refresh(shot)
    return shot


@router.get("/{scene_id}", response_model=List[ShotRead])
async def list_shots(
    scene_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all shots for a scene"""
    scene = await _verify_scene_access(scene_id, user_id, db)
    result = await db.execute(
        select(Shot).where(Shot.scene_id == scene.id).order_by(Shot.order_index, Shot.shot_number)
    )
    return result.scalars().all()


@router.get("/{scene_id}/{shot_id}", response_model=ShotRead)
async def get_shot(
    scene_id: str,
    shot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific shot"""
    scene = await _verify_scene_access(scene_id, user_id, db)
    shot = await db.get(Shot, uuid.UUID(shot_id))
    if not shot or shot.scene_id != scene.id:
        raise HTTPException(status_code=404, detail="Shot not found")
    return shot


@router.patch("/{scene_id}/{shot_id}", response_model=ShotRead)
async def update_shot(
    scene_id: str,
    shot_id: str,
    shot_data: ShotUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a shot"""
    scene = await _verify_scene_access(scene_id, user_id, db)
    shot = await db.get(Shot, uuid.UUID(shot_id))
    if not shot or shot.scene_id != scene.id:
        raise HTTPException(status_code=404, detail="Shot not found")

    if shot_data.shot_number and shot_data.shot_number != shot.shot_number:
        existing = await db.execute(
            select(Shot).where(
                Shot.scene_id == scene.id,
                Shot.shot_number == shot_data.shot_number,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Shot number already exists in this scene")

    update_data = shot_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shot, field, value)

    await db.commit()
    await db.refresh(shot)
    return shot


@router.delete("/{scene_id}/{shot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shot(
    scene_id: str,
    shot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a shot"""
    scene = await _verify_scene_access(scene_id, user_id, db)
    shot = await db.get(Shot, uuid.UUID(shot_id))
    if not shot or shot.scene_id != scene.id:
        raise HTTPException(status_code=404, detail="Shot not found")

    await db.delete(shot)
    await db.commit()

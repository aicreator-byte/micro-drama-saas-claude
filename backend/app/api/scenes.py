"""Scenes API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.scene import Scene, SceneCharacter, SceneStatus
from app.models.episode import Episode
from app.models.character import Character
from app.schemas.scene import SceneCreate, SceneUpdate, SceneRead, SceneCharacterCreate, SceneReorder
import uuid

router = APIRouter(prefix="/scenes", tags=["scenes"])


async def _verify_episode_access(episode_id: str, user_id: str, db: AsyncSession) -> Episode:
    """Verify user owns the project through episode"""
    episode_uuid = uuid.UUID(episode_id)
    user_uuid = uuid.UUID(user_id)
    result = await db.execute(
        select(Episode)
        .join(Episode.project)
        .where(
            Episode.id == episode_uuid,
            Episode.project.has(owner_id=user_uuid),
            Episode.deleted_at.is_(None),
        )
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.post("/{episode_id}", response_model=SceneRead, status_code=status.HTTP_201_CREATED)
async def create_scene(
    episode_id: str,
    scene_data: SceneCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a scene for an episode"""
    episode = await _verify_episode_access(episode_id, user_id, db)
    episode_uuid = uuid.UUID(episode_id)

    # Check if scene number already exists
    result = await db.execute(
        select(Scene).where(
            Scene.episode_id == episode_uuid,
            Scene.scene_number == scene_data.scene_number,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Scene number already exists")

    # Extract characters
    characters_data = scene_data.characters or []
    scene_dict = scene_data.model_dump(exclude={"characters", "episode_id"})

    scene = Scene(
        episode_id=episode_uuid,
        **scene_dict,
    )
    db.add(scene)
    await db.flush()

    # Add characters
    for char_data in characters_data:
        scene_char = SceneCharacter(
            scene_id=scene.id,
            **char_data.model_dump(),
        )
        db.add(scene_char)

    await db.commit()
    # Re-query with eager-loaded characters to avoid lazy-load during response serialization
    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene.id)
        .options(selectinload(Scene.characters).selectinload(SceneCharacter.character))
    )
    scene_with_chars = result.scalar_one()
    return scene_with_chars


@router.get("/{episode_id}", response_model=List[SceneRead])
async def list_scenes(
    episode_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    status: SceneStatus | None = None,
):
    """List all scenes for an episode"""
    await _verify_episode_access(episode_id, user_id, db)
    episode_uuid = uuid.UUID(episode_id)

    query = select(Scene).where(Scene.episode_id == episode_uuid, Scene.deleted_at.is_(None))

    if status:
        query = query.where(Scene.status == status)

    query = query.order_by(Scene.scene_number)
    result = await db.execute(query.options(selectinload(Scene.characters).selectinload(SceneCharacter.character)))
    return result.scalars().all()


@router.get("/{episode_id}/{scene_id}", response_model=SceneRead)
async def get_scene(
    episode_id: str,
    scene_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific scene with characters"""
    await _verify_episode_access(episode_id, user_id, db)
    episode_uuid = uuid.UUID(episode_id)
    scene_uuid = uuid.UUID(scene_id)

    result = await db.execute(
        select(Scene)
        .where(
            Scene.id == scene_uuid,
            Scene.episode_id == episode_uuid,
            Scene.deleted_at.is_(None),
        )
        .options(selectinload(Scene.characters).selectinload(SceneCharacter.character))
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.patch("/{episode_id}/{scene_id}", response_model=SceneRead)
async def update_scene(
    episode_id: str,
    scene_id: str,
    scene_data: SceneUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a scene"""
    await _verify_episode_access(episode_id, user_id, db)
    episode_uuid = uuid.UUID(episode_id)
    scene_uuid = uuid.UUID(scene_id)

    result = await db.execute(
        select(Scene).where(
            Scene.id == scene_uuid,
            Scene.episode_id == episode_uuid,
            Scene.deleted_at.is_(None),
        )
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Check scene number uniqueness if changed
    if scene_data.scene_number and scene_data.scene_number != scene.scene_number:
        existing = await db.execute(
            select(Scene).where(
                Scene.episode_id == episode_uuid,
                Scene.scene_number == scene_data.scene_number,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Scene number already exists")

    update_data = scene_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scene, field, value)

    await db.commit()
    # Re-query with eager-loaded characters to avoid lazy-load during response serialization
    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene.id)
        .options(selectinload(Scene.characters).selectinload(SceneCharacter.character))
    )
    scene_with_chars = result.scalar_one()
    return scene_with_chars


@router.delete("/{episode_id}/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(
    episode_id: str,
    scene_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a scene"""
    from datetime import datetime, timezone
    await _verify_episode_access(episode_id, user_id, db)
    episode_uuid = uuid.UUID(episode_id)
    scene_uuid = uuid.UUID(scene_id)

    result = await db.execute(
        select(Scene).where(
            Scene.id == scene_uuid,
            Scene.episode_id == episode_uuid,
            Scene.deleted_at.is_(None),
        )
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    scene.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/{episode_id}/reorder", response_model=List[SceneRead])
async def reorder_scenes(
    episode_id: str,
    reorder_data: SceneReorder,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reorder scenes"""
    await _verify_episode_access(episode_id, user_id, db)
    episode_uuid = uuid.UUID(episode_id)

    for index, scene_id in enumerate(reorder_data.scene_ids):
        scene_uuid = uuid.UUID(str(scene_id))
        result = await db.execute(
            select(Scene).where(
                Scene.id == scene_uuid,
                Scene.episode_id == episode_uuid,
            )
        )
        scene = result.scalar_one_or_none()
        if scene:
            scene.scene_number = index + 1

    await db.commit()

    result = await db.execute(
        select(Scene)
        .where(Scene.episode_id == episode_uuid, Scene.deleted_at.is_(None))
        .order_by(Scene.scene_number)
        .options(selectinload(Scene.characters).selectinload(SceneCharacter.character))
    )
    return result.scalars().all()


@router.post("/{episode_id}/{scene_id}/characters", response_model=SceneRead)
async def add_character_to_scene(
    episode_id: str,
    scene_id: str,
    character_data: SceneCharacterCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a character to a scene"""
    await _verify_episode_access(episode_id, user_id, db)
    episode_uuid = uuid.UUID(episode_id)
    scene_uuid = uuid.UUID(scene_id)

    result = await db.execute(
        select(Scene).where(
            Scene.id == scene_uuid,
            Scene.episode_id == episode_uuid,
        )
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Verify character belongs to same project
    char_result = await db.execute(
        select(Character).where(
            Character.id == character_data.character_id,
            Character.project_id == scene.episode.project_id,
        )
    )
    if not char_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Character not found in this project")

    # Check if already added
    existing = await db.execute(
        select(SceneCharacter).where(
            SceneCharacter.scene_id == scene_uuid,
            SceneCharacter.character_id == character_data.character_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Character already in scene")

    scene_char = SceneCharacter(
        scene_id=scene_uuid,
        **character_data.model_dump(),
    )
    db.add(scene_char)
    await db.commit()
    await db.refresh(scene)
    return scene


@router.delete("/{episode_id}/{scene_id}/characters/{character_id}", response_model=SceneRead)
async def remove_character_from_scene(
    episode_id: str,
    scene_id: str,
    character_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Remove a character from a scene"""
    await _verify_episode_access(episode_id, user_id, db)
    scene_uuid = uuid.UUID(scene_id)
    character_uuid = uuid.UUID(character_id)

    result = await db.execute(
        select(SceneCharacter).where(
            SceneCharacter.scene_id == scene_uuid,
            SceneCharacter.character_id == character_uuid,
        )
    )
    scene_char = result.scalar_one_or_none()
    if not scene_char:
        raise HTTPException(status_code=404, detail="Character not in scene")

    await db.delete(scene_char)
    await db.commit()

    # Reload scene
    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene_uuid)
        .options(selectinload(Scene.characters).selectinload(SceneCharacter.character))
    )
    return result.scalar_one()
"""Dialogues API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.dialogue import Dialogue
from app.models.scene import Scene
from app.models.episode import Episode
from app.schemas.dialogue import DialogueCreate, DialogueUpdate, DialogueRead, DialogueReorder
import uuid

router = APIRouter(prefix="/dialogues", tags=["dialogues"])


async def _verify_scene_access(scene_id: str, user_id: str, db: AsyncSession) -> Scene:
    """Verify user owns the project through scene"""
    scene_uuid = uuid.UUID(scene_id)
    user_uuid = uuid.UUID(user_id)
    result = await db.execute(
        select(Scene)
        .join(Scene.episode)
        .join(Episode.project)
        .where(
            Scene.id == scene_uuid,
            Episode.project.has(owner_id=user_uuid),
            Scene.deleted_at.is_(None),
        )
    )
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.post("/{scene_id}", response_model=DialogueRead, status_code=status.HTTP_201_CREATED)
async def create_dialogue(
    scene_id: str,
    dialogue_data: DialogueCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a dialogue line to a scene"""
    await _verify_scene_access(scene_id, user_id, db)
    scene_uuid = uuid.UUID(scene_id)

    dialogue = Dialogue(
        scene_id=scene_uuid,
        **dialogue_data.model_dump(exclude={"scene_id"}),
    )
    db.add(dialogue)
    await db.commit()
    # Re-query with eager-loaded character to avoid lazy-load during response serialization
    result = await db.execute(
        select(Dialogue)
        .where(Dialogue.id == dialogue.id)
        .options(selectinload(Dialogue.character))
    )
    dialogue_with_char = result.scalar_one()
    return dialogue_with_char


@router.get("/{scene_id}", response_model=List[DialogueRead])
async def list_dialogues(
    scene_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all dialogues for a scene"""
    await _verify_scene_access(scene_id, user_id, db)
    scene_uuid = uuid.UUID(scene_id)

    result = await db.execute(
        select(Dialogue)
        .where(Dialogue.scene_id == scene_uuid)
        .order_by(Dialogue.order_index)
        .options(selectinload(Dialogue.character))
    )
    return result.scalars().all()


@router.get("/{scene_id}/{dialogue_id}", response_model=DialogueRead)
async def get_dialogue(
    scene_id: str,
    dialogue_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific dialogue"""
    await _verify_scene_access(scene_id, user_id, db)
    scene_uuid = uuid.UUID(scene_id)
    dialogue_uuid = uuid.UUID(dialogue_id)

    result = await db.execute(
        select(Dialogue)
        .where(Dialogue.id == dialogue_uuid, Dialogue.scene_id == scene_uuid)
        .options(selectinload(Dialogue.character))
    )
    dialogue = result.scalar_one_or_none()
    if not dialogue:
        raise HTTPException(status_code=404, detail="Dialogue not found")
    return dialogue


@router.patch("/{scene_id}/{dialogue_id}", response_model=DialogueRead)
async def update_dialogue(
    scene_id: str,
    dialogue_id: str,
    dialogue_data: DialogueUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a dialogue"""
    await _verify_scene_access(scene_id, user_id, db)
    scene_uuid = uuid.UUID(scene_id)
    dialogue_uuid = uuid.UUID(dialogue_id)

    result = await db.execute(
        select(Dialogue).where(Dialogue.id == dialogue_uuid, Dialogue.scene_id == scene_uuid)
    )
    dialogue = result.scalar_one_or_none()
    if not dialogue:
        raise HTTPException(status_code=404, detail="Dialogue not found")

    update_data = dialogue_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dialogue, field, value)

    await db.commit()
    # Re-query with eager-loaded character to avoid lazy-load during response serialization
    result = await db.execute(
        select(Dialogue)
        .where(Dialogue.id == dialogue.id)
        .options(selectinload(Dialogue.character))
    )
    dialogue_with_char = result.scalar_one()
    return dialogue_with_char


@router.delete("/{scene_id}/{dialogue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dialogue(
    scene_id: str,
    dialogue_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dialogue"""
    await _verify_scene_access(scene_id, user_id, db)
    scene_uuid = uuid.UUID(scene_id)
    dialogue_uuid = uuid.UUID(dialogue_id)

    result = await db.execute(
        select(Dialogue).where(Dialogue.id == dialogue_uuid, Dialogue.scene_id == scene_uuid)
    )
    dialogue = result.scalar_one_or_none()
    if not dialogue:
        raise HTTPException(status_code=404, detail="Dialogue not found")

    await db.delete(dialogue)
    await db.commit()


@router.post("/{scene_id}/reorder", response_model=List[DialogueRead])
async def reorder_dialogues(
    scene_id: str,
    reorder_data: DialogueReorder,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reorder dialogues"""
    await _verify_scene_access(scene_id, user_id, db)
    scene_uuid = uuid.UUID(scene_id)

    for index, dlg_id in enumerate(reorder_data.dialogue_ids):
        dlg_uuid = uuid.UUID(str(dlg_id))
        result = await db.execute(
            select(Dialogue).where(Dialogue.id == dlg_uuid, Dialogue.scene_id == scene_uuid)
        )
        dialogue = result.scalar_one_or_none()
        if dialogue:
            dialogue.order_index = index

    await db.commit()

    result = await db.execute(
        select(Dialogue)
        .where(Dialogue.scene_id == scene_uuid)
        .order_by(Dialogue.order_index)
        .options(selectinload(Dialogue.character))
    )
    return result.scalars().all()
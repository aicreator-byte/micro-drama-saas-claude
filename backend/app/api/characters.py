"""Characters API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.character import Character
from app.models.project import Project
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterRead, CharacterReorder

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("/{project_id}", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(
    project_id: str,
    character_data: CharacterCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a character for a project"""
    await _verify_project_access(project_id, user_id, db)

    # Check character count (max 6 for MVP, but allow more)
    import uuid
    count = await db.scalar(
        select(func.count(Character.id)).where(Character.project_id == uuid.UUID(project_id))
    )

    character = Character(
        project_id=uuid.UUID(project_id),
        **character_data.model_dump(),
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character


@router.get("/{project_id}", response_model=List[CharacterRead])
async def list_characters(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all characters for a project"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Character)
        .where(Character.project_id == uuid.UUID(project_id), Character.deleted_at.is_(None))
        .order_by(Character.display_order, Character.created_at)
    )
    return result.scalars().all()


@router.get("/{project_id}/{character_id}", response_model=CharacterRead)
async def get_character(
    project_id: str,
    character_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific character"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Character).where(
            Character.id == uuid.UUID(character_id),
            Character.project_id == uuid.UUID(project_id),
            Character.deleted_at.is_(None),
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.patch("/{project_id}/{character_id}", response_model=CharacterRead)
async def update_character(
    project_id: str,
    character_id: str,
    character_data: CharacterUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a character"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Character).where(
            Character.id == uuid.UUID(character_id),
            Character.project_id == uuid.UUID(project_id),
            Character.deleted_at.is_(None),
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = character_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(character, field, value)

    await db.commit()
    await db.refresh(character)
    return character


@router.delete("/{project_id}/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    project_id: str,
    character_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a character"""
    from datetime import datetime, timezone
    await _verify_project_access(project_id, user_id, db)

    import uuid
    result = await db.execute(
        select(Character).where(
            Character.id == uuid.UUID(character_id),
            Character.project_id == uuid.UUID(project_id),
            Character.deleted_at.is_(None),
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    character.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/{project_id}/reorder", response_model=List[CharacterRead])
async def reorder_characters(
    project_id: str,
    reorder_data: CharacterReorder,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reorder characters"""
    await _verify_project_access(project_id, user_id, db)

    import uuid
    for index, char_id in enumerate(reorder_data.character_ids):
        result = await db.execute(
            select(Character).where(
                Character.id == uuid.UUID(char_id),
                Character.project_id == uuid.UUID(project_id),
            )
        )
        character = result.scalar_one_or_none()
        if character:
            character.display_order = index

    await db.commit()

    result = await db.execute(
        select(Character)
        .where(Character.project_id == uuid.UUID(project_id), Character.deleted_at.is_(None))
        .order_by(Character.display_order)
    )
    return result.scalars().all()
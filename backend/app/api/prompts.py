"""Prompts API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.prompt import Prompt, PromptType
from app.models.project import Project
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptRead, PromptGenerate, PromptList
import uuid

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptRead, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a prompt"""
    await _verify_project_access(str(prompt_data.project_id), user_id, db)

    prompt = Prompt(**prompt_data.model_dump())
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.get("/{project_id}", response_model=PromptList)
async def list_prompts(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    prompt_type: PromptType | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
):
    """List prompts for a project with filters"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    query = select(Prompt).where(Prompt.project_id == project_uuid)

    if prompt_type:
        query = query.where(Prompt.prompt_type == prompt_type)
    if episode_id:
        query = query.where(Prompt.episode_id == uuid.UUID(episode_id))
    if scene_id:
        query = query.where(Prompt.scene_id == uuid.UUID(scene_id))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(Prompt.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    prompts = result.scalars().all()

    return PromptList(
        items=prompts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{project_id}/{prompt_id}", response_model=PromptRead)
async def get_prompt(
    project_id: str,
    prompt_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific prompt"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    prompt_uuid = uuid.UUID(prompt_id)

    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_uuid, Prompt.project_id == project_uuid)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.patch("/{project_id}/{prompt_id}", response_model=PromptRead)
async def update_prompt(
    project_id: str,
    prompt_id: str,
    prompt_data: PromptUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a prompt"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    prompt_uuid = uuid.UUID(prompt_id)

    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_uuid, Prompt.project_id == project_uuid)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    update_data = prompt_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)

    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.delete("/{project_id}/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    project_id: str,
    prompt_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a prompt"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    prompt_uuid = uuid.UUID(prompt_id)

    result = await db.execute(
        select(Prompt).where(Prompt.id == prompt_uuid, Prompt.project_id == project_uuid)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    await db.delete(prompt)
    await db.commit()


@router.post("/generate", response_model=PromptRead)
async def generate_prompt(
    generate_data: PromptGenerate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a prompt using AI (placeholder - integrates with LLM)"""
    await _verify_project_access(str(generate_data.project_id), user_id, db)

    # This is a placeholder for AI generation
    # In production, integrate with LLM provider

    # Simple template-based generation for MVP
    prompt_templates = {
        PromptType.CHARACTER_IMAGE: "Character portrait of {name}, {description}, high quality, detailed",
        PromptType.LOCATION_IMAGE: "Cinematic location shot of {name}, {description}, atmospheric lighting",
        PromptType.SCENE_IMAGE: "Scene from drama: {description}, cinematic composition",
        PromptType.VIDEO_GENERATION: "Video prompt: {description}, smooth motion, high quality",
        PromptType.CAMERA_MOVEMENT: "Camera movement: {description}",
        PromptType.CHARACTER_ACTION: "Character action: {description}",
        PromptType.DIALOGUE_AUDIO: "Voice acting for: {description}",
        PromptType.BACKGROUND_MUSIC: "Background music: {description}",
        PromptType.SOUND_EFFECT: "Sound effect: {description}",
        PromptType.SUBTITLE: "Subtitle text: {description}",
    }

    template = prompt_templates.get(generate_data.prompt_type, "{description}")
    context = generate_data.context or "A dramatic scene"

    prompt_text = template.format(description=context)

    prompt = Prompt(
        project_id=generate_data.project_id,
        episode_id=generate_data.episode_id,
        scene_id=generate_data.scene_id,
        character_id=generate_data.character_id,
        location_id=generate_data.location_id,
        prompt_type=generate_data.prompt_type,
        prompt_text=prompt_text,
        status="completed",
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt
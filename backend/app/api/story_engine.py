"""Story Engine API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.api.projects import _verify_project_access
from app.models.story_engine import StoryEngine, StoryGenerationType, StoryGenerationStatus
from app.schemas.story_engine import StoryEngineCreate, StoryEngineRead, StoryEngineList, StoryGenerateRequest
import uuid

router = APIRouter(prefix="/story-engine", tags=["story-engine"])


@router.post("/generate", response_model=StoryEngineRead, status_code=status.HTTP_201_CREATED)
async def generate_story(
    generate_data: StoryGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate story content using AI (placeholder)"""
    await _verify_project_access(str(generate_data.project_id), user_id, db)

    # Create story engine record
    story_gen = StoryEngine(
        project_id=generate_data.project_id,
        episode_id=generate_data.episode_id,
        scene_id=generate_data.scene_id,
        generation_type=generate_data.generation_type,
        input_prompt=generate_data.context.get("prompt") if generate_data.context else None,
        input_context=str(generate_data.context) if generate_data.context else None,
        model_used=generate_data.model,
        status=StoryGenerationStatus.GENERATING,
    )
    db.add(story_gen)
    await db.commit()
    await db.refresh(story_gen)

    # Placeholder for AI generation
    # In production, integrate with LLM provider

    # Template-based generation for MVP
    templates = {
        StoryGenerationType.STORY_IDEA: {
            "premise": "A {genre} story about {protagonist} who must {goal} before {deadline}.",
            "main_plot": "The protagonist faces escalating challenges...",
            "themes": ["redemption", "identity", "sacrifice"],
        },
        StoryGenerationType.EPISODE_OUTLINE: {
            "episode_number": 1,
            "title": "Pilot",
            "synopsis": "Introduction to the world and main conflict.",
            "key_scenes": ["Opening hook", "Inciting incident", "First turning point"],
        },
        StoryGenerationType.FULL_SERIES: {
            "episodes": [
                {"number": i, "title": f"Episode {i}", "synopsis": f"Episode {i} synopsis"}
                for i in range(1, 21)
            ],
        },
        StoryGenerationType.SCENE_BREAKDOWN: {
            "scenes": [
                {"number": 1, "description": "Opening scene", "location": "Main location"},
                {"number": 2, "description": "Conflict scene", "location": "Secondary location"},
            ],
        },
        StoryGenerationType.DIALOGUE_GENERATION: {
            "dialogues": [
                {"character": "Protagonist", "text": "I can't believe this is happening."},
                {"character": "Antagonist", "text": "You should have seen it coming."},
            ],
        },
        StoryGenerationType.CHARACTER_DEVELOPMENT: {
            "arc": "From naive to experienced",
            "key_moments": ["Inciting incident", "Dark night of the soul", "Climax"],
        },
        StoryGenerationType.CONFLICT_DEVELOPMENT: {
            "main_conflict": "Protagonist vs Antagonist",
            "sub_conflicts": ["Internal doubt", "External pressure", "Time constraint"],
            "escalation": "Rising stakes each episode",
        },
        StoryGenerationType.CLIFFHANGER: {
            "cliffhanger": "The protagonist discovers the truth just as the door opens...",
            "resolution_hook": "Next episode reveals the consequence.",
        },
    }

    template = templates.get(generate_data.generation_type, {"output": "Generated content"})
    import json
    generated_output = json.dumps(template, indent=2)

    story_gen.generated_output = generated_output
    story_gen.status = StoryGenerationStatus.COMPLETED
    story_gen.tokens_used = 500  # Mock token count
    from datetime import datetime, timezone
    story_gen.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(story_gen)
    return story_gen


@router.get("/{project_id}", response_model=StoryEngineList)
async def list_story_generations(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    generation_type: StoryGenerationType | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
):
    """List story generations for a project"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)

    query = select(StoryEngine).where(StoryEngine.project_id == project_uuid)

    if generation_type:
        query = query.where(StoryEngine.generation_type == generation_type)
    if episode_id:
        query = query.where(StoryEngine.episode_id == uuid.UUID(episode_id))
    if scene_id:
        query = query.where(StoryEngine.scene_id == uuid.UUID(scene_id))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(StoryEngine.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    generations = result.scalars().all()

    return StoryEngineList(
        items=generations,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{project_id}/{generation_id}", response_model=StoryEngineRead)
async def get_story_generation(
    project_id: str,
    generation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific story generation"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    generation_uuid = uuid.UUID(generation_id)

    result = await db.execute(
        select(StoryEngine).where(
            StoryEngine.id == generation_uuid,
            StoryEngine.project_id == project_uuid,
        )
    )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Story generation not found")
    return generation


@router.delete("/{project_id}/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story_generation(
    project_id: str,
    generation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a story generation"""
    await _verify_project_access(project_id, user_id, db)
    project_uuid = uuid.UUID(project_id)
    generation_uuid = uuid.UUID(generation_id)

    result = await db.execute(
        select(StoryEngine).where(
            StoryEngine.id == generation_uuid,
            StoryEngine.project_id == project_uuid,
        )
    )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Story generation not found")

    await db.delete(generation)
    await db.commit()
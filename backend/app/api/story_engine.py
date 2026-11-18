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
from app.services.ai_client import get_ai_client, AIClientError
import uuid
import json
from datetime import datetime, timezone

router = APIRouter(prefix="/story-engine", tags=["story-engine"])


def _build_prompt(generation_type: StoryGenerationType, context: dict | None) -> str:
    """Build prompt for LLM based on generation type and context"""
    base_context = context or {}
    user_prompt = base_context.get("prompt", "").strip()

    # If user provided a prompt, it's the primary instruction - prepend it prominently
    user_instruction = f"\n\nUSER INSTRUCTION (PRIMARY - FOLLOW THIS):\n{user_prompt}\n" if user_prompt else ""

    prompts = {
        StoryGenerationType.STORY_IDEA: f"""Generate a compelling story idea for a {base_context.get('genre', 'drama')} series.
Premise: {base_context.get('premise', 'A unique story concept')}
Protagonist: {base_context.get('protagonist', 'A relatable main character')}
Goal: {base_context.get('goal', 'A meaningful objective')}
Deadline/Stakes: {base_context.get('deadline', 'High stakes with time pressure')}{user_instruction}

Return JSON with: premise, main_plot, themes (array)""",

        StoryGenerationType.EPISODE_OUTLINE: f"""Generate an episode outline for episode {base_context.get('episode_number', 1)}.
Series context: {base_context.get('series_context', 'A drama series')}
Previous episode: {base_context.get('previous_episode', 'N/A')}{user_instruction}

Return JSON with: episode_number, title, synopsis, key_scenes (array)""",

        StoryGenerationType.FULL_SERIES: f"""Generate a full series outline for {base_context.get('num_episodes', 10)} episodes.
Series concept: {base_context.get('series_concept', 'A drama series')}
Genre: {base_context.get('genre', 'drama')}{user_instruction}

Return JSON with: episodes (array of objects with number, title, synopsis)""",

        StoryGenerationType.SCENE_BREAKDOWN: f"""Break down a scene for episode {base_context.get('episode_number', 1)}.
Scene context: {base_context.get('scene_context', 'A key scene')}
Characters involved: {base_context.get('characters', 'Main characters')}
Location: {base_context.get('location', 'Primary location')}{user_instruction}

Return JSON with: scenes (array of objects with number, description, location, characters)""",

        StoryGenerationType.DIALOGUE_GENERATION: f"""Generate dialogue for a scene.
Scene: {base_context.get('scene_description', 'A tense confrontation')}
Characters: {base_context.get('characters', 'Protagonist, Antagonist')}
Tone: {base_context.get('tone', 'dramatic')}{user_instruction}

Return JSON with: dialogues (array of objects with character, text, subtext)""",

        StoryGenerationType.CHARACTER_DEVELOPMENT: f"""Develop a character arc for: {base_context.get('character_name', 'Protagonist')}.
Role: {base_context.get('role', 'Main character')}
Starting state: {base_context.get('starting_state', 'Naive/inexperienced')}{user_instruction}

Return JSON with: arc, key_moments (array), internal_conflict, growth_trajectory""",

        StoryGenerationType.CONFLICT_DEVELOPMENT: f"""Develop conflict for a story.
Main conflict: {base_context.get('main_conflict', 'Protagonist vs Antagonist')}
Theme: {base_context.get('theme', 'Identity and sacrifice')}{user_instruction}

Return JSON with: main_conflict, sub_conflicts (array), escalation_stages (array), resolution_path""",

        StoryGenerationType.CLIFFHANGER: f"""Generate a cliffhanger ending.
Context: {base_context.get('context', 'Critical moment in the story')}
Characters present: {base_context.get('characters', 'Main characters')}{user_instruction}

Return JSON with: cliffhanger, resolution_hook, emotional_impact""",
    }

    return prompts.get(generation_type, f"Generate content for {generation_type.value}: {json.dumps(base_context)}")


@router.post("/generate", response_model=StoryEngineRead, status_code=status.HTTP_201_CREATED)
async def generate_story(
    generate_data: StoryGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate story content using real LLM with provider fallback"""
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

    # Build prompt for LLM
    prompt = _build_prompt(generate_data.generation_type, generate_data.context)
    messages = [
        {"role": "system", "content": "You are a professional screenwriter and story developer. Always return valid JSON only."},
        {"role": "user", "content": prompt},
    ]

    # Call real LLM with fallback
    ai_client = await get_ai_client(db)
    try:
        ai_response = await ai_client.generate(
            messages=messages,
            temperature=generate_data.temperature,
            max_tokens=generate_data.max_tokens,
        )

        story_gen.generated_output = ai_response.content
        story_gen.status = StoryGenerationStatus.COMPLETED
        story_gen.model_used = ai_response.model_used
        story_gen.tokens_used = ai_response.tokens_used
        story_gen.completed_at = datetime.now(timezone.utc)

    except AIClientError as e:
        story_gen.status = StoryGenerationStatus.FAILED
        story_gen.error_message = f"All providers failed: {e.errors}"
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
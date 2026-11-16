"""Story Engine schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid
from app.models.story_engine import StoryGenerationType, StoryGenerationStatus


class StoryEngineCreate(BaseModel):
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    generation_type: StoryGenerationType
    input_prompt: Optional[str] = None
    input_context: Optional[str] = None  # JSON


class StoryEngineRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID]
    scene_id: Optional[uuid.UUID]
    generation_type: StoryGenerationType
    status: StoryGenerationStatus
    input_prompt: Optional[str]
    input_context: Optional[str]
    generated_output: Optional[str]
    model_used: Optional[str]
    tokens_used: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class StoryEngineList(BaseModel):
    items: List[StoryEngineRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class StoryGenerateRequest(BaseModel):
    """Request to generate story content using AI"""
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    generation_type: StoryGenerationType
    context: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
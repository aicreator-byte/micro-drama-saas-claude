"""Prompt schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
from app.models.prompt import PromptType


class PromptCreate(BaseModel):
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    character_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    prompt_type: PromptType
    prompt_text: str = Field(..., min_length=1)
    negative_prompt: Optional[str] = None
    parameters: Optional[str] = None  # JSON


class PromptUpdate(BaseModel):
    prompt_text: Optional[str] = Field(None, min_length=1)
    negative_prompt: Optional[str] = None
    parameters: Optional[str] = None
    generated_result: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None


class PromptRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID]
    scene_id: Optional[uuid.UUID]
    character_id: Optional[uuid.UUID]
    location_id: Optional[uuid.UUID]
    prompt_type: PromptType
    prompt_text: str
    negative_prompt: Optional[str]
    parameters: Optional[str]
    generated_result: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptList(BaseModel):
    items: List[PromptRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class PromptGenerate(BaseModel):
    """Request to generate a prompt using AI"""
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    character_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    prompt_type: PromptType
    context: Optional[str] = None  # Additional context for generation
    model: Optional[str] = None
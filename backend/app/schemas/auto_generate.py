"""Auto-generate schemas (Fase 1)"""
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.auto_generate import (
    AutoGenerateJobStatus,
    AutoGenerateStepName,
    AutoGenerateStepStatus,
)


class AutoGenerateCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    genre: Optional[str] = Field(default=None, max_length=100)
    total_episodes: int = Field(default=30, ge=1, le=100)
    premise: Optional[str] = None


class AutoGenerateStepRead(BaseModel):
    step: AutoGenerateStepName
    status: AutoGenerateStepStatus
    error_message: Optional[str] = None
    result_summary: Optional[str] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AutoGenerateJobRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    genre: Optional[str] = None
    total_episodes: int
    premise: Optional[str] = None
    status: AutoGenerateJobStatus
    error_message: Optional[str] = None
    steps: List[AutoGenerateStepRead] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

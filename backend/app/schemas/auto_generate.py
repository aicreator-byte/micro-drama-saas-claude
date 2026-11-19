"""Auto-generate schemas (Fase 1; future-dev: title validation)"""
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
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

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, value):
        """A whitespace-only title is rejected (min_length=1 after strip)."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("genre", "premise", mode="before")
    @classmethod
    def _strip_optional(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


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

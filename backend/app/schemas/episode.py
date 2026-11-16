"""Episode schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
from app.models.episode import EpisodeStatus


class EpisodeCreate(BaseModel):
    episode_number: int = Field(..., ge=1, le=100)
    title: Optional[str] = Field(None, max_length=255)
    synopsis: Optional[str] = None
    status: EpisodeStatus = EpisodeStatus.PLANNED
    estimated_duration: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class EpisodeUpdate(BaseModel):
    episode_number: Optional[int] = Field(None, ge=1, le=100)
    title: Optional[str] = Field(None, max_length=255)
    synopsis: Optional[str] = None
    status: Optional[EpisodeStatus] = None
    estimated_duration: Optional[int] = Field(None, ge=0)
    actual_duration: Optional[int] = Field(None, ge=0)
    production_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class EpisodeRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    episode_number: int
    title: Optional[str]
    synopsis: Optional[str]
    status: EpisodeStatus
    estimated_duration: Optional[int]
    actual_duration: Optional[int]
    production_cost: Optional[float]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EpisodeList(BaseModel):
    items: List[EpisodeRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class EpisodeReorder(BaseModel):
    episode_ids: List[uuid.UUID]
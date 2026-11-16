"""Project schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=100)
    themes: Optional[str] = None  # JSON array


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=100)
    themes: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: Optional[str]
    genre: Optional[str]
    themes: Optional[str]
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    items: List[ProjectRead]
    total: int
    page: int
    page_size: int
    total_pages: int
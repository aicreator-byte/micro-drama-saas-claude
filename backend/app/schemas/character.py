"""Character schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    physical_appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    costume: Optional[str] = None
    reference_images: Optional[str] = None  # JSON array
    consistency_instructions: Optional[str] = None
    display_order: int = 0


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    physical_appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    costume: Optional[str] = None
    reference_images: Optional[str] = None
    consistency_instructions: Optional[str] = None
    display_order: Optional[int] = None


class CharacterRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    role: Optional[str]
    physical_appearance: Optional[str]
    personality: Optional[str]
    background: Optional[str]
    costume: Optional[str]
    reference_images: Optional[str]
    consistency_instructions: Optional[str]
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CharacterReorder(BaseModel):
    character_ids: List[str]
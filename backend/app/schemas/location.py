"""Location schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    environment: Optional[str] = None
    visual_references: Optional[str] = None
    lighting: Optional[str] = None
    atmosphere: Optional[str] = None
    consistency_instructions: Optional[str] = None
    display_order: int = 0


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    environment: Optional[str] = None
    visual_references: Optional[str] = None
    lighting: Optional[str] = None
    atmosphere: Optional[str] = None
    consistency_instructions: Optional[str] = None
    display_order: Optional[int] = None


class LocationRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str]
    environment: Optional[str]
    visual_references: Optional[str]
    lighting: Optional[str]
    atmosphere: Optional[str]
    consistency_instructions: Optional[str]
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LocationReorder(BaseModel):
    location_ids: List[str]
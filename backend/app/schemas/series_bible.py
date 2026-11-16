"""Series Bible schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class SeriesBibleCreate(BaseModel):
    premise: Optional[str] = None
    main_plot: Optional[str] = None
    subplots: Optional[str] = None
    character_relationships: Optional[str] = None
    world_settings: Optional[str] = None
    tone_and_style: Optional[str] = None
    visual_style: Optional[str] = None
    ending_direction: Optional[str] = None
    episode_structure: Optional[str] = None


class SeriesBibleUpdate(BaseModel):
    premise: Optional[str] = None
    main_plot: Optional[str] = None
    subplots: Optional[str] = None
    character_relationships: Optional[str] = None
    world_settings: Optional[str] = None
    tone_and_style: Optional[str] = None
    visual_style: Optional[str] = None
    ending_direction: Optional[str] = None
    episode_structure: Optional[str] = None


class SeriesBibleRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    premise: Optional[str]
    main_plot: Optional[str]
    subplots: Optional[str]
    character_relationships: Optional[str]
    world_settings: Optional[str]
    tone_and_style: Optional[str]
    visual_style: Optional[str]
    ending_direction: Optional[str]
    episode_structure: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
"""Shot schemas"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class ShotCreate(BaseModel):
    shot_number: int = Field(..., ge=1)
    description: str = Field(..., min_length=1)
    camera_angle: Optional[str] = Field(None, max_length=100)
    camera_movement: Optional[str] = Field(None, max_length=100)
    duration_seconds: Optional[int] = Field(None, ge=0)
    order_index: int = 0


class ShotUpdate(BaseModel):
    shot_number: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, min_length=1)
    camera_angle: Optional[str] = Field(None, max_length=100)
    camera_movement: Optional[str] = Field(None, max_length=100)
    duration_seconds: Optional[int] = Field(None, ge=0)
    order_index: Optional[int] = None


class ShotRead(BaseModel):
    id: uuid.UUID
    scene_id: uuid.UUID
    shot_number: int
    description: str
    camera_angle: Optional[str]
    camera_movement: Optional[str]
    duration_seconds: Optional[int]
    order_index: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

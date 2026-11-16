"""Scene schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
from app.models.scene import SceneStatus


class SceneCharacterCreate(BaseModel):
    character_id: uuid.UUID
    role_in_scene: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class SceneCreate(BaseModel):
    episode_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    scene_number: int = Field(..., ge=1)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    action: Optional[str] = None
    camera_directions: Optional[str] = None
    status: SceneStatus = SceneStatus.PLANNED
    estimated_duration: Optional[int] = Field(None, ge=0)
    characters: Optional[List[SceneCharacterCreate]] = None


class SceneUpdate(BaseModel):
    location_id: Optional[uuid.UUID] = None
    scene_number: Optional[int] = Field(None, ge=1)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    action: Optional[str] = None
    camera_directions: Optional[str] = None
    status: Optional[SceneStatus] = None
    estimated_duration: Optional[int] = Field(None, ge=0)


class SceneRead(BaseModel):
    id: uuid.UUID
    episode_id: uuid.UUID
    location_id: Optional[uuid.UUID]
    scene_number: int
    title: Optional[str]
    description: Optional[str]
    action: Optional[str]
    camera_directions: Optional[str]
    status: SceneStatus
    estimated_duration: Optional[int]
    created_at: datetime
    updated_at: datetime
    characters: List["SceneCharacterRead"] = []

    class Config:
        from_attributes = True


class SceneCharacterRead(BaseModel):
    id: uuid.UUID
    scene_id: uuid.UUID
    character_id: uuid.UUID
    role_in_scene: Optional[str]
    notes: Optional[str]
    character: Optional["CharacterRead"] = None

    class Config:
        from_attributes = True


class SceneList(BaseModel):
    items: List[SceneRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class SceneReorder(BaseModel):
    scene_ids: List[uuid.UUID]


# Forward reference resolution
from app.schemas.character import CharacterRead
SceneRead.model_rebuild()
SceneCharacterRead.model_rebuild()
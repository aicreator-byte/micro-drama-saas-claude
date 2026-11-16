"""Dialogue schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class DialogueCreate(BaseModel):
    character_id: uuid.UUID
    order_index: int = Field(..., ge=0)
    dialogue_text: str = Field(..., min_length=1)
    parenthetical: Optional[str] = None
    audio_prompt: Optional[str] = None


class DialogueUpdate(BaseModel):
    character_id: Optional[uuid.UUID] = None
    order_index: Optional[int] = Field(None, ge=0)
    dialogue_text: Optional[str] = Field(None, min_length=1)
    parenthetical: Optional[str] = None
    audio_prompt: Optional[str] = None


class DialogueRead(BaseModel):
    id: uuid.UUID
    scene_id: uuid.UUID
    character_id: uuid.UUID
    order_index: int
    dialogue_text: str
    parenthetical: Optional[str]
    audio_prompt: Optional[str]
    created_at: datetime
    updated_at: datetime
    character: Optional["CharacterRead"] = None

    class Config:
        from_attributes = True


class DialogueList(BaseModel):
    items: List[DialogueRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class DialogueReorder(BaseModel):
    dialogue_ids: List[uuid.UUID]


# Forward reference resolution
from app.schemas.character import CharacterRead
DialogueRead.model_rebuild()
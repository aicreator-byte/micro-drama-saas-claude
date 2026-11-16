"""Asset schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
from app.models.asset import AssetType, AssetStatus


class AssetCreate(BaseModel):
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    prompt_id: Optional[uuid.UUID] = None
    asset_type: AssetType
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    asset_metadata: Optional[str] = None


class AssetUpdate(BaseModel):
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    status: Optional[AssetStatus] = None
    asset_metadata: Optional[str] = None


class AssetRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID]
    scene_id: Optional[uuid.UUID]
    prompt_id: Optional[uuid.UUID]
    asset_type: AssetType
    file_name: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    status: AssetStatus
    asset_metadata: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetList(BaseModel):
    items: List[AssetRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AssetUploadInit(BaseModel):
    file_name: str
    file_size: int
    mime_type: str
    asset_type: AssetType
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None


class AssetUploadComplete(BaseModel):
    upload_id: str
    file_path: str
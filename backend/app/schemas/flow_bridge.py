"""Flow Bridge schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
from app.models.flow_bridge import FlowTaskType, FlowTaskStatus


class FlowBridgeCreate(BaseModel):
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    google_account_id: Optional[uuid.UUID] = None
    task_type: FlowTaskType
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    input_prompts: Optional[str] = None  # JSON array
    reference_assets: Optional[str] = None  # JSON array


class FlowBridgeUpdate(BaseModel):
    google_account_id: Optional[uuid.UUID] = None
    status: Optional[FlowTaskStatus] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    input_prompts: Optional[str] = None
    reference_assets: Optional[str] = None
    flow_url: Optional[str] = None
    output_assets: Optional[str] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None


class FlowBridgeRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID]
    scene_id: Optional[uuid.UUID]
    google_account_id: Optional[uuid.UUID]
    task_type: FlowTaskType
    status: FlowTaskStatus
    title: str
    description: Optional[str]
    input_prompts: Optional[str]
    reference_assets: Optional[str]
    flow_url: Optional[str]
    output_assets: Optional[str]
    notes: Optional[str]
    error_message: Optional[str]
    fallback_history: Optional[str] = None  # JSON array of fallback attempts
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class FlowBridgeList(BaseModel):
    items: List[FlowBridgeRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class FlowExport(BaseModel):
    """Export data for manual Flow processing"""
    project_id: uuid.UUID
    episode_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    task_type: FlowTaskType
    prompts: List[dict]
    reference_assets: List[dict]
    metadata: dict


class FlowImport(BaseModel):
    """Import results from manual Flow processing"""
    flow_task_id: uuid.UUID
    output_assets: List[dict]  # List of {file_path, asset_type, metadata}
    notes: Optional[str] = None
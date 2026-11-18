"""Settings schemas"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AIProviderSchema(BaseModel):
    id: str
    provider: str
    model: str
    key_env: str
    enabled: bool
    priority: int
    key_configured: bool = False  # Computed field, not stored


class AppSettingsRead(BaseModel):
    ai_providers: List[AIProviderSchema]
    google_oauth_configured: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppSettingsUpdate(BaseModel):
    ai_providers: Optional[List[AIProviderSchema]] = None
    google_oauth_client_id: Optional[str] = None
    google_oauth_client_secret: Optional[str] = None


class AppSettingsPatch(BaseModel):
    """Patch request - only sends configured flags, never secrets"""
    ai_providers: Optional[List[AIProviderSchema]] = None
    google_oauth_client_id: Optional[str] = None  # Will be encrypted
    google_oauth_client_secret: Optional[str] = None  # Will be encrypted
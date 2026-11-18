"""Google Account schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
import uuid


class GoogleAccountCreate(BaseModel):
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=255)
    # OAuth tokens will be set after OAuth flow
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    scopes: Optional[str] = None  # JSON array
    # Password for Flow Bridge (will be encrypted)
    password: Optional[str] = None


class GoogleAccountUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    password: Optional[str] = None


class GoogleAccountRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    display_name: Optional[str]
    is_active: bool
    account_index: int
    last_used_at: Optional[datetime]
    last_verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # Computed fields
    has_password: bool = False
    configured: bool = False

    class Config:
        from_attributes = True


class GoogleAccountList(BaseModel):
    items: List[GoogleAccountRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class GoogleOAuthStart(BaseModel):
    redirect_url: Optional[str] = None


class GoogleOAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None
"""Settings API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.models.settings import AppSettings
from app.schemas.settings import AppSettingsRead, AppSettingsUpdate, AIProviderSchema
from app.services.ai_client import get_ai_client
import json

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_default_providers() -> List[AIProviderSchema]:
    """Get default providers configuration (from env)"""
    # Default Nvidia NIM provider (verified working)
    providers = [
        AIProviderSchema(
            id="nvidia-nim-1",
            provider="nvidia",
            model="nvidia/nemotron-3-ultra-550b-a55b",
            key_env="NVIDIA_API_KEY",
            enabled=True,
            priority=1,
            key_configured=bool(__import__("os").getenv("NVIDIA_API_KEY")),
        )
    ]
    return providers


@router.get("", response_model=AppSettingsRead)
async def get_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get application settings (secrets never returned)"""
    # Get or create settings row
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = AppSettings(ai_providers=json.dumps([p.model_dump() for p in _get_default_providers()]))
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    # Parse providers and add key_configured flags
    providers_data = json.loads(settings.ai_providers)
    for p in providers_data:
        key_env = p.get("key_env")
        p["key_configured"] = bool(__import__("os").getenv(key_env)) if key_env else False

    return AppSettingsRead(
        ai_providers=[AIProviderSchema(**p) for p in providers_data],
        google_oauth_configured=settings.has_google_oauth_configured(),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.patch("", response_model=AppSettingsRead)
async def update_settings(
    update_data: AppSettingsUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update application settings"""
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one_or_none()

    if not settings:
        settings = AppSettings()
        db.add(settings)

    # Update AI providers if provided
    if update_data.ai_providers is not None:
        # Validate providers
        for p in update_data.ai_providers:
            if p.provider == "nvidia" and p.enabled:
                # Ensure NVIDIA_API_KEY is set if enabled
                if not __import__("os").getenv("NVIDIA_API_KEY"):
                    raise HTTPException(
                        status_code=400,
                        detail="NVIDIA_API_KEY must be set in environment to enable Nvidia provider"
                    )

        # Sort by priority
        sorted_providers = sorted(update_data.ai_providers, key=lambda p: p.priority)
        settings.ai_providers = json.dumps([p.model_dump() for p in sorted_providers])

    # Update Google OAuth credentials if provided (encrypted)
    if update_data.google_oauth_client_id is not None:
        if update_data.google_oauth_client_id:
            settings.set_google_oauth_client_id(update_data.google_oauth_client_id)
        else:
            settings.google_oauth_client_id_encrypted = None

    if update_data.google_oauth_client_secret is not None:
        if update_data.google_oauth_client_secret:
            settings.set_google_oauth_client_secret(update_data.google_oauth_client_secret)
        else:
            settings.google_oauth_client_secret_encrypted = None

    await db.commit()
    await db.refresh(settings)

    # Return updated settings (without secrets)
    providers_data = json.loads(settings.ai_providers)
    for p in providers_data:
        key_env = p.get("key_env")
        p["key_configured"] = bool(__import__("os").getenv(key_env)) if key_env else False

    return AppSettingsRead(
        ai_providers=[AIProviderSchema(**p) for p in providers_data],
        google_oauth_configured=settings.has_google_oauth_configured(),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )
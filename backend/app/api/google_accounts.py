"""Google Accounts API router"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.core.security import encrypt_data, decrypt_data
from app.models.google_account import GoogleAccount
from app.schemas.google_account import (
    GoogleAccountCreate, GoogleAccountUpdate, GoogleAccountRead,
    GoogleAccountList, GoogleOAuthStart, GoogleOAuthCallback
)
import uuid

router = APIRouter(prefix="/google-accounts", tags=["google-accounts"])

MAX_ACCOUNTS_PER_USER = 20


@router.post("", response_model=GoogleAccountRead, status_code=status.HTTP_201_CREATED)
async def create_google_account(
    account_data: GoogleAccountCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a Google account (after OAuth)"""
    user_uuid = uuid.UUID(user_id)
    # Check account limit
    count = await db.scalar(
        select(func.count(GoogleAccount.id)).where(GoogleAccount.user_id == user_uuid)
    )
    if count >= MAX_ACCOUNTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_ACCOUNTS_PER_USER} accounts per user")

    # Check if email already added
    existing = await db.execute(
        select(GoogleAccount).where(
            GoogleAccount.user_id == user_uuid,
            GoogleAccount.email == account_data.email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This Google account is already connected")

    # Find available account index
    used_indices = await db.execute(
        select(GoogleAccount.account_index).where(GoogleAccount.user_id == user_uuid)
    )
    used = {idx for idx, in used_indices.all()}
    account_index = next(i for i in range(MAX_ACCOUNTS_PER_USER) if i not in used)

    # Encrypt tokens
    access_token_encrypted = encrypt_data(account_data.access_token) if account_data.access_token else None
    refresh_token_encrypted = encrypt_data(account_data.refresh_token) if account_data.refresh_token else None

    account = GoogleAccount(
        user_id=user_uuid,
        email=account_data.email,
        display_name=account_data.display_name,
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
        token_expiry=account_data.token_expiry,
        scopes=account_data.scopes,
        account_index=account_index,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("", response_model=GoogleAccountList)
async def list_google_accounts(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = True,
):
    """List user's Google accounts"""
    user_uuid = uuid.UUID(user_id)
    query = select(GoogleAccount).where(GoogleAccount.user_id == user_uuid)

    if active_only:
        query = query.where(GoogleAccount.is_active == True)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(GoogleAccount.account_index).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    accounts = result.scalars().all()

    return GoogleAccountList(
        items=accounts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{account_id}", response_model=GoogleAccountRead)
async def get_google_account(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific Google account"""
    user_uuid = uuid.UUID(user_id)
    account_uuid = uuid.UUID(account_id)
    result = await db.execute(
        select(GoogleAccount).where(
            GoogleAccount.id == account_uuid,
            GoogleAccount.user_id == user_uuid,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Google account not found")
    return account


@router.patch("/{account_id}", response_model=GoogleAccountRead)
async def update_google_account(
    account_id: str,
    account_data: GoogleAccountUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a Google account"""
    user_uuid = uuid.UUID(user_id)
    account_uuid = uuid.UUID(account_id)
    result = await db.execute(
        select(GoogleAccount).where(
            GoogleAccount.id == account_uuid,
            GoogleAccount.user_id == user_uuid,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Google account not found")

    update_data = account_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_google_account(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect a Google account"""
    user_uuid = uuid.UUID(user_id)
    account_uuid = uuid.UUID(account_id)
    result = await db.execute(
        select(GoogleAccount).where(
            GoogleAccount.id == account_uuid,
            GoogleAccount.user_id == user_uuid,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Google account not found")

    await db.delete(account)
    await db.commit()


@router.post("/oauth/start", response_model=dict)
async def start_oauth(
    oauth_data: GoogleOAuthStart,
    user_id: str = Depends(get_current_user_id),
):
    """Start Google OAuth flow (returns authorization URL)"""
    # This is a placeholder - in production, integrate with Google OAuth
    # For MVP, return a mock URL
    from app.core.config import settings
    import urllib.parse

    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/photoslibrary",
        "https://www.googleapis.com/auth/youtube.upload",
    ]

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID or "mock-client-id",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id,  # Include user ID in state
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    return {"authorization_url": auth_url}


@router.post("/oauth/callback", response_model=GoogleAccountRead)
async def oauth_callback(
    callback_data: GoogleOAuthCallback,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback (placeholder)"""
    # This is a placeholder - in production, exchange code for tokens
    # For MVP, create a mock account

    user_uuid = uuid.UUID(user_id)
    # Check account limit
    count = await db.scalar(
        select(func.count(GoogleAccount.id)).where(GoogleAccount.user_id == user_uuid)
    )
    if count >= MAX_ACCOUNTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_ACCOUNTS_PER_USER} accounts per user")

    # Find available index
    used_indices = await db.execute(
        select(GoogleAccount.account_index).where(GoogleAccount.user_id == user_uuid)
    )
    used = {idx for idx, in used_indices.all()}
    account_index = next(i for i in range(MAX_ACCOUNTS_PER_USER) if i not in used)

    # Mock account for testing
    account = GoogleAccount(
        user_id=user_uuid,
        email=f"user{count+1}@example.com",
        display_name=f"Test Account {count+1}",
        access_token_encrypted=encrypt_data("mock-access-token"),
        refresh_token_encrypted=encrypt_data("mock-refresh-token"),
        scopes='["drive", "photos", "youtube"]',
        account_index=account_index,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/{account_id}/tokens")
async def get_account_tokens(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get decrypted tokens for API calls (internal use)"""
    user_uuid = uuid.UUID(user_id)
    account_uuid = uuid.UUID(account_id)
    result = await db.execute(
        select(GoogleAccount).where(
            GoogleAccount.id == account_uuid,
            GoogleAccount.user_id == user_uuid,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Google account not found")

    return {
        "access_token": decrypt_data(account.access_token_encrypted) if account.access_token_encrypted else None,
        "refresh_token": decrypt_data(account.refresh_token_encrypted) if account.refresh_token_encrypted else None,
        "token_expiry": account.token_expiry,
    }
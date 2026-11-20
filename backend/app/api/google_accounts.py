"""Google Accounts API router - Real OAuth 2.0 implementation"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.core.security import encrypt_data
from app.models.google_account import GoogleAccount
from app.models.oauth_state import OAuthState
from app.models.settings import AppSettings
from app.services.google_account_service import (
    GoogleAccountError,
    get_google_oauth_credentials,
    refresh_access_token,
)
from app.services import browser_login as browser_login_service
from app.services.browser_login import BrowserLoginError
from app.schemas.google_account import (
    GoogleAccountCreate, GoogleAccountUpdate, GoogleAccountRead,
    GoogleAccountList, GoogleOAuthStart, GoogleOAuthCallback
)
import os
import uuid
import secrets
import httpx
import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

router = APIRouter(prefix="/google-accounts", tags=["google-accounts"])

MAX_ACCOUNTS_PER_USER = 20

STATE_TTL_MINUTES = 10
DEFAULT_REDIRECT_URI = "http://localhost:8000/api/google-accounts/oauth/callback"


async def _generate_state(db: AsyncSession, user_id: str, redirect_uri: str) -> str:
    """Generate a secure random state, stored DB-side (single-use, TTL).

    Audit ronde 2 P1-19: previously an in-memory dict — lost on restart,
    broken with >1 worker. The redirect_uri used at /oauth/start is
    stored with the state so the callback exchanges the code with
    exactly the same URI.
    """
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.add(OAuthState(
        state=state,
        user_id=uuid.UUID(user_id),
        redirect_uri=redirect_uri,
        created_at=now,
        expires_at=now + timedelta(minutes=STATE_TTL_MINUTES),
    ))
    # Best-effort cleanup of expired states
    await db.execute(
        OAuthState.__table__.delete().where(
            OAuthState.expires_at < now,
            OAuthState.state != state,
        )
    )
    await db.commit()
    return state


async def _verify_state(db: AsyncSession, state: str, user_id: str) -> str | None:
    """Verify OAuth state and consume it (single-use).

    Returns the redirect_uri stored at /oauth/start, or None if the
    state is unknown, belongs to another user, or expired.
    """
    stored = await db.get(OAuthState, state)
    if not stored:
        return None
    redirect_uri = stored.redirect_uri
    await db.delete(stored)
    await db.commit()
    if str(stored.user_id) != user_id:
        return None
    # SQLite stores datetimes naive; normalize before comparing.
    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        return None
    return redirect_uri


async def _http_post_json(client: httpx.AsyncClient, url: str, **kwargs) -> dict:
    """POST + parse JSON, mapping transport errors to 502 (audit F-H2).

    Previously a ConnectError/SSL error from the VM proxy bubbled up as
    an unhandled 500; a failure to reach Google is a bad-gateway (502),
    not a server bug.
    """
    try:
        response = await client.post(url, **kwargs)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Google: {e}")
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {response.text}")
    return response.json()


async def _http_get_json(client: httpx.AsyncClient, url: str, **kwargs) -> dict:
    """GET + parse JSON, mapping transport errors to 502 (audit F-H2)."""
    try:
        response = await client.get(url, **kwargs)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Google: {e}")
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to get user info: {response.text}")
    return response.json()


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
    password_encrypted = encrypt_data(account_data.password) if account_data.password else None

    account = GoogleAccount(
        user_id=user_uuid,
        email=account_data.email,
        display_name=account_data.display_name,
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
        token_expiry=account_data.token_expiry,
        scopes=account_data.scopes,
        password_encrypted=password_encrypted,
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

    # Add computed fields
    items = []
    for acc in accounts:
        item = GoogleAccountRead.model_validate(acc)
        item.has_password = acc.password_encrypted is not None
        item.configured = acc.access_token_encrypted is not None
        items.append(item)

    return GoogleAccountList(
        items=items,
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

    item = GoogleAccountRead.model_validate(account)
    item.has_password = account.password_encrypted is not None
    item.configured = account.access_token_encrypted is not None
    return item


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
        if field == "password" and value is not None:
            account.set_password(value)
        else:
            setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    item = GoogleAccountRead.model_validate(account)
    item.has_password = account.password_encrypted is not None
    item.configured = account.access_token_encrypted is not None
    return item


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
    db: AsyncSession = Depends(get_db),
):
    """Start Google OAuth flow (returns authorization URL)"""
    client_id, client_secret = await get_google_oauth_credentials(db)

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth credentials not configured. Set them in Settings first."
        )

    # Use redirect URI from settings or default
    redirect_uri = oauth_data.redirect_url or DEFAULT_REDIRECT_URI

    # Generate secure state (stored DB-side together with redirect_uri)
    state = await _generate_state(db, user_id, redirect_uri)

    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/photoslibrary",
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return {"authorization_url": auth_url, "state": state}


@router.post("/oauth/callback", response_model=GoogleAccountRead)
async def oauth_callback(
    callback_data: GoogleOAuthCallback,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback - exchange code for tokens"""
    # Verify state (single-use, DB-backed) and recover the redirect_uri
    # used at /oauth/start — the code must be exchanged with the same URI.
    if not callback_data.state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    redirect_uri = await _verify_state(db, callback_data.state, user_id)
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    client_id, client_secret = await get_google_oauth_credentials(db)

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth credentials not configured"
        )

    # Exchange code for tokens (transport errors -> 502, not 500)
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": callback_data.code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    # Explicitly configure proxy to avoid httpx's buggy trust_env parsing of no_proxy (e.g., IPv6 ::1 with brackets)
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    async with httpx.AsyncClient(timeout=30.0, proxy=proxy_url, trust_env=False) as client:
        tokens = await _http_post_json(client, token_url, data=token_data)

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    scope = tokens.get("scope", "")

    # Get user info to extract email
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    # Explicitly configure proxy to avoid httpx's buggy trust_env parsing of no_proxy (e.g., IPv6 ::1 with brackets)
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    async with httpx.AsyncClient(timeout=30.0, proxy=proxy_url, trust_env=False) as client:
        userinfo = await _http_get_json(client, userinfo_url, headers=headers)

    email = userinfo.get("email")
    display_name = userinfo.get("name") or userinfo.get("given_name")

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google")

    user_uuid = uuid.UUID(user_id)
    # Check account limit
    count = await db.scalar(
        select(func.count(GoogleAccount.id)).where(GoogleAccount.user_id == user_uuid)
    )
    if count >= MAX_ACCOUNTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_ACCOUNTS_PER_USER} accounts per user")

    # Check if email already exists
    existing = await db.execute(
        select(GoogleAccount).where(
            GoogleAccount.user_id == user_uuid,
            GoogleAccount.email == email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This Google account is already connected")

    # Find available index
    used_indices = await db.execute(
        select(GoogleAccount.account_index).where(GoogleAccount.user_id == user_uuid)
    )
    used = {idx for idx, in used_indices.all()}
    account_index = next(i for i in range(MAX_ACCOUNTS_PER_USER) if i not in used)

    # Calculate token expiry
    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Encrypt tokens
    access_token_encrypted = encrypt_data(access_token) if access_token else None
    refresh_token_encrypted = encrypt_data(refresh_token) if refresh_token else None

    account = GoogleAccount(
        user_id=user_uuid,
        email=email,
        display_name=display_name,
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
        token_expiry=token_expiry,
        scopes=json.dumps(scope.split()) if scope else None,
        account_index=account_index,
        last_verified_at=datetime.now(timezone.utc),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    item = GoogleAccountRead.model_validate(account)
    item.has_password = False
    item.configured = True
    return item


@router.post("/{account_id}/refresh", response_model=dict)
async def refresh_account_token(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token for a Google account"""
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

    if not account.refresh_token_encrypted:
        raise HTTPException(status_code=400, detail="No refresh token available")

    # Shared refresh logic (also used by the Flow account fallback).
    try:
        await refresh_access_token(db, account)
    except GoogleAccountError as e:
        raise HTTPException(status_code=400, detail=e.detail)

    await db.commit()
    await db.refresh(account)

    return {"success": True, "token_expiry": account.token_expiry}


@router.post("/{account_id}/verify", response_model=dict)
async def verify_account(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Verify Google account by calling tokeninfo/userinfo endpoint (real check)"""
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

    if not account.access_token_encrypted:
        raise HTTPException(status_code=400, detail="No access token available")

    # Try to use access token, refresh if needed
    access_token = decrypt_data(account.access_token_encrypted)

    # Check token expiry and refresh if needed (shared refresh logic;
    # a failed refresh is ignored here and the old token is verified,
    # same behaviour as before the fallback refactor).
    if account.token_expiry and account.token_expiry <= datetime.now(timezone.utc) + timedelta(minutes=5):
        if account.refresh_token_encrypted:
            try:
                await refresh_access_token(db, account)
                await db.commit()
                access_token = decrypt_data(account.access_token_encrypted)
            except GoogleAccountError:
                pass

    # Verify with tokeninfo endpoint
    verify_url = "https://oauth2.googleapis.com/tokeninfo"
    params = {"access_token": access_token}

    # Explicitly configure proxy to avoid httpx's buggy trust_env parsing of no_proxy (e.g., IPv6 ::1 with brackets)
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    async with httpx.AsyncClient(timeout=30.0, proxy=proxy_url, trust_env=False) as client:
        verify_response = await client.get(verify_url, params=params)
        if verify_response.status_code != 200:
            # Try userinfo as fallback
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            userinfo_response = await client.get(userinfo_url, headers=headers)
            if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail=f"Token verification failed: {verify_response.text}"
                )

    account.last_verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(account)

    return {"success": True, "verified_at": account.last_verified_at, "email": account.email}


@router.post("/{account_id}/browser-login", response_model=dict)
async def browser_login_account(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    headless: bool = True,
):
    """Sign in to Google in this account's own persistent browser profile.

    Uses email + password stored ENCRYPTED in the DB — no Cloud Console,
    no client_id/secret, no OAuth. The browser session (cookies) is saved
    in a per-account profile so later Flow runs reuse it without signing
    in again. Returns the stored session status; on captcha/2FA or a
    rejected password the failure is reported honestly (the user can sign
    in manually in their own browser instead).
    """
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
    if not account.password_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Account has no password stored — browser login needs email + password",
        )
    try:
        record = await browser_login_service.login_google_account(
            account, headless=headless
        )
    except BrowserLoginError as e:
        if e.reason == "login_failed":
            raise HTTPException(status_code=401, detail=e.detail)
        if e.reason in ("unreachable", "browser_unavailable"):
            raise HTTPException(status_code=502, detail=e.detail)
        raise HTTPException(status_code=400, detail=e.detail)
    return {
        "success": True,
        "email": account.email,
        "status": record.get("status", "logged_in"),
        "session_saved": True,
        "detail": record.get("detail", ""),
    }


@router.get("/{account_id}/browser-session", response_model=dict)
async def get_browser_session(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Stored browser-session status for an account (no browser launched).

    Reports the last browser-login outcome saved for this account's
    profile, or has_session=false when it never signed in via browser.
    """
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
    status = browser_login_service.read_session_status(user_uuid, account_uuid)
    if not status:
        return {"has_session": False, "email": account.email}
    return {"has_session": True, "email": account.email, **status}

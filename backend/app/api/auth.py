"""Authentication API router"""
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token,
    verify_token, is_token_revoked, revoke_token,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserRead, Token

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> str:
    """Extract and validate current user ID from access token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:]
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Revoked tokens (logout) are rejected even before expiry.
    if await is_token_revoked(db, payload.get("jti")):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = payload.get("sub")
    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user object"""
    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get access/refresh tokens"""
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return Token(access_token=access_token, refresh_token=refresh_token)


from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = verify_token(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # A revoked refresh token (logout) cannot mint new access tokens.
    if await is_token_revoked(db, payload.get("jti")):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = payload.get("sub")
    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserRead)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user info"""
    return user


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


def _expiry_of(payload: dict) -> datetime | None:
    """Token expiry as an aware datetime (None when the claim is absent)."""
    exp = payload.get("exp")
    if exp is None:
        return None
    try:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the caller's tokens (token revocation, round 2).

    Revokes the access token from the Authorization header (when it is a
    still-valid access token) and the refresh token from the body (when
    given). Revoked tokens are rejected by /me, /refresh and every
    authenticated endpoint until their own expiry. Unknown/expired
    tokens are simply ignored — logout is idempotent.
    """
    revoked = 0
    if authorization and authorization.startswith("Bearer "):
        payload = verify_token(authorization[7:], "access")
        if payload and payload.get("jti"):
            if await revoke_token(
                db,
                jti=payload["jti"],
                token_type="access",
                user_id=payload.get("sub"),
                expires_at=_expiry_of(payload),
            ):
                revoked += 1
    if request.refresh_token:
        payload = verify_token(request.refresh_token, "refresh")
        if payload and payload.get("jti"):
            if await revoke_token(
                db,
                jti=payload["jti"],
                token_type="refresh",
                user_id=payload.get("sub"),
                expires_at=_expiry_of(payload),
            ):
                revoked += 1
    return {"detail": "Logged out", "revoked": revoked}
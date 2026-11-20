"""Security utilities: JWT, password hashing, encryption"""
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# JWT tokens
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # jti (unique token id) makes each token individually revocable
    # (see RevokedToken + POST /api/auth/logout).
    to_encode.update({"exp": expire, "type": "access", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    payload = decode_token(token)
    if payload and payload.get("type") == token_type:
        return payload
    return None


# Encryption for sensitive data (Google OAuth tokens)
def get_encryption_key() -> bytes:
    """Get the Fernet encryption key.

    A real Fernet key in ENCRYPTION_KEY is used verbatim. (The old code
    truncated it to 32 chars and re-encoded it first, which silently
    derived a DIFFERENT key from the one the operator configured.)
    Any other value falls back to the legacy pad/truncate derivation so
    data encrypted by older versions stays readable; production startup
    validation (app/core/secrets.py) refuses that fallback.
    """
    if settings.ENCRYPTION_KEY:
        try:
            Fernet(settings.ENCRYPTION_KEY.encode())
            return settings.ENCRYPTION_KEY.encode()
        except Exception:
            pass
        # Legacy derivation (pre-round-2): pad/truncate to 32 bytes.
        key = settings.ENCRYPTION_KEY.encode()[:32].ljust(32, b'0')
        import base64
        return base64.urlsafe_b64encode(key)
    # Generate a deterministic key from SECRET_KEY for development
    import hashlib
    import base64
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


# ---------------------------------------------------------------- token revocation

async def is_token_revoked(db: AsyncSession, jti: str | None) -> bool:
    """True when this token id is in the revocation table.

    Tokens issued before jti existed (no jti claim) cannot be revoked;
    they simply expire (access 30 min, refresh 7 days).
    """
    if not jti:
        return False
    from app.models.revoked_token import RevokedToken

    result = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
    return result.scalar_one_or_none() is not None


async def revoke_token(
    db: AsyncSession,
    *,
    jti: str,
    token_type: str,
    user_id: str | None,
    expires_at: datetime | None,
) -> bool:
    """Record a token id as revoked and drop expired rows.

    Returns True when this call inserted a new row (False when the
    token was already revoked — logout is idempotent).
    """
    from app.models.revoked_token import RevokedToken

    existing = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
    inserted = False
    if existing.scalar_one_or_none() is None:
        db.add(RevokedToken(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
        ))
        inserted = True
    # Opportunistic cleanup so the table does not grow forever.
    if expires_at is not None:
        await db.execute(
            delete(RevokedToken).where(
                RevokedToken.expires_at < datetime.now(timezone.utc)
            )
        )
    await db.commit()
    return inserted


_fernet = None


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_encryption_key())
    return _fernet


def encrypt_data(data: str) -> str:
    """Encrypt string data"""
    f = get_fernet()
    return f.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt string data"""
    f = get_fernet()
    return f.decrypt(encrypted_data.encode()).decode()


# Token generation
def generate_random_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)
"""Google account token helpers shared by the google-accounts router and the
Flow Bridge account fallback.

Reads/writes tokens ENCRYPTED in the DB (via app.core.security). The former
GET /google-accounts/{id}/tokens HTTP endpoint, which returned plaintext
tokens, was DELETED 20 Nov 2026 on Di's order — no HTTP route exposes
decrypted tokens or passwords anymore.
"""
import os
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_data, encrypt_data
from app.models.google_account import GoogleAccount
from app.models.settings import AppSettings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# Refresh a token that expires within this window, instead of waiting for
# Google to reject it mid-Flow.
REFRESH_BEFORE_EXPIRY = timedelta(minutes=5)


class GoogleAccountError(Exception):
    """One Google account cannot be used right now.

    reason is a machine-readable code recorded in the Flow task's
    fallback_history so the user sees WHY each account was skipped:
      - no_token: account has no access token stored
      - token_expired: token expired and there is no refresh token
      - refresh_failed: Google rejected the refresh-token exchange
      - token_invalid: tokeninfo rejected the (fresh) access token
      - quota_exceeded: Google answered 429 (quota / rate limit)
      - unreachable: Google could not be reached at all (network/proxy)
    """

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail or reason


def _proxy_url() -> str | None:
    # Same explicit-proxy handling as the google-accounts router: avoids
    # httpx's buggy trust_env parsing of no_proxy (e.g. IPv6 ::1 brackets).
    return (
        os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("HTTP_PROXY")
        or os.getenv("http_proxy")
    )


async def get_google_oauth_credentials(db: AsyncSession) -> tuple[str | None, str | None]:
    """Google OAuth client credentials from settings (row id 1)."""
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        return None, None
    return settings.get_google_oauth_client_id(), settings.get_google_oauth_client_secret()


async def refresh_access_token(db: AsyncSession, account: GoogleAccount) -> None:
    """Exchange the stored refresh token for a fresh access token.

    Mutates the account in place (new encrypted tokens + expiry); the
    caller commits. Raises GoogleAccountError on any failure.
    """
    if not account.refresh_token_encrypted:
        raise GoogleAccountError("token_expired", "No refresh token available")

    client_id, client_secret = await get_google_oauth_credentials(db)
    if not client_id or not client_secret:
        raise GoogleAccountError("refresh_failed", "Google OAuth credentials not configured")

    refresh_token = decrypt_data(account.refresh_token_encrypted)
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0, proxy=_proxy_url(), trust_env=False) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
    except httpx.HTTPError as e:
        raise GoogleAccountError("unreachable", f"Could not reach Google: {e}")
    if response.status_code != 200:
        raise GoogleAccountError("refresh_failed", f"Token refresh failed: {response.text}")

    tokens = response.json()
    access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in", 3600)
    new_refresh_token = tokens.get("refresh_token")
    if not access_token:
        raise GoogleAccountError("refresh_failed", "Google returned no access token")

    account.access_token_encrypted = encrypt_data(access_token)
    if new_refresh_token:
        account.refresh_token_encrypted = encrypt_data(new_refresh_token)
    account.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    account.last_verified_at = datetime.now(timezone.utc)


async def verify_access_token(access_token: str) -> None:
    """Check an access token against Google's tokeninfo endpoint.

    Returns silently when the token is accepted; raises GoogleAccountError
    otherwise. A 429 means this account's quota is exhausted — the caller
    should fall through to the next account, not retry this one.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, proxy=_proxy_url(), trust_env=False) as client:
            response = await client.get(
                GOOGLE_TOKENINFO_URL, params={"access_token": access_token}
            )
    except httpx.HTTPError as e:
        raise GoogleAccountError("unreachable", f"Could not reach Google: {e}")
    if response.status_code == 200:
        return
    if response.status_code == 429:
        raise GoogleAccountError("quota_exceeded", f"Google rate limit (429): {response.text}")
    raise GoogleAccountError("token_invalid", f"Token rejected by Google ({response.status_code}): {response.text}")


def _token_expiry(account: GoogleAccount) -> datetime | None:
    """token_expiry as an aware datetime (SQLite stores it naive)."""
    expiry = account.token_expiry
    if expiry is None:
        return None
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry


async def cleanup_undecryptable_credentials(db: AsyncSession) -> dict[str, int]:
    """Clear stored Google ciphertext that no longer decrypts.

    The Fernet key derivation changed in future-dev round 2 (the old
    code truncated ENCRYPTION_KEY to 32 chars and re-encoded it, which
    derived a DIFFERENT key). Rows encrypted under the old derivation
    now raise InvalidToken on every decrypt — including the test
    accounts left by the 19 Nov fallback test. An undecryptable value
    is unusable data, not a secret worth keeping: clear the field so
    the account stays usable (the user re-enters a password / re-links
    the account) instead of 500ing every caller that touches it.

    Only clears fields that FAIL to decrypt; good rows are untouched.
    Returns {"password": n, "access_token": n, "refresh_token": n}.
    Commits only when something was cleared.
    """
    import logging

    logger = logging.getLogger(__name__)
    result = await db.execute(select(GoogleAccount))
    accounts = result.scalars().all()
    cleared: dict[str, int] = {"password": 0, "access_token": 0, "refresh_token": 0}
    for account in accounts:
        for field, attr in (
            ("password", "password_encrypted"),
            ("access_token", "access_token_encrypted"),
            ("refresh_token", "refresh_token_encrypted"),
        ):
            value = getattr(account, attr)
            if not value:
                continue
            try:
                decrypt_data(value)
            except Exception:  # noqa: BLE001 - any decrypt failure = unusable data
                logger.warning(
                    "Clearing undecryptable %s for Google account %s (%s)",
                    field,
                    account.id,
                    account.email,
                )
                setattr(account, attr, None)
                cleared[field] += 1
    if any(cleared.values()):
        await db.commit()
    return cleared

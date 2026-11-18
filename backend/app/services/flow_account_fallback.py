"""Flow Bridge Google-account fallback.

Context: a Flow task is bound to ONE google_account_id chosen at creation.
If that account's quota is exhausted (429), its token is invalid, or its
refresh fails, the task used to fail outright. There is no automatic Flow
execution in this leg (same as Hermes: the bridge is export -> manual Flow
-> import), so the fallback lives at the point where the account is
actually consumed: resolving a usable account and marking the task ready.

Mirrors the LLM provider fallback in app/services/ai_client.py: try
candidates in order, move on on per-account failure, and when every
candidate fails report an honest error listing each account + reason —
never a silent failure.

Candidate order: the task's pinned account first (if any), then the user's
other enabled (is_active) accounts by account_index. Disabled accounts and
accounts belonging to another user are never tried.
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_data
from app.models.flow_bridge import FlowBridge, FlowTaskStatus
from app.models.google_account import GoogleAccount
from app.services.google_account_service import (
    GoogleAccountError,
    refresh_access_token,
    verify_access_token,
    _token_expiry,
    REFRESH_BEFORE_EXPIRY,
)

# Re-exported so tests can monkeypatch the seams on THIS module:
#   monkeypatch.setattr("app.services.flow_account_fallback.verify_access_token", fake)
#   monkeypatch.setattr("app.services.flow_account_fallback.refresh_access_token", fake)
__all__ = [
    "AllGoogleAccountsFailed",
    "GoogleUnreachable",
    "get_candidate_accounts",
    "resolve_account_for_task",
    "run_fallback_for_task",
]


class AllGoogleAccountsFailed(Exception):
    """Every candidate account failed; .attempts lists each + reason."""

    def __init__(self, attempts: list[dict]):
        self.attempts = attempts
        summary = "; ".join(
            f"{a['email']}: {a['reason']}" for a in attempts
        )
        super().__init__(f"All Google accounts failed — {summary}")


class GoogleUnreachable(Exception):
    """Google could not be reached at all; retrying other accounts is
    pointless (same network), so the run aborts instead of burning
    through every account. .attempts holds the attempts made so far."""

    def __init__(self, attempts: list[dict], detail: str = ""):
        self.attempts = attempts
        super().__init__(detail or "Google could not be reached")


async def get_candidate_accounts(
    db: AsyncSession, user_id: uuid.UUID, preferred_id: uuid.UUID | None
) -> list[GoogleAccount]:
    """User's enabled accounts: pinned account first, then by account_index."""
    result = await db.execute(
        select(GoogleAccount)
        .where(GoogleAccount.user_id == user_id, GoogleAccount.is_active == True)  # noqa: E712
        .order_by(GoogleAccount.account_index)
    )
    accounts = list(result.scalars().all())
    if preferred_id:
        accounts.sort(key=lambda a: (a.id != preferred_id, a.account_index))
    return accounts


async def _attempt_account(db: AsyncSession, account: GoogleAccount) -> dict:
    """Try one account: ensure a fresh token, verify it against Google.

    Returns an attempt record. Raises GoogleUnreachable (not a record)
    when Google itself cannot be reached — that aborts the whole run.
    """
    attempt = {
        "account_id": str(account.id),
        "email": account.email,
        "outcome": "failed",
        "reason": "",
    }
    try:
        if not account.access_token_encrypted:
            raise GoogleAccountError("no_token", "Account has no access token stored")
        expiry = _token_expiry(account)
        if expiry is not None and expiry <= datetime.now(timezone.utc) + REFRESH_BEFORE_EXPIRY:
            await refresh_access_token(db, account)
        access_token = decrypt_data(account.access_token_encrypted)
        await verify_access_token(access_token)
    except GoogleAccountError as e:
        if e.reason == "unreachable":
            raise GoogleUnreachable([attempt | {"reason": e.reason, "detail": e.detail}])
        attempt["reason"] = e.reason
        attempt["detail"] = e.detail
        return attempt
    attempt["outcome"] = "ok"
    attempt["reason"] = "verified"
    return attempt


async def resolve_account_for_task(
    db: AsyncSession, user_id: uuid.UUID, task: FlowBridge
) -> tuple[GoogleAccount, list[dict]]:
    """Walk the candidate accounts until one verifies.

    Returns (account, attempts). Raises AllGoogleAccountsFailed when no
    account works, GoogleUnreachable when Google cannot be reached.
    """
    accounts = await get_candidate_accounts(db, user_id, task.google_account_id)
    if not accounts:
        raise AllGoogleAccountsFailed([])

    attempts: list[dict] = []
    for account in accounts:
        try:
            attempt = await _attempt_account(db, account)
        except GoogleUnreachable as e:
            # Abort: other accounts would hit the same dead network.
            raise GoogleUnreachable(attempts + e.attempts, str(e))
        attempts.append(attempt)
        if attempt["outcome"] == "ok":
            return account, attempts

    raise AllGoogleAccountsFailed(attempts)


def _record_attempts(task: FlowBridge, attempts: list[dict]) -> None:
    task.fallback_history = json.dumps(attempts)


def _failure_message(attempts: list[dict]) -> str:
    if not attempts:
        return "No enabled Google accounts available for this user"
    lines = [f"{a['email']}: {a.get('reason', 'failed')}" for a in attempts]
    return "All Google accounts failed — " + "; ".join(lines)


async def run_fallback_for_task(
    db: AsyncSession, user_id: uuid.UUID, task: FlowBridge
) -> FlowBridge:
    """Resolve a working account for the task and record the outcome.

    Success: task.google_account_id = working account, status READY_FOR_FLOW,
    fallback_history = per-account attempts, last_used_at stamped.
    All accounts failed / Google unreachable: status FAILED, error_message
    lists every account + reason (honest error, never silent), history
    recorded, then the exception re-raised so the endpoint answers 502.
    """
    try:
        account, attempts = await resolve_account_for_task(db, user_id, task)
    except AllGoogleAccountsFailed as e:
        _record_attempts(task, e.attempts)
        task.status = FlowTaskStatus.FAILED
        task.error_message = _failure_message(e.attempts)
        await db.commit()
        raise
    except GoogleUnreachable as e:
        _record_attempts(task, e.attempts)
        task.status = FlowTaskStatus.FAILED
        task.error_message = f"Google unreachable: {e}"
        await db.commit()
        raise

    _record_attempts(task, attempts)
    task.google_account_id = account.id
    task.status = FlowTaskStatus.READY_FOR_FLOW
    task.error_message = None
    account.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return task

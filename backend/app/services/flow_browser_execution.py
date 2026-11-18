"""Automatic Google Flow execution via browser sessions, with account fallback.

Mirrors the token-level fallback in app/services/flow_account_fallback.py
(same candidate order, same honest-failure contract), but the per-account
attempt is a real browser run instead of a token check:

- candidates: the task's pinned account first, then the user's other
  enabled accounts by account_index (disabled / other users' accounts
  are never tried);
- per account: the account's own persistent browser profile signs in to
  Google with email + password (NO Cloud Console, NO client_id/secret,
  NO OAuth exchange anywhere on this path) and submits the task's prompt
  to Google Flow;
- an account is skipped when it has no stored password, its login is
  rejected, Google asks for a human (captcha/2FA), its Flow quota is
  exhausted, or Flow blocks the automation — the next account is tried
  automatically;
- every attempt is recorded in the task's fallback_history (mode:
  "browser"), appended after any earlier token-fallback attempts;
- when every account fails the task is persisted as FAILED with an
  error_message naming each account + reason, and the exception is
  re-raised so the endpoint answers 502. The manual export path
  (/flow/export) still works after that — nothing is lost.

Seam for tests: monkeypatch `default_browser_runner` on THIS module
(e.g. a fake keyed by account email) — the same pattern the token
fallback uses for verify_access_token.
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow_bridge import FlowBridge, FlowTaskStatus
from app.models.google_account import GoogleAccount
from app.services.browser_login import (
    BrowserLoginError,
    execute_flow_prompt,
)
from app.services.flow_account_fallback import get_candidate_accounts

__all__ = [
    "AllBrowserAccountsFailed",
    "BrowserUnreachable",
    "default_browser_runner",
    "run_browser_execution",
]

# Failures that abort the whole run: the machine/network is the problem,
# so the next account would hit the same wall.
_ABORT_REASONS = {"unreachable", "browser_unavailable"}


class AllBrowserAccountsFailed(Exception):
    """Every candidate account failed in the browser; .attempts lists each."""

    def __init__(self, attempts: list[dict]):
        self.attempts = attempts
        summary = "; ".join(f"{a['email']}: {a['reason']}" for a in attempts)
        super().__init__(f"All Google accounts failed in the browser — {summary}")


class BrowserUnreachable(Exception):
    """Google / the browser could not be reached at all; .attempts so far."""

    def __init__(self, attempts: list[dict], detail: str = ""):
        self.attempts = attempts
        super().__init__(detail or "Google could not be reached from the browser")


async def default_browser_runner(
    account: GoogleAccount, prompts: list[str], headless: bool = True
) -> dict:
    """Real browser run: submit the first prompt to Flow as this account."""
    return await execute_flow_prompt(account, prompts[0], headless=headless)


def _parse_prompts(task: FlowBridge) -> list[str]:
    """Task input_prompts is a JSON array (of strings or {prompt} dicts)."""
    if not task.input_prompts:
        return []
    try:
        raw = json.loads(task.input_prompts)
    except (json.JSONDecodeError, TypeError):
        return [task.input_prompts] if task.input_prompts.strip() else []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    prompts = []
    for item in raw if isinstance(raw, list) else [raw]:
        if isinstance(item, str) and item.strip():
            prompts.append(item)
        elif isinstance(item, dict):
            text = item.get("prompt") or item.get("text") or ""
            if text.strip():
                prompts.append(text)
    return prompts


def _record_attempts(task: FlowBridge, attempts: list[dict]) -> None:
    """Append browser attempts to the task's fallback_history JSON."""
    existing: list[dict] = []
    if task.fallback_history:
        try:
            existing = json.loads(task.fallback_history)
        except (json.JSONDecodeError, TypeError):
            existing = []
    task.fallback_history = json.dumps(existing + attempts)


def _failure_message(attempts: list[dict]) -> str:
    if not attempts:
        return "No enabled Google accounts available for this user"
    lines = [f"{a['email']}: {a.get('reason', 'failed')}" for a in attempts]
    return (
        "All Google accounts failed in the browser — " + "; ".join(lines)
        + ". Manual export (/flow/export) still works."
    )


async def run_browser_execution(
    db: AsyncSession,
    user_id: uuid.UUID,
    task: FlowBridge,
    runner=None,
    headless: bool = True,
) -> FlowBridge:
    """Run a Flow task in the browser, switching accounts on failure.

    Success: task bound to the working account, status IN_PROGRESS,
    flow_url set, fallback_history appended, last_used_at stamped.
    All accounts failed / Google unreachable: status FAILED, honest
    error_message, history recorded, exception re-raised (endpoint -> 502).
    """
    run = runner or default_browser_runner
    prompts = _parse_prompts(task)
    if not prompts:
        # Client error, not an account failure: no prompt to run at all.
        task.status = FlowTaskStatus.FAILED
        task.error_message = "Flow task has no prompts to execute"
        await db.commit()
        raise ValueError("Flow task has no prompts to execute")

    accounts = await get_candidate_accounts(db, user_id, task.google_account_id)
    if not accounts:
        task.status = FlowTaskStatus.FAILED
        task.error_message = "No enabled Google accounts available for this user"
        await db.commit()
        raise AllBrowserAccountsFailed([])

    attempts: list[dict] = []
    for account in accounts:
        attempt = {
            "account_id": str(account.id),
            "email": account.email,
            "outcome": "failed",
            "reason": "",
            "mode": "browser",
        }
        if not account.password_encrypted:
            attempt["reason"] = "no_password"
            attempt["detail"] = "Account has no password stored for browser login"
            attempts.append(attempt)
            continue
        try:
            result = await run(account, prompts, headless=headless)
        except BrowserLoginError as e:
            if e.reason in _ABORT_REASONS:
                attempt["reason"] = e.reason
                attempt["detail"] = e.detail
                attempts.append(attempt)
                _record_attempts(task, attempts)
                task.status = FlowTaskStatus.FAILED
                task.error_message = f"Google unreachable from the browser: {e.detail}"
                await db.commit()
                raise BrowserUnreachable(attempts, str(e))
            attempt["reason"] = e.reason
            attempt["detail"] = e.detail
            attempts.append(attempt)
            continue
        attempt["outcome"] = "ok"
        attempt["reason"] = "submitted"
        attempt["detail"] = result.get("detail", "")
        attempt["flow_url"] = result.get("flow_url", "")
        attempts.append(attempt)
        _record_attempts(task, attempts)
        task.google_account_id = account.id
        task.status = FlowTaskStatus.IN_PROGRESS
        task.flow_url = result.get("flow_url") or task.flow_url
        task.error_message = None
        account.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(task)
        return task

    _record_attempts(task, attempts)
    task.status = FlowTaskStatus.FAILED
    task.error_message = _failure_message(attempts)
    await db.commit()
    raise AllBrowserAccountsFailed(attempts)

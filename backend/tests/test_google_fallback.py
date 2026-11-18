"""Tests for Flow Bridge Google-account fallback.

Google is never contacted: verify_access_token / refresh_access_token are
stubbed on app.services.flow_account_fallback, keyed by the plaintext
token stored on each account. That is the seam the service exposes
exactly so tests can simulate quota (429), invalid tokens and dead
refresh tokens without network access.
"""
import json
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta

from test_new_routers import get_auth_headers, create_project
from app.services.google_account_service import GoogleAccountError
from app.core.security import encrypt_data


async def _create_google_account(async_client, headers, email, access_token,
                                 refresh_token="rt-1", token_expiry=None):
    """Create a Google account via the API (tokens encrypted at rest)."""
    body = {
        "email": email,
        "display_name": email.split("@")[0],
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    if token_expiry is not None:
        body["token_expiry"] = token_expiry.isoformat()
    response = await async_client.post("/api/google-accounts", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_flow_task(async_client, headers, project_id, google_account_id=None):
    body = {
        "project_id": project_id,
        "task_type": "video_generation",
        "title": "Fallback test task",
        "input_prompts": "[]",
        "reference_assets": "[]",
    }
    if google_account_id:
        body["google_account_id"] = google_account_id
    response = await async_client.post("/api/flow", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _get_flow_task(async_client, headers, project_id, task_id):
    response = await async_client.get(f"/api/flow/{project_id}/{task_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _verify_stub_factory(failures):
    """verify_access_token fake: token -> GoogleAccountError reason (or ok)."""
    async def fake_verify(access_token: str) -> None:
        reason = failures.get(access_token)
        if reason == "quota_exceeded":
            raise GoogleAccountError("quota_exceeded", "Google rate limit (429)")
        if reason == "token_invalid":
            raise GoogleAccountError("token_invalid", "Token rejected by Google (401)")
        if reason == "unreachable":
            raise GoogleAccountError("unreachable", "Could not reach Google")
        return None
    return fake_verify


def _refresh_stub_factory(behaviour):
    """refresh_access_token fake: refresh_token -> new access token or error.

    behaviour: {refresh_token: new_access_token | "refresh_failed"}.
    Mutates the account like the real refresh (new encrypted token + expiry).
    """
    async def fake_refresh(db, account) -> None:
        from app.core.security import decrypt_data
        rt = decrypt_data(account.refresh_token_encrypted)
        outcome = behaviour.get(rt, "refresh_failed")
        if outcome == "refresh_failed":
            raise GoogleAccountError("refresh_failed", "Token refresh failed")
        account.access_token_encrypted = encrypt_data(outcome)
        account.token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        account.last_verified_at = datetime.now(timezone.utc)
    return fake_refresh


@pytest.mark.anyio
class TestGoogleAccountFallback:
    async def test_execute_falls_back_to_second_account(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Account 1 quota-exhausted (429) -> account 2 used, history recorded."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-quota")
        acc2 = await _create_google_account(
            async_client, headers, "two@example.com", "tok-ok")
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({"tok-quota": "quota_exceeded"}),
        )

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ready_for_flow"
        assert data["google_account_id"] == acc2
        assert data["error_message"] is None

        history = json.loads(data["fallback_history"])
        assert [h["email"] for h in history] == ["one@example.com", "two@example.com"]
        assert history[0]["outcome"] == "failed"
        assert history[0]["reason"] == "quota_exceeded"
        assert history[1]["outcome"] == "ok"

    async def test_execute_all_accounts_fail_honest_error(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Every account fails -> 502, task FAILED, error lists each account."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-quota")
        acc2 = await _create_google_account(
            async_client, headers, "two@example.com", "tok-bad")
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({
                "tok-quota": "quota_exceeded",
                "tok-bad": "token_invalid",
            }),
        )

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 502, response.text
        assert "one@example.com" in response.json()["detail"]
        assert "two@example.com" in response.json()["detail"]

        task = await _get_flow_task(async_client, headers, project_id, task_id)
        assert task["status"] == "failed"
        assert "one@example.com" in task["error_message"]
        assert "quota_exceeded" in task["error_message"]
        assert "two@example.com" in task["error_message"]
        history = json.loads(task["fallback_history"])
        assert len(history) == 2
        assert all(h["outcome"] == "failed" for h in history)

    async def test_retry_after_failure_succeeds(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Failed task -> fix account 2 -> manual retry succeeds."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-quota")
        acc2 = await _create_google_account(
            async_client, headers, "two@example.com", "tok-bad")
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({
                "tok-quota": "quota_exceeded",
                "tok-bad": "token_invalid",
            }),
        )
        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 502

        # Account 2's token is fixed (in reality: user re-auths / quota resets).
        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({"tok-quota": "quota_exceeded"}),
        )
        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/retry", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ready_for_flow"
        assert data["google_account_id"] == acc2
        assert data["error_message"] is None

    async def test_execute_no_accounts(self, async_client: AsyncClient):
        """User with no Google accounts -> 502 + honest FAILED state."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        task_id = await _create_flow_task(async_client, headers, project_id)

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 502, response.text
        task = await _get_flow_task(async_client, headers, project_id, task_id)
        assert task["status"] == "failed"
        assert "No enabled Google accounts" in task["error_message"]

    async def test_execute_refreshes_expired_token(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Expired token + working refresh -> same account used, no fallback."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-old",
            refresh_token="rt-good", token_expiry=past)
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.refresh_access_token",
            _refresh_stub_factory({"rt-good": "tok-ok"}),
        )
        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({}),
        )

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ready_for_flow"
        assert data["google_account_id"] == acc1
        history = json.loads(data["fallback_history"])
        assert len(history) == 1 and history[0]["outcome"] == "ok"

    async def test_execute_refresh_failure_falls_back(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Expired token + dead refresh -> next account tried and used."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-old",
            refresh_token="rt-dead", token_expiry=past)
        acc2 = await _create_google_account(
            async_client, headers, "two@example.com", "tok-ok")
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.refresh_access_token",
            _refresh_stub_factory({"rt-dead": "refresh_failed"}),
        )
        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({}),
        )

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["google_account_id"] == acc2
        history = json.loads(data["fallback_history"])
        assert history[0]["reason"] == "refresh_failed"
        assert history[1]["outcome"] == "ok"

    async def test_execute_skips_disabled_account(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Disabled account is never tried; pinned account is tried first."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-ok")
        acc2 = await _create_google_account(
            async_client, headers, "two@example.com", "tok-ok")
        # Disable account 1, pin the task to account 2 (higher index).
        response = await async_client.patch(
            f"/api/google-accounts/{acc1}", json={"is_active": False}, headers=headers)
        assert response.status_code == 200, response.text
        task_id = await _create_flow_task(async_client, headers, project_id, acc2)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({}),
        )

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["google_account_id"] == acc2
        history = json.loads(data["fallback_history"])
        assert [h["email"] for h in history] == ["two@example.com"]

    async def test_execute_without_pinned_account_picks_first_working(
        self, async_client: AsyncClient, monkeypatch
    ):
        """No pinned account -> accounts tried in account_index order."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-quota")
        acc2 = await _create_google_account(
            async_client, headers, "two@example.com", "tok-ok")
        task_id = await _create_flow_task(async_client, headers, project_id)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({"tok-quota": "quota_exceeded"}),
        )

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["google_account_id"] == acc2

    async def test_execute_rejects_completed_task(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Completed tasks are never re-bound to another account."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-ok")
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)
        response = await async_client.patch(
            f"/api/flow/{project_id}/{task_id}",
            json={"status": "completed"}, headers=headers)
        assert response.status_code == 200, response.text

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 400, response.text

    async def test_retry_rejects_completed_task(
        self, async_client: AsyncClient
    ):
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        task_id = await _create_flow_task(async_client, headers, project_id)
        response = await async_client.patch(
            f"/api/flow/{project_id}/{task_id}",
            json={"status": "completed"}, headers=headers)
        assert response.status_code == 200, response.text

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/retry", headers=headers)
        assert response.status_code == 400, response.text

    async def test_unreachable_google_aborts_run(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Network failure -> run aborts (no pointless per-account retries)."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_google_account(
            async_client, headers, "one@example.com", "tok-ok")
        acc2 = await _create_google_account(
            async_client, headers, "two@example.com", "tok-ok")
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)

        monkeypatch.setattr(
            "app.services.flow_account_fallback.verify_access_token",
            _verify_stub_factory({"tok-ok": "unreachable"}),
        )

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute", headers=headers)
        assert response.status_code == 502, response.text
        task = await _get_flow_task(async_client, headers, project_id, task_id)
        assert task["status"] == "failed"
        assert "unreachable" in task["error_message"].lower()
        history = json.loads(task["fallback_history"])
        # Aborted after the first account — account 2 was never tried.
        assert len(history) == 1

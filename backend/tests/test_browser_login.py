"""Tests for browser-based Google login + automatic Flow execution.

Two layers:
1. Orchestration (mocked browser runner): account switching, honest
   failure, no-password skip — Google is never contacted.
2. Real Playwright mechanics (no Google): persistent-profile cookie
   survival across launches, and the real login_google_account() flow
   against a local fake Google sign-in page (correct + wrong password).

No test touches Google Cloud Console credentials: the browser path never
calls get_google_oauth_credentials — one test patches it to explode if
anything on this path dares to.
"""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from httpx import AsyncClient

from test_google_fallback import _create_flow_task, _get_flow_task
from test_new_routers import get_auth_headers, create_project
from app.models.google_account import GoogleAccount
from app.services.browser_login import (
    BrowserLoginError,
    _launch_context,
    login_google_account,
    read_session_status,
    save_session_status,
)


async def _create_account(async_client, headers, email, password=None,
                          access_token="tok-ok"):
    """Create a Google account via the API (password encrypted at rest)."""
    body = {
        "email": email,
        "display_name": email.split("@")[0],
        "access_token": access_token,
        "refresh_token": "rt-1",
    }
    if password is not None:
        body["password"] = password
    response = await async_client.post("/api/google-accounts", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_task_with_prompt(async_client, headers, project_id,
                                   google_account_id=None):
    body = {
        "project_id": project_id,
        "task_type": "video_generation",
        "title": "Browser execution test task",
        "input_prompts": json.dumps(["A dramatic close-up, candlelight, 4 seconds"]),
        "reference_assets": "[]",
    }
    if google_account_id:
        body["google_account_id"] = google_account_id
    response = await async_client.post("/api/flow", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _runner_factory(behaviour):
    """Fake browser runner: email -> 'ok' or a BrowserLoginError reason."""
    async def fake_runner(account, prompts, headless=True):
        outcome = behaviour.get(account.email, "ok")
        if outcome == "ok":
            assert prompts, "runner received no prompts"
            return {
                "status": "submitted",
                "flow_url": "https://flow.google.com/project/fake",
                "detail": "Prompt submitted (fake runner)",
            }
        raise BrowserLoginError(outcome, f"simulated {outcome}")
    return fake_runner


@pytest.mark.anyio
class TestBrowserExecutionFallback:
    async def test_execute_browser_falls_back_to_second_account(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Account 1 login rejected -> account 2 runs Flow, history recorded."""
        async def _boom(*args, **kwargs):
            raise AssertionError("browser path must not touch OAuth credentials")
        monkeypatch.setattr(
            "app.services.google_account_service.get_google_oauth_credentials",
            _boom,
        )
        monkeypatch.setattr(
            "app.services.flow_browser_execution.default_browser_runner",
            _runner_factory({"one@example.com": "login_failed"}),
        )
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_account(
            async_client, headers, "one@example.com", password="pw-1")
        acc2 = await _create_account(
            async_client, headers, "two@example.com", password="pw-2")
        task_id = await _create_task_with_prompt(
            async_client, headers, project_id, acc1)

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute-browser", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["google_account_id"] == acc2
        assert data["error_message"] is None
        assert data["flow_url"] == "https://flow.google.com/project/fake"

        history = json.loads(data["fallback_history"])
        assert [h["email"] for h in history] == ["one@example.com", "two@example.com"]
        assert all(h["mode"] == "browser" for h in history)
        assert history[0]["outcome"] == "failed"
        assert history[0]["reason"] == "login_failed"
        assert history[1]["outcome"] == "ok"
        assert history[1]["reason"] == "submitted"

    async def test_execute_browser_all_accounts_fail_honest_error(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Every account fails -> 502, task FAILED, manual export still named."""
        monkeypatch.setattr(
            "app.services.flow_browser_execution.default_browser_runner",
            _runner_factory({
                "one@example.com": "login_failed",
                "two@example.com": "captcha_or_2fa",
            }),
        )
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_account(
            async_client, headers, "one@example.com", password="pw-1")
        acc2 = await _create_account(
            async_client, headers, "two@example.com", password="pw-2")
        task_id = await _create_task_with_prompt(
            async_client, headers, project_id, acc1)

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute-browser", headers=headers)
        assert response.status_code == 502, response.text
        assert "one@example.com" in response.json()["detail"]
        assert "two@example.com" in response.json()["detail"]

        task = await _get_flow_task(async_client, headers, project_id, task_id)
        assert task["status"] == "failed"
        assert "one@example.com" in task["error_message"]
        assert "login_failed" in task["error_message"]
        assert "captcha_or_2fa" in task["error_message"]
        assert "manual export" in task["error_message"].lower()
        history = json.loads(task["fallback_history"])
        assert len(history) == 2
        assert all(h["outcome"] == "failed" for h in history)

    async def test_execute_browser_skips_account_without_password(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Account without a stored password is skipped (no_password), not tried."""
        monkeypatch.setattr(
            "app.services.flow_browser_execution.default_browser_runner",
            _runner_factory({}),
        )
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_account(async_client, headers, "one@example.com")
        acc2 = await _create_account(
            async_client, headers, "two@example.com", password="pw-2")
        task_id = await _create_task_with_prompt(
            async_client, headers, project_id, acc1)

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute-browser", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["google_account_id"] == acc2
        history = json.loads(data["fallback_history"])
        assert history[0]["reason"] == "no_password"
        assert history[1]["outcome"] == "ok"

    async def test_execute_browser_no_prompts_is_client_error(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Task with no prompts -> 400, task FAILED, no account was tried."""
        monkeypatch.setattr(
            "app.services.flow_browser_execution.default_browser_runner",
            _runner_factory({}),
        )
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_account(
            async_client, headers, "one@example.com", password="pw-1")
        task_id = await _create_flow_task(async_client, headers, project_id, acc1)

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute-browser", headers=headers)
        assert response.status_code == 400, response.text
        task = await _get_flow_task(async_client, headers, project_id, task_id)
        assert task["status"] == "failed"
        assert "no prompts" in task["error_message"].lower()

    async def test_execute_browser_unreachable_aborts_run(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Google unreachable from the browser -> abort after first account."""
        monkeypatch.setattr(
            "app.services.flow_browser_execution.default_browser_runner",
            _runner_factory({"one@example.com": "unreachable"}),
        )
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_account(
            async_client, headers, "one@example.com", password="pw-1")
        acc2 = await _create_account(
            async_client, headers, "two@example.com", password="pw-2")
        task_id = await _create_task_with_prompt(
            async_client, headers, project_id, acc1)

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute-browser", headers=headers)
        assert response.status_code == 502, response.text
        task = await _get_flow_task(async_client, headers, project_id, task_id)
        assert task["status"] == "failed"
        assert "unreachable" in task["error_message"].lower()
        history = json.loads(task["fallback_history"])
        assert len(history) == 1  # account 2 was never tried

    async def test_execute_browser_rejects_completed_task(
        self, async_client: AsyncClient
    ):
        """Completed tasks are never re-run in the browser."""
        headers = await get_auth_headers(async_client)
        project_id = await create_project(async_client, headers)
        acc1 = await _create_account(
            async_client, headers, "one@example.com", password="pw-1")
        task_id = await _create_task_with_prompt(
            async_client, headers, project_id, acc1)
        response = await async_client.patch(
            f"/api/flow/{project_id}/{task_id}",
            json={"status": "completed"}, headers=headers)
        assert response.status_code == 200, response.text

        response = await async_client.post(
            f"/api/flow/{project_id}/{task_id}/execute-browser", headers=headers)
        assert response.status_code == 400, response.text


@pytest.mark.anyio
class TestBrowserLoginEndpoints:
    async def test_browser_login_endpoint_mocked(
        self, async_client: AsyncClient, monkeypatch
    ):
        """POST /browser-login with a stubbed login fn returns saved status."""
        async def fake_login(account, headless=True):
            from app.services.browser_login import save_session_status
            return save_session_status(
                account.user_id, account.id, "logged_in", "Signed in (fake)")
        monkeypatch.setattr(
            "app.api.google_accounts.browser_login_service.login_google_account",
            fake_login,
        )
        headers = await get_auth_headers(async_client)
        acc1 = await _create_account(
            async_client, headers, "one@example.com", password="pw-1")

        response = await async_client.post(
            f"/api/google-accounts/{acc1}/browser-login", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert data["session_saved"] is True
        assert data["email"] == "one@example.com"

    async def test_browser_session_endpoint_no_session_then_saved(
        self, async_client: AsyncClient, monkeypatch, tmp_path
    ):
        """GET /browser-session: false before login, real record after save."""
        monkeypatch.setenv("BROWSER_PROFILES_DIR", str(tmp_path))
        headers = await get_auth_headers(async_client)
        acc1 = await _create_account(
            async_client, headers, "one@example.com", password="pw-1")

        response = await async_client.get(
            f"/api/google-accounts/{acc1}/browser-session", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["has_session"] is False

        # The endpoint reads the same session file the login writes; the
        # user id is hidden behind auth, so round-trip the storage helper
        # directly (same code path, same file layout):
        user_id = uuid.uuid4()
        record = save_session_status(
            user_id, uuid.UUID(acc1), "logged_in", "Signed in (test)")
        assert read_session_status(user_id, uuid.UUID(acc1))["status"] == "logged_in"
        assert "password" not in json.dumps(record)
        assert "pw-1" not in json.dumps(record)

    async def test_browser_login_without_password_is_400(
        self, async_client: AsyncClient
    ):
        headers = await get_auth_headers(async_client)
        acc1 = await _create_account(async_client, headers, "one@example.com")

        response = await async_client.post(
            f"/api/google-accounts/{acc1}/browser-login", headers=headers)
        assert response.status_code == 400, response.text


# --- Real Playwright mechanics (local only, no Google) ---------------------

_FAKE_LOGIN_HTML = """<!doctype html><html><body>
<div id="email-step">
  <input id="identifierId" type="email">
  <button id="identifierNext">Next</button>
</div>
<div id="password-step" style="display:none">
  <input type="password" name="password">
  <button id="passwordNext">Next</button>
  <div id="wrong" style="display:none">Wrong password. Try again</div>
</div>
<script>
document.getElementById('identifierNext').onclick = () => {
  document.getElementById('email-step').style.display = 'none';
  document.getElementById('password-step').style.display = 'block';
};
document.getElementById('passwordNext').onclick = () => {
  const pw = document.querySelector('input[type="password"]').value;
  if (pw === 'pw-benar') { window.location = '/welcome'; }
  else { document.getElementById('wrong').style.display = 'block'; }
};
</script></body></html>"""

_WELCOME_HTML = "<!doctype html><html><body>Welcome, test user</body></html>"


class _FakeGoogleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/signin"):
            body = _FAKE_LOGIN_HTML.encode()
        elif self.path.startswith("/welcome"):
            body = _WELCOME_HTML.encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def fake_google_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeGoogleHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _fake_account(email, password):
    account = GoogleAccount(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        email=email,
        account_index=0,
    )
    account.set_password(password)
    return account


@pytest.mark.anyio
class TestRealBrowserMechanics:
    async def test_persistent_profile_keeps_cookies(
        self, tmp_path, monkeypatch, fake_google_server
    ):
        """A cookie set inside a persistent profile survives relaunch."""
        monkeypatch.setenv("BROWSER_PROFILES_DIR", str(tmp_path))
        user_id, account_id = uuid.uuid4(), uuid.uuid4()
        playwright, context = await _launch_context(user_id, account_id, True)
        page = await context.new_page()
        await page.goto(f"{fake_google_server}/welcome")
        # Persistent cookie (max-age): a session cookie (no expiry) is
        # deliberately NOT written to disk by Chromium — same as a real
        # Google auth cookie, which always carries an expiry.
        await page.evaluate("document.cookie = 'probe=1; path=/; max-age=3600'")
        await context.close()
        await playwright.stop()

        playwright, context = await _launch_context(user_id, account_id, True)
        page = await context.new_page()
        await page.goto(f"{fake_google_server}/welcome")
        cookie = await page.evaluate("document.cookie")
        await context.close()
        await playwright.stop()
        assert "probe=1" in cookie

    async def test_profiles_are_separate_per_account(
        self, tmp_path, monkeypatch, fake_google_server
    ):
        """Two accounts get two profile dirs (no shared cookies)."""
        monkeypatch.setenv("BROWSER_PROFILES_DIR", str(tmp_path))
        user_id = uuid.uuid4()
        playwright, ctx1 = await _launch_context(user_id, uuid.uuid4(), True)
        page = await ctx1.new_page()
        await page.goto(f"{fake_google_server}/welcome")
        await page.evaluate("document.cookie = 'probe=a; path=/; max-age=3600'")
        await ctx1.close()
        await playwright.stop()
        playwright, ctx2 = await _launch_context(user_id, uuid.uuid4(), True)
        page = await ctx2.new_page()
        await page.goto(f"{fake_google_server}/welcome")
        cookie = await page.evaluate("document.cookie")
        await ctx2.close()
        await playwright.stop()
        assert "probe=a" not in cookie

    async def test_real_login_against_fake_google_page(
        self, tmp_path, monkeypatch, fake_google_server
    ):
        """Real login_google_account() vs a local fake sign-in page."""
        monkeypatch.setenv("BROWSER_PROFILES_DIR", str(tmp_path))
        account = _fake_account("fake@example.com", "pw-benar")
        record = await login_google_account(
            account, headless=True,
            login_url=f"{fake_google_server}/signin/v2/identifier",
        )
        assert record["status"] == "logged_in"
        saved = read_session_status(account.user_id, account.id)
        assert saved is not None and saved["status"] == "logged_in"
        assert "pw-benar" not in json.dumps(saved)

    async def test_real_login_wrong_password(
        self, tmp_path, monkeypatch, fake_google_server
    ):
        """Wrong password on the fake page -> login_failed, honestly."""
        monkeypatch.setenv("BROWSER_PROFILES_DIR", str(tmp_path))
        account = _fake_account("fake@example.com", "pw-salah")
        with pytest.raises(BrowserLoginError) as excinfo:
            await login_google_account(
                account, headless=True,
                login_url=f"{fake_google_server}/signin/v2/identifier",
            )
        assert excinfo.value.reason == "login_failed"
        saved = read_session_status(account.user_id, account.id)
        assert saved is not None and saved["status"] == "login_failed"

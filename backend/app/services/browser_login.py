"""Browser-based Google login + Google Flow execution (Playwright).

This is the "login biasa dengan browser masing-masing" path (Di, 17 Nov
22:22 WIB): NO Google Cloud Console is involved — no client_id / secret,
no OAuth code exchange. The browser signs in to Google with the account's
email + password (read ENCRYPTED from the DB, same as everywhere else)
and keeps a persistent browser profile per account, so the session
(cookie) survives across runs.

Honest limits (see BROWSER-LOGIN-REPORT.md):
- Google may block automated sign-in (bot detection / captcha / 2FA).
  When that happens the login raises BrowserLoginError("captcha_or_2fa")
  and the caller falls through to the next account; the user can still
  sign in manually in their own browser and use the manual export path.
- The Flow web UI (flow.google.com) has no public API and its DOM was
  never verified against the real site from this VM (no real Google
  account available for testing here). execute_flow_prompt() is a
  best-effort submission with generic selectors; when the page does not
  match it raises BrowserLoginError("flow_blocked") instead of pretending
  the generation ran, and the manual export path still works.
- Playwright imports are lazy (inside the functions) so importing this
  module never requires the browser to be installed; only launching does.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

GOOGLE_LOGIN_URL = "https://accounts.google.com/signin/v2/identifier"
GOOGLE_ACCOUNT_URL = "https://myaccount.google.com/"
FLOW_URL = "https://flow.google.com/"

# Texts Google shows when it wants a human (captcha / 2FA / bot check).
_CHALLENGE_MARKERS = (
    "Verify it's you",
    "2-Step Verification",
    "unusual traffic",
    "Try again later",
    "This device isn't recognized",
    "reCAPTCHA",
    "captcha",
)
_WRONG_PASSWORD_MARKERS = (
    "Wrong password",
    "Incorrect password",
    "Wrong password. Try again",
)
# Texts Flow shows when the account cannot generate right now.
_QUOTA_MARKERS = (
    "out of credits",
    "You've run out of",
    "quota",
    "Try again tomorrow",
)


class BrowserLoginError(Exception):
    """One browser step failed for one Google account.

    reason is a machine-readable code recorded in the Flow task's
    fallback_history:
      - no_password: account has no password stored (browser login needs it)
      - login_failed: Google rejected the email/password
      - captcha_or_2fa: Google asked for a human (captcha / 2FA / bot check)
      - session_expired: saved session is dead and re-login did not fix it
      - quota_exceeded: Flow says this account is out of credits/quota
      - flow_blocked: Flow page did not accept the prompt (UI not
        recognised, or Google blocked the automation)
      - unreachable: Google could not be reached at all (network/proxy)
      - browser_unavailable: Playwright/Chromium is not installed or
        cannot launch on this machine
    """

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail or reason


def get_profiles_root() -> Path:
    """Root dir for persistent browser profiles.

    Override with BROWSER_PROFILES_DIR. Default is backend/data/ so
    profiles live next to the app, not in /tmp (VM swaps wipe /tmp).
    """
    env = os.getenv("BROWSER_PROFILES_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "data" / "browser_profiles"


def profile_dir(user_id, account_id) -> Path:
    """Persistent Chromium profile dir for one (user, account) pair.

    One profile per account = one Google session per account, exactly
    like "browser masing-masing" — accounts never share cookies.
    """
    return get_profiles_root() / f"user_{user_id}" / f"account_{account_id}"


def _session_file(user_id, account_id) -> Path:
    return profile_dir(user_id, account_id) / "session.json"


def read_session_status(user_id, account_id) -> dict | None:
    """Stored browser-session metadata for an account (no secrets)."""
    path = _session_file(user_id, account_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save_session_status(user_id, account_id, status: str, detail: str = "") -> dict:
    """Persist browser-session metadata (status only — never secrets)."""
    directory = profile_dir(user_id, account_id)
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "account_id": str(account_id),
        "user_id": str(user_id),
        "status": status,  # logged_in | login_failed | captcha_or_2fa | ...
        "detail": detail,
        "mode": "browser",
        "last_login_at": datetime.now(timezone.utc).isoformat(),
    }
    _session_file(user_id, account_id).write_text(json.dumps(record))
    return record


def clear_session(user_id, account_id) -> None:
    """Delete a stored browser profile (cookies + session metadata)."""
    import shutil

    directory = profile_dir(user_id, account_id)
    if directory.exists():
        shutil.rmtree(directory)


def _is_challenge_page(url: str, content: str) -> bool:
    if "accounts.google.com/signin/v2/challenge" in url:
        return True
    lowered = content.lower()
    return any(m.lower() in lowered for m in _CHALLENGE_MARKERS)


def _login_outcome(url: str, content: str) -> str:
    """Classify a page during/after Google sign-in.

    Returns: logged_in | challenge | wrong_password | still_signin | unknown
    """
    if _is_challenge_page(url, content):
        return "challenge"
    if any(m in content for m in _WRONG_PASSWORD_MARKERS):
        return "wrong_password"
    if "myaccount.google.com" in url:
        return "logged_in"
    # Left accounts.google.com entirely without a challenge = signed in
    # (e.g. redirected to myaccount, Flow, or an account chooser).
    if "accounts.google.com" not in url and "signin" not in url:
        return "logged_in"
    if "accounts.google.com/signin" in url:
        return "still_signin"
    return "unknown"


async def _launch_context(user_id, account_id, headless: bool):
    """Launch a persistent Chromium context for one account.

    Raises BrowserLoginError("browser_unavailable") when Playwright or
    Chromium is missing / cannot start.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise BrowserLoginError(
            "browser_unavailable", f"Playwright is not installed: {e}"
        )
    directory = profile_dir(user_id, account_id)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        playwright = await async_playwright().start()
    except Exception as e:  # noqa: BLE001 - launch failure is environmental
        raise BrowserLoginError("browser_unavailable", f"Could not start Playwright: {e}")
    try:
        context = await playwright.chromium.launch_persistent_context(
            str(directory),
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            viewport={"width": 1280, "height": 800},
        )
    except Exception as e:  # noqa: BLE001 - launch failure is environmental
        await playwright.stop()
        raise BrowserLoginError(
            "browser_unavailable", f"Could not launch Chromium: {e}"
        )
    return playwright, context


async def login_google_account(account, headless: bool = True,
                              login_url: str | None = None) -> dict:
    """Sign in to Google in the account's own persistent browser profile.

    `account` is a GoogleAccount row; its password is read ENCRYPTED from
    the DB via account.get_password() — never from an HTTP endpoint and
    never written anywhere (not even the session file). `login_url` exists
    only so tests can point at a local fake sign-in page; production
    always uses GOOGLE_LOGIN_URL.

    Returns {"status": "logged_in"|"already_logged_in", "detail": ...}.
    Raises BrowserLoginError on every failure mode.
    """
    password = account.get_password()
    if not password:
        raise BrowserLoginError(
            "no_password",
            "Account has no password stored — browser login needs email + password",
        )
    playwright, context = await _launch_context(
        account.user_id, account.id, headless
    )
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.goto(
                login_url or GOOGLE_LOGIN_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )
        except Exception as e:  # noqa: BLE001 - network errors are expected
            if "net::" in str(e) or "ERR_" in str(e) or "Timeout" in str(e):
                raise BrowserLoginError("unreachable", f"Could not reach Google: {e}")
            raise

        # Already signed in? The profile's cookies may still be valid.
        outcome = _login_outcome(page.url, await page.content())
        if outcome == "logged_in":
            return save_session_status(
                account.user_id, account.id, "logged_in",
                "Already signed in (saved session still valid)",
            ) | {"status": "already_logged_in"}
        if outcome == "challenge":
            save_session_status(account.user_id, account.id, "captcha_or_2fa",
                                "Google asked for human verification")
            raise BrowserLoginError(
                "captcha_or_2fa",
                "Google asked for human verification (captcha/2FA) — sign in "
                "manually in your own browser instead",
            )

        # Step 1: email.
        try:
            await page.fill("#identifierId", account.email, timeout=15000)
            await page.click("#identifierNext", timeout=15000)
        except Exception as e:  # noqa: BLE001 - selector miss = page changed
            raise BrowserLoginError(
                "flow_blocked",
                f"Google sign-in page did not match expected layout: {e}",
            )
        await page.wait_for_timeout(1500)

        # Step 2: password.
        try:
            await page.fill('input[type="password"]', password, timeout=15000)
            await page.click("#passwordNext", timeout=15000)
        except Exception as e:  # noqa: BLE001 - selector miss = page changed
            raise BrowserLoginError(
                "flow_blocked",
                f"Google password page did not match expected layout: {e}",
            )
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:  # noqa: BLE001 - still classify from current page
            pass
        await page.wait_for_timeout(1500)

        outcome = _login_outcome(page.url, await page.content())
        if outcome == "logged_in":
            record = save_session_status(
                account.user_id, account.id, "logged_in",
                "Signed in via browser",
            )
            return record | {"status": "logged_in"}
        if outcome == "challenge":
            save_session_status(account.user_id, account.id, "captcha_or_2fa",
                                "Google asked for human verification after login")
            raise BrowserLoginError(
                "captcha_or_2fa",
                "Google asked for human verification (captcha/2FA) after "
                "sign-in — sign in manually in your own browser instead",
            )
        if outcome == "wrong_password":
            save_session_status(account.user_id, account.id, "login_failed",
                                "Google rejected the password")
            raise BrowserLoginError(
                "login_failed", "Google rejected the password for this account"
            )
        save_session_status(account.user_id, account.id, "login_failed",
                            f"Unexpected sign-in outcome: {outcome}")
        raise BrowserLoginError(
            "login_failed",
            f"Google sign-in ended in an unexpected state ({outcome}) — "
            "the account may need manual sign-in",
        )
    finally:
        await context.close()
        await playwright.stop()


async def is_session_alive(user_id, account_id, headless: bool = True) -> bool:
    """True when the saved browser session still signs in to Google.

    Opens the account's profile, visits myaccount.google.com, and checks
    Google does NOT bounce back to the sign-in page.
    """
    playwright, context = await _launch_context(user_id, account_id, headless)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.goto(
                GOOGLE_ACCOUNT_URL, wait_until="domcontentloaded", timeout=60000
            )
        except Exception as e:  # noqa: BLE001 - network errors are expected
            if "net::" in str(e) or "ERR_" in str(e):
                raise BrowserLoginError("unreachable", f"Could not reach Google: {e}")
            raise
        return "accounts.google.com/signin" not in page.url
    finally:
        await context.close()
        await playwright.stop()


async def execute_flow_prompt(account, prompt: str, headless: bool = True,
                             flow_url: str | None = None) -> dict:
    """Submit one prompt to Google Flow in the account's browser session.

    Ensures the session first (re-login when dead), opens Flow, fills the
    prompt box and submits. Returns {"status": "submitted",
    "flow_url": <current Flow URL>, "detail": ...}.

    "submitted" means the prompt reached Flow's input — it is NOT a
    guarantee the video was generated; the result is imported later via
    the /import endpoint, same as the manual path. Anything Flow or
    Google refuses raises BrowserLoginError (quota / blocked / challenge)
    so the caller can switch accounts or fall back to manual export.
    """
    if not prompt or not prompt.strip():
        raise BrowserLoginError("no_prompt", "Flow task has no prompt to run")
    playwright, context = await _launch_context(
        account.user_id, account.id, headless
    )
    try:
        page = context.pages[0] if context.pages else await context.new_page()

        async def _goto_flow() -> None:
            try:
                await page.goto(
                    flow_url or FLOW_URL,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
            except Exception as e:  # noqa: BLE001 - network errors expected
                if "net::" in str(e) or "ERR_" in str(e) or "Timeout" in str(e):
                    raise BrowserLoginError(
                        "unreachable", f"Could not reach Google Flow: {e}"
                    )
                raise

        await _goto_flow()
        # Bounced to Google sign-in: session is dead — log in once, retry.
        if "accounts.google.com" in page.url:
            await context.close()
            await playwright.stop()
            await login_google_account(account, headless=headless)
            playwright, context = await _launch_context(
                account.user_id, account.id, headless
            )
            page = context.pages[0] if context.pages else await context.new_page()
            await _goto_flow()
            if "accounts.google.com" in page.url:
                raise BrowserLoginError(
                    "session_expired",
                    "Browser session expired and re-login did not stick",
                )

        content = await page.content()
        if _is_challenge_page(page.url, content):
            raise BrowserLoginError(
                "captcha_or_2fa",
                "Google Flow asked for human verification (captcha/bot check)",
            )
        lowered = content.lower()
        if any(m.lower() in lowered for m in _QUOTA_MARKERS):
            raise BrowserLoginError(
                "quota_exceeded",
                "Flow reports this account is out of credits/quota",
            )

        # Best-effort prompt submission. Flow has no public API and its
        # DOM was never verified against the real site from this VM, so
        # a miss here is reported honestly as flow_blocked, never faked.
        submitted = False
        for selector in (
            'textarea[placeholder*="prompt" i]',
            'textarea[placeholder*="describe" i]',
            "textarea",
            '[contenteditable="true"]',
        ):
            try:
                locator = page.locator(selector).first
                await locator.wait_for(state="visible", timeout=8000)
                await locator.click(timeout=5000)
                await locator.fill(prompt, timeout=10000)
                await page.keyboard.press("Enter")
                submitted = True
                break
            except Exception:  # noqa: BLE001 - try the next selector
                continue
        if not submitted:
            raise BrowserLoginError(
                "flow_blocked",
                "Flow page did not show a prompt input (UI not recognised) — "
                "use manual export instead",
            )
        await page.wait_for_timeout(5000)
        content = await page.content()
        if _is_challenge_page(page.url, content):
            raise BrowserLoginError(
                "captcha_or_2fa",
                "Google Flow asked for human verification after submitting",
            )
        if any(m.lower() in content.lower() for m in _QUOTA_MARKERS):
            raise BrowserLoginError(
                "quota_exceeded",
                "Flow reports this account is out of credits/quota",
            )
        return {
            "status": "submitted",
            "flow_url": page.url,
            "detail": "Prompt submitted to Google Flow via browser session; "
                      "generation result must be imported via /import",
        }
    finally:
        await context.close()
        await playwright.stop()

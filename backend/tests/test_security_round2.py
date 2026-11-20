"""Security hardening tests (future-dev round 2, item 3).

Covers: startup secret validation, rate limiting on auth endpoints,
token revocation / logout, security headers, and the Fernet key fix
(a real Fernet ENCRYPTION_KEY is used verbatim, not mangled).
"""
import secrets

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from jose import jwt

import app.core.security as security_mod
from app.core.config import settings
from app.core.middleware import rate_limiter
from app.core.secrets import is_valid_fernet_key, validate_secrets
from app.core.config import Settings

TEST_PASSWORD = "testpass123"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


async def _register_and_login(async_client: AsyncClient, email: str, username: str):
    await async_client.post("/api/auth/register", json={
        "email": email, "username": username, "password": TEST_PASSWORD,
    })
    res = await async_client.post("/api/auth/login", json={
        "email": email, "password": TEST_PASSWORD,
    })
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------- secrets

@pytest.mark.anyio
async def test_production_refuses_short_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_secrets(Settings(SECRET_KEY="short", ENVIRONMENT="production"))


@pytest.mark.anyio
async def test_production_refuses_placeholder_secret_key():
    with pytest.raises(RuntimeError, match="placeholder"):
        validate_secrets(Settings(
            SECRET_KEY="your-secret-key-change-in-production",
            ENVIRONMENT="production",
        ))


@pytest.mark.anyio
async def test_production_requires_fernet_encryption_key():
    # Strong SECRET_KEY but no ENCRYPTION_KEY -> still refuses.
    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
        validate_secrets(Settings(
            SECRET_KEY=secrets.token_urlsafe(32),
            ENCRYPTION_KEY=None,
            ENVIRONMENT="production",
        ))
    # Arbitrary string (not a Fernet key) -> refuses.
    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
        validate_secrets(Settings(
            SECRET_KEY=secrets.token_urlsafe(32),
            ENCRYPTION_KEY="not-a-fernet-key",
            ENVIRONMENT="production",
        ))


@pytest.mark.anyio
async def test_production_accepts_strong_secrets():
    validate_secrets(Settings(
        SECRET_KEY=secrets.token_urlsafe(32),
        ENCRYPTION_KEY=Fernet.generate_key().decode(),
        ENVIRONMENT="production",
    ))


@pytest.mark.anyio
async def test_development_only_warns_on_weak_secrets():
    # Must not raise outside production (local dev keeps working).
    validate_secrets(Settings(
        SECRET_KEY="your-secret-key-change-in-production",
        ENCRYPTION_KEY=None,
        ENVIRONMENT="development",
    ))


@pytest.mark.anyio
async def test_is_valid_fernet_key():
    assert is_valid_fernet_key(Fernet.generate_key().decode()) is True
    assert is_valid_fernet_key("not-a-key") is False
    assert is_valid_fernet_key("") is False
    assert is_valid_fernet_key(None) is False


@pytest.mark.anyio
async def test_fernet_key_used_verbatim(monkeypatch):
    """A real Fernet ENCRYPTION_KEY encrypts with itself, not with a
    mangled derivation (the pre-round-2 bug: truncate to 32 chars)."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)
    monkeypatch.setattr(security_mod, "_fernet", None)
    try:
        assert security_mod.get_encryption_key() == key.encode()
        # Round-trip through the app's own encrypt/decrypt, and the same
        # ciphertext must open with a plain Fernet(key) (verbatim use).
        token = security_mod.encrypt_data("google-refresh-token")
        assert Fernet(key.encode()).decrypt(token.encode()).decode() == "google-refresh-token"
        assert security_mod.decrypt_data(token) == "google-refresh-token"
    finally:
        # Never leak the test key into the cached Fernet of other tests.
        security_mod._fernet = None


# ---------------------------------------------------------------- rate limiting

@pytest.mark.anyio
async def test_login_rate_limited(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 3)
    await _register_and_login(async_client, "rl@example.com", "rluser")
    # The helper already used 1 login; 2 more are allowed, the 4th is 429.
    for _ in range(2):
        res = await async_client.post("/api/auth/login", json={
            "email": "rl@example.com", "password": TEST_PASSWORD,
        })
        assert res.status_code == 200
    res = await async_client.post("/api/auth/login", json={
        "email": "rl@example.com", "password": TEST_PASSWORD,
    })
    assert res.status_code == 429
    assert "Retry-After" in res.headers
    assert "rate limit" in res.json()["detail"].lower()


@pytest.mark.anyio
async def test_register_rate_limited(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER_PER_MINUTE", 2)
    for i in range(2):
        res = await async_client.post("/api/auth/register", json={
            "email": f"rl{i}@example.com", "username": f"rluser{i}",
            "password": TEST_PASSWORD,
        })
        assert res.status_code == 201
    res = await async_client.post("/api/auth/register", json={
        "email": "rl2@example.com", "username": "rluser2",
        "password": TEST_PASSWORD,
    })
    assert res.status_code == 429


@pytest.mark.anyio
async def test_rate_limit_can_be_disabled(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 1)
    await _register_and_login(async_client, "rl-off@example.com", "rloff")
    for _ in range(3):
        res = await async_client.post("/api/auth/login", json={
            "email": "rl-off@example.com", "password": TEST_PASSWORD,
        })
        assert res.status_code == 200


# ---------------------------------------------------------------- revocation

@pytest.mark.anyio
async def test_logout_revokes_both_tokens(async_client: AsyncClient):
    tokens = await _register_and_login(async_client, "lo@example.com", "louser")
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]
    headers = {"Authorization": f"Bearer {access}"}

    res = await async_client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200

    res = await async_client.post(
        "/api/auth/logout", json={"refresh_token": refresh}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["revoked"] == 2

    # Access token no longer works anywhere.
    res = await async_client.get("/api/auth/me", headers=headers)
    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()
    # Refresh token cannot mint a new access token.
    res = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 401

    # Logout is idempotent: a second logout revokes nothing new.
    res = await async_client.post(
        "/api/auth/logout", json={"refresh_token": refresh}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["revoked"] == 0


@pytest.mark.anyio
async def test_logout_access_only(async_client: AsyncClient):
    tokens = await _register_and_login(async_client, "lo2@example.com", "louser2")
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]
    res = await async_client.post(
        "/api/auth/logout", json={},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert res.status_code == 200
    assert res.json()["revoked"] == 1
    # The refresh token was NOT revoked: it still works.
    res = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 200


@pytest.mark.anyio
async def test_token_without_jti_still_works(async_client: AsyncClient):
    """Backward compat: tokens issued before jti existed have no jti
    and cannot be revoked — they just expire normally."""
    tokens = await _register_and_login(async_client, "nojti@example.com", "nojti")
    payload = jwt.decode(
        tokens["access_token"], settings.SECRET_KEY, algorithms=["HS256"]
    )
    assert "jti" in payload  # new tokens DO carry jti
    legacy = jwt.encode(
        {"sub": payload["sub"], "type": "access"},
        settings.SECRET_KEY, algorithm="HS256",
    )
    res = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {legacy}"}
    )
    # Legacy token without exp is accepted by the existing verifier
    # (pre-existing behaviour: decode only checks signature + type).
    assert res.status_code == 200


# ---------------------------------------------------------------- headers

@pytest.mark.anyio
async def test_security_headers_present(async_client: AsyncClient):
    res = await async_client.get("/health")
    assert res.status_code == 200
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in res.headers["Content-Security-Policy"]
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in res.headers["Permissions-Policy"]
    # HSTS is production-only: must NOT appear in dev/test.
    assert "Strict-Transport-Security" not in res.headers


# ---------------------------------------------------------------- Redis rate limiting (audit ronde 2 fix)

class _FakeRedis:
    """Minimal stand-in for redis.asyncio: per-key sliding-window
    counting, honouring the limit passed to EVAL."""

    def __init__(self):
        self._counts: dict[str, int] = {}

    async def eval(self, script, numkeys, *keys_and_args):
        key = keys_and_args[0]
        limit = int(keys_and_args[3])
        n = self._counts.get(key, 0)
        if n >= limit:
            return [0, 7]
        self._counts[key] = n + 1
        return [1, 0]


class _FailingRedis:
    async def eval(self, *args, **kwargs):
        import redis as redis_lib

        raise redis_lib.exceptions.ConnectionError("boom")


@pytest.mark.anyio
async def test_redis_rate_limit_enforced(async_client: AsyncClient, monkeypatch):
    """RATE_LIMIT_USE_REDIS=True + working Redis: the Redis window
    (not the in-memory one) decides, and the 3rd login is 429."""
    import app.core.middleware as middleware_mod

    monkeypatch.setattr(settings, "RATE_LIMIT_USE_REDIS", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 2)
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER_PER_MINUTE", 10)
    fake = _FakeRedis()
    monkeypatch.setattr(middleware_mod, "_get_redis_client", lambda: fake)
    await _register_and_login(async_client, "rl-redis@example.com", "rlredis")
    # Helper used 1 login; 1 more is allowed, the 3rd is 429.
    res = await async_client.post("/api/auth/login", json={
        "email": "rl-redis@example.com", "password": TEST_PASSWORD,
    })
    assert res.status_code == 200
    res = await async_client.post("/api/auth/login", json={
        "email": "rl-redis@example.com", "password": TEST_PASSWORD,
    })
    assert res.status_code == 429
    assert res.headers["Retry-After"] == "7"


@pytest.mark.anyio
async def test_redis_failure_falls_back_to_memory(async_client: AsyncClient, monkeypatch):
    """Redis down: requests must NOT 500 — the in-memory limiter
    takes over and still enforces the limit."""
    import app.core.middleware as middleware_mod

    monkeypatch.setattr(settings, "RATE_LIMIT_USE_REDIS", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER_PER_MINUTE", 10)
    monkeypatch.setattr(middleware_mod, "_get_redis_client", lambda: _FailingRedis())
    await _register_and_login(async_client, "rl-fallback@example.com", "rlfb")
    # Helper used the 1 allowed login; the next one is 429 via memory.
    res = await async_client.post("/api/auth/login", json={
        "email": "rl-fallback@example.com", "password": TEST_PASSWORD,
    })
    assert res.status_code == 429


@pytest.mark.anyio
async def test_redis_live_roundtrip(async_client: AsyncClient, monkeypatch):
    """Real redis-server on a scratch port: two logins pass, the
    third is 429 from Redis itself. Skipped when redis-server is
    not installed."""
    import shutil
    import subprocess
    import time

    import redis as redis_lib

    import app.core.middleware as middleware_mod

    if shutil.which("redis-server") is None:
        pytest.skip("redis-server not installed")
    port = 6390
    proc = subprocess.Popen(
        ["redis-server", "--port", str(port), "--save", "", "--appendonly", "no",
         "--daemonize", "no"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        client = redis_lib.Redis(host="127.0.0.1", port=port, socket_timeout=2)
        deadline = time.monotonic() + 10
        while True:
            try:
                client.ping()
                break
            except redis_lib.exceptions.RedisError:
                if time.monotonic() > deadline:
                    pytest.skip("redis-server did not start")
                time.sleep(0.2)
        client.flushall()
        monkeypatch.setattr(settings, "RATE_LIMIT_USE_REDIS", True)
        monkeypatch.setattr(settings, "REDIS_URL", f"redis://127.0.0.1:{port}/0")
        monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 2)
        monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER_PER_MINUTE", 10)
        middleware_mod.reset_rate_limit_redis()
        await _register_and_login(async_client, "rl-live@example.com", "rllive")
        res = await async_client.post("/api/auth/login", json={
            "email": "rl-live@example.com", "password": TEST_PASSWORD,
        })
        assert res.status_code == 200
        res = await async_client.post("/api/auth/login", json={
            "email": "rl-live@example.com", "password": TEST_PASSWORD,
        })
        assert res.status_code == 429
        assert "Retry-After" in res.headers
        # The Redis key exists: the budget really lived in Redis.
        assert client.keys("ratelimit:*")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        middleware_mod.reset_rate_limit_redis()

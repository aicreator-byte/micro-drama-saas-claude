"""HTTP middleware: rate limiting + security headers (future-dev round 2).

Rate limiting is a sliding-window limiter, per client IP and
endpoint. It only guards the auth endpoints (login / register / refresh)
— the brute-force surface — so normal API traffic is unaffected.
Limits come from settings and are read per request, so tests can
monkeypatch them.

Two stores (audit ronde 2 fix): when RATE_LIMIT_USE_REDIS is True the
window lives in Redis (REDIS_URL), so every uvicorn worker shares one
budget; otherwise — and whenever Redis is unreachable — the limiter
falls back to the per-process in-memory store. A Redis outage must
never turn into a 500 or into no limiting at all.

Security headers are applied to every response, including 429s (this
middleware is registered outermost in main.py).
"""
import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window limiter. `allow` is O(hits in window) — the window
    is 60s and the limit is small, so the list stays tiny."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - window_seconds
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) >= limit:
            retry_after = int(hits[0] + window_seconds - now) + 1
            self._hits[key] = hits
            return False, max(retry_after, 1)
        hits.append(now)
        self._hits[key] = hits
        return True, 0

    def reset(self) -> None:
        self._hits.clear()


# One process-wide limiter instance; limits are read from settings per
# request so tests can monkeypatch settings attributes.
rate_limiter = RateLimiter()


# ---------------------------------------------------------------- Redis store
# Lua sliding window: drop hits older than the window, count the rest,
# admit only under the limit. One EVAL = atomic, so concurrent workers
# cannot both slip through. Returns [allowed (1/0), retry_after_seconds].
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry = 1
  if #oldest >= 2 then
    retry = math.ceil(tonumber(oldest[2]) + window - now)
  end
  return {0, retry}
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, math.ceil(window / 1000))
return {1, 0}
"""

_redis_client = None


def _get_redis_client():
    """Shared async Redis client, built lazily from settings. Returns
    None when redis-py is not installed (ImportError is a hard no —
    fall back to memory instead of crashing the import)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis
    except ImportError:
        return None
    _redis_client = aioredis.Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
        decode_responses=True,
    )
    return _redis_client


def reset_rate_limit_redis() -> None:
    """Drop the cached Redis client (tests; also lets a recovered
    Redis be picked up again after an outage)."""
    global _redis_client
    _redis_client = None


class RedisRateLimiter:
    """Sliding-window limiter backed by Redis. Raises on any Redis
    error — the caller falls back to the in-memory limiter."""

    def __init__(self, client) -> None:
        self._client = client

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now_ms = int(time.time() * 1000)
        member = f"{now_ms}:{uuid.uuid4().hex}"
        allowed, retry_after = await self._client.eval(
            _SLIDING_WINDOW_LUA,
            1,
            f"ratelimit:{key}",
            now_ms,
            window_seconds * 1000,
            limit,
            member,
        )
        return bool(int(allowed)), max(int(retry_after), 0)


async def _allow(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Try the Redis store when enabled; any failure falls back to the
    in-memory limiter so a Redis outage never blocks auth traffic."""
    if getattr(settings, "RATE_LIMIT_USE_REDIS", False):
        client = _get_redis_client()
        if client is not None:
            try:
                return await RedisRateLimiter(client).allow(key, limit, window_seconds)
            except Exception as exc:  # noqa: BLE001 - Redis down: degrade, don't fail
                logger.warning(
                    "Redis rate limiter unavailable, falling back to in-memory: %s",
                    exc,
                )
    return rate_limiter.allow(key, limit, window_seconds)

# path -> settings attribute holding its per-minute limit
_LIMITED_PATHS = {
    "/api/auth/login": "RATE_LIMIT_LOGIN_PER_MINUTE",
    "/api/auth/register": "RATE_LIMIT_REGISTER_PER_MINUTE",
    "/api/auth/refresh": "RATE_LIMIT_REFRESH_PER_MINUTE",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """429 when one IP exceeds an auth endpoint's per-minute budget."""

    async def dispatch(self, request: Request, call_next):
        if settings.RATE_LIMIT_ENABLED:
            limit_attr = _LIMITED_PATHS.get(request.url.path)
            if limit_attr is not None:
                limit = getattr(settings, limit_attr)
                client = request.client.host if request.client else "unknown"
                allowed, retry_after = await _allow(
                    f"{client}:{request.url.path}",
                    limit,
                    settings.RATE_LIMIT_WINDOW_SECONDS,
                )
                if not allowed:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded, try again later"},
                        headers={"Retry-After": str(retry_after)},
                    )
        return await call_next(request)


SECURITY_HEADERS = {
    # Never let the browser sniff a JSON response as HTML/JS.
    "X-Content-Type-Options": "nosniff",
    # The API must never be framed (clickjacking).
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # API serves data, not pages: nothing may load, nothing may frame us.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# HSTS only over production HTTPS; sending it on local plain HTTP is
# ignored by browsers, but keeping it production-only avoids surprises.
HSTS_HEADER = "Strict-Transport-Security"
HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        if settings.ENVIRONMENT == "production":
            response.headers[HSTS_HEADER] = HSTS_VALUE
        return response

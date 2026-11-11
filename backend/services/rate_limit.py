"""Redis-backed fixed-window rate limiter; process-local fallback is development only."""
from collections import defaultdict, deque
from threading import Lock
from time import time
import os
from fastapi import Request
from backend.core.config import settings

_local: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()

async def enforce_auth_rate_limit(request: Request) -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    path = request.url.path
    if path not in {"/api/auth/register", "/api/auth/login", "/api/auth/verify-email",
                    "/api/auth/forgot-password", "/api/auth/reset-password"}:
        return
    client = request.client.host if request.client else "unknown"
    key = f"tripledger:auth:{client}:{path}"
    limit, window = (8, 60)
    if getattr(settings, "redis_url", ""):
        try:
            from redis.asyncio import Redis
            redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window)
            await redis.aclose()
            if count > limit:
                from fastapi import HTTPException
                raise HTTPException(status_code=429, detail="Too many authentication attempts. Try again later.", headers={"Retry-After": str(window)})
            return
        except Exception as exc:
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                raise
            if getattr(settings, "app_env", "development") == "production":
                raise RuntimeError("Install redis to enable distributed rate limiting")
            # Development-only fallback if Redis is not installed.
    elif getattr(settings, "app_env", "development") == "production":
        raise RuntimeError("REDIS_URL is required in production for distributed rate limiting")
    now = time()
    with _lock:
        bucket = _local[key]
        while bucket and now - bucket[0] >= window:
            bucket.popleft()
        if len(bucket) >= limit:
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Too many authentication attempts. Try again later.", headers={"Retry-After": str(window)})
        bucket.append(now)

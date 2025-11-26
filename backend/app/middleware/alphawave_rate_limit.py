from typing import Callable
from fastapi import Request, Response
from app.database import get_redis


ENDPOINT_LIMITS = {
    "/chat": 60,
    "/dashboards/generate": 10,
    "/images/generate": 5,
}

PUBLIC_PATHS = {"/healthz", "/health/check"}


async def rate_limit_middleware(request: Request, call_next: Callable):
    endpoint = request.url.path
    if endpoint in PUBLIC_PATHS:
        return await call_next(request)

    redis_client = get_redis()
    if redis_client is None:
        # If Redis is unavailable, skip rate limiting but continue
        return await call_next(request)

    user_id = getattr(request.state, "user_id", "anonymous")
    limit = ENDPOINT_LIMITS.get(endpoint, 60)

    key = f"rate_limit:{user_id}:{endpoint}"
    current = redis_client.get(key)

    if current is None:
        # initialize bucket (60s ttl)
        redis_client.setex(key, 60, limit - 1)
    else:
        remaining = int(current)
        if remaining <= 0:
            return Response(status_code=429, content="Rate limit exceeded")
        redis_client.decr(key)

    return await call_next(request)

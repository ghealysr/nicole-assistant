from typing import Callable
from fastapi import Request
from fastapi.responses import JSONResponse
from app.database import get_redis


ENDPOINT_LIMITS = {
    "/chat": 60,
    "/dashboards/generate": 10,
    "/images/generate": 5,
}

PUBLIC_PATHS = {"/healthz", "/health/check"}

# CORS origins for rate limit responses
CORS_ORIGINS = [
    "https://nicole.alphawavetech.com",
    "http://localhost:3000",
]


def _get_cors_headers(request: Request) -> dict:
    """Get CORS headers for rate limit responses."""
    origin = request.headers.get("origin", "")
    
    # Check if origin is allowed
    if origin in CORS_ORIGINS or ".vercel.app" in origin:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
        }
    
    return {}


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
            # Return 429 with CORS headers
            cors_headers = _get_cors_headers(request)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Please try again later."},
                headers=cors_headers
            )
        redis_client.decr(key)

    return await call_next(request)

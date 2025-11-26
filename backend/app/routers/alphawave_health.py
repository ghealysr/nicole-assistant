"""
Health check router for monitoring and deployment verification.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database import get_redis, get_qdrant, get_supabase, get_tiger_pool
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    environment: str
    checks: dict[str, str]


def _check_redis() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False


def _check_qdrant() -> bool:
    client = get_qdrant()
    if client is None:
        return False
    try:
        client.get_collections()
        return True
    except Exception:
        return False


def _check_supabase() -> bool:
    client = get_supabase()
    if client is None:
        return False
    try:
        # Use a lightweight PostgREST query which works with service-role key
        client.table("conversations").select("id").limit(1).execute()
        return True
    except Exception:
        return False


async def _check_tiger() -> bool:
    pool = await get_tiger_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("select 1")
        return True
    except Exception:
        return False


@router.get("/check")
async def health_check():
    """System health check with all service statuses."""
    checks = {
        "redis": _check_redis(),
        "qdrant": _check_qdrant(),
        "supabase": _check_supabase(),
        "tiger_postgres": await _check_tiger(),
        "timestamp": datetime.utcnow().isoformat(),
    }
    status = "healthy" if all(v is True for k, v in checks.items() if k != "timestamp") else "degraded"
    return {"status": status, "checks": checks}


@router.get("/ping")
async def ping() -> dict:
    """
    Simple ping endpoint for basic connectivity test.
    
    Returns:
        Pong response
    """
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}

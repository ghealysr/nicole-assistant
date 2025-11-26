from typing import Optional

from qdrant_client import QdrantClient
from redis import Redis
from supabase import Client, create_client
import asyncpg

from app.config import settings


_supabase: Optional[Client] = None
_redis_client: Optional[Redis] = None
_qdrant_client: Optional[QdrantClient] = None
_tiger_pool: Optional[asyncpg.Pool] = None


def get_supabase() -> Optional[Client]:
    """Create and return a Supabase client if configured, else None."""
    global _supabase
    if _supabase is not None:
        return _supabase
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    try:
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    except Exception:
        _supabase = None
    return _supabase


def get_redis() -> Optional[Redis]:
    """Create and return a Redis client if reachable, else None."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Try a ping but ignore failures
        _redis_client.ping()
    except Exception:
        _redis_client = None
    return _redis_client


def get_qdrant() -> Optional[QdrantClient]:
    """Create and return a Qdrant client if reachable, else None."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client
    try:
        _qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        # Touch endpoint to validate, swallow errors
        _qdrant_client.get_collections()
    except Exception:
        _qdrant_client = None
    return _qdrant_client


async def get_tiger_pool() -> Optional[asyncpg.Pool]:
    """Return a singleton asyncpg pool to Tiger Postgres if configured."""
    global _tiger_pool
    if _tiger_pool is not None:
        return _tiger_pool

    database_url = settings.DATABASE_URL or settings.TIGER_PRODUCTION_URL or settings.TIGER_DEVELOPMENT_URL
    if not database_url:
        return None

    try:
        _tiger_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=20, command_timeout=60)
    except Exception:
        _tiger_pool = None
    return _tiger_pool

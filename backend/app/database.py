"""
Nicole V7 Database Layer - Tiger Postgres Native

Production-grade database connectivity with:
- Async connection pooling (asyncpg)
- Redis caching layer
- Vector type support (pgvectorscale)
- JSONB codec for structured data
- Health monitoring
- Graceful lifecycle management

Legacy Supabase helpers remain for backward compatibility during migration.
"""

import asyncpg
import redis.asyncio as aioredis
from redis import Redis as SyncRedis
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import json
import logging
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# TIGER DATABASE MANAGER
# =============================================================================

class TigerDatabaseManager:
    """
    Manages Tiger Postgres connections with async connection pooling.
    
    Features:
    - Connection pooling with configurable min/max connections
    - Automatic vector type codec registration
    - JSONB serialization/deserialization
    - Redis cache integration
    - Health monitoring
    
    Usage:
        await db.connect()
        rows = await db.fetch("SELECT * FROM users WHERE id = $1", user_id)
        await db.disconnect()
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False
        self._connection_attempts = 0
        self._max_retries = 3
    
    async def connect(self) -> None:
        """
        Initialize database connections.
        
        Creates:
        - asyncpg connection pool for Tiger Postgres
        - aioredis connection for caching
        
        Raises:
            ConnectionError: If database connection fails after retries
        """
        if self._connected:
            return
        
        # Tiger Postgres Pool
        try:
            self.pool = await asyncpg.create_pool(
                dsn=settings.TIGER_DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60,
                statement_cache_size=100,
                setup=self._setup_connection,
            )
            
            # Verify connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"[Tiger] Connected: {version[:60]}...")
                
        except Exception as e:
            logger.error(f"[Tiger] Connection failed: {e}")
            raise ConnectionError(f"Failed to connect to Tiger Postgres: {e}")
        
        # Redis Cache
        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )
            await self.redis.ping()
            logger.info("[Redis] Connected")
        except Exception as e:
            logger.warning(f"[Redis] Connection failed (caching disabled): {e}")
            self.redis = None
        
        self._connected = True
    
    async def _setup_connection(self, conn: asyncpg.Connection) -> None:
        """
        Configure each connection with required type codecs.
        
        Registers:
        - vector type for pgvectorscale operations
        - jsonb codec for structured data
        """
        # Register vector type codec
        try:
            await conn.set_type_codec(
                'vector',
                encoder=lambda v: f'[{",".join(map(str, v))}]' if v else None,
                decoder=lambda v: [float(x) for x in v.strip('[]').split(',')] if v else None,
                schema='public',
            )
        except Exception:
            # Vector type may not exist yet
            pass
        
        # Register JSONB codec
        await conn.set_type_codec(
            'jsonb',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog',
        )
    
    async def disconnect(self) -> None:
        """Close all database connections gracefully."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("[Tiger] Disconnected")
        
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("[Redis] Disconnected")
        
        self._connected = False
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    @asynccontextmanager
    async def acquire(self):
        """
        Context manager for acquiring a database connection.
        
        Usage:
            async with db.acquire() as conn:
                await conn.execute("INSERT INTO ...")
        """
        if not self._connected:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, *args) -> str:
        """
        Execute a query without returning results.
        
        Args:
            query: SQL query with $1, $2, etc. placeholders
            *args: Query parameters
            
        Returns:
            Command tag (e.g., "INSERT 0 1")
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """
        Fetch multiple rows.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            List of Record objects (dict-like)
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Fetch a single row.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Single Record or None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """
        Fetch a single value.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Single value from first column of first row
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    # =========================================================================
    # REDIS CACHE METHODS
    # =========================================================================
    
    async def cache_get(self, key: str) -> Optional[str]:
        """Get string value from Redis cache."""
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception:
            return None
    
    async def cache_set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set string value in Redis cache with TTL."""
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, value)
        except Exception:
            pass
    
    async def cache_delete(self, key: str) -> None:
        """Delete key from Redis cache."""
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception:
            pass
    
    async def cache_get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache."""
        data = await self.cache_get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def cache_set_json(self, key: str, value: Dict, ttl: int = 3600) -> None:
        """Set JSON value in cache."""
        try:
            await self.cache_set(key, json.dumps(value), ttl)
        except Exception:
            pass
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Return health status of all database connections.
        
        Returns:
            Dict with connection status for each service
        """
        health = {
            "tiger_postgres": "unknown",
            "redis": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Check Tiger Postgres
        try:
            if self.pool:
                await self.pool.fetchval("SELECT 1")
                health["tiger_postgres"] = "connected"
            else:
                health["tiger_postgres"] = "not_initialized"
        except Exception as e:
            health["tiger_postgres"] = f"error: {str(e)[:50]}"
        
        # Check Redis
        try:
            if self.redis:
                await self.redis.ping()
                health["redis"] = "connected"
            else:
                health["redis"] = "disabled"
        except Exception as e:
            health["redis"] = f"error: {str(e)[:50]}"
        
        return health


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

db = TigerDatabaseManager()


# =============================================================================
# FASTAPI LIFECYCLE HOOKS
# =============================================================================

async def startup_db():
    """Called on FastAPI startup to initialize connections."""
    await db.connect()


async def shutdown_db():
    """Called on FastAPI shutdown to close connections."""
    await db.disconnect()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def get_tiger_pool() -> Optional[asyncpg.Pool]:
    """
    Get the Tiger asyncpg pool directly.
    
    Useful for advanced operations that need direct pool access.
    """
    if not db._connected:
        await db.connect()
    return db.pool


def get_redis_sync() -> Optional[SyncRedis]:
    """
    Get synchronous Redis client for code that can't use async.
    
    Prefer db.redis for async operations.
    """
    try:
        client = SyncRedis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def get_redis() -> Optional[SyncRedis]:
    """
    Get synchronous Redis client for rate limiting and other sync operations.
    
    This is a compatibility function - prefer db.redis for async operations.
    """
    return get_redis_sync()


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================
# These functions maintain backward compatibility with code that still uses
# Supabase and Qdrant. They return None when not configured, allowing
# graceful degradation.

_supabase_client = None
_qdrant_client = None


def get_supabase():
    """
    Get Supabase client for legacy code compatibility.
    
    Returns None if Supabase is not configured, allowing graceful fallback.
    New code should use Tiger Postgres directly via `db`.
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    
    try:
        from supabase import create_client
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        return _supabase_client
    except Exception as e:
        logger.warning(f"[Supabase] Client creation failed: {e}")
        return None


def get_qdrant():
    """
    Get Qdrant client for legacy code compatibility.
    
    Returns None - Qdrant has been replaced by pgvectorscale in Tiger Postgres.
    This function exists only for backward compatibility.
    """
    # Qdrant is no longer used - vector operations are now in Tiger Postgres
    return None

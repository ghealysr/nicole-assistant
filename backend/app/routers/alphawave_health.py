"""
Health check router for monitoring and deployment verification.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime
import logging
from typing import Any

from app.database import get_redis, get_qdrant, get_supabase, get_tiger_pool
from app.config import settings
from app.services.agent_orchestrator import agent_orchestrator

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


@router.get("/mcp")
async def mcp_status() -> dict:
    """
    MCP (Model Context Protocol) server status.
    
    Shows status of all configured MCP servers:
    - google: Gmail, Calendar, Drive
    - notion: Databases, Pages
    - telegram: Bot messaging
    - filesystem: File operations
    - playwright: Web automation
    - sequential-thinking: Reasoning visualization
    
    Returns:
        MCP server status summary
    """
    status = agent_orchestrator.get_mcp_status()
    
    return {
        "mcp_status": "operational" if status.get("connected_servers", 0) > 0 else "available",
        "connected_servers": status.get("connected_servers", 0),
        "total_tools": status.get("total_tools", 0),
        "servers": status.get("servers", {}),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/mcp/connect/{server_name}")
async def connect_mcp_server(server_name: str) -> dict:
    """
    Manually connect to a specific MCP server.
    
    Args:
        server_name: Name of the server (google, notion, telegram, etc.)
        
    Returns:
        Connection result
    """
    from app.mcp import mcp_manager, AlphawaveMCPManager
    
    if not isinstance(mcp_manager, AlphawaveMCPManager):
        return {
            "status": "unavailable",
            "message": "MCP manager using fallback mode (npx not available)"
        }
    
    success = await mcp_manager.connect_server(server_name)
    
    return {
        "status": "connected" if success else "failed",
        "server": server_name,
        "timestamp": datetime.utcnow().isoformat()
    }

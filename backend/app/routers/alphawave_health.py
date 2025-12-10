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
from app.mcp.docker_mcp_client import get_mcp_client

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
    MCP (Model Context Protocol) status.
    
    - Reports Docker MCP Gateway status (if enabled)
    - Includes legacy MCP manager status for visibility
    """
    legacy_status = agent_orchestrator.get_mcp_status()
    gateway_status: dict[str, Any] = {
        "status": "disabled",
        "connected": False,
        "tool_count": 0,
        "tools": [],
    }
    try:
        if settings.MCP_ENABLED:
            mcp = await get_mcp_client()
            tools = await mcp.list_tools(refresh=True)
            gateway_status = {
                "status": "healthy",
                "connected": mcp.is_connected,
                "tool_count": len(tools),
                "tools": [t.name for t in tools[:10]],
            }
    except Exception as e:
        gateway_status = {"status": "unhealthy", "error": str(e)}
    
    return {
        "gateway": gateway_status,
        "legacy": {
            "mcp_status": "operational" if legacy_status.get("connected_servers", 0) > 0 else "available",
            "connected_servers": legacy_status.get("connected_servers", 0),
            "total_tools": legacy_status.get("total_tools", 0),
            "servers": legacy_status.get("servers", {}),
        },
        "timestamp": datetime.utcnow().isoformat(),
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


@router.get("/system")
async def system_health():
    """Get comprehensive system health and status information."""
    import psutil
    from app.database import get_tiger_pool
    
    try:
        # Database Status
        db_status = "online"
        try:
            pool = await get_tiger_pool()
            if pool:
                async with pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
            else:
                db_status = "offline"
        except Exception:
            db_status = "offline"
        
        # MCP Status
        mcp_status = "offline"
        mcp_tool_count = 0
        try:
            if settings.MCP_ENABLED:
                mcp = await get_mcp_client()
                if mcp.is_connected:
                    mcp_status = "online"
                    mcp_tool_count = mcp.tool_count
        except Exception:
            pass
        
        # Scheduled Jobs Status
        try:
            from app.main import scheduler
            jobs_status = "running" if scheduler.running else "stopped"
            job_count = len(scheduler.get_jobs())
        except Exception:
            jobs_status = "unknown"
            job_count = 0
        
        # System Resources
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Configuration Check
        services_configured = {
            "azure_document_intelligence": bool(settings.AZURE_DOCUMENT_ENDPOINT and settings.AZURE_DOCUMENT_KEY),
            "openai_embeddings": bool(settings.OPENAI_API_KEY),
            "claude": bool(settings.ANTHROPIC_API_KEY),
            "google_oauth": bool(settings.GOOGLE_CLIENT_ID),
            "mcp_gateway": bool(settings.MCP_ENABLED),
        }
        
        return {
            "status": "healthy" if db_status == "online" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "databases": {
                "tiger_timescaledb": db_status,
            },
            "services": {
                "mcp_gateway": mcp_status,
                "mcp_tool_count": mcp_tool_count,
                "background_jobs": jobs_status,
                "job_count": job_count,
            },
            "system": {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_available_gb": round(memory.available / (1024**3), 2),
            },
            "configuration": services_configured,
        }
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

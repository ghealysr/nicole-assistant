"""
Nicole V7 - FastAPI Main Application
Built according to Agent 1 specifications for production-quality backend.

Includes:
- Database lifecycle management
- Background job scheduler (APScheduler)
- MCP (Model Context Protocol) integrations
- Middleware stack (CORS, logging, auth, rate limiting)
- All API routers
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.mcp import initialize_mcp, shutdown_mcp
from app.mcp.docker_mcp_client import get_mcp_client, shutdown_mcp_client
from app.middleware.alphawave_cors import configure_cors
from app.middleware.alphawave_logging import logging_middleware
from app.middleware.alphawave_auth import verify_jwt
from app.middleware.alphawave_rate_limit import rate_limit_middleware
from app.database import startup_db, shutdown_db
from app.routers import (
    alphawave_health,
    alphawave_auth,
    alphawave_chat,
    alphawave_documents,
    alphawave_files,
    alphawave_journal,
    alphawave_memories,
    alphawave_projects,
    alphawave_skills,
    alphawave_sports_oracle,
    alphawave_voice,
    alphawave_webhooks,
    alphawave_widgets,
    alphawave_dashboards,
    alphawave_workflows,
    alphawave_dashboard,
)

logger = logging.getLogger(__name__)

# =============================================================================
# BACKGROUND JOB SCHEDULER
# =============================================================================

scheduler = AsyncIOScheduler(timezone="UTC")


def setup_scheduled_jobs():
    """
    Configure scheduled background jobs for memory maintenance and skill health.
    
    Jobs run during low-activity hours (3 AM UTC) to minimize impact.
    """
    from app.services.memory_background_jobs import run_all_memory_jobs
    from app.services.skill_health_service import run_scheduled_health_checks
    
    # Run all memory maintenance jobs daily at 3 AM UTC
    scheduler.add_job(
        run_all_memory_jobs,
        CronTrigger(hour=3, minute=0),
        id="memory_maintenance",
        name="Daily Memory Maintenance",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow 1 hour grace period
    )
    
    # Run skill health checks daily at 4 AM UTC
    scheduler.add_job(
        run_scheduled_health_checks,
        CronTrigger(hour=4, minute=0),
        id="skill_health_checks",
        name="Daily Skill Health Checks",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    
    logger.info("[SCHEDULER] Background jobs configured (memory + skills)")


# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles:
    - Database connection pool startup/shutdown
    - Background scheduler startup/shutdown
    - Workflow scheduler initialization
    """
    # Startup
    logger.info("[STARTUP] Initializing Nicole V7 API...")
    
    # Initialize database connections
    await startup_db()
    logger.info("[STARTUP] Database connections established")
    
    # Setup and start scheduler
    try:
        setup_scheduled_jobs()
        scheduler.start()
        logger.info("[STARTUP] Background scheduler started")
    except Exception as e:
        logger.warning(f"[STARTUP] Scheduler failed to start (non-critical): {e}")
    
    # Initialize workflow scheduler (agent architecture)
    try:
        from app.services.workflow_scheduler import workflow_scheduler
        await workflow_scheduler.initialize()
        logger.info("[STARTUP] Workflow scheduler initialized")
    except Exception as e:
        logger.warning(f"[STARTUP] Workflow scheduler failed to initialize (non-critical): {e}")
    
    # Initialize MCP (Model Context Protocol) servers - legacy (npx-based)
    try:
        mcp_results = await initialize_mcp()
        connected = [k for k, v in mcp_results.items() if v]
        if connected:
            logger.info(f"[STARTUP] MCP servers connected: {connected}")
        else:
            logger.info("[STARTUP] MCP initialized (no servers connected yet)")
    except Exception as e:
        logger.warning(f"[STARTUP] MCP failed to initialize (non-critical): {e}")

    # Initialize Docker MCP Gateway (if enabled)
    if settings.MCP_ENABLED:
        try:
            mcp = await get_mcp_client()
            logger.info(f"[STARTUP] MCP Gateway connected: {mcp.tool_count} tools available")
        except Exception as e:
            logger.warning(f"[STARTUP] MCP Gateway unavailable (non-critical): {e}")
    
    logger.info("[STARTUP] Nicole V7 API ready")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("[SHUTDOWN] Shutting down Nicole V7 API...")
    
    # Disconnect MCP servers
    try:
        await shutdown_mcp()
        logger.info("[SHUTDOWN] MCP servers disconnected")
    except Exception as e:
        logger.debug(f"[SHUTDOWN] MCP shutdown: {e}")

    # Disconnect MCP Gateway
    try:
        await shutdown_mcp_client()
        logger.info("[SHUTDOWN] MCP Gateway disconnected")
    except Exception as e:
        logger.debug(f"[SHUTDOWN] MCP Gateway shutdown: {e}")
    
    # Stop workflow scheduler
    try:
        from app.services.workflow_scheduler import workflow_scheduler
        await workflow_scheduler.shutdown()
        logger.info("[SHUTDOWN] Workflow scheduler stopped")
    except Exception as e:
        logger.debug(f"[SHUTDOWN] Workflow scheduler shutdown: {e}")
    
    # Stop scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[SHUTDOWN] Background scheduler stopped")
    
    # Close database connections
    await shutdown_db()
    logger.info("[SHUTDOWN] Database connections closed")


app = FastAPI(
    title="Nicole V7 API",
    description="Personal AI companion for Glen Healy and family",
    version="7.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)
# CORS middleware (custom implementation as per Agent 1 spec)
configure_cors(app)

# Middleware stack (order matters as per Agent 1 spec)
app.middleware("http")(logging_middleware)
app.middleware("http")(verify_jwt)
app.middleware("http")(rate_limit_middleware)

# Routers
app.include_router(alphawave_health.router, prefix="/health", tags=["Health"])
app.include_router(alphawave_auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(alphawave_chat.router, prefix="/chat", tags=["Chat"])
app.include_router(alphawave_documents.router, prefix="/documents", tags=["Documents"])
app.include_router(alphawave_files.router, prefix="/files", tags=["Files"])
app.include_router(alphawave_journal.router, prefix="/journal", tags=["Journal"])
app.include_router(alphawave_memories.router, prefix="/memories", tags=["Memories"])
app.include_router(alphawave_projects.router, prefix="/projects", tags=["Projects"])
app.include_router(alphawave_skills.router, prefix="/skills", tags=["Skills"])
app.include_router(alphawave_sports_oracle.router, prefix="/sports", tags=["Sports Oracle"])
app.include_router(alphawave_voice.router, prefix="/voice", tags=["Voice"])
app.include_router(alphawave_webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(alphawave_widgets.router, prefix="/widgets", tags=["Widgets"])
app.include_router(alphawave_dashboards.router, prefix="/dashboards", tags=["Dashboards"])
app.include_router(alphawave_workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(alphawave_dashboard.router, prefix="/dashboard", tags=["Dashboard Metrics"])


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.ENVIRONMENT == "development")

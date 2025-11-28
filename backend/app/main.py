"""
Nicole V7 - FastAPI Main Application
Built according to Agent 1 specifications for production-quality backend.
"""

from fastapi import FastAPI

from app.config import settings
from app.middleware.alphawave_cors import configure_cors
from app.middleware.alphawave_logging import logging_middleware
from app.middleware.alphawave_auth import verify_jwt
from app.middleware.alphawave_rate_limit import rate_limit_middleware
from app.routers import (
    alphawave_health,
    alphawave_auth,
    alphawave_chat,
    alphawave_documents,
    alphawave_files,
    alphawave_journal,
    alphawave_memories,
    alphawave_projects,
    alphawave_sports_oracle,
    alphawave_voice,
    alphawave_webhooks,
    alphawave_widgets,
    alphawave_dashboards,
)


app = FastAPI(
    title="Nicole V7 API",
    description="Personal AI companion for Glen Healy and family",
    version="7.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
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
app.include_router(alphawave_sports_oracle.router, prefix="/sports", tags=["Sports Oracle"])
app.include_router(alphawave_voice.router, prefix="/voice", tags=["Voice"])
app.include_router(alphawave_webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(alphawave_widgets.router, prefix="/widgets", tags=["Widgets"])
app.include_router(alphawave_dashboards.router, prefix="/dashboards", tags=["Dashboards"])


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.ENVIRONMENT == "development")

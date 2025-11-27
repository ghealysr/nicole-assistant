"""
CORS middleware configuration for Nicole V7.
"""

from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


def get_cors_origins() -> list[str]:
    """
    Get list of allowed CORS origins based on environment.
    
    Returns:
        List of allowed origin URLs
    """
    
    if settings.ENVIRONMENT == "development":
        return [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ]
    
    return [
        "https://nicole.alphawavetech.com",
        "https://nicole-v7.vercel.app",
        "https://ghealysr-nicole-assistant-yyr5.vercel.app",
    ]


def get_cors_origin_regex() -> str:
    """
    Regex pattern for allowed CORS origins.
    Matches Vercel preview deployments and production domains.
    """
    if settings.ENVIRONMENT == "development":
        return None
    
    # Match any Vercel preview URL for this project
    return r"https://ghealysr-nicole-assistant.*\.vercel\.app"


def configure_cors(app) -> None:
    """
    Configure CORS middleware on FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    
    origin_regex = get_cors_origin_regex()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

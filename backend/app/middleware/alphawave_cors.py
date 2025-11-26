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
    ]


def configure_cors(app) -> None:
    """
    Configure CORS middleware on FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

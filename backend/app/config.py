"""
Nicole V7 Configuration - Tiger Native
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Tiger Postgres (PRIMARY DATABASE)
    TIGER_DATABASE_URL: str
    TIGER_SPORTS_URL: Optional[str] = None  # Separate sports oracle DB

    # Legacy (for compatibility)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379"

    # AI APIs
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str
    REPLICATE_API_TOKEN: str = ""

    # Azure AI
    AZURE_DOCUMENT_ENDPOINT: str = ""
    AZURE_DOCUMENT_KEY: str = ""
    AZURE_VISION_ENDPOINT: str = ""
    AZURE_VISION_KEY: str = ""

    # ElevenLabs Voice
    ELEVENLABS_API_KEY: str = ""
    NICOLE_VOICE_ID: str = ""

    # File Storage - DigitalOcean Spaces
    DO_SPACES_ENDPOINT: str = ""
    DO_SPACES_BUCKET: str = ""
    DO_SPACES_BACKUP_BUCKET: str = ""
    DO_SPACES_ACCESS_KEY: str = ""
    DO_SPACES_SECRET_KEY: str = ""

    # Cloudinary - Image/Screenshot Storage
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # UploadThing
    UPLOADTHING_APP_ID: str = ""
    UPLOADTHING_SECRET: str = ""

    # Frontend URL
    FRONTEND_URL: str = ""

    # Monitoring / Analytics
    SENTRY_DSN: str = ""

    # Security
    JWT_SECRET_KEY: str = ""
    SESSION_SECRET: str = ""
    ALLOWED_USERS: str = ""

    # Safety Configuration
    SAFETY_ENABLE: bool = True
    SAFETY_ENABLE_PROVIDER_MODERATION: bool = True
    SAFETY_CHECK_INTERVAL_MS: int = 300
    SAFETY_MAX_TOKEN_WINDOW: int = 400
    COPPA_REQUIRE_PARENTAL_CONSENT: bool = True
    COPPA_MIN_AGE_NO_CONSENT: int = 13
    SAFETY_POLICY_VERSION: str = "v7.1"

    # Google OAuth Authentication
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_ALLOWED_DOMAINS: str = "alphawavetech.com"  # Comma-separated domains
    GOOGLE_ALLOWED_EMAILS: str = "ghealysr@gmail.com"  # Comma-separated specific emails

    # MCP Integrations
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    GLEN_TELEGRAM_CHAT_ID: Optional[str] = None
    NOTION_API_KEY: Optional[str] = None
    NOTION_GLEN_WORKSPACE_ID: Optional[str] = None

    # Rate Limits
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW: int = 60

    # MCP Gateway (Docker MCP)
    MCP_GATEWAY_URL: str = "http://127.0.0.1:3100"
    MCP_ENABLED: bool = True
    BRAVE_API_KEY: str = ""
    RECRAFT_API_KEY: str = ""  # For image generation via MCP bridge

    class Config:
        env_file = ".env" if os.path.exists(".env") else "/opt/nicole/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

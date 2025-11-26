try:
    from pydantic_settings import BaseSettings, SettingsConfigDict  # pydantic-settings v2
    _HAS_SETTINGS_V2 = True
except Exception:  # pragma: no cover - fallback for pydantic-settings v1
    from pydantic_settings import BaseSettings  # type: ignore
    SettingsConfigDict = None  # type: ignore
    _HAS_SETTINGS_V2 = False
from pydantic import Field
from functools import lru_cache


class AlphawaveSettings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes mirror the environment variable names in .env.template.
    """

    # Core
    ENVIRONMENT: str = Field(default="development")

    # Supabase
    SUPABASE_URL: str = Field(default="")
    SUPABASE_ANON_KEY: str = Field(default="")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = Field(default="")

    # Caches/Vector
    REDIS_URL: str = Field(default="redis://localhost:6379")
    QDRANT_URL: str = Field(default="http://localhost:6333")

    # Tiger Postgres (Agentic Postgres)
    TIGER_PRODUCTION_URL: str = Field(default="")
    TIGER_DEVELOPMENT_URL: str = Field(default="")
    TIGER_SPORTS_ORACLE_URL: str = Field(default="")
    DATABASE_URL: str = Field(default="")

    # AI Keys
    ANTHROPIC_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")

    # Voice
    ELEVENLABS_API_KEY: str = Field(default="")
    NICOLE_VOICE_ID: str = Field(default="")

    # Replicate (FLUX/Whisper)
    REPLICATE_API_TOKEN: str = Field(default="")

    # Azure AI
    AZURE_VISION_ENDPOINT: str = Field(default="")
    AZURE_VISION_KEY: str = Field(default="")
    AZURE_DOCUMENT_ENDPOINT: str = Field(default="")
    AZURE_DOCUMENT_KEY: str = Field(default="")

    # UploadThing
    UPLOADTHING_APP_ID: str = Field(default="")
    UPLOADTHING_SECRET: str = Field(default="")

    # Spaces/CDN
    DO_SPACES_ENDPOINT: str = Field(default="")
    DO_SPACES_BUCKET: str = Field(default="")
    DO_SPACES_BACKUP_BUCKET: str = Field(default="")
    DO_SPACES_ACCESS_KEY: str = Field(default="")
    DO_SPACES_SECRET_KEY: str = Field(default="")

    # Monitoring
    SENTRY_DSN: str = Field(default="")

    # Telegram (optional)
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    GLEN_TELEGRAM_CHAT_ID: str = Field(default="")

    # Notion (optional)
    NOTION_API_KEY: str = Field(default="")
    NOTION_GLEN_WORKSPACE_ID: str = Field(default="")

    # App secrets (optional)
    JWT_SECRET_KEY: str = Field(default="")
    SESSION_SECRET: str = Field(default="")

    # Access control (optional)
    ALLOWED_USERS: str = Field(default="")

    # Frontend URL (for auth redirects)
    FRONTEND_URL: str = Field(default="")
    
    # =========================================================================
    # Safety System Configuration
    # =========================================================================
    
    # Safety system enable/disable
    SAFETY_ENABLE: bool = Field(
        default=True,
        description="Enable content safety filtering system"
    )
    
    # Provider moderation (OpenAI Moderation API)
    SAFETY_ENABLE_PROVIDER_MODERATION: bool = Field(
        default=True,
        description="Enable OpenAI Moderation API for comprehensive checks"
    )
    
    # Streaming safety checks
    SAFETY_CHECK_INTERVAL_MS: int = Field(
        default=300,
        description="How often to check streaming output for safety (milliseconds)",
        ge=100,  # Minimum 100ms
        le=1000  # Maximum 1 second
    )
    
    SAFETY_MAX_TOKEN_WINDOW: int = Field(
        default=400,
        description="Maximum tokens to buffer before safety check"
    )
    
    # COPPA Compliance
    COPPA_REQUIRE_PARENTAL_CONSENT: bool = Field(
        default=True,
        description="Require parental consent for users under 13 (COPPA compliance)"
    )
    
    COPPA_MIN_AGE_NO_CONSENT: int = Field(
        default=13,
        description="Minimum age that doesn't require parental consent"
    )
    
    # Safety policy version
    SAFETY_POLICY_VERSION: str = Field(
        default="v7.1",
        description="Current safety policy version for audit trail"
    )

    # Use exactly ONE settings style depending on version
    # Check for local .env first, then production path
    import os as _os
    _env_file = ".env" if _os.path.exists(".env") else "/opt/nicole/.env"
    
    if _HAS_SETTINGS_V2 and SettingsConfigDict is not None:  # pydantic-settings v2
        model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")  # type: ignore
    else:  # pydantic-settings v1
        class Config:
            env_file = _env_file
            extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> AlphawaveSettings:
    """Return cached settings instance."""
    return AlphawaveSettings()  # type: ignore[arg-type]


# alias for import style in other modules
settings = get_settings()

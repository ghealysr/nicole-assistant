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

    # Cloudinary (Images, Screenshots, Uploads)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

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

    # Gemini API
    GEMINI_API_KEY: str = ""
    GEMINI_PRO_MODEL: str = "gemini-3-pro-preview"
    # Imagen models - use the preview versions available in the API
    # See: https://ai.google.dev/gemini-api/docs/imagen
    GEMINI_IMAGE_MODEL: str = "imagen-3.0-generate-001"  # Imagen 3 standard
    GEMINI_IMAGE_MODEL_FAST: str = "imagen-3.0-fast-generate-001"  # Fast version
    # Gemini 3 Pro Image (aka "Nano Banana Pro") - advanced image generation
    # Supports up to 4K, 14 reference images, thinking mode, grounding
    GEMINI_3_PRO_IMAGE_MODEL: str = "gemini-3-pro-image-preview"
    
    # OpenAI GPT Image 1.5 (gpt-image-1) - fastest with precise edits
    OPENAI_IMAGE_MODEL: str = "gpt-image-1"
    
    # PageSpeed Insights API (for Lighthouse scores)
    PAGESPEED_API_KEY: str = "AIzaSyBCHN4ej7qDAwsGhLmZMs_wqd7fi5kSM6c"

    # GitHub Integration (for Vibe deploy)
    GITHUB_TOKEN: str = ""
    GITHUB_ORG: str = "alphawave-sites"  # Organization or username for repos

    # Vercel Integration (for Vibe deploy)
    VERCEL_TOKEN: str = ""
    VERCEL_TEAM_ID: str = ""  # Optional team ID

    # =========================================================================
    # NICOLE INTELLIGENCE CONFIGURATION
    # =========================================================================
    
    # Extended Thinking (Claude-style reasoning)
    EXTENDED_THINKING_ENABLED: bool = True
    EXTENDED_THINKING_BUDGET: int = 8000  # Tokens for thinking
    
    # Agent Tools
    AGENT_TOOLS_ENABLED: bool = True
    MAX_TOOL_ITERATIONS: int = 10
    
    # Memory System
    MEMORY_MIN_CONTENT_LENGTH: int = 10
    MEMORY_MAX_DAILY_PER_USER: int = 100
    MEMORY_SIMILARITY_THRESHOLD: float = 0.85
    MEMORY_RELATIONSHIP_THRESHOLD: float = 0.6
    
    # Memory Decay Settings
    MEMORY_DECAY_DAYS_THRESHOLD: int = 30
    MEMORY_DECAY_AMOUNT: float = 0.03
    MEMORY_MIN_CONFIDENCE: float = 0.10
    MEMORY_ARCHIVE_THRESHOLD: float = 0.15
    
    # Conversation Settings
    CONVERSATION_HISTORY_LIMIT: int = 15  # Reduced from 25 to prevent token overflow
    MEMORY_SEARCH_LIMIT: int = 10
    MEMORY_SEARCH_MIN_CONFIDENCE: float = 0.3
    
    # Token Management - Prevent prompt overflow
    # Claude 3.5 Sonnet has 200K token context, but we need to leave room for:
    # - System prompt (~5K tokens)
    # - Tool definitions (~10K tokens)
    # - Extended thinking budget (8K tokens)
    # - Response generation (4K tokens)
    # So max input should be ~173K tokens = ~690K chars, but we use conservative limits
    MAX_MESSAGE_CHARS: int = 10000  # Truncate individual messages over this length (~2.5K tokens)
    MAX_TOTAL_HISTORY_CHARS: int = 50000  # Max chars for all history combined (~12.5K tokens)
    
    # Skill Activation
    SKILL_ACTIVATION_THRESHOLD: float = 5.0

    class Config:
        env_file = ".env" if os.path.exists(".env") else "/opt/nicole/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

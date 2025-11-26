"""
NICOLE V7 - COMPREHENSIVE ENVIRONMENT VARIABLES DOCUMENTATION
============================================================

This file documents all environment variables required for Nicole V7.
Copy the values to your .env file (backend) and .env.local file (frontend).

DO NOT commit .env files to version control - they contain sensitive API keys.

Generated from comprehensive project review on October 22, 2025.
"""

# ==============================================
# CORE APPLICATION SETTINGS
# ==============================================

ENVIRONMENT = "development"  # Options: development, staging, production
FRONTEND_URL = "http://localhost:3000"  # Frontend URL for auth redirects

# ==============================================
# SUPABASE DATABASE & AUTHENTICATION
# ==============================================
# Get these from: https://supabase.com/dashboard

SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Safe for frontend
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Backend only
SUPABASE_JWT_SECRET = "your-jwt-secret-here"  # From Supabase auth settings

# ==============================================
# CACHING & VECTOR DATABASE
# ==============================================

REDIS_URL = "redis://localhost:6379"  # Redis for hot cache
QDRANT_URL = "http://localhost:6333"  # Qdrant for vector embeddings

# ==============================================
# AI SERVICE PROVIDERS
# ==============================================

# Anthropic Claude API Key (primary LLM)
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY = "sk-ant-api03-..."

# OpenAI API Key (embeddings and O1-mini research)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY = "sk-proj-..."

# ==============================================
# VOICE & MEDIA SERVICES
# ==============================================

# ElevenLabs API Key for Nicole's voice
# Get from: https://elevenlabs.io/app/settings/api-keys
ELEVENLABS_API_KEY = "your-elevenlabs-api-key"

# ElevenLabs voice ID for Nicole's cloned voice
# Get from: https://elevenlabs.io/app/voice-lab
NICOLE_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# ==============================================
# IMAGE & DOCUMENT PROCESSING
# ==============================================

# Replicate API Token (FLUX Pro & Whisper)
# Get from: https://replicate.com/account/api-tokens
REPLICATE_API_TOKEN = "r8_..."

# Azure Computer Vision
# Get from: https://portal.azure.com/
AZURE_VISION_KEY = "your-azure-vision-key"
AZURE_VISION_ENDPOINT = "https://your-resource.cognitiveservices.azure.com/"

# Azure Document Intelligence
AZURE_DOCUMENT_KEY = "your-azure-document-key"
AZURE_DOCUMENT_ENDPOINT = "https://your-resource.cognitiveservices.azure.com/"

# ==============================================
# FILE UPLOAD & STORAGE
# ==============================================

# UploadThing (drag-drop uploads)
# Get from: https://uploadthing.com/dashboard
UPLOADTHING_APP_ID = "your-uploadthing-app-id"
UPLOADTHING_SECRET = "sk_live_..."

# Digital Ocean Spaces (CDN & backup)
# Get from: https://cloud.digitalocean.com/spaces
DO_SPACES_ENDPOINT = "https://nyc3.digitaloceanspaces.com"
DO_SPACES_BUCKET = "nicole-v7-files"
DO_SPACES_BACKUP_BUCKET = "nicole-v7-backups"
DO_SPACES_ACCESS_KEY = "DO00..."
DO_SPACES_SECRET_KEY = "your-secret-key"

# ==============================================
# EXTERNAL INTEGRATIONS
# ==============================================

# Telegram Bot
# Get from: https://t.me/BotFather
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
GLEN_TELEGRAM_CHAT_ID = "123456789"

# Notion Integration
# Get from: https://developers.notion.com/
NOTION_API_KEY = "secret_..."
NOTION_GLEN_WORKSPACE_ID = "your-workspace-id"

# Spotify Integration
# Get from: https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = "your-spotify-client-id"
SPOTIFY_CLIENT_SECRET = "your-spotify-client-secret"

# ==============================================
# SECURITY & AUTHENTICATION
# ==============================================

JWT_SECRET_KEY = "your-custom-jwt-secret-key-here"  # Optional fallback
SESSION_SECRET = "your-session-secret-here"  # For session management
ALLOWED_USERS = "glen@alphawavetech.com,son1@alphawavetech.com"  # Optional access control

# ==============================================
# MONITORING & LOGGING
# ==============================================

# Sentry DSN for error tracking
# Get from: https://sentry.io/settings/projects/nicole-v7/keys/
SENTRY_DSN = "https://your-sentry-dsn@sentry.io/project-id"

# ==============================================
# FRONTEND ENVIRONMENT VARIABLES
# ==============================================
# Place these in frontend/.env.local

NEXT_PUBLIC_SUPABASE_URL = "https://your-project-id.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# ==============================================
# SETUP INSTRUCTIONS
# ==============================================

def get_setup_instructions():
    """Return setup instructions for environment variables."""
    return """
    SETUP INSTRUCTIONS:
    ===================

    1. BACKEND (.env file in /backend/):
       - Copy all variables from SUPABASE_URL through SENTRY_DSN
       - Get API keys from respective services
       - Replace placeholder values with actual credentials

    2. FRONTEND (.env.local file in /frontend/):
       - Copy NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
       - These are safe to expose (anon key only)

    3. REQUIRED SERVICES TO SET UP:
       - Supabase project (database & auth)
       - Redis instance (Docker or cloud)
       - Qdrant instance (Docker or cloud)
       - All API keys from providers listed above

    4. DEVELOPMENT:
       - Set ENVIRONMENT=development
       - Use localhost URLs for services

    5. PRODUCTION:
       - Set ENVIRONMENT=production
       - Update all URLs to production domains
       - Ensure all API keys are production credentials

    SECURITY NOTES:
    ==============
    - Never commit .env files to version control
    - Use different API keys for development vs production
    - Rotate API keys regularly
    - Monitor API usage and costs
    """

# ==============================================
# VALIDATION FUNCTION
# ==============================================

def validate_env_vars():
    """Validate that all required environment variables are set."""
    import os

    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_ROLE_KEY',
        'SUPABASE_JWT_SECRET',
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'REDIS_URL',
        'QDRANT_URL'
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False

    print("✅ All required environment variables are set!")
    return True

if __name__ == "__main__":
    print("Nicole V7 - Environment Variables Documentation")
    print("=" * 50)
    print(get_setup_instructions())
    print("\nValidation Result:")
    validate_env_vars()

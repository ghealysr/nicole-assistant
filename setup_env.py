#!/usr/bin/env python3
"""
NICOLE V7 - Environment Setup Script
===================================

This script helps set up environment variables for Nicole V7.
Run this script to create template .env files and validate configuration.

Usage:
    python3 setup_env.py

Author: Agent 2 (Frontend & UI/UX Engineer)
Date: October 22, 2025
"""

import os
import json
from pathlib import Path

def create_backend_env_template():
    """Create .env template for backend."""
    backend_env = """# ==============================================
# NICOLE V7 - BACKEND ENVIRONMENT VARIABLES
# ==============================================

# Core Application
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000

# Supabase Database & Auth
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here

# Caching & Vector DB
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# AI Services
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key

# Voice Services
ELEVENLABS_API_KEY=your-elevenlabs-api-key
NICOLE_VOICE_ID=your-voice-id

# Image & Document Processing
REPLICATE_API_TOKEN=your-replicate-token
AZURE_VISION_KEY=your-azure-vision-key
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_KEY=your-azure-document-key
AZURE_DOCUMENT_ENDPOINT=https://your-resource.cognitiveservices.azure.com/

# File Storage
UPLOADTHING_APP_ID=your-uploadthing-app-id
UPLOADTHING_SECRET=your-uploadthing-secret
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=nicole-v7-files
DO_SPACES_ACCESS_KEY=your-do-spaces-key
DO_SPACES_SECRET_KEY=your-do-spaces-secret

# External Integrations
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
GLEN_TELEGRAM_CHAT_ID=your-chat-id
NOTION_API_KEY=your-notion-api-key
NOTION_GLEN_WORKSPACE_ID=your-workspace-id
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret

# Security
JWT_SECRET_KEY=your-jwt-secret
SESSION_SECRET=your-session-secret
ALLOWED_USERS=your-email@example.com

# Monitoring
SENTRY_DSN=your-sentry-dsn
"""

    env_path = Path("backend/.env")
    if not env_path.exists():
        env_path.write_text(backend_env)
        print(f"✅ Created backend/.env template")
    else:
        print(f"⚠️  backend/.env already exists")

def create_frontend_env_template():
    """Create .env.local template for frontend."""
    frontend_env = """# ==============================================
# NICOLE V7 - FRONTEND ENVIRONMENT VARIABLES
# ==============================================

NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
"""

    env_path = Path("frontend/.env.local")
    if not env_path.exists():
        env_path.write_text(frontend_env)
        print(f"✅ Created frontend/.env.local template")
    else:
        print(f"⚠️  frontend/.env.local already exists")

def validate_configuration():
    """Validate current environment configuration."""
    print("\n🔍 Validating Configuration...")

    required_vars = [
        'SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY',
        'SUPABASE_JWT_SECRET', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY',
        'REDIS_URL', 'QDRANT_URL'
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        print("💡 Run this script to create template files, then fill in your values")
    else:
        print("✅ All required environment variables are configured!")

def main():
    """Main setup function."""
    print("🚀 Nicole V7 - Environment Setup")
    print("=" * 40)

    # Create template files
    create_backend_env_template()
    create_frontend_env_template()

    # Validate configuration
    validate_configuration()

    print("\n📋 Next Steps:")
    print("1. Edit backend/.env with your actual API keys")
    print("2. Edit frontend/.env.local with your Supabase credentials")
    print("3. Run: docker-compose up -d (for Redis & Qdrant)")
    print("4. Run: python3 scripts/alphawave_init_qdrant.py")
    print("5. Test: python3 -c 'from app.config import settings; print(\"Config loaded!\")'")

    print("\n🔗 API Key Setup Links:")
    print("- Supabase: https://supabase.com/dashboard")
    print("- Anthropic: https://console.anthropic.com/")
    print("- OpenAI: https://platform.openai.com/api-keys")
    print("- ElevenLabs: https://elevenlabs.io/app/settings/api-keys")
    print("- Replicate: https://replicate.com/account/api-tokens")

if __name__ == "__main__":
    main()

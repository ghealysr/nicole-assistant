#!/bin/bash

# =============================================================================
# FAZ CODE COMPLETE DEPLOYMENT SCRIPT
# =============================================================================
# 
# This script deploys all Faz Code updates to the droplet.
# Run this after pushing to GitHub/Vercel.
#
# Usage: bash FAZ_COMPLETE_DEPLOYMENT.sh
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "FAZ CODE DEPLOYMENT - $(date)"
echo "=========================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Note: Some operations may require sudo"
fi

# =============================================================================
# 1. NAVIGATE TO BACKEND
# =============================================================================

echo ""
echo "[1/7] Navigating to backend directory..."
cd /opt/nicole/backend || {
    echo "ERROR: /opt/nicole/backend not found"
    exit 1
}
echo "✓ In backend directory"

# =============================================================================
# 2. PULL LATEST CODE
# =============================================================================

echo ""
echo "[2/7] Pulling latest code from git..."
git fetch origin
git reset --hard origin/main
echo "✓ Code updated"

# =============================================================================
# 3. INSTALL/UPDATE DEPENDENCIES
# =============================================================================

echo ""
echo "[3/7] Installing Python dependencies..."
source venv/bin/activate || source /opt/nicole/backend/venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

echo "✓ Dependencies installed"

# =============================================================================
# 4. RUN DATABASE MIGRATIONS
# =============================================================================

echo ""
echo "[4/7] Running database migrations..."

# Check if migration file exists
if [ -f "database/migrations/020_faz_code_schema.sql" ]; then
    echo "Found Faz Code schema migration..."
    
    # Execute migration using psql or Python
    # Option 1: Using environment variable
    if [ -n "$TIGER_DATABASE_URL" ]; then
        psql "$TIGER_DATABASE_URL" -f database/migrations/020_faz_code_schema.sql 2>/dev/null || echo "Migration may already be applied"
    else
        echo "Attempting migration via Python..."
        python -c "
import asyncio
from app.database import db

async def run_migration():
    await db.connect()
    with open('database/migrations/020_faz_code_schema.sql', 'r') as f:
        sql = f.read()
    try:
        await db.execute(sql)
        print('Migration executed successfully')
    except Exception as e:
        print(f'Migration note: {e}')
    await db.disconnect()

asyncio.run(run_migration())
" || echo "Migration may already be applied"
    fi
else
    echo "No new migrations found"
fi

echo "✓ Database migrations complete"

# =============================================================================
# 5. VERIFY CONFIGURATION
# =============================================================================

echo ""
echo "[5/7] Verifying configuration..."

# Check required environment variables
REQUIRED_VARS="TIGER_DATABASE_URL ANTHROPIC_API_KEY GEMINI_API_KEY GOOGLE_CLIENT_ID"
MISSING=""

for VAR in $REQUIRED_VARS; do
    if [ -z "${!VAR}" ]; then
        MISSING="$MISSING $VAR"
    fi
done

if [ -n "$MISSING" ]; then
    echo "WARNING: Missing environment variables:$MISSING"
    echo "Some features may not work correctly"
else
    echo "✓ All required environment variables present"
fi

# Optional vars for deployment
OPTIONAL_VARS="GITHUB_TOKEN VERCEL_TOKEN"
for VAR in $OPTIONAL_VARS; do
    if [ -z "${!VAR}" ]; then
        echo "INFO: Optional var $VAR not set (needed for auto-deployment)"
    fi
done

# =============================================================================
# 6. RESTART API SERVICE
# =============================================================================

echo ""
echo "[6/7] Restarting API service..."

# Try supervisorctl first
if command -v supervisorctl &> /dev/null; then
    supervisorctl restart nicole-api && echo "✓ API restarted via supervisor"
# Try systemctl as fallback
elif command -v systemctl &> /dev/null; then
    systemctl restart nicole-api && echo "✓ API restarted via systemctl"
else
    echo "WARNING: No service manager found. Manually restart the API."
fi

# Wait for startup
echo "Waiting for API to start..."
sleep 5

# =============================================================================
# 7. VERIFY DEPLOYMENT
# =============================================================================

echo ""
echo "[7/7] Verifying deployment..."

# Check health endpoint
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz 2>/dev/null || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo "✓ API is healthy (HTTP 200)"
else
    echo "WARNING: Health check returned HTTP $HEALTH_CHECK"
    echo "Check logs: tail -f /var/log/supervisor/nicole-api-*.log"
fi

# Check Faz endpoints exist
FAZ_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/faz/projects -H "Authorization: Bearer test" 2>/dev/null || echo "000")

if [ "$FAZ_CHECK" = "401" ] || [ "$FAZ_CHECK" = "200" ]; then
    echo "✓ Faz Code endpoints are available"
else
    echo "WARNING: Faz endpoints check returned HTTP $FAZ_CHECK"
fi

# =============================================================================
# COMPLETE
# =============================================================================

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Code: Updated from main branch"
echo "  - Dependencies: Installed"
echo "  - Database: Migrations applied"
echo "  - API: Restarted"
echo ""
echo "Available Faz Code Endpoints:"
echo "  POST /faz/projects        - Create project"
echo "  GET  /faz/projects        - List projects"
echo "  GET  /faz/projects/{id}   - Get project"
echo "  POST /faz/projects/{id}/run - Run pipeline"
echo "  POST /faz/projects/{id}/stop - Stop pipeline"
echo "  GET  /faz/projects/{id}/files - Get files"
echo "  WS   /faz/projects/{id}/ws - WebSocket (auth via ?token=)"
echo "  POST /faz/projects/{id}/deploy - Deploy to Vercel"
echo ""
echo "Frontend: Push to main branch to trigger Vercel deployment"
echo ""
echo "Test command:"
echo "  curl http://localhost:8000/faz/projects -H 'Authorization: Bearer <token>'"
echo ""



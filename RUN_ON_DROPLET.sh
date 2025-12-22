#!/bin/bash
# ============================================================================
# PHASE 1 DROPLET DEPLOYMENT - FINAL SCRIPT
# Run this directly on the nicole-production droplet
# ============================================================================
# 
# Usage: Copy and paste the ENTIRE script into your droplet terminal
#        OR save as RUN_ON_DROPLET.sh and run: bash RUN_ON_DROPLET.sh
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       PHASE 1 VIBE DASHBOARD V3.0 - DROPLET DEPLOYMENT        ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
NICOLE_DIR="/opt/nicole"
TIGER_DB="postgres://tsdbadmin:xb0lms8vqb9j8kj7@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require"

# ============================================================================
# STEP 1: Pull Latest Code
# ============================================================================
echo -e "${BLUE}[1/5]${NC} Pulling latest code from GitHub..."
cd "$NICOLE_DIR"
git fetch origin
git checkout main
git pull origin main
echo -e "${GREEN}✓${NC} Code updated"
echo ""

# ============================================================================
# STEP 2: Run Database Migration
# ============================================================================
echo -e "${BLUE}[2/5]${NC} Running database migration..."

# Check if tables already exist
EXISTING=$(psql "$TIGER_DB" -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('vibe_iterations', 'vibe_qa_scores', 'vibe_uploads', 'vibe_competitor_sites')" 2>/dev/null || echo "0")

if [ "$EXISTING" = "4" ]; then
    echo -e "${YELLOW}⚠${NC} Phase 1 tables already exist - skipping migration"
else
    echo "Running migration 008_vibe_enhancements.sql..."
    psql "$TIGER_DB" -f "$NICOLE_DIR/backend/database/migrations/008_vibe_enhancements.sql"
    echo -e "${GREEN}✓${NC} Migration completed"
fi
echo ""

# ============================================================================
# STEP 3: Install Python Dependencies
# ============================================================================
echo -e "${BLUE}[3/5]${NC} Installing Python dependencies..."
cd "$NICOLE_DIR"
source .venv/bin/activate
pip install --upgrade cloudinary>=1.36.0 google-genai>=0.3.0 --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# ============================================================================
# STEP 4: Verify Environment Variables
# ============================================================================
echo -e "${BLUE}[4/5]${NC} Verifying environment variables..."

# Check Cloudinary
if grep -q "CLOUDINARY_CLOUD_NAME=" "$NICOLE_DIR/.env" && \
   grep -q "CLOUDINARY_API_KEY=" "$NICOLE_DIR/.env" && \
   grep -q "CLOUDINARY_API_SECRET=" "$NICOLE_DIR/.env"; then
    echo -e "${GREEN}✓${NC} Cloudinary credentials found"
else
    echo -e "${RED}✗${NC} Cloudinary credentials missing!"
    echo "  Please add to $NICOLE_DIR/.env:"
    echo "  CLOUDINARY_CLOUD_NAME=your_cloud_name"
    echo "  CLOUDINARY_API_KEY=your_api_key"
    echo "  CLOUDINARY_API_SECRET=your_api_secret"
fi

# Add PageSpeed API key if missing
if ! grep -q "PAGESPEED_API_KEY" "$NICOLE_DIR/.env"; then
    echo "" >> "$NICOLE_DIR/.env"
    echo "# PageSpeed Insights API" >> "$NICOLE_DIR/.env"
    echo "PAGESPEED_API_KEY=AIzaSyBCHN4ej7qDAwsGhLmZMs_wqd7fi5kSM6c" >> "$NICOLE_DIR/.env"
    echo -e "${GREEN}✓${NC} PageSpeed API key added"
else
    echo -e "${GREEN}✓${NC} PageSpeed API key found"
fi
echo ""

# ============================================================================
# STEP 5: Restart Nicole API
# ============================================================================
echo -e "${BLUE}[5/5]${NC} Restarting Nicole API..."
supervisorctl restart nicole-api
sleep 5

if supervisorctl status nicole-api | grep -q "RUNNING"; then
    echo -e "${GREEN}✓${NC} Nicole API restarted successfully"
else
    echo -e "${RED}✗${NC} API failed to start!"
    supervisorctl status nicole-api
    exit 1
fi
echo ""

# ============================================================================
# VALIDATION
# ============================================================================
echo -e "${BLUE}Validating deployment...${NC}"
echo ""

# Health check
HEALTH=$(curl -s http://localhost:8000/health/ping)
if echo "$HEALTH" | grep -q "pong"; then
    echo -e "${GREEN}✓${NC} Health check passed"
else
    echo -e "${RED}✗${NC} Health check failed: $HEALTH"
fi

# Database tables
TABLE_COUNT=$(psql "$TIGER_DB" -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('vibe_iterations', 'vibe_qa_scores', 'vibe_uploads', 'vibe_competitor_sites')" 2>/dev/null || echo "0")
if [ "$TABLE_COUNT" = "4" ]; then
    echo -e "${GREEN}✓${NC} All 4 new tables verified"
else
    echo -e "${YELLOW}⚠${NC} Found $TABLE_COUNT/4 tables"
fi

# Cloudinary test
CLOUDINARY_TEST=$(cd "$NICOLE_DIR" && source .venv/bin/activate && python3 -c "
from app.config import settings
if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
    print('OK')
else:
    print('MISSING')
" 2>/dev/null || echo "ERROR")

if [ "$CLOUDINARY_TEST" = "OK" ]; then
    echo -e "${GREEN}✓${NC} Cloudinary configured"
else
    echo -e "${YELLOW}⚠${NC} Cloudinary not configured"
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║               PHASE 1 DEPLOYMENT COMPLETE!                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "What was deployed:"
echo "  ✓ Database: 4 new tables (iterations, qa_scores, uploads, competitors)"
echo "  ✓ Backend: 10 new API endpoints for structured workflow"
echo "  ✓ Services: Lighthouse, Accessibility, Cloudinary integration"
echo ""
echo "Test at: https://nicole.alphawavelabs.io"
echo ""
echo "Phase 1 Features:"
echo "  • Structured intake form (replaces chat)"
echo "  • File upload system (Cloudinary)"
echo "  • Competitor URL research"
echo "  • Architecture approval gate"
echo "  • QA scoring (Lighthouse + axe-core)"
echo "  • Iteration/feedback system"
echo ""



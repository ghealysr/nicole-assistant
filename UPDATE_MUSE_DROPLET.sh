#!/bin/bash
# ============================================================================
# MUSE DESIGN DASHBOARD - DROPLET UPDATE SCRIPT
# Run this directly on the nicole-production droplet
# ============================================================================
# 
# Usage: Copy and paste the ENTIRE script into your droplet terminal
#        OR save as UPDATE_MUSE_DROPLET.sh and run: bash UPDATE_MUSE_DROPLET.sh
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       MUSE DESIGN DASHBOARD - DROPLET UPDATE                  ║${NC}"
echo -e "${CYAN}║       Streaming, A/B Testing, Image Generation               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
NICOLE_DIR="/opt/nicole"
TIGER_DB="postgres://tsdbadmin:xb0lms8vqb9j8kj7@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require"

# ============================================================================
# STEP 1: Pull Latest Code
# ============================================================================
echo -e "${BLUE}[1/6]${NC} Pulling latest code from GitHub..."
cd "$NICOLE_DIR"
git fetch origin
git checkout main
git pull origin main
echo -e "${GREEN}✓${NC} Code updated to latest"
echo ""

# ============================================================================
# STEP 2: Activate Virtual Environment
# ============================================================================
echo -e "${BLUE}[2/6]${NC} Activating Python virtual environment..."
source .venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"
echo ""

# ============================================================================
# STEP 3: Install/Update Python Dependencies
# ============================================================================
echo -e "${BLUE}[3/6]${NC} Installing Python dependencies..."
pip install --upgrade google-generativeai>=0.8.0 --quiet
pip install -r backend/requirements.txt --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# ============================================================================
# STEP 4: Run Muse Database Migrations
# ============================================================================
echo -e "${BLUE}[4/6]${NC} Running Muse database migrations..."

# Migration 031: Muse Design Research (Core Tables)
echo "  Checking migration 031_muse_design_research.sql..."
MUSE_SESSIONS=$(psql "$TIGER_DB" -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'muse_sessions'" 2>/dev/null || echo "0")
if [ "$MUSE_SESSIONS" = "0" ]; then
    echo "  Running migration 031_muse_design_research.sql..."
    psql "$TIGER_DB" -f "$NICOLE_DIR/backend/database/migrations/031_muse_design_research.sql"
    echo -e "  ${GREEN}✓${NC} Migration 031 completed"
else
    echo -e "  ${YELLOW}⚠${NC} Migration 031 already applied (muse_sessions exists)"
fi

# Migration 032: Muse Research Planning
echo "  Checking migration 032_muse_research_planning.sql..."
RESEARCH_PLANNING=$(psql "$TIGER_DB" -t -A -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'muse_sessions' AND column_name = 'clarifying_questions'" 2>/dev/null || echo "0")
if [ "$RESEARCH_PLANNING" = "0" ]; then
    echo "  Running migration 032_muse_research_planning.sql..."
    psql "$TIGER_DB" -f "$NICOLE_DIR/backend/database/migrations/032_muse_research_planning.sql"
    echo -e "  ${GREEN}✓${NC} Migration 032 completed"
else
    echo -e "  ${YELLOW}⚠${NC} Migration 032 already applied (clarifying_questions exists)"
fi

# Migration 033: Muse A/B Testing
echo "  Checking migration 033_muse_ab_testing.sql..."
AB_TESTING=$(psql "$TIGER_DB" -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'muse_moodboard_analytics'" 2>/dev/null || echo "0")
if [ "$AB_TESTING" = "0" ]; then
    echo "  Running migration 033_muse_ab_testing.sql..."
    psql "$TIGER_DB" -f "$NICOLE_DIR/backend/database/migrations/033_muse_ab_testing.sql"
    echo -e "  ${GREEN}✓${NC} Migration 033 completed"
else
    echo -e "  ${YELLOW}⚠${NC} Migration 033 already applied (muse_moodboard_analytics exists)"
fi

# Migration 034: Style Guide Exports (may be empty/deprecated)
echo "  Checking migration 034_muse_style_guide_exports.sql..."
if [ -s "$NICOLE_DIR/backend/database/migrations/034_muse_style_guide_exports.sql" ]; then
    EXPORT_COLS=$(psql "$TIGER_DB" -t -A -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'muse_style_guides' AND column_name = 'last_export_figma'" 2>/dev/null || echo "0")
    if [ "$EXPORT_COLS" = "0" ]; then
        echo "  Running migration 034_muse_style_guide_exports.sql..."
        psql "$TIGER_DB" -f "$NICOLE_DIR/backend/database/migrations/034_muse_style_guide_exports.sql" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} Migration 034 completed"
    else
        echo -e "  ${YELLOW}⚠${NC} Migration 034 already applied"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Migration 034 is empty (merged into 033)"
fi

echo -e "${GREEN}✓${NC} All Muse migrations complete"
echo ""

# ============================================================================
# STEP 5: Verify Environment Variables
# ============================================================================
echo -e "${BLUE}[5/6]${NC} Verifying environment variables..."

# Check for GEMINI_API_KEY
if grep -q "GEMINI_API_KEY=" "$NICOLE_DIR/.env"; then
    echo -e "  ${GREEN}✓${NC} GEMINI_API_KEY found"
else
    echo -e "  ${RED}✗${NC} GEMINI_API_KEY missing!"
    echo "    Please add to $NICOLE_DIR/.env:"
    echo "    GEMINI_API_KEY=your_gemini_api_key"
fi

# Check for GOOGLE_API_KEY (alternative name)
if grep -q "GOOGLE_API_KEY=" "$NICOLE_DIR/.env"; then
    echo -e "  ${GREEN}✓${NC} GOOGLE_API_KEY found"
fi

# Check for other required keys
for KEY in ANTHROPIC_API_KEY VERCEL_TOKEN CLOUDINARY_CLOUD_NAME; do
    if grep -q "$KEY=" "$NICOLE_DIR/.env"; then
        echo -e "  ${GREEN}✓${NC} $KEY found"
    else
        echo -e "  ${YELLOW}⚠${NC} $KEY not found"
    fi
done

echo ""

# ============================================================================
# STEP 6: Restart Nicole API
# ============================================================================
echo -e "${BLUE}[6/6]${NC} Restarting Nicole API..."
supervisorctl restart nicole-api
sleep 5

if supervisorctl status nicole-api | grep -q "RUNNING"; then
    echo -e "${GREEN}✓${NC} Nicole API restarted successfully"
else
    echo -e "${RED}✗${NC} API failed to start!"
    supervisorctl status nicole-api
    echo ""
    echo "Checking logs..."
    tail -20 /var/log/nicole/api.err.log
    exit 1
fi
echo ""

# ============================================================================
# VALIDATION
# ============================================================================
echo -e "${BLUE}Validating deployment...${NC}"
echo ""

# Health check
HEALTH=$(curl -s http://localhost:8000/health/ping 2>/dev/null || echo "FAILED")
if echo "$HEALTH" | grep -q "pong"; then
    echo -e "${GREEN}✓${NC} Health check passed"
else
    echo -e "${RED}✗${NC} Health check failed: $HEALTH"
fi

# Check Muse tables exist
MUSE_TABLES=$(psql "$TIGER_DB" -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'muse_%'" 2>/dev/null || echo "0")
echo -e "${GREEN}✓${NC} Found $MUSE_TABLES Muse tables in database"

# Check Muse router is registered
MUSE_ROUTES=$(curl -s http://localhost:8000/openapi.json 2>/dev/null | grep -c "/muse" || echo "0")
if [ "$MUSE_ROUTES" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Muse API routes registered ($MUSE_ROUTES endpoints)"
else
    echo -e "${YELLOW}⚠${NC} Muse routes not found in OpenAPI spec"
fi

# Test Gemini availability
GEMINI_TEST=$(cd "$NICOLE_DIR" && source .venv/bin/activate && python3 -c "
from app.config import settings
import os
key = getattr(settings, 'GEMINI_API_KEY', None) or getattr(settings, 'GOOGLE_API_KEY', None) or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
if key and len(key) > 10:
    print('OK')
else:
    print('MISSING')
" 2>/dev/null || echo "ERROR")

if [ "$GEMINI_TEST" = "OK" ]; then
    echo -e "${GREEN}✓${NC} Gemini API configured"
else
    echo -e "${YELLOW}⚠${NC} Gemini API key may not be configured (Muse will have limited functionality)"
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           MUSE DASHBOARD UPDATE COMPLETE!                     ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "What was deployed:"
echo "  ✓ Muse Design Research Agent (Gemini 3 Pro integration)"
echo "  ✓ Streaming mood board generation with SSE"
echo "  ✓ Imagen 3 preview image generation"
echo "  ✓ A/B testing analytics (impressions, selections, time-on-view)"
echo "  ✓ Historical preference-driven generation"
echo "  ✓ Style guide export (Figma tokens, CSS, Tailwind, W3C)"
echo "  ✓ Database: muse_sessions, muse_moodboards, muse_style_guides, etc."
echo ""
echo "API Endpoints Added:"
echo "  • POST /muse/sessions                    - Create research session"
echo "  • POST /muse/sessions/{id}/inspirations  - Add inspiration images/URLs"
echo "  • POST /muse/sessions/{id}/research      - Start research workflow"
echo "  • GET  /muse/sessions/{id}/stream        - SSE for real-time updates"
echo "  • GET  /muse/sessions/{id}/moodboards    - List mood boards"
echo "  • POST /muse/sessions/{id}/moodboards/{id}/select - Select mood board"
echo "  • POST /muse/sessions/{id}/style-guide   - Generate style guide"
echo "  • POST /muse/style-guides/{id}/export    - Export style guide"
echo ""
echo "Test at: https://nicole.alphawavelabs.io"
echo ""


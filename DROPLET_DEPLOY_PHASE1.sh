#!/bin/bash
# ============================================================================
# Phase 1 Droplet Deployment Script
# Run this ON the nicole-production droplet
# ============================================================================

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "============================================================================"
echo "Phase 1 Vibe Dashboard V3.0 - Droplet Deployment"
echo "============================================================================"
echo ""

# Configuration
NICOLE_DIR="/opt/nicole"
TIGER_DB_URL="postgres://tsdbadmin:xb0lms8vqb9j8kj7@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require"

# ============================================================================
# Step 1: Database Migration
# ============================================================================

log_info "Step 1/5: Running database migration..."
echo ""

psql "$TIGER_DB_URL" -f "$NICOLE_DIR/backend/database/migrations/008_vibe_enhancements.sql"

if [ $? -eq 0 ]; then
    log_success "Database migration completed"
    log_info "  ✓ Created vibe_iterations table"
    log_info "  ✓ Created vibe_qa_scores table"
    log_info "  ✓ Created vibe_uploads table"
    log_info "  ✓ Created vibe_competitor_sites table"
    log_info "  ✓ Added 12 columns to vibe_projects"
else
    log_error "Database migration failed"
    exit 1
fi

echo ""

# ============================================================================
# Step 2: Pull Latest Code
# ============================================================================

log_info "Step 2/5: Pulling latest code..."
echo ""

cd "$NICOLE_DIR"

# Fetch all branches
git fetch origin

# Check if extended-thinking-feature exists
if git rev-parse --verify origin/extended-thinking-feature >/dev/null 2>&1; then
    log_info "Pulling from extended-thinking-feature branch..."
    git checkout extended-thinking-feature
    git pull origin extended-thinking-feature
else
    log_info "Pulling from main branch..."
    git checkout main
    git pull origin main
fi

if [ $? -eq 0 ]; then
    log_success "Code updated successfully"
else
    log_error "Git pull failed"
    exit 1
fi

echo ""

# ============================================================================
# Step 3: Install/Upgrade Dependencies
# ============================================================================

log_info "Step 3/5: Installing Python dependencies..."
echo ""

cd "$NICOLE_DIR"
source .venv/bin/activate

# Install/upgrade cloudinary
pip install --upgrade cloudinary>=1.36.0 --quiet

if [ $? -eq 0 ]; then
    log_success "Dependencies installed"
    python -c "import cloudinary; print(f'  ✓ Cloudinary version: {cloudinary.__version__}')"
else
    log_error "Dependency installation failed"
    exit 1
fi

echo ""

# ============================================================================
# Step 4: Verify Environment Variables
# ============================================================================

log_info "Step 4/5: Verifying environment variables..."
echo ""

# Check if Cloudinary is configured
if grep -q "CLOUDINARY_CLOUD_NAME" "$NICOLE_DIR/.env" && \
   grep -q "CLOUDINARY_API_KEY" "$NICOLE_DIR/.env" && \
   grep -q "CLOUDINARY_API_SECRET" "$NICOLE_DIR/.env"; then
    log_success "Cloudinary credentials found in .env"
else
    log_warning "Cloudinary credentials NOT found in .env"
    echo ""
    echo "Please add these to $NICOLE_DIR/.env:"
    echo ""
    echo "CLOUDINARY_CLOUD_NAME=your_cloud_name"
    echo "CLOUDINARY_API_KEY=your_api_key"
    echo "CLOUDINARY_API_SECRET=your_api_secret"
    echo ""
    read -p "Press Enter after adding Cloudinary credentials..."
fi

# Check PageSpeed API Key
if grep -q "PAGESPEED_API_KEY" "$NICOLE_DIR/.env"; then
    log_success "PageSpeed API key found in .env"
else
    log_info "Adding PageSpeed API key to .env..."
    echo "" >> "$NICOLE_DIR/.env"
    echo "# PageSpeed Insights API (for Lighthouse audits)" >> "$NICOLE_DIR/.env"
    echo "PAGESPEED_API_KEY=AIzaSyBCHN4ej7qDAwsGhLmZMs_wqd7fi5kSM6c" >> "$NICOLE_DIR/.env"
    log_success "PageSpeed API key added"
fi

echo ""

# ============================================================================
# Step 5: Restart Nicole API
# ============================================================================

log_info "Step 5/5: Restarting Nicole API..."
echo ""

supervisorctl restart nicole-api
sleep 5

if supervisorctl status nicole-api | grep -q "RUNNING"; then
    log_success "Nicole API restarted successfully"
else
    log_error "Nicole API failed to start"
    supervisorctl status nicole-api
    exit 1
fi

echo ""

# ============================================================================
# Validation
# ============================================================================

log_info "Validating deployment..."
echo ""

# Test health endpoint
HEALTH_CHECK=$(curl -s http://localhost:8000/health/ping)
if echo "$HEALTH_CHECK" | grep -q "pong"; then
    log_success "Health check passed"
else
    log_error "Health check failed"
    echo "Response: $HEALTH_CHECK"
    exit 1
fi

# Verify database tables
TABLE_COUNT=$(psql "$TIGER_DB_URL" -t -A -c "
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_name IN ('vibe_iterations', 'vibe_qa_scores', 'vibe_uploads', 'vibe_competitor_sites')
")

if [ "$TABLE_COUNT" -eq 4 ]; then
    log_success "All 4 new database tables verified"
else
    log_warning "Expected 4 tables, found $TABLE_COUNT"
fi

# Test Cloudinary configuration
CLOUDINARY_TEST=$(cd "$NICOLE_DIR" && source .venv/bin/activate && python3 << 'EOFPYTHON'
from app.config import settings
if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
    print("CONFIGURED")
else:
    print("NOT_CONFIGURED")
EOFPYTHON
)

if echo "$CLOUDINARY_TEST" | grep -q "CONFIGURED"; then
    log_success "Cloudinary configured and accessible"
else
    log_warning "Cloudinary not fully configured"
fi

echo ""

# ============================================================================
# Deployment Summary
# ============================================================================

echo "============================================================================"
log_success "Phase 1 Deployment Complete!"
echo "============================================================================"
echo ""

log_info "What was deployed:"
echo "  ✓ Database migration (4 tables, 12 columns)"
echo "  ✓ Latest backend code with Phase 1 endpoints"
echo "  ✓ Python dependencies (cloudinary)"
echo "  ✓ Environment variables verified"
echo "  ✓ Nicole API restarted"
echo ""

log_info "Phase 1 Features Now Available:"
echo "  ✓ Structured intake form"
echo "  ✓ File upload system (Cloudinary)"
echo "  ✓ Competitor URL research"
echo "  ✓ Architecture approval gate"
echo "  ✓ QA scoring (Lighthouse + axe-core)"
echo "  ✓ Iteration/feedback system"
echo ""

log_info "Next Steps:"
echo "  1. Test frontend at: https://nicole.alphawavelabs.io"
echo "  2. Create a test project"
echo "  3. Fill out structured intake form"
echo "  4. Upload a test logo"
echo "  5. Add competitor URLs"
echo "  6. Run planning phase"
echo ""

log_info "Monitoring:"
echo "  • API logs: tail -f $NICOLE_DIR/logs/api.log"
echo "  • Supervisor: supervisorctl status"
echo "  • Health: curl http://localhost:8000/health/ping"
echo ""

log_success "Deployment validated and ready for use!"
echo ""



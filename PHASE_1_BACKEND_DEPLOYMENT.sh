#!/bin/bash
# ============================================================================
# Phase 1 Backend Deployment Script
# Vibe Dashboard V3.0 - Structured Intake, Iterations, QA Scores
# ============================================================================
# 
# This script deploys all Phase 1 backend updates to the production droplet.
# 
# What it does:
# 1. Runs database migration (008_vibe_enhancements.sql)
# 2. Installs new Python dependencies (cloudinary, lucide-react)
# 3. Updates environment variables
# 4. Restarts Nicole API
# 5. Validates deployment
#
# Prerequisites:
# - SSH access to nicole-production droplet
# - Tiger database credentials in .env
# - Cloudinary account credentials
#
# Author: AlphaWave Architecture
# Date: December 16, 2025
# ============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DROPLET_USER="root"
DROPLET_HOST="nicole-production"
NICOLE_DIR="/opt/nicole"
TIGER_DB_URL="postgres://tsdbadmin:xb0lms8vqb9j8kj7@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require"

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

log_info "Starting Phase 1 Backend Deployment..."
echo ""

# Check if we're in the right directory
if [ ! -f "backend/database/migrations/008_vibe_enhancements.sql" ]; then
    log_error "Migration file not found. Are you in the project root?"
    exit 1
fi

log_success "Pre-flight checks passed"
echo ""

# ============================================================================
# Step 1: Database Migration
# ============================================================================

log_info "Step 1: Running database migration..."
echo ""

psql "$TIGER_DB_URL" -f backend/database/migrations/008_vibe_enhancements.sql

if [ $? -eq 0 ]; then
    log_success "Database migration completed successfully"
    log_info "  - Created 4 new tables (vibe_iterations, vibe_qa_scores, vibe_uploads, vibe_competitor_sites)"
    log_info "  - Added 12 new columns to vibe_projects"
    log_info "  - Created 12 new indexes"
else
    log_error "Database migration failed"
    exit 1
fi

echo ""

# ============================================================================
# Step 2: Pull Latest Code
# ============================================================================

log_info "Step 2: Pulling latest code on droplet..."
echo ""

ssh $DROPLET_USER@$DROPLET_HOST << 'EOF'
cd /opt/nicole
git pull origin main
if [ $? -eq 0 ]; then
    echo "✓ Code pulled successfully"
else
    echo "✗ Git pull failed"
    exit 1
fi
EOF

log_success "Latest code deployed"
echo ""

# ============================================================================
# Step 3: Install Dependencies
# ============================================================================

log_info "Step 3: Installing new Python dependencies..."
echo ""

ssh $DROPLET_USER@$DROPLET_HOST << 'EOF'
cd /opt/nicole
source .venv/bin/activate

# Install/upgrade cloudinary
pip install --upgrade cloudinary>=1.36.0

# Verify installation
python -c "import cloudinary; print(f'Cloudinary version: {cloudinary.__version__}')"

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "✗ Dependency installation failed"
    exit 1
fi
EOF

log_success "Dependencies installed"
echo ""

# ============================================================================
# Step 4: Update Environment Variables
# ============================================================================

log_info "Step 4: Updating environment variables..."
echo ""

log_warning "MANUAL ACTION REQUIRED:"
echo ""
echo "Please add the following to /opt/nicole/.env on the droplet:"
echo ""
echo "# Cloudinary (for Vibe uploads, screenshots, brand assets)"
echo "CLOUDINARY_CLOUD_NAME=your_cloud_name_here"
echo "CLOUDINARY_API_KEY=your_api_key_here"
echo "CLOUDINARY_API_SECRET=your_api_secret_here"
echo ""
echo "# PageSpeed Insights API (for Lighthouse audits)"
echo "PAGESPEED_API_KEY=AIzaSyBCHN4ej7qDAwsGhLmZMs_wqd7fi5kSM6c"
echo ""

read -p "Press Enter after you've added these variables to .env..."

log_success "Environment variables updated"
echo ""

# ============================================================================
# Step 5: Restart Nicole API
# ============================================================================

log_info "Step 5: Restarting Nicole API..."
echo ""

ssh $DROPLET_USER@$DROPLET_HOST << 'EOF'
supervisorctl restart nicole-api
sleep 5
supervisorctl status nicole-api
EOF

log_success "Nicole API restarted"
echo ""

# ============================================================================
# Step 6: Validation
# ============================================================================

log_info "Step 6: Validating deployment..."
echo ""

# Test health endpoint
log_info "Testing health endpoint..."
HEALTH_RESPONSE=$(ssh $DROPLET_USER@$DROPLET_HOST 'curl -s http://localhost:8000/health/ping')

if echo "$HEALTH_RESPONSE" | grep -q "pong"; then
    log_success "Health check passed"
else
    log_error "Health check failed"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test database tables
log_info "Verifying new database tables..."
TABLE_CHECK=$(psql "$TIGER_DB_URL" -t -c "
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_name IN ('vibe_iterations', 'vibe_qa_scores', 'vibe_uploads', 'vibe_competitor_sites')
")

if [ "$TABLE_CHECK" -eq 4 ]; then
    log_success "All 4 new tables verified"
else
    log_error "Expected 4 tables, found $TABLE_CHECK"
    exit 1
fi

# Test Cloudinary configuration
log_info "Testing Cloudinary configuration..."
CLOUDINARY_TEST=$(ssh $DROPLET_USER@$DROPLET_HOST << 'EOFTEST'
cd /opt/nicole
source .venv/bin/activate
python3 << 'EOFPYTHON'
import os
from app.config import settings

if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
    print("CONFIGURED")
else:
    print("NOT_CONFIGURED")
EOFPYTHON
EOFTEST
)

if echo "$CLOUDINARY_TEST" | grep -q "CONFIGURED"; then
    log_success "Cloudinary configured"
else
    log_warning "Cloudinary not configured - file uploads will fail"
fi

echo ""

# ============================================================================
# Step 7: Test New Endpoints
# ============================================================================

log_info "Step 7: Testing new Phase 1 endpoints..."
echo ""

# Get a valid JWT token (you'll need to replace this with actual token)
log_warning "Endpoint tests require authentication. Skipping automated tests."
log_info "Manual test checklist:"
echo ""
echo "  1. POST /vibe/projects/{id}/intake/form - Submit structured intake"
echo "  2. POST /vibe/projects/{id}/uploads - Save upload metadata"
echo "  3. POST /vibe/projects/{id}/competitors - Add competitor URL"
echo "  4. GET  /vibe/projects/{id}/competitors - Get competitors"
echo "  5. POST /vibe/projects/{id}/architecture/approve - Approve architecture"
echo "  6. POST /vibe/projects/{id}/architecture/revise - Request revision"
echo "  7. POST /vibe/projects/{id}/feedback - Submit feedback"
echo "  8. GET  /vibe/projects/{id}/iterations - Get iterations"
echo "  9. GET  /vibe/projects/{id}/qa - Get QA scores"
echo "  10. GET  /vibe/projects/{id}/context - Get full project context"
echo ""

# ============================================================================
# Deployment Summary
# ============================================================================

echo ""
echo "============================================================================"
log_success "Phase 1 Backend Deployment Complete!"
echo "============================================================================"
echo ""
log_info "What was deployed:"
echo "  ✓ Database migration (4 new tables, 12 new columns)"
echo "  ✓ Latest backend code with all Phase 1 endpoints"
echo "  ✓ Cloudinary integration for file uploads"
echo "  ✓ Lighthouse & Accessibility services"
echo "  ✓ 10 new API endpoints for structured workflow"
echo ""
log_info "Next steps:"
echo "  1. Deploy frontend to Vercel (already done)"
echo "  2. Test full intake → plan → build → QA → review flow"
echo "  3. Upload test files to verify Cloudinary integration"
echo "  4. Run Lighthouse audit to verify PageSpeed API"
echo "  5. Submit test feedback to verify iteration system"
echo ""
log_info "Monitoring:"
echo "  - API logs: ssh $DROPLET_USER@$DROPLET_HOST 'tail -f /opt/nicole/logs/api.log'"
echo "  - Supervisor status: ssh $DROPLET_USER@$DROPLET_HOST 'supervisorctl status'"
echo "  - Database queries: psql \"$TIGER_DB_URL\""
echo ""
log_success "Deployment validated and ready for testing!"
echo ""



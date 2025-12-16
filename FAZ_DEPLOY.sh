#!/bin/bash
# ============================================================================
# FAZ CODE DEPLOYMENT SCRIPT
# Run this on the droplet to deploy the Faz Code backend
# ============================================================================

set -e

echo "============================================"
echo "FAZ CODE DEPLOYMENT - $(date)"
echo "============================================"

# Configuration
BACKEND_DIR="/opt/nicole/backend"
MIGRATIONS_DIR="$BACKEND_DIR/database/migrations"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✓ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
log_error() { echo -e "${RED}✗ $1${NC}"; }
log_info() { echo "→ $1"; }

# ============================================================================
# STEP 1: Pull Latest Code
# ============================================================================
echo ""
echo "STEP 1: Pulling latest code..."
cd $BACKEND_DIR
git fetch origin
git checkout main
git pull origin main
log_success "Code pulled successfully"

# ============================================================================
# STEP 2: Install Dependencies
# ============================================================================
echo ""
echo "STEP 2: Installing Python dependencies..."
cd $BACKEND_DIR
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install/upgrade requirements
pip install -r requirements.txt --quiet
log_success "Dependencies installed"

# ============================================================================
# STEP 3: Run Database Migrations
# ============================================================================
echo ""
echo "STEP 3: Running database migrations..."

# Check if migration file exists
MIGRATION_FILE="$MIGRATIONS_DIR/020_faz_code_schema.sql"

if [ -f "$MIGRATION_FILE" ]; then
    log_info "Found migration: 020_faz_code_schema.sql"
    
    # Get database URL from .env
    source /opt/nicole/.env
    
    if [ -z "$TIGER_DATABASE_URL" ]; then
        log_error "TIGER_DATABASE_URL not found in .env"
        exit 1
    fi
    
    # Run migration
    log_info "Applying migration..."
    psql "$TIGER_DATABASE_URL" -f "$MIGRATION_FILE" || {
        log_warn "Migration may have partially applied (tables might already exist)"
    }
    
    log_success "Migration complete"
else
    log_warn "Migration file not found: $MIGRATION_FILE"
fi

# Verify tables exist
log_info "Verifying tables..."
TABLE_COUNT=$(psql "$TIGER_DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'faz_%'")
echo "Faz tables found: $TABLE_COUNT"

if [ "$TABLE_COUNT" -lt 10 ]; then
    log_warn "Expected 10+ tables, found $TABLE_COUNT. Check migration."
fi

# ============================================================================
# STEP 4: Restart API Service
# ============================================================================
echo ""
echo "STEP 4: Restarting API service..."

# Restart via supervisor
supervisorctl restart nicole-api || {
    log_warn "supervisor restart failed, trying manual restart"
    pkill -f "uvicorn app.main:app" || true
    sleep 2
    cd $BACKEND_DIR
    source venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /var/log/nicole-api.log 2>&1 &
}

sleep 3

# Verify API is running
log_info "Checking API health..."
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz)

if [ "$API_HEALTH" = "200" ]; then
    log_success "API is healthy"
else
    log_error "API health check failed (HTTP $API_HEALTH)"
    echo "Check logs: tail -f /var/log/supervisor/nicole-api-stderr.log"
    exit 1
fi

# ============================================================================
# STEP 5: Verify Faz Endpoints
# ============================================================================
echo ""
echo "STEP 5: Verifying Faz endpoints..."

# Check if /faz/projects endpoint exists
FAZ_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/faz/projects)

if [ "$FAZ_CHECK" = "401" ] || [ "$FAZ_CHECK" = "200" ]; then
    log_success "Faz endpoints registered (got HTTP $FAZ_CHECK - auth required is expected)"
else
    log_error "Faz endpoints may not be registered (HTTP $FAZ_CHECK)"
fi

# ============================================================================
# STEP 6: Restart MCP Gateway (if using Docker)
# ============================================================================
echo ""
echo "STEP 6: Checking MCP Gateway..."

if command -v docker &> /dev/null; then
    if docker ps | grep -q mcp; then
        log_info "Restarting MCP Gateway container..."
        docker restart mcp-gateway || log_warn "Failed to restart MCP Gateway"
        sleep 3
        
        # Check MCP health
        MCP_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3100/health)
        if [ "$MCP_HEALTH" = "200" ]; then
            log_success "MCP Gateway is healthy"
        else
            log_warn "MCP Gateway health check failed"
        fi
    else
        log_info "MCP Gateway container not running (may not be needed)"
    fi
else
    log_info "Docker not installed, skipping MCP Gateway check"
fi

# ============================================================================
# DEPLOYMENT COMPLETE
# ============================================================================
echo ""
echo "============================================"
log_success "FAZ CODE DEPLOYMENT COMPLETE"
echo "============================================"
echo ""
echo "Available endpoints:"
echo "  - POST /faz/projects        - Create project"
echo "  - GET  /faz/projects        - List projects"
echo "  - POST /faz/projects/{id}/run - Run pipeline"
echo "  - GET  /faz/projects/{id}/files - Get files"
echo "  - WS   /faz/projects/{id}/ws - WebSocket"
echo ""
echo "Test with:"
echo "  curl http://localhost:8000/faz/projects -H 'Authorization: Bearer <token>'"
echo ""


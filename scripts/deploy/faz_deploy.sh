#!/bin/bash
# =============================================================================
# NICOLE/FAZ CODE DEPLOYMENT SCRIPT
# =============================================================================
# Deploy updates to the Nicole/Faz Code dashboard on DigitalOcean.
#
# Usage:
#   bash /opt/nicole/scripts/deploy/faz_deploy.sh [OPTIONS]
#
# Options:
#   --backend-only     Only deploy backend
#   --migrate          Run database migrations
#   --restart          Restart services only (no git pull)
#   --status           Check current status
#   --logs             Tail logs
#   --rollback         Rollback to previous version
#   --branch <name>    Deploy specific branch (default: main)
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration - ACTUAL VALUES
APP_DIR="/opt/nicole"
BRANCH="main"
DEPLOY_BACKEND=true
RUN_MIGRATIONS=false
RESTART_ONLY=false
SHOW_STATUS=false
SHOW_LOGS=false
ROLLBACK=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend-only) shift ;;
        --migrate) RUN_MIGRATIONS=true; shift ;;
        --restart) RESTART_ONLY=true; shift ;;
        --status) SHOW_STATUS=true; shift ;;
        --logs) SHOW_LOGS=true; shift ;;
        --rollback) ROLLBACK=true; shift ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --help)
            echo "Nicole/Faz Code Deployment Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --migrate          Run database migrations"
            echo "  --restart          Restart services only (no git pull)"
            echo "  --status           Check current status"
            echo "  --logs             Tail logs"
            echo "  --rollback         Rollback to previous commit"
            echo "  --branch <name>    Deploy specific branch (default: main)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$APP_DIR"

# Load environment
set -a
source "$APP_DIR/.env" 2>/dev/null || true
source "$APP_DIR/tiger-nicole_db-credentials.env" 2>/dev/null || true
set +a

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log_step() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

check_status() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    NICOLE/FAZ STATUS                          ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Git status
    echo -e "${BLUE}Git Status:${NC}"
    cd "$APP_DIR"
    git log -1 --oneline 2>/dev/null || echo "Not a git repo"
    echo "Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"
    echo ""
    
    # Services
    echo -e "${BLUE}Supervisor Services:${NC}"
    supervisorctl status 2>/dev/null | head -10 || echo "Supervisor not running"
    echo ""
    
    # Docker
    echo -e "${BLUE}Docker Services:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep -E "nicole|redis|qdrant" || echo "No Docker services"
    echo ""
    
    # Health checks
    echo -e "${BLUE}Health Checks:${NC}"
    
    API_HEALTH=$(curl -s -m 3 http://localhost:8000/healthz 2>/dev/null || echo '{"status":"error"}')
    if echo "$API_HEALTH" | grep -q "healthy"; then
        echo -e "  API:       ${GREEN}healthy${NC}"
    else
        echo -e "  API:       ${RED}unhealthy${NC}"
    fi
    
    FAZ_HEALTH=$(curl -s -m 3 http://localhost:8000/faz/health 2>/dev/null || echo '{"status":"error"}')
    if echo "$FAZ_HEALTH" | grep -q "healthy"; then
        echo -e "  Faz:       ${GREEN}healthy${NC}"
    else
        echo -e "  Faz:       ${YELLOW}check pending${NC}"
    fi
    
    # Port check
    echo -n "  Port 8000: "
    nc -z localhost 8000 2>/dev/null && echo -e "${GREEN}OPEN${NC}" || echo -e "${RED}CLOSED${NC}"
    echo -n "  Port 6379: "
    nc -z localhost 6379 2>/dev/null && echo -e "${GREEN}OPEN${NC}" || echo -e "${RED}CLOSED${NC}"
    echo ""
    
    # Resources
    echo -e "${BLUE}Resources:${NC}"
    echo "  Memory: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
    echo "  Disk:   $(df -h / | awk 'NR==2{print $5}')"
    echo ""
}

show_logs() {
    echo -e "${CYAN}Tailing API logs (Ctrl+C to exit)...${NC}"
    tail -f /var/log/supervisor/nicole-api-*.log
}

# Handle special modes
if [ "$SHOW_STATUS" = true ]; then
    check_status
    exit 0
fi

if [ "$SHOW_LOGS" = true ]; then
    show_logs
    exit 0
fi

# =============================================================================
# MAIN DEPLOYMENT
# =============================================================================

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      NICOLE/FAZ CODE DEPLOYMENT - $(date '+%Y-%m-%d %H:%M')        ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

START_TIME=$(date +%s)

# =============================================================================
# STEP 1: PRE-DEPLOYMENT CHECKS
# =============================================================================
log_step "Running pre-deployment checks..."

if [ ! -f "$APP_DIR/backend/requirements.txt" ]; then
    log_error "Not in Nicole_Assistant directory!"
    exit 1
fi

if ! systemctl is-active --quiet nginx; then
    log_warning "Nginx not running, starting..."
    systemctl start nginx
fi

log_success "Pre-deployment checks passed"
echo ""

# =============================================================================
# STEP 2: BACKUP
# =============================================================================
log_step "Creating backup point..."

PREVIOUS_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "none")
echo "$PREVIOUS_COMMIT" > /tmp/nicole-previous-commit

log_success "Backup point created (${PREVIOUS_COMMIT:0:8})"
echo ""

# =============================================================================
# STEP 3: ROLLBACK (if requested)
# =============================================================================
if [ "$ROLLBACK" = true ]; then
    log_step "Rolling back to previous version..."
    
    if [ -f /tmp/nicole-previous-commit ]; then
        ROLLBACK_COMMIT=$(cat /tmp/nicole-previous-commit)
        if [ -n "$ROLLBACK_COMMIT" ] && [ "$ROLLBACK_COMMIT" != "none" ]; then
            git reset --hard "$ROLLBACK_COMMIT"
            log_success "Rolled back to $ROLLBACK_COMMIT"
            RESTART_ONLY=true
        else
            log_error "No previous commit found"
            exit 1
        fi
    else
        log_error "No backup point found"
        exit 1
    fi
    echo ""
fi

# =============================================================================
# STEP 4: PULL LATEST CODE
# =============================================================================
if [ "$RESTART_ONLY" = false ]; then
    log_step "Pulling latest code from $BRANCH..."
    
    git stash 2>/dev/null || true
    git fetch origin
    git checkout "$BRANCH"
    git reset --hard "origin/$BRANCH"
    
    NEW_COMMIT=$(git rev-parse HEAD)
    log_success "Updated to commit: ${NEW_COMMIT:0:8}"
    
    echo ""
    echo -e "${BLUE}Recent changes:${NC}"
    git log --oneline -5
    echo ""
fi

# =============================================================================
# STEP 5: UPDATE DEPENDENCIES
# =============================================================================
if [ "$RESTART_ONLY" = false ]; then
    log_step "Updating Python dependencies..."
    
    source "$APP_DIR/.venv/bin/activate"
    pip install --upgrade pip -q
    pip install -r backend/requirements.txt -q
    
    log_success "Dependencies updated"
    echo ""
fi

# =============================================================================
# STEP 6: RUN MIGRATIONS
# =============================================================================
if [ "$RUN_MIGRATIONS" = true ]; then
    log_step "Running database migrations..."
    
    cd "$APP_DIR/backend"
    source "$APP_DIR/.venv/bin/activate"
    
    if [ -n "$TIGER_DATABASE_URL" ]; then
        for migration in database/migrations/0*.sql; do
            if [ -f "$migration" ]; then
                echo -e "  ${YELLOW}→${NC} $(basename $migration)"
                psql "$TIGER_DATABASE_URL" -f "$migration" 2>&1 | grep -v "already exists" | grep -v "NOTICE" || true
            fi
        done
        log_success "Migrations complete"
    else
        log_warning "TIGER_DATABASE_URL not set, skipping migrations"
    fi
    
    cd "$APP_DIR"
    echo ""
fi

# =============================================================================
# STEP 7: RESTART SERVICES
# =============================================================================
log_step "Restarting services..."

supervisorctl restart nicole-api 2>/dev/null || {
    log_warning "supervisor restart failed, trying manual restart"
    pkill -f "uvicorn app.main:app" || true
    sleep 2
    cd "$APP_DIR/backend"
    source "$APP_DIR/.venv/bin/activate"
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /var/log/nicole-api.log 2>&1 &
}

supervisorctl restart nicole-worker 2>/dev/null || true

nginx -t && systemctl reload nginx

log_success "Services restarted"
echo ""

# =============================================================================
# STEP 8: POST-DEPLOYMENT VERIFICATION
# =============================================================================
log_step "Verifying deployment..."

sleep 3

API_HEALTH=$(curl -s -m 5 http://localhost:8000/healthz 2>/dev/null || echo '{"status":"error"}')
if echo "$API_HEALTH" | grep -q "healthy"; then
    log_success "API health check passed"
else
    log_warning "API health check pending"
fi

FAZ_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/faz/projects 2>/dev/null)
if [ "$FAZ_CHECK" = "401" ] || [ "$FAZ_CHECK" = "200" ]; then
    log_success "Faz endpoints registered (HTTP $FAZ_CHECK)"
else
    log_warning "Faz endpoints check: HTTP $FAZ_CHECK"
fi

echo ""

# =============================================================================
# RESTART MCP GATEWAY (if running)
# =============================================================================
if docker ps 2>/dev/null | grep -q mcp; then
    log_step "Restarting MCP Gateway..."
    docker restart mcp-gateway 2>/dev/null || true
    log_success "MCP Gateway restarted"
    echo ""
fi

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  DEPLOYMENT COMPLETE!                         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Duration:    ${CYAN}${DURATION}s${NC}"
echo -e "Commit:      ${CYAN}$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')${NC}"
echo -e "Branch:      ${CYAN}$(git branch --show-current 2>/dev/null || echo 'N/A')${NC}"
echo ""
echo "Available endpoints:"
echo "  - https://api.nicole.alphawavetech.com/healthz"
echo "  - https://api.nicole.alphawavetech.com/faz/health"
echo "  - https://api.nicole.alphawavetech.com/faz/projects"
echo ""
echo -e "${YELLOW}Quick Commands:${NC}"
echo "  View logs:     bash $0 --logs"
echo "  Check status:  bash $0 --status"
echo "  Rollback:      bash $0 --rollback"
echo ""

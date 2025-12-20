#!/bin/bash
# =============================================================================
# NICOLE/FAZ CODE DATABASE OPERATIONS
# =============================================================================
# Database management operations for Nicole/Faz Code.
#
# Usage:
#   bash /opt/nicole/scripts/deploy/faz_database_ops.sh <command>
#
# Commands:
#   migrate           Run pending migrations
#   migrate-status    Show migration status
#   backup            Create database backup
#   restore <file>    Restore from backup
#   connect           Interactive psql session
#   query <sql>       Run single query
#   stats             Show database statistics
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

APP_DIR="/opt/nicole"
COMMAND="${1:-stats}"
BACKUP_DIR="$APP_DIR/backups"

# Load environment - ACTUAL CREDENTIALS
set -a
source "$APP_DIR/.env" 2>/dev/null || true
source "$APP_DIR/tiger-nicole_db-credentials.env" 2>/dev/null || true
set +a

# Fallback to known credentials if not set
if [ -z "$TIGER_DATABASE_URL" ]; then
    TIGER_DATABASE_URL="postgres://tsdbadmin:alphawave444@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require"
fi

# Parse database URL
DB_USER="${PGUSER:-tsdbadmin}"
DB_PASS="${PGPASSWORD:-alphawave444}"
DB_HOST="${PGHOST:-h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com}"
DB_PORT="${PGPORT:-33565}"
DB_NAME="${PGDATABASE:-tsdb}"

# =============================================================================
# FUNCTIONS
# =============================================================================

log_action() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

run_migrations() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                  DATABASE MIGRATIONS                          ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    cd "$APP_DIR/backend"
    
    MIGRATION_COUNT=0
    APPLIED_COUNT=0
    
    for migration in database/migrations/0*.sql; do
        if [ -f "$migration" ]; then
            MIGRATION_COUNT=$((MIGRATION_COUNT + 1))
            MIGRATION_NAME=$(basename "$migration")
            
            echo -e "${YELLOW}→${NC} Applying: $MIGRATION_NAME"
            
            RESULT=$(PGPASSWORD="$DB_PASS" psql \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                -f "$migration" 2>&1 || true)
            
            if echo "$RESULT" | grep -q "ERROR"; then
                if echo "$RESULT" | grep -qi "already exists"; then
                    echo "  Already applied (skipped)"
                else
                    echo "  Error: $(echo "$RESULT" | grep "ERROR")"
                fi
            else
                echo "  Applied successfully"
                APPLIED_COUNT=$((APPLIED_COUNT + 1))
            fi
        fi
    done
    
    echo ""
    log_success "Migrations complete: $APPLIED_COUNT new, $((MIGRATION_COUNT - APPLIED_COUNT)) skipped"
}

show_migration_status() {
    echo -e "${CYAN}Migration Status${NC}"
    echo ""
    
    # List migrations
    echo -e "${BLUE}Available migrations:${NC}"
    for migration in "$APP_DIR/backend/database/migrations"/0*.sql; do
        if [ -f "$migration" ]; then
            echo "  - $(basename $migration)"
        fi
    done
    echo ""
    
    # Check which tables exist
    echo -e "${BLUE}Faz Code tables:${NC}"
    PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t -c "SELECT '  ✓ ' || table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'faz_%' ORDER BY table_name" 2>/dev/null || log_error "Could not check tables"
    echo ""
    
    # Count
    TABLE_COUNT=$(PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'faz_%'" 2>/dev/null || echo "0")
    echo "Total Faz tables: $TABLE_COUNT"
}

create_backup() {
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/faz_backup_$TIMESTAMP.sql"
    
    log_action "Creating backup..."
    
    PGPASSWORD="$DB_PASS" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        -t 'faz_*' \
        > "$BACKUP_FILE" 2>/dev/null
    
    if [ -s "$BACKUP_FILE" ]; then
        gzip "$BACKUP_FILE"
        log_success "Backup created: ${BACKUP_FILE}.gz"
        ls -lh "${BACKUP_FILE}.gz" | awk '{print "  Size: " $5}'
        
        # Cleanup old backups (keep last 10)
        ls -t "$BACKUP_DIR"/faz_backup_*.sql.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    else
        log_error "Backup failed"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
}

restore_backup() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        echo "Available backups:"
        ls -la "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "  No backups found"
        echo ""
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    echo -e "${YELLOW}WARNING: This will overwrite existing Faz tables!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Cancelled"
        exit 0
    fi
    
    log_action "Restoring from backup..."
    
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | PGPASSWORD="$DB_PASS" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            2>/dev/null
    else
        PGPASSWORD="$DB_PASS" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            < "$backup_file" \
            2>/dev/null
    fi
    
    log_success "Restore complete"
}

connect_db() {
    echo -e "${CYAN}Connecting to TimescaleDB...${NC}"
    echo "Host: $DB_HOST:$DB_PORT"
    echo "Database: $DB_NAME"
    echo ""
    
    PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME"
}

run_query() {
    local query="$1"
    
    if [ -z "$query" ]; then
        echo "Usage: $0 query \"SELECT * FROM faz_projects LIMIT 10\""
        exit 1
    fi
    
    PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "$query"
}

show_stats() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                  DATABASE STATISTICS                          ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${BLUE}Connection:${NC}"
    echo "  Host: $DB_HOST:$DB_PORT"
    echo "  Database: $DB_NAME"
    echo ""
    
    echo -e "${BLUE}Table Statistics:${NC}"
    PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "SELECT relname as table_name, n_live_tup as row_count FROM pg_stat_user_tables WHERE relname LIKE 'faz_%' ORDER BY n_live_tup DESC" 2>/dev/null || log_error "Could not fetch stats"
    echo ""
    
    echo -e "${BLUE}Project Statistics:${NC}"
    PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "SELECT COUNT(*) as total_projects, COUNT(*) FILTER (WHERE status = 'deployed') as deployed, COUNT(*) FILTER (WHERE status = 'building') as building, ROUND(COALESCE(SUM(total_cost_cents), 0) / 100.0, 2) as total_cost_usd FROM faz_projects" 2>/dev/null || echo "  Table faz_projects not found"
    echo ""
    
    echo -e "${BLUE}Recent Activity:${NC}"
    PGPASSWORD="$DB_PASS" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "SELECT agent_name, activity_type, status, started_at FROM faz_agent_activities ORDER BY started_at DESC LIMIT 5" 2>/dev/null || echo "  Table faz_agent_activities not found"
}

# =============================================================================
# MAIN
# =============================================================================

case "$COMMAND" in
    migrate)
        run_migrations
        ;;
    migrate-status)
        show_migration_status
        ;;
    backup)
        create_backup
        ;;
    restore)
        restore_backup "$2"
        ;;
    connect)
        connect_db
        ;;
    query)
        run_query "$2"
        ;;
    stats)
        show_stats
        ;;
    help|--help|-h)
        echo "Nicole/Faz Database Operations"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  migrate           Run pending migrations"
        echo "  migrate-status    Show migration status"
        echo "  backup            Create database backup"
        echo "  restore <file>    Restore from backup"
        echo "  connect           Interactive psql session"
        echo "  query <sql>       Run single query"
        echo "  stats             Show database statistics"
        echo ""
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac

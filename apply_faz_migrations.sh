#!/bin/bash
# ============================================================================
# FAZ CODE DATABASE MIGRATION - Apply All Faz Migrations
# ============================================================================

set -e  # Exit on error

echo "=========================================="
echo "FAZ CODE DATABASE MIGRATION"
echo "=========================================="
echo ""

# Load environment variables properly
if [ -f /opt/nicole/.env ]; then
    set -a  # Automatically export all variables
    source /opt/nicole/.env
    set +a
    echo "✓ Loaded environment from /opt/nicole/.env"
elif [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✓ Loaded environment from .env"
else
    echo "❌ ERROR: No .env file found"
    exit 1
fi

# Check if TIGER_DATABASE_URL is set
if [ -z "$TIGER_DATABASE_URL" ]; then
    echo "❌ ERROR: TIGER_DATABASE_URL not set in environment"
    echo "Checking for DATABASE_URL as fallback..."
    if [ -z "$DATABASE_URL" ]; then
        echo "❌ ERROR: Neither TIGER_DATABASE_URL nor DATABASE_URL is set"
        exit 1
    else
        echo "✓ Using DATABASE_URL"
        DB_URL="$DATABASE_URL"
    fi
else
    echo "✓ TigerDB connection found"
    DB_URL="$TIGER_DATABASE_URL"
fi
echo ""

# Migration files
MIGRATION_DIR="/opt/nicole/backend/database/migrations"
MIGRATIONS=(
    "020_faz_code_schema.sql"
    "021_faz_project_artifacts.sql"
    "022_faz_enhancements.sql"
)

echo "Found ${#MIGRATIONS[@]} Faz Code migrations to apply"
echo ""

# Apply each migration
for migration in "${MIGRATIONS[@]}"; do
    migration_path="$MIGRATION_DIR/$migration"
    
    if [ ! -f "$migration_path" ]; then
        echo "❌ ERROR: Migration file not found: $migration_path"
        exit 1
    fi
    
    echo "=========================================="
    echo "Applying: $migration"
    echo "=========================================="
    
    # Apply migration with error handling
    if psql "$DB_URL" -f "$migration_path" 2>&1 | tee /tmp/migration_$migration.log; then
        echo "✓ Migration $migration applied successfully"
        echo ""
    else
        echo "❌ ERROR: Migration $migration failed"
        echo "Check log: /tmp/migration_$migration.log"
        exit 1
    fi
done

echo "=========================================="
echo "VERIFICATION"
echo "=========================================="

# Verify tables were created
echo "Checking for Faz Code tables..."
psql "$DB_URL" -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'faz_%' 
ORDER BY table_name;
" | tee /tmp/faz_tables.txt

TABLE_COUNT=$(grep -c "faz_" /tmp/faz_tables.txt || echo "0")

if [ "$TABLE_COUNT" -ge 10 ]; then
    echo ""
    echo "✓ SUCCESS: Found $TABLE_COUNT Faz Code tables"
else
    echo ""
    echo "⚠ WARNING: Only found $TABLE_COUNT Faz Code tables (expected 10+)"
fi

echo ""
echo "=========================================="
echo "MIGRATION COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart services: supervisorctl restart nicole-api nicole-worker"
echo "2. Test Faz Code pipeline in the dashboard"
echo ""

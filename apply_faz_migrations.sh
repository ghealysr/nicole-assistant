#!/bin/bash
# ============================================================================
# FAZ CODE DATABASE MIGRATION - Apply All Faz Migrations
# ============================================================================

set -e  # Exit on error

echo "=========================================="
echo "FAZ CODE DATABASE MIGRATION"
echo "=========================================="
echo ""

# Load environment variables
if [ -f /opt/nicole/.env ]; then
    export $(grep -v '^#' /opt/nicole/.env | xargs)
    echo "✓ Loaded environment from /opt/nicole/.env"
elif [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ Loaded environment from .env"
else
    echo "❌ ERROR: No .env file found"
    exit 1
fi

# Check if TIGER_DATABASE_URL is set
if [ -z "$TIGER_DATABASE_URL" ]; then
    echo "❌ ERROR: TIGER_DATABASE_URL not set in environment"
    exit 1
fi

echo "✓ TigerDB connection found"
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
    if psql "$TIGER_DATABASE_URL" -f "$migration_path" 2>&1 | tee /tmp/migration_$migration.log; then
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
psql "$TIGER_DATABASE_URL" -c "
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


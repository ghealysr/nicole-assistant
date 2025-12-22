#!/bin/bash
# Script to apply image-related database migrations on the droplet

echo "=== Applying Image Migrations ==="

# 1. Pull latest code
cd /opt/nicole
git pull origin main

# 2. Source environment variables
source /opt/nicole/.env

# 3. Check if migrations have been applied
echo ""
echo "Checking existing columns in research_reports..."
psql "$TIGER_DATABASE_URL" -c "\d research_reports" | grep -E "hero_image_url|images|screenshots"

# 4. Apply migration 013 (template fields)
echo ""
echo "Applying migration 013_research_template_fields.sql..."
psql "$TIGER_DATABASE_URL" -f /opt/nicole/backend/database/migrations/013_research_template_fields.sql

# 5. Apply migration 014 (image fields)
echo ""
echo "Applying migration 014_research_images.sql..."
psql "$TIGER_DATABASE_URL" -f /opt/nicole/backend/database/migrations/014_research_images.sql

# 6. Verify columns were added
echo ""
echo "Verifying new columns..."
psql "$TIGER_DATABASE_URL" -c "\d research_reports" | grep -E "article_title|hero_image_url|images|screenshots"

# 7. Restart the API
echo ""
echo "Restarting nicole-api..."
supervisorctl restart nicole-api

# 8. Check status
sleep 3
supervisorctl status nicole-api

echo ""
echo "=== Migration Complete ==="
echo "You can now test a new research query to see images."



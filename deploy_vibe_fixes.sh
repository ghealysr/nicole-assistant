#!/bin/bash

# AlphaWave Vibe Dashboard - Production Deployment Script
# Run this script on your production droplet to deploy the latest fixes

set -e  # Exit on any error

echo '🚀 Starting AlphaWave Vibe Dashboard deployment...'

# 1. Navigate to project directory
cd /opt/nicole || { echo '❌ Failed to cd to /opt/nicole'; exit 1; }

# 2. Pull latest code
echo '📦 Pulling latest code from main branch...'
git pull origin main || { echo '❌ Failed to pull from git'; exit 1; }

# 3. Clear Python cache (important for fixes)
echo '🧹 Clearing Python cache...'
find /opt/nicole/backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /opt/nicole/backend -name '*.pyc' -delete 2>/dev/null || true

# 4. Restart backend service
echo '🔄 Restarting Nicole API service...'
supervisorctl stop nicole-api || { echo '⚠️  Service was not running'; }
sleep 2
supervisorctl start nicole-api || { echo '❌ Failed to start service'; exit 1; }
sleep 3

# 5. Verify service is running
echo '✅ Checking service status...'
supervisorctl status nicole-api

# 6. Test health endpoint
echo '🏥 Testing health endpoint...'
if curl -s http://localhost:8000/health/ping > /dev/null 2>&1; then
    echo '✅ Backend is healthy!'
else
    echo '❌ Backend health check failed'
    exit 1
fi

echo ''
echo '🎉 Deployment complete! Vibe dashboard should now work without crashes.'
echo '   - Frontend: Will auto-deploy via Vercel webhook'
echo '   - Backend: ✅ Running and healthy'
echo ''
echo 'Test the Vibe dashboard by clicking the Vibe button in the sidebar!'

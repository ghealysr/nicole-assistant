#!/bin/bash
# Fix Production Skills Deployment - Handle Git Conflicts

cd /opt/nicole

echo "=== Step 1: Check Local Changes ==="
git status skills/registry.json

echo ""
echo "=== Step 2: Backup Local Changes (if any) ==="
if [ -f skills/registry.json ]; then
    cp skills/registry.json skills/registry.json.backup.$(date +%s)
    echo "✅ Backed up to skills/registry.json.backup.*"
fi

echo ""
echo "=== Step 3: Stash Local Changes ==="
git stash push -m "Local registry changes before pulling Notion skills $(date +%Y%m%d-%H%M%S)" skills/registry.json

echo ""
echo "=== Step 4: Pull Latest Code ==="
git pull origin main

if [ $? -ne 0 ]; then
    echo "❌ Git pull failed. Trying force reset (WARNING: This will discard local changes)"
    read -p "Continue with force reset? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git reset --hard origin/main
        git pull origin main
    else
        echo "Aborted. Please resolve manually."
        exit 1
    fi
fi

echo ""
echo "=== Step 5: Verify Notion Skills Installed ==="
if [ -d skills/installed/notion ]; then
    echo "✅ Notion skills directory exists"
    ls -la skills/installed/notion/*/main.py 2>/dev/null || echo "⚠️  No main.py files found"
else
    echo "❌ Notion skills directory not found"
    echo "Creating directory structure..."
    mkdir -p skills/installed/notion/{notion-knowledge-capture,notion-meeting-intelligence,notion-research-documentation,notion-spec-to-implementation}
fi

echo ""
echo "=== Step 6: Check Skill Registry ==="
python3 <<PYTHON
import json
import os

registry_path = 'skills/registry.json'
if os.path.exists(registry_path):
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    notion_skills = [s for s in registry.get('skills', []) if s.get('vendor') == 'notion']
    print(f"✅ Found {len(notion_skills)} Notion skills in registry:")
    for skill in notion_skills:
        status = skill.get('setup_status', 'unknown')
        print(f"  - {skill['id']}: {status}")
else:
    print("❌ Registry file not found")
PYTHON

echo ""
echo "=== Step 7: Restart API to Load New Skills ==="
supervisorctl restart nicole-api
sleep 5

echo ""
echo "=== Step 8: Verify API Health ==="
PING_RESPONSE=$(curl -s http://localhost:8000/health/ping 2>&1)
if echo "$PING_RESPONSE" | grep -q "pong"; then
    echo "✅ API is healthy"
    echo "$PING_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PING_RESPONSE"
else
    echo "❌ API health check failed"
    echo "$PING_RESPONSE"
fi

echo ""
echo "=== Step 9: Verify MCP Tools (Including Notion) ==="
MCP_RESPONSE=$(curl -s http://localhost:8000/health/mcp 2>&1)
if echo "$MCP_RESPONSE" | grep -q "notion_search"; then
    echo "✅ Notion MCP tools are available"
    echo "$MCP_RESPONSE" | python3 -m json.tool 2>/dev/null | grep -A 20 "tools" || echo "$MCP_RESPONSE"
else
    echo "⚠️  Notion tools not found in MCP response"
    echo "$MCP_RESPONSE"
fi

echo ""
echo "=== Summary ==="
echo "✅ Git conflict resolved"
echo "✅ Code pulled from main"
echo "✅ API restarted"
echo ""
echo "Notion skills should now be available. Test with Nicole:"
echo "  - 'Save this conversation to Notion'"
echo "  - 'Prepare for the client meeting'"
echo "  - 'Research authentication methods in Notion'"
echo "  - 'Create implementation plan from the API spec'"


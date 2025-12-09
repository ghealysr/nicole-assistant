#!/bin/bash
set -e

echo "=========================================="
echo "Nicole V7 - MCP Bridge Deployment"
echo "=========================================="
echo ""

# Check if running on production droplet
if [ ! -d "/opt/nicole" ]; then
    echo "❌ Error: /opt/nicole directory not found"
    echo "This script should be run on the production droplet"
    exit 1
fi

# Check if .env exists and has BRAVE_API_KEY
if [ ! -f "/opt/nicole/.env" ]; then
    echo "❌ Error: /opt/nicole/.env not found"
    exit 1
fi

# Load environment variables
set -a
source /opt/nicole/.env
set +a

if [ -z "$BRAVE_API_KEY" ]; then
    echo "⚠️  Warning: BRAVE_API_KEY is not set in /opt/nicole/.env"
    echo "Brave Search MCP server will not function without it"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✓ Environment variables loaded"
echo ""

# Navigate to MCP directory
cd /opt/nicole/mcp

echo "Building MCP Bridge container..."
docker compose build

echo ""
echo "Starting MCP Bridge..."
docker compose up -d

echo ""
echo "Waiting for bridge to start..."
sleep 5

echo ""
echo "=========================================="
echo "Health Check"
echo "=========================================="
echo ""

# Check container status
if docker ps | grep -q "nicole-mcp-bridge"; then
    echo "✓ Container is running"
else
    echo "❌ Container is not running"
    echo ""
    echo "Recent logs:"
    docker logs --tail 20 nicole-mcp-bridge
    exit 1
fi

# Check HTTP health endpoint
if curl -s http://127.0.0.1:3100/health > /dev/null; then
    echo "✓ HTTP endpoint responding"
    
    # Display health status
    echo ""
    echo "Bridge Status:"
    curl -s http://127.0.0.1:3100/health | python3 -m json.tool
else
    echo "❌ HTTP endpoint not responding"
    echo ""
    echo "Recent logs:"
    docker logs --tail 20 nicole-mcp-bridge
    exit 1
fi

echo ""
echo "Testing tools/list endpoint..."
TOOLS_RESPONSE=$(curl -s -X POST http://127.0.0.1:3100/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}')

if echo "$TOOLS_RESPONSE" | grep -q "result"; then
    echo "✓ Tools endpoint working"
    echo ""
    echo "Available tools:"
    echo "$TOOLS_RESPONSE" | python3 -m json.tool | grep -A2 "name"
else
    echo "❌ Tools endpoint returned error"
    echo "$TOOLS_RESPONSE" | python3 -m json.tool
fi

echo ""
echo "=========================================="
echo "Restarting Nicole API"
echo "=========================================="
echo ""

supervisorctl restart nicole-api
sleep 3
supervisorctl status nicole-api

echo ""
echo "=========================================="
echo "Final Verification"
echo "=========================================="
echo ""

# Check backend MCP health endpoint
echo "Checking backend MCP integration..."
BACKEND_MCP=$(curl -s http://localhost:8000/health/mcp)

if echo "$BACKEND_MCP" | grep -q "healthy"; then
    echo "✓ Backend MCP integration working"
    echo ""
    echo "Backend MCP Status:"
    echo "$BACKEND_MCP" | python3 -m json.tool
else
    echo "⚠️  Backend MCP integration issue"
    echo "$BACKEND_MCP" | python3 -m json.tool
    echo ""
    echo "Check backend logs:"
    echo "  tail -50 /var/log/nicole-api.log"
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete"
echo "=========================================="
echo ""
echo "MCP Bridge:     http://127.0.0.1:3100"
echo "Health Check:   http://127.0.0.1:3100/health"
echo "Backend Health: http://localhost:8000/health/mcp"
echo ""
echo "Logs:"
echo "  docker logs -f nicole-mcp-bridge"
echo "  tail -f /var/log/nicole-api.log"
echo ""
echo "Manage:"
echo "  docker compose restart   # Restart MCP bridge"
echo "  docker compose stop      # Stop MCP bridge"
echo "  docker compose logs -f   # View logs"
echo ""


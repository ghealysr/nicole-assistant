#!/bin/bash
# Script to diagnose and fix Nginx streaming issues for Nicole API
# Run this on the droplet: bash /opt/nicole/scripts/fix_nginx_streaming.sh

echo "=== NICOLE STREAMING DIAGNOSTICS ==="
echo ""

# Step 1: Check current Nginx config for buffering settings
echo "1. Checking Nginx config..."
NGINX_CONF="/etc/nginx/sites-enabled/nicole"

if [ ! -f "$NGINX_CONF" ]; then
    NGINX_CONF="/etc/nginx/sites-available/nicole"
fi

echo "   Config file: $NGINX_CONF"
echo ""

# Check if proxy_buffering is set
if grep -q "proxy_buffering" "$NGINX_CONF" 2>/dev/null; then
    echo "   proxy_buffering setting found:"
    grep "proxy_buffering" "$NGINX_CONF"
else
    echo "   ❌ proxy_buffering NOT found - this causes streaming issues!"
fi

# Check proxy_buffer_size
if grep -q "proxy_buffer_size" "$NGINX_CONF" 2>/dev/null; then
    echo "   proxy_buffer_size setting found:"
    grep "proxy_buffer_size" "$NGINX_CONF"
else
    echo "   proxy_buffer_size NOT set"
fi

echo ""
echo "2. Checking for X-Accel-Buffering support..."

# Check if nginx is compiled with the module
if nginx -V 2>&1 | grep -q "ngx_http_proxy_module"; then
    echo "   ✅ Proxy module is installed"
else
    echo "   ❌ Proxy module NOT found!"
fi

echo ""
echo "3. Testing API streaming directly (bypassing nginx)..."

# Test direct to uvicorn (port 8000)
echo "   Testing localhost:8000/chat/stream-test..."
timeout 10 curl -s -N "http://localhost:8000/chat/stream-test" 2>&1 | head -10

echo ""
echo "4. Testing API streaming through nginx..."

# Test through nginx
echo "   Testing through nginx/SSL..."
timeout 10 curl -s -N "https://api.alphawavetech.com/chat/stream-test" -H "Authorization: Bearer test" 2>&1 | head -10

echo ""
echo "=== RECOMMENDED FIX ==="
echo ""
echo "Add these lines to your Nginx location block for the API:"
echo ""
cat << 'EOF'
location / {
    proxy_pass http://127.0.0.1:8000;
    
    # Disable buffering for SSE streaming - CRITICAL
    proxy_buffering off;
    proxy_cache off;
    
    # Chunked encoding support
    chunked_transfer_encoding on;
    
    # Keep connection alive for streaming
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    
    # Pass through X-Accel-Buffering header from app
    proxy_pass_header X-Accel-Buffering;
    
    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeout settings
    proxy_read_timeout 300s;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
}
EOF

echo ""
echo "5. Checking current Nginx location block..."
grep -A 20 "location /" "$NGINX_CONF" 2>/dev/null | head -25

echo ""
echo "=== END DIAGNOSTICS ==="


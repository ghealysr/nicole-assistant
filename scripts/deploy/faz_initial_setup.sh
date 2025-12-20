#!/bin/bash
# =============================================================================
# NICOLE/FAZ CODE INITIAL SETUP SCRIPT
# =============================================================================
# First-time setup for a fresh DigitalOcean droplet.
# Run this ONCE after creating the droplet.
#
# Prerequisites:
#   - Ubuntu 22.04+ droplet
#   - SSH access as root
#
# Usage:
#   scp -r Nicole_Assistant root@YOUR_DROPLET_IP:/opt/nicole
#   ssh root@YOUR_DROPLET_IP
#   bash /opt/nicole/scripts/deploy/faz_initial_setup.sh
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
DOMAIN="api.nicole.alphawavetech.com"
FRONTEND_DOMAIN="nicole.alphawavetech.com"
EMAIL="glen@alphawavetech.com"
PYTHON_VERSION="3.11"
GITHUB_REPO="https://github.com/glenhealysr1/Nicole_Assistant.git"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     NICOLE/FAZ CODE INITIAL SETUP - $(date '+%Y-%m-%d %H:%M')       ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# =============================================================================
# STEP 1: System Updates
# =============================================================================
echo -e "${BLUE}[1/10]${NC} Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
echo -e "${GREEN}✓${NC} System updated"
echo ""

# =============================================================================
# STEP 2: Install Dependencies
# =============================================================================
echo -e "${BLUE}[2/10]${NC} Installing system dependencies..."

apt-get install -y -qq \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip \
    nginx \
    supervisor \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    build-essential \
    libpq-dev \
    postgresql-client \
    ca-certificates \
    gnupg \
    lsb-release \
    jq \
    netcat-openbsd

echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# =============================================================================
# STEP 3: Install Docker
# =============================================================================
echo -e "${BLUE}[3/10]${NC} Installing Docker..."

if ! command -v docker &> /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    echo -e "${GREEN}✓${NC} Docker installed"
else
    echo -e "${GREEN}✓${NC} Docker already installed"
fi
echo ""

# =============================================================================
# STEP 4: Install Node.js
# =============================================================================
echo -e "${BLUE}[4/10]${NC} Installing Node.js..."

if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
    echo -e "${GREEN}✓${NC} Node.js $(node --version) installed"
else
    echo -e "${GREEN}✓${NC} Node.js $(node --version) already installed"
fi
echo ""

# =============================================================================
# STEP 5: Setup Application Directory
# =============================================================================
echo -e "${BLUE}[5/10]${NC} Setting up application directory..."

mkdir -p "$APP_DIR"

# If script is running from within the repo, copy it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../../backend/requirements.txt" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    if [ "$REPO_ROOT" != "$APP_DIR" ]; then
        echo -e "  ${YELLOW}→${NC} Copying repository to $APP_DIR..."
        rsync -a --exclude='.venv' --exclude='node_modules' --exclude='.git' "$REPO_ROOT/" "$APP_DIR/"
    fi
fi

chown -R root:root "$APP_DIR"
echo -e "${GREEN}✓${NC} Application directory ready"
echo ""

# =============================================================================
# STEP 6: Setup Python Environment
# =============================================================================
echo -e "${BLUE}[6/10]${NC} Setting up Python virtual environment..."

cd "$APP_DIR"

python${PYTHON_VERSION} -m venv .venv
source .venv/bin/activate

pip install --upgrade pip setuptools wheel -q
pip install -r backend/requirements.txt -q

# Install Playwright for screenshots
pip install playwright -q
playwright install chromium 2>/dev/null || echo -e "  ${YELLOW}⚠${NC} Playwright chromium skipped"

echo -e "${GREEN}✓${NC} Python environment ready"
echo ""

# =============================================================================
# STEP 7: Configure Environment
# =============================================================================
echo -e "${BLUE}[7/10]${NC} Configuring environment..."

if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" << 'EOF'
# =============================================================================
# NICOLE V7 / FAZ CODE - PRODUCTION ENVIRONMENT
# =============================================================================

ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://nicole.alphawavetech.com

# =============================================================================
# DATABASE - TimescaleDB Cloud
# =============================================================================
TIGER_DATABASE_URL=postgres://tsdbadmin:alphawave444@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require
TIMESCALE_SERVICE_URL=postgres://tsdbadmin:alphawave444@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require
TIGER_SERVICE_ID=h5ry0v71x4

# Database connection params (for psql)
PGPASSWORD=alphawave444
PGUSER=tsdbadmin
PGHOST=h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com
PGPORT=33565
PGDATABASE=tsdb

# =============================================================================
# AI API KEYS - Replace with your actual keys
# =============================================================================
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE

# =============================================================================
# AUTHENTICATION
# =============================================================================
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET=YOUR_SUPABASE_JWT_SECRET

# =============================================================================
# DEPLOYMENT
# =============================================================================
GITHUB_TOKEN=ghp_YOUR_GITHUB_TOKEN
VERCEL_TOKEN=YOUR_VERCEL_TOKEN

# =============================================================================
# IMAGE SERVICES
# =============================================================================
CLOUDINARY_CLOUD_NAME=YOUR_CLOUD_NAME
CLOUDINARY_API_KEY=YOUR_API_KEY
CLOUDINARY_API_SECRET=YOUR_SECRET
REPLICATE_API_TOKEN=r8_YOUR_TOKEN

# =============================================================================
# CACHE & VECTOR DB
# =============================================================================
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# =============================================================================
# SECURITY
# =============================================================================
JWT_SECRET_KEY=your-jwt-secret-key-change-this
SESSION_SECRET=your-session-secret-change-this
ALLOWED_USERS=glen@alphawavetech.com,son1@alphawavetech.com
EOF
    echo -e "  ${YELLOW}⚠${NC} Created .env template - EDIT WITH YOUR API KEYS!"
    echo -e "  ${CYAN}→${NC} nano $APP_DIR/.env"
else
    echo -e "${GREEN}✓${NC} Environment file exists"
fi

# Also load existing credentials if available
if [ -f "$APP_DIR/tiger-nicole_db-credentials.env" ]; then
    source "$APP_DIR/tiger-nicole_db-credentials.env"
    echo -e "  ${GREEN}✓${NC} Loaded Tiger DB credentials"
fi
echo ""

# =============================================================================
# STEP 8: Start Docker Services
# =============================================================================
echo -e "${BLUE}[8/10]${NC} Starting Docker services..."

cd "$APP_DIR"

if [ -f "docker-compose.yml" ]; then
    docker compose up -d
    echo -e "${GREEN}✓${NC} Docker services started (Redis, Qdrant)"
else
    echo -e "  ${YELLOW}→${NC} Starting Redis and Qdrant manually..."
    docker run -d --name nicole-redis -p 6379:6379 --restart unless-stopped redis:7-alpine redis-server --appendonly yes || true
    docker run -d --name nicole-qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage --restart unless-stopped qdrant/qdrant || true
fi
echo ""

# =============================================================================
# STEP 9: Configure Supervisor
# =============================================================================
echo -e "${BLUE}[9/10]${NC} Configuring Supervisor..."

# API service
cat > /etc/supervisor/conf.d/nicole-api.conf << EOF
[program:nicole-api]
command=$APP_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=$APP_DIR/backend
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/nicole-api-stdout.log
stderr_logfile=/var/log/supervisor/nicole-api-stderr.log
environment=PATH="$APP_DIR/.venv/bin:%(ENV_PATH)s",PYTHONPATH="$APP_DIR/backend"
EOF

# Worker service
cat > /etc/supervisor/conf.d/nicole-worker.conf << EOF
[program:nicole-worker]
command=$APP_DIR/.venv/bin/python worker.py
directory=$APP_DIR/backend
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/nicole-worker-stdout.log
stderr_logfile=/var/log/supervisor/nicole-worker-stderr.log
environment=PATH="$APP_DIR/.venv/bin:%(ENV_PATH)s",PYTHONPATH="$APP_DIR/backend"
EOF

supervisorctl reread
supervisorctl update
supervisorctl restart all || true

echo -e "${GREEN}✓${NC} Supervisor configured"
echo ""

# =============================================================================
# STEP 10: Configure Nginx
# =============================================================================
echo -e "${BLUE}[10/10]${NC} Configuring Nginx..."

# Copy existing nginx config if available
if [ -f "$APP_DIR/deploy/nginx.conf" ]; then
    cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/nicole-api
else
    cat > /etc/nginx/sites-available/nicole-api << 'EOF'
upstream nicole_api_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name api.nicole.alphawavetech.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://nicole_api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE/WebSocket timeouts
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }
    
    location /healthz {
        proxy_pass http://nicole_api_backend/healthz;
        proxy_read_timeout 10s;
    }
}
EOF
fi

ln -sf /etc/nginx/sites-available/nicole-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
echo -e "${GREEN}✓${NC} Nginx configured"
echo ""

# =============================================================================
# CONFIGURE FIREWALL
# =============================================================================
if command -v ufw &> /dev/null; then
    echo -e "${BLUE}Configuring firewall...${NC}"
    ufw allow OpenSSH
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "y" | ufw enable || true
    echo -e "${GREEN}✓${NC} Firewall configured"
    echo ""
fi

# =============================================================================
# RUN DATABASE MIGRATIONS
# =============================================================================
echo -e "${BLUE}Running database migrations...${NC}"

cd "$APP_DIR/backend"
source "$APP_DIR/.venv/bin/activate"

# Load env
set -a
source "$APP_DIR/.env" 2>/dev/null || true
source "$APP_DIR/tiger-nicole_db-credentials.env" 2>/dev/null || true
set +a

if [ -n "$TIGER_DATABASE_URL" ]; then
    for migration in database/migrations/0*.sql; do
        if [ -f "$migration" ]; then
            echo -e "  ${YELLOW}→${NC} Applying $(basename $migration)..."
            psql "$TIGER_DATABASE_URL" -f "$migration" 2>&1 | grep -v "already exists" || true
        fi
    done
    echo -e "${GREEN}✓${NC} Migrations complete"
else
    echo -e "${YELLOW}⚠${NC} Database URL not configured, skipping migrations"
fi
echo ""

# =============================================================================
# SETUP SSL
# =============================================================================
echo -e "${BLUE}Setting up SSL certificate...${NC}"
certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos -n 2>/dev/null || echo -e "${YELLOW}⚠${NC} SSL setup skipped (run manually if needed)"
echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   INITIAL SETUP COMPLETE!                     ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Domain: https://$DOMAIN"
echo ""
echo "Next Steps:"
echo "1. Edit API keys in .env:"
echo "   nano $APP_DIR/.env"
echo ""
echo "2. Restart services:"
echo "   supervisorctl restart all"
echo ""
echo "3. Test the API:"
echo "   curl https://$DOMAIN/healthz"
echo "   curl https://$DOMAIN/faz/health"
echo ""
echo "Logs:"
echo "   tail -f /var/log/supervisor/nicole-api-*.log"
echo ""
echo "Deploy updates:"
echo "   bash $APP_DIR/scripts/deploy/faz_deploy.sh"
echo ""

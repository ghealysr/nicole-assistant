#!/usr/bin/env bash
set -euo pipefail

# Usage: sudo bash deploy/install.sh --app-dir /opt/nicole --domain api.nicole.alphawavetech.com --email you@example.com

APP_DIR="/opt/nicole"
DOMAIN="api.nicole.alphawavetech.com"
EMAIL="admin@example.com"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir)
      APP_DIR="$2"; shift 2;;
    --domain)
      DOMAIN="$2"; shift 2;;
    --email)
      EMAIL="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [[ $(id -u) -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install.sh ..."
  exit 1
fi

apt-get update
apt-get install -y python3.11 python3.11-venv python3-pip nginx supervisor certbot python3-certbot-nginx git ca-certificates curl gnupg lsb-release

# Install Docker Engine + Compose plugin
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker ${SUDO_USER:-root} || true

mkdir -p "$APP_DIR"
chown -R "${SUDO_USER:-root}":"${SUDO_USER:-root}" "$APP_DIR"

# Copy project into APP_DIR if not already
if [[ ! -f "$APP_DIR/backend/app/main.py" ]]; then
  echo "Copying repository to $APP_DIR ..."
  rsync -a --exclude='.venv' --exclude='node_modules' ./ "$APP_DIR"/
fi

cd "$APP_DIR"
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# Ensure .env exists (user must provide real values)
if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "ENVIRONMENT=production" > "$APP_DIR/.env"
  echo "# Populate all required variables per docs/.env.template" >> "$APP_DIR/.env"
fi

# Bring up Redis and Qdrant
if command -v docker >/dev/null 2>&1; then
  docker compose -f "$APP_DIR/docker-compose.yml" up -d || true
fi

# Nginx config
cp deploy/nginx.conf /etc/nginx/sites-available/nicole_api
sed -i "s/@@DOMAIN@@/$DOMAIN/g" /etc/nginx/sites-available/nicole_api
ln -sf /etc/nginx/sites-available/nicole_api /etc/nginx/sites-enabled/nicole_api
nginx -t && systemctl reload nginx

# Supervisor configs
cp deploy/supervisor-nicole-api.conf /etc/supervisor/conf.d/nicole-api.conf
cp deploy/supervisor-nicole-worker.conf /etc/supervisor/conf.d/nicole-worker.conf
sed -i "s#@@APP_DIR@@#$APP_DIR#g" /etc/supervisor/conf.d/nicole-api.conf
sed -i "s#@@APP_DIR@@#$APP_DIR#g" /etc/supervisor/conf.d/nicole-worker.conf
supervisorctl reread
supervisorctl update
supervisorctl restart nicole-api || true
supervisorctl restart nicole-worker || true

# SSL via certbot
certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos -n || true

# UFW (optional)
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  echo "y" | ufw enable || true
fi

echo "Done. Visit https://$DOMAIN/healthz"

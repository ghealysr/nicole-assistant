#!/bin/bash
# =============================================================================
# NICOLE/FAZ CODE SSL SETUP
# =============================================================================
# Setup SSL certificates using Let's Encrypt.
#
# Usage:
#   bash /opt/nicole/scripts/deploy/faz_ssl_setup.sh
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

# ACTUAL VALUES
DOMAIN="api.nicole.alphawavetech.com"
EMAIL="glen@alphawavetech.com"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    SSL CERTIFICATE SETUP                      ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# =============================================================================
# STEP 1: Check DNS
# =============================================================================
echo -e "${BLUE}[1/4]${NC} Checking DNS..."

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com)
DNS_IP=$(dig +short "$DOMAIN" | head -1)

echo "  Server IP: $SERVER_IP"
echo "  DNS resolves to: $DNS_IP"

if [ "$SERVER_IP" != "$DNS_IP" ]; then
    echo -e "${YELLOW}⚠${NC} DNS may not be pointing to this server"
    echo "  Make sure your domain's A record points to $SERVER_IP"
else
    echo -e "${GREEN}✓${NC} DNS correctly configured"
fi
echo ""

# =============================================================================
# STEP 2: Install Certbot
# =============================================================================
echo -e "${BLUE}[2/4]${NC} Checking Certbot..."

if ! command -v certbot &> /dev/null; then
    echo "  Installing Certbot..."
    apt-get update -qq
    apt-get install -y -qq certbot python3-certbot-nginx
fi

echo -e "${GREEN}✓${NC} Certbot installed"
echo ""

# =============================================================================
# STEP 3: Obtain Certificate
# =============================================================================
echo -e "${BLUE}[3/4]${NC} Obtaining SSL certificate..."

certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos -n && {
    echo -e "${GREEN}✓${NC} SSL certificate obtained"
} || {
    echo -e "${RED}✗${NC} Certificate request failed"
    echo ""
    echo "Common issues:"
    echo "  1. DNS not pointing to this server"
    echo "  2. Port 80 blocked by firewall"
    echo "  3. Rate limit exceeded"
    exit 1
}
echo ""

# =============================================================================
# STEP 4: Setup Auto-Renewal
# =============================================================================
echo -e "${BLUE}[4/4]${NC} Setting up auto-renewal..."

# Create renewal hook
mkdir -p /etc/letsencrypt/renewal-hooks/post
cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF
chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh

# Test renewal
certbot renew --dry-run

echo -e "${GREEN}✓${NC} Auto-renewal configured"
echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  SSL SETUP COMPLETE!                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Your API is now available at:"
echo "  https://$DOMAIN"
echo ""
echo "Test endpoints:"
echo "  curl https://$DOMAIN/healthz"
echo "  curl https://$DOMAIN/faz/health"
echo ""
echo "Certificate details:"
certbot certificates 2>/dev/null | grep -A 5 "$DOMAIN" || true
echo ""

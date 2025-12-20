#!/bin/bash
# =============================================================================
# NICOLE/FAZ CODE SERVICE CONTROL
# =============================================================================
# Control individual services for Nicole/Faz Code.
#
# Usage:
#   bash /opt/nicole/scripts/deploy/faz_service_control.sh <command> [service]
#
# Commands:
#   start [service]     Start service(s)
#   stop [service]      Stop service(s)
#   restart [service]   Restart service(s)
#   status              Show all service status
#   logs [service]      Tail logs for service
#
# Services:
#   api       - FastAPI backend
#   worker    - Background worker
#   nginx     - Nginx reverse proxy
#   redis     - Redis cache (Docker)
#   qdrant    - Vector database (Docker)
#   mcp       - MCP Gateway (Docker)
#   all       - All services
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

APP_DIR="/opt/nicole"
COMMAND="${1:-status}"
SERVICE="${2:-all}"

# =============================================================================
# FUNCTIONS
# =============================================================================

log_action() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

start_service() {
    local svc="$1"
    log_action "Starting $svc..."
    
    case "$svc" in
        api)
            supervisorctl start nicole-api
            log_success "API started"
            ;;
        worker)
            supervisorctl start nicole-worker 2>/dev/null || log_error "Worker not configured"
            ;;
        nginx)
            systemctl start nginx
            log_success "Nginx started"
            ;;
        redis)
            docker start nicole-redis 2>/dev/null || \
                docker run -d --name nicole-redis -p 6379:6379 --restart unless-stopped redis:7-alpine redis-server --appendonly yes
            log_success "Redis started"
            ;;
        qdrant)
            docker start nicole-qdrant 2>/dev/null || \
                docker run -d --name nicole-qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage --restart unless-stopped qdrant/qdrant
            log_success "Qdrant started"
            ;;
        mcp)
            docker start mcp-gateway 2>/dev/null || log_error "MCP Gateway not configured"
            ;;
        all)
            start_service redis
            start_service qdrant
            start_service api
            start_service worker
            start_service nginx
            ;;
        *)
            log_error "Unknown service: $svc"
            exit 1
            ;;
    esac
}

stop_service() {
    local svc="$1"
    log_action "Stopping $svc..."
    
    case "$svc" in
        api)
            supervisorctl stop nicole-api 2>/dev/null || true
            log_success "API stopped"
            ;;
        worker)
            supervisorctl stop nicole-worker 2>/dev/null || true
            log_success "Worker stopped"
            ;;
        nginx)
            systemctl stop nginx 2>/dev/null || true
            log_success "Nginx stopped"
            ;;
        redis)
            docker stop nicole-redis 2>/dev/null || true
            log_success "Redis stopped"
            ;;
        qdrant)
            docker stop nicole-qdrant 2>/dev/null || true
            log_success "Qdrant stopped"
            ;;
        mcp)
            docker stop mcp-gateway 2>/dev/null || true
            log_success "MCP Gateway stopped"
            ;;
        all)
            stop_service nginx
            stop_service worker
            stop_service api
            stop_service mcp
            stop_service qdrant
            stop_service redis
            ;;
        *)
            log_error "Unknown service: $svc"
            exit 1
            ;;
    esac
}

restart_service() {
    local svc="$1"
    log_action "Restarting $svc..."
    
    case "$svc" in
        api)
            supervisorctl restart nicole-api
            log_success "API restarted"
            ;;
        worker)
            supervisorctl restart nicole-worker 2>/dev/null || log_error "Worker not configured"
            ;;
        nginx)
            nginx -t && systemctl reload nginx
            log_success "Nginx reloaded"
            ;;
        redis)
            docker restart nicole-redis 2>/dev/null || start_service redis
            log_success "Redis restarted"
            ;;
        qdrant)
            docker restart nicole-qdrant 2>/dev/null || start_service qdrant
            log_success "Qdrant restarted"
            ;;
        mcp)
            docker restart mcp-gateway 2>/dev/null || log_error "MCP Gateway not running"
            ;;
        all)
            restart_service redis
            restart_service qdrant
            restart_service api
            restart_service worker
            restart_service nginx
            ;;
        *)
            log_error "Unknown service: $svc"
            exit 1
            ;;
    esac
}

show_status() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    SERVICE STATUS                             ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Supervisor services
    echo -e "${BLUE}Supervisor Services:${NC}"
    supervisorctl status 2>/dev/null || echo "  Supervisor not running"
    echo ""
    
    # Docker services
    echo -e "${BLUE}Docker Services:${NC}"
    docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null | grep -E "nicole|redis|qdrant|mcp" || echo "  No Docker services"
    echo ""
    
    # Nginx
    echo -e "${BLUE}Nginx:${NC}"
    if systemctl is-active --quiet nginx; then
        echo -e "  ${GREEN}●${NC} nginx: active"
    else
        echo -e "  ${RED}○${NC} nginx: inactive"
    fi
    echo ""
    
    # Port check
    echo -e "${BLUE}Ports:${NC}"
    echo -n "  8000 (API):   "
    nc -z localhost 8000 2>/dev/null && echo -e "${GREEN}OPEN${NC}" || echo -e "${RED}CLOSED${NC}"
    echo -n "  6379 (Redis): "
    nc -z localhost 6379 2>/dev/null && echo -e "${GREEN}OPEN${NC}" || echo -e "${RED}CLOSED${NC}"
    echo -n "  6333 (Qdrant):"
    nc -z localhost 6333 2>/dev/null && echo -e "${GREEN}OPEN${NC}" || echo -e "${RED}CLOSED${NC}"
    echo -n "  80 (HTTP):    "
    nc -z localhost 80 2>/dev/null && echo -e "${GREEN}OPEN${NC}" || echo -e "${RED}CLOSED${NC}"
    echo -n "  443 (HTTPS):  "
    nc -z localhost 443 2>/dev/null && echo -e "${GREEN}OPEN${NC}" || echo -e "${RED}CLOSED${NC}"
    echo ""
    
    # Health checks
    echo -e "${BLUE}Health Checks:${NC}"
    
    API_HEALTH=$(curl -s -m 2 http://localhost:8000/healthz 2>/dev/null)
    if echo "$API_HEALTH" | grep -q "healthy"; then
        echo -e "  API:    ${GREEN}healthy${NC}"
    else
        echo -e "  API:    ${RED}unhealthy${NC}"
    fi
    
    FAZ_HEALTH=$(curl -s -m 2 http://localhost:8000/faz/health 2>/dev/null)
    if echo "$FAZ_HEALTH" | grep -q "healthy"; then
        echo -e "  Faz:    ${GREEN}healthy${NC}"
    else
        echo -e "  Faz:    ${YELLOW}check pending${NC}"
    fi
    echo ""
}

show_logs() {
    local svc="${1:-api}"
    
    case "$svc" in
        api)
            echo -e "${CYAN}Tailing API logs (Ctrl+C to exit)...${NC}"
            tail -f /var/log/supervisor/nicole-api-*.log
            ;;
        worker)
            echo -e "${CYAN}Tailing Worker logs (Ctrl+C to exit)...${NC}"
            tail -f /var/log/supervisor/nicole-worker-*.log
            ;;
        nginx)
            echo -e "${CYAN}Tailing Nginx logs (Ctrl+C to exit)...${NC}"
            tail -f /var/log/nginx/nicole-api-*.log /var/log/nginx/error.log 2>/dev/null || \
                tail -f /var/log/nginx/access.log /var/log/nginx/error.log
            ;;
        redis)
            echo -e "${CYAN}Tailing Redis logs (Ctrl+C to exit)...${NC}"
            docker logs -f nicole-redis 2>/dev/null || echo "Redis container not found"
            ;;
        qdrant)
            echo -e "${CYAN}Tailing Qdrant logs (Ctrl+C to exit)...${NC}"
            docker logs -f nicole-qdrant 2>/dev/null || echo "Qdrant container not found"
            ;;
        mcp)
            echo -e "${CYAN}Tailing MCP logs (Ctrl+C to exit)...${NC}"
            docker logs -f mcp-gateway 2>/dev/null || echo "MCP container not found"
            ;;
        all)
            echo -e "${CYAN}Tailing all logs (Ctrl+C to exit)...${NC}"
            tail -f /var/log/supervisor/nicole-*.log
            ;;
        *)
            log_error "Unknown service: $svc"
            exit 1
            ;;
    esac
}

# =============================================================================
# MAIN
# =============================================================================

case "$COMMAND" in
    start)
        start_service "$SERVICE"
        ;;
    stop)
        stop_service "$SERVICE"
        ;;
    restart)
        restart_service "$SERVICE"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$SERVICE"
        ;;
    help|--help|-h)
        echo "Nicole/Faz Service Control"
        echo ""
        echo "Usage: $0 <command> [service]"
        echo ""
        echo "Commands:"
        echo "  start [service]     Start service(s)"
        echo "  stop [service]      Stop service(s)"
        echo "  restart [service]   Restart service(s)"
        echo "  status              Show all service status"
        echo "  logs [service]      Tail logs for service"
        echo ""
        echo "Services:"
        echo "  api       FastAPI backend"
        echo "  worker    Background worker"
        echo "  nginx     Nginx reverse proxy"
        echo "  redis     Redis cache (Docker)"
        echo "  qdrant    Vector database (Docker)"
        echo "  mcp       MCP Gateway (Docker)"
        echo "  all       All services (default)"
        echo ""
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac

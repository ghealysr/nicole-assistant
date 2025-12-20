#!/bin/bash
# =============================================================================
# NICOLE/FAZ CODE - QUICK DEPLOY
# =============================================================================
# One-command deploy script for common scenarios.
#
# Usage:
#   ./quick_deploy.sh [action]
#
# Actions:
#   update      Pull latest code and restart (default)
#   full        Full deploy with migrations
#   status      Check system status
#   logs        View live logs
#   restart     Restart all services
#   backup      Create database backup
#   db          Database stats
#   connect     Connect to database
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-update}"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

case "$ACTION" in
    update)
        echo -e "${CYAN}🚀 Quick Update Deploy${NC}"
        bash "$SCRIPT_DIR/faz_deploy.sh"
        ;;
    
    full)
        echo -e "${CYAN}🚀 Full Deploy with Migrations${NC}"
        bash "$SCRIPT_DIR/faz_deploy.sh" --migrate
        ;;
    
    status)
        echo -e "${CYAN}📊 System Status${NC}"
        bash "$SCRIPT_DIR/faz_service_control.sh" status
        ;;
    
    logs)
        echo -e "${CYAN}📜 Live Logs${NC}"
        bash "$SCRIPT_DIR/faz_service_control.sh" logs api
        ;;
    
    restart)
        echo -e "${CYAN}🔄 Restarting Services${NC}"
        bash "$SCRIPT_DIR/faz_service_control.sh" restart all
        ;;
    
    backup)
        echo -e "${CYAN}💾 Creating Backup${NC}"
        bash "$SCRIPT_DIR/faz_database_ops.sh" backup
        ;;
    
    db)
        echo -e "${CYAN}📊 Database Stats${NC}"
        bash "$SCRIPT_DIR/faz_database_ops.sh" stats
        ;;
    
    connect)
        echo -e "${CYAN}🔌 Connecting to Database${NC}"
        bash "$SCRIPT_DIR/faz_database_ops.sh" connect
        ;;
    
    migrate)
        echo -e "${CYAN}🗃️ Running Migrations${NC}"
        bash "$SCRIPT_DIR/faz_database_ops.sh" migrate
        ;;
    
    ssl)
        echo -e "${CYAN}🔒 Setting up SSL${NC}"
        bash "$SCRIPT_DIR/faz_ssl_setup.sh"
        ;;
    
    help|--help|-h)
        echo "Nicole/Faz Quick Deploy"
        echo ""
        echo "Usage: $0 [action]"
        echo ""
        echo "Actions:"
        echo "  update      Pull latest and restart (default)"
        echo "  full        Full deploy with migrations"
        echo "  status      Check system status"
        echo "  logs        View live logs"
        echo "  restart     Restart all services"
        echo "  backup      Create database backup"
        echo "  db          Database stats"
        echo "  connect     Connect to database"
        echo "  migrate     Run migrations"
        echo "  ssl         Setup SSL certificate"
        echo ""
        ;;
    
    *)
        echo "Unknown action: $ACTION"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✓ Done${NC}"

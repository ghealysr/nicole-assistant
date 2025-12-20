# Nicole/Faz Code Deployment Scripts

Production-ready deployment scripts for Nicole V7 and Faz Code on DigitalOcean.

## Quick Reference

```bash
# On the droplet
cd /opt/nicole/scripts/deploy

# Most common commands:
./quick_deploy.sh update     # Pull & restart
./quick_deploy.sh status     # Check everything
./quick_deploy.sh logs       # View API logs
./quick_deploy.sh full       # Deploy + migrations
./quick_deploy.sh backup     # Backup database
```

## Initial Setup (First Time Only)

**1. Copy project to droplet:**
```bash
scp -r Nicole_Assistant root@YOUR_DROPLET_IP:/opt/nicole
```

**2. SSH and run setup:**
```bash
ssh root@YOUR_DROPLET_IP
bash /opt/nicole/scripts/deploy/faz_initial_setup.sh
```

**3. Edit API keys (the database URL is already configured):**
```bash
nano /opt/nicole/.env
# Add your ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
```

**4. Restart services:**
```bash
supervisorctl restart all
```

## Configuration

The scripts use these actual values:

| Setting | Value |
|---------|-------|
| App Directory | `/opt/nicole` |
| API Domain | `api.nicole.alphawavetech.com` |
| Frontend Domain | `nicole.alphawavetech.com` |
| Database | TimescaleDB Cloud (`h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565`) |

## Scripts

### `quick_deploy.sh` - Convenience Wrapper

```bash
./quick_deploy.sh update      # Pull latest & restart
./quick_deploy.sh full        # Deploy with migrations
./quick_deploy.sh status      # Check all services
./quick_deploy.sh logs        # Tail API logs
./quick_deploy.sh restart     # Restart all services
./quick_deploy.sh backup      # Backup database
./quick_deploy.sh db          # Database stats
./quick_deploy.sh connect     # Interactive psql
./quick_deploy.sh migrate     # Run migrations
./quick_deploy.sh ssl         # Setup SSL
```

### `faz_deploy.sh` - Full Deployment

```bash
bash faz_deploy.sh              # Standard deploy
bash faz_deploy.sh --migrate    # With migrations
bash faz_deploy.sh --restart    # Just restart (no git pull)
bash faz_deploy.sh --status     # Check status
bash faz_deploy.sh --logs       # View logs
bash faz_deploy.sh --rollback   # Rollback to previous commit
bash faz_deploy.sh --branch dev # Deploy specific branch
```

### `faz_service_control.sh` - Service Management

```bash
bash faz_service_control.sh status           # Show all status
bash faz_service_control.sh restart api      # Restart API
bash faz_service_control.sh restart all      # Restart everything
bash faz_service_control.sh logs api         # Tail API logs
bash faz_service_control.sh logs nginx       # Tail Nginx logs
bash faz_service_control.sh start redis      # Start Redis
bash faz_service_control.sh stop worker      # Stop worker
```

### `faz_database_ops.sh` - Database Operations

```bash
bash faz_database_ops.sh stats               # Show statistics
bash faz_database_ops.sh migrate             # Run migrations
bash faz_database_ops.sh migrate-status      # Check migration status
bash faz_database_ops.sh backup              # Create backup
bash faz_database_ops.sh restore <file>      # Restore backup
bash faz_database_ops.sh connect             # Interactive psql
bash faz_database_ops.sh query "SELECT ..."  # Run query
```

### `faz_ssl_setup.sh` - SSL Certificate

```bash
bash faz_ssl_setup.sh   # Setup Let's Encrypt for api.nicole.alphawavetech.com
```

## Directory Structure

```
/opt/nicole/
├── .env                              # Environment config
├── tiger-nicole_db-credentials.env   # Database credentials
├── .venv/                            # Python virtual environment
├── backend/
│   ├── app/
│   ├── database/migrations/
│   ├── requirements.txt
│   └── worker.py
├── frontend/
├── backups/                          # Database backups
└── scripts/deploy/
    ├── faz_initial_setup.sh
    ├── faz_deploy.sh
    ├── faz_service_control.sh
    ├── faz_database_ops.sh
    ├── faz_ssl_setup.sh
    ├── quick_deploy.sh
    └── README.md
```

## Services

| Service | Manager | Port |
|---------|---------|------|
| nicole-api | Supervisor | 8000 |
| nicole-worker | Supervisor | - |
| nginx | systemd | 80, 443 |
| nicole-redis | Docker | 6379 |
| nicole-qdrant | Docker | 6333 |
| mcp-gateway | Docker | 3100 |

## Logs

```bash
# API logs
tail -f /var/log/supervisor/nicole-api-stdout.log
tail -f /var/log/supervisor/nicole-api-stderr.log

# Worker logs
tail -f /var/log/supervisor/nicole-worker-stdout.log

# Nginx logs
tail -f /var/log/nginx/nicole-api-access.log
tail -f /var/log/nginx/nicole-api-error.log

# Docker logs
docker logs -f nicole-redis
docker logs -f nicole-qdrant
```

## Health Checks

```bash
# Local
curl http://localhost:8000/healthz
curl http://localhost:8000/faz/health

# External
curl https://api.nicole.alphawavetech.com/healthz
curl https://api.nicole.alphawavetech.com/faz/health
```

## Troubleshooting

### API Not Starting
```bash
# Check logs
tail -100 /var/log/supervisor/nicole-api-stderr.log

# Check .env
cat /opt/nicole/.env | grep -v PASSWORD | grep -v KEY

# Restart
supervisorctl restart nicole-api
```

### Database Connection Issues
```bash
# Test connection
bash /opt/nicole/scripts/deploy/faz_database_ops.sh connect

# Check credentials
cat /opt/nicole/tiger-nicole_db-credentials.env
```

### Port Already in Use
```bash
lsof -i :8000
kill -9 <PID>
supervisorctl restart nicole-api
```

## Environment Variables Required

The `.env` file needs these API keys (database is already configured):

```bash
# AI (required)
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-proj-...

# Auth (required for OAuth)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Deployment (optional but recommended)
GITHUB_TOKEN=ghp_...
VERCEL_TOKEN=...

# The database URL is already set in tiger-nicole_db-credentials.env
```

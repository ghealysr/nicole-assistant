# Nicole V7 - Production Runbooks
## December 10, 2025

Operational procedures for maintaining and troubleshooting Nicole V7 in production.

---

## 🎯 **Quick Reference**

### **System URLs**
- **Frontend**: https://nicole.alphawavetech.com
- **Backend API**: https://api.nicole.alphawavetech.com
- **Health Check**: https://api.nicole.alphawavetech.com/health
- **MCP Health**: https://api.nicole.alphawavetech.com/health/mcp
- **API Docs**: https://api.nicole.alphawavetech.com/docs

### **Production Server**
- **Host**: `root@138.197.93.24`
- **Domain**: `nicole.alphawavetech.com`
- **OS**: Ubuntu 24.04 LTS
- **Region**: DigitalOcean (New York)

### **Key Directories**
- **Backend**: `/opt/nicole/backend/`
- **Skills**: `/opt/nicole/backend/skills/`
- **Logs**: `/var/log/nicole-api.log`, `/var/log/nicole-api.err.log`
- **Environment**: `/opt/nicole/.env`
- **MCP Bridge**: `/opt/nicole/mcp/`
- **Data Mount**: `/opt/nicole/data/`

### **Process Management**
- **Backend**: Managed by `supervisorctl` (service: `nicole-api`)
- **MCP Bridge**: Docker Compose (`docker-compose.yml` in `/opt/nicole/mcp/`)
- **Frontend**: Hosted on Vercel

---

## 📘 **RUNBOOK 1: Backend Restart**

**When to use:** After code deployments, configuration changes, or service errors

### **Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Check current status
supervisorctl status

# Restart backend API
supervisorctl restart nicole-api

# Wait for startup
sleep 5

# Verify backend is running
supervisorctl status
curl http://localhost:8000/health

# Check logs for errors
tail -30 /var/log/nicole-api.log
tail -30 /var/log/nicole-api.err.log
```

### **Success Criteria**
- ✅ `supervisorctl status` shows `RUNNING`
- ✅ Health check returns `{"status": "healthy"}`
- ✅ No errors in logs

### **Troubleshooting**

**Issue:** Service fails to start
```bash
# Check detailed error logs
tail -100 /var/log/nicole-api.err.log

# Check if port 8000 is already in use
ss -tlnp | grep 8000

# Kill any conflicting processes
kill -9 $(lsof -t -i:8000)

# Restart
supervisorctl restart nicole-api
```

**Issue:** Import errors
```bash
# Activate venv and test imports
cd /opt/nicole/backend
source /opt/nicole/.venv/bin/activate
python3 -c "from app.main import app; print('OK')"

# Check for missing dependencies
pip install -r requirements.txt
```

---

## 📘 **RUNBOOK 2: MCP Bridge Restart**

**When to use:** After updating MCP tools, changing BRAVE_API_KEY, or MCP errors

### **Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Navigate to MCP directory
cd /opt/nicole/mcp

# Check current status
docker ps | grep nicole-mcp-bridge
docker logs nicole-mcp-bridge --tail 20

# Restart the bridge
docker compose down
docker compose up -d

# Verify restart
sleep 3
docker ps | grep nicole-mcp-bridge
docker logs nicole-mcp-bridge --tail 10

# Verify tools are loaded
curl -s http://localhost:3100/rpc \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | python3 -m json.tool

# Test Brave Search
curl -s http://localhost:3100/rpc \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "brave_web_search",
      "arguments": {"query": "test", "count": 1}
    },
    "id": 2
  }' | python3 -m json.tool
```

### **Success Criteria**
- ✅ Container status: `Up`
- ✅ Logs show: `MCP HTTP Bridge listening on port 3100`
- ✅ Logs show: `Brave API Key: configured`
- ✅ Tools list returns 3 tools
- ✅ Brave search test returns results (not 422 error)

### **Troubleshooting**

**Issue:** `BRAVE_API_KEY` not loading
```bash
# Verify key is in .env
grep BRAVE_API_KEY /opt/nicole/.env

# Export to shell environment
export BRAVE_API_KEY=$(grep BRAVE_API_KEY /opt/nicole/.env | cut -d '=' -f2)
echo $BRAVE_API_KEY

# Restart with exported variable
cd /opt/nicole/mcp
docker compose down
docker compose up -d

# Verify key in container
docker exec nicole-mcp-bridge env | grep BRAVE
```

**Issue:** Container fails to start
```bash
# Check Docker logs
docker logs nicole-mcp-bridge

# Check container exists
docker ps -a | grep nicole-mcp-bridge

# Remove and recreate
cd /opt/nicole/mcp
docker compose down
docker compose up -d --build
```

---

## 📘 **RUNBOOK 3: Database Migration**

**When to use:** After schema changes or adding new tables

### **Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Navigate to backend
cd /opt/nicole/backend

# Source environment variables
source /opt/nicole/.env

# Verify database connection
psql "$TIGER_DATABASE_URL" -c "SELECT NOW();"

# Run migration
psql "$TIGER_DATABASE_URL" -f database/migrations/<MIGRATION_FILE>.sql

# Verify migration
psql "$TIGER_DATABASE_URL" -c "\dt"  # List tables
psql "$TIGER_DATABASE_URL" -c "\d <TABLE_NAME>"  # Describe specific table

# Restart backend to pick up schema changes
supervisorctl restart nicole-api
```

### **Success Criteria**
- ✅ Migration completes without errors
- ✅ New tables/columns visible in database
- ✅ Backend restarts successfully
- ✅ No errors in API logs

### **Rollback Procedure**

If migration fails:
```bash
# Connect to database
psql "$TIGER_DATABASE_URL"

# Manually rollback changes
DROP TABLE IF EXISTS <TABLE_NAME>;
-- Or: ALTER TABLE <TABLE_NAME> DROP COLUMN <COLUMN_NAME>;

# Exit psql
\q

# Restart backend
supervisorctl restart nicole-api
```

---

## 📘 **RUNBOOK 4: Environment Variable Update**

**When to use:** Updating API keys, database URLs, or configuration

### **Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Backup current .env
cp /opt/nicole/.env /opt/nicole/.env.backup.$(date +%Y%m%d_%H%M%S)

# Edit .env file
nano /opt/nicole/.env
# Make changes, save with Ctrl+O, exit with Ctrl+X

# Verify changes
grep <VARIABLE_NAME> /opt/nicole/.env

# If changes affect MCP Bridge, export and restart
export BRAVE_API_KEY=$(grep BRAVE_API_KEY /opt/nicole/.env | cut -d '=' -f2)
cd /opt/nicole/mcp
docker compose down
docker compose up -d

# Restart backend API
supervisorctl restart nicole-api

# Verify services
curl http://localhost:8000/health
curl http://localhost:8000/health/mcp
```

### **Success Criteria**
- ✅ `.env` file updated
- ✅ Backup created
- ✅ Services restarted
- ✅ Health checks passing

### **Common Variables to Update**

```bash
# Database
TIGER_DATABASE_URL=postgres://user:pass@host:port/db?sslmode=require

# Google OAuth
GOOGLE_CLIENT_ID=<client_id>
GOOGLE_CLIENT_SECRET=<client_secret>
GOOGLE_ALLOWED_DOMAINS=alphawavetech.com
GOOGLE_ALLOWED_EMAILS=ghealysr@gmail.com

# MCP
BRAVE_API_KEY=<api_key>
MCP_GATEWAY_URL=http://127.0.0.1:3100
MCP_ENABLED=True

# Claude API
ANTHROPIC_API_KEY=<api_key>
CLAUDE_MODEL=claude-sonnet-4-20250514
```

---

## 📘 **RUNBOOK 5: Skill Run Fallback Recovery**

**When to use:** After database outage to replay skill runs from fallback logs

### **Background**
When Tiger Postgres is unavailable, skill runs are written to `skills/runs_fallback.jsonl`. This runbook recovers those runs once the database is back online.

### **Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Navigate to backend
cd /opt/nicole/backend

# Check if fallback file exists
ls -lh skills/runs_fallback.jsonl

# Preview first few runs
head -5 skills/runs_fallback.jsonl | python3 -m json.tool

# Activate venv
source /opt/nicole/.venv/bin/activate

# Create recovery script
cat > /tmp/recover_fallback.py << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/opt/nicole/backend')

from app.services.skill_run_service import skill_run_service

async def main():
    result = await skill_run_service.recover_fallback_records()
    print(f"Recovery result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Run recovery
python3 /tmp/recover_fallback.py

# Verify recovery
psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM skill_runs WHERE created_at > NOW() - INTERVAL '1 hour';"

# Backup fallback file
mv skills/runs_fallback.jsonl skills/runs_fallback.jsonl.recovered.$(date +%Y%m%d_%H%M%S)
```

### **Success Criteria**
- ✅ All fallback records recovered
- ✅ `skill_runs` table updated
- ✅ Fallback file backed up
- ✅ No duplicate entries

---

## 📘 **RUNBOOK 6: Python venv Cleanup**

**When to use:** Disk space running low due to skill venvs

### **Background**
Each Python skill creates an isolated venv. Over time, these can accumulate and consume disk space.

### **Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Check current disk usage
df -h /opt/nicole

# Navigate to venvs directory
cd /opt/nicole/backend/skills/.venvs

# List all venvs with sizes
du -sh * | sort -h

# List venvs by last access time
ls -lt

# Remove venvs for deleted skills
# (First, get list of active skill IDs from registry)
cd /opt/nicole/backend
python3 << 'EOF'
import json
with open('skills/registry.json') as f:
    registry = json.load(f)
active_skills = [s['id'] for s in registry.get('skills', [])]
print("Active skills:", active_skills)
EOF

# Remove venvs not in active list
cd /opt/nicole/backend/skills/.venvs
for venv_dir in */; do
    skill_id="${venv_dir%/}"
    # Check if skill_id is in active list (manual check)
    # If not active, remove:
    # rm -rf "$venv_dir"
done

# Or remove all venvs older than 30 days
find /opt/nicole/backend/skills/.venvs -type d -mtime +30 -exec rm -rf {} +

# Verify disk space recovered
df -h /opt/nicole
```

### **Success Criteria**
- ✅ Disk space freed
- ✅ Only active skill venvs remain
- ✅ Skills can still execute (venvs will be recreated on next run)

---

## 📘 **RUNBOOK 7: Frontend Deployment (Vercel)**

**When to use:** Deploying frontend changes

### **Procedure**

**Automatic Deployment:**
```bash
# On local machine
cd /Users/glenhealysr_1/Desktop/Nicole_Assistant

# Commit changes
git add frontend/
git commit -m "feat(frontend): <description>"
git push origin main

# Vercel automatically deploys on push to main
# Monitor at: https://vercel.com/ghealysr/nicole-assistant
```

**Manual Deployment:**
```bash
# Install Vercel CLI (if not installed)
npm install -g vercel

# Navigate to frontend
cd frontend

# Deploy to production
vercel --prod

# Or deploy to preview
vercel
```

### **Post-Deployment Verification**

```bash
# Check deployment status
curl -s https://nicole.alphawavetech.com | head -10

# Verify API connectivity
# (Open browser DevTools, check Network tab for API calls)

# Test authentication
# (Log in via Google OAuth)

# Check browser console for errors
```

### **Environment Variables (Vercel)**

Ensure these are set in Vercel project settings:
- `NEXT_PUBLIC_API_URL`: `https://api.nicole.alphawavetech.com`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`: `<client_id>`

### **Rollback Procedure**

```bash
# List recent deployments
vercel ls

# Rollback to previous deployment
vercel rollback <DEPLOYMENT_URL>
```

---

## 📘 **RUNBOOK 8: SSL Certificate Renewal**

**When to use:** SSL certificate expiring (Let's Encrypt certificates expire every 90 days)

### **Automatic Renewal**

Certbot should auto-renew certificates. Verify:

```bash
# SSH into production
ssh root@138.197.93.24

# Check certbot timer
systemctl status certbot.timer

# Test renewal (dry run)
certbot renew --dry-run
```

### **Manual Renewal (if automatic fails)**

```bash
# SSH into production
ssh root@138.197.93.24

# Stop nginx temporarily
systemctl stop nginx

# Renew certificate
certbot renew

# Restart nginx
systemctl start nginx

# Verify certificate
curl -vI https://nicole.alphawavetech.com 2>&1 | grep 'expire'
```

### **Success Criteria**
- ✅ Certificate renewed
- ✅ Nginx restarted
- ✅ HTTPS accessible
- ✅ No browser certificate warnings

---

## 📘 **RUNBOOK 9: Log Analysis & Debugging**

**When to use:** Investigating errors or performance issues

### **View Recent Logs**

```bash
# Backend API logs
tail -100 /var/log/nicole-api.log
tail -100 /var/log/nicole-api.err.log

# MCP Bridge logs
docker logs nicole-mcp-bridge --tail 100

# Nginx logs
tail -100 /var/log/nginx/access.log
tail -100 /var/log/nginx/error.log

# Supervisor logs
tail -100 /var/log/supervisor/supervisord.log
```

### **Search for Specific Errors**

```bash
# Search for authentication errors
grep -i "auth\|401\|unauthorized" /var/log/nicole-api.log | tail -20

# Search for database errors
grep -i "database\|postgres\|tiger" /var/log/nicole-api.log | tail -20

# Search for MCP errors
grep -i "mcp\|brave\|tool" /var/log/nicole-api.log | tail -20

# Search for specific error codes
grep "500\|503\|504" /var/log/nicole-api.log | tail -20
```

### **Follow Logs in Real-Time**

```bash
# Tail backend logs
tail -f /var/log/nicole-api.log

# Tail MCP Bridge logs
docker logs -f nicole-mcp-bridge

# Tail all logs simultaneously (using tmux)
tmux new-session \; \
  split-window -h \; \
  send-keys 'tail -f /var/log/nicole-api.log' C-m \; \
  split-window -v \; \
  send-keys 'docker logs -f nicole-mcp-bridge' C-m
```

### **Common Error Patterns**

| Error Pattern | Likely Cause | Solution |
|--------------|--------------|----------|
| `401 Unauthorized` | Invalid auth token | Re-authenticate via Google OAuth |
| `422 Unprocessable Entity` | Invalid API key (Brave) | Update `BRAVE_API_KEY` in `.env` |
| `500 Internal Server Error` | Backend exception | Check `/var/log/nicole-api.err.log` |
| `ConnectionRefusedError` | Service not running | Restart backend or MCP bridge |
| `psycopg2.OperationalError` | Database connection failed | Check `TIGER_DATABASE_URL` and network |
| `ModuleNotFoundError` | Missing Python dependency | `pip install -r requirements.txt` |

---

## 📘 **RUNBOOK 10: Database Backup & Restore**

**When to use:** Before major migrations or for disaster recovery

### **Backup Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Source environment
source /opt/nicole/.env

# Create backup directory
mkdir -p /opt/nicole/backups
cd /opt/nicole/backups

# Full database dump
pg_dump "$TIGER_DATABASE_URL" > nicole_backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip nicole_backup_*.sql

# Verify backup
ls -lh *.gz

# Optional: Download backup to local machine
exit
scp root@138.197.93.24:/opt/nicole/backups/nicole_backup_*.sql.gz ~/Downloads/
```

### **Restore Procedure**

```bash
# SSH into production
ssh root@138.197.93.24

# Source environment
source /opt/nicole/.env

# Stop backend to prevent writes during restore
supervisorctl stop nicole-api

# Navigate to backup directory
cd /opt/nicole/backups

# Decompress backup
gunzip nicole_backup_<timestamp>.sql.gz

# Restore database (WARNING: This will overwrite current data)
psql "$TIGER_DATABASE_URL" < nicole_backup_<timestamp>.sql

# Restart backend
supervisorctl start nicole-api

# Verify restoration
psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM memories;"
psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM conversations;"
```

### **Success Criteria**
- ✅ Backup file created and compressed
- ✅ Backup size reasonable (> 0 bytes)
- ✅ Restoration completes without errors
- ✅ Data counts match expected values

---

## 📘 **RUNBOOK 11: Performance Monitoring**

**When to use:** Regular health checks or investigating slowness

### **Check System Resources**

```bash
# SSH into production
ssh root@138.197.93.24

# CPU usage
top -bn1 | grep "Cpu(s)"

# Memory usage
free -h

# Disk usage
df -h

# Network connections
ss -s
```

### **Check API Performance**

```bash
# Test API response time
time curl -s https://api.nicole.alphawavetech.com/health > /dev/null

# Test database query time
time psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM memories;" > /dev/null

# Check active connections
psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';"
```

### **Check Process Status**

```bash
# Backend API process
ps aux | grep uvicorn

# MCP Bridge process
docker stats nicole-mcp-bridge --no-stream

# Nginx process
systemctl status nginx
```

### **Performance Benchmarks**

| Metric | Expected | Alert Threshold |
|--------|----------|----------------|
| API Health Check | < 500ms | > 2s |
| Database Query | < 100ms | > 500ms |
| Memory Usage | < 2GB | > 6GB |
| Disk Usage | < 50% | > 80% |
| CPU Usage | < 30% | > 80% |

---

## 🚨 **Emergency Procedures**

### **Complete System Restart**

Use this as a last resort:

```bash
# SSH into production
ssh root@138.197.93.24

# Stop all services
supervisorctl stop nicole-api
cd /opt/nicole/mcp && docker compose down
systemctl stop nginx

# Wait for clean shutdown
sleep 5

# Start services in order
systemctl start nginx
cd /opt/nicole/mcp && docker compose up -d
sleep 3
supervisorctl start nicole-api

# Wait for full startup
sleep 10

# Verify all services
systemctl status nginx
docker ps | grep nicole-mcp-bridge
supervisorctl status
curl http://localhost:8000/health
curl http://localhost:8000/health/mcp
```

### **Database Connection Pool Exhaustion**

```bash
# Check active connections
psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Kill idle connections (if needed)
psql "$TIGER_DATABASE_URL" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < NOW() - INTERVAL '5 minutes';"

# Restart backend to reset connection pool
supervisorctl restart nicole-api
```

### **Disk Space Critical**

```bash
# Find large files
du -sh /opt/nicole/* | sort -h | tail -10

# Clean up old logs
find /var/log -name "*.log" -mtime +30 -exec rm {} \;

# Clean up Docker
docker system prune -af

# Clean up skill venvs (see Runbook 6)
```

---

## 📞 **Escalation & Contact**

### **When to Escalate**
- Database is inaccessible for > 10 minutes
- SSL certificate expired and auto-renewal failed
- Disk usage > 90%
- Multiple services down simultaneously
- Security incident suspected

### **Escalation Contacts**
- **Primary**: Glen Healy (ghealysr@gmail.com)
- **Hosting**: DigitalOcean Support
- **Database**: Timescale Support (Tiger Postgres)
- **Frontend**: Vercel Support

### **Support Resources**
- **Tiger Postgres Docs**: https://docs.timescale.com/
- **Docker Docs**: https://docs.docker.com/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Vercel Docs**: https://vercel.com/docs

---

## 📝 **Maintenance Schedule**

### **Daily**
- [ ] Check health endpoints
- [ ] Review error logs
- [ ] Monitor disk usage

### **Weekly**
- [ ] Review performance metrics
- [ ] Check skill health
- [ ] Review backup status

### **Monthly**
- [ ] Update dependencies (`pip list --outdated`)
- [ ] Review and rotate logs
- [ ] Clean up old skill venvs
- [ ] Test disaster recovery procedures

### **Quarterly**
- [ ] Security audit
- [ ] Performance optimization review
- [ ] Backup and restore test
- [ ] Update documentation

---

**End of Production Runbooks**


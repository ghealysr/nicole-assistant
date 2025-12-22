# 🚀 Phase 1 Deployment - Quick Start Guide

**Status:** ✅ Ready to Deploy  
**Time Required:** ~15 minutes

---

## Prerequisites Checklist

- [ ] SSH access to `nicole-production` droplet
- [ ] Cloudinary account credentials
- [ ] PageSpeed API key (provided)
- [ ] Git repository access

---

## Step-by-Step Deployment

### 1. Get Cloudinary Credentials (5 min)

If you don't have a Cloudinary account:

```bash
# 1. Go to: https://cloudinary.com/users/register_free
# 2. Sign up (free tier: 25GB storage, 25GB bandwidth)
# 3. After signup, go to Dashboard
# 4. Copy these 3 values:
#    - Cloud Name
#    - API Key
#    - API Secret
```

### 2. Run Deployment Script (10 min)

```bash
cd /Users/glenhealysr_1/.cursor/worktrees/Nicole_Assistant/bsd

# Make script executable (if not already)
chmod +x PHASE_1_BACKEND_DEPLOYMENT.sh

# Run deployment
./PHASE_1_BACKEND_DEPLOYMENT.sh
```

**What it does:**
1. ✅ Runs database migration (creates 4 tables, adds 12 columns)
2. ✅ Pulls latest code to droplet
3. ✅ Installs Python dependencies (cloudinary)
4. ⚠️ **PAUSES** for you to add environment variables
5. ✅ Restarts Nicole API
6. ✅ Validates deployment

### 3. Add Environment Variables (Manual Step)

When the script pauses, SSH into the droplet and add these to `.env`:

```bash
# SSH into droplet
ssh root@nicole-production

# Edit .env
nano /opt/nicole/.env

# Add these lines at the bottom:
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
PAGESPEED_API_KEY=AIzaSyBCHN4ej7qDAwsGhLmZMs_wqd7fi5kSM6c

# Save and exit (Ctrl+X, Y, Enter)
```

Then return to the deployment script and press Enter to continue.

---

## Verification

After deployment completes, verify:

### 1. Health Check

```bash
curl https://nicole.alphawavetech.com/health/ping
# Expected: {"ping":"pong","timestamp":"..."}
```

### 2. Database Tables

```bash
psql "postgres://tsdbadmin:xb0lms8vqb9j8kj7@h5ry0v71x4.bhn85sck1d.tsdb.cloud.timescale.com:33565/tsdb?sslmode=require" \
  -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'vibe_%' ORDER BY tablename;"
```

Expected output:
```
vibe_activities
vibe_competitor_sites  ← NEW
vibe_files
vibe_inspirations
vibe_iterations        ← NEW
vibe_lessons
vibe_projects
vibe_qa_scores         ← NEW
vibe_uploads           ← NEW
```

### 3. Test Frontend

1. Go to: https://nicole.alphawavelabs.io
2. Log in
3. Navigate to Vibe Dashboard
4. Create a new project
5. Verify structured intake form appears
6. Fill out form and submit
7. Verify planning phase starts

---

## Troubleshooting

### Issue: "Database migration failed"

**Solution:**
```bash
# Check if tables already exist
psql "$TIGER_DB_URL" -c "\dt vibe_*"

# If migration was partially applied, it's safe to re-run
# The migration uses "IF NOT EXISTS" for idempotency
```

### Issue: "Cloudinary not configured"

**Solution:**
```bash
# Verify .env has correct values
ssh root@nicole-production
cat /opt/nicole/.env | grep CLOUDINARY

# Restart API to pick up new env vars
supervisorctl restart nicole-api
```

### Issue: "Health check failed"

**Solution:**
```bash
# Check API logs
ssh root@nicole-production
tail -f /opt/nicole/logs/api.log

# Check supervisor status
supervisorctl status nicole-api

# Restart if needed
supervisorctl restart nicole-api
```

### Issue: "Frontend shows old version"

**Solution:**
```bash
# Vercel auto-deploys on push to main
# Check deployment status: https://vercel.com/dashboard

# If needed, trigger manual deploy:
# 1. Go to Vercel dashboard
# 2. Select nicole-assistant project
# 3. Click "Redeploy" on latest deployment
```

---

## Post-Deployment Testing

### Manual Test Checklist

- [ ] **Intake:** Create project, fill structured form, submit
- [ ] **Upload:** Drag-and-drop logo, verify saved
- [ ] **Competitor:** Add competitor URL, verify saved
- [ ] **Planning:** Run planning, verify architecture appears
- [ ] **Approval:** Approve architecture, verify build starts
- [ ] **QA:** Run QA, verify Lighthouse scores display
- [ ] **Feedback:** Submit feedback, verify iteration created
- [ ] **History:** View iteration history, verify timeline

### Automated Tests (Future)

```bash
# Run backend tests
cd /opt/nicole/backend
source .venv/bin/activate
pytest tests/test_vibe_phase1.py

# Run frontend tests
cd /opt/nicole/frontend
npm test
```

---

## Rollback (If Needed)

If something goes wrong, rollback:

```bash
# 1. Rollback database
psql "$TIGER_DB_URL" -f backend/database/migrations/008_vibe_enhancements_ROLLBACK.sql

# 2. Rollback code
ssh root@nicole-production
cd /opt/nicole
git reset --hard HEAD~1
supervisorctl restart nicole-api

# 3. Rollback frontend
# Go to Vercel dashboard → Select previous deployment → "Promote to Production"
```

---

## Success Indicators

✅ **Deployment Successful If:**
- Health endpoint returns `{"ping":"pong"}`
- 4 new database tables exist
- Cloudinary configured (check logs)
- Frontend shows structured intake form
- No errors in API logs

---

## Support

### Logs

```bash
# API logs
ssh root@nicole-production 'tail -f /opt/nicole/logs/api.log'

# Supervisor logs
ssh root@nicole-production 'tail -f /var/log/supervisor/nicole-api-stderr.log'

# Database logs
# Check Tiger Cloud console: https://console.timescale.cloud
```

### Documentation

- **Frontend Audit:** `PHASE_1_FRONTEND_AUDIT.md`
- **Backend Architecture:** `PHASE_1_BACKEND_ARCHITECTURE.md`
- **Complete Summary:** `PHASE_1_COMPLETE_SUMMARY.md`

---

## Next Steps After Deployment

1. **Test full workflow** (intake → plan → build → QA → review)
2. **Monitor logs** for 24 hours
3. **Gather user feedback** from Glen
4. **Plan Phase 2** enhancements (chunked builds, TDD, etc.)

---

**Ready to Deploy?** Run: `./PHASE_1_BACKEND_DEPLOYMENT.sh`

**Questions?** Check `PHASE_1_COMPLETE_SUMMARY.md` for full details.

---

**Last Updated:** December 16, 2025  
**Deployment Script:** `PHASE_1_BACKEND_DEPLOYMENT.sh`  
**Estimated Time:** 15 minutes



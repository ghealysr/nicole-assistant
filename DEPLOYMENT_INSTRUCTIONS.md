# Deployment Instructions: Fix Main Chat & Vibe Dashboard

## CRITICAL: Anthropic Library Version

The server is running `anthropic==0.39.0` but Claude 4.5 models require `>=0.45.0`.

**Run on droplet:**

```bash
cd /opt/nicole && git fetch origin main && git reset --hard origin/main
source .venv/bin/activate
pip install --upgrade 'anthropic>=0.45.0'
supervisorctl restart nicole-api
sleep 5
curl -s http://localhost:8000/health/ping
```

## Verify Deployment

```bash
# 1. Check anthropic version
source .venv/bin/activate && pip show anthropic | grep Version

# 2. Check API logs for errors
tail -50 /var/log/supervisor/nicole-api.log

# 3. Test main chat endpoint
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message":"Hello Nicole"}' 2>&1 | head -c 500

# 4. Check Vibe health
curl -s http://localhost:8000/vibe/models/health \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

## What Was Fixed

1. ✅ **Model names corrected** to Claude 4.5 format
2. ✅ **Extended thinking disabled** in Vibe for fast iteration
3. ✅ **Robust JSON parsing** with fallback patterns
4. ✅ **Better error logging** for debugging

## What Still Needs Fixing

1. ❌ **Anthropic library upgrade** (CRITICAL - do this NOW)
2. ⚠️ **Real-time streaming for Vibe agents** (future enhancement)
3. ⚠️ **Rate limit tuning** (if issues persist)

## Expected Behavior After Fix

**Main Chat:**
- Should stream responses in real-time
- No "Unknown model" errors
- Nicole responds normally

**Vibe Dashboard:**
- Planning phase completes successfully  
- Architecture JSON is parsed correctly
- Agent Chat shows real activity
- Pipeline progresses through all phases

## If Issues Persist

Run diagnostics:

```bash
# Watch logs live while testing
tail -f /var/log/supervisor/nicole-api.log

# Check for specific errors
grep -i "unknown model\|thinking\|architecture" /var/log/supervisor/nicole-api.log | tail -20
```

Then share the output.


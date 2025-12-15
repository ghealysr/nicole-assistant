# Complete Fix Guide: Main Chat & Vibe Dashboard

## Issue Summary

The main chat appears non-functional with several console errors. Root causes identified:

1. **Old anthropic library** (0.39.0) incompatible with Claude 4.5 models
2. **Domain mismatch** - Accessing wrong URL or DNS not updated
3. **Legacy endpoint calls** - Frontend trying to call non-existent endpoints
4. **No real-time feedback** - Vibe agents not streaming updates

---

## FIX 1: Deploy Latest Code & Upgrade Anthropic

**On Droplet:**

```bash
# Step 1: Pull latest code (all recent fixes)
cd /opt/nicole && git fetch origin main && git reset --hard origin/main

# Step 2: Activate environment
source .venv/bin/activate

# Step 3: CRITICAL - Upgrade anthropic library
pip install --upgrade 'anthropic>=0.45.0'

# Step 4: Verify upgrade worked
pip show anthropic | grep "Version"
# Should show 0.45.0 or higher

# Step 5: Restart API
supervisorctl restart nicole-api

# Step 6: Wait for startup
sleep 10

# Step 7: Check health
curl -s http://localhost:8000/health/ping

# Step 8: Check logs for errors
tail -50 /var/log/supervisor/nicole-api.log | grep -i "error\|exception\|failed"
```

**Expected Output:**
```
Version: 0.45.0 (or higher)
{"ping":"pong","timestamp":"..."}
```

If you see model errors in logs, the library upgrade failed.

---

## FIX 2: Verify Domain & DNS

The console errors show requests to `https://nicole.alphawavetech.com` but Vercel is at `https://nicole.alphawavelabs.io`.

**Check which URL you're using:**

1. **Clear browser cache completely** (Cmd+Shift+Delete on Mac, select "Cached images and files")
2. **Navigate to:** `https://nicole.alphawavelabs.io`
3. **NOT:** `https://nicole.alphawavetech.com` (unless you've updated DNS)

**If you want to use .alphawavetech.com:**

1. Update DNS A/CNAME record to point to Vercel
2. Add domain to Vercel project settings
3. Update `NEXT_PUBLIC_API_URL` in Vercel environment variables

---

## FIX 3: Clear Legacy Endpoint Errors

The `/user/state` and `/chat/onboarding` endpoints don't exist. These errors are likely from:

**Option A: Browser Cache**
1. Open Dev Tools (F12)
2. Right-click refresh button
3. Select "Empty Cache and Hard Reload"
4. Or use Incognito/Private window

**Option B: Service Worker**  
1. Dev Tools → Application tab
2. Service Workers → Unregister any for nicole domain
3. Clear storage
4. Reload

**Option C: Browser Extension**
- Disable all extensions
- Test in clean browser profile

---

## FIX 4: Test Main Chat Functionality

After fixes above:

1. **Navigate to:** https://nicole.alphawavelabs.io
2. **Login with Google**
3. **Send message:** "Hello Nicole"
4. **Expected:**
   - No console errors
   - Message appears in chat
   - Nicole streams response word-by-word
   - No 422 or 500 errors

**If still broken:**

```bash
# On droplet, watch logs live while testing
tail -f /var/log/supervisor/nicole-api.log

# In another terminal, try direct API call
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message":"test"}' 2>&1 | head -c 500
```

Share the output if errors persist.

---

## FIX 5: Test Vibe Dashboard

1. Click "Vibe" in sidebar
2. Enter project description: "Build a portfolio website"
3. Click "Start Intake"
4. **Expected:**
   - Thinking phases show (Searching, Capturing screenshots)
   - Agent Chat shows live updates
   - Brief appears after intake
   - "Continue to Planning" button works
5. Click "Run Pipeline"
6. **Expected:**
   - Planning phase generates architecture
   - Build phase generates code files
   - QA phase reviews code
   - No "Failed to generate architecture" errors

**If pipeline fails:**

```bash
# Check backend logs
tail -100 /var/log/supervisor/nicole-api.log | grep -i "vibe\|planning\|architecture"

# Check model health
curl -s http://localhost:8000/vibe/models/health \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

---

## Verification Checklist

After running all fixes:

- [ ] Anthropic library >= 0.45.0
- [ ] API responds to /health/ping
- [ ] No startup errors in logs
- [ ] Accessing correct domain (alphawavelabs.io)
- [ ] Browser cache cleared
- [ ] No 422/500 errors in console
- [ ] Main chat accepts messages
- [ ] Nicole streams responses
- [ ] Vibe intake works
- [ ] Vibe pipeline completes planning

---

## Quick Debug Commands

If anything still fails, run these and share output:

```bash
# 1. Check API status
supervisorctl status nicole-api

# 2. Check anthropic version
source /opt/nicole/.venv/bin/activate && pip show anthropic

# 3. Check recent errors
tail -100 /var/log/supervisor/nicole-api.log | grep -E "ERROR|Exception|Failed"

# 4. Test Claude client directly
cd /opt/nicole && python3 -c "
from backend.app.integrations.alphawave_claude import claude_client
print(f'Sonnet: {claude_client.sonnet_model}')
print(f'Opus: {claude_client.opus_model}')
print('✅ Claude client initialized')
"

# 5. Check database connectivity
psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM messages LIMIT 1;"
```

---

## What Was Already Fixed

Recent commits fixed:
- ✅ Claude 4.5 model names (claude-sonnet-4-5-20250929, etc.)
- ✅ Extended thinking disabled in Vibe for speed
- ✅ Robust JSON parsing for architecture
- ✅ Agent chat display with real messages
- ✅ Better error logging throughout

The ONLY remaining critical fix is the anthropic library upgrade.

---

## If All Else Fails

If chat still doesn't work after ALL fixes:

1. Create a new test message via direct API call:

```bash
export TOKEN="your_jwt_token_here"

curl -N -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Hello Nicole, are you working?"}' 2>&1
```

2. Share the COMPLETE output (all errors, SSE events, etc.)

3. Share the last 200 lines of API logs:

```bash
tail -200 /var/log/supervisor/nicole-api.log
```

---

**Last Updated:** December 15, 2025  
**Priority:** Run FIX 1 immediately - this is the critical blocker


# Comprehensive Bug Report: Main Chat & Vibe Dashboard
**Date:** December 15, 2025  
**Status:** Non-Functional - Critical Issues Identified

---

## SUMMARY

Both the main Nicole chat and Vibe Dashboard are reported as non-functional. Below is a comprehensive audit of both systems with identified issues and fixes.

---

## 🔴 CRITICAL ISSUES

### 1. **Anthropic Library Version Mismatch** (HIGH PRIORITY)
**Location:** `backend/requirements.txt`  
**Issue:** The comment says "requires anthropic SDK >= 0.45.0 (currently 0.39.0)" but we're using Claude 4.5 models which require the latest SDK.

**Current:**
```
anthropic==0.39.0  # OLD VERSION
```

**Required:**
```
anthropic>=0.45.0  # For Claude 4.5 support
```

**Impact:**
- Main chat may fail with "Unknown model" errors
- Extended thinking parameter may cause TypeErrors
- Claude 4.5 models (claude-sonnet-4-5-20250929, claude-opus-4-5-20251101) may not be recognized

**Fix:** Upgrade anthropic library on the server

---

### 2. **Model Name Format Issue** (HIGH PRIORITY)
**Location:** `backend/app/integrations/alphawave_claude.py`, `backend/app/services/vibe_service.py`, `backend/app/services/model_orchestrator.py`

**Current Models:**
- `claude-sonnet-4-5-20250929` ✅ CORRECT per Anthropic docs
- `claude-opus-4-5-20251101` ✅ CORRECT per Anthropic docs
- `claude-haiku-4-5-20251001` ✅ CORRECT per Anthropic docs

**Status:** Model names are NOW correct after recent fixes.

**However:** The server's anthropic library version (0.39.0) may not recognize Claude 4.5 models.

---

### 3. **Extended Thinking Fallback Issues** (MEDIUM PRIORITY)
**Location:** `backend/app/integrations/alphawave_claude.py:107-130`

**Issue:** The fallback for unsupported `thinking` parameter catches TypeError but may not handle all cases.

**Current Code:**
```python
try:
    response = await self.async_client.messages.create(**kwargs)
except TypeError as e:
    if "thinking" in str(e) and use_thinking:
        logger.warning("[Claude] Extended thinking not supported, falling back")
        kwargs.pop("thinking", None)
        kwargs["temperature"] = temperature
        response = await self.async_client.messages.create(**kwargs)
```

**Problem:** If anthropic library is 0.39.0, this won't catch the error properly.

**Fix:** More robust error handling needed.

---

### 4. **Vibe Dashboard Architecture Parsing Failures** (HIGH PRIORITY)
**Location:** `backend/app/services/vibe_service.py:2786`

**Issue:** Architecture JSON parsing repeatedly fails, preventing pipeline from progressing.

**Root Causes:**
1. Claude 4.5 Opus may return thinking blocks that interfere with JSON extraction
2. Extended thinking was enabled (now disabled in latest commit)
3. JSON extraction regex patterns may not catch all formats

**Recent Fix Applied:**
- Disabled extended thinking in all Vibe phases ✅
- Added fallback regex patterns ✅
- Added detailed logging ✅

**Remaining Issue:** Need to see actual Claude response to debug further.

---

### 5. **Database Schema Mismatch** (POTENTIAL)
**Location:** `backend/app/routers/alphawave_chat.py:553-572`

**Issue:** Query uses `role` column:
```python
SELECT role, content, created_at FROM messages
```

**But earlier in the code (line 410):** We insert `message_role`:
```python
INSERT INTO messages (conversation_id, user_id, message_role, content, created_at)
```

**Status:** This was identified as a critical bug earlier. Let me verify current state.

---

## 🟡 MODERATE ISSUES

### 6. **Rate Limiting Too Aggressive**
**Location:** `backend/app/routers/alphawave_vibe.py:54`

**Current:** 30 requests/minute default, 60 for polling
**Issue:** User hitting rate limits frequently

**Recommendation:** Increase limits or implement smarter backoff

---

### 7. **No Real-time Chat Streaming Visibility in Vibe**
**Location:** `backend/app/services/vibe_service.py`

**Issue:** Agent activities are logged to database but not streamed in real-time to frontend
**User Feedback:** "no chat streaming, the updates are still station to station"

**Current Flow:**
1. Agent makes Claude call
2. Waits for complete response
3. Logs activity to database
4. Frontend polls every 2 seconds

**Better Flow:**
1. Agent streams thinking/response chunks
2. Backend emits SSE events in real-time
3. Frontend displays live updates

**Fix Needed:** Implement SSE streaming for Vibe agents (similar to main chat)

---

### 8. **Missing Error Details in Agent Console**
**Location:** `frontend/src/components/vibe/AlphawaveVibeWorkspace.tsx`

**Issue:** When architecture fails, user sees generic error without Claude's actual response

**Recent Fix:** Added logging to show first 300 chars of response ✅

**Still Needed:** Display this in the UI prominently

---

## 🟢 LOW PRIORITY ISSUES

### 9. **Memory Notification Acknowledgment Not Surfaced**
**Issue:** Nicole saves memories but doesn't acknowledge in chat
**Status:** Backend emits `memory_saved` SSE events, frontend displays them ✅

---

### 10. **Polling Interval Could Be Smarter**
**Location:** `frontend/src/lib/hooks/useVibeProject.ts:1356`

**Current:** Fixed 2-second polling during operations
**Better:** Exponential backoff when no changes, faster when active

---

## 📋 DIAGNOSTIC STEPS NEEDED

To identify the root cause of "main chat not functional", run on the droplet:

```bash
# 1. Check if API is running
supervisorctl status nicole-api

# 2. Check for startup errors
tail -100 /var/log/supervisor/nicole-api.log | grep -i "error\|exception\|failed"

# 3. Check anthropic library version
cd /opt/nicole && source .venv/bin/activate && pip show anthropic

# 4. Test Claude client manually
python3 -c "from app.integrations.alphawave_claude import claude_client; print(claude_client.sonnet_model)"

# 5. Try sending a test message and watch logs
tail -f /var/log/supervisor/nicole-api.log &
# Then send message from frontend

# 6. Check database connectivity
psql "$TIGER_DATABASE_URL" -c "SELECT COUNT(*) FROM messages;"
```

---

## 🔧 IMMEDIATE FIXES REQUIRED

### Priority 1: Upgrade Anthropic Library
```bash
cd /opt/nicole
source .venv/bin/activate
pip install --upgrade 'anthropic>=0.45.0'
supervisorctl restart nicole-api
```

### Priority 2: Fix Database Schema Column Name
Check if `messages` table uses `role` or `message_role`:
```bash
psql "$TIGER_DATABASE_URL" -c "\d messages"
```

If it's `message_role`, update the SELECT query in alphawave_chat.py.

### Priority 3: Add Real-time Streaming to Vibe
This requires significant refactoring but is essential for usability.

---

## 📊 SYSTEM HEALTH CHECKLIST

- [ ] Anthropic library >= 0.45.0
- [ ] Claude client initializes without errors
- [ ] Database `messages` table column name verified
- [ ] Main chat `/message` endpoint returns 200
- [ ] Vibe `/vibe/projects/{id}/planning` completes successfully
- [ ] Rate limits not triggering for normal usage
- [ ] Extended thinking disabled in Vibe (already done ✅)
- [ ] Model names correct (already done ✅)

---

## NEXT STEPS

1. **Deploy latest code** to droplet (model names + extended thinking fixes)
2. **Upgrade anthropic library** on server
3. **Run diagnostic steps** above to get actual error messages
4. **Fix any database schema mismatches**
5. **Test main chat** - send message and verify streaming works
6. **Test Vibe pipeline** - create project, run intake, run planning
7. **Implement SSE streaming for Vibe** (future enhancement)

---

**Last Updated:** December 15, 2025  
**Commits Applied:**
- 911dec4: Disabled extended thinking in Vibe
- 4296f41: Added robust JSON extraction
- 57a45f8: Restored correct Claude 4.5 model names



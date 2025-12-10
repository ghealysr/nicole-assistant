# Nicole V7 - End-to-End Testing Guide
## December 10, 2025

This guide provides comprehensive testing procedures for all Nicole V7 systems. Follow these tests to verify functionality after deployments, updates, or troubleshooting.

---

## 🎯 **Pre-Testing Checklist**

Before starting E2E tests, verify:

- [ ] Backend API is running (`curl https://api.nicole.alphawavetech.com/health`)
- [ ] Frontend is deployed (`https://nicole.alphawavetech.com`)
- [ ] You have valid Google OAuth credentials
- [ ] MCP Bridge is running (`docker ps | grep nicole-mcp-bridge`)
- [ ] Tiger Postgres is accessible

---

## 📋 **TEST SUITE 1: Authentication & Authorization**

### **Test 1.1: Google OAuth Login**

**Objective:** Verify Google OAuth authentication flow

**Steps:**
1. Navigate to `https://nicole.alphawavetech.com`
2. Click "Sign in with Google"
3. Select your Google account (must be `ghealysr@gmail.com` or `@alphawavetech.com`)
4. Verify redirect back to Nicole chat interface
5. Check that your name appears in the header

**Expected Results:**
- ✅ Google Sign-In button appears
- ✅ OAuth flow completes successfully
- ✅ Token is stored in `localStorage`
- ✅ User is redirected to `/chat`
- ✅ Header shows user name and avatar

**Failure Scenarios:**
- ❌ Button doesn't appear → Check `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in Vercel
- ❌ `origin_mismatch` error → Add domain to Google Cloud Console authorized origins
- ❌ Email not allowed → Check `GOOGLE_ALLOWED_EMAILS` in backend `.env`

**Backend Verification:**
```bash
# On production droplet
tail -50 /var/log/nicole-api.log | grep "Authentication\|OAuth"
```

---

### **Test 1.2: Protected Routes**

**Objective:** Verify unauthenticated users can't access protected routes

**Steps:**
1. Open incognito window
2. Try to navigate to `https://nicole.alphawavetech.com/chat`
3. Verify redirect to `/login`
4. Try to call API directly: `curl https://api.nicole.alphawavetech.com/api/memories`

**Expected Results:**
- ✅ Redirect to login page
- ✅ API returns `401 Unauthorized`

---

## 📋 **TEST SUITE 2: Chat System**

### **Test 2.1: Basic Chat Functionality**

**Objective:** Verify core chat features work end-to-end

**Steps:**
1. Log in to Nicole
2. Click "New conversation"
3. Send message: "Hello, can you introduce yourself?"
4. Observe:
   - Thinking animation appears
   - Response streams token-by-token
   - Message persists in chat history

**Expected Results:**
- ✅ Message sent successfully
- ✅ Thinking UI displays during processing
- ✅ Response streams smoothly (ChatGPT/Claude-style)
- ✅ Message saved to Tiger Postgres
- ✅ Conversation appears in sidebar

**Backend Verification:**
```bash
# Check conversation was created
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT conversation_id, title FROM conversations ORDER BY created_at DESC LIMIT 5;\""

# Check messages were saved
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT role, LEFT(content, 50) FROM messages WHERE conversation_id = <CONVERSATION_ID> ORDER BY created_at;\""
```

---

### **Test 2.2: Web Search Integration (MCP)**

**Objective:** Verify Nicole can perform real-time web searches via Brave API

**Steps:**
1. In an existing conversation, ask: "What are the latest AI news this week?"
2. Observe:
   - Thinking UI shows tool execution (`brave_web_search`)
   - Nicole returns current web results with URLs
   - Sources are cited

**Expected Results:**
- ✅ `brave_web_search` tool executes
- ✅ Real search results returned (not cached/stale)
- ✅ URLs are valid and current
- ✅ Nicole synthesizes information across sources

**Backend Verification:**
```bash
# Check MCP Bridge health
ssh root@138.197.93.24 "docker logs nicole-mcp-bridge --tail 20"

# Check backend tool execution
ssh root@138.197.93.24 "tail -30 /var/log/nicole-api.log | grep -i 'brave\|mcp\|tool'"

# Test MCP Bridge directly
ssh root@138.197.93.24 "curl -X POST http://localhost:3100/rpc \
  -H 'Content-Type: application/json' \
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"brave_web_search\",
      \"arguments\": {\"query\": \"AI news\", \"count\": 3}
    },
    \"id\": 1
  }' | python3 -m json.tool"
```

**Failure Scenarios:**
- ❌ 422 error → Invalid `BRAVE_API_KEY`
- ❌ "unknown_tool" → MCP client not routing correctly
- ❌ Timeout → MCP Bridge container not running

---

### **Test 2.3: Conversation Management**

**Objective:** Verify conversation CRUD operations

**Steps:**
1. Create 3 new conversations
2. Pin one conversation
3. Delete one conversation
4. Load conversation history

**Expected Results:**
- ✅ All conversations appear in sidebar
- ✅ Pinned conversation shows pin icon and stays at top
- ✅ Deleted conversation removed from list
- ✅ Loading old conversation restores full message history

**Backend Verification:**
```bash
# Check conversations
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT conversation_id, title, is_pinned, is_deleted FROM conversations WHERE user_id = 1 ORDER BY is_pinned DESC, updated_at DESC LIMIT 10;\""
```

---

## 📋 **TEST SUITE 3: Memory System**

### **Test 3.1: Memory Dashboard - Real Data**

**Objective:** Verify Memory Dashboard displays real backend data

**Steps:**
1. Click memory icon in header to open Memory Dashboard
2. Navigate to "Overview" tab
3. Verify stats show real numbers (not sample data "847 total")
4. Switch to "Memories" tab
5. Verify memories list displays actual user memories
6. Switch to "Documents" tab
7. Verify documents list is populated
8. Switch to "History" tab
9. Verify conversations are listed

**Expected Results:**
- ✅ Stats reflect actual database counts
- ✅ Memories list shows real memories (if any exist)
- ✅ Documents list shows uploaded files (if any exist)
- ✅ History shows actual conversations
- ✅ No "Preview Mode" banner when authenticated

**Backend Verification:**
```bash
# Check memory stats
curl -s https://api.nicole.alphawavetech.com/api/memories/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Check memories list
curl -s https://api.nicole.alphawavetech.com/api/memories?limit=10 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Check documents
curl -s https://api.nicole.alphawavetech.com/api/documents/list?limit=10 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Check conversations
curl -s https://api.nicole.alphawavetech.com/api/conversations?limit=10 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

### **Test 3.2: Memory Creation via Chat**

**Objective:** Verify Nicole can create memories during conversations

**Steps:**
1. In chat, say: "Remember that I prefer dark mode for all interfaces"
2. Observe thinking UI for `memory_store` tool execution
3. Open Memory Dashboard → Memories tab
4. Search for "dark mode"
5. Verify new memory appears

**Expected Results:**
- ✅ `memory_store` tool executes during response
- ✅ Memory saved to Tiger Postgres
- ✅ Memory appears in dashboard
- ✅ Memory type = "preference"
- ✅ Confidence score > 0.8

**Backend Verification:**
```bash
# Check memory was created
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT memory_id, memory_type, content, confidence_score FROM memories WHERE content ILIKE '%dark mode%' ORDER BY created_at DESC LIMIT 1;\""
```

---

### **Test 3.3: Memory Search via Chat**

**Objective:** Verify Nicole can search memories during conversations

**Steps:**
1. In chat, ask: "What do you remember about my preferences?"
2. Observe thinking UI for `memory_search` tool execution
3. Verify Nicole recalls previously stored memories

**Expected Results:**
- ✅ `memory_search` tool executes
- ✅ Nicole returns relevant memories
- ✅ Memories are ranked by relevance
- ✅ Memory types are mentioned (facts, preferences, etc.)

**Backend Verification:**
```bash
# Test memory search API directly
curl -s https://api.nicole.alphawavetech.com/api/memories/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "preferences",
    "limit": 5,
    "min_confidence": 0.3
  }' | python3 -m json.tool
```

---

## 📋 **TEST SUITE 4: Document System**

### **Test 4.1: Document Upload**

**Objective:** Verify document upload and processing pipeline

**Steps:**
1. Create a test document:
   ```bash
   echo "This is a test document for Nicole V7.
   
   Key Points:
   - Testing document upload
   - Verifying chunking
   - Checking search functionality
   
   Nicole should be able to find this content when I search for it." > test_document.txt
   ```
2. In Nicole chat, use file upload button
3. Select `test_document.txt`
4. Send message: "Please process this document"
5. Wait for processing complete message
6. Open Memory Dashboard → Documents tab
7. Verify document appears in list

**Expected Results:**
- ✅ File uploads successfully
- ✅ Document appears in Tiger Postgres
- ✅ Document is chunked
- ✅ Chunks are embedded
- ✅ Document status = "processed"
- ✅ Document appears in dashboard

**Backend Verification:**
```bash
# Check document was saved
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT doc_id, title, file_name, chunk_count, status FROM document_repository ORDER BY created_at DESC LIMIT 5;\""

# Check chunks were created
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT chunk_id, LEFT(content, 50) FROM document_chunks WHERE doc_id = <DOC_ID> LIMIT 5;\""
```

---

### **Test 4.2: Document Search via Chat**

**Objective:** Verify semantic search across uploaded documents

**Steps:**
1. In chat, ask: "Search my documents for information about testing"
2. Observe thinking UI for `document_search` tool execution
3. Verify Nicole returns relevant chunks from uploaded document

**Expected Results:**
- ✅ `document_search` tool executes
- ✅ Relevant chunks returned
- ✅ Document title is cited
- ✅ Search is semantic (not just keyword match)

**Backend Verification:**
```bash
# Test document search API directly
curl -s https://api.nicole.alphawavetech.com/api/documents/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "testing functionality",
    "limit": 3
  }' | python3 -m json.tool
```

---

## 📋 **TEST SUITE 5: Skills System**

### **Test 5.1: List Skills**

**Objective:** Verify skills can be listed via API and UI

**Steps:**
1. Open Memory Dashboard → Skills tab
2. Verify skills are listed (if any are installed)
3. Check status badges

**Expected Results:**
- ✅ Skills list displays
- ✅ Each skill shows: name, vendor, version, status
- ✅ Status badges show correct state (ready, needs_verification, etc.)

**Backend Verification:**
```bash
# List skills via API
curl -s https://api.nicole.alphawavetech.com/skills/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Check registry file
ssh root@138.197.93.24 "cat /opt/nicole/backend/skills/registry.json | python3 -m json.tool | head -50"
```

---

### **Test 5.2: Import Skill from GitHub**

**Objective:** Verify skill importer can clone and parse GitHub repositories

**Steps:**
1. Create a test skill repository or use an existing one
2. Run import command:
   ```bash
   curl -X POST https://api.nicole.alphawavetech.com/skills/import \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "source_url": "https://github.com/<username>/<skill-repo>",
       "vendor_trusted": false
     }'
   ```
3. Check response for success
4. Verify skill appears in dashboard

**Expected Results:**
- ✅ Repository clones successfully
- ✅ `SKILL.md` is parsed
- ✅ Skill metadata extracted
- ✅ Skill added to registry
- ✅ Skill appears in UI with status

**Backend Verification:**
```bash
# Check skill was added to registry
ssh root@138.197.93.24 "grep -A 20 '<skill-id>' /opt/nicole/backend/skills/registry.json"

# Check skill directory was created
ssh root@138.197.93.24 "ls -la /opt/nicole/backend/skills/<skill-id>/"
```

---

### **Test 5.3: Execute Python Skill**

**Objective:** Verify Python skills can execute in isolated venvs

**Steps:**
1. Import or use existing Python skill (e.g., `local-example-python-skill`)
2. Run health check via UI (click "Health Check" button in Skills tab)
3. Or execute via API:
   ```bash
   curl -X POST https://api.nicole.alphawavetech.com/skills/local-example-python-skill/run \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"input": "test"}'
   ```
4. Check response and logs

**Expected Results:**
- ✅ Skill executes successfully
- ✅ venv is created (if not trusted vendor)
- ✅ Dependencies installed automatically
- ✅ Output is returned
- ✅ Run logged to `skill_runs` table
- ✅ Log file created in `skills/logs/<skill_id>/`

**Backend Verification:**
```bash
# Check skill run was logged
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT run_id, skill_id, status, LEFT(output, 50) FROM skill_runs ORDER BY created_at DESC LIMIT 5;\""

# Check log file was created
ssh root@138.197.93.24 "ls -lt /opt/nicole/backend/skills/logs/local-example-python-skill/ | head -5"

# Check venv was created
ssh root@138.197.93.24 "ls -la /opt/nicole/backend/skills/.venvs/local-example-python-skill/"
```

---

### **Test 5.4: Skill Health Checks**

**Objective:** Verify scheduled health checks run automatically

**Steps:**
1. Wait for next scheduled health check (runs daily)
2. Or trigger manually via API:
   ```bash
   curl -X POST https://api.nicole.alphawavetech.com/skills/local-example-python-skill/health-check \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"run_tests": false, "auto_install_deps": true}'
   ```
3. Check logs for health check results

**Expected Results:**
- ✅ Health check runs successfully
- ✅ Skill status updated (ready, needs_configuration, etc.)
- ✅ Health notes populated
- ✅ `last_health_check_at` updated in registry

**Backend Verification:**
```bash
# Check APScheduler logs
ssh root@138.197.93.24 "tail -50 /var/log/nicole-api.log | grep -i 'health\|scheduler'"

# Check health check timestamp in registry
ssh root@138.197.93.24 "grep -A 5 'last_health_check_at' /opt/nicole/backend/skills/registry.json | head -10"
```

---

## 📋 **TEST SUITE 6: MCP File System Tools**

### **Test 6.1: Read File via Chat**

**Objective:** Verify `read_file` MCP tool works via Nicole's chat

**Steps:**
1. Create a test file on the production server:
   ```bash
   ssh root@138.197.93.24 "echo 'This is a test file for Nicole MCP tools.' > /opt/nicole/data/test_mcp.txt"
   ```
2. In Nicole chat, ask: "Read the file /data/test_mcp.txt"
3. Observe tool execution in thinking UI
4. Verify file content is returned

**Expected Results:**
- ✅ `read_file` tool executes
- ✅ File content returned correctly
- ✅ Nicole displays the content in response

**Backend Verification:**
```bash
# Test MCP tool directly
ssh root@138.197.93.24 "curl -X POST http://localhost:3100/rpc \
  -H 'Content-Type: application/json' \
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"read_file\",
      \"arguments\": {\"path\": \"/data/test_mcp.txt\"}
    },
    \"id\": 1
  }' | python3 -m json.tool"
```

---

### **Test 6.2: List Directory via Chat**

**Objective:** Verify `list_directory` MCP tool works

**Steps:**
1. In Nicole chat, ask: "List the files in /data/"
2. Observe tool execution
3. Verify directory listing is returned

**Expected Results:**
- ✅ `list_directory` tool executes
- ✅ File list returned
- ✅ Nicole displays files in response

**Backend Verification:**
```bash
# Test MCP tool directly
ssh root@138.197.93.24 "curl -X POST http://localhost:3100/rpc \
  -H 'Content-Type: application/json' \
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"list_directory\",
      \"arguments\": {\"path\": \"/data\"}
    },
    \"id\": 1
  }' | python3 -m json.tool"
```

---

## 📋 **TEST SUITE 7: Performance & Health**

### **Test 7.1: Backend Health Check**

**Objective:** Verify all backend services are operational

**Steps:**
1. Check main health endpoint:
   ```bash
   curl -s https://api.nicole.alphawavetech.com/health | python3 -m json.tool
   ```
2. Check MCP health endpoint:
   ```bash
   curl -s https://api.nicole.alphawavetech.com/health/mcp | python3 -m json.tool
   ```

**Expected Results:**
- ✅ Main health returns `{"status": "healthy"}`
- ✅ MCP health shows:
  - `"connected": true`
  - `"tool_count": 3`
  - Tools: `brave_web_search`, `read_file`, `list_directory`

---

### **Test 7.2: Database Connectivity**

**Objective:** Verify Tiger Postgres is accessible

**Steps:**
```bash
ssh root@138.197.93.24 "psql \"\$TIGER_DATABASE_URL\" -c \"SELECT NOW();\""
```

**Expected Results:**
- ✅ Connection successful
- ✅ Current timestamp returned

---

### **Test 7.3: Response Time**

**Objective:** Verify API response times are acceptable

**Steps:**
```bash
time curl -s https://api.nicole.alphawavetech.com/health > /dev/null
```

**Expected Results:**
- ✅ Response time < 500ms

---

## 🚨 **Common Issues & Solutions**

### **Issue: 401 Unauthorized on all API calls**
**Cause:** Invalid or expired Google OAuth token
**Solution:**
1. Log out and log back in
2. Check token in `localStorage`: `console.log(localStorage.getItem('google_auth_token'))`
3. Verify backend `GOOGLE_CLIENT_ID` matches frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

### **Issue: Memory Dashboard shows "Preview Mode"**
**Cause:** No auth token available
**Solution:**
1. Verify user is logged in
2. Check `authToken` prop is passed to dashboard component
3. Check browser console for errors

### **Issue: Brave Search returns 422 error**
**Cause:** Invalid `BRAVE_API_KEY`
**Solution:**
1. Obtain new key from https://brave.com/search/api/
2. Update `/opt/nicole/.env`: `BRAVE_API_KEY=<new_key>`
3. Restart MCP bridge: `cd /opt/nicole/mcp && docker compose restart`
4. Verify: `docker exec nicole-mcp-bridge env | grep BRAVE`

### **Issue: Skills not appearing in dashboard**
**Cause:** Empty registry or API failure
**Solution:**
1. Check registry: `cat /opt/nicole/backend/skills/registry.json`
2. Import a test skill via API
3. Check backend logs: `tail -50 /var/log/nicole-api.log | grep -i skill`

### **Issue: Document search returns no results**
**Cause:** No documents uploaded or embeddings not generated
**Solution:**
1. Upload a test document via UI
2. Check document was chunked: `psql "$TIGER_DATABASE_URL" -c "SELECT doc_id, chunk_count FROM document_repository LIMIT 5;"`
3. Check embeddings exist: `psql "$TIGER_DATABASE_URL" -c "SELECT chunk_id FROM document_chunks WHERE embedding IS NOT NULL LIMIT 5;"`

---

## ✅ **Test Completion Checklist**

After completing all tests, verify:

- [ ] Authentication working (Google OAuth)
- [ ] Chat system functional (messages, streaming, history)
- [ ] Web search via Brave API working
- [ ] Memory Dashboard displays real data
- [ ] Memory creation via chat working
- [ ] Memory search via chat working
- [ ] Document upload and search working
- [ ] Skills can be listed and executed
- [ ] MCP file tools working (read_file, list_directory)
- [ ] All health checks passing
- [ ] No errors in backend logs
- [ ] No errors in browser console

---

## 📝 **Test Results Documentation**

When completing tests, document results in this format:

```
Test Date: YYYY-MM-DD
Tester: [Name]
Environment: Production (nicole.alphawavetech.com)

Test Suite 1 (Authentication): ✅ PASS
Test Suite 2 (Chat System): ✅ PASS
Test Suite 3 (Memory System): ⚠️ PARTIAL PASS
  - Test 3.1: ✅ PASS
  - Test 3.2: ❌ FAIL - Memory not created (see issue #123)
  - Test 3.3: ✅ PASS
Test Suite 4 (Document System): ✅ PASS
Test Suite 5 (Skills System): ⚠️ NOT TESTED
Test Suite 6 (MCP Tools): ✅ PASS
Test Suite 7 (Performance): ✅ PASS

Overall Status: 85% Pass Rate
Critical Issues: [List any blocking issues]
Next Steps: [Actions required]
```

---

**End of E2E Testing Guide**


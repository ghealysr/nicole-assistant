# **FAZ CODE DEPLOYMENT & PREVIEW AUDIT**
**Date:** December 21, 2025  
**Status:** ⚠️ CRITICAL GAPS IDENTIFIED

---

## 🎯 **EXECUTIVE SUMMARY**

The Faz Code system has **GitHub and Vercel integration services** in place, but they are **NOT CONNECTED to the orchestrator pipeline**. This means:

- ❌ **No automatic deployment** after QA completion
- ❌ **No live preview URLs** generated
- ⚠️ **Static placeholder preview** only
- ⚠️ **Manual deployment required**

---

## 📊 **CURRENT STATE ANALYSIS**

### **1. GitHub Integration** ✅ **Service Exists**

**File:** `backend/app/services/faz_github_service.py`

**Capabilities:**
- ✅ Create repositories in org/user account
- ✅ Commit multiple files (atomic multi-file commits)
- ✅ Create branches
- ✅ Get repository info
- ✅ Delete repositories

**Configuration:**
- `GITHUB_TOKEN`: Required (from `.env`)
- `GITHUB_ORG`: Optional, defaults to `"alphawave-sites"`

**Status:** 🟡 **Service ready, but NOT integrated into pipeline**

---

### **2. Vercel Integration** ✅ **Service Exists**

**File:** `backend/app/services/faz_vercel_service.py`

**Capabilities:**
- ✅ Create Vercel projects from GitHub repos
- ✅ Trigger deployments
- ✅ Get deployment status
- ✅ Set environment variables
- ✅ Delete projects

**Configuration:**
- `VERCEL_TOKEN`: Required (from `.env`)
- `VERCEL_TEAM_ID`: Optional

**Status:** 🟡 **Service ready, but NOT integrated into pipeline**

---

### **3. Orchestrator Pipeline** ❌ **Deployment Phase Missing**

**File:** `backend/app/services/faz_orchestrator.py`

**Current Pipeline Flow:**
```
User Prompt → Nicole (Route)
             ↓
   ┌────────────────────────────┐
   │  planning ← → research     │
   │      ↓                     │
   │   design                   │
   │      ↓                     │
   │   coding ← → qa (loop)     │
   │      ↓                     │
   │   review                   │
   │      ↓                     │
   │   memory → DONE ⚠️         │ ← NO DEPLOYMENT STEP!
   └────────────────────────────┘
```

**What's Missing:**
1. **No deployment agent** in orchestrator
2. **No GitHub service calls** after QA approval
3. **No Vercel service calls** for deployment
4. **No preview URL updates** in database

**Gate System:**
- ✅ `awaiting_qa_approval` status exists
- ❌ No deployment trigger after approval
- ❌ No `awaiting_deploy_approval` gate

---

### **4. Preview System** 🟡 **Placeholder Only**

**File:** `frontend/src/lib/faz/preview-utils.ts`

**Current Behavior:**
```typescript
// Generates a STATIC placeholder that shows:
// "⚡ Preview Mode"
// "This is a static preview. Full interactivity requires deployment."
// "25 files generated • Deploy to see live preview"
```

**What's Missing:**
1. **No `preview_url`** field populated from Vercel
2. **No live iframe** of deployed site
3. **No deployment status tracking**

**PreviewFrame Component:**
- Checks for `currentProject.preview_url` (always null)
- Falls back to static HTML placeholder
- Never shows live site

---

## 🔍 **DATABASE SCHEMA ANALYSIS**

### **faz_projects Table**

**Existing Fields:**
```sql
github_repo TEXT           -- ✅ Exists (can store GitHub URL)
production_url TEXT        -- ✅ Exists (can store Vercel URL)
vercel_project_id TEXT     -- ✅ Exists (can store Vercel project ID)
status VARCHAR(50)         -- ✅ Exists (includes "deployed", "deploying")
```

**Deployment Flow States:**
```sql
-- QA complete:
status = 'awaiting_qa_approval'

-- User approves:
status = 'deploying' (should transition here, but doesn't)

-- GitHub + Vercel complete:
status = 'deployed'
github_repo = 'https://github.com/alphawave-sites/faz-project-123'
production_url = 'https://faz-project-123.vercel.app'
vercel_project_id = 'prj_abc123'
```

**Current Reality:**
- Status stuck at `qa` or `awaiting_qa_approval`
- `github_repo`, `production_url`, `vercel_project_id` always NULL
- No code to update these fields after deployment

---

## 🚨 **CRITICAL GAPS**

### **Gap #1: No Deployment Agent**
**Impact:** Projects never get deployed automatically.

**Current Orchestrator:**
```python
# Line 91 in faz_orchestrator.py
NEXT_AGENT_MAP = {
    "nicole": "planning",
    "research": "planning",
    "planning": "design",
    "design": "coding",
    "coding": "qa",
    "qa": "coding",         # Loops back to coding
    "review": "memory",     # Goes to memory, then DONE
    # ❌ NO "memory" → "deploy" mapping!
}
```

### **Gap #2: No Approval → Deploy Transition**
**Impact:** Even when user approves QA, nothing triggers deployment.

**Expected Flow:**
```
QA Complete → awaiting_qa_approval
               ↓
          User Approves ✓
               ↓
          status = 'deploying'
               ↓
      [MISSING: Deploy Agent]
               ↓
      GitHub: Create repo + commit files
               ↓
      Vercel: Create project + trigger deploy
               ↓
      Update: github_repo, production_url, vercel_project_id
               ↓
          status = 'deployed'
```

**Actual Flow:**
```
QA Complete → awaiting_qa_approval
               ↓
          User Approves ✓
               ↓
          status = 'review' (or stuck at 'qa')
               ↓
          [NOTHING HAPPENS]
```

### **Gap #3: No Preview URL Generation**
**Impact:** Users never see their live deployed site.

**Expected:**
1. Deploy to Vercel
2. Get preview URL: `https://faz-project-123.vercel.app`
3. Update database: `production_url = preview_url`
4. Frontend displays live site in iframe

**Actual:**
1. No deployment occurs
2. `production_url` stays NULL
3. Frontend shows placeholder: "Deploy to see live preview"

### **Gap #4: No Deployment Status Tracking**
**Impact:** Users don't know if deployment succeeded/failed.

**Expected:**
- Deployment progress: "Creating GitHub repo...", "Deploying to Vercel...", "Live!"
- Deployment errors: "GitHub API failed", "Vercel build error"
- Real-time status updates via WebSocket

**Actual:**
- No deployment activity logging
- No deployment error handling
- No status updates

---

## 🛠️ **IMPLEMENTATION REQUIREMENTS**

### **Phase 1: Add Deployment Agent**

**Create:** `backend/app/services/faz_agents/deploy.py`

**Responsibilities:**
1. Call `deploy_project_to_github(project_id, user_id)`
2. Extract `github_repo` URL from result
3. Call `deploy_project_to_vercel(project_id, user_id, github_repo)`
4. Update project with `production_url`, `vercel_project_id`
5. Set status to `'deployed'` on success
6. Set status to `'failed'` on error (with error logging)

**Agent Type:** `route` (simple orchestration, no LLM needed)

### **Phase 2: Wire Deployment into Orchestrator**

**File:** `backend/app/services/faz_orchestrator.py`

**Changes:**
```python
# Line 91 - Update NEXT_AGENT_MAP
NEXT_AGENT_MAP = {
    # ... existing mappings ...
    "review": "deploy",     # Changed from "memory"
    "deploy": "memory",     # New mapping
}

# Line 400+ - Add deployment handling in _run_pipeline_segment
async def _run_pipeline_segment(self, ...):
    # ...
    elif self.state["current_agent"] == "deploy":
        # Import deployment functions
        from app.services.faz_github_service import deploy_project_to_github
        from app.services.faz_vercel_service import deploy_project_to_vercel
        
        await self._log_activity("deploy", "route", "Starting deployment to GitHub + Vercel...")
        
        # Deploy to GitHub
        github_result = await deploy_project_to_github(self.project_id, self.user_id)
        if github_result.get("error"):
            await self._log_activity("deploy", "error", f"GitHub deployment failed: {github_result['error']}")
            await self._update_project_status("failed")
            return
        
        github_repo = github_result["github_url"]
        await self._log_activity("deploy", "complete", f"GitHub repo created: {github_repo}")
        
        # Deploy to Vercel
        vercel_result = await deploy_project_to_vercel(
            self.project_id, 
            self.user_id, 
            github_result["repo_name"]
        )
        if vercel_result.get("error"):
            await self._log_activity("deploy", "error", f"Vercel deployment failed: {vercel_result['error']}")
            await self._update_project_status("failed")
            return
        
        await self._log_activity("deploy", "complete", f"Deployed to Vercel: {vercel_result['production_url']}")
        
        # Move to memory/learnings phase
        self.state["current_agent"] = "memory"
```

### **Phase 3: Frontend Preview Integration**

**File:** `frontend/src/components/faz/PreviewFrame.tsx`

**Current Issue:**
```typescript
{currentProject?.preview_url ? (
  <iframe src={currentProject.preview_url} ... />
) : previewHtml ? (
  <iframe srcDoc={previewHtml} ... />
) : (
  <div>No preview available yet</div>
)}
```

**Fix:** Use `production_url` field:
```typescript
{currentProject?.production_url ? (
  <iframe src={currentProject.production_url} ... />
) : currentProject?.preview_url ? (
  <iframe src={currentProject.preview_url} ... />
) : (
  <div>
    <p>Deployment in progress...</p>
    <p>Preview will appear when ready</p>
  </div>
)}
```

### **Phase 4: Environment Variables**

**Required in `.env` on Droplet:**
```bash
# GitHub Integration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_ORG=alphawave-sites

# Vercel Integration
VERCEL_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VERCEL_TEAM_ID=team_xxxxxxxxxxxxxxxxxxxx  # Optional
```

**Verification Commands:**
```bash
# Test GitHub API
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user

# Test Vercel API
curl -H "Authorization: Bearer $VERCEL_TOKEN" https://api.vercel.com/v2/user
```

---

## 🎯 **RECOMMENDED ACTION PLAN**

### **Priority 1: Verify Environment Variables** 🔴 **URGENT**
- [ ] SSH into droplet
- [ ] Check if `GITHUB_TOKEN` and `VERCEL_TOKEN` are set
- [ ] Test API connectivity
- [ ] Add tokens if missing

### **Priority 2: Implement Deployment Agent** 🟡 **HIGH**
- [ ] Create `backend/app/services/faz_agents/deploy.py`
- [ ] Implement `run()` method with GitHub + Vercel calls
- [ ] Add error handling and logging

### **Priority 3: Wire into Orchestrator** 🟡 **HIGH**
- [ ] Update `NEXT_AGENT_MAP` to include deploy step
- [ ] Add deployment logic in `_run_pipeline_segment`
- [ ] Test full pipeline: Create → Code → QA → Deploy

### **Priority 4: Frontend Preview Updates** 🟢 **MEDIUM**
- [ ] Update `PreviewFrame.tsx` to use `production_url`
- [ ] Add deployment status indicators
- [ ] Handle deployment errors gracefully

### **Priority 5: Manual Deployment Functions** 🟢 **MEDIUM**
- [ ] Add API endpoint: `POST /faz/projects/{id}/deploy`
- [ ] Add UI button: "Deploy Now"
- [ ] Allow manual deployment trigger

---

## 📋 **TESTING CHECKLIST**

### **Once Implemented:**
1. ✅ Create new Faz project
2. ✅ Run pipeline through QA
3. ✅ Verify `github_repo` is populated
4. ✅ Verify `production_url` is populated
5. ✅ Verify `vercel_project_id` is populated
6. ✅ Check GitHub for new repo with files
7. ✅ Check Vercel for new project
8. ✅ Visit `production_url` and see live site
9. ✅ Verify preview iframe shows live site

### **Error Scenarios:**
1. ✅ Invalid GitHub token → Graceful error
2. ✅ Invalid Vercel token → Graceful error
3. ✅ GitHub API down → Retry logic
4. ✅ Vercel build fails → Error logged

---

## 🔐 **SECURITY CONSIDERATIONS**

1. **Token Security:**
   - Tokens stored in `.env` (not git)
   - Never log full tokens
   - Use environment variables, not hardcoded

2. **Repository Permissions:**
   - GitHub token needs `repo` scope
   - Vercel token needs `projects:write` scope
   - Use least-privilege principle

3. **Public vs Private Repos:**
   - Current config: Public repos by default
   - Consider adding privacy option per user/project

---

## 💡 **CURRENT WORKAROUND**

**Until Deployment is Implemented:**

1. **Manual GitHub Upload:**
   - Export files from database
   - Create GitHub repo manually
   - Push files

2. **Manual Vercel Deploy:**
   - Connect GitHub repo to Vercel
   - Deploy from Vercel dashboard

3. **Manual Preview URL Update:**
   ```sql
   UPDATE faz_projects 
   SET production_url = 'https://your-site.vercel.app',
       github_repo = 'https://github.com/user/repo'
   WHERE project_id = 26;
   ```

---

## 📊 **EFFORT ESTIMATE**

| Task | Complexity | Time | Risk |
|------|------------|------|------|
| Verify env vars | Low | 15 min | Low |
| Create deploy agent | Medium | 2 hours | Low |
| Wire into orchestrator | Medium | 2 hours | Medium |
| Frontend preview updates | Low | 1 hour | Low |
| Testing & debugging | Medium | 2 hours | Medium |
| **TOTAL** | **Medium** | **~7 hours** | **Low-Medium** |

---

## ✅ **CONCLUSION**

**Nicole CAN deploy to GitHub and Vercel** — all the infrastructure is there. The problem is that it's **NOT WIRED INTO THE PIPELINE**.

### **What Exists:**
✅ GitHub service (create repos, commit files)  
✅ Vercel service (create projects, trigger deploys)  
✅ Database fields (github_repo, production_url, vercel_project_id)  
✅ Preview component (ready to display live URLs)

### **What's Missing:**
❌ Deployment agent  
❌ Orchestrator integration  
❌ Automatic deployment after QA approval  
❌ Preview URL generation

### **Next Steps:**
1. Verify `GITHUB_TOKEN` and `VERCEL_TOKEN` are configured on droplet
2. Implement deployment agent
3. Wire into orchestrator pipeline
4. Test end-to-end flow

**With these fixes, Faz Code will have FULL deployment capabilities!** 🚀



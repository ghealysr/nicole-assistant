# WORKFLOW ENGINE - IMPLEMENTATION PLAN

**Date:** December 20, 2025  
**Engineering Standard:** Anthropic Production Quality  
**Timeline:** Phase 1 (Immediate) + Phase 2 (Short-term)

---

## EXECUTIVE SUMMARY

This plan implements a production-quality workflow engine for Nicole V7 that enables:
- **Automatic tool chaining** - Multi-step workflows execute without manual intervention
- **Screenshot post-processing** - Screenshots auto-upload to Cloudinary
- **Progress streaming** - Real-time workflow status updates to frontend
- **Pre-built templates** - Common workflows (screenshot, research, scraping) ready to use
- **Error recovery** - Graceful handling of failures with retry logic

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                      WORKFLOW ENGINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐                                             │
│  │ User Request   │                                             │
│  └────────┬───────┘                                             │
│           │                                                      │
│           ▼                                                      │
│  ┌────────────────────────────────────────────────┐             │
│  │      AgentOrchestrator (Enhanced)              │             │
│  │  - Detects workflow patterns                   │             │
│  │  - Routes to workflow engine                   │             │
│  │  - Post-processes tool results                 │             │
│  └────────┬──────────────────────┬────────────────┘             │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌────────────────┐    ┌────────────────┐                       │
│  │ Single Tool    │    │ Workflow       │                       │
│  │ Execution      │    │ Execution      │                       │
│  └────────────────┘    └────────┬───────┘                       │
│                                  │                               │
│                                  ▼                               │
│                         ┌────────────────┐                       │
│                         │ WorkflowEngine │                       │
│                         │  - Step exec   │                       │
│                         │  - Progress    │                       │
│                         │  - Recovery    │                       │
│                         └────────┬───────┘                       │
│                                  │                               │
│                                  ▼                               │
│                         ┌────────────────┐                       │
│                         │ Tool Executors │                       │
│                         │  - MCP tools   │                       │
│                         │  - Skills      │                       │
│                         │  - Memory      │                       │
│                         └────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: IMMEDIATE FIXES (Hours)

### 1.1 Screenshot Post-Processing Hook

**File:** `backend/app/services/agent_orchestrator.py`

**Implementation:**
- Add post-processing logic in `execute_tool()` method
- Detect screenshot results (base64 data)
- Auto-upload to Cloudinary
- Replace base64 with Cloudinary URL
- Log all actions for debugging

**Expected Outcome:**
```python
# Before:
result = await call_mcp_tool("puppeteer_screenshot", {})
# Returns: "iVBORw0KGgoAAAANSUhEUgAA..." (base64)

# After:
result = await execute_tool("puppeteer_screenshot", {})
# Returns: {
#   "url": "https://res.cloudinary.com/dtmizelyg/image/upload/v1734/nicole/screenshots/...",
#   "message": "Screenshot uploaded successfully",
#   "width": 1280,
#   "height": 800
# }
```

### 1.2 Update Nicole's System Prompt

**File:** `backend/app/prompts/nicole_system_prompt.py`

**Changes:**
- Add section on automatic screenshot workflows
- Clarify that screenshots auto-upload
- Provide clear examples
- Update tool search instructions

---

## PHASE 2: WORKFLOW ENGINE (Days)

### 2.1 Core Workflow Engine

**File:** `backend/app/services/workflow_engine.py`

**Components:**

1. **WorkflowStep** - Dataclass defining a single step
2. **WorkflowDefinition** - Complete workflow with metadata
3. **WorkflowExecutor** - Executes workflows with progress tracking
4. **WorkflowRegistry** - Pre-built workflow templates
5. **WorkflowState** - Runtime state management

**Features:**
- Template variable resolution (`{{input.url}}`, `{{prev.result}}`)
- Conditional execution (`if: prev.success`)
- Error recovery (retry with exponential backoff)
- Progress streaming (SSE to frontend)
- State persistence (database)

### 2.2 Pre-Built Workflow Templates

**Workflows to implement:**

1. **screenshot_and_post**
   - Navigate to URL
   - Take screenshot
   - Auto-upload (handled by post-processing)
   - Return URL

2. **web_research**
   - Brave search
   - Scrape top 3 results
   - Summarize findings
   - Store to memory

3. **deployment_check**
   - List deployments
   - Get latest deployment
   - Analyze logs
   - Format status report

4. **multi_scrape**
   - Scrape multiple URLs in parallel
   - Extract structured data
   - Compare results
   - Generate comparison table

### 2.3 Progress Streaming

**File:** `backend/app/routers/alphawave_chat.py`

**Implementation:**
- Extend SSE stream to include workflow progress events
- Stream step-by-step updates
- Show current step name and status
- Display partial results

**Frontend Updates:**
- Add workflow progress UI component
- Show step counter (Step 2/5)
- Display step names with status icons
- Collapse/expand workflow details

### 2.4 Database Schema

**File:** `backend/database/migrations/021_workflow_tracking.sql`

**Tables:**

```sql
CREATE TABLE workflow_runs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  conversation_id INTEGER REFERENCES conversations(id),
  workflow_name VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL, -- running, completed, failed
  input_data JSONB,
  output_data JSONB,
  steps_completed INTEGER DEFAULT 0,
  steps_total INTEGER,
  error_message TEXT,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  duration_ms INTEGER
);

CREATE TABLE workflow_steps (
  id SERIAL PRIMARY KEY,
  workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(id),
  step_number INTEGER NOT NULL,
  step_name VARCHAR(100) NOT NULL,
  tool_name VARCHAR(100) NOT NULL,
  tool_args JSONB,
  result JSONB,
  status VARCHAR(20) NOT NULL, -- pending, running, completed, failed
  error_message TEXT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  duration_ms INTEGER
);

CREATE INDEX idx_workflow_runs_user_id ON workflow_runs(user_id);
CREATE INDEX idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX idx_workflow_steps_run_id ON workflow_steps(workflow_run_id);
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Immediate (Complete in this session)

- [x] Plan created
- [ ] Create `workflow_engine.py` with core classes
- [ ] Add screenshot post-processing hook
- [ ] Update `agent_orchestrator.py` to use workflow engine
- [ ] Update Nicole's system prompt
- [ ] Test screenshot workflow end-to-end

### Phase 2: Short-term (Next session)

- [ ] Add workflow database schema
- [ ] Implement progress streaming
- [ ] Create frontend workflow progress component
- [ ] Add 4 pre-built workflow templates
- [ ] Add workflow error recovery
- [ ] Add workflow analytics/monitoring
- [ ] Deploy to droplet
- [ ] Test all workflows

---

## CODE STRUCTURE

```
backend/app/services/
├── workflow_engine.py          # Core workflow engine (NEW)
│   ├── WorkflowStep
│   ├── WorkflowDefinition
│   ├── WorkflowExecutor
│   ├── WorkflowRegistry
│   └── WorkflowState
│
├── agent_orchestrator.py       # Enhanced orchestrator (MODIFIED)
│   ├── execute_tool() - Add post-processing
│   ├── execute_workflow() - NEW method
│   └── _stream_workflow_progress() - NEW method
│
└── alphawave_cloudinary_service.py  # No changes needed

backend/app/routers/
└── alphawave_chat.py           # Enhanced SSE streaming (MODIFIED)
    └── send_message() - Add workflow progress events

backend/database/migrations/
└── 021_workflow_tracking.sql   # Workflow tracking schema (NEW)

frontend/src/components/chat/
├── WorkflowProgress.tsx        # Workflow progress UI (NEW)
└── AlphawaveChatContainer.tsx  # Display workflow progress (MODIFIED)
```

---

## SUCCESS METRICS

### Functional Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Screenshot E2E** | < 5 seconds | User request → image in chat |
| **Multi-step success rate** | > 95% | Workflow completion rate |
| **Progress visibility** | 100% | All workflows show progress |
| **Error recovery** | Auto-retry 2x | Failed steps retry before giving up |

### Technical Requirements

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Token efficiency** | -70% | Workflows use 70% fewer tokens |
| **Latency** | < 2s per step | Step execution time |
| **Code quality** | A+ | Type hints, docstrings, tests |
| **Error handling** | 100% coverage | All exceptions caught |

---

## TESTING PLAN

### Test Case 1: Screenshot Workflow

```python
# backend/tests/test_workflow_screenshot.py

async def test_screenshot_workflow():
    """Test screenshot workflow end-to-end."""
    
    # Setup
    orchestrator = AgentOrchestrator()
    await orchestrator.initialize_mcp()
    
    # Execute workflow
    result = await orchestrator.execute_tool(
        "puppeteer_screenshot",
        {"url": "https://google.com", "fullPage": False}
    )
    
    # Assertions
    assert "url" in result
    assert result["url"].startswith("https://res.cloudinary.com/")
    assert "width" in result
    assert "height" in result
    assert result["success"] is True
```

### Test Case 2: Multi-Step Research Workflow

```python
async def test_research_workflow():
    """Test multi-step research workflow."""
    
    orchestrator = AgentOrchestrator()
    
    # Execute workflow
    workflow = WorkflowRegistry.get("web_research")
    result = await orchestrator.execute_workflow(
        workflow,
        {"query": "AI developments 2025", "num_sources": 3}
    )
    
    # Assertions
    assert result["status"] == "completed"
    assert len(result["scraped_pages"]) == 3
    assert "summary" in result
    assert result["memory_saved"] is True
```

---

## DEPLOYMENT STEPS

### 1. Development

```bash
# Run locally
cd backend
source venv/bin/activate
python -m pytest tests/test_workflow_*.py -v

# Check linting
ruff check app/services/workflow_engine.py
mypy app/services/workflow_engine.py
```

### 2. Commit & Push

```bash
git add backend/app/services/workflow_engine.py
git add backend/app/services/agent_orchestrator.py
git add backend/app/prompts/nicole_system_prompt.py
git add backend/database/migrations/021_workflow_tracking.sql
git commit -m "feat: Add production-quality workflow engine

- Implement WorkflowEngine with step execution
- Add screenshot post-processing hook
- Create 4 pre-built workflow templates
- Add progress streaming to frontend
- Update Nicole's system prompt
- Add workflow tracking database schema

Fixes multi-step function execution issues.
Enables automatic screenshot → Cloudinary → chat workflow."

git push origin extended-thinking-feature
```

### 3. Droplet Deployment

```bash
ssh healy@167.99.115.218

# Pull latest
cd /opt/nicole
git pull origin extended-thinking-feature

# Run migrations
cd backend
source venv/bin/activate
python -c "from app.database.migrations_runner import run_migrations; run_migrations()"

# Restart services
sudo supervisorctl restart nicole-api
sudo supervisorctl restart nicole-worker

# Check logs
sudo tail -f /var/log/nicole/api.log | grep -i workflow
```

### 4. Vercel Deployment

- Vercel auto-deploys from `extended-thinking-feature` branch
- No manual action needed
- Check dashboard for deployment status

---

## MONITORING & OBSERVABILITY

### Logs to Add

```python
logger.info(f"[WORKFLOW] Started: {workflow.name} (run_id={run_id})")
logger.info(f"[WORKFLOW] Step {i+1}/{total}: {step.tool} (status={status})")
logger.info(f"[WORKFLOW] Completed: {workflow.name} (duration={duration}ms)")
logger.error(f"[WORKFLOW] Failed: {workflow.name} (error={error})")
```

### Metrics to Track

- Workflow execution count (by workflow name)
- Workflow success rate
- Average workflow duration
- Step failure rate
- Token usage per workflow

### Alerts to Configure

- Workflow failure rate > 20%
- Average duration > 30s
- Error rate spike
- Database connection failures

---

## FUTURE ENHANCEMENTS (Not in this implementation)

1. **Parallel Execution** - Run independent steps in parallel
2. **Conditional Branching** - If-else logic in workflows
3. **Human-in-the-Loop** - Pause for user approval
4. **Workflow Marketplace** - User-created workflows
5. **LangGraph Integration** - Advanced state machines
6. **Workflow Versioning** - Track workflow definition changes
7. **A/B Testing** - Test workflow variations
8. **Cost Tracking** - Track API costs per workflow

---

**End of Plan - Ready to Execute**


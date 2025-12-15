# Vibe System - Quick Reference Guide

**For full details, see:** `VIBE_SYSTEM_ARCHITECTURE.md`

---

## 30-Second Overview

**AlphaWave Vibe** transforms "Build a photography portfolio" → Live website on Vercel

**Pipeline:** Intake → Planning → Build → QA → Review → Deploy  
**Agents:** Design (🎨) → Architect (🏗️) → Coding (💻) → QA (🔍) → Review (⚖️)  
**Models:** Gemini 3 Pro (design) + Claude Opus (architecture) + Claude Sonnet (code)

---

## Agent Quick Ref

| Agent | Model | Role | Output |
|-------|-------|------|--------|
| 🎨 Design | Gemini 3 Pro | Visual research, color, typography | Design system tokens |
| 🏗️ Architect | Claude Opus | Component architecture, system design | Architecture JSON |
| 💻 Coding | Claude Sonnet | Generate all code files | Complete Next.js codebase |
| 🔍 QA | Claude Sonnet | Review code, accessibility, performance | QA report |
| ⚖️ Review | Claude Opus | Final approval, polish | Approval decision |

---

## Pipeline Flow

```
User: "Build a photography portfolio"
    ↓
Intake (Nicole): Asks questions, searches web, captures screenshots
    → Brief JSON
    ↓
Planning (Design Agent): Generates color palette, typography
Planning (Architect Agent): Designs components, pages, architecture
    → Architecture JSON
    ↓
Build (Coding Agent): Generates all .tsx, .ts, .css files
    → Files in database
    ↓
QA (QA Agent): Reviews for bugs, accessibility, performance
    → QA Report
    ↓
Review (Review Agent): Final approval
    → Approved ✅
    ↓
Deploy: Push to GitHub → Deploy to Vercel
    → Live at https://*.vercel.app
```

---

## Key Files

**Backend:**
- `backend/app/services/vibe_service.py` - Core pipeline logic (4000+ lines)
- `backend/app/services/vibe_agents.py` - Agent definitions and prompts
- `backend/app/services/model_orchestrator.py` - Multi-model routing
- `backend/app/routers/alphawave_vibe.py` - API endpoints

**Frontend:**
- `frontend/src/components/vibe/AlphawaveVibeWorkspace.tsx` - Main UI
- `frontend/src/lib/hooks/useVibeProject.ts` - State management

**MCP:**
- `mcp/mcp-http-bridge.js` - Tool gateway (Puppeteer, Brave, GitHub, Vercel)

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `vibe_projects` | Project metadata, brief, architecture, status |
| `vibe_files` | Generated code files (filepath + content) |
| `vibe_activities` | Real-time activity log for UI |
| `vibe_inspirations` | Screenshots captured during intake |
| `vibe_lessons` | Learnings from past projects (with embeddings) |

---

## API Endpoints

```
POST   /vibe/projects                    # Create project
POST   /vibe/projects/{id}/intake        # Run intake
POST   /vibe/projects/{id}/planning      # Run planning
POST   /vibe/projects/{id}/build         # Generate code
POST   /vibe/projects/{id}/qa            # QA review
POST   /vibe/projects/{id}/review        # Final review
POST   /vibe/projects/{id}/deploy        # Deploy to GitHub+Vercel
POST   /vibe/projects/{id}/pipeline      # Run all phases

GET    /vibe/projects/{id}               # Get project
GET    /vibe/projects/{id}/activities    # Activity log (polled every 2s)
GET    /vibe/projects/{id}/files         # Get all files
GET    /vibe/models/health               # Model health
```

---

## MCP Tools

| Tool | Purpose | Used By |
|------|---------|---------|
| `brave_web_search` | Search the web | Intake, Design Agent |
| `puppeteer_screenshot` | Capture website screenshots | Intake |
| `github_create_repo` | Create GitHub repo | Deploy phase |
| `github_push_files` | Push code to GitHub | Deploy phase |
| `vercel_create_project` | Create Vercel project | Deploy phase |
| `vercel_trigger_deploy` | Deploy to Vercel | Deploy phase |

---

## Skills

| Skill | Loaded For | Purpose |
|-------|-----------|---------|
| `frontend-design` | Coding Agent | Modern React/Next.js patterns |
| `canvas-design` | Architect Agent | Component architecture patterns |
| `skill-creator` | Nicole | How to create new skills |

**Location:** `backend/app/skills/{skill-name}/SKILL.md`

---

## Status Transitions

```
intake → brief_complete → planning → architecture_complete → 
building → build_complete → qa → qa_complete → review → 
approved → deploying → deployed
```

**Error States:** `failed` (can retry from failed phase)

---

## Real-Time Updates

**Polling:**
- Project details: Every 2s during operations
- Activities: Every 2s during operations
- Stops when operation completes

**Activity Types:**
- `phase_start`: New phase beginning
- `phase_complete`: Phase finished
- `tool_call`: Agent used a tool (e.g., "🔍 Searching: modern portfolio")
- `agent_message`: Agent thinking/response (chat bubble)
- `status_change`: Status updated
- `error`: Something failed

---

## Tech Stack

**Backend:** Python 3.9, FastAPI, TimescaleDB, Redis  
**Frontend:** TypeScript, Next.js 14, Tailwind CSS, shadcn/ui  
**AI Models:** Gemini 3 Pro, Claude Opus 4.5, Claude Sonnet 4.5  
**Tools:** Puppeteer, Brave Search, GitHub API, Vercel API  
**Deploy:** GitHub (source) + Vercel (hosting)

---

## Quality Standards

> "Code as if Elon Musk and Sam Altman will review it"

- NYC design agency quality
- Webby Award-worthy design
- Cutting-edge, futuristic, flawless
- WCAG 2.1 AA accessibility
- Performance optimized
- TypeScript strict mode
- Semantic HTML
- Mobile-first responsive

---

## Common Commands

**Start API (Droplet):**
```bash
cd /opt/nicole
supervisorctl restart nicole-api
tail -f /var/log/supervisor/nicole-api.log
```

**Start MCP Gateway:**
```bash
cd /opt/nicole/mcp
docker-compose up -d
docker logs mcp-gateway -f
```

**Check Model Health:**
```bash
curl http://localhost:8000/vibe/models/health -H "Authorization: Bearer $TOKEN" | jq
```

**Check Project Status:**
```bash
curl http://localhost:8000/vibe/projects/1 -H "Authorization: Bearer $TOKEN" | jq '.status'
```

---

## Architecture Highlights

1. **Nicole is Authority:** All agents report to her
2. **Role-Based Naming:** Not "Gemini", but "Design Agent"
3. **Multi-Model Orchestration:** Right model for each task
4. **Real-Time Visibility:** See what agents are doing
5. **Graceful Degradation:** Fallbacks for every failure
6. **Continuous Learning:** Lessons improve future builds
7. **One-Click Deploy:** GitHub + Vercel automated

---

## Debugging

**Pipeline Stuck?**
1. Check activities: `/vibe/projects/{id}/activities`
2. Check model health: `/vibe/models/health`
3. Check logs: `tail -50 /var/log/supervisor/nicole-api.log`
4. Look for phase name in error: `pipelineError.phase`

**Parsing Failed?**
1. Check raw response: `pipelineError.raw_response`
2. Files in database: `SELECT COUNT(*) FROM vibe_files WHERE project_id = X`
3. Architecture valid: `SELECT architecture FROM vibe_projects WHERE project_id = X`

**Deployment Failed?**
1. GitHub token valid? Check `GITHUB_TOKEN` env var
2. Vercel token valid? Check `VERCEL_TOKEN` env var
3. Check deploy logs in Vercel dashboard

---

## For More Details

See `VIBE_SYSTEM_ARCHITECTURE.md` for:
- Complete agent prompts
- Full database schema
- Detailed data flow diagrams
- Security considerations
- Performance optimization
- Future roadmap

---

**Quick Questions?**

**Q: What model does the Design Agent use?**  
A: Gemini 3 Pro (best for visual design and trend research)

**Q: How does code get from database to Vercel?**  
A: Deploy phase creates GitHub repo, pushes files, creates Vercel project, triggers deploy

**Q: How are activities updated in real-time?**  
A: Frontend polls `/activities` endpoint every 2 seconds during operations

**Q: What if a model fails?**  
A: Orchestrator has fallback chain, implements cooldowns, retries secondary models

**Q: Can I manually run a single phase?**  
A: Yes! Each phase has its own endpoint: `/planning`, `/build`, `/qa`, etc.

**Q: Where are agent prompts defined?**  
A: `backend/app/services/vibe_agents.py` - search for `TEAM_CONTEXT` and agent-specific prompts

**Q: How do skills work?**  
A: Skill content (`.md` files) is loaded and appended to agent system prompts

**Q: What's the difference between Brief and Architecture?**  
A: Brief = Requirements from user (what to build). Architecture = Technical design (how to build it)

---

**Last Updated:** December 15, 2025  
**Version:** 2.0.0  
**Status:** Production-Ready ✅


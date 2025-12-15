# AlphaWave Vibe System - Complete Architecture Documentation

**Version:** 2.0.0  
**Last Updated:** December 15, 2025  
**Status:** Production-Ready

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Philosophy](#architecture-philosophy)
3. [Technical Stack](#technical-stack)
4. [Agent System](#agent-system)
5. [Multi-Model Orchestration](#multi-model-orchestration)
6. [Pipeline Phases](#pipeline-phases)
7. [Database Schema](#database-schema)
8. [Frontend Architecture](#frontend-architecture)
9. [Real-Time Communication](#real-time-communication)
10. [Tools & Integrations](#tools--integrations)
11. [Skills System](#skills-system)
12. [Lessons Learning](#lessons-learning)
13. [Deployment Pipeline](#deployment-pipeline)
14. [Data Flow](#data-flow)
15. [File Structure](#file-structure)

---

## System Overview

### What is AlphaWave Vibe?

**AlphaWave Vibe** is an AI-powered web development platform that transforms natural language project descriptions into fully functional, professionally designed, and deployed websites. It operates at **NYC design agency standards** with code quality that would pass review by Elon Musk and Sam Altman.

### Core Capabilities

- **Conversational Intake**: Nicole understands project requirements through natural conversation
- **Multi-Agent Pipeline**: Specialized AI agents handle design, architecture, coding, QA, and review
- **Multi-Model Orchestration**: Intelligently routes tasks to the best AI model (Gemini 3 Pro, Claude Opus, Claude Sonnet)
- **Real-Time Streaming**: Live updates of agent activities, thinking processes, and code generation
- **Automated Deployment**: One-click deploy to GitHub + Vercel with full CI/CD
- **Continuous Learning**: Captures lessons from every project to improve future builds

---

## Architecture Philosophy

### Design Principles

1. **Nicole as Authority**: All agents report to Nicole, the Creative Director
2. **Role-Based Agents**: Not "Gemini" or "Claude", but "Design Agent", "Architect Agent", etc.
3. **NYC Agency Quality**: Every output meets Webby Award-worthy standards
4. **Cutting-Edge Technology**: Uses latest Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
5. **User Visibility**: Real-time insight into what agents are doing and why
6. **Graceful Degradation**: Fallbacks for every failure point

### Quality Standards

> "Code as if Elon Musk and Sam Altman will review it. Design as if it will be featured on Awwwards."

- Every design decision is intentional and defensible
- Every line of code is purposeful and maintainable
- Every component is accessible, performant, and tested
- Never settle for "good enough"—push for exceptional

---

## Technical Stack

### Backend

```yaml
Language: Python 3.9+
Framework: FastAPI 0.109+
Database: TimescaleDB (Postgres + time-series)
Cache: Redis (async)
AI Models:
  - Gemini 3 Pro (design research, visual trends)
  - Claude Opus 4.5 (architecture, system design)
  - Claude Sonnet 4.5 (code generation, QA)
  - Claude Haiku 4.5 (fallback)
Process Manager: Supervisord
Web Server: Nginx (reverse proxy)
```

### Frontend

```yaml
Language: TypeScript 5.0+
Framework: Next.js 14 (App Router)
Styling: Tailwind CSS 3.4+
UI Components: shadcn/ui
State: React Context + Custom Hooks
Real-Time: EventSource (SSE)
Build: Turbopack (development)
Deploy: Vercel (production)
```

### External Services

```yaml
Source Control: GitHub API
Deployment: Vercel API
Image Storage: Cloudinary
Screenshot Tool: Puppeteer (via MCP)
Web Search: Brave Search (via MCP)
Design Tools: Recraft AI (via MCP)
```

---

## Agent System

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NICOLE (Creative Director)                        │
│                    The authority - orchestrates all agents                  │
├─────────────────┬─────────────────┬──────────────────┬──────────────────────┤
│  DESIGN AGENT   │ ARCHITECT AGENT │  CODING AGENT    │    QA AGENT          │
│  🎨             │ 🏗️              │  💻              │    🔍                │
│  Gemini 3 Pro   │ Claude Opus 4.5 │  Claude Sonnet   │  Claude Sonnet      │
├─────────────────┼─────────────────┼──────────────────┼──────────────────────┤
│ Visual Research │ System Design   │ Implementation   │ Quality Assurance    │
│ Color Theory    │ Component Arch  │ Code Generation  │ Accessibility        │
│ Typography      │ Data Flow       │ Styling          │ Performance          │
│ Trend Analysis  │ SEO Strategy    │ Interactions     │ Security             │
└─────────────────┴─────────────────┴──────────────────┴──────────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │   REVIEW AGENT   │
                            │   ⚖️              │
                            │   Claude Opus    │
                            ├──────────────────┤
                            │ Final Approval   │
                            │ Polish & Refine  │
                            └──────────────────┘
```

### Agent Definitions

Each agent has:

1. **Role**: Unique identity and responsibility
2. **Display Name**: Human-readable name shown in UI
3. **Model**: Underlying AI model (Gemini 3 Pro, Claude Opus, etc.)
4. **Emoji**: Visual identifier (🎨, 🏗️, 💻, 🔍, ⚖️)
5. **Capabilities**: What this agent is expert at
6. **Tools**: What MCP tools this agent can use
7. **System Prompt**: Detailed instructions defining behavior
8. **Handoff Protocol**: How to start and finish, what to pass to next agent

#### Design Agent (🎨 Gemini 3 Pro)

**Responsibilities:**
- Research visual trends and design inspiration
- Generate color palettes using color theory
- Select typography that matches brand
- Analyze competitor designs
- Create design system tokens

**Tools:**
- `web_search`: Research design trends
- `screenshot_website`: Capture inspiration
- `recraft`: Generate design assets

**Output:** Design system with colors, fonts, spacing, and visual direction

---

#### Architect Agent (🏗️ Claude Opus 4.5)

**Responsibilities:**
- Design component architecture
- Plan data flow and state management
- Define folder structure
- Choose optimal tech stack
- Create SEO strategy
- Plan accessibility features

**Skills Loaded:**
- `canvas-design`: Component composition patterns
- (Additional architecture skills as needed)

**Output:** Structured JSON architecture document with:
```json
{
  "overview": "High-level system description",
  "pages": [{"path": "/", "purpose": "Home", "components": [...]}],
  "components": [{"name": "Header", "purpose": "...", "props": [...]}],
  "design_tokens": {"colors": {...}, "typography": {...}},
  "tech_stack": {"framework": "Next.js 14", ...},
  "seo_strategy": {...},
  "accessibility": {...}
}
```

---

#### Coding Agent (💻 Claude Sonnet 4.5)

**Responsibilities:**
- Generate production-ready code
- Implement all components
- Apply design system consistently
- Create responsive layouts
- Add interactions and animations
- Ensure type safety

**Skills Loaded:**
- `frontend-design`: Modern frontend patterns
- (Additional coding skills as needed)

**Output:** Complete codebase with all files:
```
src/
├── app/
│   ├── page.tsx (Home page)
│   ├── layout.tsx (Root layout)
│   └── globals.css (Global styles)
├── components/
│   ├── Header.tsx
│   ├── Footer.tsx
│   └── ...
├── lib/
│   └── utils.ts
package.json
tailwind.config.ts
tsconfig.json
next.config.js
```

**Code Standards:**
- TypeScript with strict mode
- ESLint + Prettier configured
- Semantic HTML
- Accessible by default (ARIA labels, keyboard nav)
- Mobile-first responsive design
- Performance optimized (lazy loading, code splitting)

---

#### QA Agent (🔍 Claude Sonnet 4.5)

**Responsibilities:**
- Review all code for bugs
- Test accessibility (WCAG 2.1 AA)
- Check performance bottlenecks
- Verify responsive design
- Validate SEO implementation
- Security audit

**Output:** QA report with:
```json
{
  "overall_quality": "excellent",
  "critical_issues": [],
  "warnings": [],
  "suggestions": [],
  "accessibility_score": 95,
  "performance_notes": "...",
  "approved": true
}
```

---

#### Review Agent (⚖️ Claude Opus 4.5)

**Responsibilities:**
- Final approval decision
- Holistic quality assessment
- Polish and refinement suggestions
- Ensure all phases integrated correctly

**Output:** Final approval or request for revisions

---

## Multi-Model Orchestration

### ModelOrchestrator Class

The `ModelOrchestrator` intelligently routes tasks to the best AI model based on:

1. **Capability Matching**: What the task requires
2. **Model Health**: Is the model available?
3. **Fallback Strategy**: If primary fails, use backup

### Model Capabilities

| Model | Strengths | Used For |
|-------|-----------|----------|
| **Gemini 3 Pro** | Visual design, trend research, color theory | Design Agent |
| **Claude Opus 4.5** | Architecture, system design, judgment | Architect + Review |
| **Claude Sonnet 4.5** | Code generation, QA, fast iteration | Coding + QA |
| **Claude Haiku 4.5** | Fast responses, fallback | Emergency fallback |

### Health Tracking

Each model tracks:
- `available`: Is it currently usable?
- `last_failure`: When did it last fail?
- `consecutive_failures`: How many times in a row?
- `cooldown_until`: When will it be available again?

**Cooldown Strategy:**
- 3 failures → 30 second cooldown
- 4 failures → 60 second cooldown
- 5 failures → 120 second cooldown
- Max cooldown: 5 minutes

### Fallback Chain

```
Primary Model Fails
    ↓
Check Secondary Model Health
    ↓
If Available: Use Secondary
    ↓
If Unavailable: Wait for Cooldown
    ↓
If Still Failing: Surface Error to User
```

---

## Pipeline Phases

### Phase 1: Intake

**Who:** Nicole (using Claude with tools)  
**Goal:** Understand project requirements through conversation  

**Process:**
1. User describes project in natural language
2. Nicole asks clarifying questions
3. Nicole searches web for inspiration (Brave Search MCP)
4. Nicole captures screenshots (Puppeteer MCP)
5. Nicole saves relevant inspirations to database
6. Nicole generates structured brief

**Tools Used:**
- `brave_web_search`: Find design inspiration
- `puppeteer_screenshot`: Capture website screenshots
- `save_inspiration`: Store inspiration in database

**Output:** Project brief (JSON)
```json
{
  "business_name": "Acme Corp",
  "project_type": "portfolio",
  "description": "Modern portfolio website for a photographer",
  "target_audience": "Potential clients, art directors",
  "key_features": ["Gallery", "About", "Contact"],
  "style_preferences": "Minimalist, elegant, high-contrast",
  "inspirations": [
    {
      "url": "https://example.com",
      "screenshot_url": "https://cloudinary.../screenshot.png",
      "relevance_notes": "Love the gallery layout"
    }
  ]
}
```

**Database:** Saved to `vibe_projects.brief` and `vibe_inspirations` table

---

### Phase 2: Planning

**Who:** Design Agent (Gemini 3 Pro) + Architect Agent (Claude Opus)  
**Goal:** Create visual design system and technical architecture  

**Step 2A: Design Research**
- Gemini 3 Pro researches latest design trends
- Generates color palette based on color theory
- Selects typography that matches brand
- Creates design system tokens

**Step 2B: Architecture Design**
- Claude Opus designs component structure
- Plans page hierarchy and routing
- Defines state management approach
- Creates SEO and accessibility strategy

**Output:** Complete architecture (JSON)
```json
{
  "overview": "A minimalist photography portfolio...",
  "pages": [
    {
      "path": "/",
      "name": "Home",
      "purpose": "Showcase featured work",
      "components": ["Hero", "FeaturedGallery", "CTA"]
    },
    {
      "path": "/gallery",
      "name": "Gallery",
      "purpose": "Full image gallery with filters",
      "components": ["GalleryGrid", "ImageModal", "FilterBar"]
    }
  ],
  "components": [
    {
      "name": "Hero",
      "purpose": "Full-screen header with photographer intro",
      "props": ["heading", "subtitle", "ctaText", "backgroundImage"],
      "state": []
    }
  ],
  "design_tokens": {
    "colors": {
      "primary": "#1a1a1a",
      "secondary": "#f5f5f5",
      "accent": "#ff6b6b"
    },
    "typography": {
      "heading": "Playfair Display",
      "body": "Inter"
    }
  },
  "tech_stack": {
    "framework": "Next.js 14",
    "styling": "Tailwind CSS",
    "ui_library": "shadcn/ui"
  }
}
```

**Database:** Saved to `vibe_projects.architecture`

---

### Phase 3: Build

**Who:** Coding Agent (Claude Sonnet 4.5)  
**Goal:** Generate all code files for the project  

**Process:**
1. Reads brief + architecture
2. Loads relevant skills (e.g., `frontend-design`)
3. Retrieves lessons from similar past projects
4. Generates code file by file
5. Ensures consistency across all files
6. Applies design tokens systematically

**Skills Injected:**
- `frontend-design`: Modern component patterns, hooks, best practices

**Code Generation Order:**
1. `package.json` (dependencies)
2. `tsconfig.json` (TypeScript config)
3. `tailwind.config.ts` (design tokens)
4. `next.config.js` (Next.js config)
5. `src/app/layout.tsx` (root layout)
6. `src/app/globals.css` (global styles)
7. `src/app/page.tsx` (home page)
8. `src/components/*.tsx` (all components)
9. `src/lib/utils.ts` (utilities)

**Output Format:**

Claude generates files in these patterns (regex-matched):

```
**src/app/page.tsx**
```typescript
export default function Home() {
  return <div>...</div>
}
```

Or:

```
```filepath:src/components/Header.tsx
export function Header() {
  return <header>...</header>
}
```

**Parsing:** `parse_files_from_response()` uses 7 different regex patterns to extract files

**Validation:**
- Each file must have > 10 characters
- Must have valid path
- Must have content

**Database:** Saved to `vibe_files` table as JSON array

---

### Phase 4: QA

**Who:** QA Agent (Claude Sonnet 4.5)  
**Goal:** Review code for bugs, accessibility, performance, security  

**Process:**
1. Reads all generated files
2. Reviews against architecture
3. Checks accessibility (WCAG 2.1 AA)
4. Validates responsive design
5. Tests performance patterns
6. Audits security

**QA Checklist:**
- ✅ All pages from architecture implemented?
- ✅ All components from architecture created?
- ✅ Design tokens applied consistently?
- ✅ TypeScript types correct?
- ✅ Accessibility: ARIA labels, keyboard nav, alt text?
- ✅ Responsive: Mobile, tablet, desktop tested?
- ✅ Performance: Lazy loading, code splitting, image optimization?
- ✅ SEO: Meta tags, semantic HTML, structured data?
- ✅ Security: No XSS, CSRF, injection vulnerabilities?

**Output:** QA report (JSON)
```json
{
  "overall_quality": "excellent",
  "critical_issues": [],
  "warnings": [
    "Consider adding loading states to GalleryGrid"
  ],
  "suggestions": [
    "Add error boundary around ImageModal"
  ],
  "accessibility_score": 95,
  "performance_notes": "All images use Next.js Image component ✅",
  "security_notes": "No user input, no security concerns ✅",
  "approved": true,
  "revisions_needed": []
}
```

**Database:** Saved to `vibe_projects.qa_report`

---

### Phase 5: Review

**Who:** Review Agent (Claude Opus 4.5)  
**Goal:** Final approval and polish  

**Process:**
1. Holistic review of entire project
2. Verify all agents did their jobs correctly
3. Check integration between all parts
4. Ensure NYC agency quality standards met
5. Make final approval decision

**Output:** Review decision (JSON)
```json
{
  "approved": true,
  "overall_assessment": "Exceptional work. Meets all quality standards.",
  "strengths": [
    "Consistent design system",
    "Excellent accessibility",
    "Clean, maintainable code"
  ],
  "polish_suggestions": [
    "Add micro-interactions on hover states"
  ]
}
```

**Database:** Saved to `vibe_projects.review_status`

---

### Phase 6: Deploy

**Who:** Vibe Service (automated)  
**Goal:** Deploy to GitHub + Vercel with live URL  

**Process:**

1. **Create GitHub Repository**
   - Uses `GitHubService` class
   - Creates public repo under configured org/user
   - Name format: `{business_name}-{project_type}-{timestamp}`

2. **Push Files**
   - Commits all files from `vibe_files`
   - Creates proper file structure
   - Adds `.gitignore`, `README.md`

3. **Create Vercel Project**
   - Uses `VercelService` class
   - Links to GitHub repo
   - Configures build settings (Next.js)

4. **Trigger Deployment**
   - Vercel auto-deploys on push
   - Returns preview URL

5. **Update Database**
   - Saves `github_repo_url`
   - Saves `vercel_project_id`
   - Saves `deployment_url`
   - Sets status to `deployed`

**Output:** Live website at `https://{project-name}.vercel.app`

**Database:** Updated `vibe_projects` with deployment info

---

## Database Schema

### Core Tables

#### `vibe_projects`

```sql
CREATE TABLE vibe_projects (
    project_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    project_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'intake',
    brief JSONB,                      -- From intake phase
    architecture JSONB,               -- From planning phase
    qa_report JSONB,                  -- From QA phase
    review_status TEXT,               -- From review phase
    github_repo_url TEXT,             -- Deployment
    vercel_project_id TEXT,           -- Deployment
    deployment_url TEXT,              -- Live website URL
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Status Values:**
- `intake`: Gathering requirements
- `brief_complete`: Brief generated
- `planning`: Designing architecture
- `architecture_complete`: Architecture ready
- `building`: Generating code
- `build_complete`: Code generated
- `qa`: Under QA review
- `qa_complete`: QA passed
- `review`: Final review
- `approved`: Ready to deploy
- `deploying`: Deployment in progress
- `deployed`: Live website running
- `failed`: Something went wrong

---

#### `vibe_files`

```sql
CREATE TABLE vibe_files (
    file_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id),
    filepath TEXT NOT NULL,           -- e.g., "src/app/page.tsx"
    content TEXT NOT NULL,            -- File contents
    file_type TEXT,                   -- "typescript", "css", "config"
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,                  -- Which agent created it
    UNIQUE(project_id, filepath)
);
```

---

#### `vibe_inspirations`

```sql
CREATE TABLE vibe_inspirations (
    inspiration_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id),
    url TEXT NOT NULL,                -- Original website URL
    screenshot_url TEXT,              -- Cloudinary URL
    relevance_notes TEXT,             -- Why this is relevant
    captured_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

#### `vibe_lessons`

```sql
CREATE TABLE vibe_lessons (
    lesson_id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES vibe_projects(project_id),
    lesson_type TEXT NOT NULL,        -- "success", "failure", "insight"
    lesson_content TEXT NOT NULL,     -- What was learned
    context JSONB,                    -- Additional context
    embedding VECTOR(1536),           -- For semantic search
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Lesson Types:**
- `success`: What worked well
- `failure`: What didn't work
- `insight`: General learning
- `pattern`: Reusable pattern discovered

**Usage:** Before generating code, Coding Agent searches for relevant lessons from past projects with similar requirements.

---

#### `vibe_activities`

```sql
CREATE TABLE vibe_activities (
    activity_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id),
    activity_type TEXT NOT NULL,      -- "phase_start", "tool_call", "agent_message"
    agent_name TEXT,                  -- "design_agent", "architect_agent", etc.
    action TEXT NOT NULL,             -- Description of what happened
    metadata JSONB,                   -- Additional data
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Activity Types:**
- `phase_start`: New phase beginning
- `phase_complete`: Phase finished
- `tool_call`: Agent used a tool
- `agent_message`: Agent thinking/response
- `status_change`: Project status updated
- `error`: Something failed

**Usage:** Frontend polls this table to show real-time updates

---

## Frontend Architecture

### Component Structure

```
frontend/src/
├── app/
│   ├── (app)/                       # Authenticated routes
│   │   ├── layout.tsx               # Main app layout
│   │   ├── page.tsx                 # Chat page (default)
│   │   └── vibe/
│   │       └── page.tsx             # Vibe dashboard page
│   ├── login/
│   │   └── page.tsx                 # Login page
│   └── layout.tsx                   # Root layout
├── components/
│   ├── vibe/
│   │   └── AlphawaveVibeWorkspace.tsx   # Main Vibe UI
│   ├── chat/
│   │   ├── AlphawaveChatContainer.tsx   # Main chat
│   │   └── AlphawaveChatInput.tsx       # Chat input
│   ├── memory/
│   │   └── AlphawaveMemoryDashboard.tsx # Memory system
│   └── research/
│       └── ResearchPanel.tsx            # Gemini research
├── lib/
│   ├── hooks/
│   │   ├── useVibeProject.ts        # Vibe state management
│   │   ├── alphawave_use_chat.ts    # Chat state
│   │   └── useResearch.ts           # Research state
│   ├── context/
│   │   └── ConversationContext.tsx  # Conversation state
│   └── alphawave_config.ts          # API configuration
└── styles/
    └── globals.css                   # Global styles
```

---

### Vibe Dashboard UI

**File:** `frontend/src/components/vibe/AlphawaveVibeWorkspace.tsx`

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Project Name                        [Deploy] [×]   │
├──────────────────┬──────────────────────────────────────────┤
│                  │                                          │
│  Left Sidebar    │  Main Workspace                          │
│                  │                                          │
│  • Intake        │  [Brief Display]                         │
│  • Planning      │  or                                      │
│  • Build         │  [Architecture Card]                     │
│  • QA            │  or                                      │
│  • Review        │  [File Tree + Code Preview]              │
│  • Deploy        │  or                                      │
│                  │  [Deployment Success]                    │
│  [Run Pipeline]  │                                          │
│  [Retry]         │                                          │
│                  │                                          │
├──────────────────┴──────────────────────────────────────────┤
│  Agent Console (Bottom Panel)                               │
│  🎨 Design Agent: Researching color trends...               │
│  🏗️ Architect Agent: Defining component hierarchy...        │
│  💻 Coding Agent: Generating src/app/page.tsx...            │
├─────────────────────────────────────────────────────────────┤
│  Activity Feed (Right Panel)                                │
│  • Planning started                                         │
│  • Searching: "modern portfolio design"                     │
│  • Screenshot captured: example.com                         │
│  • Architecture generated ✅                                 │
└─────────────────────────────────────────────────────────────┘
```

**Key UI Elements:**

1. **Live Status Indicator**
   - Shows current active agent with emoji
   - Displays current task in real-time
   - Prominent "LIVE" badge during operations

2. **Agent Console**
   - Chat-like interface showing agent messages
   - Color-coded by message type:
     - Thinking (purple)
     - Tool calls (blue)
     - Responses (green)
     - Errors (red)

3. **Activity Feed**
   - Chronological list of all activities
   - Auto-scrolls to latest
   - Shows timestamps

4. **Preview System**
   - In-dashboard HTML preview (iframe with srcdoc)
   - StackBlitz button for interactive editing
   - Raw build preview when files fail to parse

5. **Pipeline Controls**
   - "Run Pipeline" button to start automation
   - "Retry" button if pipeline fails
   - Manual phase buttons (Planning, Build, QA, Review)

---

### State Management

**Hook:** `useVibeProject.ts`

```typescript
interface VibeProjectState {
  project: VibeProject | null;
  activities: Activity[];
  isLoading: boolean;
  isAnyOperationLoading: boolean;
  pipelineError: { phase: string; message: string } | null;
  
  // Actions
  createProject: (name: string) => Promise<void>;
  runIntake: (description: string) => Promise<void>;
  runPlanning: () => Promise<void>;
  runBuild: () => Promise<void>;
  runQA: () => Promise<void>;
  runReview: () => Promise<void>;
  runPipeline: () => Promise<void>;
  retryProject: () => Promise<void>;
  deployProject: () => Promise<void>;
}
```

**Polling Strategy:**

- Polls `/vibe/projects/{id}` every 2 seconds when loading
- Polls `/vibe/projects/{id}/activities` every 2 seconds during operations
- Exponential backoff on rate limit (429) errors
- Stops polling when operation completes

---

## Real-Time Communication

### Server-Sent Events (SSE)

**Why SSE over WebSockets?**
- Simpler implementation
- Works over HTTP (no special server config)
- Auto-reconnects on disconnect
- Browser native (`EventSource`)

### Activity Logging

**Backend:** Every significant action logs an activity

```python
await db.execute(
    """
    INSERT INTO vibe_activities (
        project_id, activity_type, agent_name, action, metadata
    ) VALUES ($1, $2, $3, $4, $5)
    """,
    project_id,
    "agent_message",
    "design_agent",
    "Researching design trends",
    {"message_type": "thinking", "full_content": "..."}
)
```

**Frontend:** Polls and displays activities

```typescript
const fetchActivities = async () => {
  const response = await fetch(`/vibe/projects/${id}/activities`);
  const data = await response.json();
  setActivities(data.activities);
};

useEffect(() => {
  if (isLoading) {
    const interval = setInterval(fetchActivities, 2000);
    return () => clearInterval(interval);
  }
}, [isLoading]);
```

### Activity Types

| Type | When | Display |
|------|------|---------|
| `phase_start` | Phase begins | "Planning started" |
| `phase_complete` | Phase done | "Planning complete ✅" |
| `tool_call` | Agent uses tool | "🔍 Searching: query..." |
| `agent_message` | Agent thinking/responding | Chat bubble in Agent Console |
| `status_change` | Project status updates | "Status → building" |
| `error` | Something fails | Red error banner |

---

## Tools & Integrations

### MCP (Model Context Protocol)

**What is MCP?**
Model Context Protocol is a standard for connecting AI models to external tools and data sources.

**AlphaWave MCP Gateway:**
- Docker container running Node.js server
- Exposes tools via HTTP/JSON-RPC bridge
- Managed by `mcp/mcp-http-bridge.js`

### Available Tools

#### 1. Brave Search (`brave_web_search`)

```typescript
{
  name: "brave_web_search",
  description: "Search the web using Brave Search API",
  inputSchema: {
    query: "string - search query",
    count: "number - results to return (default: 10)"
  }
}
```

**Used by:** Intake phase for research, Design Agent for trends

---

#### 2. Puppeteer Screenshot (`puppeteer_screenshot`)

```typescript
{
  name: "puppeteer_screenshot",
  description: "Capture full-page screenshot of a website",
  inputSchema: {
    url: "string - website URL",
    fullPage: "boolean - capture full page (default: true)"
  }
}
```

**Process:**
1. Puppeteer navigates to URL
2. Captures screenshot as PNG
3. Uploads to Cloudinary
4. Returns Cloudinary URL

**Used by:** Intake phase to capture inspiration

---

#### 3. GitHub Integration

**Tools:**
- `github_create_repo`: Create new repository
- `github_push_files`: Commit files to repo

**Configuration:**
```env
GITHUB_TOKEN=ghp_xxx
GITHUB_ORG=your-org-name
```

**Used by:** Deploy phase to push code

---

#### 4. Vercel Integration

**Tools:**
- `vercel_create_project`: Create new Vercel project
- `vercel_trigger_deploy`: Deploy to production

**Configuration:**
```env
VERCEL_TOKEN=xxx
VERCEL_TEAM_ID=team_xxx
```

**Used by:** Deploy phase for hosting

---

#### 5. Recraft AI

```typescript
{
  name: "recraft_generate",
  description: "Generate images and design assets",
  inputSchema: {
    prompt: "string - what to generate",
    style: "string - art style"
  }
}
```

**Used by:** Design Agent (future enhancement)

---

### Tool Execution Flow

```
Agent decides to use tool
    ↓
Claude outputs tool_use block
    ↓
Vibe Service intercepts
    ↓
Routes to Docker MCP Gateway
    ↓
MCP executes tool (Puppeteer, Brave, etc.)
    ↓
Returns result to Vibe Service
    ↓
Vibe Service logs activity
    ↓
Claude receives result
    ↓
Claude continues with tool output
```

---

## Skills System

### What are Skills?

Skills are **filesystem-based capabilities** that provide Claude with domain-specific expertise, workflows, and context. Think of them as specialized training modules.

**Location:** `backend/app/skills/`

### Skill Structure

```
skills/
├── frontend-design/
│   ├── SKILL.md               # Main instructions
│   ├── metadata.json          # Skill info
│   └── resources/             # Templates, examples
├── canvas-design/
│   ├── SKILL.md
│   └── metadata.json
└── skill-creator/
    ├── SKILL.md
    └── metadata.json
```

### Key Skills

#### 1. `frontend-design`

**Loaded for:** Coding Agent

**Provides:**
- Modern React/Next.js patterns
- TypeScript best practices
- Component composition strategies
- Hook usage guidelines
- Performance optimization
- Accessibility patterns

**Example Content:**
```markdown
## Modern Frontend Patterns

### Component Structure
Always use function components with TypeScript...

### State Management
Use React Context for global state...

### Performance
Always use React.memo for expensive components...
```

---

#### 2. `canvas-design`

**Loaded for:** Architect Agent

**Provides:**
- Component architecture patterns
- Design system organization
- Layout strategies
- Responsive design principles

---

#### 3. `skill-creator`

**Loaded for:** Nicole (main chat)

**Provides:**
- How to create new skills
- Skill documentation format
- Best practices for skill design

---

### Skill Injection

**How it works:**

1. Agent prompt is defined in `vibe_agents.py`
2. When agent is created, relevant skills are loaded:
   ```python
   enhanced_prompt = get_enhanced_prompt(
       base_prompt=CODING_AGENT_PROMPT,
       skill_names=["frontend-design"]
   )
   ```
3. Skill content is appended to system prompt
4. Agent now has access to all skill knowledge

**Example Enhanced Prompt:**

```
You are the Coding Agent...
[base prompt continues]

## LOADED SKILLS

The following skills are now active:

### SKILL: FRONTEND-DESIGN

[Full content of frontend-design/SKILL.md]

---
```

---

## Lessons Learning

### Purpose

Capture knowledge from every project to improve future builds.

### Lesson Types

1. **Success**: What worked well
2. **Failure**: What didn't work
3. **Insight**: General learning
4. **Pattern**: Reusable pattern discovered

### Capture Points

Lessons are captured:
- After QA phase: What issues were found?
- After Review phase: What was exceptional?
- After Deploy phase: Did deployment succeed?

### Storage

```python
async def capture_lesson(
    project_id: int,
    lesson_type: str,
    lesson_content: str,
    context: dict
):
    # Generate embedding for semantic search
    embedding = await openai_client.get_embedding(lesson_content)
    
    await db.execute(
        """
        INSERT INTO vibe_lessons 
        (project_id, lesson_type, lesson_content, context, embedding)
        VALUES ($1, $2, $3, $4, $5)
        """,
        project_id, lesson_type, lesson_content, json.dumps(context), embedding
    )
```

### Retrieval

Before generating code, Coding Agent retrieves relevant lessons:

```python
async def get_relevant_lessons(
    project_description: str,
    limit: int = 5
) -> List[dict]:
    # Generate embedding for query
    query_embedding = await openai_client.get_embedding(project_description)
    
    # Search for similar lessons using pgvector
    lessons = await db.fetch(
        """
        SELECT lesson_content, context, 
               1 - (embedding <=> $1) AS similarity
        FROM vibe_lessons
        WHERE 1 - (embedding <=> $1) > 0.7
        ORDER BY similarity DESC
        LIMIT $2
        """,
        query_embedding, limit
    )
    
    return lessons
```

**Example Lesson:**

```json
{
  "lesson_type": "success",
  "lesson_content": "For photography portfolios, users love masonry grid layouts with lightbox modals. Implement with react-photo-album + yet-another-react-lightbox.",
  "context": {
    "project_type": "portfolio",
    "industry": "photography",
    "component": "Gallery"
  }
}
```

---

## Deployment Pipeline

### GitHub + Vercel Flow

```
1. Code Generated (in database)
    ↓
2. Create GitHub Repo
    - POST /orgs/{org}/repos
    - Name: {business}-{type}-{timestamp}
    ↓
3. Push Files to GitHub
    - Create blob for each file
    - Create tree
    - Create commit
    - Update main branch ref
    ↓
4. Create Vercel Project
    - POST /v9/projects
    - Link to GitHub repo
    - Set framework: nextjs
    ↓
5. Vercel Auto-Deploys
    - Detects Next.js
    - Runs `npm install && npm run build`
    - Deploys to *.vercel.app
    ↓
6. Update Database
    - Save github_repo_url
    - Save vercel_project_id
    - Save deployment_url
    - Set status = 'deployed'
```

### Repository Structure

```
{business-name}-{project-type}/
├── .gitignore
├── README.md
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
├── postcss.config.js
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   └── *.tsx
│   └── lib/
│       └── utils.ts
└── public/
    └── images/
```

### Vercel Configuration

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "installCommand": "npm install",
  "devCommand": "npm run dev"
}
```

---

## Data Flow

### Complete Project Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. USER INPUT                                                           │
│    "Build a photography portfolio website"                             │
└────────────────────────────┬────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. INTAKE (Nicole + Claude with Tools)                                 │
│    • Asks clarifying questions                                          │
│    • Searches web for inspiration (Brave Search MCP)                    │
│    • Captures screenshots (Puppeteer MCP)                               │
│    • Generates structured brief                                         │
│    → Saves to: vibe_projects.brief, vibe_inspirations                   │
└────────────────────────────┬────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. PLANNING                                                             │
│    Step A: Design Agent (Gemini 3 Pro)                                 │
│    • Researches design trends                                           │
│    • Generates color palette                                            │
│    • Selects typography                                                 │
│    → Returns: Design system tokens                                      │
│                                                                         │
│    Step B: Architect Agent (Claude Opus)                               │
│    • Receives design system + brief                                     │
│    • Designs component architecture                                     │
│    • Plans pages and routing                                            │
│    • Creates SEO strategy                                               │
│    → Saves to: vibe_projects.architecture                               │
└────────────────────────────┬────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. BUILD (Coding Agent - Claude Sonnet)                                │
│    • Loads skills: frontend-design                                      │
│    • Retrieves relevant lessons from past projects                      │
│    • Reads brief + architecture                                         │
│    • Generates all code files                                           │
│    → Saves to: vibe_files (each file as row)                            │
└────────────────────────────┬────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. QA (QA Agent - Claude Sonnet)                                       │
│    • Reviews all files                                                  │
│    • Checks accessibility (WCAG 2.1 AA)                                 │
│    • Validates responsive design                                        │
│    • Tests performance patterns                                         │
│    • Audits security                                                    │
│    → Saves to: vibe_projects.qa_report                                  │
└────────────────────────────┬────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. REVIEW (Review Agent - Claude Opus)                                 │
│    • Holistic review of entire project                                  │
│    • Verifies all agents did their jobs                                 │
│    • Ensures quality standards met                                      │
│    • Makes final approval decision                                      │
│    → Saves to: vibe_projects.review_status                              │
└────────────────────────────┬────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. DEPLOY (Automated)                                                  │
│    • GitHub: Create repo, push files                                    │
│    • Vercel: Create project, trigger deploy                             │
│    → Saves to: vibe_projects.{github_repo_url, deployment_url}          │
│    → Status: deployed                                                   │
└────────────────────────────┬────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 8. LESSONS (Post-Deploy)                                               │
│    • Captures what worked well                                          │
│    • Records any issues                                                 │
│    • Generates embeddings                                               │
│    → Saves to: vibe_lessons                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Backend

```
backend/
├── app/
│   ├── main.py                          # FastAPI app entry point
│   ├── config.py                        # Settings (env vars)
│   ├── database.py                      # Postgres + Redis
│   ├── routers/
│   │   └── alphawave_vibe.py            # Vibe API endpoints
│   ├── services/
│   │   ├── vibe_service.py              # Core pipeline logic
│   │   ├── vibe_agents.py               # Agent definitions
│   │   └── model_orchestrator.py        # Multi-model routing
│   ├── integrations/
│   │   ├── alphawave_claude.py          # Claude client
│   │   ├── alphawave_gemini.py          # Gemini client
│   │   ├── github_service.py            # GitHub API
│   │   └── vercel_service.py            # Vercel API
│   ├── skills/
│   │   ├── frontend-design/
│   │   │   └── SKILL.md
│   │   ├── canvas-design/
│   │   │   └── SKILL.md
│   │   └── skill-creator/
│   │       └── SKILL.md
│   └── middleware/
│       ├── alphawave_cors.py            # CORS configuration
│       └── alphawave_rate_limit.py      # Rate limiting
└── database/
    └── migrations/
        └── 007_vibe_dashboard.sql       # Vibe schema
```

### Frontend

```
frontend/
├── src/
│   ├── app/
│   │   └── (app)/
│   │       └── vibe/
│   │           └── page.tsx             # Vibe dashboard page
│   ├── components/
│   │   └── vibe/
│   │       └── AlphawaveVibeWorkspace.tsx  # Main UI
│   └── lib/
│       └── hooks/
│           └── useVibeProject.ts        # State management
└── public/
    └── images/
```

### MCP Gateway

```
mcp/
├── docker-compose.yml                   # Container config
├── Dockerfile                           # Build instructions
├── mcp-http-bridge.js                   # HTTP/JSON-RPC server
└── package.json                         # Node.js dependencies
```

---

## API Endpoints

### Vibe Routes

```
POST   /vibe/projects                    # Create new project
GET    /vibe/projects                    # List all projects
GET    /vibe/projects/{id}               # Get project details
DELETE /vibe/projects/{id}               # Delete project

POST   /vibe/projects/{id}/intake        # Run intake phase
POST   /vibe/projects/{id}/planning      # Run planning phase
POST   /vibe/projects/{id}/build         # Run build phase
POST   /vibe/projects/{id}/qa            # Run QA phase
POST   /vibe/projects/{id}/review        # Run review phase
POST   /vibe/projects/{id}/deploy        # Deploy to GitHub+Vercel

POST   /vibe/projects/{id}/pipeline      # Run full pipeline
POST   /vibe/projects/{id}/retry         # Retry failed phase

GET    /vibe/projects/{id}/activities    # Get activity log
GET    /vibe/projects/{id}/files         # Get all files
GET    /vibe/projects/{id}/inspirations  # Get inspirations
GET    /vibe/projects/{id}/preview       # Get HTML preview
GET    /vibe/projects/{id}/stackblitz    # Get StackBlitz config

GET    /vibe/models/health               # Model health status
GET    /vibe/agents/status               # Agent status
```

---

## Environment Variables

### Backend

```env
# Database
TIGER_DATABASE_URL=postgres://user:pass@host:port/dbname
REDIS_URL=redis://localhost:6379

# AI Models
ANTHROPIC_API_KEY=sk-ant-xxx
GEMINI_API_KEY=xxx
OPENAI_API_KEY=sk-xxx

# Deployment
GITHUB_TOKEN=ghp_xxx
GITHUB_ORG=your-org-name
VERCEL_TOKEN=xxx
VERCEL_TEAM_ID=team_xxx

# MCP Gateway
MCP_ENABLED=true
MCP_GATEWAY_URL=http://localhost:3100

# Image Storage
CLOUDINARY_CLOUD_NAME=xxx
CLOUDINARY_API_KEY=xxx
CLOUDINARY_API_SECRET=xxx
```

### Frontend

```env
NEXT_PUBLIC_API_URL=https://api.nicole.alphawavelabs.io
```

---

## Performance & Optimization

### Caching Strategy

1. **Redis Cache**
   - Brief templates
   - Common architecture patterns
   - Design system presets

2. **Prompt Cache** (In-Memory)
   - Skill content loaded once
   - Agent prompts compiled once

### Rate Limiting

```python
# Per endpoint limits
/vibe/projects/{id}/activities: 60 requests/min  # High (polling)
/vibe/projects/{id}/planning:   30 requests/min  # Standard
/vibe/projects/{id}/build:      30 requests/min  # Standard
```

### Database Optimization

```sql
-- Indexes for fast lookups
CREATE INDEX idx_vibe_projects_user_status ON vibe_projects(user_id, status);
CREATE INDEX idx_vibe_activities_project_created ON vibe_activities(project_id, created_at DESC);
CREATE INDEX idx_vibe_files_project ON vibe_files(project_id);

-- Vector index for lessons
CREATE INDEX idx_vibe_lessons_embedding ON vibe_lessons 
USING ivfflat (embedding vector_cosine_ops);
```

---

## Error Handling

### Graceful Degradation

1. **Model Failures**
   - Primary model fails → Fallback to secondary
   - Secondary fails → Cooldown + retry
   - All fail → Surface error to user

2. **Tool Failures**
   - Screenshot fails → Continue without screenshot
   - Search fails → Use cached design patterns
   - Deploy fails → Show manual deploy instructions

3. **Parsing Failures**
   - Architecture JSON invalid → Retry with clearer prompt
   - Files not parsed → Show raw response for debugging
   - QA report missing → Generate minimal report

### User-Facing Errors

```typescript
interface PipelineError {
  phase: string;              // Which phase failed
  message: string;            // What went wrong
  suggestion: string;         // How to fix
  raw_response?: string;      // For debugging
}
```

**Example:**

```json
{
  "phase": "Planning",
  "message": "Failed to generate valid architecture",
  "suggestion": "Try simplifying the project description or retry the pipeline",
  "raw_response": "Claude's raw output here..."
}
```

---

## Security Considerations

### API Authentication

All Vibe endpoints require:
- Valid JWT token in `Authorization: Bearer {token}` header
- User ID extracted from JWT
- All projects scoped to user

### Rate Limiting

Prevents abuse:
- Activity polling: 60 req/min
- Phase execution: 30 req/min
- Deployment: 10 req/min

### Database Security

- Row-Level Security (RLS) policies
- All queries parameterized (prevent SQL injection)
- Sensitive data encrypted at rest

### External API Security

- GitHub token: Minimal scopes (repo, workflow)
- Vercel token: Team-scoped
- Never expose tokens in frontend

---

## Future Enhancements

### Roadmap

1. **Real-time SSE Streaming**
   - Stream agent responses word-by-word
   - Show Claude thinking in real-time
   - Eliminate polling

2. **Interactive Preview**
   - Live edit in StackBlitz
   - Hot reload on changes
   - Comment/feedback on components

3. **Multi-Page Apps**
   - E-commerce with cart
   - Blogs with CMS
   - Admin dashboards

4. **Design System Library**
   - Pre-built design systems
   - User can pick from gallery
   - Custom branding

5. **Collaboration**
   - Share projects with team
   - Real-time co-editing
   - Version control

6. **AI Testing**
   - Automated E2E tests
   - Accessibility audits
   - Performance benchmarks

---

## Glossary

| Term | Definition |
|------|------------|
| **Vibe** | AlphaWave's AI web development platform |
| **Agent** | Specialized AI with specific role (Design, Architect, Coding, QA, Review) |
| **Nicole** | Creative Director AI overseeing all agents |
| **MCP** | Model Context Protocol - standard for AI tool integration |
| **Brief** | Structured project requirements from intake phase |
| **Architecture** | Technical design document from planning phase |
| **Design System** | Colors, typography, spacing tokens |
| **Lesson** | Knowledge captured from project to improve future builds |
| **Skill** | Domain-specific expertise loaded into agent prompts |
| **Pipeline** | Automated sequence: Intake → Planning → Build → QA → Review → Deploy |

---

## Credits

**Architecture:** AlphaWave Engineering Team  
**Creative Direction:** Nicole AI  
**Models:** Anthropic Claude, Google Gemini, OpenAI  
**Standards:** NYC Design Agency Quality  
**Philosophy:** Code as if Elon and Sam will review it  

---

**END OF DOCUMENTATION**

For questions or contributions, refer to the main README or contact the engineering team.


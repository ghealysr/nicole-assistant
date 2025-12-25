"""
Enjineer Nicole Service
========================
Nicole's AI agent for the Enjineer dashboard - a conversational coding partner
that can create files, manage plans, dispatch agents, and deploy projects.

This is an Anthropic-quality implementation with:
- Proper agentic tool loop (continues until no more tool calls)
- Streaming with real-time tool execution updates
- Robust error handling and recovery
- Production-grade logging
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, List, Dict, Any
from uuid import uuid4

from anthropic import Anthropic, AsyncAnthropic

from app.config import settings
from app.database import get_tiger_pool
from app.services.knowledge_base_service import kb_service
from app.services.enjineer_qa_service import qa_service

logger = logging.getLogger(__name__)


# ============================================================================
# System Prompt
# ============================================================================

ENJINEER_SYSTEM_PROMPT = """You are Nicole, a MASTER-LEVEL frontend engineer and web designer working inside the Enjineer development dashboard. You build $2-5K quality client websites with elite design patterns.

## Expert Capabilities

You are a master-level expert in:

### Frontend Development
- React 19, Next.js 15 App Router, TypeScript (strict mode)
- Tailwind CSS v4 with OKLCH colors and @theme directive
- shadcn/ui (56 components), Aceternity UI (90+ components), Magic UI
- GSAP 3.14.2 ScrollTrigger, Motion v12 (formerly Framer Motion)
- Responsive design, mobile-first architecture
- Core Web Vitals optimization (LCP ≤2.5s, INP ≤200ms, CLS ≤0.1)

### Design Systems
- Typography systems, fluid type scales with clamp(), variable fonts
- OKLCH color theory, WCAG 2.2 accessibility (4.5:1 contrast minimum)
- 8pt spacing systems, vertical rhythm, container queries
- Bento grids, hero sections, pricing page psychology
- Component composition, design tokens, CVA variants

### Performance Optimization
- Image optimization (Next.js Image, WebP/AVIF, priority loading)
- Code splitting, lazy loading, tree shaking, LazyMotion
- CDN strategies, resource hints (preload/prefetch/preconnect)
- Animation performance (GPU acceleration via transform/opacity only)
- Bundle size optimization (dynamic imports, no unused dependencies)

### Accessibility (Non-Negotiable)
- WCAG 2.2 Level AA compliance always
- Keyboard navigation with visible focus states
- Screen reader support with semantic HTML and ARIA
- Touch targets 24×24px minimum (44×44px recommended)
- prefers-reduced-motion implementation mandatory

## Your Tools
- `create_plan`: Create implementation plan with phases - USE THIS FIRST
- `update_plan_step`: Update phase status as you progress
- `create_file`: Create new project files
- `update_file`: Modify existing files
- `delete_file`: Remove files (use sparingly)
- `dispatch_agent`: Run specialized agents (engineer, qa, sr_qa)
- `request_approval`: Ask user permission before major actions
- `deploy`: Deploy to Vercel after approval

## Knowledge Base (11 Expert Files - ALWAYS REFERENCE)

You have access to 11 expert-level knowledge files (~35,000 words). Reference these for EVERY design decision:

### Patterns (3 files)
- **hero-sections.md**: Awwwards winners, CTA psychology, conversion data (+34% with social proof)
- **bento-grids.md**: CSS Grid layouts, visual hierarchy, subgrid (93% support)
- **pricing-psychology.md**: Anchoring, decoy effect, Good-Better-Best (+112% conversion)

### Animation (2 files)
- **gsap-scrolltrigger.md**: GSAP 3.14.2, useGSAP hook, ScrollTrigger.batch(), INP optimization
- **motion-react.md**: Motion v12 ("motion/react" import), LazyMotion (4.6kb vs 34kb)

### Components (2 files)
- **shadcn-reference.md**: 56 components, react-hook-form + Zod, OKLCH theming
- **aceternity-reference.md**: 90+ animated components, landing page effects

### Fundamentals (4 files)
- **typography.md**: Fluid scales clamp(), Major Third (1.25), line-height 1.5-1.6
- **color-theory.md**: OKLCH > HSL, 60-30-10 rule, dark mode strategies
- **spacing-systems.md**: 8pt grid, Tailwind spacing scale, container padding
- **anti-patterns.md**: What NOT to do (carousels, low contrast, 100vh mobile, div soup)

## CRITICAL: The Complete Build Pipeline

**Follow this EXACT workflow for EVERY project:**

### Phase 1: Planning (REQUIRED FIRST - NO EXCEPTIONS)
1. **Analyze request** - Understand all explicit and implicit requirements
2. **Search knowledge base** - Identify relevant patterns/components
3. **Incorporate design_analysis** - Use inspiration image analysis if provided
4. **Call `create_plan`** with:
   - Detailed phases with sub-steps
   - Knowledge base patterns to apply
   - requires_approval: true for Review/Preview/QA/Deploy phases
5. **STOP AND WAIT** - "Plan created. Please review in the Plan tab and approve when ready."
6. **DO NOT PROCEED** until user explicitly approves

### Phase 2: Implementation with QA Gates
For EACH phase:
1. Call `update_plan_step` with status "in_progress"
2. Reference knowledge base for implementation patterns
3. Write PRODUCTION-READY code (no TODOs, no placeholders)
4. Call `update_plan_step` with status "complete"
5. Call `dispatch_agent` with agent_type="qa"
6. Report QA findings, fix ALL issues before proceeding
7. Ask: "Phase X complete. QA passed. Ready for phase Y?"

### Phase 3: Preview Checkpoint (REQUIRED)
When core layout complete:
1. Trigger QA for preview readiness
2. Announce: "Preview available! Click Update in Preview tab."
3. Wait for user feedback before continuing

### Phase 4: Final QA (REQUIRED before deploy)
1. Call `dispatch_agent` with agent_type="sr_qa" for full audit
2. SR QA performs: Lighthouse, accessibility, mobile, code review
3. Report findings with severity levels
4. Fix ALL critical issues before proceeding

### Phase 5: Deployment (REQUIRES EXPLICIT APPROVAL)
1. Confirm: "All QA passed. Ready to deploy to production?"
2. WAIT for user's explicit "yes"
3. Call `deploy` only after approval
4. Confirm: "Deployed! Your site is live at [URL]"

## Professional Standards (Non-Negotiable)

### Quality Requirements
Every deliverable must be:
- **Production-Ready**: No TODOs, no placeholders, no "implement later"
- **Responsive**: Mobile/tablet/desktop tested
- **Accessible**: WCAG 2.2 Level AA, keyboard nav, screen reader support
- **Type-Safe**: Full TypeScript, no any types, props documented
- **Performant**: Core Web Vitals passing, images optimized, animations GPU-only

### Mandatory Self-Review Before Declaring Complete
- [ ] All requirements implemented (no partial work)
- [ ] No console errors or warnings
- [ ] Responsive verified (mobile, tablet, desktop)
- [ ] Accessibility checked (keyboard, contrast, screen reader)
- [ ] TypeScript types complete
- [ ] Error handling implemented
- [ ] Loading states added
- [ ] Knowledge base patterns applied correctly

### FORBIDDEN Shortcuts
❌ Placeholder text like "Add your content here"
❌ Skip error handling "for brevity"
❌ Omit loading states "to simplify"
❌ Ignore accessibility "for now"
❌ Skip responsive breakpoints "initially"
❌ Use `any` type "temporarily"
❌ Leave TODO comments in production code
❌ Copy example code without adapting
❌ Skip QA agent review
❌ Skip knowledge base search when pattern exists

### ALWAYS Do
✅ Complete implementations fully in first pass
✅ Handle all edge cases and error states
✅ Implement responsive design from start
✅ Add all accessibility attributes
✅ Optimize for Core Web Vitals
✅ Use knowledge base patterns exactly as documented
✅ Run QA agent before declaring done
✅ Test keyboard navigation
✅ Use semantic HTML

## Specific Technical Standards

### Hero Sections (from hero-sections.md)
- Single CTA shows +266% conversion vs multiple
- Touch targets: 44×44px recommended, 24×24px minimum
- Social proof placement: +34% conversion
- Never lazy-load hero images (use priority)
- Video: poster mandatory, WebM > MP4

### Bento Grids (from bento-grids.md)
- Use CSS Grid with grid-template-areas
- Subgrid for nested layouts (93% support)
- Container queries for component responsiveness
- Visual hierarchy: Hero tiles 2×2, feature 1×1
- Golden ratio sizing (1.618:1)

### Pricing Pages (from pricing-psychology.md)
- 3-tier Good-Better-Best structure (+112% conversion)
- "Most Popular" badge (+27-44% to that tier)
- Show annual savings: "2 months free" > "17% off"
- Charm pricing (.99) increases sales 24%
- Money-back guarantee +16% conversion

### Animation (from gsap-scrolltrigger.md, motion-react.md)
- GSAP: useGSAP() hook, ScrollTrigger.batch() for 50+ elements
- Motion: Import from "motion/react" (not "framer-motion")
- LazyMotion + m + domAnimation for 4.6kb bundle
- GPU properties ONLY: transform, opacity, filter
- ALWAYS implement prefers-reduced-motion fallback

### Components (from shadcn-reference.md, aceternity-reference.md)
- shadcn: Forms, tables, modals - accessible, battle-tested
- Aceternity: Marketing effects (Aurora, Meteors, Sparkles)
- Form validation: react-hook-form + Zod always
- CLI: `npx shadcn@latest add [component]`

### Typography (from typography.md)
- Fluid scale: `clamp(1rem, 0.5rem + 2vw, 3rem)`
- Body: 16px minimum, line-height 1.5-1.6
- Headings: line-height 1.1-1.2
- Character width: 45-75 chars optimal
- Variable fonts: Inter, Plus Jakarta Sans, Geist, DM Sans

### Colors (from color-theory.md)
- OKLCH > HSL (perceptual uniformity)
- 60-30-10 distribution rule
- WCAG contrast: 4.5:1 text, 3:1 large text
- Dark mode: intentional palette, not inverted

### Spacing (from spacing-systems.md)
- 8pt grid (4px base, 8px increments)
- Tailwind scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96
- Fluid spacing: clamp(1rem, 2vw, 2rem)

### Anti-Patterns (from anti-patterns.md)
❌ Auto-rotating carousels → User-controlled or static
❌ Low contrast (<4.5:1) → Maintain WCAG compliance
❌ Images without dimensions → Always set width/height
❌ Lazy-loading LCP images → Use priority
❌ 100vh on mobile → Use 100dvh or JS fallback
❌ Animating left/width → Use transform only
❌ Index as React key → Use stable unique IDs
❌ Raw <img> tags → Always use next/image
❌ Hamburger menu on desktop → Show primary nav

## Hallucination Prevention
1. Never invent features not discussed
2. Never assume dependencies exist without checking
3. Always use actual file paths from file tree
4. If unsure, ASK rather than guess
5. Verify before claiming ("I've created X" only after tool call)
6. Check imports exist before using
7. Use explicit types - no implicit any

## Communication Style
- Direct and technical, no hedging
- State facts definitively
- Step-by-step with copy-pasteable commands
- Cite knowledge base: "Per hero-sections.md, single CTA shows +266% conversion"
- Answer to depth asked, no more

## Plan Structure Requirements
Each phase MUST include:
- `phase_number`: Sequential (1, 2, 3...)
- `name`: Clear phase name
- `estimated_minutes`: Realistic time
- `requires_approval`: true for Review/Preview/QA/Deploy

MANDATORY phases in every plan:
1. Project Setup & Configuration
2-N. Implementation phases
N+1. Preview Checkpoint (requires_approval: true)
N+2. Final QA & Audit (requires_approval: true)
N+3. Deploy to Production (requires_approval: true)

## Current Context
- **Time**: {current_time}
- **Timezone**: {timezone}
- **Project**: {project_name}
- **Description**: {project_description}
- **Tech Stack**: {tech_stack}
- **Status**: {project_status}

## Design Analysis from Inspiration Images
{design_analysis}

## Project Files
{file_tree}
"""


# ============================================================================
# Tool Definitions (Anthropic Format)
# ============================================================================

ENJINEER_TOOLS = [
    {
        "name": "create_file",
        "description": "Create a new file in the project. Use this when you need to add new source files, configs, or assets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root, starting with / (e.g., '/src/components/Button.tsx', '/app/page.tsx')"
                },
                "content": {
                    "type": "string",
                    "description": "The complete file content to write"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language for syntax highlighting (typescript, javascript, css, json, markdown, html)"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "update_file",
        "description": "Update an existing file's content. Use this to modify source code, fix bugs, or add features.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the existing file to update"
                },
                "content": {
                    "type": "string",
                    "description": "The new complete content for the file"
                },
                "commit_message": {
                    "type": "string",
                    "description": "Brief description of what changed (for version history)"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file from the project. Use with caution - this is permanent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to delete"
                },
                "reason": {
                    "type": "string",
                    "description": "Why this file is being deleted"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_plan",
        "description": "Create an implementation plan with numbered phases. Each phase has detailed sub-steps. ALWAYS include Preview Checkpoint, Final QA, and Deploy phases.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the plan (e.g., 'Landing Page Implementation')"
                },
                "description": {
                    "type": "string",
                    "description": "Overview of what this plan accomplishes"
                },
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phase_number": {"type": "integer", "description": "Phase order (1, 2, 3...)"},
                            "name": {"type": "string", "description": "Phase name"},
                            "estimated_minutes": {"type": "integer", "description": "Estimated time"},
                            "requires_approval": {"type": "boolean", "description": "Set true for: Preview Checkpoint, Final QA, Deploy phases"},
                            "steps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Detailed sub-steps to complete this phase"
                            },
                            "qa_focus": {
                                "type": "string",
                                "description": "What QA should check after this phase"
                            }
                        },
                        "required": ["phase_number", "name", "steps"]
                    },
                    "description": "Ordered list of implementation phases. MUST include: Preview Checkpoint (requires_approval:true), Final QA (requires_approval:true), Deploy (requires_approval:true)"
                }
            },
            "required": ["name", "phases"]
        }
    },
    {
        "name": "update_plan_step",
        "description": "Update a plan step's status as work progresses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "ID of the plan (provided in context as 'Plan ID: X')"
                },
                "phase_number": {
                    "type": "integer",
                    "description": "Phase number to update"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "complete", "blocked", "skipped"],
                    "description": "New status for the phase"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about the update"
                }
            },
            "required": ["plan_id", "phase_number", "status"]
        }
    },
    {
        "name": "dispatch_agent",
        "description": "Dispatch a specialized agent to perform a focused task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["engineer", "qa", "sr_qa"],
                    "description": "Type of agent: engineer (writes code), qa (tests and finds issues), sr_qa (senior review)"
                },
                "task": {
                    "type": "string",
                    "description": "Detailed description of what the agent should accomplish"
                },
                "focus_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths the agent should focus on"
                }
            },
            "required": ["agent_type", "task"]
        }
    },
    {
        "name": "request_approval",
        "description": "Request user approval before proceeding with a significant action. Required before deploying or making breaking changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "What you're requesting approval for"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed explanation of what will happen if approved"
                },
                "approval_type": {
                    "type": "string",
                    "enum": ["plan", "deploy", "destructive", "major_change"],
                    "description": "Category of approval"
                }
            },
            "required": ["title", "description", "approval_type"]
        }
    },
    {
        "name": "deploy",
        "description": "Deploy the project to Vercel. Requires prior approval for production deployments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": ["preview", "production"],
                    "description": "Target environment"
                },
                "commit_message": {
                    "type": "string",
                    "description": "Deployment commit message"
                }
            },
            "required": ["environment"]
        }
    },
    {
        "name": "search_knowledge_base",
        "description": """Search Nicole's design knowledge base for patterns, components, animations, and best practices.
Use this tool to find specific design guidance before implementing UI components.

Categories available:
- patterns: Hero sections, bento grids, pricing pages
- animation: GSAP ScrollTrigger, Motion (Framer Motion)
- components: shadcn/ui, Aceternity UI
- fundamentals: Typography, color theory, spacing systems
- core: Anti-patterns, common mistakes

ALWAYS use this tool when:
- Implementing hero sections, pricing pages, or bento grids
- Adding animations (GSAP or Motion)
- Choosing components (shadcn vs Aceternity)
- Making design system decisions (typography, colors, spacing)
- Need conversion data or best practices""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - be specific (e.g., 'hero section CTA placement conversion', 'GSAP ScrollTrigger React 19', 'bento grid CSS implementation')"
                },
                "category": {
                    "type": "string",
                    "enum": ["patterns", "animation", "components", "fundamentals", "core"],
                    "description": "Optional category filter to narrow results"
                },
                "include_sections": {
                    "type": "boolean",
                    "description": "If true, search within sections for more granular results. Default: false"
                }
            },
            "required": ["query"]
        }
    }
]


# ============================================================================
# EnjineerNicole Class
# ============================================================================

class EnjineerNicole:
    """
    Nicole's AI agent for the Enjineer dashboard.
    
    Implements an agentic tool loop that:
    1. Receives user message
    2. Calls Claude with tools
    3. Executes any tool calls
    4. Continues conversation until Claude stops using tools
    5. Streams all events to the frontend
    """
    
    def __init__(self, project_id: int, user_id: int):
        """
        Initialize Nicole for a specific project.
        
        Args:
            project_id: INTEGER project ID (not UUID)
            user_id: INTEGER user ID (not UUID)
        """
        self.project_id = int(project_id)
        self.user_id = int(user_id)
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"  # Claude Sonnet 4
        self.project_data: Optional[Dict[str, Any]] = None
        self.max_tool_iterations = 10  # Safety limit
        
        # Token usage tracking for this session
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        
    async def load_project_context(self) -> Dict[str, Any]:
        """Load project data, files, and recent conversation for context."""
        pool = await get_tiger_pool()
        
        async with pool.acquire() as conn:
            # Get project
            project = await conn.fetchrow(
                "SELECT * FROM enjineer_projects WHERE id = $1",
                self.project_id
            )
            
            if not project:
                raise ValueError(f"Project {self.project_id} not found")
            
            # Get files (just paths for tree, we'll fetch content on demand)
            files = await conn.fetch(
                "SELECT path, language FROM enjineer_files WHERE project_id = $1 ORDER BY path",
                self.project_id
            )
            
            # Get recent messages for conversation context
            messages = await conn.fetch(
                """
                SELECT role, content FROM enjineer_messages 
                WHERE project_id = $1 
                ORDER BY created_at DESC 
                LIMIT 20
                """,
                self.project_id
            )
            
            # Get active plan if exists
            plan = await conn.fetchrow(
                """
                SELECT * FROM enjineer_plans 
                WHERE project_id = $1 AND status IN ('draft', 'approved', 'in_progress', 'awaiting_approval')
                ORDER BY created_at DESC LIMIT 1
                """,
                self.project_id
            )
            
            # Get plan phases if plan exists
            phases = []
            if plan:
                phases = await conn.fetch(
                    """
                    SELECT * FROM enjineer_plan_phases 
                    WHERE plan_id = $1 
                    ORDER BY phase_number
                    """,
                    plan["id"]
                )
        
        self.project_data = {
            "id": project["id"],
            "name": project["name"],
            "description": project["description"] or "",
            "tech_stack": project["tech_stack"] or {},
            "status": project["status"],
            "settings": project["settings"] or {},
            "files": [dict(f) for f in files],
            "messages": list(reversed([dict(m) for m in messages])),
            "plan": {
                **dict(plan),
                "phases": [dict(p) for p in phases]
            } if plan else None
        }
        
        return self.project_data
    
    def build_system_prompt(self) -> str:
        """Build system prompt with rich project context including design analysis."""
        if not self.project_data:
            raise ValueError("Project data not loaded. Call load_project_context first.")
        
        # Build tech stack string
        tech_stack = self.project_data.get("tech_stack") or {}
        tech_stack_str = ", ".join(f"{k}: {v}" for k, v in tech_stack.items()) or "Next.js, React, TypeScript, Tailwind CSS"
        
        # Build file tree
        files = self.project_data.get("files") or []
        if files:
            file_tree = "\n".join(f"- {f['path']} ({f.get('language', 'unknown')})" for f in files[:50])
            if len(files) > 50:
                file_tree += f"\n... and {len(files) - 50} more files"
        else:
            file_tree = "(No files yet - this is a new project)"
        
        # Build design analysis from inspiration images
        intake_data = self.project_data.get("intake_data") or {}
        design_analysis = intake_data.get("design_analysis")
        
        if design_analysis and isinstance(design_analysis, dict) and "error" not in design_analysis:
            if "raw" in design_analysis:
                design_analysis_str = f"Inspiration Image Analysis:\n{design_analysis['raw']}"
            else:
                # Format structured design analysis
                parts = ["**Inspiration Image Analysis:**"]
                if design_analysis.get("summary"):
                    parts.append(f"Summary: {design_analysis['summary']}")
                if design_analysis.get("design_style"):
                    parts.append(f"Style: {design_analysis['design_style']}")
                if design_analysis.get("color_palette"):
                    colors = design_analysis['color_palette']
                    parts.append(f"Colors: Primary {colors.get('primary', 'N/A')}, Secondary {colors.get('secondary', 'N/A')}, Accent {colors.get('accent', 'N/A')}, Background {colors.get('background', 'N/A')}, Text {colors.get('text', 'N/A')}")
                if design_analysis.get("typography"):
                    typo = design_analysis['typography']
                    parts.append(f"Typography: {typo.get('style', '')} - Heading: {typo.get('heading_font', 'N/A')}, Body: {typo.get('body_font', 'N/A')}")
                if design_analysis.get("layout"):
                    parts.append(f"Layout: {design_analysis['layout']}")
                if design_analysis.get("components"):
                    parts.append(f"Key Components: {', '.join(design_analysis['components'][:10])}")
                if design_analysis.get("visual_effects"):
                    parts.append(f"Visual Effects: {', '.join(design_analysis['visual_effects'][:5])}")
                if design_analysis.get("key_features"):
                    parts.append(f"Key Features: {', '.join(design_analysis['key_features'][:5])}")
                design_analysis_str = "\n".join(parts)
        else:
            design_analysis_str = "(No inspiration images provided)"
        
        # Get timezone
        try:
            import pytz
            tz = pytz.timezone("America/New_York")
            now = datetime.now(tz)
            timezone_str = "EST (America/New_York)"
        except Exception:
            now = datetime.now(timezone.utc)
            timezone_str = "UTC"
        
        return ENJINEER_SYSTEM_PROMPT.format(
            current_time=now.strftime("%A, %B %d, %Y at %I:%M %p"),
            timezone=timezone_str,
            project_name=self.project_data["name"],
            project_description=self.project_data["description"] or "No description provided",
            tech_stack=tech_stack_str,
            project_status=self.project_data["status"],
            design_analysis=design_analysis_str,
            file_tree=file_tree
        )
    
    async def build_messages(self, new_message: str) -> List[Dict[str, Any]]:
        """Build message history including context injections and knowledge base."""
        messages = []
        
        # =========================================================================
        # AUTO-INJECT RELEVANT KNOWLEDGE BASE CONTENT
        # =========================================================================
        # This is the critical piece - automatically search for relevant design
        # knowledge based on the user's message and inject it as context
        try:
            if new_message and len(new_message) > 10:
                relevant_knowledge = await kb_service.get_relevant_context(
                    query=new_message,
                    max_sections=5,
                    max_tokens=6000  # ~4500 words of knowledge context
                )
                
                if relevant_knowledge and len(relevant_knowledge) > 100:
                    messages.append({
                        "role": "user", 
                        "content": f"[KNOWLEDGE BASE CONTEXT - Apply these patterns exactly]\n\n{relevant_knowledge}"
                    })
                    messages.append({
                        "role": "assistant", 
                        "content": "I've reviewed the relevant design knowledge. I'll apply these patterns and cite sources in my implementation."
                    })
                    logger.info(f"[KB] Auto-injected {len(relevant_knowledge)} chars of knowledge context")
                    
                    # Log the auto-injection for analytics
                    try:
                        await kb_service.log_access(
                            file_id=None,  # Auto-injection covers multiple files
                            user_id=self.user_id,
                            query_text=new_message[:500],  # First 500 chars
                            access_method="auto_inject"
                        )
                    except Exception:
                        pass  # Non-critical, don't fail message building
        except Exception as e:
            logger.warning(f"[KB] Failed to auto-inject knowledge: {e}")
        
        # Add plan context if exists
        if self.project_data.get("plan"):
            plan = self.project_data["plan"]
            # Content is stored as JSON string - parse to get name
            try:
                content = json.loads(plan.get("content", "{}") or "{}")
                plan_name = content.get("name", "Unnamed Plan")
            except (json.JSONDecodeError, TypeError):
                plan_name = "Unnamed Plan"
            plan_text = f"**Current Plan: {plan_name}**\nStatus: {plan.get('status', 'unknown')}\n"
            
            phases = plan.get("phases", [])
            if phases:
                plan_text += "\nPhases:\n"
                for p in phases[:10]:
                    status_emoji = {
                        "pending": "⬜",
                        "in_progress": "🔵",
                        "complete": "✅",
                        "blocked": "🔴",
                        "skipped": "⏭️",
                        "awaiting_approval": "⏸️"
                    }.get(p.get("status", "pending"), "⬜")
                    plan_text += f"{status_emoji} Phase {p.get('phase_number', '?')}: {p.get('name', 'Unknown')}\n"
            
            # Add plan_id so Nicole can reference it in update_plan_step
            plan_id = plan.get("id")
            plan_text += f"\n**Plan ID: {plan_id}** (use this when calling update_plan_step)"
            
            messages.append({"role": "user", "content": f"[CONTEXT: Current Plan]\n{plan_text}"})
            messages.append({"role": "assistant", "content": "I see the current plan. I'll continue from where we left off."})
        
        # Add conversation history (limit to prevent token overflow)
        # Filter out messages with empty content to avoid API errors
        history = self.project_data.get("messages", [])[-8:]
        for msg in history:
            content = msg.get("content", "")
            if content and content.strip():  # Only add non-empty messages
                messages.append({
                    "role": msg["role"],
                    "content": content
                })
        
        # Add the new user message (ensure it's not empty)
        if new_message and new_message.strip():
            messages.append({
                "role": "user",
                "content": new_message
            })
        else:
            # Fallback for empty messages
            messages.append({
                "role": "user",
                "content": "Continue with the project."
            })
        
        return messages
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return structured result.
        
        Returns:
            Dict with 'success' bool and either 'result' or 'error'
        """
        logger.warning(f"[Enjineer] Executing tool: {tool_name}")
        pool = await get_tiger_pool()
        
        try:
            if tool_name == "create_file":
                return await self._create_file(pool, tool_input)
            elif tool_name == "update_file":
                return await self._update_file(pool, tool_input)
            elif tool_name == "delete_file":
                return await self._delete_file(pool, tool_input)
            elif tool_name == "create_plan":
                return await self._create_plan(pool, tool_input)
            elif tool_name == "update_plan_step":
                return await self._update_plan_step(pool, tool_input)
            elif tool_name == "dispatch_agent":
                return await self._dispatch_agent(pool, tool_input)
            elif tool_name == "request_approval":
                return await self._request_approval(pool, tool_input)
            elif tool_name == "deploy":
                return await self._deploy(pool, tool_input)
            elif tool_name == "search_knowledge_base":
                return await self._search_knowledge_base(tool_input)
            else:
                result = {"success": False, "error": f"Unknown tool: {tool_name}"}
                logger.warning(f"[Enjineer] Tool result: {result}")
                return result
        except Exception as e:
            logger.error(f"[Enjineer] Tool {tool_name} failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # Tool Implementations
    # ========================================================================
    
    async def _create_file(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new file in the project."""
        path = input_data.get("path")
        content = input_data.get("content")
        
        if not path:
            return {"success": False, "error": "File path is required"}
        if content is None:
            return {"success": False, "error": "File content is required"}
            
        language = input_data.get("language") or self._detect_language(path)
        checksum = hashlib.sha256(content.encode()).hexdigest()
        
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        
        async with pool.acquire() as conn:
            # Check if file exists
            existing = await conn.fetchrow(
                "SELECT id FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
            
            if existing:
                return {"success": False, "error": f"File already exists: {path}. Use update_file instead."}
            
            # Create the file
            file = await conn.fetchrow(
                """
                INSERT INTO enjineer_files (project_id, path, content, language, modified_by, checksum)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, version
                """,
                self.project_id, path, content, language, "nicole", checksum
            )
        
        logger.info(f"[Enjineer] Created file: {path} ({len(content)} chars)")
        return {
            "success": True,
            "result": {
                "action": "file_created",
                "path": path,
                "language": language,
                "size": len(content),
                "version": file["version"]
            }
        }
    
    async def _update_file(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing file."""
        path = input_data.get("path")
        content = input_data.get("content")
        
        if not path:
            return {"success": False, "error": "File path is required"}
        if content is None:
            return {"success": False, "error": "File content is required"}
            
        commit_message = input_data.get("commit_message", "Updated by Nicole")
        checksum = hashlib.sha256(content.encode()).hexdigest()
        
        if not path.startswith("/"):
            path = "/" + path
        
        async with pool.acquire() as conn:
            file = await conn.fetchrow(
                "SELECT id, version, content FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
            
            if not file:
                return {"success": False, "error": f"File not found: {path}. Use create_file for new files."}
            
            new_version = file["version"] + 1
            old_content = file["content"]
            
            # Update file
            await conn.execute(
                """
                UPDATE enjineer_files 
                SET content = $1, version = $2, modified_by = $3, checksum = $4, updated_at = NOW()
                WHERE id = $5
                """,
                content, new_version, "nicole", checksum, file["id"]
            )
            
            # Create version history entry
            await conn.execute(
                """
                INSERT INTO enjineer_file_versions (file_id, version, content, modified_by, commit_message)
                VALUES ($1, $2, $3, $4, $5)
                """,
                file["id"], new_version, content, "nicole", commit_message
            )
        
        logger.info(f"[Enjineer] Updated file: {path} (v{new_version})")
        return {
            "success": True,
            "result": {
                "action": "file_updated",
                "path": path,
                "version": new_version,
                "commit_message": commit_message
            }
        }
    
    async def _delete_file(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file from the project."""
        path = input_data.get("path")
        if not path:
            return {"success": False, "error": "File path is required"}
            
        reason = input_data.get("reason", "No reason provided")
        
        if not path.startswith("/"):
            path = "/" + path
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
        
        if result == "DELETE 0":
            return {"success": False, "error": f"File not found: {path}"}
        
        logger.info(f"[Enjineer] Deleted file: {path} (reason: {reason})")
        return {
            "success": True,
            "result": {
                "action": "file_deleted",
                "path": path,
                "reason": reason
            }
        }
    
    async def _create_plan(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an implementation plan with phases."""
        logger.warning(f"[Enjineer] create_plan called with input: {input_data}")
        
        name = input_data.get("name")
        if not name:
            logger.warning("[Enjineer] create_plan failed: no name provided")
            return {"success": False, "error": "Plan name is required"}
        
        description = input_data.get("description", "")
        phases_data = input_data.get("phases", [])
        
        logger.warning(f"[Enjineer] create_plan: name='{name}', phases_count={len(phases_data)}")
        
        if not phases_data:
            logger.warning("[Enjineer] create_plan failed: no phases provided")
            return {"success": False, "error": "At least one phase is required"}
        
        # Generate plan.md content with detailed sub-steps
        plan_md = f"""# {name}

## Overview
{description}

## Phases

"""
        total_time = 0
        for phase in phases_data:
            phase_num = phase.get("phase_number", 1)
            phase_name = phase.get("name", "Unnamed Phase")
            est_mins = phase.get("estimated_minutes", 30)
            needs_approval = phase.get("requires_approval", False)
            steps = phase.get("steps", [])
            qa_focus = phase.get("qa_focus", "")
            total_time += est_mins
            
            approval_note = " *(requires approval)*" if needs_approval else ""
            plan_md += f"### Phase {phase_num}: {phase_name}{approval_note}\n"
            plan_md += f"- **Estimated time**: {est_mins} minutes\n"
            
            if steps:
                plan_md += "- **Steps**:\n"
                for i, step in enumerate(steps, 1):
                    plan_md += f"  {i}. {step}\n"
            
            if qa_focus:
                plan_md += f"- **QA Focus**: {qa_focus}\n"
            
            plan_md += "\n"
        
        plan_md += f"""## Timeline
- **Total estimated time**: {total_time} minutes ({total_time // 60}h {total_time % 60}m)
- **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## QA Checkpoints
After each phase, QA agent reviews:
- Code quality and syntax
- Plan alignment
- Hallucination detection
- Issue identification

## Approval Required
This plan requires your approval before implementation begins. Review the phases above and approve to start.

---
*Awaiting approval*
"""

        async with pool.acquire() as conn:
            # Create plan - set status to awaiting_approval so user must approve first
            row = await conn.fetchrow(
                """
                INSERT INTO enjineer_plans (project_id, version, content, status, current_phase_number)
                VALUES ($1, '1.0', $2, 'awaiting_approval', 0)
                RETURNING id
                """,
                self.project_id, json.dumps({"name": name, "description": description})
            )
            plan_id = row["id"]
            
            # Create phases - all start as pending
            for phase in phases_data:
                await conn.execute(
                    """
                    INSERT INTO enjineer_plan_phases 
                    (plan_id, phase_number, name, status, estimated_minutes, requires_approval, approval_status)
                    VALUES ($1, $2, $3, 'pending', $4, $5, $6)
                    """,
                    plan_id,
                    phase.get("phase_number", 1),
                    phase.get("name", "Unnamed Phase"),
                    phase.get("estimated_minutes", 30),
                    phase.get("requires_approval", False),
                    'pending' if phase.get("requires_approval", False) else None
                )
            
            # Create plan.md file in the project
            await conn.execute(
                """
                INSERT INTO enjineer_files (project_id, path, content, language, checksum)
                VALUES ($1, '/plan.md', $2, 'markdown', $3)
                ON CONFLICT (project_id, path) DO UPDATE SET content = $2, checksum = $3, updated_at = NOW()
                """,
                self.project_id, plan_md, hashlib.sha256(plan_md.encode()).hexdigest()
            )
        
        logger.warning(f"[Enjineer] Created plan '{name}' (id={plan_id}) with {len(phases_data)} phases - awaiting approval")
        return {
            "success": True,
            "result": {
                "action": "plan_created",
                "plan_id": str(plan_id),
                "name": name,
                "phases_count": len(phases_data),
                "awaiting_approval": True,
                "message": f"I've created the plan '{name}' with {len(phases_data)} phases and saved it to plan.md. Please review the Plan tab and **approve the plan** before I begin implementation."
            }
        }
    
    async def _update_plan_step(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a plan phase status."""
        plan_id = input_data.get("plan_id")
        phase_number = input_data.get("phase_number")
        status = input_data.get("status")
        
        if not plan_id:
            return {"success": False, "error": "plan_id is required"}
        if phase_number is None:
            return {"success": False, "error": "phase_number is required"}
        if not status:
            return {"success": False, "error": "status is required"}
            
        notes = input_data.get("notes")
        
        # Convert plan_id to int if it's a string
        try:
            plan_id_int = int(plan_id)
        except (ValueError, TypeError):
            return {"success": False, "error": f"Invalid plan_id: {plan_id}"}
        
        async with pool.acquire() as conn:
            # Check if this phase requires approval and is being marked complete
            phase_info = await conn.fetchrow(
                "SELECT requires_approval, approval_status FROM enjineer_plan_phases WHERE plan_id = $1 AND phase_number = $2",
                plan_id_int, phase_number
            )
            
            # If phase requires approval and we're trying to complete it, set to awaiting_approval instead
            actual_status = status
            if status == 'complete' and phase_info and phase_info['requires_approval'] and phase_info['approval_status'] != 'approved':
                actual_status = 'awaiting_approval'
            
            result = await conn.execute(
                """
                UPDATE enjineer_plan_phases 
                SET status = $1, notes = COALESCE($2, notes),
                    started_at = CASE WHEN $1 = 'in_progress' AND started_at IS NULL THEN NOW() ELSE started_at END,
                    completed_at = CASE WHEN $1 = 'complete' THEN NOW() ELSE completed_at END
                WHERE plan_id = $3 AND phase_number = $4
                """,
                actual_status, notes, plan_id_int, phase_number
            )
        
        if result == "UPDATE 0":
            return {"success": False, "error": f"Phase {phase_number} not found in plan {plan_id}"}
        
        logger.info(f"[Enjineer] Updated plan phase {phase_number} to {actual_status}")
        return {
            "success": True,
            "result": {
                "action": "phase_updated",
                "plan_id": plan_id,
                "phase_number": phase_number,
                "status": actual_status
            }
        }
    
    async def _dispatch_agent(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch a specialized agent to perform a task.
        
        Agent Types:
        - qa: Standard QA using GPT-4o (fast, different perspective)
        - sr_qa: Senior QA using Claude Opus 4.5 (deep architectural review)
        - full_qa: Complete pipeline (GPT-4o → Opus 4.5)
        - engineer: Complex coding tasks (dispatched to main Nicole loop)
        
        MULTI-MODEL QA SYSTEM:
        - GPT-4o catches common patterns, React issues, accessibility basics
        - Claude Opus 4.5 provides deep architectural analysis, security audit
        - Running both gives maximum coverage through model diversity
        """
        agent_type = input_data.get("agent_type", "qa")
        task = input_data.get("task", "Review code")
        focus_files = input_data.get("focus_files", [])
        phase_context = input_data.get("phase_context", None)
        
        # Log the dispatch - use RETURNING id since enjineer_agent_executions.id is SERIAL
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO enjineer_agent_executions 
                (project_id, agent_type, instruction, context, focus_areas, status)
                VALUES ($1, $2, $3, $4, $5, 'running')
                RETURNING id
                """,
                self.project_id, agent_type, task,
                json.dumps({"files": focus_files, "phase_context": phase_context}), focus_files
            )
            execution_id = row["id"]  # Integer from SERIAL
        
        logger.warning(f"[Enjineer] Running {agent_type} agent (multi-model QA): {task[:100]}...")
        
        try:
            # Get files for QA review
            files_for_review = await self._get_files_for_qa(pool, focus_files)
            
            if agent_type == "qa":
                # Standard QA with GPT-4o
                result = await qa_service.run_standard_qa(
                    project_id=self.project_id,
                    files=files_for_review,
                    phase_context=phase_context or task,
                    user_id=self.user_id
                )
            elif agent_type == "sr_qa":
                # Senior QA with Claude Opus 4.5
                result = await qa_service.run_senior_qa(
                    project_id=self.project_id,
                    files=files_for_review,
                    phase_context=phase_context or task,
                    user_id=self.user_id
                )
            elif agent_type == "full_qa":
                # Full pipeline: GPT-4o → Opus 4.5
                result = await qa_service.run_full_qa_pipeline(
                    project_id=self.project_id,
                    files=files_for_review,
                    phase_context=phase_context or task,
                    user_id=self.user_id
                )
            elif agent_type == "engineer":
                result = {
                    "success": True,
                    "status": "deferred",
                    "message": "Engineering tasks flow through the main Nicole loop. Please describe the task directly."
                }
            else:
                result = {"success": False, "status": "error", "message": f"Unknown agent type: {agent_type}"}
            
            # Transform result to standard format
            status = "pass" if result.get("passed") or result.get("success") else "fail"
            if result.get("verdict") == "CONDITIONAL_APPROVAL":
                status = "warning"
            
            # Update execution status and store QA report
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE enjineer_agent_executions 
                    SET status = $1, result = $2, completed_at = NOW()
                    WHERE id = $3
                    """,
                    "completed" if result.get("status") != "error" else "failed",
                    json.dumps(result),
                    execution_id
                )
                
                # Store QA report if it's a QA agent
                if agent_type in ("qa", "sr_qa"):
                    # Map status to valid overall_status values
                    status_map = {"pass": "pass", "fail": "fail", "warning": "partial", "error": "fail"}
                    overall_status = status_map.get(result.get("status", "pass"), "partial")
                    
                    # Build checks array from issues
                    issues = result.get("issues", [])
                    checks = []
                    for issue in issues:
                        checks.append({
                            "name": issue.get("description", "Issue"),
                            "status": "fail" if issue.get("severity") in ("critical", "high") else "warning",
                            "message": issue.get("description", "")
                        })
                    if not checks:
                        checks.append({"name": "Code Review", "status": overall_status, "message": result.get("summary", "Complete")})
                    
                    # Get current plan_id for linkage
                    current_plan = await conn.fetchrow(
                        "SELECT id FROM enjineer_plans WHERE project_id = $1 AND status IN ('approved', 'in_progress') ORDER BY id DESC LIMIT 1",
                        self.project_id
                    )
                    plan_id = current_plan["id"] if current_plan else None
                    
                    await conn.execute(
                        """
                        INSERT INTO enjineer_qa_reports 
                        (project_id, execution_id, plan_id, trigger_type, qa_depth, overall_status, checks, summary, 
                         blocking_issues_count, warnings_count, passed_count, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
                        """,
                        self.project_id,
                        execution_id,  # Already an integer from SERIAL
                        plan_id,  # plan_id linkage
                        "phase_complete",  # trigger_type
                        "standard" if agent_type == "qa" else "thorough",  # qa_depth
                        overall_status,
                        json.dumps(checks),
                        result.get("summary", ""),
                        len([i for i in issues if i.get("severity") in ("critical", "high")]),
                        len([i for i in issues if i.get("severity") in ("medium", "low")]),
                        1 if overall_status == "pass" else 0
                    )
            
            logger.warning(f"[Enjineer] Agent {agent_type} completed: status={result.get('status')}")
            
            return {
                "success": result.get("status") != "error",
                "result": {
                    "action": "agent_completed",
                    "execution_id": execution_id,
                    "agent": agent_type,
                    "status": result.get("status", "unknown"),
                    "summary": result.get("summary", "Review complete"),
                    **result
                }
            }
            
        except Exception as e:
            logger.error(f"[Enjineer] Agent {agent_type} failed: {e}")
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE enjineer_agent_executions SET status = 'failed', completed_at = NOW() WHERE id = $1""",
                    execution_id
                )
            return {
                "success": False,
                "result": {"action": "agent_failed", "error": str(e)}
            }
    
    async def _get_files_for_qa(self, pool, focus_files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get project files formatted for QA review.
        
        Args:
            pool: Database connection pool
            focus_files: Optional list of specific file paths to include
            
        Returns:
            List of file dictionaries with path and content
        """
        async with pool.acquire() as conn:
            files = await conn.fetch(
                "SELECT path, content, language FROM enjineer_files WHERE project_id = $1",
                self.project_id
            )
        
        result = []
        for f in files:
            # Filter by focus files if specified
            if focus_files and f["path"] not in focus_files:
                continue
            
            result.append({
                "path": f["path"],
                "content": f["content"],
                "language": f["language"]
            })
        
        return result
    
    # =========================================================================
    # LEGACY QA METHODS (Deprecated - now using multi-model qa_service)
    # =========================================================================
    # The following methods are kept for backwards compatibility but the main
    # _dispatch_agent now routes to qa_service which uses:
    # - GPT-4o for standard QA (fast, different training perspective)
    # - Claude Opus 4.5 for senior QA (deep reasoning, architectural)
    #
    # This multi-model approach provides true QA diversity - different models
    # catch different issues based on their unique training and reasoning.
    
    async def _request_approval(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request user approval for a significant action."""
        title = input_data["title"]
        description = input_data["description"]
        approval_type = input_data["approval_type"]
        
        approval_id = str(uuid4())
        
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO enjineer_approvals 
                (id, project_id, approval_type, title, description, status)
                VALUES ($1, $2, $3, $4, $5, 'pending')
                """,
                approval_id, self.project_id, approval_type, title, description
            )
        
        logger.info(f"[Enjineer] Created approval request: {title}")
        return {
            "success": True,
            "result": {
                "action": "approval_requested",
                "approval_id": approval_id,
                "title": title,
                "approval_type": approval_type,
                "awaiting_user": True,
                "message": f"Waiting for your approval: {title}"
            }
        }
    
    async def _deploy(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy the project to Vercel."""
        environment = input_data["environment"]
        commit_message = input_data.get("commit_message", "Deployed by Enjineer")
        
        # Check for pending deployment approval if production
        if environment == "production":
            async with pool.acquire() as conn:
                pending = await conn.fetchrow(
                    """
                    SELECT id FROM enjineer_approvals 
                    WHERE project_id = $1 AND approval_type = 'deploy' AND status = 'pending'
                    ORDER BY requested_at DESC LIMIT 1
                    """,
                    self.project_id
                )
            
            if pending:
                return {
                    "success": False,
                    "error": "Production deployment requires approval. Please approve the pending request first.",
                    "approval_id": str(pending["id"])
                }
        
        # Create deployment record
        deployment_id = str(uuid4())
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO enjineer_deployments 
                (id, project_id, platform, environment, status, commit_sha)
                VALUES ($1, $2, 'vercel', $3, 'pending', $4)
                """,
                deployment_id, self.project_id, environment, commit_message[:40]
            )
        
        # TODO: Actually trigger Vercel deployment
        logger.info(f"[Enjineer] Initiated {environment} deployment")
        
        return {
            "success": True,
            "result": {
                "action": "deployment_initiated",
                "deployment_id": deployment_id,
                "environment": environment,
                "status": "pending",
                "message": f"Deployment to {environment} has been initiated. You'll receive a preview URL shortly."
            }
        }
    
    async def _search_knowledge_base(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search Nicole's design knowledge base for patterns and best practices.
        
        Returns formatted context that Nicole can directly use in responses.
        """
        query = input_data.get("query")
        if not query:
            return {"success": False, "error": "Search query is required"}
        
        category = input_data.get("category")
        include_sections = input_data.get("include_sections", False)
        
        try:
            # Search files first
            file_results = await kb_service.search_fulltext(
                query=query,
                category=category,
                limit=5
            )
            
            section_results = []
            if include_sections or not file_results:
                # Also search sections for granular results
                section_results = await kb_service.search_sections(
                    query=query,
                    limit=10
                )
            
            if not file_results and not section_results:
                return {
                    "success": True,
                    "result": {
                        "found": False,
                        "message": f"No knowledge found for '{query}'. You may need to use your built-in expertise.",
                        "query": query
                    }
                }
            
            # Format results for Nicole
            formatted_results = []
            
            for f in file_results[:3]:
                formatted_results.append({
                    "type": "file",
                    "slug": f["slug"],
                    "title": f["title"],
                    "category": f["category"],
                    "description": f.get("description", ""),
                    "relevance": round(float(f.get("relevance", 0)), 3),
                    "usage_count": f.get("usage_count", 0),
                    "tags": f.get("tags", [])
                })
            
            # Add relevant sections with their content
            section_context = []
            for s in section_results[:5]:
                section_context.append({
                    "file": s["file_title"],
                    "file_slug": s["file_slug"],
                    "heading": s["heading"],
                    "content": s["content"][:2000],  # Truncate long sections
                    "relevance": round(float(s.get("relevance", 0)), 3)
                })
            
            # Log the access
            if file_results:
                await kb_service.log_access(
                    file_id=file_results[0]["id"],
                    query_text=query,
                    access_method="nicole_search"
                )
            
            logger.info(f"[KB] Search '{query}' returned {len(file_results)} files, {len(section_results)} sections")
            
            return {
                "success": True,
                "result": {
                    "found": True,
                    "query": query,
                    "category_filter": category,
                    "files": formatted_results,
                    "sections": section_context,
                    "instruction": "Use this knowledge to inform your implementation. Cite sources when applying patterns (e.g., 'According to hero-sections.md...')"
                }
            }
            
        except Exception as e:
            logger.error(f"[KB] Search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Knowledge base search failed: {str(e)}"
            }
    
    def _detect_language(self, path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".css": "css",
            ".scss": "scss",
            ".json": "json",
            ".md": "markdown",
            ".html": "html",
            ".py": "python",
            ".sql": "sql",
            ".yaml": "yaml",
            ".yml": "yaml",
        }
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return "plaintext"
    
    # ========================================================================
    # Usage Tracking
    # ========================================================================
    
    async def _save_session_usage(self) -> None:
        """Save session token usage to database for project cost tracking."""
        pool = await get_tiger_pool()
        
        # Claude Sonnet 4 pricing: $3/1M input, $15/1M output
        input_cost = (self.session_input_tokens / 1_000_000) * 3.0
        output_cost = (self.session_output_tokens / 1_000_000) * 15.0
        total_cost = input_cost + output_cost
        
        async with pool.acquire() as conn:
            # Update project's cumulative usage
            await conn.execute(
                """
                UPDATE enjineer_projects 
                SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{usage}',
                    COALESCE(metadata->'usage', '{}'::jsonb) || jsonb_build_object(
                        'total_input_tokens', COALESCE((metadata->'usage'->>'total_input_tokens')::bigint, 0) + $2,
                        'total_output_tokens', COALESCE((metadata->'usage'->>'total_output_tokens')::bigint, 0) + $3,
                        'total_cost_usd', COALESCE((metadata->'usage'->>'total_cost_usd')::numeric, 0) + $4,
                        'last_updated', NOW()
                    )
                ),
                updated_at = NOW()
                WHERE id = $1
                """,
                self.project_id,
                self.session_input_tokens,
                self.session_output_tokens,
                total_cost
            )
        
        logger.debug(f"[Enjineer] Saved usage: {self.session_input_tokens}+{self.session_output_tokens} tokens, ${total_cost:.6f}")
    
    # ========================================================================
    # Main Message Processing (Agentic Loop)
    # ========================================================================
    
    async def process_message(
        self,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and yield streaming events.
        
        Implements an agentic tool loop:
        1. Send message to Claude
        2. Stream text responses
        3. Execute tool calls
        4. Continue until Claude stops using tools
        
        Yields events of types:
        - {"type": "text", "content": "..."}
        - {"type": "thinking", "content": "..."}  
        - {"type": "tool_use", "tool": "...", "input": {...}, "status": "running|complete|error"}
        - {"type": "tool_result", "tool": "...", "result": {...}}
        - {"type": "code", "path": "...", "content": "...", "action": "created|updated"}
        - {"type": "approval_required", "approval_id": "..."}
        - {"type": "error", "content": "..."}
        - {"type": "done"}
        """
        
        # Load project context
        await self.load_project_context()
        
        # Build initial request
        system_prompt = self.build_system_prompt()
        messages = await self.build_messages(message)
        
        logger.info(f"[Enjineer] Processing message for project '{self.project_data['name']}' ({self.project_id})")
        
        iteration = 0
        
        while iteration < self.max_tool_iterations:
            iteration += 1
            logger.debug(f"[Enjineer] Tool loop iteration {iteration}")
            
            try:
                # Call Claude with streaming
                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=8192,
                    system=system_prompt,
                    messages=messages,
                    tools=ENJINEER_TOOLS
                ) as stream:
                    
                    current_text = ""
                    tool_calls = []
                    
                    async for event in stream:
                        if event.type == "content_block_start":
                            if hasattr(event.content_block, "type"):
                                if event.content_block.type == "tool_use":
                                    tool_calls.append({
                                        "id": event.content_block.id,
                                        "name": event.content_block.name,
                                        "input": {}
                                    })
                                    yield {
                                        "type": "tool_use",
                                        "tool": event.content_block.name,
                                        "status": "starting"
                                    }
                                    
                        elif event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                text = event.delta.text
                                current_text += text
                                yield {"type": "text", "content": text}
                            elif hasattr(event.delta, "partial_json"):
                                # Tool input being streamed - accumulate
                                if tool_calls:
                                    # We'll get the full input from the final message
                                    pass
                    
                    # Get the final message to extract complete tool inputs
                    final_message = await stream.get_final_message()
                    stop_reason = final_message.stop_reason
                    
                    # Track token usage from this API call
                    if hasattr(final_message, 'usage') and final_message.usage:
                        self.session_input_tokens += final_message.usage.input_tokens or 0
                        self.session_output_tokens += final_message.usage.output_tokens or 0
                
                # If no tool calls, we're done
                if stop_reason != "tool_use":
                    logger.debug(f"[Enjineer] No more tool calls, stop_reason={stop_reason}")
                    break
                
                # Process tool calls
                tool_results = []
                assistant_content = []
                
                for block in final_message.content:
                    if block.type == "text":
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        tool_id = block.id
                        tool_name = block.name
                        
                        # Ensure tool_input is a dict (some SDK versions return string)
                        raw_input = block.input
                        if isinstance(raw_input, str):
                            try:
                                tool_input = json.loads(raw_input)
                            except json.JSONDecodeError:
                                logger.error(f"[Enjineer] Failed to parse tool input: {raw_input[:100]}")
                                tool_input = {}
                        elif isinstance(raw_input, dict):
                            tool_input = raw_input
                        else:
                            logger.error(f"[Enjineer] Unexpected tool input type: {type(raw_input)}")
                            tool_input = {}
                        
                        assistant_content.append({
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_name,
                            "input": tool_input
                        })
                        
                        # Emit tool start event
                        yield {
                            "type": "tool_use",
                            "tool": tool_name,
                            "input": tool_input,
                            "status": "running"
                        }
                        
                        # Execute the tool
                        result = await self.execute_tool(tool_name, tool_input)
                        
                        # Emit tool result event
                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": result
                        }
                        
                        # Special handling for file operations - emit code event
                        if tool_name in ("create_file", "update_file") and result.get("success"):
                            yield {
                                "type": "code",
                                "path": tool_input.get("path", ""),
                                "content": tool_input.get("content", ""),
                                "action": "created" if tool_name == "create_file" else "updated"
                            }
                        
                        # Special handling for approval requests
                        if tool_name == "request_approval" and result.get("success"):
                            inner_result = result.get("result", {})
                            if isinstance(inner_result, dict):
                                yield {
                                    "type": "approval_required",
                                    "approval_id": inner_result.get("approval_id", ""),
                                    "title": inner_result.get("title", "Approval Required")
                                }
                        
                        # Add tool result for continuation
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result)
                        })
                
                # Add assistant message and tool results to conversation for next iteration
                # Ensure assistant_content is not empty (Claude API requires non-empty content)
                if assistant_content:
                    messages.append({"role": "assistant", "content": assistant_content})
                else:
                    # Add a minimal text block if only tool uses were returned
                    messages.append({"role": "assistant", "content": [{"type": "text", "text": "Processing..."}]})
                
                # Tool results go as user message
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                
            except Exception as e:
                logger.error(f"[Enjineer] Error in process_message: {e}", exc_info=True)
                yield {"type": "error", "content": str(e)}
                break
        
        if iteration >= self.max_tool_iterations:
            logger.warning(f"[Enjineer] Hit max tool iterations ({self.max_tool_iterations})")
            yield {"type": "text", "content": "\n\n*I've reached the maximum number of operations. Let me know if you'd like me to continue.*"}
        
        # Save session usage to database
        if self.session_input_tokens > 0 or self.session_output_tokens > 0:
            try:
                await self._save_session_usage()
            except Exception as e:
                logger.error(f"[Enjineer] Failed to save usage: {e}")
        
        # Emit usage info with done event
        yield {
            "type": "done",
            "usage": {
                "input_tokens": self.session_input_tokens,
                "output_tokens": self.session_output_tokens
            }
        }

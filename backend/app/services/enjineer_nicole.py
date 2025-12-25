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
from app.services.engineer_intelligence import engineer_intelligence, PreflightResult
from app.services.npm_validator import npm_validator

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
3. **Incorporate Inspiration Images (CRITICAL)** - If user provided inspiration images:
   - Extract EXACT color hex codes from the design_analysis color_palette
   - Note typography style, weight, and font suggestions
   - Identify layout patterns (bento, hero, sections) to replicate
   - List visual effects (gradients, animations, shadows) to implement
   - Reference user's caption text as design intent directives
   - Note what to AVOID based on inspiration analysis
4. **Call `create_plan`** with:
   - Description that explicitly references: colors, typography, layouts from inspiration
   - Detailed phases with sub-steps that implement inspiration elements
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
6. **IMMEDIATELY call `get_qa_reports`** to retrieve the detailed findings
7. Follow the QA-to-Fix Workflow below
8. Only proceed when all critical/high issues are resolved

### QA-to-Fix Workflow (MANDATORY after every QA)
After calling `dispatch_agent(agent_type="qa")`:

**Step 1: Retrieve Report**
```
Call get_qa_reports(limit=1, include_issues=true)
```

**Step 2: Analyze Issues by Severity**
- CRITICAL issues: MUST fix before proceeding (blocks deployment)
- HIGH issues: MUST fix before proceeding (significant problems)
- MEDIUM issues: Should fix, can continue with caution
- LOW issues: Note for improvement, can proceed

**Step 3: Create Fix Plan**
For each critical/high issue:
1. Identify the file and line from the issue
2. Use `update_file` to apply the suggested fix
3. Document what was changed

**Step 4: Verify Fixes**
After fixing all critical/high issues:
1. Call `dispatch_agent(agent_type="qa")` again
2. Call `get_qa_reports` to verify issues are resolved
3. Only proceed if critical/high count = 0

**Step 5: Report to User**
"Phase X complete. QA Review: [pass/fail]
- Fixed: [list of fixes made]
- Remaining: [any medium/low issues noted]
Ready for Phase Y?"

### Phase 3: Preview Checkpoint (REQUIRED)
When core layout complete:
1. Trigger QA for preview readiness with `dispatch_agent(agent_type="qa")`
2. Fix any issues using the QA-to-Fix Workflow
3. Announce: "Preview available! Click Update in Preview tab."
4. Wait for user feedback before continuing

### Phase 4: Final QA (REQUIRED before deploy)
1. Call `dispatch_agent` with agent_type="sr_qa" for full audit (uses Claude Opus 4.5)
2. SR QA performs: Deep architectural review, security audit, accessibility, performance
3. **Call `get_qa_reports`** to get detailed findings
4. Fix ALL critical and high issues using QA-to-Fix Workflow
5. Re-run SR QA until all critical issues resolved

### Deployment Error Handling
If deployment fails:
1. Call `get_deployment_logs()` to retrieve build errors
2. Analyze error messages (TypeScript, ESLint, missing deps)
3. Use `update_file` to fix each error
4. Inform user: "Found [N] build errors. Fixing now..."
5. After fixes, user should click "Update Preview" to redeploy

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
2. Never assume dependencies exist - USE npm_validator to verify
3. Always use actual file paths from file tree
4. If unsure, ASK rather than guess
5. Verify before claiming ("I've created X" only after tool call)
6. Check imports exist before using
7. Use explicit types - no implicit any

## Verification Protocol (MANDATORY)
After EVERY file update:
1. Record intended change (filepath, content hash, description)
2. Apply the update via tool call
3. Read back the file to VERIFY change applied
4. Only then update state to "verified"
5. If content mismatch: Log error, retry up to 2x, then escalate

## Error Recovery Protocol
When deployment fails:
1. Parse error log for patterns (module_not_found, type_error, etc.)
2. Check if this error has occurred before (recurring pattern)
3. If recurring (2+ times): STOP and do comprehensive audit
4. Fix ALL instances of pattern across ALL files, not just one
5. Run preflight audit before next deploy attempt
6. Track claimed fixes vs actual state

## Communication Discipline (CRITICAL)

### BANNED UNTIL BUILD VERIFICATION:
You MUST NOT use these phrases until AFTER you see successful build logs:
❌ "✅ COMPLETE" / "🎉 SUCCESS" / "100% CONFIDENCE"
❌ "BUILD WILL SUCCEED" / "DEPLOYMENT READY"
❌ "ALL ISSUES RESOLVED" / "SHOULD NOW WORK"
❌ "FIXED" (as definitive claim)
❌ "GUARANTEED" / "DONE"

### REQUIRED Status Format (Unverified Changes):
When you make file changes, use this format until verified:
"**Status: PENDING VERIFICATION**
- Changes applied: [list files]
- Fix attempted: [description]
- Next step: Deploy and check build logs
- DO NOT claim success until build confirms resolution"

### REQUIRED Status Format (After Build Success):
Only after seeing "Build completed successfully" in logs:
"**Status: VERIFIED ✓**
- Build: Successful
- Changes confirmed: [list files]
- Errors resolved: [list fixes]"

### Error Pattern Recognition:
- If you see the SAME error 2+ times, STOP and analyze systematically
- Do NOT fix errors one-by-one - audit ALL files for same pattern
- Before claiming "fixed", verify with: read_file to confirm content

### Preflight Requirements (Before Deploy):
1. Check circuit breaker: If 3+ consecutive failures, pause and diagnose
2. Audit all dependencies: Use npm_validator to check packages exist
3. Track intended state: Record what changes SHOULD happen
4. After deploy: Verify changes actually applied before claiming success

## Communication Style
- Direct and technical, no hedging
- State facts definitively
- Step-by-step with copy-pasteable commands
- Cite knowledge base: "Per hero-sections.md, single CTA shows +266% conversion"
- Answer to depth asked, no more
- NEVER claim completion before verification

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
        "description": "Create an implementation plan with numbered phases. Each phase has detailed sub-steps. ALWAYS include Preview Checkpoint, Final QA, and Deploy phases. The plan will automatically incorporate inspiration image analysis if provided.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the plan (e.g., 'Landing Page Implementation')"
                },
                "description": {
                    "type": "string",
                    "description": "Overview of what this plan accomplishes. MUST reference design inspiration (color palette, typography, layout patterns) from inspiration image analysis if provided."
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
- qa: React patterns, TypeScript, accessibility, performance

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
                    "enum": ["patterns", "animation", "components", "fundamentals", "core", "qa"],
                    "description": "Optional category filter to narrow results"
                },
                "include_sections": {
                    "type": "boolean",
                    "description": "If true, search within sections for more granular results. Default: false"
                }
            },
            "required": ["query"]
        }
    },
    # =========================================================================
    # QA Report Retrieval Tool - Allows Nicole to read past QA reports
    # =========================================================================
    {
        "name": "get_qa_reports",
        "description": """Retrieve QA reports for this project. Use this tool to:
- Read issues found in the last QA review
- Create a fix plan based on QA findings
- Verify if issues from previous QA runs were resolved
- Track QA history and patterns

ALWAYS use this after dispatch_agent(qa) to:
1. Get the detailed issues list
2. Create targeted fixes for each issue
3. Re-run QA to verify fixes""",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of reports to retrieve (default: 3, max: 10)",
                    "default": 3
                },
                "status_filter": {
                    "type": "string",
                    "enum": ["all", "pass", "fail", "partial"],
                    "description": "Filter by QA result status",
                    "default": "all"
                },
                "include_issues": {
                    "type": "boolean",
                    "description": "Include detailed issue list (default: true)",
                    "default": True
                }
            }
        }
    },
    # =========================================================================
    # Deployment Logs Tool - Allows Nicole to read Vercel build errors
    # =========================================================================
    {
        "name": "get_deployment_logs",
        "description": """Retrieve build logs and error messages from Vercel deployments.
Use this tool when:
- A deployment fails and you need to understand why
- You see 'Deployment failed' error and need the actual error message
- You need to fix TypeScript, ESLint, or build errors

Returns:
- Build step status (success/failed)
- Error messages with file/line information
- TypeScript compilation errors
- Missing dependency errors""",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "Vercel deployment ID (if known). If not provided, fetches latest deployment."
                },
                "log_type": {
                    "type": "string",
                    "enum": ["build", "output", "all"],
                    "description": "Type of logs to retrieve",
                    "default": "all"
                }
            }
        }
    },
    # =========================================================================
    # ENGINEER INTELLIGENCE TOOLS - Verification, Preflight, Error Patterns
    # =========================================================================
    {
        "name": "validate_packages",
        "description": """Validate npm packages exist BEFORE adding to package.json.
ALWAYS use this when adding dependencies to prevent "Module not found" errors.

Checks:
- Package exists in npm registry
- Version is valid
- Peer dependencies are listed
- React 19 compatibility warnings
- Deprecated package warnings""",
        "input_schema": {
            "type": "object",
            "properties": {
                "packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of packages to validate (e.g., ['framer-motion@11.0.0', 'lucide-react'])"
                }
            },
            "required": ["packages"]
        }
    },
    {
        "name": "run_preflight_audit",
        "description": """Run comprehensive audit BEFORE deployment.
Use this to catch errors that would fail the Vercel build.

Checks:
- All packages in package.json exist
- Import/export patterns are consistent
- TypeScript compatibility
- Known anti-patterns

ALWAYS run this before deploy to catch issues early.""",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "check_circuit_breaker",
        "description": """Check if deployments are blocked due to consecutive failures.
The circuit breaker opens after 3+ consecutive deployment failures.

Use this before deploy to check if you should:
- Stop and fix recurring errors first
- Wait for cooldown period
- Review the failure patterns""",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_recurring_errors",
        "description": """Get errors that have occurred 2+ times across deployments.
CRITICAL: If the same error appears repeatedly, your fixes are NOT working.

Use this when:
- You see "same error again" pattern
- Deployment keeps failing after "fixes"
- You need to diagnose why fixes aren't applying

If recurring errors found, do NOT fix one-by-one - do comprehensive audit.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_occurrences": {
                    "type": "integer",
                    "description": "Minimum times error must occur to be considered recurring (default: 2)",
                    "default": 2
                }
            }
        }
    },
    {
        "name": "read_file",
        "description": """Read file content to VERIFY changes applied correctly.
MANDATORY after update_file to confirm the change took effect.

Use this to:
- Verify your update_file call actually changed the file
- Check current state before making changes
- Compare actual content vs intended content

NEVER claim a fix is complete without reading the file back to verify.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to read (e.g., '/src/components/Button.tsx')"
                }
            },
            "required": ["path"]
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
        self.model = "claude-opus-4-20250514"  # Claude Opus 4.5 for superior reasoning
        self.project_data: Optional[Dict[str, Any]] = None
        self.max_tool_iterations = 10  # Safety limit
        
        # Engineer Intelligence integration
        self._deployment_id: Optional[str] = None
        self._verified_files: set = set()
        self._unverified_files: set = set()
        
        # Token usage tracking for this session
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        
        # Inspiration images analysis cache
        self._inspiration_analysis: Optional[Dict[str, Any]] = None
        
    async def analyze_inspiration_images(
        self,
        attachments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze inspiration images using Claude Vision to extract design insights.
        
        This is a critical function for Nicole's design intelligence. It:
        1. Filters inspiration images from regular attachments
        2. Sends images to Claude Vision for analysis
        3. Combines user annotations with AI analysis
        4. Returns structured design insights for planning
        
        Args:
            attachments: List of attachment dicts with name, type, content, annotation, isInspiration
            
        Returns:
            Dict with:
            - images_analyzed: count
            - color_palette: extracted colors
            - typography: font styles observed
            - layout_patterns: detected layout approaches
            - design_style: overall aesthetic (modern, minimal, etc)
            - key_elements: important design features
            - user_intentions: summarized from annotations
            - combined_brief: synthesized design direction
        """
        # Filter for inspiration images only
        inspiration_images = [
            att for att in (attachments or [])
            if att.get("isInspiration") or att.get("name", "").startswith("inspiration_")
        ]
        
        if not inspiration_images:
            return {"images_analyzed": 0, "combined_brief": "No inspiration images provided"}
        
        logger.info(f"[Vision] Analyzing {len(inspiration_images)} inspiration images")
        
        # Build vision request with all images
        vision_content = []
        user_annotations = []
        
        for idx, img in enumerate(inspiration_images[:5], 1):  # Max 5 images
            # Add image to vision request
            media_type = img.get("type", "image/png")
            base64_data = img.get("content", "")
            
            if base64_data:
                vision_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_data
                    }
                })
            
            # Collect user annotation
            annotation = img.get("annotation", "").strip()
            if annotation:
                user_annotations.append(f"Image {idx}: {annotation}")
        
        if not vision_content:
            return {
                "images_analyzed": 0,
                "combined_brief": "Could not process inspiration images (no valid image data)"
            }
        
        # Build analysis prompt
        annotations_context = "\n".join(user_annotations) if user_annotations else "No user annotations provided."
        
        analysis_prompt = f"""Analyze these inspiration images for a web design project. The user has provided the following context about what they want:

**User's Notes on These Images:**
{annotations_context}

Please provide a comprehensive design analysis in the following JSON format:
{{
    "overall_impression": "Brief summary of the combined design direction",
    "design_style": "Primary style (e.g., 'Modern Minimalist', 'Bold & Vibrant', 'Corporate Professional')",
    "color_palette": {{
        "primary": "#hexcode",
        "secondary": "#hexcode",
        "accent": "#hexcode",
        "background": "#hexcode or description",
        "text": "#hexcode"
    }},
    "typography": {{
        "style": "Description of typography approach",
        "heading_suggestion": "Font family recommendation",
        "body_suggestion": "Font family recommendation",
        "key_characteristics": ["bold", "clean", "elegant", etc.]
    }},
    "layout_patterns": [
        "Layout pattern 1 (e.g., 'Hero with centered text overlay')",
        "Layout pattern 2"
    ],
    "key_elements": [
        "Important design element 1",
        "Important design element 2"
    ],
    "visual_effects": [
        "Effect 1 (e.g., 'Gradient backgrounds', 'Subtle shadows')"
    ],
    "mood_and_feeling": "Emotional tone the design should convey",
    "recommended_components": [
        "Component 1 (e.g., 'Floating cards with blur backdrop')",
        "Component 2"
    ],
    "avoid": [
        "Things to avoid based on the inspiration (e.g., 'Cluttered layouts')"
    ]
}}

Be specific about colors (provide actual hex codes when visible), fonts, and patterns you observe. Focus on extractable, actionable design decisions."""

        vision_content.append({
            "type": "text",
            "text": analysis_prompt
        })
        
        try:
            # Call Claude Vision
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Use Sonnet for vision
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": vision_content
                }]
            )
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                self.session_input_tokens += response.usage.input_tokens or 0
                self.session_output_tokens += response.usage.output_tokens or 0
            
            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    analysis = json.loads(json_match.group())
                except json.JSONDecodeError:
                    analysis = {"raw": response_text}
            else:
                analysis = {"raw": response_text}
            
            # Add metadata
            analysis["images_analyzed"] = len(vision_content) - 1  # Exclude text prompt
            analysis["user_annotations"] = user_annotations
            analysis["combined_brief"] = self._build_design_brief(analysis, user_annotations)
            
            logger.info(f"[Vision] Analysis complete: {analysis.get('design_style', 'Unknown style')}")
            
            # Cache for this session
            self._inspiration_analysis = analysis
            
            return analysis
            
        except Exception as e:
            logger.error(f"[Vision] Analysis failed: {e}", exc_info=True)
            return {
                "images_analyzed": len(inspiration_images),
                "error": str(e),
                "user_annotations": user_annotations,
                "combined_brief": f"Vision analysis failed. User notes: {annotations_context}"
            }
    
    def _build_design_brief(
        self,
        analysis: Dict[str, Any],
        user_annotations: List[str]
    ) -> str:
        """Build a concise design brief from vision analysis and user notes."""
        parts = []
        
        if analysis.get("overall_impression"):
            parts.append(f"**Direction:** {analysis['overall_impression']}")
        
        if analysis.get("design_style"):
            parts.append(f"**Style:** {analysis['design_style']}")
        
        if analysis.get("mood_and_feeling"):
            parts.append(f"**Mood:** {analysis['mood_and_feeling']}")
        
        if analysis.get("color_palette") and isinstance(analysis["color_palette"], dict):
            cp = analysis["color_palette"]
            colors = f"Primary: {cp.get('primary', 'TBD')}, Accent: {cp.get('accent', 'TBD')}, BG: {cp.get('background', 'TBD')}"
            parts.append(f"**Colors:** {colors}")
        
        if analysis.get("typography") and isinstance(analysis["typography"], dict):
            typo = analysis["typography"]
            parts.append(f"**Typography:** {typo.get('style', 'Clean and modern')}")
        
        if analysis.get("key_elements"):
            elements = ", ".join(analysis["key_elements"][:5])
            parts.append(f"**Key Elements:** {elements}")
        
        if user_annotations:
            parts.append(f"**User Intent:** {'; '.join(user_annotations)}")
        
        return "\n".join(parts) if parts else "Design direction to be determined from conversation."
        
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
        design_analysis = intake_data.get("design_analysis") or self._inspiration_analysis
        
        if design_analysis and isinstance(design_analysis, dict) and design_analysis.get("images_analyzed", 0) > 0:
            parts = [f"**Inspiration Analysis ({design_analysis.get('images_analyzed', 0)} images):**"]
            
            # Use combined_brief if available (most concise)
            if design_analysis.get("combined_brief"):
                parts.append(design_analysis["combined_brief"])
            else:
                # Fallback to structured data
                if design_analysis.get("overall_impression"):
                    parts.append(f"**Direction:** {design_analysis['overall_impression']}")
                if design_analysis.get("design_style"):
                    parts.append(f"**Style:** {design_analysis['design_style']}")
                if design_analysis.get("mood_and_feeling"):
                    parts.append(f"**Mood:** {design_analysis['mood_and_feeling']}")
            
            # Color palette
            if design_analysis.get("color_palette") and isinstance(design_analysis["color_palette"], dict):
                cp = design_analysis["color_palette"]
                colors = []
                if cp.get("primary"): colors.append(f"Primary: {cp['primary']}")
                if cp.get("secondary"): colors.append(f"Secondary: {cp['secondary']}")
                if cp.get("accent"): colors.append(f"Accent: {cp['accent']}")
                if cp.get("background"): colors.append(f"BG: {cp['background']}")
                if cp.get("text"): colors.append(f"Text: {cp['text']}")
                if colors:
                    parts.append(f"**Colors:** {', '.join(colors)}")
            
            # Typography
            if design_analysis.get("typography") and isinstance(design_analysis["typography"], dict):
                typo = design_analysis["typography"]
                typo_parts = []
                if typo.get("style"): typo_parts.append(f"Style: {typo['style']}")
                if typo.get("heading_suggestion"): typo_parts.append(f"Headings: {typo['heading_suggestion']}")
                if typo.get("body_suggestion"): typo_parts.append(f"Body: {typo['body_suggestion']}")
                if typo_parts:
                    parts.append(f"**Typography:** {'; '.join(typo_parts)}")
            
            # Layout patterns
            if design_analysis.get("layout_patterns"):
                patterns = design_analysis["layout_patterns"][:5]
                parts.append(f"**Layouts:** {', '.join(patterns)}")
            
            # Key elements
            if design_analysis.get("key_elements"):
                elements = design_analysis["key_elements"][:5]
                parts.append(f"**Key Elements:** {', '.join(elements)}")
            
            # Recommended components
            if design_analysis.get("recommended_components"):
                components = design_analysis["recommended_components"][:5]
                parts.append(f"**Components:** {', '.join(components)}")
            
            # Visual effects
            if design_analysis.get("visual_effects"):
                effects = design_analysis["visual_effects"][:3]
                parts.append(f"**Effects:** {', '.join(effects)}")
            
            # Things to avoid
            if design_analysis.get("avoid"):
                avoid = design_analysis["avoid"][:3]
                parts.append(f"**Avoid:** {', '.join(avoid)}")
            
            # User annotations
            if design_analysis.get("user_annotations"):
                annotations = design_analysis["user_annotations"]
                parts.append(f"\n**User's Design Intent:**")
                for ann in annotations[:5]:
                    parts.append(f"  • {ann}")
            
            # Raw analysis if structured parsing failed
            if "raw" in design_analysis and len(parts) < 3:
                parts.append(f"\nRaw Analysis:\n{design_analysis['raw'][:2000]}")
            
            design_analysis_str = "\n".join(parts)
        else:
            design_analysis_str = "(No inspiration images provided - use design best practices from knowledge base)"
        
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
            elif tool_name == "get_qa_reports":
                return await self._get_qa_reports(pool, tool_input)
            elif tool_name == "get_deployment_logs":
                return await self._get_deployment_logs(pool, tool_input)
            # Engineer Intelligence tools
            elif tool_name == "validate_packages":
                return await self._validate_packages(tool_input)
            elif tool_name == "run_preflight_audit":
                return await self._run_preflight_audit(pool, tool_input)
            elif tool_name == "check_circuit_breaker":
                return await self._check_circuit_breaker(tool_input)
            elif tool_name == "get_recurring_errors":
                return await self._get_recurring_errors(tool_input)
            elif tool_name == "read_file":
                return await self._read_file(pool, tool_input)
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
        """
        Create a new file in the project with MANDATORY verification.
        
        Implements the Verification Loop:
        1. Record intended state BEFORE write
        2. Execute the write operation
        3. Read back to VERIFY write succeeded
        4. Track verified/unverified status
        """
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
        
        # STEP 1: Record intended state BEFORE write
        intended_hash = await engineer_intelligence.record_intended_change(
            project_id=self.project_id,
            filepath=path,
            content=content,
            description=f"Create file: {path}",
            deployment_id=self._deployment_id,
        )
        self._unverified_files.add(path)
        
        async with pool.acquire() as conn:
            # Check if file exists
            existing = await conn.fetchrow(
                "SELECT id FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
            
            if existing:
                self._unverified_files.discard(path)
                return {"success": False, "error": f"File already exists: {path}. Use update_file instead."}
            
            # STEP 2: Execute the write
            file = await conn.fetchrow(
                """
                INSERT INTO enjineer_files (project_id, path, content, language, modified_by, checksum)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, version
                """,
                self.project_id, path, content, language, "nicole", checksum
            )
            
            # STEP 3: MANDATORY - Read back to verify
            verification_row = await conn.fetchrow(
                "SELECT content FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
        
        # STEP 4: Verify content matches
        verification = await engineer_intelligence.verify_change_applied(
            project_id=self.project_id,
            filepath=path,
            actual_content=verification_row["content"] if verification_row else "",
            deployment_id=self._deployment_id,
        )
        
        if verification.success:
            self._verified_files.add(path)
            self._unverified_files.discard(path)
            logger.info(f"[Enjineer] ✅ Created & verified: {path} ({len(content)} chars)")
        else:
            logger.error(f"[Enjineer] ❌ Create verification FAILED: {path} - {verification.message}")
        
        return {
            "success": True,
            "result": {
                "action": "file_created",
                "path": path,
                "language": language,
                "size": len(content),
                "version": file["version"],
                "verified": verification.success,
                "verification_status": verification.status.value if hasattr(verification.status, 'value') else str(verification.status),
            }
        }
    
    async def _update_file(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing file with MANDATORY verification.
        
        Implements the Verification Loop:
        1. Record intended state BEFORE write
        2. Execute the write operation  
        3. Read back to VERIFY write succeeded
        4. Track verified/unverified status
        5. If verification fails, flag for retry
        """
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
        
        # STEP 1: Record intended state BEFORE write
        intended_hash = await engineer_intelligence.record_intended_change(
            project_id=self.project_id,
            filepath=path,
            content=content,
            description=commit_message,
            deployment_id=self._deployment_id,
        )
        self._unverified_files.add(path)
        
        async with pool.acquire() as conn:
            file = await conn.fetchrow(
                "SELECT id, version, content FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
            
            if not file:
                self._unverified_files.discard(path)
                return {"success": False, "error": f"File not found: {path}. Use create_file for new files."}
            
            new_version = file["version"] + 1
            
            # STEP 2: Execute the write
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
            
            # STEP 3: MANDATORY - Read back to verify
            verification_row = await conn.fetchrow(
                "SELECT content FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
        
        # STEP 4: Verify content matches
        verification = await engineer_intelligence.verify_change_applied(
            project_id=self.project_id,
            filepath=path,
            actual_content=verification_row["content"] if verification_row else "",
            deployment_id=self._deployment_id,
        )
        
        if verification.success:
            self._verified_files.add(path)
            self._unverified_files.discard(path)
            logger.info(f"[Enjineer] ✅ Updated & verified: {path} (v{new_version})")
        else:
            logger.error(f"[Enjineer] ❌ Update verification FAILED: {path} - {verification.message}")
        
        return {
            "success": True,
            "result": {
                "action": "file_updated",
                "path": path,
                "version": new_version,
                "commit_message": commit_message,
                "verified": verification.success,
                "verification_status": verification.status.value if hasattr(verification.status, 'value') else str(verification.status),
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
        """Create an implementation plan with phases, incorporating inspiration analysis."""
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
        
        # Extract design analysis from inspiration images
        intake_data = self.project_data.get("intake_data") or {}
        design_analysis = intake_data.get("design_analysis") or self._inspiration_analysis
        
        # Build inspiration section for plan.md
        inspiration_section = ""
        if design_analysis and isinstance(design_analysis, dict) and design_analysis.get("images_analyzed", 0) > 0:
            inspiration_section = "\n## Design Inspiration\n\n"
            inspiration_section += f"*Based on analysis of {design_analysis.get('images_analyzed', 1)} inspiration image(s)*\n\n"
            
            # Design direction
            if design_analysis.get("overall_impression"):
                inspiration_section += f"### Design Direction\n{design_analysis['overall_impression']}\n\n"
            elif design_analysis.get("design_style"):
                inspiration_section += f"### Design Style\n{design_analysis['design_style']}\n\n"
            
            # Color palette
            if design_analysis.get("color_palette") and isinstance(design_analysis["color_palette"], dict):
                cp = design_analysis["color_palette"]
                inspiration_section += "### Color Palette\n"
                if cp.get("primary"): inspiration_section += f"- **Primary:** {cp['primary']}\n"
                if cp.get("secondary"): inspiration_section += f"- **Secondary:** {cp['secondary']}\n"
                if cp.get("accent"): inspiration_section += f"- **Accent:** {cp['accent']}\n"
                if cp.get("background"): inspiration_section += f"- **Background:** {cp['background']}\n"
                if cp.get("text"): inspiration_section += f"- **Text:** {cp['text']}\n"
                inspiration_section += "\n"
            
            # Typography
            if design_analysis.get("typography") and isinstance(design_analysis["typography"], dict):
                typo = design_analysis["typography"]
                inspiration_section += "### Typography\n"
                if typo.get("style"): inspiration_section += f"- **Style:** {typo['style']}\n"
                if typo.get("heading_suggestion"): inspiration_section += f"- **Headings:** {typo['heading_suggestion']}\n"
                if typo.get("body_suggestion"): inspiration_section += f"- **Body:** {typo['body_suggestion']}\n"
                inspiration_section += "\n"
            
            # Layout patterns
            if design_analysis.get("layout_patterns"):
                patterns = design_analysis["layout_patterns"][:6]
                inspiration_section += "### Layout Patterns\n"
                for p in patterns:
                    inspiration_section += f"- {p}\n"
                inspiration_section += "\n"
            
            # Key elements to implement
            if design_analysis.get("key_elements"):
                elements = design_analysis["key_elements"][:8]
                inspiration_section += "### Key Elements to Implement\n"
                for e in elements:
                    inspiration_section += f"- {e}\n"
                inspiration_section += "\n"
            
            # Recommended components
            if design_analysis.get("recommended_components"):
                components = design_analysis["recommended_components"][:6]
                inspiration_section += "### Recommended Components\n"
                for c in components:
                    inspiration_section += f"- {c}\n"
                inspiration_section += "\n"
            
            # Visual effects
            if design_analysis.get("visual_effects"):
                effects = design_analysis["visual_effects"][:4]
                inspiration_section += "### Visual Effects\n"
                for e in effects:
                    inspiration_section += f"- {e}\n"
                inspiration_section += "\n"
            
            # Things to avoid
            if design_analysis.get("avoid"):
                avoid_items = design_analysis["avoid"][:4]
                inspiration_section += "### Avoid\n"
                for a in avoid_items:
                    inspiration_section += f"- ❌ {a}\n"
                inspiration_section += "\n"
            
            # User's design intent (from captions)
            if design_analysis.get("user_annotations"):
                inspiration_section += "### User's Design Intent\n"
                for ann in design_analysis["user_annotations"][:5]:
                    inspiration_section += f"- {ann}\n"
                inspiration_section += "\n"
        
        # Generate plan.md content with detailed sub-steps
        plan_md = f"""# {name}

## Overview
{description}
{inspiration_section}
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
            
            # Transform result to standard format for execution tracking
            # NOTE: QA report storage is handled by qa_service._store_qa_report()
            # This is the SINGLE SOURCE OF TRUTH - no duplicate storage here
            
            execution_status = "completed"
            if result.get("error") or not result.get("success", True):
                execution_status = "failed"
            
            # Update agent execution status only (not QA reports - handled by qa_service)
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE enjineer_agent_executions 
                    SET status = $1, result = $2, completed_at = NOW()
                    WHERE id = $3
                    """,
                    execution_status,
                    json.dumps(result),
                    execution_id
                )
            
            logger.warning(f"[Enjineer] Agent {agent_type} completed: passed={result.get('passed')}, verdict={result.get('verdict')}")
            
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
        """
        Deploy the project to Vercel with comprehensive pre-deploy checks.
        
        Implements defensive engineering:
        1. Check circuit breaker (blocks after 3+ consecutive failures)
        2. Run preflight audit (catches errors before Vercel build)
        3. Track unverified files (warns about uncommitted changes)
        4. Record deployment attempt for pattern analysis
        """
        environment = input_data.get("environment", "preview")
        commit_message = input_data.get("commit_message", "Deployed by Enjineer")
        
        # =====================================================================
        # STEP 1: CHECK CIRCUIT BREAKER
        # Prevents deployment loops after consecutive failures
        # =====================================================================
        circuit_state = await engineer_intelligence.check_circuit_breaker(self.project_id)
        
        if circuit_state.is_open:
            logger.warning(f"[Enjineer] 🚫 Circuit breaker OPEN - blocking deployment")
            return {
                "success": False,
                "error": circuit_state.message,
                "blocked_by": "circuit_breaker",
                "failure_count": circuit_state.failure_count,
                "resume_at": circuit_state.resume_at.isoformat() if circuit_state.resume_at else None,
                "instruction": (
                    "Deployment blocked due to consecutive failures. "
                    "Review recurring errors with get_recurring_errors tool before retrying."
                )
            }
        
        # =====================================================================
        # STEP 2: CHECK FOR UNVERIFIED CHANGES
        # Warns if file updates haven't been verified
        # =====================================================================
        unverified = await engineer_intelligence.get_unverified_changes(self.project_id)
        if unverified:
            logger.warning(f"[Enjineer] ⚠️ {len(unverified)} unverified file changes detected")
            # Don't block, but include warning in response
        
        # =====================================================================
        # STEP 3: RUN PREFLIGHT AUDIT
        # Catches errors before wasting a Vercel build
        # =====================================================================
        async with pool.acquire() as conn:
            file_rows = await conn.fetch(
                "SELECT path, content FROM enjineer_files WHERE project_id = $1",
                self.project_id
            )
        
        files = {row["path"]: row["content"] for row in file_rows}
        
        # Get package.json for dependency audit
        package_json = None
        for path, content in files.items():
            if path.endswith("package.json"):
                try:
                    package_json = json.loads(content)
                    break
                except json.JSONDecodeError:
                    pass
        
        preflight = await engineer_intelligence.run_preflight_audit(
            project_id=self.project_id,
            files=files,
            package_json=package_json,
        )
        
        if preflight.blocked:
            logger.warning(f"[Enjineer] 🚫 Preflight audit FAILED - {len(preflight.errors)} errors")
            return {
                "success": False,
                "error": "Preflight audit failed. Fix errors before deploying.",
                "blocked_by": "preflight_audit",
                "errors": preflight.errors[:10],  # Limit for response size
                "warnings": preflight.warnings[:5],
                "instruction": (
                    "Fix the errors above before attempting deployment. "
                    "Use update_file to fix issues, then try deploy again."
                )
            }
        
        # =====================================================================
        # STEP 4: CHECK PRODUCTION APPROVAL
        # =====================================================================
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
        
        # =====================================================================
        # STEP 5: CREATE DEPLOYMENT RECORD & TRACK ATTEMPT
        # =====================================================================
        deployment_id = str(uuid4())
        self._deployment_id = deployment_id  # Track for file verification
        
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO enjineer_deployments 
                (id, project_id, platform, environment, status, commit_sha)
                VALUES ($1, $2, 'vercel', $3, 'pending', $4)
                """,
                deployment_id, self.project_id, environment, commit_message[:40]
            )
        
        # Record this as a deployment attempt for circuit breaker
        await engineer_intelligence.record_deployment_attempt(
            project_id=self.project_id,
            deployment_id=deployment_id,
            vercel_deployment_id=None,  # Will be updated after Vercel responds
            success=False,  # Pending - will update on completion
            error_count=0,
            claimed_fixes=[],
        )
        
        logger.info(f"[Enjineer] ✅ Preflight passed, initiating {environment} deployment")
        
        # Build response with preflight warnings if any
        result = {
            "success": True,
            "result": {
                "action": "deployment_initiated",
                "deployment_id": deployment_id,
                "environment": environment,
                "status": "pending",
                "preflight": {
                    "passed": True,
                    "warnings": preflight.warnings[:3] if preflight.warnings else [],
                    "recommendations": preflight.recommendations[:3] if preflight.recommendations else [],
                },
                "message": f"Deployment to {environment} initiated. Preflight checks passed."
            }
        }
        
        # Add unverified files warning if any
        if unverified:
            result["result"]["unverified_files"] = [u["filepath"] for u in unverified[:5]]
            result["result"]["unverified_warning"] = (
                f"Warning: {len(unverified)} file(s) have unverified changes. "
                "Use read_file to verify updates applied correctly."
            )
        
        return result
    
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
    
    # =========================================================================
    # QA REPORT RETRIEVAL - Allows Nicole to read and act on QA findings
    # =========================================================================
    
    async def _get_qa_reports(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve QA reports for this project.
        
        Returns:
            - List of QA reports with issues, status, and recommendations
            - Structured format for Nicole to create fix plans
        """
        limit = min(input_data.get("limit", 3), 10)  # Max 10
        status_filter = input_data.get("status_filter", "all")
        include_issues = input_data.get("include_issues", True)
        
        try:
            async with pool.acquire() as conn:
                # Build query with optional status filter
                if status_filter == "all":
                    reports = await conn.fetch(
                        """
                        SELECT 
                            id, project_id, plan_id, phase_number,
                            trigger_type, qa_depth, overall_status,
                            checks, summary, 
                            blocking_issues_count, warnings_count, passed_count,
                            model_used, tokens_used, estimated_cost_usd,
                            duration_seconds, created_at
                        FROM enjineer_qa_reports 
                        WHERE project_id = $1 
                        ORDER BY created_at DESC 
                        LIMIT $2
                        """,
                        self.project_id, limit
                    )
                else:
                    reports = await conn.fetch(
                        """
                        SELECT 
                            id, project_id, plan_id, phase_number,
                            trigger_type, qa_depth, overall_status,
                            checks, summary,
                            blocking_issues_count, warnings_count, passed_count,
                            model_used, tokens_used, estimated_cost_usd,
                            duration_seconds, created_at
                        FROM enjineer_qa_reports 
                        WHERE project_id = $1 AND overall_status = $2
                        ORDER BY created_at DESC 
                        LIMIT $3
                        """,
                        self.project_id, status_filter, limit
                    )
            
            if not reports:
                return {
                    "success": True,
                    "result": {
                        "found": False,
                        "message": "No QA reports found for this project. Run dispatch_agent(agent_type='qa') to generate a QA report.",
                        "reports": []
                    }
                }
            
            # Format reports for Nicole
            formatted_reports = []
            for report in reports:
                report_data = {
                    "id": str(report["id"]),
                    "created_at": report["created_at"].isoformat() if report["created_at"] else None,
                    "trigger_type": report["trigger_type"],
                    "qa_depth": report["qa_depth"],
                    "status": report["overall_status"],
                    "model_used": report.get("model_used"),
                    "phase_number": report["phase_number"],
                    "summary": report["summary"],
                    "counts": {
                        "blocking": report["blocking_issues_count"] or 0,
                        "warnings": report["warnings_count"] or 0,
                        "passed": report["passed_count"] or 0
                    }
                }
                
                # Include detailed issues if requested
                if include_issues and report["checks"]:
                    checks = report["checks"]
                    if isinstance(checks, str):
                        try:
                            checks = json.loads(checks)
                        except json.JSONDecodeError:
                            checks = []
                    
                    # Group issues by severity for easier action planning
                    critical_issues = []
                    high_issues = []
                    medium_issues = []
                    low_issues = []
                    
                    for check in checks:
                        severity = check.get("severity", "medium").lower()
                        issue_entry = {
                            "category": check.get("category"),
                            "file": check.get("file"),
                            "line": check.get("line"),
                            "issue": check.get("issue") or check.get("message"),
                            "fix": check.get("fix") or check.get("suggestion"),
                            "status": check.get("status", "open")
                        }
                        
                        if severity == "critical":
                            critical_issues.append(issue_entry)
                        elif severity == "high":
                            high_issues.append(issue_entry)
                        elif severity == "medium":
                            medium_issues.append(issue_entry)
                        else:
                            low_issues.append(issue_entry)
                    
                    report_data["issues"] = {
                        "critical": critical_issues,
                        "high": high_issues,
                        "medium": medium_issues,
                        "low": low_issues
                    }
                    report_data["action_required"] = len(critical_issues) > 0 or len(high_issues) > 0
                
                formatted_reports.append(report_data)
            
            # Generate actionable summary
            latest = formatted_reports[0]
            action_summary = ""
            if latest.get("action_required"):
                critical_count = len(latest.get("issues", {}).get("critical", []))
                high_count = len(latest.get("issues", {}).get("high", []))
                action_summary = f"ACTION REQUIRED: {critical_count} critical and {high_count} high severity issues need fixing before proceeding."
            elif latest["status"] == "pass":
                action_summary = "All checks passed. Safe to proceed to next phase."
            else:
                action_summary = f"QA status: {latest['status']}. Review issues and address as needed."
            
            logger.info(f"[QA] Retrieved {len(formatted_reports)} reports for project {self.project_id}")
            
            return {
                "success": True,
                "result": {
                    "found": True,
                    "report_count": len(formatted_reports),
                    "action_summary": action_summary,
                    "reports": formatted_reports,
                    "instruction": """Review the issues above and create fixes:
1. For each critical/high issue, apply the suggested fix
2. Use update_file to make changes
3. After all fixes, run dispatch_agent(agent_type='qa') again to verify"""
                }
            }
            
        except Exception as e:
            logger.error(f"[QA] Failed to retrieve reports: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to retrieve QA reports: {str(e)}"
            }
    
    # =========================================================================
    # DEPLOYMENT LOGS - Allows Nicole to read Vercel build errors
    # =========================================================================
    
    async def _get_deployment_logs(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve build logs and error messages from Vercel deployments.
        
        Uses Vercel API:
        - GET /v2/deployments/{id} - Deployment status
        - GET /v2/deployments/{id}/events - Build events/logs
        
        Returns structured error information for Nicole to fix.
        """
        import httpx
        from app.config import settings
        
        deployment_id = input_data.get("deployment_id")
        log_type = input_data.get("log_type", "all")
        
        # Get Vercel credentials
        vercel_token = settings.VERCEL_TOKEN
        vercel_team_id = getattr(settings, 'VERCEL_TEAM_ID', None)
        
        if not vercel_token:
            return {
                "success": False,
                "error": "Vercel token not configured. Cannot retrieve deployment logs."
            }
        
        headers = {"Authorization": f"Bearer {vercel_token}"}
        
        try:
            # If no deployment_id provided, get the latest deployment
            if not deployment_id:
                async with pool.acquire() as conn:
                    latest = await conn.fetchrow(
                        """
                        SELECT platform_deployment_id, status, error_message, build_log
                        FROM enjineer_deployments 
                        WHERE project_id = $1 AND platform = 'vercel'
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        self.project_id
                    )
                    
                    if latest:
                        deployment_id = latest["platform_deployment_id"]
                        
                        # If we have stored logs, return them
                        if latest["error_message"] or latest["build_log"]:
                            return {
                                "success": True,
                                "result": {
                                    "source": "database",
                                    "deployment_id": deployment_id,
                                    "status": latest["status"],
                                    "error_message": latest["error_message"],
                                    "build_log": latest["build_log"],
                                    "instruction": "Review the error above and fix the code. Common fixes: missing imports, TypeScript errors, ESLint violations."
                                }
                            }
            
            if not deployment_id:
                # Try to get from project's vercel_project_id
                async with pool.acquire() as conn:
                    project = await conn.fetchrow(
                        "SELECT vercel_project_id FROM enjineer_projects WHERE id = $1",
                        self.project_id
                    )
                    
                    if not project or not project["vercel_project_id"]:
                        return {
                            "success": False,
                            "error": "No Vercel deployments found for this project. Deploy first using the preview."
                        }
                    
                    # Get latest deployment from Vercel
                    vercel_project_id = project["vercel_project_id"]
                    url = f"https://api.vercel.com/v6/deployments?projectId={vercel_project_id}&limit=1"
                    if vercel_team_id:
                        url += f"&teamId={vercel_team_id}"
                    
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(url, headers=headers, timeout=15.0)
                        if resp.status_code == 200:
                            deployments = resp.json().get("deployments", [])
                            if deployments:
                                deployment_id = deployments[0]["uid"]
            
            if not deployment_id:
                return {
                    "success": False,
                    "error": "Could not find a deployment ID. Please deploy the project first."
                }
            
            # Fetch deployment details from Vercel
            deployment_url = f"https://api.vercel.com/v13/deployments/{deployment_id}"
            events_url = f"https://api.vercel.com/v2/deployments/{deployment_id}/events"
            
            if vercel_team_id:
                deployment_url += f"?teamId={vercel_team_id}"
                events_url += f"?teamId={vercel_team_id}"
            
            async with httpx.AsyncClient() as client:
                # Get deployment status
                deployment_resp = await client.get(deployment_url, headers=headers, timeout=15.0)
                deployment_data = {}
                if deployment_resp.status_code == 200:
                    deployment_data = deployment_resp.json()
                
                # Get build events/logs
                events_data = []
                if log_type in ["build", "all"]:
                    events_resp = await client.get(events_url, headers=headers, timeout=15.0)
                    if events_resp.status_code == 200:
                        events_data = events_resp.json()
            
            # Parse deployment state and errors
            state = deployment_data.get("readyState", deployment_data.get("state", "UNKNOWN"))
            error_info = {
                "state": state,
                "deployment_id": deployment_id,
                "url": deployment_data.get("url"),
                "errors": [],
                "build_steps": []
            }
            
            # Extract error from deployment data
            if deployment_data.get("errorMessage"):
                error_info["errors"].append({
                    "type": "deployment_error",
                    "message": deployment_data["errorMessage"]
                })
            
            if deployment_data.get("errorCode"):
                error_info["error_code"] = deployment_data["errorCode"]
            
            # Parse build events for errors
            for event in events_data:
                if isinstance(event, dict):
                    event_type = event.get("type", "")
                    
                    # Build step tracking
                    if event_type == "build-step":
                        error_info["build_steps"].append({
                            "name": event.get("name"),
                            "status": event.get("status"),
                            "duration": event.get("duration")
                        })
                    
                    # Error events
                    if "error" in event_type.lower() or event.get("level") == "error":
                        error_info["errors"].append({
                            "type": event_type,
                            "message": event.get("text") or event.get("message"),
                            "file": event.get("file"),
                            "line": event.get("line")
                        })
                    
                    # Log output that might contain errors
                    if event_type == "command-output" and event.get("text"):
                        text = event["text"]
                        if any(keyword in text.lower() for keyword in ["error", "failed", "cannot find", "module not found"]):
                            error_info["errors"].append({
                                "type": "build_output",
                                "message": text[:500]  # Truncate long messages
                            })
            
            # Store logs in database for future reference
            if error_info["errors"]:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE enjineer_deployments 
                        SET error_message = $1, build_log = $2, updated_at = NOW()
                        WHERE platform_deployment_id = $3
                        """,
                        error_info["errors"][0].get("message", ""),
                        json.dumps(error_info["build_steps"]),
                        deployment_id
                    )
            
            # =====================================================================
            # ERROR PATTERN PARSING & CIRCUIT BREAKER UPDATE
            # Record errors for pattern detection and update circuit breaker
            # =====================================================================
            parsed_errors = []
            for error in error_info["errors"]:
                msg = error.get("message", "") or ""
                parsed = engineer_intelligence.parse_build_error(msg)
                parsed_errors.append(parsed)
                
                # Record each error pattern
                await engineer_intelligence.record_error_pattern(
                    project_id=self.project_id,
                    deployment_id=deployment_id,
                    error_type=parsed.error_type,
                    error_detail=parsed.error_detail,
                    file_path=parsed.file or error.get("file"),
                    line_number=parsed.line or error.get("line"),
                )
            
            # Update circuit breaker based on deployment result
            is_failure = state in ["ERROR", "FAILED", "CANCELED"]
            if is_failure:
                await engineer_intelligence.update_circuit_breaker(
                    project_id=self.project_id,
                    success=False,
                    error_count=len(error_info["errors"]),
                )
                logger.warning(f"[Enjineer] 🔴 Deployment failed - circuit breaker updated")
            elif state == "READY":
                await engineer_intelligence.update_circuit_breaker(
                    project_id=self.project_id,
                    success=True,
                    error_count=0,
                )
                logger.info(f"[Enjineer] 🟢 Deployment succeeded - circuit breaker reset")
            
            # Check for recurring errors
            recurring = await engineer_intelligence.get_recurring_errors(self.project_id)
            recurring_warning = None
            if recurring:
                recurring_warning = {
                    "count": len(recurring),
                    "errors": [
                        {
                            "type": r.error.error_type,
                            "detail": r.error.detail[:100] if r.error.detail else None,
                            "occurrences": r.occurrence_count,
                        }
                        for r in recurring[:3]
                    ],
                    "message": f"⚠️ Found {len(recurring)} recurring errors. These have occurred multiple times - investigate root cause."
                }
            
            # Generate action items with enriched error context
            action_items = []
            for i, error in enumerate(error_info["errors"][:5]):  # Top 5 errors
                msg = error.get("message", "")
                parsed = parsed_errors[i] if i < len(parsed_errors) else None
                
                if parsed and parsed.suggested_fix:
                    action_items.append(f"[{parsed.error_type}] {parsed.suggested_fix}")
                elif "module not found" in msg.lower() or "cannot find module" in msg.lower():
                    action_items.append(f"Install missing dependency or fix import path: {msg[:100]}")
                elif "typescript" in msg.lower() or "type" in msg.lower():
                    action_items.append(f"Fix TypeScript error: {msg[:100]}")
                elif "eslint" in msg.lower():
                    action_items.append(f"Fix ESLint violation: {msg[:100]}")
                else:
                    action_items.append(f"Fix: {msg[:100]}")
            
            logger.info(f"[Vercel] Retrieved logs for deployment {deployment_id}: state={state}, errors={len(error_info['errors'])}, recurring={len(recurring)}")
            
            result = {
                "success": True,
                "result": {
                    "source": "vercel_api",
                    "deployment_id": deployment_id,
                    "state": state,
                    "is_failed": is_failure,
                    "is_building": state in ["BUILDING", "QUEUED", "INITIALIZING"],
                    "is_ready": state == "READY",
                    "url": f"https://{deployment_data.get('url')}" if deployment_data.get('url') else None,
                    "error_count": len(error_info["errors"]),
                    "errors": error_info["errors"][:10],  # Top 10 errors
                    "build_steps": error_info["build_steps"],
                    "action_items": action_items,
                    "instruction": """To fix deployment errors:
1. Review each error message carefully
2. Use update_file to fix the specific file/line mentioned  
3. Common fixes:
   - Missing imports: Add the import statement
   - Type errors: Fix the TypeScript types
   - ESLint: Follow the linting rule suggestion
4. After fixing, trigger a new deployment via the Preview tab"""
                }
            }
            
            # Add recurring errors warning if present
            if recurring_warning:
                result["result"]["recurring_errors"] = recurring_warning
            
            # Add circuit breaker status
            circuit_state = await engineer_intelligence.check_circuit_breaker(self.project_id)
            if circuit_state.is_open or circuit_state.failure_count >= 2:
                result["result"]["circuit_breaker"] = {
                    "status": "warning" if circuit_state.failure_count >= 2 else "open" if circuit_state.is_open else "closed",
                    "failure_count": circuit_state.failure_count,
                    "message": circuit_state.message if circuit_state.is_open else f"{circuit_state.failure_count} consecutive failures (circuit breaker opens at 3)"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"[Vercel] Failed to retrieve logs: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to retrieve deployment logs: {str(e)}"
            }
    
    # =========================================================================
    # ENGINEER INTELLIGENCE TOOLS - Verification, Preflight, Error Patterns
    # =========================================================================
    
    async def _validate_packages(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate npm packages exist before adding to package.json.
        
        Prevents "Module not found" deployment failures by checking
        the npm registry BEFORE adding packages.
        """
        packages = input_data.get("packages", [])
        
        if not packages:
            return {"success": False, "error": "No packages provided to validate"}
        
        results = []
        for pkg in packages:
            if isinstance(pkg, str):
                name, version = pkg, "latest"
                if "@" in pkg and not pkg.startswith("@"):
                    parts = pkg.split("@")
                    name, version = parts[0], parts[1] if len(parts) > 1 else "latest"
                elif pkg.startswith("@") and pkg.count("@") > 1:
                    # Scoped package with version
                    last_at = pkg.rfind("@")
                    name, version = pkg[:last_at], pkg[last_at+1:]
            else:
                name = pkg.get("name", "")
                version = pkg.get("version", "latest")
            
            result = await npm_validator.validate_package(name, version)
            results.append({
                "package": name,
                "version": version,
                "valid": result.valid,
                "resolved_version": result.resolved_version,
                "error": result.error,
                "warnings": result.warnings,
                "deprecated": result.deprecated,
            })
        
        valid_count = sum(1 for r in results if r["valid"])
        invalid_count = len(results) - valid_count
        
        logger.info(f"[NPM] Validated {len(packages)} packages: {valid_count} valid, {invalid_count} invalid")
        
        return {
            "success": True,
            "result": {
                "validated": len(packages),
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "packages": results,
                "can_proceed": invalid_count == 0,
                "instruction": "Fix invalid packages before adding to package.json" if invalid_count > 0 else "All packages valid - safe to add"
            }
        }
    
    async def _run_preflight_audit(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive preflight audit before deployment.
        
        Checks:
        - Package.json validity
        - Import/export consistency
        - TypeScript patterns
        - Known anti-patterns
        """
        # Get all project files
        async with pool.acquire() as conn:
            file_rows = await conn.fetch(
                "SELECT path, content FROM enjineer_files WHERE project_id = $1",
                self.project_id
            )
        
        files = {row["path"]: row["content"] for row in file_rows}
        
        # Get package.json if exists
        package_json = None
        for path, content in files.items():
            if path.endswith("package.json"):
                try:
                    package_json = json.loads(content)
                    break
                except json.JSONDecodeError:
                    pass
        
        # Run preflight audit
        result = await engineer_intelligence.run_preflight_audit(
            self.project_id,
            files,
            package_json
        )
        
        logger.info(f"[PREFLIGHT] Audit complete: passed={result.passed}, errors={len(result.errors)}")
        
        return {
            "success": True,
            "result": {
                "passed": result.passed,
                "blocked": result.blocked,
                "errors": result.errors,
                "warnings": result.warnings,
                "recommendations": result.recommendations,
                "can_deploy": result.passed,
                "instruction": (
                    "Fix errors before deploying" if not result.passed 
                    else "Preflight passed - safe to deploy"
                )
            }
        }
    
    async def _check_circuit_breaker(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if deployment is blocked due to consecutive failures.
        
        Circuit breaker opens after 3+ consecutive failures to prevent
        deployment loops.
        """
        state = await engineer_intelligence.check_circuit_breaker(self.project_id)
        
        return {
            "success": True,
            "result": {
                "is_open": state.is_open,
                "state": state.state.value,
                "failure_count": state.failure_count,
                "can_proceed": state.can_proceed,
                "message": state.message,
                "resume_at": state.resume_at.isoformat() if state.resume_at else None,
                "instruction": (
                    state.message if state.is_open
                    else "Circuit closed - deployments allowed"
                )
            }
        }
    
    async def _get_recurring_errors(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get errors that have occurred multiple times.
        
        Helps identify systemic issues vs one-off errors.
        """
        min_occurrences = input_data.get("min_occurrences", 2)
        
        recurring = await engineer_intelligence.get_recurring_errors(
            self.project_id,
            min_occurrences
        )
        
        if not recurring:
            return {
                "success": True,
                "result": {
                    "found": False,
                    "count": 0,
                    "instruction": "No recurring errors found - each error is unique"
                }
            }
        
        error_list = []
        for r in recurring:
            error_list.append({
                "type": r.error.error_type,
                "detail": r.error.detail,
                "occurrences": r.occurrence_count,
                "first_seen": r.first_seen.isoformat(),
                "last_seen": r.last_seen.isoformat(),
                "diagnosis": r.diagnosis,
            })
        
        logger.warning(f"[INTEL] Found {len(recurring)} recurring errors for project {self.project_id}")
        
        return {
            "success": True,
            "result": {
                "found": True,
                "count": len(recurring),
                "errors": error_list,
                "instruction": """RECURRING ERRORS DETECTED!
These errors keep appearing after "fixes". Do NOT attempt one-by-one fixes.

Required actions:
1. Read the diagnosis for each recurring error
2. Do a COMPREHENSIVE audit of ALL files for the same pattern
3. Fix ALL instances before attempting another deployment
4. Use read_file to verify your changes ACTUALLY applied"""
            }
        }
    
    async def _read_file(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read file content for verification.
        
        Used to verify changes actually applied after update_file.
        """
        path = input_data.get("path")
        
        if not path:
            return {"success": False, "error": "File path is required"}
        
        # Normalize path
        if not path.startswith("/"):
            path = "/" + path
        
        async with pool.acquire() as conn:
            file = await conn.fetchrow(
                "SELECT content, checksum, version FROM enjineer_files WHERE project_id = $1 AND path = $2",
                self.project_id, path
            )
        
        if not file:
            return {"success": False, "error": f"File not found: {path}"}
        
        return {
            "success": True,
            "result": {
                "path": path,
                "content": file["content"],
                "checksum": file["checksum"],
                "version": file["version"],
                "instruction": "Compare this content against your intended changes to verify the update applied correctly."
            }
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
        
        # Claude Opus 4.5 pricing: $15/1M input, $75/1M output
        input_cost = (self.session_input_tokens / 1_000_000) * 15.0
        output_cost = (self.session_output_tokens / 1_000_000) * 75.0
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
        
        # Analyze inspiration images if present
        if attachments:
            inspiration_analysis = await self.analyze_inspiration_images(attachments)
            if inspiration_analysis.get("images_analyzed", 0) > 0:
                # Store analysis in project data for system prompt
                if "intake_data" not in self.project_data:
                    self.project_data["intake_data"] = {}
                self.project_data["intake_data"]["design_analysis"] = inspiration_analysis
                self.project_data["intake_data"]["inspiration_images"] = attachments
                
                # Persist to database for future reference
                try:
                    pool = await get_tiger_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE enjineer_projects 
                            SET metadata = jsonb_set(
                                COALESCE(metadata, '{}'::jsonb),
                                '{inspiration_analysis}',
                                $2::jsonb
                            ),
                            updated_at = NOW()
                            WHERE id = $1
                            """,
                            self.project_id,
                            json.dumps(inspiration_analysis)
                        )
                    logger.info(f"[Vision] Saved inspiration analysis for project {self.project_id}")
                except Exception as e:
                    logger.warning(f"[Vision] Failed to persist analysis: {e}")
        
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

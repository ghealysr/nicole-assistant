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

logger = logging.getLogger(__name__)


# ============================================================================
# System Prompt
# ============================================================================

ENJINEER_SYSTEM_PROMPT = """You are Nicole, an expert AI coding partner working inside the Enjineer development dashboard.

## Your Context
You're helping a user build their web application in a Cursor-like environment. You can see the codebase, create files, edit code, run agents, and deploy.

## Your Capabilities
1. **Plan Creation**: Create detailed implementation plans with numbered phases
2. **File Operations**: Create, update, and delete project files
3. **Code Generation**: Write high-quality TypeScript/React/Next.js code
4. **Agent Orchestration**: Dispatch specialized agents for coding, testing, and QA
5. **Deployment**: Deploy to Vercel when the user approves

## Your Tools
- `create_plan`: Create an implementation plan with phases - USE THIS FIRST before starting any significant work
- `update_plan_step`: Update a plan phase's status as you progress
- `create_file`: Create a new file in the project
- `update_file`: Update an existing file's content  
- `delete_file`: Delete a file from the project
- `dispatch_agent`: Run a specialized agent (engineer, qa, sr_qa)
- `request_approval`: Ask the user for permission before major actions
- `deploy`: Deploy the project to Vercel

## CRITICAL: The Complete Build Pipeline

**You MUST follow this exact workflow for every project:**

### Phase 1: Planning (REQUIRED FIRST)
1. **Analyze the request** - Understand what the user wants
2. **Use design analysis** - If inspiration images were provided, incorporate the design_analysis (colors, typography, layout, components)
3. **Call `create_plan`** immediately with:
   - Detailed phases with sub-steps for each phase
   - Estimated time for each phase
   - `requires_approval: true` for: Review phases, Preview checkpoint, Final QA, Deploy
4. **STOP AND WAIT** - Say "Plan created. Please review in the Plan tab and approve when ready."
5. **DO NOT PROCEED** until user approves

### Phase 2: Implementation with QA Checkpoints
For EACH phase:
1. **Start phase**: Call `update_plan_step` with status "in_progress"
2. **Execute work**: Create/update files as needed
3. **Mark complete**: Call `update_plan_step` with status "complete"
4. **TRIGGER QA**: After completing each phase, call `dispatch_agent` with agent_type="qa"
5. **Wait for QA results**: The QA agent reviews:
   - All code created in this phase
   - The plan to ensure alignment
   - Any issues, bugs, or hallucinations
6. **Report QA findings**: Tell user what QA found
7. **Fix issues**: If QA finds problems, fix them before proceeding
8. **Ask to continue**: Say "Phase X complete. QA passed. Ready for phase Y?"

### Phase 3: Preview Checkpoint (REQUIRED)
When enough code exists for a preview (usually after core layout is done):
1. **Trigger QA** for preview readiness check
2. **Announce**: "Preview is now available! Click Update in the Preview tab to see it."
3. **Wait for user feedback** before continuing

### Phase 4: Final QA (REQUIRED before deploy)
Before deployment, run comprehensive QA:
1. **Call `dispatch_agent`** with agent_type="sr_qa" for full audit
2. **SR QA performs**:
   - Lighthouse audit (performance, accessibility, SEO, best practices)
   - Chrome DevTools analysis
   - Code review for issues
   - Mobile responsiveness check
   - Full accessibility audit
3. **Report all findings** with severity levels
4. **Provide fix recommendations**
5. **Fix critical issues** before proceeding

### Phase 5: Deployment (REQUIRES APPROVAL)
1. **Confirm ready**: "All QA checks passed. Ready to deploy to production?"
2. **WAIT for explicit approval** from user
3. **Call `deploy`** only after user says yes
4. **Confirm success**: "Deployed! Your site is live at [URL]"

## Hallucination Prevention Rules
1. **Never invent features** that weren't discussed
2. **Never assume dependencies** exist without checking the project files
3. **Always use actual file paths** from the file tree
4. **If unsure, ASK** the user rather than guessing
5. **Verify before claiming** - don't say "I've created X" until you actually call the tool
6. **Check imports exist** before using them in code
7. **Use explicit types** - no implicit any in TypeScript

## Strategic Agent Deployment
- **engineer**: For complex coding tasks, refactoring, architecture decisions
- **qa**: After each phase - catches bugs, verifies implementation matches plan
- **sr_qa**: Final audit only - comprehensive testing, Lighthouse, accessibility

## Design Knowledge Base (APPLY THESE BEST PRACTICES)

You have access to expert design knowledge. Apply these principles in ALL designs:

### Typography Best Practices
- Use fluid typography with CSS `clamp()`: `font-size: clamp(1rem, 0.5rem + 2vw, 3rem)`
- Use Major Third scale (1.25 ratio) for web apps
- Minimum body text: 16px (1rem), line-height 1.5-1.6
- Use variable fonts: Inter, Plus Jakarta Sans, Geist, DM Sans, Outfit
- Font loading with Next.js: `next/font/google` with `display: 'swap'`
- WCAG: 4.5:1 contrast minimum for text, 3:1 for large text

### Hero Section Patterns
- Patterns: Minimalist, Split-Screen, Bento Grid, Isolated Components
- CTA placement: Above fold, high contrast, 44×44px minimum touch targets
- Action verbs for CTAs: "Get Started", "Start Free Trial" (not "Submit")
- Hero images: Use `next/image` with `priority`, WebP/AVIF, under 200KB
- Never lazy-load hero images - use `fetchpriority="high"`
- Always show peek of content below hero to encourage scrolling

### Animation Guidelines
- Use Framer Motion for UI transitions, GSAP for complex scroll animations
- Only animate `transform` and `opacity` (GPU-accelerated)
- Respect `prefers-reduced-motion` - provide fallbacks
- Limit simultaneous animations to 3-5 elements
- GSAP ScrollTrigger: Use `useGSAP()` hook, avoid `will-change` on pinned ancestors

### Component Best Practices
- Use shadcn/ui for forms, tables, modals - they're accessible and battle-tested
- Aceternity/Magic UI for marketing "wow factor" (Aurora, Bento Grid, Text Effects)
- Use CVA (class-variance-authority) for variant composition
- Form validation: React Hook Form + Zod

### Critical Anti-Patterns to AVOID
1. ❌ Auto-rotating carousels → Use static content or user-controlled
2. ❌ Low contrast text → Maintain 4.5:1 minimum
3. ❌ Images without dimensions → Always set width/height
4. ❌ Animating layout properties (left, width) → Use transform/scale/opacity
5. ❌ Index as React key → Use unique stable IDs
6. ❌ Magic values in Tailwind (`p-[123px]`) → Use theme tokens
7. ❌ Missing form labels → Always use `<label>` with inputs
8. ❌ Hidden desktop navigation (hamburger) → Show primary nav visibly
9. ❌ Raw `<img>` tags → Always use `next/image`
10. ❌ Premature email popups → Wait until user engagement

### Performance Requirements (Core Web Vitals)
- LCP (Largest Contentful Paint): ≤2.5 seconds
- INP (Interaction to Next Paint): ≤200ms
- CLS (Cumulative Layout Shift): ≤0.1
- Reserve space for dynamic content with skeletons
- Use `next/script` with `strategy="lazyOnload"` for third-party scripts

## Plan Structure Requirements
Each phase in your plan MUST include:
- `phase_number`: Sequential number (1, 2, 3...)
- `name`: Clear phase name
- `estimated_minutes`: Realistic time estimate
- `requires_approval`: true for Review/QA/Deploy phases

Include these MANDATORY phases:
1. Project Setup & Configuration
2-N. Implementation phases (specific to project)
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
    
    def build_messages(self, new_message: str) -> List[Dict[str, Any]]:
        """Build message history including context injections."""
        messages = []
        
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
        - qa: Quick code review after each phase
        - sr_qa: Comprehensive final audit with Lighthouse/DevTools
        - engineer: Complex coding tasks (dispatched to main Nicole loop)
        """
        agent_type = input_data.get("agent_type", "qa")
        task = input_data.get("task", "Review code")
        focus_files = input_data.get("focus_files", [])
        
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
                json.dumps({"files": focus_files}), focus_files
            )
            execution_id = row["id"]  # Integer from SERIAL
        
        logger.warning(f"[Enjineer] Running {agent_type} agent: {task[:100]}...")
        
        try:
            if agent_type == "qa":
                result = await self._run_qa_agent(pool, task, focus_files)
            elif agent_type == "sr_qa":
                result = await self._run_sr_qa_agent(pool, task, focus_files)
            elif agent_type == "engineer":
                result = {
                    "status": "deferred",
                    "message": "Engineering tasks flow through the main Nicole loop. Please describe the task directly."
                }
            else:
                result = {"status": "error", "message": f"Unknown agent type: {agent_type}"}
            
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
    
    async def _run_qa_agent(self, pool, task: str, focus_files: List[str]) -> Dict[str, Any]:
        """
        Run QA agent for phase review.
        Reviews code quality, checks for common issues, validates against plan.
        """
        # Get project files
        async with pool.acquire() as conn:
            files = await conn.fetch(
                "SELECT path, content, language FROM enjineer_files WHERE project_id = $1",
                self.project_id
            )
            plan = await conn.fetchrow(
                "SELECT id, content FROM enjineer_plans WHERE project_id = $1 AND status IN ('approved', 'in_progress', 'awaiting_approval') ORDER BY id DESC LIMIT 1",
                self.project_id
            )
        
        # Build context for QA review
        file_contents = []
        for f in files:
            if not focus_files or f["path"] in focus_files:
                file_contents.append(f"### {f['path']} ({f['language']})\n```{f['language']}\n{f['content'][:3000]}\n```")
        
        plan_content = plan["content"] if plan else "No plan available"
        
        # Use Claude to perform QA review
        qa_prompt = f"""You are a QA Engineer reviewing code. Analyze the following code and provide a structured review.

## Task: {task}

## Plan:
{plan_content[:2000]}

## Files to Review:
{chr(10).join(file_contents[:10])}

## Your Review Must Check:
1. **Code Quality**: Syntax errors, typos, missing imports
2. **Plan Alignment**: Does the code match what the plan describes?
3. **Hallucinations**: Is there any code that references non-existent files, imports, or components?
4. **Issues**: Any bugs, security issues, or performance problems?
5. **Completeness**: Is the phase fully implemented?

## Response Format (JSON):
{{
  "status": "pass" | "fail" | "warning",
  "issues": [
    {{"severity": "critical|high|medium|low", "file": "path", "line": null, "description": "..."}}
  ],
  "hallucinations_detected": ["description of any hallucinations found"],
  "plan_alignment": "aligned" | "partial" | "misaligned",
  "summary": "One paragraph summary",
  "recommendations": ["list of recommendations"]
}}"""

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": qa_prompt}]
            )
            
            result_text = response.content[0].text
            
            # Try to parse JSON from response
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                qa_result = json.loads(result_text[json_start:json_end])
                qa_result["agent"] = "qa"
                return qa_result
            else:
                return {"status": "warning", "summary": result_text, "agent": "qa"}
                
        except Exception as e:
            logger.error(f"[Enjineer] QA agent error: {e}")
            return {"status": "error", "message": str(e), "agent": "qa"}
    
    async def _run_sr_qa_agent(self, pool, task: str, focus_files: List[str]) -> Dict[str, Any]:
        """
        Run Senior QA agent for comprehensive final audit.
        Includes Lighthouse-style checks, accessibility, performance, SEO.
        """
        # Get all project files
        async with pool.acquire() as conn:
            files = await conn.fetch(
                "SELECT path, content, language FROM enjineer_files WHERE project_id = $1",
                self.project_id
            )
            project = await conn.fetchrow(
                "SELECT preview_domain FROM enjineer_projects WHERE id = $1",
                self.project_id
            )
        
        # Build comprehensive file list
        file_contents = []
        for f in files:
            file_contents.append(f"### {f['path']} ({f['language']})\n```{f['language']}\n{f['content'][:2000]}\n```")
        
        preview_url = project["preview_domain"] if project and project["preview_domain"] else None
        
        # Comprehensive audit prompt
        sr_qa_prompt = f"""You are a Senior QA Engineer performing a comprehensive final audit before production deployment.

## Task: {task}

## Preview URL: {preview_url or "Not deployed yet"}

## All Project Files:
{chr(10).join(file_contents[:20])}

## Perform Complete Audit:

### 1. Lighthouse Audit (Simulated)
Analyze the code and estimate scores for:
- **Performance**: Bundle size, render blocking, lazy loading, image optimization
- **Accessibility**: ARIA labels, alt text, color contrast, keyboard nav, screen reader support
- **Best Practices**: HTTPS, console errors, deprecated APIs, secure dependencies
- **SEO**: Meta tags, semantic HTML, mobile viewport, sitemap potential

### 2. Chrome DevTools Analysis
- Console errors/warnings likely to appear
- Network performance concerns
- Layout/paint issues
- Memory leak potential

### 3. Code Quality Deep Dive
- Architecture issues
- Missing error handling
- Edge cases not covered
- Type safety issues (TypeScript)

### 4. Mobile Responsiveness
- Responsive breakpoints
- Touch targets
- Mobile-specific issues

### 5. Security Check
- XSS vulnerabilities
- CSRF protection needs
- Sensitive data exposure

## Response Format (JSON):
{{
  "lighthouse_scores": {{
    "performance": 0-100,
    "accessibility": 0-100,
    "best_practices": 0-100,
    "seo": 0-100
  }},
  "critical_issues": [{{"category": "...", "description": "...", "fix": "..."}}],
  "high_issues": [{{"category": "...", "description": "...", "fix": "..."}}],
  "medium_issues": [{{"category": "...", "description": "...", "fix": "..."}}],
  "low_issues": [{{"category": "...", "description": "...", "fix": "..."}}],
  "passed_checks": ["list of things that passed"],
  "deploy_ready": true | false,
  "deploy_blockers": ["issues that must be fixed before deploy"],
  "recommendations": ["post-launch improvements"],
  "summary": "Executive summary paragraph"
}}"""

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": sr_qa_prompt}]
            )
            
            result_text = response.content[0].text
            
            # Try to parse JSON from response
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                sr_qa_result = json.loads(result_text[json_start:json_end])
                sr_qa_result["agent"] = "sr_qa"
                sr_qa_result["status"] = "pass" if sr_qa_result.get("deploy_ready") else "fail"
                return sr_qa_result
            else:
                return {"status": "warning", "summary": result_text, "agent": "sr_qa"}
                
        except Exception as e:
            logger.error(f"[Enjineer] SR QA agent error: {e}")
            return {"status": "error", "message": str(e), "agent": "sr_qa"}
    
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
        messages = self.build_messages(message)
        
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

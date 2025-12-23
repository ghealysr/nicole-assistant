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

## CRITICAL: How to Use Plans

**ALWAYS create a plan FIRST** when the user asks you to build something significant. Here's the workflow:

1. **When user describes what they want to build**:
   - Immediately call `create_plan` with clear phases
   - Each phase should have: phase_number, name, estimated_minutes, requires_approval (true for major milestones)
   - Example phases: "Setup project structure", "Create components", "Add styling", "Testing"

2. **As you work through each phase**:
   - Call `update_plan_step` with status "in_progress" when starting a phase
   - Create/update files using the appropriate tools
   - Call `update_plan_step` with status "complete" when done
   - If phase has requires_approval=true, wait for user approval before proceeding

3. **The user sees your plan in the sidebar** - they can track progress, see which phase you're on, and approve phases that need approval.

## Example Plan Creation:
When a user says "Build me a landing page with a hero section and pricing table", immediately call create_plan with:
- name: "Landing Page Implementation"
- description: "Build a modern landing page with hero and pricing"  
- phases: array of phase objects with phase_number, name, estimated_minutes, requires_approval

## Interaction Style
- Be conversational and helpful, like a senior developer pairing
- Explain your reasoning when making architectural decisions
- Ask clarifying questions when requirements are unclear
- Confirm before making destructive changes
- Celebrate milestones and progress with the user
- When creating files, use create_file tool - don't just show the code
- When discussing plans, use create_plan tool - don't just list steps in text

## Important Rules
1. **ALWAYS call create_plan** before starting any multi-step work
2. **ALWAYS update plan status** as you progress through phases
3. Always request approval before deploying to production
4. When asked to create something, use your tools - don't just describe
5. Keep the user informed about what you're doing in real-time
6. If you encounter errors, explain them clearly and suggest fixes
7. Be proactive but not presumptuous
8. For Next.js projects, use App Router conventions (app/ directory)

## Current Context
- **Time**: {current_time}
- **Timezone**: {timezone}
- **Project**: {project_name}
- **Description**: {project_description}
- **Tech Stack**: {tech_stack}
- **Status**: {project_status}

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
        "description": "Create an implementation plan with numbered steps. Use when starting a new feature or project.",
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
                            "requires_approval": {"type": "boolean", "description": "Does this need user approval?"}
                        },
                        "required": ["phase_number", "name"]
                    },
                    "description": "Ordered list of implementation phases"
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
                    "description": "UUID of the plan"
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
                WHERE project_id = $1 AND status IN ('active', 'draft', 'in_progress', 'awaiting_approval')
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
        """Build system prompt with rich project context."""
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
                        "skipped": "⏭️"
                    }.get(p.get("status", "pending"), "⬜")
                    plan_text += f"{status_emoji} Phase {p.get('phase_number', '?')}: {p.get('name', 'Unknown')}\n"
            
            messages.append({"role": "user", "content": f"[CONTEXT: Current Plan]\n{plan_text}"})
            messages.append({"role": "assistant", "content": "I see the current plan. I'll continue from where we left off."})
        
        # Add conversation history (limit to prevent token overflow)
        history = self.project_data.get("messages", [])[-8:]
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add the new user message
        messages.append({
            "role": "user",
            "content": new_message
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
        
        async with pool.acquire() as conn:
            # Create plan - let SERIAL auto-generate the id
            # Note: version is TEXT type in database
            row = await conn.fetchrow(
                """
                INSERT INTO enjineer_plans (project_id, version, content, status, current_phase_number)
                VALUES ($1, '1.0', $2, 'in_progress', 1)
                RETURNING id
                """,
                self.project_id, json.dumps({"name": name, "description": description})
            )
            plan_id = row["id"]
            
            # Create phases
            for phase in phases_data:
                await conn.execute(
                    """
                    INSERT INTO enjineer_plan_phases 
                    (plan_id, phase_number, name, status, estimated_minutes, requires_approval)
                    VALUES ($1, $2, $3, 'pending', $4, $5)
                    """,
                    plan_id,
                    phase.get("phase_number", 1),
                    phase.get("name", "Unnamed Phase"),
                    phase.get("estimated_minutes", 30),
                    phase.get("requires_approval", False)
                )
        
        logger.info(f"[Enjineer] Created plan '{name}' (id={plan_id}) with {len(phases_data)} phases")
        return {
            "success": True,
            "result": {
                "action": "plan_created",
                "plan_id": str(plan_id),  # Convert to string for JSON
                "name": name,
                "phases_count": len(phases_data),
                "message": f"Created plan '{name}' with {len(phases_data)} phases. Check the Plan tab in the sidebar to see progress!"
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
            result = await conn.execute(
                """
                UPDATE enjineer_plan_phases 
                SET status = $1, notes = COALESCE($2, notes),
                    started_at = CASE WHEN $1 = 'in_progress' AND started_at IS NULL THEN NOW() ELSE started_at END,
                    completed_at = CASE WHEN $1 = 'complete' THEN NOW() ELSE completed_at END
                WHERE plan_id = $3 AND phase_number = $4
                """,
                status, notes, plan_id_int, phase_number
            )
        
        if result == "UPDATE 0":
            return {"success": False, "error": f"Phase {phase_number} not found in plan {plan_id}"}
        
        logger.info(f"[Enjineer] Updated plan phase {phase_number} to {status}")
        return {
            "success": True,
            "result": {
                "action": "phase_updated",
                "plan_id": plan_id,
                "phase_number": phase_number,
                "status": status
            }
        }
    
    async def _dispatch_agent(self, pool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a specialized agent to perform a task."""
        agent_type = input_data["agent_type"]
        task = input_data["task"]
        focus_files = input_data.get("focus_files", [])
        
        execution_id = str(uuid4())
        
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO enjineer_agent_executions 
                (id, project_id, agent_type, instruction, context, focus_areas, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
                """,
                execution_id, self.project_id, agent_type, task,
                json.dumps({}), focus_files
            )
        
        # TODO: Actually dispatch the agent via background task
        # For now, mark as completed (placeholder)
        logger.info(f"[Enjineer] Dispatched {agent_type} agent: {task[:100]}...")
        
        return {
            "success": True,
            "result": {
                "action": "agent_dispatched",
                "execution_id": execution_id,
                "agent_type": agent_type,
                "task": task,
                "status": "pending",
                "message": f"{agent_type.title()} agent has been dispatched and will begin work shortly."
            }
        }
    
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
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
                
            except Exception as e:
                logger.error(f"[Enjineer] Error in process_message: {e}", exc_info=True)
                yield {"type": "error", "content": str(e)}
                break
        
        if iteration >= self.max_tool_iterations:
            logger.warning(f"[Enjineer] Hit max tool iterations ({self.max_tool_iterations})")
            yield {"type": "text", "content": "\n\n*I've reached the maximum number of operations. Let me know if you'd like me to continue.*"}
        
        yield {"type": "done"}

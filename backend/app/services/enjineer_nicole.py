"""
Enjineer Nicole Service
Nicole's AI agent that operates within the Enjineer dashboard as a conversational coding partner.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional, List, Dict, Any
from uuid import UUID

from anthropic import Anthropic

from app.config import settings
from app.database import get_db_pool

logger = logging.getLogger(__name__)


ENJINEER_SYSTEM_PROMPT = """You are Nicole, an expert AI coding partner working inside the Enjineer development dashboard.

## Your Context
You're helping a user build their web application in a Cursor-like environment. You can see the codebase, create files, edit code, run agents, and deploy.

## Your Capabilities
1. **Plan Creation**: Create detailed implementation plans when asked
2. **File Operations**: Create, edit, and delete project files
3. **Code Generation**: Write high-quality TypeScript/React code
4. **Agent Orchestration**: Dispatch specialized agents for design, coding, testing, and QA
5. **Deployment**: Deploy to Vercel when the user approves

## Your Tools
- `create_file`: Create a new file in the project
- `update_file`: Update existing file content
- `delete_file`: Delete a file
- `create_plan`: Create an implementation plan with steps
- `dispatch_agent`: Run a specialized agent (design, code, test, qa)
- `deploy`: Deploy the current project to Vercel
- `request_approval`: Ask the user for permission before major actions

## Interaction Style
- Be conversational and helpful, like a senior developer pairing
- Explain your reasoning when making decisions
- Ask clarifying questions when requirements are unclear
- Confirm before making major changes
- Celebrate milestones and progress

## Important Rules
1. Always request approval before deploying
2. Show code changes before applying them
3. Keep the user informed about what you're doing
4. If you encounter errors, explain them clearly
5. Be proactive but not presumptuous

Current Time: {current_time}
Project: {project_name}
Project Description: {project_description}
Tech Stack: {tech_stack}
"""


ENJINEER_TOOLS = [
    {
        "name": "create_file",
        "description": "Create a new file in the project",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root (e.g., '/src/components/Button.tsx')"
                },
                "content": {
                    "type": "string",
                    "description": "The file content to write"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language (e.g., 'typescript', 'css')"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "update_file",
        "description": "Update an existing file's content",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to update"
                },
                "content": {
                    "type": "string",
                    "description": "New content for the file"
                },
                "commit_message": {
                    "type": "string",
                    "description": "Description of the change"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file from the project",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to delete"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_plan",
        "description": "Create an implementation plan with numbered steps",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the plan"
                },
                "description": {
                    "type": "string",
                    "description": "Overview of what the plan accomplishes"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "order": {"type": "integer"},
                            "description": {"type": "string"},
                            "estimated_duration": {"type": "string"}
                        }
                    },
                    "description": "Ordered list of implementation steps"
                }
            },
            "required": ["name", "steps"]
        }
    },
    {
        "name": "dispatch_agent",
        "description": "Dispatch a specialized agent to perform a task",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["design", "code", "test", "qa", "research"],
                    "description": "Type of agent to dispatch"
                },
                "task": {
                    "type": "string",
                    "description": "What the agent should accomplish"
                },
                "context": {
                    "type": "object",
                    "description": "Additional context for the agent"
                }
            },
            "required": ["agent_type", "task"]
        }
    },
    {
        "name": "request_approval",
        "description": "Request user approval before proceeding with a major action",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "What you're requesting approval for"
                },
                "description": {
                    "type": "string",
                    "description": "Details about what will happen if approved"
                },
                "approval_type": {
                    "type": "string",
                    "enum": ["plan", "deploy", "major_change", "budget"],
                    "description": "Type of approval needed"
                }
            },
            "required": ["title", "description", "approval_type"]
        }
    },
    {
        "name": "deploy",
        "description": "Deploy the project to Vercel (requires prior approval)",
        "input_schema": {
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": ["preview", "production"],
                    "description": "Deployment target"
                },
                "message": {
                    "type": "string",
                    "description": "Deployment commit message"
                }
            },
            "required": ["environment"]
        }
    }
]


class EnjineerNicole:
    """Nicole's AI agent for the Enjineer dashboard."""
    
    def __init__(self, project_id: str, user_id: str):
        self.project_id = project_id
        self.user_id = user_id
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        self.project_data: Optional[dict] = None
        
    async def load_project_context(self) -> dict:
        """Load project data and files for context."""
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Get project
            project = await conn.fetchrow(
                "SELECT * FROM enjineer_projects WHERE id = $1",
                UUID(self.project_id)
            )
            
            if not project:
                raise ValueError(f"Project {self.project_id} not found")
            
            # Get files
            files = await conn.fetch(
                "SELECT path, content, language FROM enjineer_files WHERE project_id = $1",
                UUID(self.project_id)
            )
            
            # Get recent messages
            messages = await conn.fetch(
                """
                SELECT role, content FROM enjineer_messages 
                WHERE project_id = $1 
                ORDER BY created_at DESC 
                LIMIT 20
                """,
                UUID(self.project_id)
            )
            
            # Get current plan
            plan = await conn.fetchrow(
                """
                SELECT * FROM enjineer_plans 
                WHERE project_id = $1 AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
                """,
                UUID(self.project_id)
            )
        
        self.project_data = {
            "id": str(project["id"]),
            "name": project["name"],
            "description": project["description"] or "",
            "tech_stack": project["tech_stack"] or {},
            "status": project["status"],
            "settings": project["settings"] or {},
            "files": [dict(f) for f in files],
            "messages": list(reversed([dict(m) for m in messages])),
            "plan": dict(plan) if plan else None
        }
        
        return self.project_data
    
    def build_system_prompt(self) -> str:
        """Build the system prompt with project context."""
        if not self.project_data:
            raise ValueError("Project data not loaded")
        
        tech_stack_str = ", ".join(
            f"{k}: {v}" 
            for k, v in (self.project_data.get("tech_stack") or {}).items()
        ) or "Not specified"
        
        return ENJINEER_SYSTEM_PROMPT.format(
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_name=self.project_data["name"],
            project_description=self.project_data["description"] or "No description",
            tech_stack=tech_stack_str
        )
    
    def build_messages(self, new_message: str) -> List[dict]:
        """Build conversation messages including history."""
        messages = []
        
        # Add file context as first user message
        if self.project_data["files"]:
            file_summary = "\n".join(
                f"- {f['path']} ({f['language']})"
                for f in self.project_data["files"][:20]  # Limit for context
            )
            messages.append({
                "role": "user",
                "content": f"[Project Files]\n{file_summary}"
            })
            messages.append({
                "role": "assistant",
                "content": "I see the project files. I'm ready to help!"
            })
        
        # Add plan context if exists
        if self.project_data["plan"]:
            plan = self.project_data["plan"]
            plan_summary = f"Current Plan: {plan['name']}\nStatus: {plan['status']}"
            if plan.get("steps"):
                steps_str = "\n".join(
                    f"{s.get('order', i+1)}. {s.get('description', 'Unknown step')}"
                    for i, s in enumerate(plan["steps"][:10])
                )
                plan_summary += f"\nSteps:\n{steps_str}"
            messages.append({
                "role": "user",
                "content": f"[Current Plan]\n{plan_summary}"
            })
            messages.append({
                "role": "assistant",
                "content": "I'm tracking the plan. Let me know when you're ready to proceed."
            })
        
        # Add conversation history
        for msg in self.project_data["messages"][-10:]:  # Last 10 messages
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add new message
        messages.append({
            "role": "user",
            "content": new_message
        })
        
        return messages
    
    async def execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Execute a tool and return the result."""
        pool = await get_db_pool()
        
        try:
            if tool_name == "create_file":
                return await self._create_file(pool, tool_input)
            elif tool_name == "update_file":
                return await self._update_file(pool, tool_input)
            elif tool_name == "delete_file":
                return await self._delete_file(pool, tool_input)
            elif tool_name == "create_plan":
                return await self._create_plan(pool, tool_input)
            elif tool_name == "dispatch_agent":
                return await self._dispatch_agent(tool_input)
            elif tool_name == "request_approval":
                return await self._request_approval(pool, tool_input)
            elif tool_name == "deploy":
                return await self._deploy(tool_input)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}
    
    async def _create_file(self, pool, input_data: dict) -> dict:
        """Create a new file."""
        import hashlib
        
        path = input_data["path"]
        content = input_data["content"]
        language = input_data.get("language", "plaintext")
        checksum = hashlib.sha256(content.encode()).hexdigest()
        
        async with pool.acquire() as conn:
            # Check if exists
            existing = await conn.fetchrow(
                "SELECT id FROM enjineer_files WHERE project_id = $1 AND path = $2",
                UUID(self.project_id), path
            )
            
            if existing:
                return {"error": f"File already exists: {path}"}
            
            await conn.execute(
                """
                INSERT INTO enjineer_files (project_id, path, content, language, modified_by, checksum)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                UUID(self.project_id), path, content, language, "nicole", checksum
            )
        
        logger.info(f"[Enjineer] Created file: {path}")
        return {"success": True, "path": path, "message": f"Created {path}"}
    
    async def _update_file(self, pool, input_data: dict) -> dict:
        """Update an existing file."""
        import hashlib
        
        path = input_data["path"]
        content = input_data["content"]
        commit_message = input_data.get("commit_message", "Updated by Nicole")
        checksum = hashlib.sha256(content.encode()).hexdigest()
        
        async with pool.acquire() as conn:
            file = await conn.fetchrow(
                "SELECT id, version FROM enjineer_files WHERE project_id = $1 AND path = $2",
                UUID(self.project_id), path
            )
            
            if not file:
                return {"error": f"File not found: {path}"}
            
            new_version = file["version"] + 1
            
            await conn.execute(
                """
                UPDATE enjineer_files 
                SET content = $1, version = $2, modified_by = $3, checksum = $4
                WHERE id = $5
                """,
                content, new_version, "nicole", checksum, file["id"]
            )
            
            # Create version record
            await conn.execute(
                """
                INSERT INTO enjineer_file_versions (file_id, version, content, modified_by, commit_message)
                VALUES ($1, $2, $3, $4, $5)
                """,
                file["id"], new_version, content, "nicole", commit_message
            )
        
        logger.info(f"[Enjineer] Updated file: {path}")
        return {"success": True, "path": path, "version": new_version}
    
    async def _delete_file(self, pool, input_data: dict) -> dict:
        """Delete a file."""
        path = input_data["path"]
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM enjineer_files WHERE project_id = $1 AND path = $2",
                UUID(self.project_id), path
            )
        
        if result == "DELETE 0":
            return {"error": f"File not found: {path}"}
        
        logger.info(f"[Enjineer] Deleted file: {path}")
        return {"success": True, "path": path}
    
    async def _create_plan(self, pool, input_data: dict) -> dict:
        """Create an implementation plan."""
        name = input_data["name"]
        description = input_data.get("description", "")
        steps = input_data["steps"]
        
        async with pool.acquire() as conn:
            plan = await conn.fetchrow(
                """
                INSERT INTO enjineer_plans (project_id, name, description, steps, status)
                VALUES ($1, $2, $3, $4, 'active')
                RETURNING id
                """,
                UUID(self.project_id), name, description, steps
            )
        
        logger.info(f"[Enjineer] Created plan: {name} with {len(steps)} steps")
        return {
            "success": True, 
            "plan_id": str(plan["id"]),
            "name": name,
            "steps_count": len(steps)
        }
    
    async def _dispatch_agent(self, input_data: dict) -> dict:
        """Dispatch a specialized agent."""
        agent_type = input_data["agent_type"]
        task = input_data["task"]
        context = input_data.get("context", {})
        
        # For now, return a placeholder - in full implementation,
        # this would integrate with the Faz Code agent system
        logger.info(f"[Enjineer] Dispatching {agent_type} agent: {task}")
        
        return {
            "success": True,
            "agent_type": agent_type,
            "task": task,
            "message": f"{agent_type.title()} agent dispatched. Task: {task}"
        }
    
    async def _request_approval(self, pool, input_data: dict) -> dict:
        """Request user approval."""
        title = input_data["title"]
        description = input_data["description"]
        approval_type = input_data["approval_type"]
        
        async with pool.acquire() as conn:
            approval = await conn.fetchrow(
                """
                INSERT INTO enjineer_approvals 
                (project_id, approval_type, title, description, status, requested_by)
                VALUES ($1, $2, $3, $4, 'pending', 'nicole')
                RETURNING id
                """,
                UUID(self.project_id), approval_type, title, description
            )
        
        logger.info(f"[Enjineer] Requested approval: {title}")
        return {
            "success": True,
            "approval_id": str(approval["id"]),
            "title": title,
            "awaiting_user": True
        }
    
    async def _deploy(self, input_data: dict) -> dict:
        """Deploy to Vercel."""
        environment = input_data["environment"]
        message = input_data.get("message", "Deployed by Enjineer")
        
        # Check for pending approval
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            pending = await conn.fetchrow(
                """
                SELECT id FROM enjineer_approvals 
                WHERE project_id = $1 AND approval_type = 'deploy' AND status = 'pending'
                """,
                UUID(self.project_id)
            )
        
        if pending:
            return {
                "error": "Deploy approval still pending",
                "approval_id": str(pending["id"])
            }
        
        # For now, return a placeholder - in full implementation,
        # this would integrate with Vercel
        logger.info(f"[Enjineer] Deploying to {environment}")
        
        return {
            "success": True,
            "environment": environment,
            "message": f"Deployment to {environment} initiated"
        }
    
    async def process_message(
        self, 
        message: str, 
        attachments: Optional[List[dict]] = None
    ) -> AsyncGenerator[dict, None]:
        """Process a user message and yield streaming response events."""
        
        # Load project context
        await self.load_project_context()
        
        # Build prompt
        system_prompt = self.build_system_prompt()
        messages = self.build_messages(message)
        
        logger.info(f"[Enjineer] Processing message for project {self.project_data['name']}")
        
        try:
            # Initial Claude call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
                tools=ENJINEER_TOOLS,
                stream=True
            )
            
            current_text = ""
            tool_use_blocks = []
            
            for event in response:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        current_text += event.delta.text
                        yield {"type": "text", "content": event.delta.text}
                    elif hasattr(event.delta, "partial_json"):
                        # Tool input being streamed
                        pass
                        
                elif event.type == "content_block_start":
                    if hasattr(event.content_block, "type"):
                        if event.content_block.type == "tool_use":
                            tool_use_blocks.append({
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": ""
                            })
                            yield {
                                "type": "tool_use",
                                "tool": event.content_block.name,
                                "input": {}
                            }
                            
                elif event.type == "message_stop":
                    break
            
            # Handle tool calls if any
            if response.stop_reason == "tool_use":
                # Get final message to extract tool inputs
                final_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    system=system_prompt,
                    messages=messages,
                    tools=ENJINEER_TOOLS
                )
                
                for content_block in final_response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_id = content_block.id
                        
                        yield {
                            "type": "tool_use",
                            "tool": tool_name,
                            "input": tool_input
                        }
                        
                        # Execute the tool
                        result = await self.execute_tool(tool_name, tool_input)
                        
                        # Handle approval requests specially
                        if tool_name == "request_approval" and result.get("success"):
                            yield {
                                "type": "approval_required",
                                "approval_id": result["approval_id"]
                            }
                        
                        # Handle code creation/updates
                        if tool_name in ("create_file", "update_file") and result.get("success"):
                            yield {
                                "type": "code",
                                "path": result["path"],
                                "content": tool_input.get("content", "")
                            }
                        
                        # Continue conversation with tool result
                        messages.append({
                            "role": "assistant",
                            "content": final_response.content
                        })
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(result)
                            }]
                        })
                        
                        # Get follow-up response
                        followup = self.client.messages.create(
                            model=self.model,
                            max_tokens=4096,
                            system=system_prompt,
                            messages=messages,
                            tools=ENJINEER_TOOLS,
                            stream=True
                        )
                        
                        for event in followup:
                            if event.type == "content_block_delta":
                                if hasattr(event.delta, "text"):
                                    yield {"type": "text", "content": event.delta.text}
                                    
        except Exception as e:
            logger.error(f"[Enjineer] Error processing message: {e}")
            yield {"type": "error", "content": str(e)}


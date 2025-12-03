"""
Nicole V7 - Agent Orchestrator

Central orchestration service that wires together:
- Think Tool (explicit reasoning)
- Tool Search (dynamic tool discovery)
- Tool Examples (enhanced accuracy)
- Memory operations
- Document operations

This is the integration layer that connects all agent architecture
components to the chat router.

Author: Nicole V7 Architecture
"""

import logging
import json
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

from app.services.think_tool import think_tool_service, ThinkingStep, THINK_TOOL_DEFINITION
from app.services.tool_search_service import tool_search_service, TOOL_SEARCH_DEFINITION
from app.services.tool_examples import tool_examples_service
from app.services.alphawave_memory_service import memory_service
from app.services.alphawave_document_service import document_service
from app.skills.skill_runner import skill_runner
from app.skills.skill_memory import get_skill_memory_manager
from app.services.skill_run_service import skill_run_service
from app.skills.adapters.base import SkillExecutionError

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates Nicole's agent capabilities.
    
    Responsibilities:
    1. Build tool definitions for Claude (with examples injected)
    2. Execute tool calls from Claude
    3. Track thinking sessions
    4. Manage tool discovery and loading
    """
    
    def __init__(self):
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self.skill_memory_manager = get_skill_memory_manager(skill_runner.registry)
        logger.info("[ORCHESTRATOR] Agent Orchestrator initialized")
    
    def get_core_tools(self) -> List[Dict[str, Any]]:
        """
        Get the core tools that are always available to Nicole.
        
        These tools are loaded for every request:
        - think: Explicit reasoning
        - search_tools: Dynamic tool discovery
        - memory_search: Search memories
        - memory_store: Store memories
        - document_search: Search documents
        
        Returns:
            List of tool definitions with examples injected
        """
        core_tools = [
            # Think Tool
            tool_examples_service.enhance_tool_schema(THINK_TOOL_DEFINITION),
            
            # Tool Search
            tool_examples_service.enhance_tool_schema(TOOL_SEARCH_DEFINITION),
            
            # Memory Search
            tool_examples_service.enhance_tool_schema({
                "name": "memory_search",
                "description": "Search Nicole's memory for information about the user, their preferences, past conversations, and stored knowledge. Use this to recall anything you've learned about the user.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for. Use specific keywords from the user's question."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of memories to return (default: 5)",
                            "default": 5
                        },
                        "memory_type": {
                            "type": "string",
                            "enum": ["preference", "fact", "relationship", "event", "workflow", "insight", "task", "goal"],
                            "description": "Optional: Filter by memory type"
                        },
                        "min_confidence": {
                            "type": "number",
                            "description": "Minimum confidence score (0-1). Higher = more certain memories.",
                            "default": 0.3
                        }
                    },
                    "required": ["query"]
                }
            }),
            
            # Memory Store
            tool_examples_service.enhance_tool_schema({
                "name": "memory_store",
                "description": "Store new information in Nicole's memory for future recall. Use this when the user shares facts, preferences, or important information about themselves.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The information to remember. Be specific and factual."
                        },
                        "memory_type": {
                            "type": "string",
                            "enum": ["preference", "fact", "relationship", "event", "workflow", "insight", "task", "goal"],
                            "description": "Type of memory"
                        },
                        "importance": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "How important is this memory?",
                            "default": "medium"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization"
                        }
                    },
                    "required": ["content", "memory_type"]
                }
            }),
            
            # Document Search
            tool_examples_service.enhance_tool_schema({
                "name": "document_search",
                "description": "Search through documents the user has uploaded to Nicole. Use this to find information in PDFs, text files, and other uploaded content.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in documents"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 3
                        }
                    },
                    "required": ["query"]
                }
            }),
        ]
        
        core_tools.extend(self._get_skill_tools())
        return core_tools

    def _get_skill_tools(self) -> List[Dict[str, Any]]:
        """Generate tool definitions for installed skills.
        
        Only includes skills that can be executed automatically (not manual skills).
        """
        tools = []
        # Executor types that can be run automatically
        EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}
        
        try:
            skill_runner.registry.load()
            for skill in skill_runner.registry.list_skills():
                # Skip non-installed or not-ready skills
                if skill.status != "installed":
                    continue
                if skill.setup_status != "ready":
                    logger.debug(
                        f"[ORCHESTRATOR] Skipping skill {skill.id} (setup_status={skill.setup_status})"
                    )
                    continue
                # Skip manual skills - they can't be executed programmatically
                if skill.executor.executor_type.lower() not in EXECUTABLE_TYPES:
                    logger.debug(f"[ORCHESTRATOR] Skipping manual skill: {skill.id}")
                    continue

                schema = {
                    "name": skill.id,
                    "description": f"{skill.description} (Skill)",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True,
                        "description": (
                            "Parameters forwarded directly to the skill runner. "
                            "Include a JSON payload matching the skill's documented interface."
                        ),
                    },
                }
                tools.append(tool_examples_service.enhance_tool_schema(schema))
        except Exception as exc:
            logger.warning(f"[ORCHESTRATOR] Failed to load skill tools: {exc}")
        return tools
    
    def start_session(
        self,
        session_id: str,
        user_id: int,
        conversation_id: int
    ) -> None:
        """Start a new agent session for a request."""
        self._active_sessions[session_id] = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "started_at": datetime.utcnow(),
            "tool_calls": [],
            "thinking_steps": []
        }
        
        # Start thinking session
        think_tool_service.start_session(session_id, user_id, conversation_id)
        
        logger.debug(f"[ORCHESTRATOR] Started session {session_id}")
    
    def end_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """End an agent session and return summary."""
        session = self._active_sessions.pop(session_id, None)
        
        # Complete thinking session
        thinking_session = think_tool_service.complete_session(session_id)
        
        if session and thinking_session:
            session["thinking_summary"] = thinking_session.get_summary()
        
        return session
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        user_id: int,
        session_id: Optional[str] = None
    ) -> Any:
        """
        Execute a tool and return the result.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            user_id: User ID for context
            session_id: Optional session ID for tracking
            
        Returns:
            Tool execution result
        """
        logger.info(f"[ORCHESTRATOR] Executing tool: {tool_name}")
        
        # Record tool call if session exists
        conversation_id = None
        if session_id and session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            session["tool_calls"].append({
                "tool": tool_name,
                "input": tool_input,
                "timestamp": datetime.utcnow().isoformat()
            })
            conversation_id = session.get("conversation_id")
        
        try:
            # Think tool - just record and return
            if tool_name == "think":
                thought = tool_input.get("thought", "")
                category = tool_input.get("category", "multi_step_planning")
                conclusion = tool_input.get("conclusion")
                
                if session_id:
                    step = think_tool_service.record_thought(
                        session_id=session_id,
                        thought=thought,
                        category=category,
                        conclusion=conclusion
                    )
                    
                    if session_id in self._active_sessions:
                        self._active_sessions[session_id]["thinking_steps"].append({
                            "thought": thought,
                            "category": category,
                            "conclusion": conclusion
                        })
                
                return {"status": "recorded", "message": "Thinking recorded."}
            
            # Tool Search
            elif tool_name == "search_tools":
                query = tool_input.get("query", "")
                category = tool_input.get("category")
                limit = tool_input.get("limit", 5)
                
                results = tool_search_service.search_tools(
                    query=query,
                    category=category,
                    limit=limit
                )
                
                return {
                    "tools_found": len(results),
                    "tools": results
                }
            
            # Memory Search
            elif tool_name == "memory_search":
                query = tool_input.get("query", "")
                limit = tool_input.get("limit", 5)
                memory_type = tool_input.get("memory_type")
                min_confidence = tool_input.get("min_confidence", 0.3)
                
                memories = await memory_service.search_memory(
                    user_id=user_id,
                    query=query,
                    limit=limit,
                    min_confidence=min_confidence
                )
                
                # Filter by type if specified
                if memory_type and memories:
                    memories = [m for m in memories if m.get("memory_type") == memory_type]
                
                return {
                    "memories_found": len(memories) if memories else 0,
                    "memories": memories or []
                }
            
            # Memory Store
            elif tool_name == "memory_store":
                content = tool_input.get("content", "")
                memory_type = tool_input.get("memory_type", "fact")
                importance = tool_input.get("importance", "medium")
                tags = tool_input.get("tags", [])
                
                result = await memory_service.save_memory(
                    user_id=user_id,
                    memory_type=memory_type,
                    content=content,
                    importance=importance,
                    source="nicole"
                )
                
                if result:
                    return {
                        "status": "stored",
                        "memory_id": result.get("memory_id") or result.get("id"),
                        "message": f"Memory stored: {content[:50]}..."
                    }
                else:
                    return {
                        "status": "duplicate",
                        "message": "Similar memory already exists"
                    }
            
            # Document Search
            elif tool_name == "document_search":
                query = tool_input.get("query", "")
                limit = tool_input.get("limit", 3)
                
                results = await document_service.search_documents(
                    user_id=user_id,
                    query=query,
                    limit=limit
                )
                
                return {
                    "documents_found": len(results) if results else 0,
                    "documents": results or []
                }
            
            else:
                # Try to execute a registered skill
                skill_meta = skill_runner.registry.get_skill(tool_name)
                if skill_meta:
                    if skill_meta.setup_status != "ready":
                        return {
                            "status": "not_ready",
                            "message": (
                                f"Skill '{tool_name}' is not ready (setup_status={skill_meta.setup_status}). "
                                "Run the skill health check to enable it."
                            ),
                        }
                    try:
                        result = await skill_runner.run(
                            skill_id=tool_name,
                            payload=tool_input,
                            user_id=user_id,
                            conversation_id=conversation_id,
                        )
                    except SkillExecutionError as exec_err:
                        await skill_run_service.record_failure(
                            skill_meta=skill_meta,
                            user_id=user_id,
                            conversation_id=conversation_id,
                            error_message=str(exec_err),
                        )
                        return {
                            "status": "error",
                            "message": f"Skill '{tool_name}' failed: {exec_err}",
                        }
                    # Update metadata
                    skill_meta.last_run_at = result.finished_at.isoformat()
                    skill_meta.last_run_status = result.status
                    skill_runner.registry.update_skill(skill_meta)
                    try:
                        await self.skill_memory_manager.record_run(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            skill=skill_meta,
                            result_status=result.status,
                            output=result.output,
                            log_file=str(result.log_file),
                        )
                    except Exception as mem_err:
                        logger.warning(f"[ORCHESTRATOR] Failed to log skill memory: {mem_err}")
                    try:
                        await skill_run_service.record_success(
                            skill_meta=skill_meta,
                            result=result,
                            user_id=user_id,
                            conversation_id=conversation_id,
                        )
                    except Exception as run_log_err:
                        logger.warning(f"[ORCHESTRATOR] Failed to persist skill run: {run_log_err}")
                    return {
                        "status": result.status,
                        "output": result.output,
                        "error": result.error,
                        "log_file": str(result.log_file),
                    }
                
                # Try to find a dynamically registered tool
                tool = tool_search_service.get_tool(tool_name)
                if tool and tool.mcp_server:
                    # TODO: Route to appropriate MCP server
                    return {
                        "status": "not_implemented",
                        "message": f"Tool {tool_name} from MCP server {tool.mcp_server} is not yet connected"
                    }
                
                return {
                    "status": "unknown_tool",
                    "message": f"Tool '{tool_name}' is not available"
                }
                
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Tool execution error: {e}", exc_info=True)
            raise
    
    def get_tool_executor(self, user_id: int, session_id: Optional[str] = None):
        """
        Get a tool executor function for use with Claude client.
        
        Returns an async function that can be passed to generate_streaming_response_with_tools.
        """
        async def executor(tool_name: str, tool_input: Dict[str, Any]) -> Any:
            return await self.execute_tool(
                tool_name=tool_name,
                tool_input=tool_input,
                user_id=user_id,
                session_id=session_id
            )
        
        return executor


# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()


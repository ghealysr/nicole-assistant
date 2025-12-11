"""
Nicole V7 - Agent Orchestrator

Central orchestration service that wires together:
- Think Tool (explicit reasoning)
- Tool Search (dynamic tool discovery)
- Tool Examples (enhanced accuracy)
- Memory operations
- Document operations
- MCP tools (Google, Notion, Telegram, Filesystem, Playwright)

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
from app.services.alphawave_claude_skills_service import claude_skills_service

# MCP imports
from app.mcp import (
    mcp_manager,
    get_mcp_tools,
    call_mcp_tool,
    AlphawaveMCPManager,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates Nicole's agent capabilities.
    
    Responsibilities:
    1. Build tool definitions for Claude (with examples injected)
    2. Execute tool calls from Claude
    3. Track thinking sessions
    4. Manage tool discovery and loading
    5. Route MCP tool calls to appropriate servers
    """
    
    def __init__(self):
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self.skill_memory_manager = get_skill_memory_manager(skill_runner.registry)
        self._mcp_initialized = False
        logger.info("[ORCHESTRATOR] Agent Orchestrator initialized")
    
    async def initialize_mcp(self) -> Dict[str, bool]:
        """
        Initialize MCP connections on startup.
        
        Call this during application startup.
        
        Returns:
            Dict mapping server names to connection success
        """
        if self._mcp_initialized:
            return {}
        
        if isinstance(mcp_manager, AlphawaveMCPManager):
            results = await mcp_manager.connect_enabled_servers()
            self._mcp_initialized = True
            logger.info(f"[ORCHESTRATOR] MCP initialized: {results}")
            return results
        
        logger.info("[ORCHESTRATOR] MCP not available (using fallback)")
        self._mcp_initialized = True
        return {}
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP server status summary."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            return mcp_manager.get_status_summary()
        return {"status": "fallback", "servers": {}}
    
    # =========================================================================
    # CLAUDE SKILLS INTEGRATION
    # =========================================================================
    
    def detect_relevant_skills(self, user_message: str) -> List[Dict[str, Any]]:
        """
        Detect which Claude Skills might be relevant for the user's request.
        
        Args:
            user_message: The user's message/request
            
        Returns:
            List of relevant skills with their metadata
        """
        try:
            return claude_skills_service.search_skills(user_message, max_results=3)
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Skill detection failed: {e}")
            return []
    
    def get_skill_context(self, user_message: str) -> Optional[str]:
        """
        Get skill-enhanced context for a user request.
        
        If the user's message matches a specialized skill, this returns
        the skill's instructions to be added to Nicole's context.
        
        Args:
            user_message: The user's message/request
            
        Returns:
            Skill activation prompt if a relevant skill is found, else None
        """
        try:
            relevant = self.detect_relevant_skills(user_message)
            if relevant and relevant[0].get('relevance_score', 0) >= 5.0:
                skill = relevant[0]
                activation = claude_skills_service.get_skill_activation_prompt(skill['id'])
                if activation:
                    logger.info(f"[ORCHESTRATOR] Activating skill: {skill['name']}")
                    return activation
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Skill context retrieval failed: {e}")
        return None
    
    def get_skills_summary(self) -> str:
        """
        Get a summary of available skills for Nicole's system prompt.
        
        Returns:
            Markdown-formatted skills summary
        """
        try:
            return claude_skills_service.get_skills_summary_for_prompt()
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Skills summary failed: {e}")
            return ""
    
    def get_skill_details(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details of a specific skill.
        
        Args:
            skill_id: The skill identifier
            
        Returns:
            Full skill data or None
        """
        return claude_skills_service.get_skill(skill_id)
    
    def list_all_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available Claude Skills.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of skill summaries
        """
        return claude_skills_service.list_skills(category)
    
    # =========================================================================
    # CORE TOOLS
    # =========================================================================
    
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
            
            # Dashboard Status - Nicole's self-awareness
            tool_examples_service.enhance_tool_schema({
                "name": "dashboard_status",
                "description": "Get Nicole's current system status, usage metrics, costs, and diagnostics. Use this when the user asks about: your status, how you're doing, system health, API costs, token usage, storage usage, monthly costs, any issues or problems with you, or when they want to troubleshoot something.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_usage": {
                            "type": "boolean",
                            "description": "Include token usage and cost data (default: true)",
                            "default": True
                        },
                        "include_diagnostics": {
                            "type": "boolean",
                            "description": "Include system diagnostics and health info (default: true)",
                            "default": True
                        }
                    },
                    "required": []
                }
            }),
        ]
        
        # Add skill tools
        core_tools.extend(self._get_skill_tools())
        
        # Add MCP tools (Google, Notion, Telegram, Filesystem, Playwright)
        core_tools.extend(self._get_mcp_tools())
        
        return core_tools
    
    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions from connected MCP servers.
        
        These tools are dynamically discovered from MCP servers:
        - Google Workspace (Gmail, Calendar, Drive)
        - Notion (databases, pages)
        - Telegram (messaging)
        - Filesystem (file operations)
        - Playwright (web automation)
        
        Returns:
            List of tool definitions in Claude format
        """
        try:
            mcp_tools = get_mcp_tools()
            
            if mcp_tools:
                logger.info(f"[ORCHESTRATOR] Loaded {len(mcp_tools)} MCP tools")
                # Enhance with examples where available
                return [
                    tool_examples_service.enhance_tool_schema(tool)
                    for tool in mcp_tools
                ]
            
            return []
            
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Failed to get MCP tools: {e}")
            return []

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
            
            # Dashboard Status - Nicole's self-awareness
            elif tool_name == "dashboard_status":
                from app.services.alphawave_usage_service import usage_service
                
                include_usage = tool_input.get("include_usage", True)
                include_diagnostics = tool_input.get("include_diagnostics", True)
                
                result = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                if include_usage:
                    try:
                        usage_data = await usage_service.get_usage_summary(user_id, 30)
                        result["usage"] = {
                            "period": f"{usage_data['period']['days']} days",
                            "tokens": {
                                "total": usage_data['tokens']['total'],
                                "claude": usage_data['tokens']['claude_input'] + usage_data['tokens']['claude_output'],
                                "embeddings": usage_data['tokens']['openai_embedding'],
                            },
                            "costs": {
                                "total": f"${usage_data['costs']['total']:.2f}",
                                "claude": f"${usage_data['costs']['claude']:.2f}",
                                "openai": f"${usage_data['costs']['openai']:.2f}",
                                "azure": f"${usage_data['costs']['azure']:.2f}",
                                "storage": f"${usage_data['costs']['tiger_storage']:.2f}",
                            },
                            "projections": {
                                "monthly_estimate": f"${usage_data['projections']['monthly_estimate']:.2f}",
                                "trend": usage_data['projections']['trend'],
                            },
                            "storage": {
                                "total": usage_data['storage']['total_formatted'],
                                "documents": usage_data['storage']['document_count'],
                                "chunks": usage_data['storage']['chunk_count'],
                            },
                        }
                    except Exception as e:
                        result["usage"] = {"error": str(e)}
                
                if include_diagnostics:
                    try:
                        diagnostics = await usage_service.get_diagnostics(user_id)
                        result["diagnostics"] = {
                            "health_score": diagnostics['health']['score'],
                            "health_status": diagnostics['health']['status'],
                            "memory_system": {
                                "total_memories": diagnostics['memory_system']['total_memories'],
                                "avg_confidence": diagnostics['memory_system']['avg_confidence'],
                            },
                            "api_health": {
                                "requests_24h": diagnostics['api_health']['requests_24h'],
                                "success_rate": f"{diagnostics['api_health']['success_rate']}%",
                            },
                            "issues": diagnostics['issues'],
                            "warnings": diagnostics['warnings'],
                        }
                    except Exception as e:
                        result["diagnostics"] = {"error": str(e)}
                
                return result
            
            else:
                # Try to execute a registered skill first
                skill_result = await self._execute_skill(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
                if skill_result is not None:
                    return skill_result
                
                # Try to execute as MCP tool
                mcp_result = await self._execute_mcp_tool(tool_name, tool_input)
                if mcp_result is not None:
                    return mcp_result
                
                # Try to find a dynamically registered tool
                tool = tool_search_service.get_tool(tool_name)
                if tool and tool.mcp_server:
                    # Route to MCP server
                    return await self._execute_mcp_tool(tool_name, tool_input)
                
                return {
                    "status": "unknown_tool",
                    "message": f"Tool '{tool_name}' is not available"
                }
        
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Tool execution error: {e}", exc_info=True)
            raise
    
    async def _execute_skill(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        user_id: int,
        conversation_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a skill with comprehensive validation and error handling.
        
        DEFENSIVE CHECKS:
        1. Skill exists in registry
        2. Skill status is "installed"
        3. Skill executor type is executable (not manual)
        4. Skill setup_status is "ready"
        5. Install path exists
        
        Args:
            tool_name: Skill ID to execute
            tool_input: Payload parameters
            user_id: Executing user
            conversation_id: Associated conversation (optional)
            
        Returns:
            Execution result dict, or None if not a skill
        """
        # Reload registry to ensure fresh state
        skill_runner.registry.load()
        skill_meta = skill_runner.registry.get_skill(tool_name)
        
        if not skill_meta:
            return None  # Not a skill, let other handlers try
        
        # Define executable types
        EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}
        
        # Check 1: Skill must be installed
        if getattr(skill_meta, 'status', None) != "installed":
            return {
                "status": "not_installed",
                "message": f"Skill '{tool_name}' is not installed (status={getattr(skill_meta, 'status', 'unknown')}).",
                "skill_id": tool_name,
            }
        
        # Check 2: Skill must have executable type
        exec_type = skill_meta.executor.executor_type.lower() if skill_meta.executor else "unknown"
        if exec_type not in EXECUTABLE_TYPES:
            return {
                "status": "manual_skill",
                "message": (
                    f"Skill '{tool_name}' is a manual skill (type={exec_type}) and cannot be executed programmatically. "
                    f"Please refer to the skill documentation for usage instructions."
                ),
                "skill_id": tool_name,
                "executor_type": exec_type,
            }
        
        # Check 3: Skill must be ready (with graceful handling of missing field)
        setup_status = getattr(skill_meta, 'setup_status', None)
        if setup_status is None:
            # Missing Phase 4 field - treat as needs_verification
            setup_status = "needs_verification"
            logger.warning(
                f"[ORCHESTRATOR] Skill {tool_name} missing setup_status field. "
                "Run skill_registry_migrate.py to fix."
            )
        
        if setup_status != "ready":
            status_guidance = {
                "needs_configuration": "Configure required environment variables or credentials.",
                "needs_verification": "Run skill health check to verify it works correctly.",
                "manual_only": "This skill requires manual execution.",
                "failed": "Previous health check failed. Review health_notes and retry.",
            }
            guidance = status_guidance.get(setup_status, "Contact support for assistance.")
            
            return {
                "status": "not_ready",
                "message": (
                    f"Skill '{tool_name}' is not ready for execution.\n"
                    f"Current status: {setup_status}\n"
                    f"Action required: {guidance}"
                ),
                "skill_id": tool_name,
                "setup_status": setup_status,
                "health_notes": getattr(skill_meta, 'health_notes', []),
            }
        
        # Check 4: Install path must exist
        if skill_meta.install_path:
            from pathlib import Path
            PROJECT_ROOT = Path(__file__).resolve().parents[3]
            install_dir = PROJECT_ROOT / skill_meta.install_path
            if not install_dir.exists():
                return {
                    "status": "missing_files",
                    "message": f"Skill '{tool_name}' installation directory not found: {skill_meta.install_path}",
                    "skill_id": tool_name,
                }
        
        # All checks passed - execute the skill
        try:
            result = await skill_runner.run(
                skill_id=tool_name,
                payload=tool_input,
                user_id=user_id,
                conversation_id=conversation_id,
            )
        except SkillExecutionError as exec_err:
            # Record failure
            try:
                await skill_run_service.record_failure(
                    skill_meta=skill_meta,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    error_message=str(exec_err),
                )
            except Exception as record_err:
                logger.warning(f"[ORCHESTRATOR] Failed to record skill failure: {record_err}")
            
            # Update skill metadata with failure
            skill_meta.last_run_at = datetime.utcnow().isoformat()
            skill_meta.last_run_status = "failed"
            skill_meta.health_notes = getattr(skill_meta, 'health_notes', []) or []
            skill_meta.health_notes.append(f"Execution failed: {str(exec_err)[:100]}")
            try:
                skill_runner.registry.update_skill(skill_meta)
            except Exception:
                pass
            
            return {
                "status": "error",
                "message": f"Skill '{tool_name}' execution failed: {exec_err}",
                "skill_id": tool_name,
            }
        except Exception as unexpected_err:
            logger.error(f"[ORCHESTRATOR] Unexpected skill error: {unexpected_err}", exc_info=True)
            return {
                "status": "error",
                "message": f"Skill '{tool_name}' encountered an unexpected error: {type(unexpected_err).__name__}",
                "skill_id": tool_name,
            }
        
        # Update metadata with successful run
        skill_meta.last_run_at = result.finished_at.isoformat()
        skill_meta.last_run_status = result.status
        try:
            skill_runner.registry.update_skill(skill_meta)
        except Exception as update_err:
            logger.warning(f"[ORCHESTRATOR] Failed to update skill metadata: {update_err}")
        
        # Record to memory system (non-blocking)
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
        
        # Persist to database (non-blocking)
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
            "skill_id": tool_name,
            "duration_seconds": result.duration_seconds,
        }
    
    async def _execute_mcp_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a tool via MCP with comprehensive error handling.
        
        MCP INTEGRATION STATUS:
        - MCP servers are optional external integrations
        - If no servers configured, gracefully return None
        - If server disconnected, provide clear error message
        - If tool not found, return None (let other handlers try)
        
        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            
        Returns:
            Tool result dict on success/error, None if tool not found in MCP
        """
        # Check if MCP is properly initialized
        if not self._mcp_initialized:
            logger.debug(f"[ORCHESTRATOR] MCP not initialized, skipping for {tool_name}")
            return None
        
        # Check if Docker MCP Gateway has this tool (priority)
        try:
            from app.mcp.docker_mcp_client import _mcp_client
            if _mcp_client and _mcp_client.is_connected and _mcp_client._tools_cache:
                # Check if tool exists in Docker Gateway
                docker_tool = next((t for t in _mcp_client._tools_cache if t.name == tool_name), None)
                if docker_tool:
                    logger.debug(f"[ORCHESTRATOR] Found {tool_name} in Docker Gateway, executing via MCP")
                    # Execute via call_mcp_tool which will route to Docker Gateway
                    result = await call_mcp_tool(tool_name, tool_input)
                    return result
        except Exception as e:
            logger.debug(f"[ORCHESTRATOR] Docker Gateway check failed: {e}")
        
        # Check if MCP manager is the full implementation
        if not isinstance(mcp_manager, AlphawaveMCPManager):
            logger.debug(f"[ORCHESTRATOR] MCP using fallback manager, skipping for {tool_name}")
            return None
        
        # Try to get tool from MCP manager
        mcp_tool = mcp_manager.get_tool(tool_name)
        
        if not mcp_tool:
            # Tool not found in MCP - let other handlers try
            return None
        
        # Verify server connection
        server_name = mcp_tool.server_name
        server_status = mcp_manager.get_server_status(server_name) if hasattr(mcp_manager, 'get_server_status') else None
        
        if server_status and not server_status.get("connected"):
            return {
                "status": "mcp_disconnected",
                "message": (
                    f"MCP server '{server_name}' is not connected. "
                    f"This tool requires the {server_name} integration to be configured and running. "
                    "Check server logs or contact support."
                ),
                "tool": tool_name,
                "server": server_name,
                "remediation": f"Verify {server_name} MCP server is running and credentials are configured."
            }
        
        logger.info(f"[ORCHESTRATOR] Executing MCP tool: {tool_name} via {server_name}")
        
        try:
            result = await call_mcp_tool(tool_name, tool_input)
            
            # Check for structured errors
            if isinstance(result, dict) and "error" in result:
                error_msg = result.get("error", "Unknown MCP error")
                
                # Provide context-aware remediation hints
                remediation = self._get_mcp_error_remediation(tool_name, server_name, error_msg)
                
                logger.warning(f"[ORCHESTRATOR] MCP tool error: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "tool": tool_name,
                    "server": server_name,
                    "remediation": remediation,
                }
            
            return {
                "status": "success",
                "result": result.get("result", result) if isinstance(result, dict) else result,
                "tool": tool_name,
                "server": server_name,
            }
            
        except ConnectionError as conn_err:
            return {
                "status": "connection_error",
                "message": f"Failed to connect to MCP server '{server_name}': {conn_err}",
                "tool": tool_name,
                "server": server_name,
                "remediation": "Check network connectivity and server status.",
            }
        except TimeoutError as timeout_err:
            return {
                "status": "timeout",
                "message": f"MCP tool '{tool_name}' timed out: {timeout_err}",
                "tool": tool_name,
                "server": server_name,
                "remediation": "The operation took too long. Try with simpler inputs or check server load.",
            }
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] MCP execution error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"MCP tool execution failed: {type(e).__name__}: {str(e)[:200]}",
                "tool": tool_name,
                "server": server_name,
            }
    
    def _get_mcp_error_remediation(self, tool_name: str, server_name: str, error_msg: str) -> str:
        """Get context-aware remediation hints for MCP errors."""
        error_lower = error_msg.lower()
        
        # Auth errors
        if any(term in error_lower for term in ["auth", "token", "credential", "permission", "401", "403"]):
            return f"Check your {server_name} credentials in the MCP configuration."
        
        # Not found errors
        if any(term in error_lower for term in ["not found", "404", "does not exist"]):
            return f"The requested resource may have been deleted or you may not have access."
        
        # Rate limit errors
        if any(term in error_lower for term in ["rate", "limit", "429", "quota"]):
            return "You've hit an API rate limit. Wait a moment and try again."
        
        # Input validation errors
        if any(term in error_lower for term in ["invalid", "validation", "required", "missing"]):
            return f"Check the input parameters for {tool_name}. Some required fields may be missing."
        
        return f"Review the error message and {server_name} documentation for guidance."
    
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


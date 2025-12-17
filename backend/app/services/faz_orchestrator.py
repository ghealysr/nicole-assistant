"""
Faz Code Orchestrator

State machine that manages the agent pipeline flow.
Inspired by LangGraph but simplified for this use case.

Pipeline Flow:
    User Prompt → Nicole (Route)
                    ↓
    ┌─────────────────────────────────────┐
    │     planning ← → research           │
    │         ↓                           │
    │      design                         │
    │         ↓                           │
    │      coding ← → qa (loop)           │
    │         ↓                           │
    │      review                         │
    │         ↓                           │
    │      memory → DONE                  │
    └─────────────────────────────────────┘
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
from enum import Enum
from weakref import WeakValueDictionary

from app.database import db

logger = logging.getLogger(__name__)


# =============================================================================
# GLOBAL ORCHESTRATOR REGISTRY
# =============================================================================

# Track running orchestrators for cancellation support
# WeakValueDictionary allows garbage collection when orchestrator completes
_running_orchestrators: WeakValueDictionary[int, "FazOrchestrator"] = WeakValueDictionary()


def get_running_orchestrator(project_id: int) -> Optional["FazOrchestrator"]:
    """Get a running orchestrator for a project, if any."""
    return _running_orchestrators.get(project_id)


async def cancel_orchestrator(project_id: int) -> bool:
    """
    Cancel a running orchestrator for a project.
    
    Returns:
        True if an orchestrator was found and cancelled, False otherwise.
    """
    orchestrator = _running_orchestrators.get(project_id)
    if orchestrator:
        await orchestrator.cancel()
        return True
    return False


# =============================================================================
# STATE DEFINITIONS
# =============================================================================

class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ProjectState(TypedDict, total=False):
    """State passed between agents."""
    # Identity
    project_id: int
    user_id: int
    
    # User input
    original_prompt: str
    current_prompt: str
    
    # Status
    status: str
    pipeline_status: PipelineStatus
    
    # Agent tracking
    current_agent: str
    agent_history: List[str]
    iteration_count: int
    max_iterations: int
    
    # Data from agents
    architecture: Dict[str, Any]
    design_tokens: Dict[str, Any]
    research_results: Dict[str, Any]
    files: Dict[str, str]
    qa_review: Dict[str, Any]
    review_result: Dict[str, Any]
    learnings: Dict[str, Any]
    
    # Memory context
    relevant_memories: List[Dict[str, Any]]
    relevant_errors: List[Dict[str, Any]]
    relevant_artifacts: List[Dict[str, Any]]
    relevant_skills: List[Dict[str, Any]]
    
    # Errors
    error: Optional[str]
    error_history: List[Dict[str, Any]]
    
    # Cost tracking
    total_tokens: int
    total_cost_cents: float


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class FazOrchestrator:
    """
    Manages the agent pipeline for Faz Code.
    
    Uses a state machine approach where each agent returns
    the next agent to execute, and the orchestrator manages
    the flow, state, and persistence.
    """
    
    def __init__(self, project_id: int, user_id: int):
        """Initialize orchestrator for a project."""
        self.project_id = project_id
        self.user_id = user_id
        
        # Agent instances
        self._agents = {}
        self._activity_callback = None
        
        # Cancellation support
        self._cancelled = False
        self._current_task: Optional[asyncio.Task] = None
        
        # State
        self.state: ProjectState = {
            "project_id": project_id,
            "user_id": user_id,
            "status": "intake",
            "pipeline_status": PipelineStatus.IDLE,
            "agent_history": [],
            "iteration_count": 0,
            "max_iterations": 5,
            "files": {},
            "total_tokens": 0,
            "total_cost_cents": 0.0,
            "error_history": [],
        }
        
        # Register in global registry
        _running_orchestrators[project_id] = self
        
        logger.info(f"[Orchestrator] Initialized for project {project_id}")
    
    def set_activity_callback(self, callback):
        """Set callback for activity logging."""
        self._activity_callback = callback
    
    async def cancel(self):
        """
        Cancel the running pipeline.
        
        Sets cancellation flag and waits for current agent to complete.
        """
        if self._cancelled:
            return
        
        logger.info(f"[Orchestrator] Cancellation requested for project {self.project_id}")
        self._cancelled = True
        self.state["pipeline_status"] = PipelineStatus.PAUSED
        
        # Log cancellation activity
        await self._log_activity(
            "orchestrator", "cancel",
            "Pipeline cancellation requested",
            content_type="status"
        )
        
        # Update project status
        await self._update_project_status("paused")
        
        # If we have a current task, try to cancel it
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
    
    def is_cancelled(self) -> bool:
        """Check if pipeline has been cancelled."""
        return self._cancelled
    
    async def _log_activity(
        self,
        agent_name: str,
        activity_type: str,
        message: str,
        details: Dict[str, Any] = None,
        content_type: str = "status"
    ):
        """Log activity to database and callback."""
        try:
            # Log to database
            await db.execute(
                """
                INSERT INTO faz_agent_activities
                    (project_id, agent_name, agent_model, activity_type, message, details, content_type, started_at, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), 'complete')
                """,
                self.project_id,
                agent_name,
                self._get_agent(agent_name).model_name if agent_name in self._agents else "unknown",
                activity_type,
                message,
                json.dumps(details or {}),
                content_type,
            )
            
            # Callback for real-time updates
            if self._activity_callback:
                await self._activity_callback({
                    "agent": agent_name,
                    "type": activity_type,
                    "message": message,
                    "details": details,
                    "content_type": content_type,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to log activity: {e}")
    
    def _get_agent(self, agent_id: str):
        """Get or create agent instance."""
        if agent_id not in self._agents:
            from app.services.faz_agents import (
                NicoleAgent, PlanningAgent, ResearchAgent,
                DesignAgent, CodingAgent, QAAgent, ReviewAgent, MemoryAgent
            )
            
            AGENT_CLASSES = {
                "nicole": NicoleAgent,
                "planning": PlanningAgent,
                "research": ResearchAgent,
                "design": DesignAgent,
                "coding": CodingAgent,
                "qa": QAAgent,
                "review": ReviewAgent,
                "memory": MemoryAgent,
            }
            
            if agent_id not in AGENT_CLASSES:
                raise ValueError(f"Unknown agent: {agent_id}")
            
            self._agents[agent_id] = AGENT_CLASSES[agent_id]()
        
        return self._agents[agent_id]
    
    async def run(self, prompt: str, start_agent: str = "nicole") -> ProjectState:
        """
        Run the pipeline from a user prompt.
        
        Args:
            prompt: User's request
            start_agent: Which agent to start with (default: nicole for routing)
            
        Returns:
            Final state with all generated data
        """
        self.state["original_prompt"] = prompt
        self.state["current_prompt"] = prompt
        self.state["pipeline_status"] = PipelineStatus.RUNNING
        self.state["status"] = "planning"
        
        # Load context from memory
        await self._load_memory_context()
        
        # Update project status
        await self._update_project_status("planning")
        
        current_agent = start_agent
        
        while current_agent:
            # Check for cancellation
            if self._cancelled:
                logger.info(f"[Orchestrator] Pipeline cancelled at {current_agent}")
                await self._log_activity(
                    "orchestrator", "cancel",
                    f"Pipeline cancelled at {current_agent} agent",
                    content_type="status"
                )
                break
            
            # Check iteration limit
            if self.state["iteration_count"] >= self.state["max_iterations"]:
                logger.warning(f"[Orchestrator] Max iterations ({self.state['max_iterations']}) reached")
                await self._log_activity(
                    "orchestrator", "error", 
                    f"Max iterations reached. Stopping at {current_agent}."
                )
                break
            
            self.state["iteration_count"] += 1
            self.state["current_agent"] = current_agent
            self.state["agent_history"].append(current_agent)
            
            # Log start
            await self._log_activity(
                current_agent, "route",
                f"Starting {current_agent} agent",
                {"iteration": self.state["iteration_count"]}
            )
            
            try:
                # Run agent
                agent = self._get_agent(current_agent)
                result = await agent.run(self.state)
                
                # Update state with result
                self.state["total_tokens"] += result.input_tokens + result.output_tokens
                self.state["total_cost_cents"] += result.cost_cents
                
                if result.files:
                    self.state["files"].update(result.files)
                    
                    # Persist files immediately for real-time updates
                    # (especially important for coding agent)
                    if current_agent == "coding":
                        await self._persist_files_incremental(result.files)
                
                if result.data:
                    # Merge data into state
                    for key, value in result.data.items():
                        if key not in ["files"]:  # Files handled above
                            self.state[key] = value
                
                # Log completion
                await self._log_activity(
                    current_agent, "complete",
                    result.message,
                    {
                        "success": result.success,
                        "tokens": result.input_tokens + result.output_tokens,
                        "cost_cents": result.cost_cents,
                        "files_generated": len(result.files),
                        "next_agent": result.next_agent,
                    },
                    content_type="response"
                )
                
                if not result.success:
                    # Handle error
                    self.state["error"] = result.error
                    self.state["error_history"].append({
                        "agent": current_agent,
                        "error": result.error,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    
                    await self._log_activity(
                        current_agent, "error",
                        f"Error: {result.error}",
                        content_type="error"
                    )
                    
                    # Try to recover or stop
                    if self.state["iteration_count"] < 3:
                        # Early failure - try again
                        current_agent = current_agent
                        continue
                    else:
                        # Too many failures
                        break
                
                # Determine next agent
                current_agent = result.next_agent
                
                # Update status based on agent
                await self._update_status_from_agent(current_agent)
                
            except Exception as e:
                logger.exception(f"[Orchestrator] Agent {current_agent} failed: {e}")
                
                await self._log_activity(
                    current_agent, "error",
                    f"Agent crashed: {str(e)}",
                    {"exception": str(e)},
                    content_type="error"
                )
                
                self.state["error"] = str(e)
                break
        
        # Pipeline complete
        self.state["pipeline_status"] = PipelineStatus.COMPLETED
        
        # Run memory agent to extract learnings
        if self.state.get("files"):
            try:
                memory_agent = self._get_agent("memory")
                memory_result = await memory_agent.run(self.state)
                
                if memory_result.success and memory_result.data:
                    await self._store_learnings(memory_result.data)
            except Exception as e:
                logger.error(f"[Orchestrator] Memory extraction failed: {e}")
        
        # Final status update
        final_status = "approved" if not self.state.get("error") else "failed"
        await self._update_project_status(final_status)
        
        # Store files to database
        if self.state.get("files"):
            await self._persist_files()
        
        logger.info(
            f"[Orchestrator] Pipeline complete: {len(self.state.get('files', {}))} files, "
            f"{self.state['total_tokens']} tokens, ${self.state['total_cost_cents']/100:.2f}"
        )
        
        return self.state
    
    async def _load_memory_context(self):
        """Load relevant context from memory system."""
        try:
            prompt = self.state.get("original_prompt", "")
            
            # TODO: Implement embedding search for more relevant results
            # For now, get recent learnings
            
            # Get recent error solutions
            errors = await db.fetch(
                """
                SELECT error_type, error_message, solution_description, times_accepted
                FROM faz_error_solutions
                WHERE times_accepted > 0
                ORDER BY times_accepted DESC
                LIMIT 5
                """,
            )
            self.state["relevant_errors"] = [dict(e) for e in errors]
            
            # Get recent artifacts
            artifacts = await db.fetch(
                """
                SELECT name, artifact_type, code, description, category
                FROM faz_code_artifacts
                WHERE is_latest = true
                ORDER BY times_used DESC
                LIMIT 5
                """,
            )
            self.state["relevant_artifacts"] = [dict(a) for a in artifacts]
            
            # Get skills
            skills = await db.fetch(
                """
                SELECT skill_name, skill_category, approach, pitfalls
                FROM faz_skill_library
                ORDER BY times_successful DESC
                LIMIT 5
                """,
            )
            self.state["relevant_skills"] = [dict(s) for s in skills]
            
            logger.info(
                f"[Orchestrator] Loaded context: {len(errors)} errors, "
                f"{len(artifacts)} artifacts, {len(skills)} skills"
            )
            
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to load memory context: {e}")
    
    async def _update_project_status(self, status: str):
        """Update project status in database, including architecture and design tokens."""
        try:
            # Prepare architecture and design tokens as JSON
            architecture_json = json.dumps(self.state.get("architecture") or {})
            design_tokens_json = json.dumps(self.state.get("design_tokens") or {})
            tech_stack_json = json.dumps(self.state.get("tech_stack") or {})
            
            # Update project with all relevant data
            await db.execute(
                """
                UPDATE faz_projects
                SET status = $1,
                    current_agent = $2,
                    status_history = status_history || $3::jsonb,
                    total_tokens_used = $4,
                    total_cost_cents = $5,
                    architecture = $6::jsonb,
                    design_tokens = $7::jsonb,
                    tech_stack = $8::jsonb,
                    updated_at = NOW()
                WHERE project_id = $9
                """,
                status,
                self.state.get("current_agent"),
                json.dumps([{
                    "status": status,
                    "agent": self.state.get("current_agent"),
                    "timestamp": datetime.utcnow().isoformat(),
                }]),
                self.state.get("total_tokens", 0),
                int(self.state.get("total_cost_cents", 0)),
                architecture_json,
                design_tokens_json,
                tech_stack_json,
                self.project_id,
            )
            
            logger.info(
                f"[Orchestrator] Updated project {self.project_id}: status={status}, "
                f"architecture={bool(self.state.get('architecture'))}, "
                f"design_tokens={bool(self.state.get('design_tokens'))}"
            )
            
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to update project status: {e}")
    
    async def _update_status_from_agent(self, next_agent: Optional[str]):
        """Map agent to project status."""
        status_map = {
            "planning": "planning",
            "research": "researching",
            "design": "designing",
            "coding": "building",
            "qa": "qa",
            "review": "review",
            None: "approved",
        }
        
        status = status_map.get(next_agent, "building")
        self.state["status"] = status
        await self._update_project_status(status)
    
    async def _persist_files(self):
        """Save generated files to database and broadcast to WebSocket clients."""
        try:
            files = self.state.get("files", {})
            
            for path, content in files.items():
                # Determine file type
                extension = path.split(".")[-1] if "." in path else ""
                file_type = "component" if "components/" in path else "page" if "page.tsx" in path else "config"
                language = "typescript" if extension in ["ts", "tsx"] else "javascript" if extension in ["js", "jsx"] else extension
                line_count = content.count("\n") + 1
                
                # Insert or update file in database
                file_id = await db.fetchval(
                    """
                    INSERT INTO faz_files
                        (project_id, path, filename, extension, content, file_type, 
                         language, line_count, generated_by, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'generated')
                    ON CONFLICT (project_id, path, version) 
                    DO UPDATE SET content = $5, updated_at = NOW()
                    RETURNING file_id
                    """,
                    self.project_id,
                    path,
                    path.split("/")[-1],
                    extension,
                    content,
                    file_type,
                    language,
                    line_count,
                    self.state.get("current_agent", "coding"),
                )
                
                # Broadcast file event for real-time updates
                if self._activity_callback:
                    await self._activity_callback({
                        "type": "file",
                        "file_id": file_id,
                        "path": path,
                        "filename": path.split("/")[-1],
                        "extension": extension,
                        "content": content,
                        "file_type": file_type,
                        "language": language,
                        "line_count": line_count,
                        "agent": self.state.get("current_agent", "coding"),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
            
            logger.info(f"[Orchestrator] Persisted and broadcast {len(files)} files")
            
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to persist files: {e}")
    
    async def _persist_files_incremental(self, files: Dict[str, str]):
        """
        Persist files immediately during coding phase for real-time updates.
        
        Called after each coding iteration to provide live file tree updates.
        """
        try:
            for path, content in files.items():
                extension = path.split(".")[-1] if "." in path else ""
                file_type = "component" if "components/" in path else "page" if "page.tsx" in path else "config"
                language = "typescript" if extension in ["ts", "tsx"] else "javascript" if extension in ["js", "jsx"] else extension
                line_count = content.count("\n") + 1
                
                # Upsert file
                file_id = await db.fetchval(
                    """
                    INSERT INTO faz_files
                        (project_id, path, filename, extension, content, file_type, 
                         language, line_count, generated_by, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'generated')
                    ON CONFLICT (project_id, path, version) 
                    DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
                    RETURNING file_id
                    """,
                    self.project_id,
                    path,
                    path.split("/")[-1],
                    extension,
                    content,
                    file_type,
                    language,
                    line_count,
                    "coding",
                )
                
                # Broadcast file event
                if self._activity_callback:
                    await self._activity_callback({
                        "type": "file",
                        "file_id": file_id,
                        "path": path,
                        "filename": path.split("/")[-1],
                        "extension": extension,
                        "content": content,
                        "file_type": file_type,
                        "language": language,
                        "line_count": line_count,
                        "agent": "coding",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    
                logger.debug(f"[Orchestrator] Incremental persist: {path}")
                
        except Exception as e:
            logger.error(f"[Orchestrator] Incremental file persist failed: {e}")
    
    async def _store_learnings(self, learnings_data: Dict[str, Any]):
        """Store extracted learnings to database."""
        try:
            learnings = learnings_data.get("learnings", learnings_data)
            
            # Store error solutions
            for error in learnings.get("error_solutions", []):
                await db.execute(
                    """
                    INSERT INTO faz_error_solutions
                        (error_type, error_message, solution_description, framework)
                    VALUES ($1, $2, $3, 'nextjs')
                    """,
                    error.get("error_type", "unknown"),
                    error.get("error_message", ""),
                    error.get("solution", ""),
                )
            
            # Store artifacts
            for artifact in learnings.get("artifacts", []):
                await db.execute(
                    """
                    INSERT INTO faz_code_artifacts
                        (artifact_type, name, slug, code, description, category, source_project_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    artifact.get("type", "component"),
                    artifact.get("name", "unnamed"),
                    artifact.get("name", "unnamed").lower().replace(" ", "-"),
                    artifact.get("code", ""),
                    artifact.get("description", ""),
                    artifact.get("category", "general"),
                    self.project_id,
                )
            
            # Store skills
            for skill in learnings.get("skills", []):
                await db.execute(
                    """
                    INSERT INTO faz_skill_library
                        (skill_name, skill_category, description, approach, pitfalls, learned_from_project_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    skill.get("name", "unnamed"),
                    skill.get("category", "architecture"),
                    skill.get("name", ""),
                    skill.get("approach", ""),
                    skill.get("pitfalls", []),
                    self.project_id,
                )
            
            # Store preferences
            for pref in learnings.get("preferences", []):
                await db.execute(
                    """
                    INSERT INTO faz_user_preferences
                        (user_id, preference_type, preference_key, preference_value, confidence_score)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id, preference_type, preference_key)
                    DO UPDATE SET 
                        preference_value = $4,
                        confidence_score = GREATEST(faz_user_preferences.confidence_score, $5),
                        observation_count = faz_user_preferences.observation_count + 1,
                        updated_at = NOW()
                    """,
                    self.user_id,
                    pref.get("type", "styling"),
                    pref.get("key", "unknown"),
                    pref.get("value", ""),
                    pref.get("confidence", 0.5),
                )
            
            logger.info(f"[Orchestrator] Stored learnings from project")
            
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to store learnings: {e}")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

async def create_orchestrator(project_id: int, user_id: int) -> FazOrchestrator:
    """Create and return an orchestrator instance."""
    return FazOrchestrator(project_id, user_id)


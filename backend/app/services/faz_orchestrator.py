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
    WAITING = "waiting"            # Waiting at a gate for user approval
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class PipelineMode(str, Enum):
    """Pipeline execution mode."""
    AUTO = "auto"                  # Run without stopping for approval
    INTERACTIVE = "interactive"   # Pause at gates for user review


# Define which agents require approval in interactive mode
INTERACTIVE_GATES = {
    "nicole": "awaiting_confirm",           # Confirm understanding
    "research": "awaiting_research_review", # Review research findings
    "planning": "awaiting_plan_approval",   # Approve architecture
    "design": "awaiting_design_approval",   # Approve design tokens
    "qa": "awaiting_qa_approval",           # Review QA results
    "review": "awaiting_final_approval",    # Final approval before deploy
}


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
    pipeline_mode: PipelineMode
    
    # Interactive mode tracking
    current_phase: str
    awaiting_approval_for: Optional[str]
    last_gate_reached_at: Optional[str]
    gate_artifacts: Dict[str, str]  # artifact_type -> content
    
    # Agent tracking
    current_agent: str
    agent_history: List[str]
    iteration_count: int
    max_iterations: int
    qa_iteration_count: int      # Track coding↔qa cycles (agent-driven)
    max_qa_iterations: int       # Max agent loops before forcing user review
    user_iteration_count: int    # Track user-driven iterations (no limit)
    is_user_testing: bool        # True when user is actively testing/iterating
    
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
    
    def __init__(self, project_id: int, user_id: int, mode: PipelineMode = PipelineMode.AUTO):
        """
        Initialize orchestrator for a project.
        
        Args:
            project_id: The project ID
            user_id: The user ID
            mode: Pipeline mode (AUTO or INTERACTIVE)
        """
        self.project_id = project_id
        self.user_id = user_id
        self.mode = mode
        
        # Agent instances
        self._agents = {}
        self._activity_callback = None
        
        # Cancellation support
        self._cancelled = False
        self._current_task: Optional[asyncio.Task] = None
        
        # For interactive mode - store state at gate for resumption
        self._gate_state: Optional[ProjectState] = None
        self._pending_next_agent: Optional[str] = None
        
        # State
        self.state: ProjectState = {
            "project_id": project_id,
            "user_id": user_id,
            "status": "intake",
            "pipeline_status": PipelineStatus.IDLE,
            "pipeline_mode": mode,
            "agent_history": [],
            "iteration_count": 0,
            "max_iterations": 10,  # Increased for interactive mode
            "qa_iteration_count": 0,  # Track agent-driven coding↔qa cycles
            "max_qa_iterations": 3,   # Max agent loops before forcing user review
            "user_iteration_count": 0, # User-driven iterations have no limit
            "is_user_testing": False,  # Flag for user testing phase
            "files": {},
            "gate_artifacts": {},
            "total_tokens": 0,
            "total_cost_cents": 0.0,
            "error_history": [],
        }
        
        # Register in global registry
        _running_orchestrators[project_id] = self
        
        logger.info(f"[Orchestrator] Initialized for project {project_id} in {mode.value} mode")
    
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
    
    def is_at_gate(self) -> bool:
        """Check if pipeline is waiting at an approval gate."""
        return self.state.get("pipeline_status") == PipelineStatus.WAITING
    
    def get_gate_status(self) -> Optional[Dict[str, Any]]:
        """Get current gate status for frontend display."""
        if not self.is_at_gate():
            return None
        
        return {
            "gate": self.state.get("awaiting_approval_for"),
            "current_agent": self.state.get("current_agent"),
            "artifacts": self.state.get("gate_artifacts", {}),
            "reached_at": self.state.get("last_gate_reached_at"),
        }
    
    async def run_to_gate(self, prompt: str, start_agent: str = "nicole") -> ProjectState:
        """
        Run pipeline until it hits an approval gate (INTERACTIVE mode).
        
        This runs agents sequentially until one completes that requires approval.
        The pipeline then pauses and waits for proceed_from_gate() to continue.
        
        Args:
            prompt: User's request
            start_agent: Which agent to start with
            
        Returns:
            Current state (may be at a gate waiting for approval)
        """
        self.state["original_prompt"] = prompt
        self.state["current_prompt"] = prompt
        self.state["pipeline_status"] = PipelineStatus.RUNNING
        self.state["status"] = "planning"
        
        # Load context from memory
        await self._load_memory_context()
        
        # Update project status
        await self._update_project_status("planning")
        
        # Run until we hit a gate or complete
        return await self._run_pipeline_segment(start_agent)
    
    async def proceed_from_gate(
        self,
        approved: bool = True,
        feedback: Optional[str] = None,
        modifications: Optional[Dict[str, Any]] = None
    ) -> ProjectState:
        """
        Continue pipeline execution after user approves at a gate.
        
        Args:
            approved: Whether the user approved
            feedback: Optional user feedback
            modifications: Optional changes to apply before continuing
            
        Returns:
            Updated state (may hit another gate or complete)
        """
        if not self.is_at_gate():
            logger.warning(f"[Orchestrator] proceed_from_gate called but not at a gate")
            return self.state
        
        gate = self.state.get("awaiting_approval_for")
        
        # Log the approval/rejection
        await self._log_activity(
            "user", "approve" if approved else "reject",
            f"User {'approved' if approved else 'rejected'} at {gate}",
            {"feedback": feedback, "modifications": modifications},
            content_type="status"
        )
        
        # Store feedback in artifact if provided
        if feedback and gate:
            await self._store_gate_feedback(gate, approved, feedback)
        
        if not approved:
            # User rejected - determine what to do
            if self._pending_next_agent:
                # Go back to previous agent with feedback
                self.state["current_prompt"] = f"{self.state['original_prompt']}\n\nUser feedback: {feedback}"
                
                # Log phase transition
                await self._log_phase_transition(
                    from_phase=gate,
                    to_phase=self.state.get("current_agent"),
                    trigger="reject"
                )
            
            self.state["pipeline_status"] = PipelineStatus.RUNNING
            self.state["awaiting_approval_for"] = None
            
            # Re-run current agent with feedback
            return await self._run_pipeline_segment(self.state.get("current_agent", "nicole"))
        
        # User approved - apply any modifications
        if modifications:
            for key, value in modifications.items():
                if key in self.state:
                    self.state[key] = value
        
        # Clear gate status
        self.state["pipeline_status"] = PipelineStatus.RUNNING
        self.state["awaiting_approval_for"] = None
        
        # Log phase transition
        await self._log_phase_transition(
            from_phase=gate,
            to_phase=self._pending_next_agent,
            trigger="approve"
        )
        
        # Continue with next agent
        if self._pending_next_agent:
            return await self._run_pipeline_segment(self._pending_next_agent)
        else:
            # No next agent - pipeline complete
            return await self._finalize_pipeline()
    
    async def _run_pipeline_segment(self, start_agent: str) -> ProjectState:
        """
        Run pipeline from a given agent until completion or gate.
        
        In INTERACTIVE mode, stops at gates. In AUTO mode, runs to completion.
        """
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
            self.state["current_phase"] = current_agent
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
                    if current_agent == "coding":
                        await self._persist_files_incremental(result.files)
                
                if result.data:
                    # Merge data into state
                    for key, value in result.data.items():
                        if key not in ["files"]:
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
                        continue
                    else:
                        break
                
                # Store artifact for this agent (for review at gate)
                await self._store_agent_artifact(current_agent, result)
                
                # Check if we need to stop at a gate (INTERACTIVE mode)
                if (self.mode == PipelineMode.INTERACTIVE and 
                    current_agent in INTERACTIVE_GATES):
                    
                    gate_status = INTERACTIVE_GATES[current_agent]
                    self._pending_next_agent = result.next_agent
                    
                    # Set gate state
                    self.state["pipeline_status"] = PipelineStatus.WAITING
                    self.state["awaiting_approval_for"] = gate_status
                    self.state["last_gate_reached_at"] = datetime.utcnow().isoformat()
                    
                    # Update project with gate status
                    await self._update_project_status(gate_status)
                    
                    # Log gate reached
                    await self._log_activity(
                        "orchestrator", "gate",
                        f"Waiting for approval at {gate_status}",
                        {
                            "gate": gate_status,
                            "next_agent": result.next_agent,
                            "artifacts": list(self.state.get("gate_artifacts", {}).keys()),
                        },
                        content_type="status"
                    )
                    
                    # Return - pipeline paused at gate
                    logger.info(f"[Orchestrator] Paused at gate: {gate_status}")
                    return self.state
                
                # Determine next agent
                next_agent = result.next_agent
                
                # Track coding↔qa iterations to prevent infinite agent loops
                if current_agent == "qa" and next_agent == "coding":
                    # Skip limit if user is actively testing (user iterations have no limit)
                    if self.state.get("is_user_testing", False):
                        self.state["user_iteration_count"] = self.state.get("user_iteration_count", 0) + 1
                        logger.info(
                            f"[Orchestrator] User testing iteration {self.state['user_iteration_count']}"
                        )
                    else:
                        # Agent-driven iterations have a limit
                        self.state["qa_iteration_count"] = self.state.get("qa_iteration_count", 0) + 1
                        max_qa = self.state.get("max_qa_iterations", 3)
                        
                        if self.state["qa_iteration_count"] >= max_qa:
                            # Max agent iterations reached - enter user testing phase
                            logger.info(
                                f"[Orchestrator] Max agent QA iterations ({max_qa}) reached. "
                                f"Entering user testing phase."
                            )
                            await self._log_activity(
                                "orchestrator", "user_testing",
                                f"Agent QA iterations reached limit ({max_qa}). Ready for user testing.",
                                {"qa_iterations": self.state["qa_iteration_count"]},
                                content_type="status"
                            )
                            
                            # Mark as user testing phase - user iterations now have no limit
                            self.state["is_user_testing"] = True
                            self.state["user_iteration_count"] = 0
                            
                            # Force a gate for user testing before proceeding to review
                            self.state["pipeline_status"] = PipelineStatus.WAITING
                            self.state["awaiting_approval_for"] = "awaiting_user_testing"
                            self.state["last_gate_reached_at"] = datetime.utcnow().isoformat()
                            
                            await self._update_project_status("awaiting_user_testing")
                            
                            # Store QA summary as artifact for user to review
                            qa_summary = self.state.get("qa_review", {})
                            self.state["gate_artifacts"]["qa_report"] = json.dumps(qa_summary, indent=2)
                            
                            logger.info("[Orchestrator] Paused for user testing phase")
                            return self.state
                
                current_agent = next_agent
                
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
        
        # Pipeline segment complete - finalize if no more agents
        if not current_agent and not self._cancelled:
            return await self._finalize_pipeline()
        
        return self.state
    
    async def _finalize_pipeline(self) -> ProjectState:
        """Finalize the pipeline after all agents complete."""
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
    
    async def _store_agent_artifact(self, agent_name: str, result):
        """Store agent output as an artifact for user review."""
        try:
            artifact_type_map = {
                "nicole": "project_brief",
                "research": "research",
                "planning": "architecture",
                "design": "design_system",
                "qa": "qa_report",
                "review": "review_summary",
            }
            
            artifact_type = artifact_type_map.get(agent_name)
            if not artifact_type:
                return
            
            # Generate content based on agent
            if agent_name == "nicole":
                content = f"# Project Understanding\n\n{result.message}\n\n## Analysis\n{json.dumps(result.data, indent=2)}"
            elif agent_name == "research":
                content = f"# Research Findings\n\n{json.dumps(result.data.get('research_results', result.data), indent=2)}"
            elif agent_name == "planning":
                content = f"# Architecture Plan\n\n```json\n{json.dumps(result.data.get('architecture', result.data), indent=2)}\n```"
            elif agent_name == "design":
                content = f"# Design System\n\n```json\n{json.dumps(result.data.get('design_tokens', result.data), indent=2)}\n```"
            elif agent_name == "qa":
                content = f"# QA Report\n\n{json.dumps(result.data.get('qa_review', result.data), indent=2)}"
            elif agent_name == "review":
                content = f"# Review Summary\n\n{json.dumps(result.data.get('review_result', result.data), indent=2)}"
            else:
                content = json.dumps(result.data, indent=2)
            
            # Store in gate_artifacts for immediate access
            self.state["gate_artifacts"][artifact_type] = content
            
            # Persist to database
            await db.execute(
                """
                INSERT INTO faz_project_artifacts
                    (project_id, artifact_type, title, content, content_format, generated_by)
                VALUES ($1, $2, $3, $4, 'markdown', $5)
                ON CONFLICT (project_id, artifact_type, version)
                DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
                """,
                self.project_id,
                artifact_type,
                f"{agent_name.title()} Output",
                content,
                agent_name,
            )
            
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to store artifact for {agent_name}: {e}")
    
    async def _store_gate_feedback(self, gate: str, approved: bool, feedback: str):
        """Store user feedback for a gate."""
        try:
            artifact_type_map = {
                "awaiting_confirm": "project_brief",
                "awaiting_research_review": "research",
                "awaiting_plan_approval": "architecture",
                "awaiting_design_approval": "design_system",
                "awaiting_qa_approval": "qa_report",
                "awaiting_final_approval": "review_summary",
            }
            
            artifact_type = artifact_type_map.get(gate)
            if artifact_type:
                await db.execute(
                    """
                    UPDATE faz_project_artifacts
                    SET is_approved = $1,
                        approved_at = CASE WHEN $1 THEN NOW() ELSE NULL END,
                        user_feedback = $2,
                        updated_at = NOW()
                    WHERE project_id = $3 AND artifact_type = $4
                    """,
                    approved,
                    feedback,
                    self.project_id,
                    artifact_type,
                )
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to store gate feedback: {e}")
    
    async def _log_phase_transition(
        self,
        from_phase: Optional[str],
        to_phase: Optional[str],
        trigger: str = "auto"
    ):
        """Log a phase transition for audit trail."""
        try:
            await db.execute(
                """
                INSERT INTO faz_phase_history
                    (project_id, from_phase, to_phase, from_status, to_status,
                     triggered_by, trigger_action, tokens_used, cost_cents)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                self.project_id,
                from_phase,
                to_phase,
                self.state.get("status"),
                to_phase or "completed",
                "user" if trigger in ["approve", "reject"] else "system",
                trigger,
                self.state.get("total_tokens", 0),
                self.state.get("total_cost_cents", 0),
            )
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to log phase transition: {e}")
    
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
        
        In AUTO mode, runs to completion.
        In INTERACTIVE mode, use run_to_gate() instead.
        
        Args:
            prompt: User's request
            start_agent: Which agent to start with (default: nicole for routing)
            
        Returns:
            Final state with all generated data
        """
        # If in interactive mode, delegate to run_to_gate
        if self.mode == PipelineMode.INTERACTIVE:
            return await self.run_to_gate(prompt, start_agent)
        
        # AUTO mode - run to completion
        self.state["original_prompt"] = prompt
        self.state["current_prompt"] = prompt
        self.state["pipeline_status"] = PipelineStatus.RUNNING
        self.state["status"] = "planning"
        
        # Load context from memory
        await self._load_memory_context()
        
        # Update project status
        await self._update_project_status("planning")
        
        # Run the full pipeline
        return await self._run_pipeline_segment(start_agent)
    
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
# FACTORY FUNCTIONS
# =============================================================================

async def create_orchestrator(
    project_id: int,
    user_id: int,
    mode: Optional[PipelineMode] = None
) -> FazOrchestrator:
    """
    Create and return an orchestrator instance.
    
    Args:
        project_id: The project ID
        user_id: The user ID
        mode: Pipeline mode (if None, reads from project settings)
    """
    # If mode not specified, try to get from project
    if mode is None:
        project_mode = await db.fetchval(
            "SELECT pipeline_mode FROM faz_projects WHERE project_id = $1",
            project_id
        )
        mode = PipelineMode(project_mode) if project_mode else PipelineMode.AUTO
    
    return FazOrchestrator(project_id, user_id, mode)


async def create_interactive_orchestrator(project_id: int, user_id: int) -> FazOrchestrator:
    """Create an orchestrator in INTERACTIVE mode."""
    return FazOrchestrator(project_id, user_id, PipelineMode.INTERACTIVE)


async def resume_orchestrator(project_id: int) -> Optional[FazOrchestrator]:
    """
    Resume an existing orchestrator from database state.
    
    Used when the server restarts while a project is at a gate.
    """
    try:
        project = await db.fetchrow(
            """
            SELECT project_id, user_id, pipeline_mode, status, current_agent,
                   awaiting_approval_for, original_prompt, architecture,
                   design_tokens, total_tokens_used, total_cost_cents
            FROM faz_projects
            WHERE project_id = $1
            """,
            project_id
        )
        
        if not project:
            return None
        
        mode = PipelineMode(project["pipeline_mode"]) if project["pipeline_mode"] else PipelineMode.AUTO
        orchestrator = FazOrchestrator(project["project_id"], project["user_id"], mode)
        
        # Restore state
        orchestrator.state["original_prompt"] = project["original_prompt"] or ""
        orchestrator.state["current_prompt"] = project["original_prompt"] or ""
        orchestrator.state["status"] = project["status"]
        orchestrator.state["current_agent"] = project["current_agent"]
        orchestrator.state["awaiting_approval_for"] = project["awaiting_approval_for"]
        orchestrator.state["architecture"] = json.loads(project["architecture"]) if project["architecture"] else {}
        orchestrator.state["design_tokens"] = json.loads(project["design_tokens"]) if project["design_tokens"] else {}
        orchestrator.state["total_tokens"] = project["total_tokens_used"] or 0
        orchestrator.state["total_cost_cents"] = project["total_cost_cents"] or 0
        
        # Set pipeline status based on awaiting_approval_for
        if project["awaiting_approval_for"]:
            orchestrator.state["pipeline_status"] = PipelineStatus.WAITING
        
        # Load files
        files = await db.fetch(
            "SELECT path, content FROM faz_files WHERE project_id = $1",
            project_id
        )
        orchestrator.state["files"] = {f["path"]: f["content"] for f in files}
        
        # Load artifacts
        artifacts = await db.fetch(
            "SELECT artifact_type, content FROM faz_project_artifacts WHERE project_id = $1",
            project_id
        )
        orchestrator.state["gate_artifacts"] = {a["artifact_type"]: a["content"] for a in artifacts}
        
        logger.info(f"[Orchestrator] Resumed orchestrator for project {project_id}")
        return orchestrator
        
    except Exception as e:
        logger.error(f"[Orchestrator] Failed to resume orchestrator: {e}")
        return None


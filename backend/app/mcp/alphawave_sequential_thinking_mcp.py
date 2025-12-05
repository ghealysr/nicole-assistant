"""
Sequential Thinking MCP Integration for Nicole V7

Provides structured reasoning visualization for complex problem-solving.
Works in conjunction with the Think Tool for explicit reasoning display.

Features:
- Step-by-step reasoning display
- Thought branching and exploration
- Conclusion tracking
- Reasoning chain visualization
"""

from typing import Any, Dict, List, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime

from app.mcp.alphawave_mcp_manager import mcp_manager, AlphawaveMCPManager

logger = logging.getLogger(__name__)


@dataclass
class ThinkingStep:
    """Represents a single step in a thinking chain."""
    step_number: int
    thought: str
    category: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    branches: List['ThinkingStep'] = field(default_factory=list)
    conclusion: Optional[str] = None


@dataclass
class ThinkingSession:
    """A complete thinking session with all steps."""
    session_id: str
    user_id: int
    conversation_id: int
    started_at: datetime = field(default_factory=datetime.utcnow)
    steps: List[ThinkingStep] = field(default_factory=list)
    final_conclusion: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    def add_step(
        self,
        thought: str,
        category: str = "analysis",
        conclusion: Optional[str] = None
    ) -> ThinkingStep:
        """Add a new thinking step."""
        step = ThinkingStep(
            step_number=len(self.steps) + 1,
            thought=thought,
            category=category,
            conclusion=conclusion
        )
        self.steps.append(step)
        return step
    
    def get_summary(self) -> str:
        """Get a summary of the thinking session."""
        if not self.steps:
            return "No thinking steps recorded."
        
        summary_parts = [f"Thinking session with {len(self.steps)} steps:"]
        
        for step in self.steps:
            summary_parts.append(f"{step.step_number}. [{step.category}] {step.thought[:100]}...")
        
        if self.final_conclusion:
            summary_parts.append(f"\nConclusion: {self.final_conclusion}")
        
        return "\n".join(summary_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [
                {
                    "step_number": s.step_number,
                    "thought": s.thought,
                    "category": s.category,
                    "timestamp": s.timestamp.isoformat(),
                    "conclusion": s.conclusion
                }
                for s in self.steps
            ],
            "final_conclusion": self.final_conclusion,
            "step_count": len(self.steps)
        }


class AlphawaveSequentialThinkingMCP:
    """
    Sequential Thinking MCP integration.
    
    Provides structured reasoning capabilities:
    - Create thinking sessions
    - Record thinking steps
    - Track reasoning chains
    - Visualize thought process
    """
    
    SERVER_NAME = "sequential-thinking"
    
    def __init__(self):
        """Initialize Sequential Thinking MCP."""
        self._sessions: Dict[str, ThinkingSession] = {}
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if Sequential Thinking MCP is available."""
        # This can work without MCP via local implementation
        return True
    
    async def connect(self) -> bool:
        """
        Connect to Sequential Thinking MCP server.
        
        Note: This MCP is optional - local fallback is available.
        
        Returns:
            True (always available via fallback)
        """
        if isinstance(mcp_manager, AlphawaveMCPManager):
            # Try to connect to MCP server
            self._connected = await mcp_manager.connect_server(self.SERVER_NAME)
            if self._connected:
                logger.info("[Sequential Thinking] Connected to MCP server")
                return True
        
        # Fallback to local implementation
        self._connected = True
        logger.info("[Sequential Thinking] Using local implementation")
        return True
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def start_session(
        self,
        session_id: str,
        user_id: int,
        conversation_id: int
    ) -> ThinkingSession:
        """
        Start a new thinking session.
        
        Args:
            session_id: Unique session identifier
            user_id: User ID
            conversation_id: Conversation ID
            
        Returns:
            New thinking session
        """
        session = ThinkingSession(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id
        )
        self._sessions[session_id] = session
        
        logger.debug(f"[Sequential Thinking] Started session {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ThinkingSession]:
        """Get an existing thinking session."""
        return self._sessions.get(session_id)
    
    def complete_session(
        self,
        session_id: str,
        conclusion: Optional[str] = None
    ) -> Optional[ThinkingSession]:
        """
        Complete a thinking session.
        
        Args:
            session_id: Session to complete
            conclusion: Optional final conclusion
            
        Returns:
            Completed session
        """
        session = self._sessions.get(session_id)
        if session:
            session.final_conclusion = conclusion
            session.completed_at = datetime.utcnow()
            logger.debug(f"[Sequential Thinking] Completed session {session_id}")
        return session
    
    def cleanup_session(self, session_id: str) -> None:
        """Remove a session from memory."""
        self._sessions.pop(session_id, None)
    
    # =========================================================================
    # THINKING OPERATIONS
    # =========================================================================
    
    def record_thought(
        self,
        session_id: str,
        thought: str,
        category: str = "analysis",
        conclusion: Optional[str] = None
    ) -> Optional[ThinkingStep]:
        """
        Record a thinking step in a session.
        
        Args:
            session_id: Session to add to
            thought: The thought/reasoning content
            category: Category of thought (analysis, planning, evaluation, etc.)
            conclusion: Optional conclusion from this step
            
        Returns:
            Created thinking step
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"[Sequential Thinking] Session not found: {session_id}")
            return None
        
        step = session.add_step(thought, category, conclusion)
        logger.debug(f"[Sequential Thinking] Recorded step {step.step_number}")
        return step
    
    async def analyze_with_steps(
        self,
        session_id: str,
        problem: str,
        approach: str = "systematic"
    ) -> Dict[str, Any]:
        """
        Perform structured analysis with automatic step recording.
        
        If MCP server is connected, uses server for analysis.
        Otherwise, provides framework for Claude to fill in.
        
        Args:
            session_id: Session for this analysis
            problem: Problem to analyze
            approach: Analysis approach (systematic, creative, comparative)
            
        Returns:
            Analysis structure
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # If connected to MCP server, use it
        if isinstance(mcp_manager, AlphawaveMCPManager) and self._connected:
            result = await mcp_manager.call_tool(
                "sequential_thinking",
                {
                    "problem": problem,
                    "approach": approach,
                    "session_id": session_id
                }
            )
            return result
        
        # Local framework for Claude to use
        return {
            "session_id": session_id,
            "problem": problem,
            "approach": approach,
            "framework": {
                "steps": [
                    {"name": "understand", "prompt": "What is the core problem?"},
                    {"name": "decompose", "prompt": "What are the sub-components?"},
                    {"name": "analyze", "prompt": "What are the key factors?"},
                    {"name": "synthesize", "prompt": "What conclusions can we draw?"},
                    {"name": "recommend", "prompt": "What actions should be taken?"}
                ],
                "instruction": "Use the think tool to work through each step"
            }
        }
    
    # =========================================================================
    # VISUALIZATION
    # =========================================================================
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of a thinking session for display."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return session.to_dict()
    
    def get_thinking_chain(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the thinking chain for visualization.
        
        Returns a list of steps formatted for frontend display.
        """
        session = self._sessions.get(session_id)
        if not session:
            return []
        
        return [
            {
                "step": s.step_number,
                "thought": s.thought,
                "category": s.category,
                "hasConclusion": s.conclusion is not None,
                "conclusion": s.conclusion
            }
            for s in session.steps
        ]
    
    def get_active_sessions_count(self) -> int:
        """Get count of active thinking sessions."""
        return len(self._sessions)
    
    def cleanup_old_sessions(self, max_age_minutes: int = 60) -> int:
        """
        Cleanup old sessions.
        
        Args:
            max_age_minutes: Maximum age for sessions
            
        Returns:
            Number of sessions cleaned up
        """
        cutoff = datetime.utcnow()
        old_sessions = [
            sid for sid, session in self._sessions.items()
            if (cutoff - session.started_at).total_seconds() > max_age_minutes * 60
        ]
        
        for sid in old_sessions:
            del self._sessions[sid]
        
        return len(old_sessions)


# Global instance
sequential_thinking_mcp = AlphawaveSequentialThinkingMCP()


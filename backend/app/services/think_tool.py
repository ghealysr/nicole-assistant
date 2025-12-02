"""
Nicole V7 - Think Tool Service

Implements Anthropic's Think Tool pattern for explicit reasoning during complex operations.

The Think Tool allows Nicole to pause and reason through decisions explicitly,
rather than making implicit jumps. This is different from Extended Thinking
(which happens before response) - Think Tool happens DURING response, between
tool calls.

Usage:
    Nicole can call the think tool to reason through:
    - Complex multi-step tool chains
    - Policy-heavy decisions (content filtering, safety)
    - Sequential decisions where mistakes are costly
    - Ambiguous user requests that need clarification

Example:
    User: "Send an email to my team about the meeting"
    Nicole thinks: "Let me consider what information I need:
        1. Who is 'my team'? Need to check memory for team members
        2. What meeting? Check calendar or ask for clarification
        3. What should the email say? User didn't specify
        Decision: Ask user for meeting details before proceeding"

Impact: 54% improvement on complex multi-step tasks (Anthropic benchmark)

Author: Nicole V7 Architecture
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ThinkingCategory(str, Enum):
    """Categories of thinking for analysis and debugging."""
    TOOL_SELECTION = "tool_selection"      # Deciding which tool to use
    PARAMETER_PLANNING = "parameter_planning"  # Planning tool parameters
    RESULT_ANALYSIS = "result_analysis"    # Analyzing tool results
    SAFETY_CHECK = "safety_check"          # Content/safety decisions
    CLARIFICATION = "clarification"        # Deciding to ask user
    MEMORY_INTEGRATION = "memory_integration"  # Incorporating memories
    MULTI_STEP_PLANNING = "multi_step_planning"  # Planning complex workflows
    ERROR_RECOVERY = "error_recovery"      # Handling errors/retries


@dataclass
class ThinkingStep:
    """A single thinking step with metadata."""
    thought: str
    category: ThinkingCategory
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Optional[Dict[str, Any]] = None
    conclusion: Optional[str] = None
    confidence: float = 1.0  # 0-1 confidence in this reasoning


@dataclass
class ThinkingSession:
    """A session of thinking steps for a single request."""
    session_id: str
    user_id: int
    conversation_id: int
    steps: List[ThinkingStep] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def add_step(self, step: ThinkingStep) -> None:
        """Add a thinking step to this session."""
        self.steps.append(step)
    
    def get_summary(self) -> str:
        """Get a summary of all thinking steps."""
        if not self.steps:
            return "No thinking steps recorded."
        
        summary_parts = []
        for i, step in enumerate(self.steps, 1):
            summary_parts.append(f"{i}. [{step.category.value}] {step.thought[:100]}...")
            if step.conclusion:
                summary_parts.append(f"   → Conclusion: {step.conclusion}")
        
        return "\n".join(summary_parts)
    
    def complete(self) -> None:
        """Mark this thinking session as complete."""
        self.completed_at = datetime.utcnow()


# The Think Tool definition for Claude
THINK_TOOL_DEFINITION = {
    "name": "think",
    "description": """Use this tool to reason through complex decisions step by step.

WHEN TO USE:
- Before making a multi-step tool chain (e.g., search memory, then search documents, then generate response)
- When a user request is ambiguous and you need to decide whether to ask for clarification
- When applying content safety policies or making sensitive decisions
- When analyzing results from previous tool calls to decide next steps
- When integrating information from memory with current context

HOW TO USE:
Call this tool with your reasoning process. Be explicit about:
1. What you're trying to decide
2. What information you have
3. What information you're missing
4. Your conclusion and next action

This tool does NOT execute any actions - it only records your reasoning.
After thinking, you should take the appropriate action or respond to the user.

EXAMPLES:
- "I need to send an email but the user didn't specify recipients. Let me check memory for their team members, or ask for clarification if not found."
- "The user asked about 'the project' - I see 3 projects in memory. I should ask which one they mean."
- "This request involves financial advice. According to my guidelines, I should provide general information but recommend consulting a professional."
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Your detailed reasoning process. Be explicit about what you're considering and why."
            },
            "category": {
                "type": "string",
                "enum": [c.value for c in ThinkingCategory],
                "description": "The category of thinking this represents."
            },
            "conclusion": {
                "type": "string",
                "description": "Optional: Your conclusion or decision after this thinking step."
            }
        },
        "required": ["thought"]
    }
}


class ThinkToolService:
    """
    Service for managing Nicole's explicit thinking during complex operations.
    
    This service:
    1. Provides the Think Tool definition for Claude
    2. Records thinking steps for debugging and analysis
    3. Enables thinking step emission via SSE for frontend display
    4. Tracks thinking patterns for system improvement
    """
    
    def __init__(self):
        self._active_sessions: Dict[str, ThinkingSession] = {}
        logger.info("[THINK] Think Tool Service initialized")
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get the Think Tool definition for Claude."""
        return THINK_TOOL_DEFINITION
    
    def start_session(
        self,
        session_id: str,
        user_id: int,
        conversation_id: int
    ) -> ThinkingSession:
        """Start a new thinking session for a request."""
        session = ThinkingSession(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id
        )
        self._active_sessions[session_id] = session
        logger.debug(f"[THINK] Started session {session_id}")
        return session
    
    def record_thought(
        self,
        session_id: str,
        thought: str,
        category: Optional[str] = None,
        conclusion: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0
    ) -> Optional[ThinkingStep]:
        """
        Record a thinking step from Claude's think tool call.
        
        Args:
            session_id: The session to record to
            thought: The reasoning text
            category: Category of thinking (defaults to multi_step_planning)
            conclusion: Optional conclusion
            context: Optional context data
            confidence: Confidence level (0-1)
            
        Returns:
            The recorded ThinkingStep, or None if session not found
        """
        session = self._active_sessions.get(session_id)
        if not session:
            logger.warning(f"[THINK] Session {session_id} not found")
            return None
        
        # Parse category
        try:
            cat = ThinkingCategory(category) if category else ThinkingCategory.MULTI_STEP_PLANNING
        except ValueError:
            cat = ThinkingCategory.MULTI_STEP_PLANNING
        
        step = ThinkingStep(
            thought=thought,
            category=cat,
            conclusion=conclusion,
            context=context,
            confidence=confidence
        )
        
        session.add_step(step)
        logger.info(f"[THINK] Recorded [{cat.value}]: {thought[:80]}...")
        
        return step
    
    def get_session(self, session_id: str) -> Optional[ThinkingSession]:
        """Get an active thinking session."""
        return self._active_sessions.get(session_id)
    
    def complete_session(self, session_id: str) -> Optional[ThinkingSession]:
        """Complete and remove a thinking session."""
        session = self._active_sessions.pop(session_id, None)
        if session:
            session.complete()
            logger.info(f"[THINK] Session {session_id} completed with {len(session.steps)} steps")
        return session
    
    def format_for_sse(self, step: ThinkingStep) -> Dict[str, Any]:
        """Format a thinking step for SSE emission."""
        return {
            "type": "thinking_step",
            "description": step.thought[:200] + ("..." if len(step.thought) > 200 else ""),
            "category": step.category.value,
            "status": "complete",
            "conclusion": step.conclusion,
            "timestamp": step.timestamp.isoformat()
        }
    
    def get_prompt_injection(self) -> str:
        """
        Get the system prompt injection that tells Nicole about the think tool.
        
        This should be added to Nicole's system prompt to enable thinking.
        """
        return """
## 🧠 THINK TOOL

You have access to a special `think` tool for explicit reasoning. Use it when:

1. **Before multi-step operations**: Think through the sequence before starting
2. **Ambiguous requests**: Reason about whether to ask for clarification
3. **Safety decisions**: Explicitly reason through content policies
4. **Complex tool chains**: Plan which tools to use and in what order
5. **Error recovery**: Reason through what went wrong and how to fix it

The think tool does NOT execute actions - it only records your reasoning process.
After thinking, you should take the appropriate action.

Example:
```
<think>
The user asked me to "send the report to the team." Let me consider:
1. Which report? I see 3 recent reports in memory: Q3 Financial, Marketing, Project Status
2. Who is "the team"? Memory shows 5 team members from the AlphaWave project
3. How to send? Email seems appropriate

Conclusion: I should ask the user which report they mean, then confirm the recipient list.
</think>
```

Use thinking liberally - it improves your accuracy significantly.
"""


# Global service instance
think_tool_service = ThinkToolService()


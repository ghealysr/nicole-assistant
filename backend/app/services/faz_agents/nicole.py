"""
Nicole - Faz Code Orchestrator Agent

Routes user intent to appropriate agents and manages the pipeline flow.
Uses Claude Opus 4.5 for complex reasoning and intent analysis.
"""

from typing import Any, Dict, List
import json
import logging

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class NicoleAgent(BaseAgent):
    """
    Nicole is the orchestrator - she analyzes user intent and routes to the right agent.
    
    Responsibilities:
    - Analyze user prompts for intent
    - Determine which agent should handle the request
    - Manage handoffs between agents
    - Resolve conflicts and errors
    - Communicate with user
    """
    
    agent_id = "nicole"
    agent_name = "Nicole"
    agent_role = "Orchestrator - Routes requests and manages the agent pipeline"
    model_provider = "anthropic"
    model_name = "claude-opus-4-5-20251101"
    temperature = 0.7
    max_tokens = 2048
    
    capabilities = [
        "routing",
        "intent_analysis",
        "conflict_resolution",
        "user_communication",
        "pipeline_management"
    ]
    
    valid_handoff_targets = ["planning", "research", "design", "coding", "qa", "review"]
    receives_handoffs_from = []  # Nicole is the entry point
    
    def _get_system_prompt(self) -> str:
        return """You are Nicole, the Creative Director and Orchestrator for Faz Code.

## YOUR ROLE
You analyze user prompts and route them to the appropriate agent. You're the first point of contact and manage the entire pipeline.

## AVAILABLE AGENTS
- **planning**: Creates architecture, file structure, component breakdown. Use for new projects or major changes.
- **research**: Web search, competitor analysis, design inspiration. Use when user wants to see examples or trends.
- **design**: Color palettes, typography, design tokens. Use when user needs visual direction.
- **coding**: Code generation, file creation. Use for implementation.
- **qa**: Quality checks, Lighthouse audits. Use after code is generated.
- **review**: Final approval, code review. Use before deployment.

## YOUR TASK
Analyze the user's prompt and decide:
1. Which agent should handle this?
2. What should that agent focus on?

## OUTPUT FORMAT
Respond with JSON:
```json
{
  "intent": "brief description of what user wants",
  "next_agent": "planning|research|design|coding|qa|review",
  "agent_instructions": "specific instructions for the next agent",
  "user_message": "friendly message to show the user about what's happening"
}
```

## ROUTING LOGIC
- New project or "build me a..." → planning
- "Show me examples" or "what's trending" → research
- "Make it look..." or "change colors" → design
- "Add a feature" or "fix this" on existing project → coding
- "Check quality" or "run tests" → qa
- "Review" or "is this ready?" → review

Always be helpful and explain what you're doing."""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for Nicole's routing decision."""
        prompt_parts = []
        
        # User's current request
        prompt_parts.append(f"## USER REQUEST\n{state.get('current_prompt', state.get('original_prompt', ''))}")
        
        # Project context if exists
        if state.get("project_id"):
            prompt_parts.append(f"\n## PROJECT CONTEXT\n- Project ID: {state['project_id']}")
            
            if state.get("status"):
                prompt_parts.append(f"- Current status: {state['status']}")
            
            if state.get("architecture"):
                prompt_parts.append(f"- Has architecture: Yes")
                
            if state.get("files"):
                file_count = len(state["files"]) if isinstance(state["files"], dict) else 0
                prompt_parts.append(f"- Generated files: {file_count}")
        
        # Agent history
        if state.get("agent_history"):
            prompt_parts.append(f"\n## PREVIOUS AGENTS\n{' → '.join(state['agent_history'][-5:])}")
        
        # Any errors to handle
        if state.get("error"):
            prompt_parts.append(f"\n## ERROR TO HANDLE\n{state['error']}")
        
        prompt_parts.append("\n## YOUR TASK\nAnalyze the request and route to the appropriate agent.")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse Nicole's routing decision."""
        try:
            # Extract JSON from response
            data = self.extract_json(response)
            
            if not data:
                # Fallback: try to determine intent from text
                response_lower = response.lower()
                if "planning" in response_lower or "architect" in response_lower:
                    next_agent = "planning"
                elif "research" in response_lower or "search" in response_lower:
                    next_agent = "research"
                elif "design" in response_lower or "color" in response_lower:
                    next_agent = "design"
                elif "coding" in response_lower or "code" in response_lower or "build" in response_lower:
                    next_agent = "coding"
                elif "qa" in response_lower or "quality" in response_lower or "test" in response_lower:
                    next_agent = "qa"
                elif "review" in response_lower or "approve" in response_lower:
                    next_agent = "review"
                else:
                    next_agent = "planning"  # Default to planning for new requests
                
                data = {
                    "intent": "User request",
                    "next_agent": next_agent,
                    "agent_instructions": state.get("current_prompt", ""),
                    "user_message": f"I'm routing this to the {next_agent} agent."
                }
            
            next_agent = data.get("next_agent", "planning")
            
            # Validate agent
            if next_agent not in self.valid_handoff_targets:
                next_agent = "planning"
            
            return AgentResult(
                success=True,
                message=data.get("user_message", f"Routing to {next_agent}"),
                data={
                    "intent": data.get("intent", ""),
                    "agent_instructions": data.get("agent_instructions", ""),
                    "routing_decision": next_agent,
                },
                next_agent=next_agent,
            )
            
        except Exception as e:
            logger.error(f"[Nicole] Failed to parse response: {e}")
            # Default to planning on error
            return AgentResult(
                success=True,
                message="Starting with project planning",
                data={"routing_decision": "planning"},
                next_agent="planning",
            )


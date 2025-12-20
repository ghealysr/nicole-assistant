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
    
    valid_handoff_targets = ["planning", "design", "coding", "qa", "review"]  # research is handled via planning
    receives_handoffs_from = []  # Nicole is the entry point
    
    def _get_system_prompt(self) -> str:
        return """You are Nicole, the Creative Director and Orchestrator for Faz Code.

## YOUR ROLE
You analyze user prompts and extract clear requirements. You're the first point of contact and set the stage for the entire pipeline.

## PIPELINE FLOW
The standard pipeline for new websites is:
  Nicole (you) → Planning → Research → Design → Coding → QA → Review → Deploy

For new projects, ALWAYS start with **planning** to create architecture first.
Research and Design happen after Planning to be informed by the architecture.

## AVAILABLE AGENTS
- **planning**: Creates architecture, file structure, tech stack, component breakdown. ALWAYS use for new projects.
- **research**: Gathers design inspiration, competitor analysis, trends. Use AFTER planning for design research.
- **design**: Creates color palettes, typography, design tokens. Follows research recommendations.
- **coding**: Generates production-ready code. Implements the architecture.
- **qa**: Reviews code quality, accessibility, performance. Catches issues before deployment.
- **review**: Final approval gate. Ensures business requirements are met.

## YOUR TASK
1. Understand what the user wants to build
2. Extract key requirements (industry, style, features)
3. Create a clear brief for the Planning agent

## OUTPUT FORMAT
```json
{
  "intent": "clear summary of what user wants",
  "project_type": "landing_page|portfolio|saas|ecommerce|blog|agency|other",
  "key_requirements": ["requirement 1", "requirement 2"],
  "style_hints": "any style preferences mentioned",
  "next_agent": "planning",
  "agent_instructions": "detailed brief for the planning agent",
  "user_message": "friendly message confirming understanding"
}
```

## ROUTING LOGIC
- ANY new project request → planning (ALWAYS start here)
- "Show me examples" or research request → research (skip for now, planning first)
- "Change colors/fonts" on existing project → design
- "Add feature" or "fix bug" on existing project → coding
- "Check quality" or "run tests" → qa
- "Review this" or "is it ready?" → review

For new projects, you MUST route to planning first. The architecture informs everything else."""
    
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


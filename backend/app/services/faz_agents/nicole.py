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
You're an expert web developer and creative director who helps users build beautiful, professional websites. You don't just route requests - you DISCUSS, PLAN, and COLLABORATE with the user.

## YOUR PERSONALITY
- Professional but friendly - like a senior creative director at a top agency
- You ask clarifying questions when needed
- You present plans and wait for approval before proceeding
- You explain what you're doing and why
- You understand what makes websites great (UX, design, performance, accessibility)

## AVAILABLE AGENTS (your team)
- **planning**: Creates architecture, file structure, technical blueprint. Use for new projects.
- **research**: Competitor analysis, design inspiration, industry trends.
- **design**: Visual design system, colors, typography, layout.
- **coding**: Code generation using Sonnet (expert coder).
- **qa**: Quality testing, accessibility, Lighthouse audits.
- **review**: Final review before deployment.

## HOW YOU WORK
1. **UNDERSTAND**: When a user says "build me a baseball website", don't just route. Think about what a GREAT baseball website needs: schedule, roster, stats, news, tickets, etc.

2. **PROPOSE**: Present a brief plan to the user. Example:
   "I'd love to help build your baseball website! Here's what I'm thinking:
   - **Homepage**: Hero with team branding, upcoming games, latest news
   - **Schedule**: Interactive game calendar with buy tickets CTAs
   - **Roster**: Player cards with stats and photos
   - **About**: Team history, stadium info
   
   Does this sound right, or would you like to focus on specific areas?"

3. **CONFIRM**: Wait for user confirmation before proceeding to planning agent.

4. **EXECUTE**: Route to the right agent with clear instructions.

## OUTPUT FORMAT
Respond with JSON:
```json
{
  "intent": "brief description of what user wants",
  "next_agent": "planning|research|design|coding|qa|review|none",
  "agent_instructions": "specific instructions for the next agent",
  "user_message": "conversational message presenting your thoughts and plan",
  "needs_approval": true|false,
  "questions": ["optional clarifying questions"]
}
```

Use `"next_agent": "none"` and `"needs_approval": true` when you want to discuss with the user first.

## ROUTING LOGIC
- New project: FIRST discuss the plan with user, THEN route to planning
- "Show me examples" or inspiration → research
- "Change the colors/fonts" → design
- "Add a feature" or "fix this" → coding
- "Check quality" → qa
- "Review" or "deploy" → review

## REMEMBER
- You're building WITH the user, not FOR them
- Present plans, ask for feedback, iterate
- Every great website starts with understanding the user's vision"""
    
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


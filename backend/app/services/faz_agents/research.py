"""
Research Agent - Faz Code Analyst

Gathers design inspiration, competitor analysis, and current trends.
Uses Gemini 3 Pro with web search grounding.
"""

from typing import Any, Dict
import json
import logging

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """
    The Research Agent gathers inspiration and analyzes competitors.
    
    Responsibilities:
    - Web search for design trends
    - Screenshot competitor sites
    - Gather inspiration images
    - Analyze industry patterns
    """
    
    agent_id = "research"
    agent_name = "Research Agent"
    agent_role = "Analyst - Gathers design inspiration and competitor insights"
    model_provider = "google"
    model_name = "gemini-2.5-pro-preview-05-06"
    temperature = 0.7
    max_tokens = 4096
    
    capabilities = [
        "web_search",
        "competitor_analysis",
        "design_inspiration",
        "trend_detection",
        "screenshot_analysis"
    ]
    
    available_tools = ["brave_web_search", "puppeteer_screenshot", "puppeteer_navigate"]
    valid_handoff_targets = ["planning", "design"]
    receives_handoffs_from = ["nicole"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Research Agent for Faz Code, an expert design analyst.

## YOUR ROLE
Research design trends, analyze competitors, and gather inspiration for web projects.

## PROCESS
1. Identify the industry/niche from the user request
2. Search for current design trends in that space
3. Find 2-3 competitor or inspiration sites
4. Note key design patterns and elements

## OUTPUT FORMAT
```json
{
  "industry": "e-commerce|saas|portfolio|agency|etc",
  "trends": [
    "trend 1 description",
    "trend 2 description"
  ],
  "inspiration_sites": [
    {
      "url": "https://example.com",
      "what_works": "description of notable design elements",
      "relevant_for": "which aspects to consider"
    }
  ],
  "color_recommendations": {
    "palette_type": "warm|cool|neutral|bold",
    "suggested_colors": ["#hex1", "#hex2", "#hex3"],
    "reasoning": "why these colors work for this industry"
  },
  "typography_recommendations": {
    "heading_style": "modern|classic|playful|professional",
    "suggested_fonts": ["Font1", "Font2"],
    "reasoning": "why these fonts work"
  },
  "key_patterns": [
    "pattern 1 to incorporate",
    "pattern 2 to incorporate"
  ],
  "summary": "Brief summary of research findings"
}
```

## HANDOFF
After research, hand off to:
- **design**: To create detailed design tokens (default)
- **planning**: If user needs full architecture"""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for research."""
        prompt_parts = []
        
        original = state.get("original_prompt", state.get("current_prompt", ""))
        prompt_parts.append(f"## PROJECT REQUEST\n{original}")
        
        if state.get("data", {}).get("agent_instructions"):
            prompt_parts.append(f"\n## ORCHESTRATOR INSTRUCTIONS\n{state['data']['agent_instructions']}")
        
        prompt_parts.append("""
## YOUR TASK
1. Identify the industry/type of website needed
2. Research current design trends for this industry
3. Find inspiring examples
4. Recommend colors, typography, and patterns
5. Output your findings as JSON""")
        
        return "\n".join(prompt_parts)
    
    async def run(self, state: Dict[str, Any]) -> AgentResult:
        """Run research with web search."""
        try:
            # First, do a web search for trends
            original = state.get("original_prompt", "")
            
            # Extract industry from prompt
            search_query = f"{original} website design trends 2025"
            
            logger.info(f"[Research] Searching: {search_query}")
            
            # Call web search tool
            search_result = await self.call_tool("brave_web_search", {"query": search_query, "count": 5})
            
            search_context = ""
            if search_result.get("content"):
                search_context = f"\n## WEB SEARCH RESULTS\n{search_result['content'][:3000]}"
            
            # Build prompt with search results
            prompt = self._build_prompt(state) + search_context
            system_prompt = self._get_system_prompt()
            
            # Call LLM to analyze
            response, input_tokens, output_tokens = await self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                state=state
            )
            
            # Parse response
            result = self._parse_response(response, state)
            
            # Add token tracking
            from .base_agent import MODEL_PRICING
            pricing = MODEL_PRICING.get(self.model_name, {"input": 0, "output": 0})
            cost_cents = (
                (input_tokens / 1000) * pricing["input"] +
                (output_tokens / 1000) * pricing["output"]
            ) * 100
            
            result.input_tokens = input_tokens
            result.output_tokens = output_tokens
            result.cost_cents = cost_cents
            
            return result
            
        except Exception as e:
            logger.exception(f"[Research] Error: {e}")
            return AgentResult(
                success=False,
                message="Research failed",
                error=str(e),
            )
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse research findings."""
        try:
            data = self.extract_json(response)
            
            if not data:
                # Create minimal result from text
                data = {
                    "summary": response[:500],
                    "trends": [],
                    "inspiration_sites": [],
                }
            
            return AgentResult(
                success=True,
                message=f"Research complete: {data.get('summary', 'Findings gathered')[:200]}",
                data={
                    "research_results": data,
                    "industry": data.get("industry", "general"),
                    "trends": data.get("trends", []),
                    "color_recommendations": data.get("color_recommendations", {}),
                    "typography_recommendations": data.get("typography_recommendations", {}),
                },
                next_agent="design",
            )
            
        except Exception as e:
            logger.error(f"[Research] Parse error: {e}")
            return AgentResult(
                success=False,
                message="Failed to parse research",
                error=str(e),
            )


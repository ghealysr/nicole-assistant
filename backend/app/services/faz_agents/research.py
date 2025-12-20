"""
Research Agent - Faz Code Analyst

Gathers design inspiration, competitor analysis, and current trends.
Uses Gemini 3 Pro with web search grounding.
Enhanced with competitor screenshot capture for visual reference.
"""

from typing import Any, Dict, List, Optional
import json
import logging

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Try to import screenshot service for competitor analysis
try:
    from app.services.faz_screenshot_service import screenshot_service, PLAYWRIGHT_AVAILABLE
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    screenshot_service = None


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
    model_name = "gemini-3-pro-preview"
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
    valid_handoff_targets = ["design"]
    receives_handoffs_from = ["nicole", "planning"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Research Agent for Faz Code, an expert design analyst powered by Gemini 3 Pro.

## YOUR ROLE
Gather design inspiration and competitive insights to inform the Design Agent. You have web search capabilities.

## CONTEXT
You receive the project ARCHITECTURE from the Planning Agent. Use this to:
- Search for designs in the specific industry
- Find competitor sites that match the project's target audience
- Recommend colors and typography appropriate for the business type

## PROCESS
1. Review the architecture to understand the project type and audience
2. Search for current design trends in that industry (2025)
3. Find 2-3 high-quality inspiration sites
4. Recommend specific colors and fonts that match the brand goals

## OUTPUT FORMAT
```json
{
  "industry": "identified industry/niche",
  "target_audience": "who the site is for",
  "trends": [
    "trend 1 with specific details",
    "trend 2 with specific details"
  ],
  "inspiration_sites": [
    {
      "url": "https://example.com",
      "what_works": "specific design elements to emulate",
      "relevant_for": "which components this inspires"
    }
  ],
  "color_recommendations": {
    "palette_type": "warm|cool|neutral|bold|gradient",
    "primary": "#hex with name",
    "secondary": "#hex with name",
    "accent": "#hex with name",
    "reasoning": "why these colors work for this brand/industry"
  },
  "typography_recommendations": {
    "heading_font": "Google Font name",
    "body_font": "Google Font name",
    "style": "modern|classic|playful|professional|minimalist",
    "reasoning": "why these fonts match the brand"
  },
  "key_patterns": [
    "specific pattern with implementation notes",
    "specific pattern with implementation notes"
  ],
  "summary": "Brief summary for the Design Agent"
}
```

## HANDOFF
After research, hand off to **design** with your recommendations."""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for research with architecture context."""
        prompt_parts = []
        
        original = state.get("original_prompt", state.get("current_prompt", ""))
        prompt_parts.append(f"## PROJECT REQUEST\n{original}")
        
        # Include architecture from Planning agent
        architecture = state.get("architecture") or state.get("data", {}).get("architecture")
        if architecture:
            prompt_parts.append(f"\n## PROJECT ARCHITECTURE")
            if architecture.get("project_summary"):
                prompt_parts.append(f"**Project**: {json.dumps(architecture['project_summary'], indent=2)}")
            if architecture.get("tech_stack"):
                prompt_parts.append(f"**Tech Stack**: {json.dumps(architecture['tech_stack'], indent=2)}")
            if architecture.get("pages"):
                page_names = [p.get("name", p.get("path", "")) for p in architecture["pages"][:5]]
                prompt_parts.append(f"**Pages**: {', '.join(page_names)}")
            if architecture.get("components"):
                comp_names = [c.get("name", "") for c in architecture["components"][:10]]
                prompt_parts.append(f"**Components**: {', '.join(comp_names)}")
        
        if state.get("data", {}).get("agent_instructions"):
            prompt_parts.append(f"\n## ORCHESTRATOR INSTRUCTIONS\n{state['data']['agent_instructions']}")
        
        prompt_parts.append("""
## YOUR TASK
Based on the architecture above:
1. Identify the industry and target audience
2. Search for 2025 design trends in this space
3. Find 2-3 high-quality inspiration sites
4. Recommend specific colors and Google Fonts
5. Identify design patterns for the key components
6. Output your findings as JSON for the Design Agent""")
        
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
    
    async def capture_competitor_screenshots(
        self,
        urls: List[str],
        viewport: str = "desktop",
    ) -> List[Dict[str, Any]]:
        """
        Capture screenshots of competitor/inspiration websites.
        
        Args:
            urls: List of URLs to screenshot
            viewport: Viewport size for captures
            
        Returns:
            List of screenshot results
        """
        if not PLAYWRIGHT_AVAILABLE or not screenshot_service:
            logger.warning("[Research] Screenshot capture not available")
            return []
        
        results = []
        
        for url in urls[:5]:  # Limit to 5 sites
            try:
                result = await screenshot_service.capture_url(
                    url,
                    viewport=viewport,
                    wait_time_ms=3000,  # Wait for JS to load
                )
                
                if result.get("success"):
                    results.append({
                        "url": url,
                        "success": True,
                        "image_base64": result.get("image_base64"),
                        "width": result.get("width"),
                        "height": result.get("height"),
                    })
                    logger.info(f"[Research] Captured screenshot: {url}")
                else:
                    results.append({
                        "url": url,
                        "success": False,
                        "error": result.get("error"),
                    })
                    
            except Exception as e:
                logger.warning(f"[Research] Failed to capture {url}: {e}")
                results.append({
                    "url": url,
                    "success": False,
                    "error": str(e),
                })
        
        return results
    
    async def run_with_screenshots(
        self,
        state: Dict[str, Any],
        capture_inspirations: bool = True,
    ) -> AgentResult:
        """
        Run research with competitor screenshot capture.
        
        Extends standard run() with visual inspiration gathering.
        """
        # Run standard research first
        result = await self.run(state)
        
        # If successful and screenshots enabled, capture inspiration sites
        if result.success and capture_inspirations and PLAYWRIGHT_AVAILABLE:
            inspiration_sites = result.data.get("research_results", {}).get("inspiration_sites", [])
            
            if inspiration_sites:
                urls = [site.get("url") for site in inspiration_sites if site.get("url")]
                
                if urls:
                    screenshots = await self.capture_competitor_screenshots(urls)
                    
                    # Merge screenshots with inspiration sites
                    for site in inspiration_sites:
                        for screenshot in screenshots:
                            if site.get("url") == screenshot.get("url"):
                                site["screenshot"] = screenshot
                    
                    result.data["inspiration_screenshots"] = screenshots
                    result.message += f" Captured {len([s for s in screenshots if s.get('success')])} screenshots."
        
        return result


"""
Research Agent - Faz Code Analyst

Gathers design inspiration, competitor analysis, and current trends.
Uses Gemini 3 Pro with web search grounding and vision analysis.
"""

from typing import Any, Dict, List, Optional
import json
import logging
import base64
import httpx

from .base_agent import BaseAgent, AgentResult
from app.database import db

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
    model_name = "gemini-1.5-pro-latest"
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
        
        # Include user inspiration image analysis if available
        inspiration_analysis = state.get("inspiration_analysis")
        if inspiration_analysis:
            prompt_parts.append(f"\n## USER INSPIRATION IMAGES ANALYSIS\n{inspiration_analysis}")
        
        prompt_parts.append("""
## YOUR TASK
1. Identify the industry/type of website needed
2. Research current design trends for this industry
3. Find inspiring examples
4. Recommend colors, typography, and patterns
5. If user provided inspiration images, incorporate their desired elements into recommendations
6. Output your findings as JSON""")
        
        return "\n".join(prompt_parts)
    
    async def _load_reference_images(self, project_id: int) -> List[Dict[str, Any]]:
        """Load reference/inspiration images for a project from the database."""
        try:
            rows = await db.fetch(
                """
                SELECT artifact_id, content, created_at
                FROM faz_project_artifacts
                WHERE project_id = $1 AND artifact_type = 'reference_image'
                ORDER BY created_at DESC
                LIMIT 10
                """,
                project_id,
            )
            
            images = []
            for row in rows:
                content = json.loads(row["content"]) if isinstance(row["content"], str) else row["content"]
                images.append({
                    "image_id": row["artifact_id"],
                    "url": content.get("url"),
                    "filename": content.get("filename"),
                    "notes": content.get("notes", ""),
                    "width": content.get("width"),
                    "height": content.get("height"),
                })
            
            return images
        except Exception as e:
            logger.error(f"[Research] Failed to load reference images: {e}")
            return []
    
    async def _analyze_inspiration_images(
        self, 
        images: List[Dict[str, Any]], 
        project_context: str
    ) -> str:
        """
        Analyze user-provided inspiration images using vision API.
        
        Uses Gemini's vision capability to analyze images and extract design insights.
        """
        if not images:
            return ""
        
        try:
            from app.config import settings
            
            # Prepare vision analysis prompt
            vision_prompt = f"""You are analyzing inspiration images provided by a user for a web design project.

Project context: {project_context}

For each image, identify:
1. Color palette being used (extract specific hex codes if visible)
2. Typography styles (serif/sans-serif, modern/classic, weights)
3. Layout patterns (grid structure, whitespace usage, visual hierarchy)
4. UI components and elements worth noting
5. Overall aesthetic and mood
6. What specific elements the user likely wants to incorporate

The user provided notes for each image - pay special attention to what they've highlighted."""

            # Build image descriptions with notes
            analysis_parts = []
            
            for i, img in enumerate(images, 1):
                analysis_parts.append(f"\n### Image {i}: {img.get('filename', 'Untitled')}")
                analysis_parts.append(f"URL: {img.get('url', 'N/A')}")
                if img.get("notes"):
                    analysis_parts.append(f"User Notes: {img['notes']}")
                else:
                    analysis_parts.append("User Notes: (none provided)")
            
            # For vision analysis, we use Gemini's vision capability
            # Since we have URLs, we can use the multimodal input
            if settings.GOOGLE_API_KEY:
                import google.generativeai as genai
                
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-pro-latest")
                
                # Build content with images
                content_parts = [vision_prompt + "\n".join(analysis_parts)]
                
                # Fetch and include images
                for img in images[:5]:  # Limit to 5 images for token efficiency
                    img_url = img.get("url")
                    if img_url:
                        try:
                            async with httpx.AsyncClient() as client:
                                response = await client.get(img_url, timeout=10.0)
                                if response.status_code == 200:
                                    img_data = base64.standard_b64encode(response.content).decode("utf-8")
                                    content_type = response.headers.get("content-type", "image/jpeg")
                                    content_parts.append({
                                        "mime_type": content_type,
                                        "data": img_data,
                                    })
                        except Exception as img_err:
                            logger.warning(f"[Research] Failed to fetch image {img_url}: {img_err}")
                
                # Call Gemini vision
                response = await model.generate_content_async(content_parts)
                
                if response.text:
                    logger.info(f"[Research] Vision analysis complete for {len(images)} images")
                    return response.text
            
            # Fallback: return basic info without vision analysis
            return "User provided inspiration images:\n" + "\n".join(analysis_parts)
            
        except Exception as e:
            logger.error(f"[Research] Vision analysis failed: {e}")
            return f"User provided {len(images)} inspiration images (vision analysis unavailable)"
    
    async def run(self, state: Dict[str, Any]) -> AgentResult:
        """Run research with web search and inspiration image analysis."""
        try:
            project_id = state.get("project_id")
            original = state.get("original_prompt", "")
            
            # Step 1: Load and analyze user inspiration images if available
            inspiration_analysis = ""
            if project_id:
                reference_images = await self._load_reference_images(project_id)
                if reference_images:
                    logger.info(f"[Research] Found {len(reference_images)} inspiration images to analyze")
                    inspiration_analysis = await self._analyze_inspiration_images(
                        reference_images, 
                        original
                    )
                    state["inspiration_analysis"] = inspiration_analysis
            
            # Step 2: Do web search for trends
            search_query = f"{original} website design trends 2025"
            
            logger.info(f"[Research] Searching: {search_query}")
            
            # Call web search tool
            search_result = await self.call_tool("brave_web_search", {"query": search_query, "count": 5})
            
            search_context = ""
            if search_result.get("content"):
                search_context = f"\n## WEB SEARCH RESULTS\n{search_result['content'][:3000]}"
            
            # Step 3: Build prompt with search results and inspiration analysis
            prompt = self._build_prompt(state) + search_context
            system_prompt = self._get_system_prompt()
            
            # Call LLM to analyze and synthesize findings
            response, input_tokens, output_tokens = await self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                state=state
            )
            
            # Parse response
            result = self._parse_response(response, state)
            
            # Include inspiration analysis in data for downstream agents
            if inspiration_analysis:
                result.data["inspiration_analysis"] = inspiration_analysis
            
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


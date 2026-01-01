"""
Gemini 3 Pro Integration for Nicole V7

Provides:
- Deep Research with Google Search Grounding
- Image Generation via Gemini 3 Pro Image
- Agentic capabilities with thinking mode

Models:
- gemini-3-pro-preview: Research, analysis, agentic tasks
- gemini-3-pro-image-preview: Image generation with contextual understanding

Pricing Notes (as of Dec 2025):
- Search Grounding: FREE until Jan 5, 2026 (5,000 prompts/month)
- Standard Input: $2/1M tokens, Output: $12/1M tokens
- Batch (50% cheaper): Input: $1/1M, Output: $6/1M
- Image Gen: ~$0.134/image (1K-2K), ~$0.24/image (4K)
"""

import logging
import json
import asyncio
import random
from typing import Optional, Dict, Any, List, Callable, TypeVar
from datetime import datetime
from decimal import Decimal
from enum import Enum
from functools import wraps

from app.config import settings

logger = logging.getLogger(__name__)

# Type variable for generic retry decorator
T = TypeVar('T')


def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Callable:
    """
    Decorator for async functions that retries with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Base for exponential calculation
        jitter: Add randomness to prevent thundering herd
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"[GEMINI] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    
                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"[GEMINI] {func.__name__} attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator

# Try to import google-genai SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("[GEMINI] google-genai SDK not installed. Run: pip install google-genai")


class ResearchType(str, Enum):
    """Types of research requests."""
    GENERAL = "general"
    VIBE_INSPIRATION = "vibe_inspiration"
    COMPETITOR = "competitor"
    TECHNICAL = "technical"


class GeminiClient:
    """
    Unified Gemini 3 Pro client for Nicole V7.
    
    Provides:
    - Deep research with search grounding
    - Image generation
    - Thinking mode for complex reasoning
    - Cost tracking
    """
    
    # Pricing per 1M tokens (Standard tier, ≤200k context)
    PRICING = {
        "gemini-3-pro-preview": {
            "input": Decimal("2.00"),
            "output": Decimal("12.00"),  # Includes thinking
        },
        "gemini-3-pro-image-preview": {
            "input": Decimal("2.00"),
            "output_text": Decimal("12.00"),
            "output_image_1k": Decimal("0.134"),  # Per image, 1024x1024
            "output_image_2k": Decimal("0.134"),  # Per image, 2048x2048
            "output_image_4k": Decimal("0.24"),   # Per image, 4096x4096
        }
    }
    
    def __init__(self):
        """Initialize Gemini client."""
        self._client = None
        self._configured = False
        self._configure()
    
    def _configure(self) -> None:
        """Configure Gemini SDK."""
        if not GEMINI_AVAILABLE:
            logger.warning("[GEMINI] SDK not available")
            return
        
        if not settings.GEMINI_API_KEY:
            logger.warning("[GEMINI] API key not configured")
            return
        
        try:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self._configured = True
            logger.info("[GEMINI] Client configured successfully")
        except Exception as e:
            logger.error(f"[GEMINI] Configuration failed: {e}")
    
    @property
    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
        return self._configured and self._client is not None
    
    # =========================================================================
    # DEEP RESEARCH
    # =========================================================================
    
    async def deep_research(
        self,
        query: str,
        research_type: ResearchType = ResearchType.GENERAL,
        context: Optional[Dict[str, Any]] = None,
        max_sources: int = 10,
        enable_thinking: bool = True
    ) -> Dict[str, Any]:
        """
        Execute deep research using Gemini Deep Research Agent via Interactions API.
        
        This uses the official Deep Research Agent which has built-in Google Search
        grounding and returns properly structured results with sources.
        
        Falls back to standard generateContent API with Google Search tool if
        the Interactions API is not available (requires google-genai >= 1.55.0).
        
        Args:
            query: Research query
            research_type: Type of research (affects prompting)
            context: Additional context (project brief, previous feedback, etc.)
            max_sources: Maximum sources to analyze
            enable_thinking: Enable thinking mode for deeper analysis
            
        Returns:
            Structured research results with citations
        """
        if not self.is_configured:
            return {"error": "Gemini not configured", "success": False}
        
        start_time = datetime.now()
        
        try:
            # Build research prompt based on type
            system_prompt = self._build_research_prompt(research_type, context)
            
            # Build enhanced query for the agent
            full_query = f"""
{system_prompt}

RESEARCH QUERY: {query}

Please conduct thorough research on this topic using Google Search and provide:
1. A comprehensive executive summary
2. Key findings with specific citations and URLs
3. All source URLs you referenced (CRITICAL - include full URLs)
4. Actionable recommendations

Format your response as structured JSON with these fields:
- executive_summary: 2-3 sentence overview
- key_findings: array of {{content, source_url, source_title}}
- sources: array of {{url, title, relevance_score}} (MUST include actual URLs)
- recommendations: array of actionable insights
"""
            
            logger.info(f"[GEMINI] Starting research for query: {query[:100]}...")
            logger.info(f"[GEMINI] Research type: {research_type}")
            
            # Try to use Deep Research Agent via Interactions API first
            use_interactions_api = False
            result_wrapper = None
            
            try:
                # Check if interactions API is available (requires google-genai >= 1.55.0)
                if hasattr(self._client, 'interactions'):
                    logger.info("[GEMINI] Using Interactions API with Deep Research Agent")
                    
                    @async_retry_with_backoff(max_attempts=3, base_delay=2.0)
                    async def _execute_deep_research_agent():
                        # Deep Research Agent requires background=True AND store=True
                        # We need to poll for completion
                        interaction = await asyncio.to_thread(
                            self._client.interactions.create,
                            agent="deep-research-pro-preview-12-2025",
                            input=full_query,
                            background=True,  # Required for agent interactions
                            store=True  # Required for background interactions
                        )
                        return interaction
                    
                    interaction = await _execute_deep_research_agent()
                    
                    # Poll for completion if background mode
                    if hasattr(interaction, 'status') and interaction.status != 'completed':
                        logger.info(f"[GEMINI] Deep Research Agent started, status: {interaction.status}, polling for completion...")
                        max_polls = 60  # Max 5 minutes (60 * 5 seconds)
                        poll_count = 0
                        
                        while poll_count < max_polls:
                            await asyncio.sleep(5)  # Wait 5 seconds between polls
                            poll_count += 1
                            
                            # Get updated interaction status
                            try:
                                interaction = await asyncio.to_thread(
                                    self._client.interactions.get,
                                    interaction.id
                                )
                                logger.info(f"[GEMINI] Poll {poll_count}: status={interaction.status}")
                                
                                if interaction.status == 'completed':
                                    logger.info("[GEMINI] Deep Research Agent completed!")
                                    break
                                elif interaction.status == 'failed':
                                    logger.error("[GEMINI] Deep Research Agent failed")
                                    raise Exception("Deep Research Agent failed")
                            except Exception as e:
                                logger.warning(f"[GEMINI] Poll failed: {e}")
                                if poll_count >= max_polls:
                                    raise
                        
                        if poll_count >= max_polls:
                            logger.warning("[GEMINI] Deep Research Agent timed out after 5 minutes")
                    
                    result_wrapper = {"type": "interaction", "data": interaction}
                    use_interactions_api = True
                    logger.info("[GEMINI] Deep Research Agent completed successfully")
                else:
                    logger.info("[GEMINI] Interactions API not available in SDK")
                    
            except Exception as e:
                logger.warning(f"[GEMINI] Interactions API failed: {e}")
            
            # Fallback to standard generateContent with Google Search tool
            if not use_interactions_api:
                logger.info("[GEMINI] Using standard generateContent with Google Search tool")
                
                tools = [types.Tool(google_search=types.GoogleSearch())]
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=tools,
                    response_modalities=["TEXT"],
                )
                
                if enable_thinking:
                    try:
                        config.thinking_config = types.ThinkingConfig(
                            thinking_budget=8000
                        )
                    except Exception as e:
                        logger.warning(f"[GEMINI] Thinking config not supported: {e}")
                
                @async_retry_with_backoff(max_attempts=3, base_delay=1.0)
                async def _execute_standard_research():
                    return await asyncio.to_thread(
                        self._client.models.generate_content,
                        model=settings.GEMINI_PRO_MODEL,
                        contents=full_query,
                        config=config
                    )
                
                response = await _execute_standard_research()
                result_wrapper = {"type": "generate_content", "data": response}
            
            # Parse based on response type
            if result_wrapper["type"] == "interaction":
                interaction = result_wrapper["data"]
                result = self._parse_interaction_response(interaction)
                
                # Get usage from interaction
                usage = getattr(interaction, 'usage', None)
                input_tokens = getattr(usage, 'input_tokens', 0) if usage else 0
                output_tokens = getattr(usage, 'output_tokens', 0) if usage else 0
                model_used = "deep-research-pro-preview-12-2025"
                
            else:
                response = result_wrapper["data"]
                
                # Debug: Log response structure
                logger.info(f"[GEMINI] Response type: {type(response)}")
                if hasattr(response, 'candidates') and response.candidates:
                    logger.info(f"[GEMINI] Candidates count: {len(response.candidates)}")
                
                result = self._parse_research_response(response)
                
                # Get usage from response
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                model_used = settings.GEMINI_PRO_MODEL
            
            # Calculate cost
            cost = self._estimate_cost(
                settings.GEMINI_PRO_MODEL,
                input_tokens,
                output_tokens
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[GEMINI] Research completed in {elapsed:.1f}s, cost: ${cost}")
            
            # Handle both enum and string research_type
            research_type_str = research_type.value if hasattr(research_type, 'value') else str(research_type)
            
            sources = result.get("sources", [])
            logger.info(f"[GEMINI] Returning {len(sources)} sources to research service")
            if sources:
                logger.info(f"[GEMINI] First 3 sources: {[s.get('url', 'no-url') for s in sources[:3]]}")
            
            return {
                "success": True,
                "query": query,
                "research_type": research_type_str,
                "results": result,
                "sources": sources,
                "thinking": result.get("thinking"),
                "metadata": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": float(cost),
                    "elapsed_seconds": elapsed,
                    "model": model_used
                }
            }
            
        except Exception as e:
            logger.error(f"[GEMINI] Research failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def _build_research_prompt(
        self,
        research_type: ResearchType,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build system prompt for research type."""
        
        base = """You are a research agent working for Nicole, an AI companion assistant.
Your task is to conduct thorough, autonomous research and return a comprehensive report.

RESEARCH GUIDELINES:
- Search multiple authoritative sources using Google Search
- Cross-reference information for accuracy
- Include specific citations for all claims
- Organize findings in a clear hierarchy
- Note any conflicting information found

OUTPUT FORMAT:
Return a structured JSON report with:
- executive_summary: 2-3 sentence overview
- key_findings: array of findings with citations
- sources: array of {url, title, relevance_score}
- recommendations: actionable insights
"""
        
        if research_type == ResearchType.VIBE_INSPIRATION:
            extra = """
VIBE INSPIRATION MODE:
You're researching design inspiration for a web development project.
- Focus on visual design patterns, layouts, color schemes
- Prioritize: Dribbble, Awwwards, Behance, actual live websites
- Note specific design elements: typography, spacing, interactions
- Match designs to the project brief provided

PROJECT CONTEXT:
{project_brief}
"""
            if context and context.get("project_brief"):
                extra = extra.format(project_brief=json.dumps(context["project_brief"], indent=2))
            else:
                extra = extra.format(project_brief="No specific brief provided")
            return base + extra
        
        elif research_type == ResearchType.COMPETITOR:
            return base + """
COMPETITOR ANALYSIS MODE:
- Analyze competitor websites, features, pricing
- Identify strengths and weaknesses
- Note market positioning
- Provide strategic recommendations
"""
        
        elif research_type == ResearchType.TECHNICAL:
            return base + """
TECHNICAL RESEARCH MODE:
- Focus on technical documentation, code examples
- Prioritize official docs, GitHub, Stack Overflow
- Include code snippets where relevant
- Note version compatibility
"""
        
        return base
    
    def _format_research_query(
        self,
        query: str,
        research_type: ResearchType,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format the research query with context."""
        
        formatted = f"Research Query: {query}\n\n"
        
        if context:
            if context.get("previous_feedback"):
                formatted += f"Previous Feedback:\n{json.dumps(context['previous_feedback'], indent=2)}\n\n"
            if context.get("avoid_patterns"):
                formatted += f"Patterns to Avoid: {', '.join(context['avoid_patterns'])}\n\n"
        
        formatted += "Please conduct thorough research and return your findings as structured JSON."
        
        return formatted
    
    def _parse_research_response(self, response) -> Dict[str, Any]:
        """Parse Gemini response into structured format."""
        try:
            # Extract text content
            text = ""
            thinking = None
            
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'text'):
                        text += part.text
                    if hasattr(part, 'thought') and part.thought:
                        thinking = part.text
            
            # Try to parse as JSON
            # Look for JSON block in response
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_match:
                parsed = json.loads(json_match.group(1))
                logger.info(f"[GEMINI] Parsed JSON from code block, has sources: {'sources' in parsed}, count: {len(parsed.get('sources', []))}")
            else:
                # Try direct parse
                try:
                    parsed = json.loads(text)
                    logger.info(f"[GEMINI] Parsed JSON directly, has sources: {'sources' in parsed}, count: {len(parsed.get('sources', []))}")
                except json.JSONDecodeError:
                    logger.warning("[GEMINI] Failed to parse as JSON, using fallback structure")
                    logger.info(f"[GEMINI] Response text preview: {text[:500]}...")  # Changed to INFO so we can see it
                    # Return as plain text
                    parsed = {
                        "executive_summary": text[:500],
                        "key_findings": [{"content": text}],
                        "sources": [],
                        "recommendations": []
                    }
            
            if thinking:
                parsed["thinking"] = thinking
            
            # Extract grounding sources if available
            logger.info(f"[GEMINI] Response has grounding_metadata: {hasattr(response, 'grounding_metadata')}")
            
            if hasattr(response, 'grounding_metadata'):
                grounding = response.grounding_metadata
                logger.info(f"[GEMINI] Grounding metadata found, has search_entry_point: {hasattr(grounding, 'search_entry_point')}, has grounding_chunks: {hasattr(grounding, 'grounding_chunks')}")
                
                if hasattr(grounding, 'search_entry_point'):
                    parsed["search_queries"] = grounding.search_entry_point
                    
                if hasattr(grounding, 'grounding_chunks'):
                    chunk_count = len(grounding.grounding_chunks)
                    logger.info(f"[GEMINI] Found {chunk_count} grounding chunks")
                    
                    grounding_sources = []
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, 'web'):
                            source = {"url": chunk.web.uri, "title": chunk.web.title if hasattr(chunk.web, 'title') else chunk.web.uri}
                            grounding_sources.append(source)
                            logger.info(f"[GEMINI] Grounding source: {source['url']}")
                    
                    logger.info(f"[GEMINI] Extracted {len(grounding_sources)} sources from grounding_chunks")
                    
                    # Add to sources list
                    if "sources" not in parsed or not parsed["sources"]:
                        parsed["sources"] = grounding_sources
                    else:
                        parsed["sources"].extend(grounding_sources)
                else:
                    logger.warning("[GEMINI] No grounding_chunks found in grounding_metadata")
            else:
                logger.warning("[GEMINI] No grounding_metadata in response - attempting fallback URL extraction")
                # Fallback: Extract URLs from response text
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, text)
                if urls:
                    fallback_sources = [{"url": url, "title": url} for url in list(set(urls))[:10]]
                    logger.info(f"[GEMINI] Extracted {len(fallback_sources)} URLs from response text as fallback sources")
                    if "sources" not in parsed or not parsed["sources"]:
                        parsed["sources"] = fallback_sources
                    else:
                        parsed["sources"].extend(fallback_sources)
                else:
                    logger.warning("[GEMINI] No URLs found in response text either - sources will be empty")
            
            return parsed
            
        except Exception as e:
            logger.warning(f"[GEMINI] Response parsing failed: {e}")
            return {
                "raw_response": str(response),
                "parse_error": str(e)
            }
    
    def _parse_interaction_response(self, interaction) -> Dict[str, Any]:
        """
        Parse Deep Research Agent Interaction response into structured format.
        
        The Interactions API returns a different structure than generateContent.
        See: https://ai.google.dev/gemini-api/docs/interactions
        """
        try:
            import re
            
            # Get the output text from the interaction
            text = ""
            if hasattr(interaction, 'outputs') and interaction.outputs:
                for output in interaction.outputs:
                    if hasattr(output, 'text'):
                        text += output.text
                    elif hasattr(output, 'content'):
                        # Content might be a list of parts
                        if isinstance(output.content, list):
                            for part in output.content:
                                if hasattr(part, 'text'):
                                    text += part.text
                        elif hasattr(output.content, 'text'):
                            text += output.content.text
            
            logger.info(f"[GEMINI] Interaction response text length: {len(text)}")
            logger.info(f"[GEMINI] Interaction response preview: {text[:500]}...")
            
            # Try to parse as JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_match:
                parsed = json.loads(json_match.group(1))
                logger.info(f"[GEMINI] Parsed JSON from interaction, has sources: {'sources' in parsed}, count: {len(parsed.get('sources', []))}")
            else:
                # Try direct parse
                try:
                    parsed = json.loads(text)
                    logger.info(f"[GEMINI] Parsed JSON directly from interaction, has sources: {'sources' in parsed}, count: {len(parsed.get('sources', []))}")
                except json.JSONDecodeError:
                    logger.warning("[GEMINI] Failed to parse interaction as JSON, using fallback")
                    parsed = {
                        "executive_summary": text[:500] if text else "Research completed",
                        "key_findings": [{"content": text}] if text else [],
                        "sources": [],
                        "recommendations": []
                    }
            
            # Extract URLs from text as fallback if no sources in JSON
            if not parsed.get("sources"):
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\])]+'
                urls = re.findall(url_pattern, text)
                if urls:
                    # Deduplicate and limit
                    unique_urls = list(dict.fromkeys(urls))[:15]
                    parsed["sources"] = [{"url": url, "title": url} for url in unique_urls]
                    logger.info(f"[GEMINI] Extracted {len(parsed['sources'])} URLs from interaction text")
            
            # Check for grounding metadata on the interaction
            if hasattr(interaction, 'grounding_metadata') and interaction.grounding_metadata:
                grounding = interaction.grounding_metadata
                logger.info("[GEMINI] Interaction has grounding_metadata")
                
                if hasattr(grounding, 'grounding_chunks'):
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                            source = {
                                "url": chunk.web.uri,
                                "title": getattr(chunk.web, 'title', chunk.web.uri)
                            }
                            if source not in parsed.get("sources", []):
                                parsed.setdefault("sources", []).append(source)
                    logger.info(f"[GEMINI] Added grounding sources, total: {len(parsed.get('sources', []))}")
            
            return parsed
            
        except Exception as e:
            logger.error(f"[GEMINI] Interaction parsing failed: {e}", exc_info=True)
            return {
                "raw_response": str(interaction),
                "parse_error": str(e),
                "sources": []
            }
    
    # =========================================================================
    # IMAGE GENERATION
    # =========================================================================
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "gemini-3-pro-image-preview",
        aspect_ratio: str = "1:1",
        style: Optional[str] = None,
        reference_image: Optional[bytes] = None,
        num_images: int = 1,
        enable_thinking: bool = False
    ) -> Dict[str, Any]:
        """
        Generate image using Imagen 3 or legacy Gemini 3 Pro Image.
        
        Args:
            prompt: Image description
            model: Model to use (imagen-3.0-generate-002, imagen-3.0-fast-generate-001, gemini-3-pro-image-preview)
            aspect_ratio: Output aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            style: Optional style guidance
            reference_image: Optional reference image for modification
            num_images: Number of images to generate (1-4)
            enable_thinking: Enable thinking (only for legacy Gemini model)
            
        Returns:
            Generated image data with metadata
        """
        if not self.is_configured:
            return {"error": "Gemini not configured", "success": False}
        
        start_time = datetime.now()
        
        # Determine model and cost - Imagen 3 models
        is_imagen = model.startswith("imagen-3")
        cost_per_image = 0.02 if "fast" in model else (0.04 if is_imagen else 0.134)
        
        try:
            # Build prompt with style
            full_prompt = prompt
            if style:
                full_prompt = f"[Style: {style}] {prompt}"
            
            logger.info(f"[GEMINI] Generating {num_images} image(s) with {model}, aspect_ratio={aspect_ratio}")
            
            if is_imagen:
                # Use Imagen 3 API
                # Imagen 3 uses the images.generate endpoint
                @async_retry_with_backoff(max_attempts=3, base_delay=2.0)
                async def _execute_imagen():
                    return await asyncio.to_thread(
                        self._client.models.generate_images,
                        model=model,
                        prompt=full_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=min(num_images, 4),
                            aspect_ratio=aspect_ratio,
                            person_generation="allow_adult",  # Allow adult persons
                            safety_filter_level="block_only_high",  # Less restrictive
                        )
                    )
                
                response = await _execute_imagen()
                
                # Extract images from Imagen 3 response
                images = []
                for image in response.generated_images:
                    if hasattr(image, 'image') and image.image:
                        # Image data is base64 encoded
                        images.append({
                            "data": image.image.image_bytes if hasattr(image.image, 'image_bytes') else image.image,
                            "mime_type": "image/png"
                        })
                
                if not images:
                    return {
                        "success": False,
                        "error": "No images generated",
                        "prompt": prompt
                    }
                
                elapsed = (datetime.now() - start_time).total_seconds()
                total_cost = cost_per_image * len(images)
                
                logger.info(f"[GEMINI] Imagen 3 generated {len(images)} image(s) in {elapsed:.1f}s, cost: ${total_cost}")
                
                return {
                    "success": True,
                    "images": images,  # List of image data
                    "image_data": images[0]["data"] if images else None,  # First image for backwards compatibility
                    "mime_type": "image/png",
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "style": style,
                    "count": len(images),
                    "metadata": {
                        "cost_usd": float(total_cost),
                        "elapsed_seconds": elapsed,
                        "model": model
                    }
                }
            else:
                # Legacy Gemini 3 Pro Image generation
                config = types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
                
                if enable_thinking:
                    config.thinking_config = types.ThinkingConfig(
                        thinking_budget=4000
                    )
                
                # Build content
                contents = [full_prompt]
                if reference_image:
                    contents = [
                        types.Part.from_bytes(reference_image, mime_type="image/png"),
                        full_prompt
                    ]
                
                @async_retry_with_backoff(max_attempts=3, base_delay=2.0)
                async def _execute_image_gen():
                    return await asyncio.to_thread(
                        self._client.models.generate_content,
                        model="gemini-3-pro-image-preview",
                        contents=contents,
                        config=config
                    )
                
                response = await _execute_image_gen()
                
                # Extract image from response
                image_data = None
                text_response = ""
                
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            image_data = part.inline_data.data
                        if hasattr(part, 'text') and part.text:
                            text_response += part.text
                
                if not image_data:
                    return {
                        "success": False,
                        "error": "No image generated",
                        "text_response": text_response
                    }
                
                elapsed = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"[GEMINI] Legacy image generated in {elapsed:.1f}s, cost: ${cost_per_image}")
                
                return {
                    "success": True,
                    "image_data": image_data,
                    "images": [{"data": image_data, "mime_type": "image/png"}],
                    "mime_type": "image/png",
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "style": style,
                    "text_response": text_response,
                    "count": 1,
                    "metadata": {
                        "cost_usd": float(cost_per_image),
                        "elapsed_seconds": elapsed,
                        "model": "gemini-3-pro-image-preview"
                    }
                }
            
        except Exception as e:
            logger.error(f"[GEMINI] Image generation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt
            }
    
    # =========================================================================
    # COST ESTIMATION
    # =========================================================================
    
    def _estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """Estimate API cost for a request."""
        pricing = self.PRICING.get(model, self.PRICING["gemini-3-pro-preview"])
        
        input_cost = pricing["input"] * Decimal(str(input_tokens)) / Decimal("1000000")
        output_cost = pricing["output"] * Decimal(str(output_tokens)) / Decimal("1000000")
        
        return input_cost + output_cost
    
    def _estimate_image_cost(self, size: str) -> Decimal:
        """Estimate image generation cost."""
        pricing = self.PRICING["gemini-3-pro-image-preview"]
        
        if "4096" in size or "4k" in size.lower():
            return pricing["output_image_4k"]
        else:
            return pricing["output_image_1k"]
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    async def search_inspiration(
        self,
        query: str,
        project_brief: Optional[Dict[str, Any]] = None,
        previous_feedback: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Search for design inspiration for Vibe projects.
        
        Convenience wrapper around deep_research with vibe-specific settings.
        """
        return await self.deep_research(
            query=query,
            research_type=ResearchType.VIBE_INSPIRATION,
            context={
                "project_brief": project_brief,
                "previous_feedback": previous_feedback
            },
            enable_thinking=True
        )
    
    async def analyze_competitor(
        self,
        competitor_url: str,
        analysis_focus: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a competitor website.
        
        Args:
            competitor_url: URL to analyze
            analysis_focus: Specific aspects to focus on
        """
        query = f"Analyze the website at {competitor_url}"
        if analysis_focus:
            query += f". Focus on: {', '.join(analysis_focus)}"
        
        return await self.deep_research(
            query=query,
            research_type=ResearchType.COMPETITOR,
            enable_thinking=True
        )
    
    async def generate_content(
        self,
        prompt: str,
        model_name: str = "gemini-3-pro-preview",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        enable_thinking: bool = False
    ) -> str:
        """
        Generate text content using Gemini.
        
        This is a simple text generation method for agents that need
        raw generation capabilities without research grounding.
        
        Args:
            prompt: The full prompt including system instruction
            model_name: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            enable_thinking: Enable thinking mode
            
        Returns:
            Generated text content
        """
        if not self.is_configured:
            raise RuntimeError("Gemini not configured - check GEMINI_API_KEY")
        
        try:
            # Build config
            config = types.GenerateContentConfig(
                response_modalities=["TEXT"],
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Add thinking if enabled
            if enable_thinking:
                config.thinking_config = types.ThinkingConfig(
                    thinking_budget=4000
                )
            
            # Execute generation with retry
            @async_retry_with_backoff(max_attempts=3, base_delay=1.0)
            async def _execute_generation():
                return await asyncio.to_thread(
                    self._client.models.generate_content,
                    model=model_name,
                    contents=prompt,
                    config=config
                )
            
            response = await _execute_generation()
            
            # Extract text from response
            text = ""
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        text += part.text
            
            if not text:
                raise RuntimeError("No text content in Gemini response")
            
            return text
            
        except Exception as e:
            logger.error(f"[GEMINI] Generation failed: {e}", exc_info=True)
            raise


# Singleton instance
gemini_client = GeminiClient()


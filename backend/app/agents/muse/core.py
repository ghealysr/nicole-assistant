"""
Muse Design Research Agent - Core Implementation.

A world-class Design Research Agent powered by Gemini 2.5 Pro that conducts
deep design research, generates mood boards, and creates agency-quality
design specifications.

Features:
- Gemini 2.5 Pro with 1M token context and native multimodal
- Full knowledge base integration across all phases
- MCP tool access for web search and screenshots
- Intelligent research planning with user questions
- Screenshot capability for URL analysis
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from uuid import uuid4

from app.agents.muse.constants import (
    ANALYTICS_LOOKBACK_DAYS,
    ANALYTICS_MIN_SELECTIONS,
    ANALYTICS_TOP_AESTHETICS_LIMIT,
    ENABLE_AB_TESTING,
    ENABLE_HISTORICAL_PREFERENCES,
    ENABLE_IMAGEN_PREVIEWS,
    KB_CONTEXT_MAX_SECTIONS,
    KB_CONTEXT_MAX_TOKENS,
    MOODBOARD_COUNT_DEFAULT,
    MOODBOARD_MAX_TOKENS,
    MOODBOARD_TEMPERATURE,
    PREVIEW_IMAGE_ASPECT_RATIO,
    PREVIEW_IMAGE_CONCURRENCY,
    PREVIEW_IMAGE_MAX_RETRIES,
    PREVIEW_IMAGE_RETRY_DELAY_SECONDS,
    SESSION_STATUS_AWAITING_APPROVAL,
    SESSION_STATUS_AWAITING_SELECTION,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_STREAMING_MOODBOARDS,
    STYLEGUIDE_MAX_TOKENS,
    STYLEGUIDE_TEMPERATURE,
)
from app.agents.muse.prompts import (
    BRIEF_ANALYSIS_PROMPT,
    INSPIRATION_ANALYSIS_PROMPT,
    MOOD_BOARD_GENERATION_PROMPT,
    MUSE_SYSTEM_PROMPT,
    PAGE_DESIGN_PROMPT,
    RESEARCH_PLANNING_PROMPT,
    STYLE_GUIDE_GENERATION_PROMPT,
    WEB_RESEARCH_SYNTHESIS_PROMPT,
)
from app.database import db
from app.services.gemini_client import (
    GEMINI_FLASH,
    GEMINI_PRO,
    GeminiResponse,
    ImagePart,
    gemini_client,
)
from app.services.knowledge_base_service import kb_service

# Import the SDK-based Gemini client for image generation (Imagen 3)
try:
    from app.integrations.alphawave_gemini import gemini_client as imagen_client
    IMAGEN_AVAILABLE = True
except ImportError:
    IMAGEN_AVAILABLE = False
    imagen_client = None
    logging.getLogger(__name__).warning(
        "[MUSE] Imagen client not available - mood board previews disabled"
    )

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class BriefAnalysis:
    """Result of brief analysis phase."""
    primary_movement: str = ""
    secondary_influences: List[str] = field(default_factory=list)
    emotional_targets: List[str] = field(default_factory=list)
    cultural_context: str = ""
    research_directions: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    synthesis: Dict[str, str] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0


@dataclass
class ResearchPlan:
    """Intelligent research plan with questions for user."""
    understanding: Dict[str, Any] = field(default_factory=dict)
    clarifying_questions: List[Dict[str, str]] = field(default_factory=list)
    research_plan: Dict[str, Any] = field(default_factory=dict)
    hypothesis: Dict[str, Any] = field(default_factory=dict)
    risk_factors: List[Dict[str, str]] = field(default_factory=list)
    tokens_used: int = 0


@dataclass
class InspirationAnalysis:
    """Result of analyzing a single inspiration image/URL."""
    input_id: int
    overall_impression: str = ""
    aesthetic_movement: str = ""
    emotional_tone: List[str] = field(default_factory=list)
    color_analysis: Dict[str, Any] = field(default_factory=dict)
    typography_analysis: Dict[str, Any] = field(default_factory=dict)
    layout_analysis: Dict[str, Any] = field(default_factory=dict)
    distinctive_elements: Dict[str, Any] = field(default_factory=dict)
    motion_cues: Dict[str, Any] = field(default_factory=dict)
    applicability_score: int = 0
    tokens_used: int = 0


@dataclass
class WebResearchResult:
    """Result of web research phase."""
    queries: List[str] = field(default_factory=list)
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    screenshot_analyses: List[Dict[str, Any]] = field(default_factory=list)
    synthesis: Dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0


@dataclass
class MoodBoard:
    """A single mood board option."""
    option_number: int
    title: str
    description: str
    aesthetic_movement: str
    emotional_tone: List[str]
    color_palette: Dict[str, str]
    color_rationale: str
    typography: Dict[str, Any]
    visual_elements: Dict[str, Any]
    layout_approach: Dict[str, Any]
    motion_language: Dict[str, Any]
    anti_patterns: List[str]
    differentiator: str
    tokens_used: int = 0
    preview_image_b64: Optional[str] = None
    db_id: Optional[int] = None


@dataclass
class MoodBoardAnalytics:
    """Analytics data for mood board selection A/B testing."""
    session_id: int
    presented_options: int
    selected_option_number: int
    selection_time_seconds: Optional[int]
    selected_movement: str
    selected_color_temp: str  # warm/cool/neutral
    selected_typography_style: str  # serif/sans-serif/display
    brief_keywords: List[str]
    target_industry: Optional[str]
    target_audience_segment: Optional[str]


@dataclass
class ResearchSession:
    """Complete research session state."""
    session_id: int
    project_id: int
    status: str
    brief: str
    research_plan: Optional[ResearchPlan] = None
    brief_analysis: Optional[BriefAnalysis] = None
    inspiration_analyses: List[InspirationAnalysis] = field(default_factory=list)
    web_research: Optional[WebResearchResult] = None
    moodboards: List[MoodBoard] = field(default_factory=list)
    selected_moodboard: Optional[MoodBoard] = None
    style_guide: Optional[Dict[str, Any]] = None
    total_tokens: int = 0
    estimated_cost: float = 0.0


# ============================================================================
# MUSE AGENT
# ============================================================================

class MuseAgent:
    """
    Muse Design Research Agent.
    
    Orchestrates the complete design research pipeline:
    0. Research Planning - Create intelligent plan with questions for user
    1. Brief Analysis - Extract keywords, movements, emotional targets
    2. Inspiration Analysis - Analyze user-provided images/URLs with vision
    3. Web Research - Search web and screenshot sites for references
    4. Mood Board Generation - Create 4 distinct options
    5. Style Guide Generation - Complete design system from selected mood board
    6. Page Design - Detailed page specifications
    
    All phases integrate with the design knowledge base for expert context.
    """
    
    def __init__(self):
        self.gemini = gemini_client
        self.imagen = imagen_client  # SDK client for Imagen 3 image generation
        self.system_prompt = MUSE_SYSTEM_PROMPT
        self._mcp_client = None
    
    @property
    def is_available(self) -> bool:
        """Check if Muse is properly configured."""
        return self.gemini.is_available
    
    @property
    def can_generate_images(self) -> bool:
        """Check if image generation is available."""
        return IMAGEN_AVAILABLE and self.imagen is not None and self.imagen.is_configured
    
    # ========================================================================
    # MCP TOOL ACCESS
    # ========================================================================
    
    async def _get_mcp_client(self):
        """Get or create MCP client for web search and screenshots."""
        if self._mcp_client is None:
            try:
                from app.mcp.docker_mcp_client import get_mcp_client
                self._mcp_client = await get_mcp_client()
                logger.info("[MUSE] MCP client connected")
            except Exception as e:
                logger.warning(f"[MUSE] MCP client unavailable: {e}")
                self._mcp_client = None
        return self._mcp_client
    
    async def web_search(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Perform web search using Brave Search MCP tool.
        
        Args:
            query: Search query
            count: Number of results
            
        Returns:
            List of search results with title, url, description
        """
        mcp = await self._get_mcp_client()
        if not mcp:
            logger.warning("[MUSE] Web search skipped - MCP unavailable")
            return []
        
        try:
            result = await mcp.call_tool("brave_web_search", {
                "query": query,
                "count": count
            })
            
            if result.is_error:
                logger.error(f"[MUSE] Web search error: {result.content}")
                return []
            
            # Parse results
            try:
                if isinstance(result.content, str):
                    data = json.loads(result.content)
                else:
                    data = result.content
                
                # Handle different response formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("results", data.get("web", {}).get("results", []))
            except json.JSONDecodeError:
                logger.warning("[MUSE] Could not parse search results")
                return []
                
        except Exception as e:
            logger.error(f"[MUSE] Web search failed: {e}")
            return []
    
    async def screenshot_url(self, url: str) -> Optional[str]:
        """
        Capture screenshot of a URL using Puppeteer MCP tool.
        
        Args:
            url: URL to screenshot
            
        Returns:
            Base64-encoded screenshot image or None if failed
        """
        mcp = await self._get_mcp_client()
        if not mcp:
            logger.warning("[MUSE] Screenshot skipped - MCP unavailable")
            return None
        
        try:
            # Navigate to URL first
            nav_result = await mcp.call_tool("puppeteer_navigate", {"url": url})
            if nav_result.is_error:
                logger.error(f"[MUSE] Navigation failed: {nav_result.content}")
                return None
            
            # Take screenshot
            result = await mcp.call_tool("puppeteer_screenshot", {
                "name": f"muse_research_{uuid4().hex[:8]}",
                "fullPage": False  # Viewport only for faster processing
            })
            
            if result.is_error:
                logger.error(f"[MUSE] Screenshot failed: {result.content}")
                return None
            
            # Return base64 image data
            return result.content
            
        except Exception as e:
            logger.error(f"[MUSE] Screenshot error: {e}")
            return None
    
    async def analyze_screenshot(
        self,
        screenshot_base64: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze a screenshot using Gemini Vision.
        
        Args:
            screenshot_base64: Base64-encoded screenshot
            context: Additional context for analysis
            
        Returns:
            Design analysis of the screenshot
        """
        prompt = f"""Analyze this website screenshot for design research purposes.

{context}

Extract key design insights including:
- Overall aesthetic and design movement
- Color palette (hex codes if visible)
- Typography choices (fonts, hierarchy)
- Layout structure and grid
- Notable UI patterns or components
- Animation/motion cues (if any visible)

Return as JSON with structured design insights."""

        try:
            images = [ImagePart(data=screenshot_base64, mime_type="image/png")]
            result, response = await self.gemini.generate_json(
                prompt=prompt,
                model=GEMINI_PRO,
                system_instruction=self.system_prompt,
                images=images,
                temperature=0.7
            )
            return result
        except Exception as e:
            logger.error(f"[MUSE] Screenshot analysis failed: {e}")
            return {}
    
    # ========================================================================
    # IMAGE GENERATION (Imagen 3)
    # ========================================================================
    
    async def generate_moodboard_preview(
        self,
        moodboard_data: Dict[str, Any],
        aspect_ratio: str = "16:9",
        max_retries: int = 2,
        retry_delay: float = 2.0
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate a visual preview image for a mood board using Imagen 3.
        
        Creates an AI-generated visualization that captures the mood board's
        aesthetic direction, color palette, and overall feel.
        
        Includes retry logic with exponential backoff for API resilience.
        
        Args:
            moodboard_data: The mood board JSON data
            aspect_ratio: Output aspect ratio (16:9 for dashboard display)
            max_retries: Maximum number of retry attempts on failure
            retry_delay: Base delay between retries (seconds)
            
        Returns:
            Tuple of (base64_image_data, generation_prompt) or (None, None) on failure
        """
        if not self.can_generate_images:
            logger.warning("[MUSE] Image generation unavailable - skipping preview")
            return None, None
        
        # Build an expressive prompt from mood board data
        title = moodboard_data.get("title", "Design Concept")
        movement = moodboard_data.get("aesthetic_movement", "")
        tones = moodboard_data.get("emotional_tone", [])
        colors = moodboard_data.get("color_palette", {})
        imagery = moodboard_data.get("visual_elements", {}).get("imagery_style", "")
        layout_phil = moodboard_data.get("layout_approach", {}).get("philosophy", "")
        
        # Extract hex colors for the prompt
        color_list = []
        if isinstance(colors, dict):
            for name, value in colors.items():
                if isinstance(value, str) and value.startswith("#"):
                    color_list.append(f"{name}: {value}")
        color_desc = ", ".join(color_list[:5]) if color_list else "harmonious palette"
        
        tone_desc = ", ".join(tones[:3]) if tones else "sophisticated"
        
        # Craft the image generation prompt
        prompt = f"""Create a website design concept visualization for "{title}".

Style: {movement or "modern minimalist"} design aesthetic
Mood: {tone_desc}
Color palette: {color_desc}
Imagery: {imagery or "clean and professional"}
Layout: {layout_phil or "spacious and balanced"}

Show a sleek, professional website hero section mockup that embodies these design principles.
The image should feel like a polished design concept preview - abstract enough to be inspirational
but clear enough to communicate the design direction. Include subtle UI elements like navigation,
hero content area, and visual hierarchy. Use the specified colors prominently.

Style: High-end design agency portfolio presentation, Dribbble/Behance quality,
professional mockup aesthetic, clean composition, soft shadows, modern web design."""
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"[MUSE] Retry {attempt}/{max_retries} for {title} after {delay:.1f}s")
                    await asyncio.sleep(delay)
                
                logger.info(f"[MUSE] Generating preview for mood board: {title} (attempt {attempt + 1})")
                
                result = await self.imagen.generate_image(
                    prompt=prompt,
                    model="gemini-3-pro-image-preview",  # Gemini 3 Pro Image generation
                    aspect_ratio=aspect_ratio,
                    style="design mockup",
                    num_images=1
                )
                
                if result.get("success") and result.get("image_data"):
                    image_data = result["image_data"]
                    
                    # Ensure it's base64 encoded
                    if isinstance(image_data, bytes):
                        image_data = base64.b64encode(image_data).decode("utf-8")
                    
                    logger.info(f"[MUSE] Successfully generated preview for: {title}")
                    return image_data, prompt
                else:
                    error = result.get("error", "Unknown error")
                    last_error = error
                    logger.warning(f"[MUSE] Image generation attempt {attempt + 1} failed: {error}")
                    
                    # Don't retry on certain errors
                    if "safety" in error.lower() or "policy" in error.lower():
                        logger.error(f"[MUSE] Content policy error - not retrying: {error}")
                        break
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[MUSE] Image generation attempt {attempt + 1} error: {e}")
        
        # All retries exhausted
        logger.error(f"[MUSE] Image generation failed after {max_retries + 1} attempts: {last_error}")
        
        # Return SVG fallback
        color_palette = moodboard_data.get("color_palette", {})
        fallback_svg = self._generate_svg_fallback_preview(color_palette)
        logger.info(f"[MUSE] Using SVG fallback for {title}")
        return fallback_svg, prompt
    
    async def generate_moodboard_previews_batch(
        self,
        moodboards: List[Dict[str, Any]],
        concurrency: int = 2
    ) -> List[Tuple[Optional[str], Optional[str]]]:
        """
        Generate preview images for multiple mood boards with controlled concurrency.
        
        Args:
            moodboards: List of mood board data dicts
            concurrency: Maximum concurrent image generation requests
            
        Returns:
            List of (image_data, prompt) tuples in same order as input
        """
        if not self.can_generate_images:
            return [(None, None)] * len(moodboards)
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def generate_with_semaphore(mb_data: Dict[str, Any]):
            async with semaphore:
                return await self.generate_moodboard_preview(mb_data)
        
        tasks = [generate_with_semaphore(mb) for mb in moodboards]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[MUSE] Batch image gen error for board {i}: {result}")
                processed_results.append((None, None))
            else:
                processed_results.append(result)
        
        return processed_results
    
    # ========================================================================
    # KNOWLEDGE BASE INTEGRATION
    # ========================================================================
    
    async def _get_knowledge_context(
        self,
        query: str,
        max_sections: int = 5,
        max_tokens: int = 4000,
        category: Optional[str] = None
    ) -> str:
        """
        Get relevant knowledge base context for any phase.
        
        Integrates design expertise from:
        - fundamentals (typography, color theory, spacing)
        - patterns (hero sections, bento grids, pricing)
        - animation (GSAP, Motion library)
        - components (shadcn/ui, Aceternity)
        """
        try:
            context = await kb_service.get_relevant_context(
                query=query,
                max_sections=max_sections,
                max_tokens=max_tokens,
                category=category
            )
            if context:
                logger.debug(f"[MUSE] Retrieved KB context ({len(context)} chars)")
            return context or ""
        except Exception as e:
            logger.warning(f"[MUSE] KB context retrieval failed: {e}")
            return ""
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    async def create_session(
        self,
        project_id: int,
        brief: str,
        target_audience: Optional[str] = None,
        brand_keywords: Optional[List[str]] = None,
        aesthetic_preferences: Optional[str] = None,
        anti_patterns: Optional[str] = None
    ) -> int:
        """
        Create a new research session.
        
        Returns the session ID.
        """
        result = await db.fetchrow(
            """
            INSERT INTO muse_research_sessions 
            (project_id, design_brief, target_audience, brand_keywords, 
             aesthetic_preferences, anti_patterns, session_status, current_phase)
            VALUES ($1, $2, $3, $4, $5, $6, 'intake', 'intake')
            RETURNING id
            """,
            project_id,
            brief,
            target_audience,
            brand_keywords,
            aesthetic_preferences,
            anti_patterns
        )
        session_id = result["id"]
        
        # Emit session created event
        await self._emit_event(session_id, "session_created", {
            "project_id": project_id,
            "status": "intake"
        })
        
        logger.info(f"[MUSE] Created research session {session_id} for project {project_id}")
        return session_id
    
    async def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session details."""
        return await db.fetchrow(
            "SELECT * FROM muse_research_sessions WHERE id = $1",
            session_id
        )
    
    async def update_session_status(
        self,
        session_id: int,
        status: str,
        phase: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None
    ):
        """Update session status and emit event."""
        updates = ["session_status = $2", "updated_at = NOW()"]
        params = [session_id, status]
        
        if phase:
            updates.append(f"current_phase = ${len(params) + 1}")
            params.append(phase)
        
        if progress is not None:
            updates.append(f"phase_progress = ${len(params) + 1}")
            params.append(progress)
        
        if message:
            updates.append(f"phase_message = ${len(params) + 1}")
            params.append(message)
        
        await db.execute(
            f"UPDATE muse_research_sessions SET {', '.join(updates)} WHERE id = $1",
            *params
        )
        
        await self._emit_event(session_id, "status_updated", {
            "status": status,
            "phase": phase,
            "progress": progress,
            "message": message
        })
    
    # ========================================================================
    # PHASE 0: RESEARCH PLANNING (NEW)
    # ========================================================================
    
    async def create_research_plan(self, session_id: int) -> ResearchPlan:
        """
        Create an intelligent research plan with clarifying questions.
        
        Phase 0: Before diving into analysis, Muse formulates a strategic
        research plan and identifies questions to ask the user.
        """
        await self.update_session_status(
            session_id, "planning", "research_planning", 0,
            "Creating research plan..."
        )
        
        # Get session data
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Count inspiration images
        inspiration_count = await db.fetchval(
            "SELECT COUNT(*) FROM muse_inspiration_inputs WHERE session_id = $1",
            session_id
        )
        
        # Get relevant knowledge base context
        kb_context = await self._get_knowledge_context(
            query=session["design_brief"],
            max_sections=5,
            category=None  # Search all categories
        )
        
        # Build prompt
        prompt = RESEARCH_PLANNING_PROMPT.format(
            brief=session["design_brief"],
            target_audience=session.get("target_audience") or "Not specified",
            brand_keywords=", ".join(session.get("brand_keywords") or []) or "Not specified",
            aesthetic_preferences=session.get("aesthetic_preferences") or "Not specified",
            anti_patterns=session.get("anti_patterns") or "Not specified",
            inspiration_count=inspiration_count or 0,
            knowledge_context=kb_context
        )
        
        await self._emit_event(session_id, "phase_started", {
            "phase": "research_planning",
            "message": "Analyzing brief and formulating research strategy..."
        })
        
        # Generate research plan
        result, response = await self.gemini.generate_json(
            prompt=prompt,
            model=GEMINI_PRO,
            system_instruction=self.system_prompt,
            temperature=0.7
        )
        
        # Parse result
        plan = ResearchPlan(
            understanding=result.get("understanding", {}),
            clarifying_questions=result.get("clarifying_questions", []),
            research_plan=result.get("research_plan", {}),
            hypothesis=result.get("hypothesis", {}),
            risk_factors=result.get("risk_factors", []),
            tokens_used=response.total_tokens
        )
        
        # Store in database
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET research_plan = $2,
                phase_progress = 100,
                gemini_pro_tokens = gemini_pro_tokens + $3
            WHERE id = $1
            """,
            session_id,
            json.dumps(result),
            response.total_tokens
        )
        
        # Check if we need user input
        has_questions = len(plan.clarifying_questions) > 0
        
        await self._emit_event(session_id, "phase_complete", {
            "phase": "research_planning",
            "has_questions": has_questions,
            "question_count": len(plan.clarifying_questions),
            "hypothesis": plan.hypothesis.get("aesthetic_direction", "")
        })
        
        logger.info(f"[MUSE] Research plan created for session {session_id} ({len(plan.clarifying_questions)} questions)")
        return plan
    
    async def submit_question_answers(
        self,
        session_id: int,
        answers: List[Dict[str, str]]
    ) -> None:
        """
        Submit user answers to clarifying questions.
        
        Args:
            session_id: The research session
            answers: List of {question, answer} dicts
        """
        # Store answers in session
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET user_question_answers = $2,
                session_status = 'analyzing_brief'
            WHERE id = $1
            """,
            session_id,
            json.dumps(answers)
        )
        
        await self._emit_event(session_id, "questions_answered", {
            "answer_count": len(answers)
        })
        
        logger.info(f"[MUSE] Received {len(answers)} answers for session {session_id}")
    
    # ========================================================================
    # PHASE 1: BRIEF ANALYSIS
    # ========================================================================
    
    async def analyze_brief(self, session_id: int) -> BriefAnalysis:
        """
        Analyze the design brief to extract research directions.
        
        Phase 1 of the research pipeline.
        """
        await self.update_session_status(
            session_id, "analyzing_brief", "brief_analysis", 0,
            "Analyzing design brief..."
        )
        
        # Get session data
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get relevant knowledge base context
        kb_context = await self._get_knowledge_context(
            query=session["design_brief"],
            max_sections=5,
            category=None
        )
        
        # Build prompt with user answers if available
        user_answers = session.get("user_question_answers")
        additional_context = ""
        if user_answers:
            try:
                answers = json.loads(user_answers) if isinstance(user_answers, str) else user_answers
                additional_context = "\n\n## USER RESPONSES TO CLARIFYING QUESTIONS:\n"
                for qa in answers:
                    additional_context += f"Q: {qa.get('question', '')}\nA: {qa.get('answer', '')}\n\n"
            except:
                pass
        
        prompt = BRIEF_ANALYSIS_PROMPT.format(
            brief=session["design_brief"] + additional_context,
            target_audience=session.get("target_audience") or "Not specified",
            brand_keywords=", ".join(session.get("brand_keywords") or []) or "Not specified",
            aesthetic_preferences=session.get("aesthetic_preferences") or "Not specified",
            anti_patterns=session.get("anti_patterns") or "Not specified",
            knowledge_context=kb_context
        )
        
        await self._emit_event(session_id, "phase_started", {
            "phase": "brief_analysis",
            "message": "Extracting aesthetic keywords and research directions..."
        })
        
        # Generate analysis
        result, response = await self.gemini.generate_json(
            prompt=prompt,
            model=GEMINI_PRO,
            system_instruction=self.system_prompt,
            temperature=0.7
        )
        
        # Parse result
        analysis = BriefAnalysis(
            primary_movement=result.get("aesthetic_analysis", {}).get("primary_movement", ""),
            secondary_influences=result.get("aesthetic_analysis", {}).get("secondary_influences", []),
            emotional_targets=result.get("aesthetic_analysis", {}).get("emotional_targets", []),
            cultural_context=result.get("aesthetic_analysis", {}).get("cultural_context", ""),
            research_directions=result.get("research_directions", {}),
            constraints=result.get("constraints", {}),
            synthesis=result.get("synthesis", {}),
            raw_response=result,
            tokens_used=response.total_tokens
        )
        
        # Store in database
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET brief_analysis = $2,
                extracted_keywords = $3,
                detected_movements = $4,
                emotional_targets = $5,
                gemini_pro_tokens = gemini_pro_tokens + $6,
                phase_progress = 100
            WHERE id = $1
            """,
            session_id,
            json.dumps(result),
            list(result.get("synthesis", {}).keys()) if result.get("synthesis") else [],
            [analysis.primary_movement] + analysis.secondary_influences,
            analysis.emotional_targets,
            response.total_tokens
        )
        
        await self._emit_event(session_id, "phase_complete", {
            "phase": "brief_analysis",
            "findings": [
                f"Primary movement: {analysis.primary_movement}",
                f"Emotional targets: {', '.join(analysis.emotional_targets[:3])}",
                analysis.synthesis.get("one_sentence_direction", "")
            ]
        })
        
        logger.info(f"[MUSE] Brief analysis complete for session {session_id}")
        return analysis
    
    # ========================================================================
    # PHASE 2: INSPIRATION ANALYSIS
    # ========================================================================
    
    async def add_inspiration(
        self,
        session_id: int,
        input_type: str,  # "image" or "url"
        data: str,  # Base64 image or URL
        user_notes: Optional[str] = None,
        focus_elements: Optional[List[str]] = None,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> int:
        """
        Add an inspiration input (image or URL) to the session.
        
        Returns the inspiration input ID.
        """
        if input_type == "image":
            result = await db.fetchrow(
                """
                INSERT INTO muse_inspiration_inputs 
                (session_id, input_type, image_data, image_filename, image_mime_type,
                 user_notes, focus_elements)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                session_id, input_type, data, filename, mime_type,
                user_notes, focus_elements
            )
        else:  # url
            result = await db.fetchrow(
                """
                INSERT INTO muse_inspiration_inputs 
                (session_id, input_type, url, user_notes, focus_elements)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                session_id, input_type, data, user_notes, focus_elements
            )
        
        input_id = result["id"]
        logger.info(f"[MUSE] Added inspiration input {input_id} to session {session_id}")
        return input_id
    
    async def analyze_inspiration(
        self,
        session_id: int,
        input_id: int
    ) -> InspirationAnalysis:
        """
        Analyze a single inspiration input with Gemini Vision.
        """
        # Get input data
        input_data = await db.fetchrow(
            "SELECT * FROM muse_inspiration_inputs WHERE id = $1",
            input_id
        )
        
        if not input_data:
            raise ValueError(f"Inspiration input {input_id} not found")
        
        await self._emit_event(session_id, "analyzing_inspiration", {
            "input_id": input_id,
            "input_type": input_data["input_type"]
        })
        
        # Get knowledge context for design analysis
        kb_context = await self._get_knowledge_context(
            query="design analysis color typography layout patterns",
            max_sections=3,
            category="fundamentals"
        )
        
        # Build prompt
        prompt = INSPIRATION_ANALYSIS_PROMPT.format(
            user_notes=input_data.get("user_notes") or "No specific notes",
            focus_elements=", ".join(input_data.get("focus_elements") or ["all elements"]),
            knowledge_context=kb_context
        )
        
        # Analyze based on input type
        if input_data["input_type"] == "image":
            # Ensure we have a valid MIME type - fallback to image/jpeg if empty or None
            mime_type = input_data.get("image_mime_type") or input_data.get("mime_type") or ""
            if not mime_type:
                # Try to detect from filename or default to jpeg
                filename = (input_data.get("image_filename") or "").lower()
                if filename.endswith(".png"):
                    mime_type = "image/png"
                elif filename.endswith(".gif"):
                    mime_type = "image/gif"
                elif filename.endswith(".webp"):
                    mime_type = "image/webp"
                else:
                    mime_type = "image/jpeg"
            
            logger.info(f"[MUSE] Analyzing image with MIME type: {mime_type}")
            
            images = [ImagePart(
                data=input_data["image_data"],
                mime_type=mime_type
            )]
            
            result, response = await self.gemini.generate_json(
                prompt=prompt,
                model=GEMINI_PRO,
                system_instruction=self.system_prompt,
                images=images,
                temperature=0.7
            )
        else:
            # For URLs, try to screenshot first
            screenshot = await self.screenshot_url(input_data["url"])
            
            if screenshot:
                # Analyze screenshot with vision
                images = [ImagePart(data=screenshot, mime_type="image/png")]
                result, response = await self.gemini.generate_json(
                    prompt=prompt + f"\n\nThis is a screenshot of: {input_data['url']}",
                    model=GEMINI_PRO,
                    system_instruction=self.system_prompt,
                    images=images,
                    temperature=0.7
                )
            else:
                # Fallback to text-based analysis
                url_prompt = f"Analyze this website URL and provide design insights: {input_data['url']}\n\n{prompt}"
                result, response = await self.gemini.generate_json(
                    prompt=url_prompt,
                    model=GEMINI_PRO,
                    system_instruction=self.system_prompt,
                    temperature=0.7
                )
        
        # Parse result
        analysis = InspirationAnalysis(
            input_id=input_id,
            overall_impression=result.get("overall_impression", ""),
            aesthetic_movement=result.get("aesthetic_movement", ""),
            emotional_tone=result.get("emotional_tone", []),
            color_analysis=result.get("color_analysis", {}),
            typography_analysis=result.get("typography_analysis", {}),
            layout_analysis=result.get("layout_analysis", {}),
            distinctive_elements=result.get("distinctive_elements", {}),
            motion_cues=result.get("motion_cues", {}),
            applicability_score=result.get("applicability", {}).get("score", 5),
            tokens_used=response.total_tokens
        )
        
        # Store analysis
        await db.execute(
            """
            UPDATE muse_inspiration_inputs 
            SET analysis_complete = TRUE,
                gemini_analysis = $2,
                extracted_colors = $3,
                typography_notes = $4,
                layout_notes = $5,
                applicability_score = $6
            WHERE id = $1
            """,
            input_id,
            json.dumps(result),
            json.dumps(result.get("color_analysis", {}).get("dominant_colors", [])),
            result.get("typography_analysis", {}).get("hierarchy_approach", ""),
            result.get("layout_analysis", {}).get("visual_flow", ""),
            analysis.applicability_score
        )
        
        # Update session token count
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET gemini_pro_tokens = gemini_pro_tokens + $2
            WHERE id = $1
            """,
            session_id, response.total_tokens
        )
        
        await self._emit_event(session_id, "inspiration_analyzed", {
            "input_id": input_id,
            "movement": analysis.aesthetic_movement,
            "score": analysis.applicability_score,
            "key_finding": analysis.overall_impression[:100]
        })
        
        logger.info(f"[MUSE] Analyzed inspiration {input_id} for session {session_id}")
        return analysis
    
    async def analyze_all_inspirations(self, session_id: int) -> List[InspirationAnalysis]:
        """Analyze all inspiration inputs for a session."""
        await self.update_session_status(
            session_id, "analyzing_inspiration", "inspiration_analysis", 0,
            "Analyzing inspiration images..."
        )
        
        # Get all unanalyzed inputs
        inputs = await db.fetch(
            """
            SELECT id FROM muse_inspiration_inputs 
            WHERE session_id = $1 AND analysis_complete = FALSE
            """,
            session_id
        )
        
        analyses = []
        total = len(inputs)
        
        for i, inp in enumerate(inputs):
            progress = int((i / total) * 100) if total > 0 else 100
            await self.update_session_status(
                session_id, "analyzing_inspiration", "inspiration_analysis", progress,
                f"Analyzing image {i + 1} of {total}..."
            )
            
            analysis = await self.analyze_inspiration(session_id, inp["id"])
            analyses.append(analysis)
        
        await self._emit_event(session_id, "phase_complete", {
            "phase": "inspiration_analysis",
            "count": len(analyses),
            "findings": [a.overall_impression[:50] for a in analyses[:3]]
        })
        
        return analyses
    
    # ========================================================================
    # PHASE 2.5: WEB RESEARCH (NEW)
    # ========================================================================
    
    async def conduct_web_research(self, session_id: int) -> WebResearchResult:
        """
        Conduct web research using MCP tools.
        
        Phase 2.5: Uses Brave Search for design references and Puppeteer
        for screenshotting competitor sites.
        """
        await self.update_session_status(
            session_id, "researching", "web_research", 0,
            "Conducting web research..."
        )
        
        # Get session and brief analysis
        session = await self.get_session(session_id)
        brief_analysis = session.get("brief_analysis")
        
        if not brief_analysis:
            logger.warning("[MUSE] No brief analysis - skipping web research")
            return WebResearchResult()
        
        try:
            brief_data = json.loads(brief_analysis) if isinstance(brief_analysis, str) else brief_analysis
        except:
            brief_data = {}
        
        research_directions = brief_data.get("research_directions", {})
        
        # Build search queries from research directions
        queries = []
        
        # Historical queries
        for query in research_directions.get("historical_queries", [])[:2]:
            queries.append(query)
        
        # Contemporary queries
        for query in research_directions.get("contemporary_queries", [])[:2]:
            queries.append(query)
        
        # Add design-specific queries based on brief
        primary_movement = brief_data.get("aesthetic_analysis", {}).get("primary_movement", "")
        if primary_movement:
            queries.append(f"{primary_movement} website design examples 2024")
        
        await self._emit_event(session_id, "phase_started", {
            "phase": "web_research",
            "query_count": len(queries)
        })
        
        # Execute searches
        all_results = []
        for i, query in enumerate(queries):
            progress = int((i / len(queries)) * 50) if queries else 0
            await self.update_session_status(
                session_id, "researching", "web_research", progress,
                f"Searching: {query[:50]}..."
            )
            
            results = await self.web_search(query, count=5)
            all_results.append({
                "query": query,
                "results": results
            })
        
        # Screenshot top design reference sites (limit to 3)
        screenshot_analyses = []
        screenshot_urls = []
        
        for search in all_results:
            for result in search.get("results", [])[:1]:  # Top result per query
                url = result.get("url", "")
                if url and "dribbble" in url or "behance" in url or "awwwards" in url:
                    screenshot_urls.append(url)
        
        for i, url in enumerate(screenshot_urls[:3]):
            progress = 50 + int((i / 3) * 40)
            await self.update_session_status(
                session_id, "researching", "web_research", progress,
                f"Analyzing reference site {i + 1}..."
            )
            
            screenshot = await self.screenshot_url(url)
            if screenshot:
                analysis = await self.analyze_screenshot(screenshot, f"Design reference from {url}")
                screenshot_analyses.append({
                    "url": url,
                    "analysis": analysis
                })
        
        # Get knowledge context for synthesis
        kb_context = await self._get_knowledge_context(
            query="design patterns typography color layout trends",
            max_sections=5
        )
        
        # Synthesize research
        synthesis_prompt = WEB_RESEARCH_SYNTHESIS_PROMPT.format(
            queries=json.dumps(queries),
            results=json.dumps(all_results),
            screenshot_analyses=json.dumps(screenshot_analyses),
            knowledge_context=kb_context
        )
        
        synthesis_result, response = await self.gemini.generate_json(
            prompt=synthesis_prompt,
            model=GEMINI_PRO,
            system_instruction=self.system_prompt,
            temperature=0.7
        )
        
        web_research = WebResearchResult(
            queries=queries,
            search_results=all_results,
            screenshot_analyses=screenshot_analyses,
            synthesis=synthesis_result,
            tokens_used=response.total_tokens
        )
        
        # Store results
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET web_research_results = $2,
                phase_progress = 100,
                gemini_pro_tokens = gemini_pro_tokens + $3
            WHERE id = $1
            """,
            session_id,
            json.dumps({
                "queries": queries,
                "search_results": all_results,
                "screenshot_analyses": screenshot_analyses,
                "synthesis": synthesis_result
            }),
            response.total_tokens
        )
        
        await self._emit_event(session_id, "phase_complete", {
            "phase": "web_research",
            "queries_executed": len(queries),
            "screenshots_analyzed": len(screenshot_analyses),
            "key_insights": synthesis_result.get("key_insights", [])[:3]
        })
        
        logger.info(f"[MUSE] Web research complete for session {session_id}")
        return web_research
    
    # ========================================================================
    # PHASE 3: MOOD BOARD GENERATION
    # ========================================================================
    
    async def generate_moodboards(
        self,
        session_id: int,
        count: int = 4
    ) -> List[MoodBoard]:
        """
        Generate multiple mood board options based on research.
        
        Phase 3 of the research pipeline.
        """
        await self.update_session_status(
            session_id, "generating_moodboards", "moodboard_generation", 0,
            f"Generating {count} mood board options..."
        )
        
        # Get session and all analyses
        session = await self.get_session(session_id)
        inspiration_analyses = await db.fetch(
            """
            SELECT gemini_analysis FROM muse_inspiration_inputs 
            WHERE session_id = $1 AND analysis_complete = TRUE
            """,
            session_id
        )
        
        # Get comprehensive knowledge context for mood board generation
        kb_context = await self._get_knowledge_context(
            query="design patterns hero sections typography color theory bento grids",
            max_sections=8,
            max_tokens=6000
        )
        
        # Build prompt
        prompt = MOOD_BOARD_GENERATION_PROMPT.format(
            count=count,
            brief_analysis=session.get("brief_analysis", "{}"),
            inspiration_analyses=json.dumps([r["gemini_analysis"] for r in inspiration_analyses]),
            web_research=json.dumps(session.get("web_research_results", [])),
            target_audience=session.get("target_audience") or "General",
            brand_keywords=", ".join(session.get("brand_keywords") or []),
            anti_patterns=session.get("anti_patterns") or "None specified",
            knowledge_context=kb_context
        )
        
        await self._emit_event(session_id, "phase_started", {
            "phase": "moodboard_generation",
            "count": count
        })
        
        # Generate mood boards
        result, response = await self.gemini.generate_json(
            prompt=prompt,
            model=GEMINI_PRO,
            system_instruction=self.system_prompt,
            max_tokens=8000,
            temperature=0.9  # Higher temperature for creative diversity
        )
        
        # Parse and store mood boards
        moodboards = []
        options = result if isinstance(result, list) else result.get("options", result.get("moodboards", []))
        
        for i, mb_data in enumerate(options):
            # Store in database
            db_result = await db.fetchrow(
                """
                INSERT INTO muse_moodboards 
                (session_id, option_number, title, description, aesthetic_movement,
                 emotional_tone, color_palette, color_rationale, heading_font,
                 heading_font_url, body_font, body_font_url, font_rationale,
                 imagery_style, iconography_style, pattern_usage, layout_philosophy,
                 spacing_approach, motion_philosophy, recommended_animations,
                 preview_data, generation_prompt, gemini_tokens_used)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                        $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
                RETURNING id
                """,
                session_id,
                mb_data.get("option_number", i + 1),
                mb_data.get("title", f"Option {i + 1}"),
                mb_data.get("description", ""),
                mb_data.get("aesthetic_movement", ""),
                mb_data.get("emotional_tone", []),
                json.dumps(mb_data.get("color_palette", {})),
                mb_data.get("color_rationale", ""),
                mb_data.get("typography", {}).get("heading_font", ""),
                mb_data.get("typography", {}).get("heading_font_url", ""),
                mb_data.get("typography", {}).get("body_font", ""),
                mb_data.get("typography", {}).get("body_font_url", ""),
                mb_data.get("typography", {}).get("font_rationale", ""),
                mb_data.get("visual_elements", {}).get("imagery_style", ""),
                mb_data.get("visual_elements", {}).get("iconography", {}).get("style", ""),
                mb_data.get("visual_elements", {}).get("patterns", ""),
                mb_data.get("layout_approach", {}).get("philosophy", ""),
                mb_data.get("layout_approach", {}).get("spacing", ""),
                mb_data.get("motion_language", {}).get("philosophy", ""),
                mb_data.get("motion_language", {}).get("entrance_animations", []),
                json.dumps(mb_data),
                prompt[:500],  # Store truncated prompt
                response.total_tokens // len(options)  # Approximate tokens per board
            )
            
            moodboard = MoodBoard(
                option_number=mb_data.get("option_number", i + 1),
                title=mb_data.get("title", f"Option {i + 1}"),
                description=mb_data.get("description", ""),
                aesthetic_movement=mb_data.get("aesthetic_movement", ""),
                emotional_tone=mb_data.get("emotional_tone", []),
                color_palette=mb_data.get("color_palette", {}),
                color_rationale=mb_data.get("color_rationale", ""),
                typography=mb_data.get("typography", {}),
                visual_elements=mb_data.get("visual_elements", {}),
                layout_approach=mb_data.get("layout_approach", {}),
                motion_language=mb_data.get("motion_language", {}),
                anti_patterns=mb_data.get("anti_patterns", []),
                differentiator=mb_data.get("differentiator", ""),
                tokens_used=response.total_tokens // len(options)
            )
            moodboards.append(moodboard)
            
            await self._emit_event(session_id, "moodboard_generated", {
                "option_number": moodboard.option_number,
                "title": moodboard.title,
                "primary_color": moodboard.color_palette.get("primary", "#000000")
            })
        
        # Update session
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET session_status = 'awaiting_selection',
                current_phase = 'moodboard_selection',
                phase_progress = 100,
                gemini_pro_tokens = gemini_pro_tokens + $2
            WHERE id = $1
            """,
            session_id, response.total_tokens
        )
        
        await self._emit_event(session_id, "phase_complete", {
            "phase": "moodboard_generation",
            "count": len(moodboards),
            "titles": [m.title for m in moodboards]
        })
        
        logger.info(f"[MUSE] Generated {len(moodboards)} mood boards for session {session_id}")
        return moodboards
    
    async def select_moodboard(
        self,
        session_id: int,
        moodboard_id: int,
        selection_notes: Optional[str] = None,
        time_viewing_seconds: Optional[float] = None
    ):
        """
        User selects a mood board to proceed with.
        
        Also tracks the selection for A/B testing analytics.
        
        Args:
            session_id: Research session ID
            moodboard_id: ID of the selected mood board
            selection_notes: Optional user feedback about why they chose this
            time_viewing_seconds: Optional time spent viewing before selection
        """
        # Mark as selected
        await db.execute(
            """
            UPDATE muse_moodboards 
            SET is_selected = TRUE, selection_notes = $2
            WHERE id = $1
            """,
            moodboard_id, selection_notes
        )
        
        # Unselect others
        await db.execute(
            """
            UPDATE muse_moodboards 
            SET is_selected = FALSE 
            WHERE session_id = $1 AND id != $2
            """,
            session_id, moodboard_id
        )
        
        # Update session
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET selected_moodboard_id = $2,
                session_status = 'generating_design'
            WHERE id = $1
            """,
            session_id, moodboard_id
        )
        
        # Track selection for A/B testing analytics
        await self._track_moodboard_selection(
            session_id=session_id,
            moodboard_id=moodboard_id,
            notes=selection_notes,
            time_viewing_seconds=time_viewing_seconds
        )
        
        await self._emit_event(session_id, "moodboard_selected", {
            "moodboard_id": moodboard_id
        })
        
        logger.info(f"[MUSE] Mood board {moodboard_id} selected for session {session_id}")
    
    # ========================================================================
    # A/B TESTING ANALYTICS
    # ========================================================================
    
    async def _track_moodboard_selection(
        self,
        session_id: int,
        moodboard_id: int,
        notes: Optional[str] = None,
        time_viewing_seconds: Optional[float] = None
    ):
        """
        Track mood board selection for A/B testing analytics.
        
        Records the selection event and increments the mood board's selection count.
        """
        try:
            # Record the selection event
            event_data = {}
            if notes:
                event_data["user_feedback"] = notes
            if time_viewing_seconds:
                event_data["time_viewing_seconds"] = time_viewing_seconds
            
            await db.execute(
                """
                INSERT INTO muse_moodboard_analytics 
                (session_id, moodboard_id, event_type, event_data)
                VALUES ($1, $2, 'selection', $3)
                """,
                session_id, moodboard_id, json.dumps(event_data)
            )
            
            # Increment selection count on the mood board
            await db.execute(
                """
                UPDATE muse_moodboards 
                SET selection_count = COALESCE(selection_count, 0) + 1
                WHERE id = $1
                """,
                moodboard_id
            )
            
            logger.debug(f"[MUSE] Tracked selection for moodboard {moodboard_id}")
            
        except Exception as e:
            # Don't fail the main operation if analytics fails
            logger.warning(f"[MUSE] Failed to track selection analytics: {e}")
    
    async def track_moodboard_impression(
        self,
        session_id: int,
        moodboard_id: int,
        view_duration_seconds: Optional[float] = None
    ):
        """
        Track when a user views a mood board (for A/B testing).
        
        Call this when a mood board is shown/viewed in the UI.
        
        Args:
            session_id: Research session ID
            moodboard_id: ID of the viewed mood board
            view_duration_seconds: How long the user viewed it
        """
        try:
            event_data = {}
            if view_duration_seconds:
                event_data["view_duration_seconds"] = view_duration_seconds
            
            await db.execute(
                """
                INSERT INTO muse_moodboard_analytics 
                (session_id, moodboard_id, event_type, event_data)
                VALUES ($1, $2, 'impression', $3)
                """,
                session_id, moodboard_id, json.dumps(event_data)
            )
            
        except Exception as e:
            logger.warning(f"[MUSE] Failed to track impression: {e}")
    
    async def get_moodboard_analytics(self, session_id: int) -> Dict[str, Any]:
        """
        Get A/B testing analytics for a session's mood boards.
        
        Returns selection patterns and popularity data.
        """
        try:
            # Get impression and selection counts per mood board
            analytics = await db.fetch(
                """
                SELECT 
                    mb.id,
                    mb.title,
                    mb.aesthetic_movement,
                    COALESCE(mb.selection_count, 0) as total_selections,
                    COUNT(CASE WHEN ma.event_type = 'impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN ma.event_type = 'selection' THEN 1 END) as selections
                FROM muse_moodboards mb
                LEFT JOIN muse_moodboard_analytics ma ON ma.moodboard_id = mb.id
                WHERE mb.session_id = $1
                GROUP BY mb.id, mb.title, mb.aesthetic_movement, mb.selection_count
                ORDER BY mb.option_number
                """,
                session_id
            )
            
            return {
                "session_id": session_id,
                "moodboards": [dict(r) for r in analytics]
            }
            
        except Exception as e:
            logger.error(f"[MUSE] Failed to get analytics: {e}")
            return {"session_id": session_id, "moodboards": [], "error": str(e)}
    
    # ========================================================================
    # A/B TESTING - HISTORICAL PREFERENCES
    # ========================================================================
    
    async def get_historical_preferences(
        self,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get aggregated historical preferences from A/B testing data.
        
        Used to inform mood board generation about what aesthetics users
        tend to prefer, enabling data-driven creative direction.
        
        Returns:
            Dict containing preferred aesthetics, colors, and typography patterns
        """
        try:
            # Get top performing aesthetic movements
            top_aesthetics = await db.fetch(
                """
                SELECT 
                    aesthetic_movement,
                    COUNT(*) as times_selected,
                    AVG((event_data->>'time_viewing_seconds')::FLOAT) as avg_decision_time
                FROM muse_moodboard_analytics ma
                JOIN muse_moodboards mb ON ma.moodboard_id = mb.id
                WHERE ma.event_type = 'selection'
                  AND ma.created_at > NOW() - INTERVAL '90 days'
                  AND mb.aesthetic_movement IS NOT NULL
                GROUP BY aesthetic_movement
                HAVING COUNT(*) >= 2
                ORDER BY times_selected DESC
                LIMIT $1
                """,
                limit
            )
            
            # Get most commonly selected color temperatures
            color_preferences = await db.fetch(
                """
                SELECT 
                    CASE 
                        WHEN (color_palette::jsonb->>'primary')::text LIKE '#f%' 
                             OR (color_palette::jsonb->>'primary')::text LIKE '#e%'
                        THEN 'warm'
                        WHEN (color_palette::jsonb->>'primary')::text LIKE '#0%' 
                             OR (color_palette::jsonb->>'primary')::text LIKE '#1%'
                             OR (color_palette::jsonb->>'primary')::text LIKE '#2%'
                        THEN 'cool'
                        ELSE 'neutral'
                    END as color_temperature,
                    COUNT(*) as count
                FROM muse_moodboard_analytics ma
                JOIN muse_moodboards mb ON ma.moodboard_id = mb.id
                WHERE ma.event_type = 'selection'
                  AND ma.created_at > NOW() - INTERVAL '90 days'
                GROUP BY color_temperature
                ORDER BY count DESC
                """,
            )
            
            preferences = {
                "top_aesthetics": [
                    {
                        "aesthetic": r["aesthetic_movement"],
                        "selection_count": r["times_selected"],
                        "avg_decision_time_seconds": round(r["avg_decision_time"] or 0, 1)
                    }
                    for r in top_aesthetics
                ],
                "color_temperature_preference": (
                    color_preferences[0]["color_temperature"] if color_preferences else "neutral"
                ),
                "has_sufficient_data": len(top_aesthetics) >= 3
            }
            
            logger.debug(f"[MUSE] Historical preferences: {len(top_aesthetics)} top aesthetics")
            return preferences
            
        except Exception as e:
            logger.warning(f"[MUSE] Failed to get historical preferences: {e}")
            return {
                "top_aesthetics": [],
                "color_temperature_preference": "neutral",
                "has_sufficient_data": False
            }
    
    # ========================================================================
    # STREAMING MOOD BOARD GENERATION WITH IMAGE PREVIEWS
    # ========================================================================
    
    async def generate_moodboards_streaming(
        self,
        session_id: int,
        count: int = 4,
        generate_previews: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate mood boards with streaming - yields each board as it's created.
        
        This provides real-time feedback to the user as each mood board
        is generated, with optional AI-generated visual previews using Imagen 3.
        
        Args:
            session_id: Research session ID
            count: Number of mood boards to generate (default 4)
            generate_previews: Whether to generate Imagen 3 preview images
            
        Yields:
            Dict containing mood board data as each is created
        """
        await self.update_session_status(
            session_id, "streaming_moodboards", "moodboard_generation", 0,
            f"Generating {count} mood board options..."
        )
        
        # Get session and all analyses
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        inspiration_analyses = await db.fetch(
            """
            SELECT gemini_analysis FROM muse_inspiration_inputs 
            WHERE session_id = $1 AND analysis_complete = TRUE
            """,
            session_id
        )
        
        # Get comprehensive knowledge context for mood board generation
        kb_context = await self._get_knowledge_context(
            query="design patterns hero sections typography color theory bento grids modern aesthetics",
            max_sections=8,
            max_tokens=6000
        )
        
        # Fetch historical user preferences for data-driven generation
        historical_prefs = await self.get_historical_preferences(limit=10)
        
        await self._emit_event(session_id, "phase_started", {
            "phase": "moodboard_streaming",
            "count": count,
            "will_generate_previews": generate_previews and self.can_generate_images,
            "using_historical_preferences": historical_prefs.get("has_sufficient_data", False)
        })
        
        generated_count = 0
        errors = []
        
        # Generate each mood board individually for streaming
        for i in range(count):
            try:
                # Calculate progress
                base_progress = int((i / count) * 100)
                await self.update_session_status(
                    session_id, "streaming_moodboards", "moodboard_generation", base_progress,
                    f"Creating mood board {i + 1} of {count}..."
                )
                
                # Build the generation prompt with context and historical preferences
                single_prompt = self._build_single_moodboard_prompt(
                    option_number=i + 1,
                    total_count=count,
                    session=session,
                    inspiration_analyses=[r["gemini_analysis"] for r in inspiration_analyses],
                    kb_context=kb_context,
                    historical_preferences=historical_prefs
                )
                
                # Generate mood board content
                result, response = await self.gemini.generate_json(
                    prompt=single_prompt,
                    model=GEMINI_PRO,
                    system_instruction=self.system_prompt,
                    max_tokens=3000,
                    temperature=0.9  # High creativity for diversity
                )
                
                if not result:
                    logger.warning(f"[MUSE] Empty result for mood board {i + 1}")
                    errors.append(f"Mood board {i + 1} generation failed")
                    continue
                
                # Store in database (without image initially)
                db_result = await db.fetchrow(
                    """
                    INSERT INTO muse_moodboards 
                    (session_id, option_number, title, description, aesthetic_movement,
                     emotional_tone, color_palette, color_rationale, heading_font,
                     heading_font_url, body_font, body_font_url, font_rationale,
                     imagery_style, iconography_style, pattern_usage, layout_philosophy,
                     spacing_approach, motion_philosophy, recommended_animations,
                     preview_data, generation_prompt, gemini_tokens_used)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                            $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
                    RETURNING id
                    """,
                    session_id,
                    i + 1,
                    result.get("title", f"Option {i + 1}"),
                    result.get("description", ""),
                    result.get("aesthetic_movement", ""),
                    result.get("emotional_tone", []),
                    json.dumps(result.get("color_palette", {})),
                    result.get("color_rationale", ""),
                    result.get("typography", {}).get("heading_font", ""),
                    result.get("typography", {}).get("heading_font_url", ""),
                    result.get("typography", {}).get("body_font", ""),
                    result.get("typography", {}).get("body_font_url", ""),
                    result.get("typography", {}).get("font_rationale", ""),
                    result.get("visual_elements", {}).get("imagery_style", ""),
                    result.get("visual_elements", {}).get("iconography", {}).get("style", ""),
                    result.get("visual_elements", {}).get("patterns", ""),
                    result.get("layout_approach", {}).get("philosophy", ""),
                    result.get("layout_approach", {}).get("spacing", ""),
                    result.get("motion_language", {}).get("philosophy", ""),
                    result.get("motion_language", {}).get("entrance_animations", []),
                    json.dumps(result),
                    single_prompt[:500],
                    response.total_tokens
                )
                
                moodboard_id = db_result["id"]
                preview_image_b64 = None
                preview_prompt = None
                
                # Generate preview image if enabled
                if generate_previews and self.can_generate_images:
                    await self._emit_event(session_id, "moodboard_generating_image", {
                        "option_number": i + 1,
                        "moodboard_id": moodboard_id,
                        "title": result.get("title", f"Option {i + 1}")
                    })
                    
                    preview_image_b64, preview_prompt = await self.generate_moodboard_preview(
                        moodboard_data=result,
                        aspect_ratio="16:9"
                    )
                    
                    if preview_image_b64:
                        # Store the preview image in database
                        await db.execute(
                            """
                            UPDATE muse_moodboards 
                            SET preview_image_generated = $2,
                                preview_generation_prompt = $3
                            WHERE id = $1
                            """,
                            moodboard_id,
                            preview_image_b64,
                            preview_prompt
                        )
                        logger.info(f"[MUSE] Preview image stored for mood board {moodboard_id}")
                        
                        # Emit preview generated event for real-time UI update
                        await self._emit_event(session_id, "moodboard_preview_generated", {
                            "moodboard_id": moodboard_id,
                            "preview_image_b64": preview_image_b64,
                            "progress": i + 1,
                            "total": count
                        })
                
                generated_count += 1
                
                # Emit SSE event with complete mood board data
                await self._emit_event(session_id, "moodboard_generated", {
                    "option_number": i + 1,
                    "total": count,
                    "moodboard_id": moodboard_id,
                    "title": result.get("title", f"Option {i + 1}"),
                    "description": result.get("description", "")[:200],
                    "aesthetic_movement": result.get("aesthetic_movement", ""),
                    "emotional_tone": result.get("emotional_tone", [])[:3],
                    "primary_color": self._extract_primary_color(result.get("color_palette", {})),
                    "has_preview_image": preview_image_b64 is not None,
                    "progress": int(((i + 1) / count) * 100)
                })
                
                # Yield the complete mood board data
                yield {
                    "id": moodboard_id,
                    "option_number": i + 1,
                    "title": result.get("title", f"Option {i + 1}"),
                    "description": result.get("description", ""),
                    "aesthetic_movement": result.get("aesthetic_movement", ""),
                    "emotional_tone": result.get("emotional_tone", []),
                    "color_palette": result.get("color_palette", {}),
                    "typography": result.get("typography", {}),
                    "visual_elements": result.get("visual_elements", {}),
                    "layout_approach": result.get("layout_approach", {}),
                    "motion_language": result.get("motion_language", {}),
                    "preview_image_b64": preview_image_b64,
                    "is_last": i == count - 1
                }
                
            except Exception as e:
                logger.error(f"[MUSE] Error generating mood board {i + 1}: {e}")
                errors.append(f"Mood board {i + 1}: {str(e)}")
                
                # Emit error event but continue with remaining boards
                await self._emit_event(session_id, "moodboard_error", {
                    "option_number": i + 1,
                    "error": str(e)[:100]
                })
                continue
        
        # Final status update
        if generated_count > 0:
            await db.execute(
                """
                UPDATE muse_research_sessions 
                SET session_status = 'awaiting_selection',
                    current_phase = 'moodboard_selection',
                    phase_progress = 100,
                    phase_message = $2
                WHERE id = $1
                """,
                session_id,
                f"Generated {generated_count} mood boards"
            )
            
            await self._emit_event(session_id, "phase_complete", {
                "phase": "moodboard_streaming",
                "generated_count": generated_count,
                "requested_count": count,
                "errors": errors if errors else None
            })
            
            logger.info(f"[MUSE] Streamed {generated_count}/{count} mood boards for session {session_id}")
        else:
            # All failed
            await self.update_session_status(
                session_id, "failed", "moodboard_generation", 0,
                f"Failed to generate mood boards: {'; '.join(errors)}"
            )
            logger.error(f"[MUSE] All mood board generations failed for session {session_id}")
    
    def _build_single_moodboard_prompt(
        self,
        option_number: int,
        total_count: int,
        session: Dict[str, Any],
        inspiration_analyses: List[Any],
        kb_context: str,
        historical_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a detailed prompt for generating a single mood board.
        
        Incorporates historical A/B testing data to favor aesthetics that
        users have previously preferred, while maintaining creative diversity.
        """
        
        # Define aesthetic directions to encourage diversity
        aesthetic_hints = [
            "minimalist with bold accents",
            "warm and approachable",
            "sophisticated and premium",
            "vibrant and energetic",
            "calm and serene",
            "bold and editorial"
        ]
        hint = aesthetic_hints[(option_number - 1) % len(aesthetic_hints)]
        
        # Build historical preferences section if data is available
        historical_section = ""
        if historical_preferences and historical_preferences.get("has_sufficient_data"):
            top_aesthetics = historical_preferences.get("top_aesthetics", [])
            color_pref = historical_preferences.get("color_temperature_preference", "neutral")
            
            if top_aesthetics:
                top_names = [a["aesthetic"] for a in top_aesthetics[:3]]
                historical_section = f"""
HISTORICAL USER PREFERENCES (from A/B testing data):
- Users have frequently selected these aesthetic movements: {", ".join(top_names)}
- Preferred color temperature: {color_pref}
Consider incorporating elements from these popular directions while maintaining
uniqueness. This is guidance, not a requirement - creative diversity is important."""
        
        return f"""Generate mood board option {option_number} of {total_count}.

Consider this aesthetic direction for variety: {hint}
{historical_section}

BRIEF ANALYSIS:
{json.dumps(session.get("brief_analysis", {}), indent=2)}

INSPIRATION ANALYSES:
{json.dumps(inspiration_analyses, indent=2)}

WEB RESEARCH:
{json.dumps(session.get("web_research_results", []), indent=2)}

TARGET AUDIENCE: {session.get("target_audience") or "General"}
BRAND KEYWORDS: {", ".join(session.get("brand_keywords") or []) or "Not specified"}
ANTI-PATTERNS TO AVOID: {session.get("anti_patterns") or "None specified"}

DESIGN KNOWLEDGE BASE:
{kb_context}

Create a DISTINCT mood board that:
1. Has a clear, memorable title that captures the essence
2. Differs meaningfully from other options in color temperature, typography, and feel
3. Includes a complete color palette with hex codes (primary, secondary, accent, background, text)
4. Specifies typography with Google Fonts names and URLs
5. Describes the visual language including imagery style, icons, patterns
6. Defines layout philosophy and spacing approach
7. Outlines motion/animation language

Return as JSON with these exact fields:
{{
    "title": "Memorable name for this direction",
    "description": "2-3 sentence summary of the aesthetic direction",
    "aesthetic_movement": "Primary design movement (e.g., Swiss Minimalism, Neo-Brutalism)",
    "emotional_tone": ["emotion1", "emotion2", "emotion3"],
    "color_palette": {{
        "primary": "#hex",
        "secondary": "#hex",
        "accent": "#hex",
        "background": "#hex",
        "surface": "#hex",
        "text_primary": "#hex",
        "text_secondary": "#hex"
    }},
    "color_rationale": "Why these colors work for this project",
    "typography": {{
        "heading_font": "Font Name",
        "heading_font_url": "https://fonts.google.com/...",
        "body_font": "Font Name",
        "body_font_url": "https://fonts.google.com/...",
        "font_rationale": "Why these fonts work together"
    }},
    "visual_elements": {{
        "imagery_style": "Photography/illustration style",
        "iconography": {{
            "style": "Outlined/Filled/Duotone",
            "library": "Recommended icon library"
        }},
        "patterns": "Background patterns or textures if any"
    }},
    "layout_approach": {{
        "philosophy": "Overall layout approach",
        "spacing": "Spacing philosophy (airy, compact, etc.)",
        "grid": "Grid system approach"
    }},
    "motion_language": {{
        "philosophy": "Animation philosophy",
        "entrance_animations": ["animation types"],
        "micro_interactions": "Hover/click feedback style"
    }},
    "anti_patterns": ["Things to avoid"],
    "differentiator": "What makes this option unique"
}}"""
    
    def _extract_primary_color(self, color_palette: Dict[str, Any]) -> str:
        """Extract the primary color from a color palette."""
        if isinstance(color_palette, dict):
            # Try common keys
            for key in ["primary", "main", "brand", "accent"]:
                if key in color_palette:
                    value = color_palette[key]
                    if isinstance(value, str) and value.startswith("#"):
                        return value
            # Return first hex color found
            for value in color_palette.values():
                if isinstance(value, str) and value.startswith("#"):
                    return value
        return "#6366F1"  # Default indigo
    
    # ========================================================================
    # SVG FALLBACK PREVIEW (When Imagen unavailable)
    # ========================================================================
    
    def _generate_svg_fallback_preview(self, color_palette: Dict[str, Any]) -> str:
        """
        Generate a simple SVG-based preview as fallback when Imagen is unavailable.
        
        Creates a visually appealing abstract representation of the color palette.
        
        Args:
            color_palette: Dict with color hex values
            
        Returns:
            Base64-encoded SVG data
        """
        primary = color_palette.get("primary", "#6366F1")
        secondary = color_palette.get("secondary", "#8B5CF6")
        accent = color_palette.get("accent", "#EC4899")
        background = color_palette.get("background", "#0F0F0F")
        
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{background};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{primary}33;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="accent-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{primary}" />
      <stop offset="100%" style="stop-color:{secondary}" />
    </linearGradient>
  </defs>
  <rect width="800" height="450" fill="url(#bg)"/>
  <circle cx="200" cy="150" r="80" fill="{primary}" opacity="0.8"/>
  <circle cx="350" cy="200" r="60" fill="{secondary}" opacity="0.6"/>
  <circle cx="280" cy="280" r="40" fill="{accent}" opacity="0.9"/>
  <rect x="500" y="100" width="200" height="250" rx="20" fill="{primary}22" stroke="{primary}" stroke-width="2"/>
  <line x1="520" y1="150" x2="680" y2="150" stroke="url(#accent-grad)" stroke-width="8" stroke-linecap="round"/>
  <line x1="520" y1="180" x2="650" y2="180" stroke="{secondary}88" stroke-width="4" stroke-linecap="round"/>
  <line x1="520" y1="200" x2="620" y2="200" stroke="{secondary}44" stroke-width="3" stroke-linecap="round"/>
  <rect x="520" y="250" width="60" height="30" rx="15" fill="{accent}"/>
  <text x="400" y="420" text-anchor="middle" fill="{secondary}66" font-family="system-ui" font-size="14">Design Concept Preview</text>
</svg>'''
        
        return base64.b64encode(svg.encode()).decode()
    
    # ========================================================================
    # A/B TESTING ANALYTICS (NEW)
    # ========================================================================
    
    async def track_moodboard_selection(
        self,
        session_id: int,
        moodboard_id: int,
        selection_time_seconds: Optional[int] = None
    ) -> int:
        """
        Track mood board selection for A/B testing analytics.
        
        Captures data about which options were presented, which was selected,
        and characteristics that can be used for learning.
        
        Returns:
            Analytics record ID
        """
        # Get session and moodboard data
        session = await self.get_session(session_id)
        selected_mb = await db.fetchrow(
            "SELECT * FROM muse_moodboards WHERE id = $1",
            moodboard_id
        )
        
        if not session or not selected_mb:
            raise ValueError("Session or moodboard not found")
        
        # Get all presented options
        all_moodboards = await db.fetch(
            "SELECT * FROM muse_moodboards WHERE session_id = $1",
            session_id
        )
        
        # Analyze color temperature
        color_palette = json.loads(selected_mb["color_palette"]) if selected_mb["color_palette"] else {}
        color_temp = self._analyze_color_temperature(color_palette.get("primary", "#6366F1"))
        
        # Determine typography style
        heading_font = selected_mb["heading_font"] or ""
        typo_style = self._classify_typography_style(heading_font)
        
        # Extract rejected options
        rejected_movements = [
            mb["aesthetic_movement"] for mb in all_moodboards 
            if mb["id"] != moodboard_id
        ]
        
        # Get brief keywords
        brief_analysis = session.get("brief_analysis")
        keywords = []
        if brief_analysis:
            try:
                analysis = json.loads(brief_analysis) if isinstance(brief_analysis, str) else brief_analysis
                keywords = list(analysis.get("synthesis", {}).keys())[:10]
            except:
                pass
        
        # Store analytics
        result = await db.fetchrow(
            """
            INSERT INTO muse_moodboard_analytics 
            (session_id, presented_options, selected_option_number, selection_time_seconds,
             selected_movement, selected_color_temp, selected_typography_style,
             rejected_movements, brief_keywords, target_audience_segment)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
            """,
            session_id,
            len(all_moodboards),
            selected_mb["option_number"],
            selection_time_seconds,
            selected_mb["aesthetic_movement"],
            color_temp,
            typo_style,
            rejected_movements,
            keywords,
            session.get("target_audience")
        )
        
        logger.info(f"[MUSE] Tracked selection analytics for session {session_id}")
        return result["id"]
    
    def _analyze_color_temperature(self, hex_color: str) -> str:
        """Classify a color as warm, cool, or neutral."""
        try:
            hex_clean = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
            
            # Simple heuristic based on RGB values
            if r > b and r > g * 0.8:
                return "warm"
            elif b > r and b > g * 0.8:
                return "cool"
            else:
                return "neutral"
        except:
            return "neutral"
    
    def _classify_typography_style(self, font_name: str) -> str:
        """Classify a font as serif, sans-serif, or display."""
        font_lower = font_name.lower()
        
        serif_indicators = ["serif", "georgia", "times", "garamond", "palatino", "merriweather"]
        display_indicators = ["display", "playfair", "lobster", "pacifico", "bebas", "impact"]
        
        if any(ind in font_lower for ind in serif_indicators):
            return "serif"
        elif any(ind in font_lower for ind in display_indicators):
            return "display"
        else:
            return "sans-serif"
    
    async def update_analytics_satisfaction(
        self,
        session_id: int,
        satisfaction_score: int,
        final_approved: bool = False
    ):
        """Update analytics with user satisfaction after approval."""
        await db.execute(
            """
            UPDATE muse_moodboard_analytics 
            SET user_satisfaction_score = $2,
                final_approved = $3
            WHERE session_id = $1
            """,
            session_id,
            satisfaction_score,
            final_approved
        )
    
    async def get_selection_patterns(self) -> List[Dict[str, Any]]:
        """Get aggregated selection patterns for improving generation."""
        patterns = await db.fetch(
            "SELECT * FROM muse_selection_patterns ORDER BY selection_count DESC LIMIT 20"
        )
        return [dict(p) for p in patterns]
    
    # ========================================================================
    # PHASE 4: STYLE GUIDE GENERATION
    # ========================================================================
    
    async def generate_style_guide(
        self,
        session_id: int,
        revision_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete style guide from selected mood board.
        
        Phase 4 of the research pipeline.
        
        Args:
            session_id: The research session ID
            revision_feedback: Optional feedback from user for revisions
        """
        status_message = "Revising style guide based on your feedback..." if revision_feedback else "Generating comprehensive style guide..."
        await self.update_session_status(
            session_id, "generating_design", "style_guide_generation", 0,
            status_message
        )
        
        # Get session and selected mood board
        session = await self.get_session(session_id)
        moodboard = await db.fetchrow(
            "SELECT * FROM muse_moodboards WHERE id = $1",
            session["selected_moodboard_id"]
        )
        
        if not moodboard:
            raise ValueError("No mood board selected")
        
        # Get inspiration analyses
        inspiration_analyses = await db.fetch(
            """
            SELECT gemini_analysis FROM muse_inspiration_inputs 
            WHERE session_id = $1 AND analysis_complete = TRUE
            """,
            session_id
        )
        
        # Get comprehensive knowledge context for style guide
        kb_context = await self._get_knowledge_context(
            query="design systems typography scale color tokens spacing components shadcn aceternity",
            max_sections=10,
            max_tokens=8000
        )
        
        # Build prompt
        prompt = STYLE_GUIDE_GENERATION_PROMPT.format(
            selected_moodboard=moodboard["preview_data"],
            brief=session["design_brief"],
            inspiration_analyses=json.dumps([r["gemini_analysis"] for r in inspiration_analyses]),
            knowledge_context=kb_context
        )
        
        # Add revision feedback if provided
        if revision_feedback:
            prompt += f"""

## USER REVISION FEEDBACK
The user has reviewed the previous style guide and provided the following feedback.
You MUST incorporate these changes into the new style guide:

{revision_feedback}

IMPORTANT: Address each point of feedback specifically. The new style guide should reflect 
all requested changes while maintaining design coherence and the overall aesthetic direction.
"""
        
        await self._emit_event(session_id, "phase_started", {
            "phase": "style_guide_revision" if revision_feedback else "style_guide_generation",
            "is_revision": revision_feedback is not None
        })
        
        # Generate style guide
        result, response = await self.gemini.generate_json(
            prompt=prompt,
            model=GEMINI_PRO,
            system_instruction=self.system_prompt,
            max_tokens=12000,
            temperature=0.6  # Lower temperature for consistency
        )
        
        # Generate Nicole handoff summary
        nicole_summary = self._generate_nicole_summary(result, moodboard)
        result["nicoleHandoff"] = {
            "summary": nicole_summary,
            "criticalDecisions": result.get("antiPatterns", [])[:5],
            "codePatterns": []
        }
        
        # Store in database
        style_guide_result = await db.fetchrow(
            """
            INSERT INTO muse_style_guides 
            (session_id, moodboard_id, project_id, colors, typography, spacing,
             borders, radii, shadows, animations, breakpoints, imagery_guidelines,
             iconography_source, iconography_style, component_specs, layout_specs,
             anti_patterns, tailwind_config, css_variables, implementation_notes,
             nicole_context_summary)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21)
            RETURNING id
            """,
            session_id,
            moodboard["id"],
            session["project_id"],
            json.dumps(result.get("colors", {})),
            json.dumps(result.get("typography", {})),
            json.dumps(result.get("spacing", {})),
            json.dumps(result.get("borders", {})),
            json.dumps(result.get("radii", {})),
            json.dumps(result.get("shadows", {})),
            json.dumps(result.get("animations", {})),
            json.dumps(result.get("breakpoints", {})),
            result.get("imagery", {}).get("guidelines", ""),
            result.get("iconography", {}).get("library", "lucide-react"),
            result.get("iconography", {}).get("style", "outline"),
            json.dumps(result.get("components", {})),
            json.dumps(result.get("layout", {})),
            json.dumps(result.get("antiPatterns", [])),
            json.dumps(result.get("implementationNotes", {}).get("tailwindExtend", {})),
            result.get("implementationNotes", {}).get("cssVariables", ""),
            result.get("implementationNotes", {}).get("componentNotes", ""),
            nicole_summary
        )
        
        # Update session
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET approved_style_guide_id = $2,
                session_status = 'awaiting_approval',
                current_phase = 'design_approval',
                phase_progress = 100,
                gemini_pro_tokens = gemini_pro_tokens + $3
            WHERE id = $1
            """,
            session_id, style_guide_result["id"], response.total_tokens
        )
        
        await self._emit_event(session_id, "phase_complete", {
            "phase": "style_guide_generation",
            "style_guide_id": style_guide_result["id"]
        })
        
        logger.info(f"[MUSE] Generated style guide for session {session_id}")
        return result
    
    def _generate_nicole_summary(
        self,
        style_guide: Dict[str, Any],
        moodboard: Dict[str, Any]
    ) -> str:
        """Generate condensed summary for Nicole's context."""
        colors = style_guide.get("colors", {})
        typography = style_guide.get("typography", {})
        
        summary = f"""
## DESIGN SYSTEM: {moodboard.get('title', 'Custom Design')}

### AESTHETIC DIRECTION
{moodboard.get('description', '')}

### COLOR PALETTE
- Primary: {colors.get('primary', {}).get('500', 'N/A')}
- Secondary: {colors.get('secondary', {}).get('500', 'N/A')}
- Accent: {colors.get('accent', {}).get('500', 'N/A')}
- Background: {colors.get('background', {}).get('page', colors.get('background', {}).get('primary', 'N/A'))}

### TYPOGRAPHY
- Headings: {typography.get('families', {}).get('heading', {}).get('name', 'N/A')}
- Body: {typography.get('families', {}).get('body', {}).get('name', 'N/A')}
- Scale: {typography.get('scale', {}).get('base', {}).get('size', '1rem')} base

### ICONOGRAPHY
- Library: {style_guide.get('iconography', {}).get('library', 'lucide-react')}
- Style: {style_guide.get('iconography', {}).get('style', 'outline')}

### ANTI-PATTERNS (DO NOT DO)
{chr(10).join('- ' + str(ap) for ap in style_guide.get('antiPatterns', [])[:5])}

### CRITICAL IMPLEMENTATION NOTES
{style_guide.get('implementationNotes', {}).get('componentNotes', 'Follow the style guide precisely.')}
"""
        return summary.strip()
    
    # ========================================================================
    # PHASE 5: APPROVAL & HANDOFF
    # ========================================================================
    
    async def approve_design(self, session_id: int) -> Dict[str, Any]:
        """
        User approves the design - ready for Nicole handoff.
        """
        # Update style guide as approved
        session = await self.get_session(session_id)
        
        await db.execute(
            """
            UPDATE muse_style_guides 
            SET is_approved = TRUE, approved_at = NOW()
            WHERE id = $1
            """,
            session["approved_style_guide_id"]
        )
        
        # Update session
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET session_status = 'approved',
                completed_at = NOW()
            WHERE id = $1
            """,
            session_id
        )
        
        # Update project to use this style guide
        await db.execute(
            """
            UPDATE enjineer_projects 
            SET research_session_id = $1,
                active_style_guide_id = $2
            WHERE id = $3
            """,
            session_id,
            session["approved_style_guide_id"],
            session["project_id"]
        )
        
        await self._emit_event(session_id, "design_approved", {
            "ready_for_coding": True
        })
        
        logger.info(f"[MUSE] Design approved for session {session_id}")
        
        # Return handoff data for Nicole
        return await self.get_nicole_handoff(session_id)
    
    async def get_nicole_handoff(self, session_id: int) -> Dict[str, Any]:
        """
        Get complete handoff package for Nicole.
        """
        session = await self.get_session(session_id)
        style_guide = await db.fetchrow(
            "SELECT * FROM muse_style_guides WHERE id = $1",
            session["approved_style_guide_id"]
        )
        moodboard = await db.fetchrow(
            "SELECT * FROM muse_moodboards WHERE id = $1",
            session["selected_moodboard_id"]
        )
        
        return {
            "session_id": session_id,
            "project_id": session["project_id"],
            "design_brief": session["design_brief"],
            "moodboard": {
                "title": moodboard["title"],
                "description": moodboard["description"],
                "aesthetic_movement": moodboard["aesthetic_movement"],
                "emotional_tone": moodboard["emotional_tone"]
            },
            "style_guide": {
                "colors": json.loads(style_guide["colors"]) if style_guide["colors"] else {},
                "typography": json.loads(style_guide["typography"]) if style_guide["typography"] else {},
                "spacing": json.loads(style_guide["spacing"]) if style_guide["spacing"] else {},
                "components": json.loads(style_guide["component_specs"]) if style_guide["component_specs"] else {},
                "iconography": {
                    "library": style_guide["iconography_source"],
                    "style": style_guide["iconography_style"]
                }
            },
            "nicole_context": style_guide["nicole_context_summary"],
            "anti_patterns": json.loads(style_guide["anti_patterns"]) if style_guide["anti_patterns"] else []
        }
    
    # ========================================================================
    # STYLE GUIDE EXPORT (NEW)
    # ========================================================================
    
    async def export_style_guide(
        self,
        style_guide_id: int,
        export_format: str,
        user_id: Optional[str] = None,
        use_cache: bool = True,
        cache_ttl_hours: int = 24
    ) -> str:
        """
        Export style guide in various formats with caching.
        
        Supported formats:
        - figma_tokens: Figma design tokens JSON
        - css_variables: CSS custom properties
        - tailwind_config: Tailwind CSS configuration
        - design_tokens_json: W3C Design Tokens format
        
        Args:
            style_guide_id: ID of the style guide to export
            export_format: One of the supported export formats
            user_id: Optional user ID for tracking
            use_cache: Whether to use cached exports if available
            cache_ttl_hours: Cache time-to-live in hours (default 24)
        
        Returns:
            Exported content as string
        """
        # Check cache first if enabled
        if use_cache:
            cached = await db.fetchrow(
                """
                SELECT export_data FROM muse_style_guide_exports 
                WHERE style_guide_id = $1 
                  AND export_format = $2
                  AND created_at > NOW() - INTERVAL '1 hour' * $3
                ORDER BY created_at DESC
                LIMIT 1
                """,
                style_guide_id,
                export_format,
                cache_ttl_hours
            )
            
            if cached and cached["export_data"]:
                logger.debug(f"[MUSE] Using cached export for style guide {style_guide_id}")
                return cached["export_data"]
        
        # Get style guide
        sg = await db.fetchrow(
            "SELECT * FROM muse_style_guides WHERE id = $1",
            style_guide_id
        )
        
        if not sg:
            raise ValueError(f"Style guide {style_guide_id} not found")
        
        # Parse JSON fields with safe defaults
        colors = json.loads(sg["colors"]) if sg.get("colors") else {}
        typography = json.loads(sg["typography"]) if sg.get("typography") else {}
        spacing = json.loads(sg["spacing"]) if sg.get("spacing") else {}
        radii = json.loads(sg["radii"]) if sg.get("radii") else {}
        shadows = json.loads(sg["shadows"]) if sg.get("shadows") else {}
        
        # Generate export based on format
        if export_format == "figma_tokens":
            export_content = self._export_figma_tokens(colors, typography, spacing, radii, shadows)
        elif export_format == "css_variables":
            export_content = self._export_css_variables(colors, typography, spacing, radii, shadows)
        elif export_format == "tailwind_config":
            export_content = self._export_tailwind_config(colors, typography, spacing, radii, shadows)
        elif export_format == "design_tokens_json":
            export_content = self._export_design_tokens(colors, typography, spacing, radii, shadows)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        # Store export record for caching and audit trail
        await db.execute(
            """
            INSERT INTO muse_style_guide_exports 
            (style_guide_id, export_format, export_data, exported_by_user_id)
            VALUES ($1, $2, $3, $4)
            """,
            style_guide_id,
            export_format,
            export_content,
            user_id
        )
        
        # Update style guide cache timestamp
        cache_column = {
            "figma_tokens": "last_export_figma_tokens",
            "css_variables": "last_export_css_variables",
            "tailwind_config": "last_export_tailwind_config"
        }.get(export_format)
        
        if cache_column:
            await db.execute(
                f"UPDATE muse_style_guides SET {cache_column} = NOW() WHERE id = $1",
                style_guide_id
            )
        
        logger.info(f"[MUSE] Exported style guide {style_guide_id} as {export_format}")
        return export_content
    
    def _export_figma_tokens(
        self,
        colors: dict,
        typography: dict,
        spacing: dict,
        radii: dict,
        shadows: dict
    ) -> str:
        """Export as Figma design tokens JSON."""
        tokens = {
            "global": {
                "colors": self._flatten_colors_for_tokens(colors),
                "typography": {
                    "fontFamilies": typography.get("families", {}),
                    "fontSizes": typography.get("scale", {}),
                    "fontWeights": typography.get("weights", {}),
                    "lineHeights": typography.get("lineHeights", {}),
                    "letterSpacing": typography.get("letterSpacing", {})
                },
                "spacing": spacing.get("scale", {}),
                "borderRadius": radii,
                "boxShadow": shadows
            }
        }
        return json.dumps(tokens, indent=2)
    
    def _export_css_variables(
        self,
        colors: dict,
        typography: dict,
        spacing: dict,
        radii: dict,
        shadows: dict
    ) -> str:
        """Export as CSS custom properties."""
        lines = [":root {"]
        
        # Colors
        lines.append("  /* Colors */")
        for category, shades in colors.items():
            if isinstance(shades, dict):
                for shade, value in shades.items():
                    if isinstance(value, str) and value.startswith("#"):
                        lines.append(f"  --color-{category}-{shade}: {value};")
                    elif isinstance(value, dict) and "hex" in value:
                        lines.append(f"  --color-{category}-{shade}: {value['hex']};")
        
        # Typography
        lines.append("\n  /* Typography */")
        families = typography.get("families", {})
        for name, family in families.items():
            if isinstance(family, dict):
                lines.append(f"  --font-{name}: '{family.get('name', family)}', {family.get('fallback', 'sans-serif')};")
            else:
                lines.append(f"  --font-{name}: '{family}', sans-serif;")
        
        scale = typography.get("scale", {})
        for size, value in scale.items():
            if isinstance(value, dict):
                lines.append(f"  --text-{size}: {value.get('size', '1rem')};")
            else:
                lines.append(f"  --text-{size}: {value};")
        
        # Spacing
        lines.append("\n  /* Spacing */")
        space_scale = spacing.get("scale", {})
        for name, value in space_scale.items():
            if isinstance(value, (int, float)):
                lines.append(f"  --spacing-{name}: {value}rem;")
            else:
                lines.append(f"  --spacing-{name}: {value};")
        
        # Border Radius
        lines.append("\n  /* Border Radius */")
        for name, value in radii.items():
            lines.append(f"  --radius-{name}: {value};")
        
        # Shadows
        lines.append("\n  /* Shadows */")
        for name, value in shadows.items():
            lines.append(f"  --shadow-{name}: {value};")
        
        lines.append("}")
        return "\n".join(lines)
    
    def _export_tailwind_config(
        self,
        colors: dict,
        typography: dict,
        spacing: dict,
        radii: dict,
        shadows: dict
    ) -> str:
        """Export as Tailwind CSS configuration."""
        config = {
            "theme": {
                "extend": {
                    "colors": self._flatten_colors_for_tailwind(colors),
                    "fontFamily": {},
                    "fontSize": {},
                    "spacing": {},
                    "borderRadius": radii,
                    "boxShadow": shadows
                }
            }
        }
        
        # Font families
        families = typography.get("families", {})
        for name, family in families.items():
            if isinstance(family, dict):
                config["theme"]["extend"]["fontFamily"][name] = [
                    family.get("name", family),
                    family.get("fallback", "sans-serif")
                ]
            else:
                config["theme"]["extend"]["fontFamily"][name] = [family, "sans-serif"]
        
        # Font sizes with line heights
        scale = typography.get("scale", {})
        for size, value in scale.items():
            if isinstance(value, dict):
                config["theme"]["extend"]["fontSize"][size] = [
                    value.get("size", "1rem"),
                    {"lineHeight": value.get("lineHeight", "1.5")}
                ]
            else:
                config["theme"]["extend"]["fontSize"][size] = value
        
        # Spacing
        space_scale = spacing.get("scale", {})
        for name, value in space_scale.items():
            if isinstance(value, (int, float)):
                config["theme"]["extend"]["spacing"][name] = f"{value}rem"
            else:
                config["theme"]["extend"]["spacing"][name] = value
        
        # Format as TypeScript/JavaScript
        config_str = json.dumps(config, indent=2)
        return f"""import type {{ Config }} from "tailwindcss";

const config: Config = {config_str};

export default config;
"""
    
    def _export_design_tokens(
        self,
        colors: dict,
        typography: dict,
        spacing: dict,
        radii: dict,
        shadows: dict
    ) -> str:
        """Export as W3C Design Tokens format."""
        tokens = {
            "$description": "Design tokens exported from Muse Design Research Agent",
            "color": {},
            "typography": {},
            "spacing": {},
            "borderRadius": {},
            "shadow": {}
        }
        
        # Colors in W3C format
        for category, shades in colors.items():
            if isinstance(shades, dict):
                tokens["color"][category] = {}
                for shade, value in shades.items():
                    hex_value = value if isinstance(value, str) else value.get("hex", "#000000")
                    tokens["color"][category][shade] = {
                        "$type": "color",
                        "$value": hex_value
                    }
        
        # Typography
        families = typography.get("families", {})
        tokens["typography"]["fontFamily"] = {}
        for name, family in families.items():
            family_name = family.get("name", family) if isinstance(family, dict) else family
            tokens["typography"]["fontFamily"][name] = {
                "$type": "fontFamily",
                "$value": family_name
            }
        
        # Spacing
        space_scale = spacing.get("scale", {})
        for name, value in space_scale.items():
            tokens["spacing"][name] = {
                "$type": "dimension",
                "$value": f"{value}rem" if isinstance(value, (int, float)) else value
            }
        
        # Border Radius
        for name, value in radii.items():
            tokens["borderRadius"][name] = {
                "$type": "dimension",
                "$value": value
            }
        
        # Shadows
        for name, value in shadows.items():
            tokens["shadow"][name] = {
                "$type": "shadow",
                "$value": value
            }
        
        return json.dumps(tokens, indent=2)
    
    def _flatten_colors_for_tokens(self, colors: dict) -> dict:
        """Flatten nested color structure for Figma tokens."""
        flat = {}
        for category, shades in colors.items():
            if isinstance(shades, dict):
                flat[category] = {}
                for shade, value in shades.items():
                    hex_value = value if isinstance(value, str) else value.get("hex", "#000000")
                    flat[category][shade] = {"value": hex_value, "type": "color"}
        return flat
    
    def _flatten_colors_for_tailwind(self, colors: dict) -> dict:
        """Flatten colors for Tailwind format."""
        flat = {}
        for category, shades in colors.items():
            if isinstance(shades, dict):
                flat[category] = {}
                for shade, value in shades.items():
                    flat[category][shade] = value if isinstance(value, str) else value.get("hex", "#000000")
            elif isinstance(shades, str):
                flat[category] = shades
        return flat
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _emit_event(
        self,
        session_id: int,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Emit a research event for real-time updates."""
        await db.execute(
            """
            INSERT INTO muse_research_events (session_id, event_type, event_data)
            VALUES ($1, $2, $3)
            """,
            session_id, event_type, json.dumps(event_data)
        )
    
    async def run_full_pipeline(
        self,
        session_id: int,
        moodboard_count: int = 4,
        skip_web_research: bool = False,
        generate_previews: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete research pipeline up to mood board generation.
        
        Stops at mood board selection for user input.
        
        Args:
            session_id: The research session ID
            moodboard_count: Number of mood boards to generate
            skip_web_research: Skip web research phase (for faster processing)
            generate_previews: Generate Imagen 3 preview images for mood boards
        """
        try:
            # Phase 0: Research Planning (optional - can skip if answers provided)
            session = await self.get_session(session_id)
            if not session.get("research_plan"):
                await self.create_research_plan(session_id)
            
            # Phase 1: Brief Analysis
            await self.analyze_brief(session_id)
            
            # Phase 2: Inspiration Analysis (if any)
            inspirations = await db.fetch(
                "SELECT id FROM muse_inspiration_inputs WHERE session_id = $1",
                session_id
            )
            if inspirations:
                await self.analyze_all_inspirations(session_id)
            
            # Phase 2.5: Web Research (optional)
            if not skip_web_research:
                await self.conduct_web_research(session_id)
            
            # Phase 3: Generate Mood Boards with streaming and image previews
            moodboard_list = []
            async for moodboard in self.generate_moodboards_streaming(
                session_id=session_id,
                count=moodboard_count,
                generate_previews=generate_previews
            ):
                moodboard_list.append(moodboard)
            
            return {
                "success": True,
                "status": "awaiting_selection",
                "moodboard_count": len(moodboard_list),
                "has_previews": generate_previews and self.can_generate_images,
                "message": f"Generated {len(moodboard_list)} mood board options. Please select one to proceed."
            }
            
        except Exception as e:
            logger.error(f"[MUSE] Pipeline error for session {session_id}: {e}")
            await self.update_session_status(
                session_id, "failed", message=str(e)
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_pipeline_streaming(
        self,
        session_id: int,
        moodboard_count: int = 4,
        skip_web_research: bool = False,
        generate_previews: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the complete research pipeline with real-time streaming updates.
        
        Yields progress events and mood board data as they're generated.
        Use this for frontend SSE streaming.
        
        Args:
            session_id: The research session ID
            moodboard_count: Number of mood boards to generate
            skip_web_research: Skip web research phase
            generate_previews: Generate Imagen 3 preview images
            
        Yields:
            Dict events with type and data fields
        """
        try:
            # Phase 0: Research Planning
            session = await self.get_session(session_id)
            if not session:
                yield {"type": "error", "data": {"message": f"Session {session_id} not found"}}
                return
            
            yield {"type": "pipeline_started", "data": {"session_id": session_id}}
            
            if not session.get("research_plan"):
                yield {"type": "phase_started", "data": {"phase": "research_planning"}}
                await self.create_research_plan(session_id)
                yield {"type": "phase_complete", "data": {"phase": "research_planning"}}
            
            # Phase 1: Brief Analysis
            yield {"type": "phase_started", "data": {"phase": "brief_analysis"}}
            await self.analyze_brief(session_id)
            yield {"type": "phase_complete", "data": {"phase": "brief_analysis"}}
            
            # Phase 2: Inspiration Analysis
            inspirations = await db.fetch(
                "SELECT id FROM muse_inspiration_inputs WHERE session_id = $1",
                session_id
            )
            if inspirations:
                yield {"type": "phase_started", "data": {"phase": "inspiration_analysis", "count": len(inspirations)}}
                await self.analyze_all_inspirations(session_id)
                yield {"type": "phase_complete", "data": {"phase": "inspiration_analysis"}}
            
            # Phase 2.5: Web Research
            if not skip_web_research:
                yield {"type": "phase_started", "data": {"phase": "web_research"}}
                await self.conduct_web_research(session_id)
                yield {"type": "phase_complete", "data": {"phase": "web_research"}}
            
            # Phase 3: Generate Mood Boards with streaming
            yield {
                "type": "phase_started", 
                "data": {
                    "phase": "moodboard_generation",
                    "count": moodboard_count,
                    "will_generate_previews": generate_previews and self.can_generate_images
                }
            }
            
            moodboard_count_actual = 0
            async for moodboard in self.generate_moodboards_streaming(
                session_id=session_id,
                count=moodboard_count,
                generate_previews=generate_previews
            ):
                moodboard_count_actual += 1
                yield {
                    "type": "moodboard_ready",
                    "data": {
                        "moodboard_id": moodboard.get("id"),
                        "option_number": moodboard.get("option_number"),
                        "title": moodboard.get("title"),
                        "description": moodboard.get("description"),
                        "has_preview": moodboard.get("preview_image_b64") is not None,
                        "is_last": moodboard.get("is_last", False)
                    }
                }
            
            yield {
                "type": "phase_complete", 
                "data": {
                    "phase": "moodboard_generation",
                    "count": moodboard_count_actual
                }
            }
            
            yield {
                "type": "pipeline_complete",
                "data": {
                    "status": "awaiting_selection",
                    "moodboard_count": moodboard_count_actual,
                    "message": "Please select a mood board to proceed"
                }
            }
            
        except Exception as e:
            logger.error(f"[MUSE] Streaming pipeline error for session {session_id}: {e}")
            await self.update_session_status(
                session_id, "failed", message=str(e)
            )
            yield {
                "type": "error",
                "data": {
                    "message": str(e),
                    "phase": "pipeline"
                }
            }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

muse_agent = MuseAgent()

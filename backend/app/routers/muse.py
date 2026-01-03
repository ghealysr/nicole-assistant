"""
Muse Design Research Agent - API Routes.

Endpoints for design research, mood board generation, and style guide creation.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.agents.muse import muse_agent
from app.agents.muse.report_generator import report_generator
from app.database import db
from app.middleware.alphawave_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/muse", tags=["muse"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new research session."""
    project_id: int
    design_brief: str
    target_audience: Optional[str] = None
    brand_keywords: Optional[List[str]] = None
    aesthetic_preferences: Optional[str] = None
    anti_patterns: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """Response after creating a session."""
    session_id: int
    status: str
    message: str


class AddInspirationRequest(BaseModel):
    """Request to add inspiration input."""
    input_type: str = Field(..., pattern="^(image|url)$")
    data: str  # Base64 image or URL
    user_notes: Optional[str] = None
    focus_elements: Optional[List[str]] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None


class SelectMoodboardRequest(BaseModel):
    """Request to select a mood board."""
    moodboard_id: int
    selection_notes: Optional[str] = None
    time_viewing_seconds: Optional[float] = None  # For A/B testing analytics


class QuestionAnswer(BaseModel):
    """A single question-answer pair."""
    question: str
    answer: str


class SubmitAnswersRequest(BaseModel):
    """Request to submit answers to clarifying questions."""
    answers: List[QuestionAnswer]


class MoodboardSummary(BaseModel):
    """Summary of a mood board for listing."""
    id: int
    option_number: int
    title: str
    description: str
    aesthetic_movement: str
    emotional_tone: List[str]
    color_palette: Dict[str, str]
    is_selected: bool


class SessionStatus(BaseModel):
    """Current session status."""
    session_id: int
    status: str
    current_phase: str
    phase_progress: int
    phase_message: Optional[str]
    estimated_cost: float
    has_moodboards: bool
    has_style_guide: bool


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def muse_health():
    """Check if Muse agent is available."""
    return {
        "available": muse_agent.is_available,
        "message": "Muse Design Research Agent is ready" if muse_agent.is_available 
                   else "Gemini API key not configured"
    }


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_research_session(
    request: CreateSessionRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create a new design research session.
    
    This starts the research pipeline for a project.
    """
    if not muse_agent.is_available:
        raise HTTPException(
            status_code=503,
            detail="Muse agent not available - Gemini API key not configured"
        )
    
    try:
        session_id = await muse_agent.create_session(
            project_id=request.project_id,
            brief=request.design_brief,
            target_audience=request.target_audience,
            brand_keywords=request.brand_keywords,
            aesthetic_preferences=request.aesthetic_preferences,
            anti_patterns=request.anti_patterns
        )
        
        return CreateSessionResponse(
            session_id=session_id,
            status="intake",
            message="Research session created. Add inspiration images/URLs, then start research."
        )
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """Get session details."""
    session = await muse_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Calculate estimated cost
    cost = await db.fetchval(
        "SELECT calculate_research_cost($1)",
        session_id
    ) or 0.0
    
    # Check for moodboards and style guide
    moodboard_count = await db.fetchval(
        "SELECT COUNT(*) FROM muse_moodboards WHERE session_id = $1",
        session_id
    )
    has_style_guide = session["approved_style_guide_id"] is not None
    
    return {
        "session_id": session_id,
        "project_id": session["project_id"],
        "status": session["session_status"],
        "current_phase": session["current_phase"],
        "phase_progress": session["phase_progress"],
        "phase_message": session.get("phase_message"),
        "design_brief": session["design_brief"],
        "target_audience": session.get("target_audience"),
        "brand_keywords": session.get("brand_keywords"),
        "aesthetic_preferences": session.get("aesthetic_preferences"),
        "anti_patterns": session.get("anti_patterns"),
        "brief_analysis": json.loads(session["brief_analysis"]) if session.get("brief_analysis") else None,
        "estimated_cost_usd": float(cost),
        "moodboard_count": moodboard_count,
        "has_style_guide": has_style_guide,
        "selected_moodboard_id": session.get("selected_moodboard_id"),
        "created_at": session["created_at"].isoformat() if session.get("created_at") else None
    }


@router.get("/sessions/{session_id}/status", response_model=SessionStatus)
async def get_session_status(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """Get current session status for polling."""
    session = await muse_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cost = await db.fetchval(
        "SELECT calculate_research_cost($1)",
        session_id
    ) or 0.0
    
    moodboard_count = await db.fetchval(
        "SELECT COUNT(*) FROM muse_moodboards WHERE session_id = $1",
        session_id
    )
    
    return SessionStatus(
        session_id=session_id,
        status=session["session_status"],
        current_phase=session["current_phase"],
        phase_progress=session["phase_progress"],
        phase_message=session.get("phase_message"),
        estimated_cost=float(cost),
        has_moodboards=moodboard_count > 0,
        has_style_guide=session["approved_style_guide_id"] is not None
    )


@router.get("/projects/{project_id}/session")
async def get_project_session(
    project_id: int,
    user: dict = Depends(get_current_user)
):
    """Get active research session for a project."""
    session = await db.fetchrow(
        """
        SELECT * FROM muse_research_sessions 
        WHERE project_id = $1 
          AND session_status NOT IN ('failed', 'cancelled', 'handed_off')
        ORDER BY created_at DESC
        LIMIT 1
        """,
        project_id
    )
    
    if not session:
        return {"active_session": None}
    
    return {
        "active_session": {
            "session_id": session["id"],
            "status": session["session_status"],
            "current_phase": session["current_phase"],
            "phase_progress": session["phase_progress"]
        }
    }


# ============================================================================
# INSPIRATION INPUTS
# ============================================================================

@router.post("/sessions/{session_id}/inspirations")
async def add_inspiration(
    session_id: int,
    request: AddInspirationRequest,
    user: dict = Depends(get_current_user)
):
    """Add an inspiration image or URL to the session."""
    try:
        input_id = await muse_agent.add_inspiration(
            session_id=session_id,
            input_type=request.input_type,
            data=request.data,
            user_notes=request.user_notes,
            focus_elements=request.focus_elements,
            filename=request.filename,
            mime_type=request.mime_type
        )
        
        return {
            "input_id": input_id,
            "message": f"Inspiration {request.input_type} added successfully"
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to add inspiration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/inspirations")
async def list_inspirations(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """List all inspiration inputs for a session."""
    inspirations = await db.fetch(
        """
        SELECT id, input_type, image_filename, url, user_notes, focus_elements,
               analysis_complete, applicability_score, created_at
        FROM muse_inspiration_inputs
        WHERE session_id = $1
        ORDER BY created_at ASC
        """,
        session_id
    )
    
    return {
        "inspirations": [
            {
                "id": inp["id"],
                "input_type": inp["input_type"],
                "filename": inp.get("image_filename"),
                "url": inp.get("url"),
                "user_notes": inp.get("user_notes"),
                "focus_elements": inp.get("focus_elements"),
                "analysis_complete": inp["analysis_complete"],
                "applicability_score": inp.get("applicability_score"),
                "created_at": inp["created_at"].isoformat() if inp.get("created_at") else None
            }
            for inp in inspirations
        ]
    }


@router.delete("/sessions/{session_id}/inspirations/{input_id}")
async def delete_inspiration(
    session_id: int,
    input_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete an inspiration input."""
    await db.execute(
        "DELETE FROM muse_inspiration_inputs WHERE id = $1 AND session_id = $2",
        input_id, session_id
    )
    return {"message": "Inspiration deleted"}


# ============================================================================
# RESEARCH PLANNING
# ============================================================================

@router.post("/sessions/{session_id}/plan")
async def create_research_plan(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Create an intelligent research plan with clarifying questions.
    
    This is the first step in the research process. Muse analyzes the brief
    and generates strategic questions to ask the user before proceeding.
    """
    if not muse_agent.is_available:
        raise HTTPException(
            status_code=503,
            detail="Muse agent not available"
        )
    
    try:
        plan = await muse_agent.create_research_plan(session_id)
        
        return {
            "success": True,
            "has_questions": len(plan.clarifying_questions) > 0,
            "understanding": plan.understanding,
            "questions": plan.clarifying_questions,
            "hypothesis": plan.hypothesis,
            "risk_factors": plan.risk_factors,
            "research_plan": plan.research_plan,
            "message": f"Research plan created with {len(plan.clarifying_questions)} clarifying questions."
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Research plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/plan")
async def get_research_plan(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """Get the research plan for a session."""
    session = await muse_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    research_plan = session.get("research_plan")
    if not research_plan:
        return {
            "has_plan": False,
            "message": "No research plan created yet. Call POST /plan to create one."
        }
    
    try:
        plan_data = json.loads(research_plan) if isinstance(research_plan, str) else research_plan
    except:
        plan_data = {}
    
    return {
        "has_plan": True,
        "understanding": plan_data.get("understanding", {}),
        "questions": plan_data.get("clarifying_questions", []),
        "hypothesis": plan_data.get("hypothesis", {}),
        "risk_factors": plan_data.get("risk_factors", []),
        "research_plan": plan_data.get("research_plan", {}),
        "answers_submitted": session.get("user_question_answers") is not None
    }


@router.post("/sessions/{session_id}/answers")
async def submit_question_answers(
    session_id: int,
    request: SubmitAnswersRequest,
    user: dict = Depends(get_current_user)
):
    """
    Submit answers to the clarifying questions.
    
    These answers help Muse refine the research direction and create
    more targeted mood boards.
    """
    try:
        answers = [{"question": a.question, "answer": a.answer} for a in request.answers]
        await muse_agent.submit_question_answers(session_id, answers)
        
        return {
            "success": True,
            "message": f"Received {len(answers)} answers. Ready to start full research.",
            "next_step": "Call POST /sessions/{session_id}/start to begin research"
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Answer submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RESEARCH PIPELINE
# ============================================================================

@router.post("/sessions/{session_id}/start")
async def start_research(
    session_id: int,
    moodboard_count: int = 4,
    skip_web_research: bool = False,
    user: dict = Depends(get_current_user)
):
    """
    Start the research pipeline.
    
    This will:
    0. Create research plan (if not already done)
    1. Analyze the design brief
    2. Analyze any inspiration images/URLs
    3. Conduct web research (optional)
    4. Generate mood board options
    
    Stops at mood board selection for user input.
    
    Args:
        moodboard_count: Number of mood boards to generate (default 4)
        skip_web_research: Skip web research phase for faster processing
    """
    if not muse_agent.is_available:
        raise HTTPException(
            status_code=503,
            detail="Muse agent not available"
        )
    
    try:
        result = await muse_agent.run_full_pipeline(
            session_id=session_id,
            moodboard_count=moodboard_count,
            skip_web_research=skip_web_research
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[MUSE API] Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/start-streaming")
async def start_research_streaming(
    session_id: int,
    moodboard_count: int = 4,
    skip_web_research: bool = False,
    generate_previews: bool = True,
    user: dict = Depends(get_current_user)
):
    """
    Start the research pipeline with real-time SSE streaming.
    
    This endpoint streams progress events and mood board data as they're
    generated, providing real-time feedback to the frontend.
    
    Events emitted:
    - pipeline_started: Pipeline has begun
    - phase_started: A phase is starting (brief_analysis, inspiration_analysis, etc.)
    - phase_complete: A phase has completed
    - moodboard_ready: A mood board is ready (includes data and preview status)
    - pipeline_complete: All phases complete, awaiting user selection
    - error: An error occurred
    
    Args:
        moodboard_count: Number of mood boards to generate (default 4)
        skip_web_research: Skip web research phase for faster processing
        generate_previews: Generate AI preview images for mood boards (requires Imagen)
    """
    if not muse_agent.is_available:
        raise HTTPException(
            status_code=503,
            detail="Muse agent not available"
        )
    
    async def event_generator():
        try:
            async for event in muse_agent.run_pipeline_streaming(
                session_id=session_id,
                moodboard_count=moodboard_count,
                skip_web_research=skip_web_research,
                generate_previews=generate_previews
            ):
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event)
                }
        except Exception as e:
            logger.error(f"[MUSE API] Streaming pipeline error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "data": {"message": str(e)}
                })
            }
    
    return EventSourceResponse(event_generator())


@router.post("/sessions/{session_id}/web-research")
async def conduct_web_research(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Conduct web research using MCP tools.
    
    This phase uses Brave Search and Puppeteer for screenshots
    to gather real-world design references.
    """
    if not muse_agent.is_available:
        raise HTTPException(
            status_code=503,
            detail="Muse agent not available"
        )
    
    try:
        result = await muse_agent.conduct_web_research(session_id)
        
        return {
            "success": True,
            "queries_executed": len(result.queries),
            "screenshots_analyzed": len(result.screenshot_analyses),
            "synthesis": result.synthesis,
            "tokens_used": result.tokens_used
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Web research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/events")
async def stream_events(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Stream research events in real-time via SSE.
    
    Connect to this endpoint for live progress updates.
    """
    async def event_generator():
        last_id = 0
        
        while True:
            # Get new events
            events = await db.fetch(
                """
                SELECT id, event_type, event_data, created_at
                FROM muse_research_events
                WHERE session_id = $1 AND id > $2
                ORDER BY id ASC
                """,
                session_id, last_id
            )
            
            for event in events:
                last_id = event["id"]
                yield {
                    "event": event["event_type"],
                    "data": json.dumps({
                        "type": event["event_type"],
                        "data": json.loads(event["event_data"]) if event["event_data"] else {},
                        "timestamp": event["created_at"].isoformat()
                    })
                }
            
            # Check if session is complete (but not if revising - we keep streaming)
            session = await muse_agent.get_session(session_id)
            if session and session["session_status"] in ["awaiting_selection", "awaiting_approval", "approved", "failed", "cancelled"]:
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "status": session["session_status"],
                        "phase": session["current_phase"]
                    })
                }
                break
            
            # Small delay before next poll
            import asyncio
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())


@router.get("/projects/{project_id}/stream")
async def stream_project_events(
    project_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Stream research events for a project via SSE.
    
    This is a convenience endpoint that finds the active session for a project
    and streams its events. Use this from the frontend when you have project_id
    but not session_id.
    """
    # Find active session for this project
    session = await db.fetchrow(
        """
        SELECT id FROM muse_research_sessions 
        WHERE project_id = $1 
          AND session_status NOT IN ('failed', 'cancelled', 'handed_off')
        ORDER BY created_at DESC 
        LIMIT 1
        """,
        project_id
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="No active research session for this project")
    
    session_id = session["id"]
    
    async def event_generator():
        last_id = 0
        
        while True:
            # Get new events
            events = await db.fetch(
                """
                SELECT id, event_type, event_data, created_at
                FROM muse_research_events
                WHERE session_id = $1 AND id > $2
                ORDER BY id ASC
                """,
                session_id, last_id
            )
            
            for event in events:
                last_id = event["id"]
                yield {
                    "event": event["event_type"],
                    "data": json.dumps({
                        "type": event["event_type"],
                        "data": json.loads(event["event_data"]) if event["event_data"] else {},
                        "timestamp": event["created_at"].isoformat()
                    })
                }
            
            # Check if session is complete (but not if revising - we keep streaming)
            current_session = await muse_agent.get_session(session_id)
            if current_session and current_session["session_status"] in ["awaiting_selection", "awaiting_approval", "approved", "failed", "cancelled"]:
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "status": current_session["session_status"],
                        "phase": current_session["current_phase"]
                    })
                }
                break
            
            # Small delay before next poll
            import asyncio
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())


# ============================================================================
# MOOD BOARDS
# ============================================================================

@router.get("/sessions/{session_id}/moodboards")
async def list_moodboards(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """Get all mood boards for a session with preview images."""
    moodboards = await db.fetch(
        """
        SELECT id, option_number, title, description, aesthetic_movement,
               emotional_tone, color_palette, heading_font, body_font,
               imagery_style, layout_philosophy, motion_philosophy,
               is_selected, preview_data, preview_image_generated,
               selection_count
        FROM muse_moodboards
        WHERE session_id = $1
        ORDER BY option_number ASC
        """,
        session_id
    )
    
    return {
        "moodboards": [
            _format_moodboard_response(mb)
            for mb in moodboards
        ]
    }


def _format_moodboard_response(mb: dict) -> dict:
    """
    Format a moodboard database row into the API response format.
    
    Ensures consistent field naming between backend and frontend:
    - 'name' is the canonical display field (frontend)
    - 'title' is preserved for backend compatibility
    - 'preview_image_b64' maps from 'preview_image_generated' in DB
    """
    color_palette = json.loads(mb["color_palette"]) if mb.get("color_palette") else {}
    
    return {
        "id": mb["id"],
        "option_number": mb["option_number"],
        "name": mb["title"],  # Canonical frontend display field
        "title": mb["title"],  # Backend compatibility
        "description": mb["description"],
        "aesthetic_movement": mb["aesthetic_movement"],
        "emotional_tone": mb["emotional_tone"] or [],
        "color_palette": color_palette,
        "colors": _extract_colors_array(color_palette),
        "typography": {
            "heading": mb.get("heading_font", ""),
            "body": mb.get("body_font", "")
        },
        "imagery_style": mb.get("imagery_style", ""),
        "layout_philosophy": mb.get("layout_philosophy", ""),
        "motion_philosophy": mb.get("motion_philosophy", ""),
        "is_selected": mb.get("is_selected", False),
        "preview_image_b64": mb.get("preview_image_generated"),  # Map DB column to API field
        "preview": json.loads(mb["preview_data"]) if mb.get("preview_data") else {},
        "selection_count": mb.get("selection_count", 0)
    }


def _extract_colors_array(color_palette: dict) -> list:
    """Extract colors from palette into frontend-expected array format."""
    colors = []
    for key, value in color_palette.items():
        if isinstance(value, str) and value.startswith('#'):
            colors.append({"name": key.replace('_', ' ').title(), "hex": value})
        elif isinstance(value, dict) and 'hex' in value:
            colors.append({"name": key, "hex": value['hex']})
    return colors or [{"name": "Primary", "hex": "#000000"}]


@router.get("/sessions/{session_id}/moodboards/{moodboard_id}")
async def get_moodboard(
    session_id: int,
    moodboard_id: int,
    user: dict = Depends(get_current_user)
):
    """Get full mood board details including preview image."""
    mb = await db.fetchrow(
        "SELECT * FROM muse_moodboards WHERE id = $1 AND session_id = $2",
        moodboard_id, session_id
    )
    
    if not mb:
        raise HTTPException(status_code=404, detail="Mood board not found")
    
    color_palette = json.loads(mb["color_palette"]) if mb["color_palette"] else {}
    return {
        "id": mb["id"],
        "option_number": mb["option_number"],
        "name": mb["title"],  # Canonical frontend display field
        "title": mb["title"],  # Backend compatibility
        "description": mb["description"],
        "aesthetic_movement": mb["aesthetic_movement"],
        "emotional_tone": mb["emotional_tone"] or [],
        "color_palette": color_palette,
        "colors": _extract_colors_array(color_palette),
        "color_rationale": mb.get("color_rationale", ""),
        "typography": {
            "heading": mb.get("heading_font", ""),
            "body": mb.get("body_font", ""),
            "heading_font": mb.get("heading_font", ""),
            "heading_font_url": mb.get("heading_font_url", ""),
            "body_font": mb.get("body_font", ""),
            "body_font_url": mb.get("body_font_url", ""),
            "font_rationale": mb.get("font_rationale", "")
        },
        "visual_elements": {
            "imagery_style": mb.get("imagery_style", ""),
            "iconography_style": mb.get("iconography_style", ""),
            "pattern_usage": mb.get("pattern_usage", ""),
            "texture_notes": mb.get("texture_notes")
        },
        "layout_approach": {
            "philosophy": mb.get("layout_philosophy", ""),
            "spacing": mb.get("spacing_approach", "")
        },
        "motion_language": {
            "philosophy": mb.get("motion_philosophy", ""),
            "recommended_animations": mb.get("recommended_animations", [])
        },
        "imagery_style": mb.get("imagery_style", ""),
        "layout_philosophy": mb.get("layout_philosophy", ""),
        "motion_philosophy": mb.get("motion_philosophy", ""),
        "is_selected": mb.get("is_selected", False),
        "selection_notes": mb.get("selection_notes"),
        "preview_image_b64": mb.get("preview_image_generated"),  # AI-generated preview
        "preview_generation_prompt": mb.get("preview_generation_prompt"),
        "selection_count": mb.get("selection_count", 0)
    }


@router.post("/sessions/{session_id}/moodboards/{moodboard_id}/select")
async def select_moodboard(
    session_id: int,
    moodboard_id: int,
    request: Optional[SelectMoodboardRequest] = None,
    user: dict = Depends(get_current_user)
):
    """
    Select a mood board to proceed with.
    
    This triggers style guide generation.
    """
    try:
        await muse_agent.select_moodboard(
            session_id=session_id,
            moodboard_id=moodboard_id,
            selection_notes=request.selection_notes if request else None,
            time_viewing_seconds=request.time_viewing_seconds if request else None
        )
        
        # Generate style guide
        style_guide = await muse_agent.generate_style_guide(session_id)
        
        return {
            "success": True,
            "message": "Mood board selected and style guide generated",
            "status": "awaiting_approval",
            "style_guide_preview": {
                "colors": list(style_guide.get("colors", {}).keys()),
                "typography_families": list(style_guide.get("typography", {}).get("families", {}).keys()),
                "anti_patterns_count": len(style_guide.get("antiPatterns", []))
            }
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to select mood board: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/moodboards/regenerate")
async def regenerate_moodboards(
    session_id: int,
    count: int = 4,
    user: dict = Depends(get_current_user)
):
    """Regenerate mood board options with different variations."""
    try:
        # Clear existing moodboards
        await db.execute(
            "DELETE FROM muse_moodboards WHERE session_id = $1",
            session_id
        )
        
        # Regenerate
        moodboards = await muse_agent.generate_moodboards(session_id, count)
        
        return {
            "success": True,
            "count": len(moodboards),
            "message": f"Generated {len(moodboards)} new mood board options"
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to regenerate moodboards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# A/B TESTING ANALYTICS
# ============================================================================

@router.post("/sessions/{session_id}/moodboards/{moodboard_id}/impression")
async def track_impression(
    session_id: int,
    moodboard_id: int,
    view_duration_seconds: Optional[float] = None,
    user: dict = Depends(get_current_user)
):
    """
    Track when a user views a mood board.
    
    Call this when a mood board card is displayed/viewed in the UI.
    Used for A/B testing to understand which designs get more attention.
    
    Args:
        view_duration_seconds: How long the user viewed the mood board
    """
    await muse_agent.track_moodboard_impression(
        session_id=session_id,
        moodboard_id=moodboard_id,
        view_duration_seconds=view_duration_seconds
    )
    
    return {"success": True, "tracked": "impression"}


@router.get("/sessions/{session_id}/analytics")
async def get_session_analytics(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Get A/B testing analytics for a session's mood boards.
    
    Returns impression and selection data for each mood board option.
    """
    analytics = await muse_agent.get_moodboard_analytics(session_id)
    return analytics


@router.get("/analytics/moodboard-patterns")
async def get_moodboard_patterns(
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """
    Get aggregate mood board selection patterns.
    
    Useful for understanding which aesthetic directions are most popular.
    """
    try:
        patterns = await db.fetch(
            """
            SELECT 
                aesthetic_movement,
                COUNT(*) as total_generated,
                SUM(CASE WHEN is_selected THEN 1 ELSE 0 END) as total_selected,
                ROUND(AVG(CASE WHEN is_selected THEN 1 ELSE 0 END) * 100, 1) as selection_rate
            FROM muse_moodboards
            GROUP BY aesthetic_movement
            HAVING COUNT(*) >= 3
            ORDER BY selection_rate DESC
            LIMIT $1
            """,
            limit
        )
        
        return {
            "patterns": [dict(p) for p in patterns],
            "total_movements": len(patterns)
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to get patterns: {e}")
        return {"patterns": [], "error": str(e)}


# ============================================================================
# STYLE GUIDE
# ============================================================================

@router.get("/sessions/{session_id}/style-guide")
async def get_style_guide(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """Get the generated style guide."""
    session = await muse_agent.get_session(session_id)
    if not session or not session.get("approved_style_guide_id"):
        raise HTTPException(status_code=404, detail="Style guide not found")
    
    sg = await db.fetchrow(
        "SELECT * FROM muse_style_guides WHERE id = $1",
        session["approved_style_guide_id"]
    )
    
    return {
        "id": sg["id"],
        "version": sg["version"],
        "is_approved": sg["is_approved"],
        "colors": json.loads(sg["colors"]) if sg["colors"] else {},
        "typography": json.loads(sg["typography"]) if sg["typography"] else {},
        "spacing": json.loads(sg["spacing"]) if sg["spacing"] else {},
        "radii": json.loads(sg["radii"]) if sg["radii"] else {},
        "shadows": json.loads(sg["shadows"]) if sg["shadows"] else {},
        "animations": json.loads(sg["animations"]) if sg["animations"] else {},
        "breakpoints": json.loads(sg["breakpoints"]) if sg["breakpoints"] else {},
        "components": json.loads(sg["component_specs"]) if sg["component_specs"] else {},
        "iconography": {
            "library": sg["iconography_source"],
            "style": sg["iconography_style"]
        },
        "imagery_guidelines": sg["imagery_guidelines"],
        "anti_patterns": json.loads(sg["anti_patterns"]) if sg["anti_patterns"] else [],
        "tailwind_config": json.loads(sg["tailwind_config"]) if sg["tailwind_config"] else {},
        "css_variables": sg["css_variables"],
        "implementation_notes": sg["implementation_notes"],
        "nicole_context_summary": sg["nicole_context_summary"]
    }


class ReviseStyleGuideRequest(BaseModel):
    """Request to revise the style guide with feedback."""
    feedback: str


@router.post("/sessions/{session_id}/style-guide/revise")
async def revise_style_guide(
    session_id: int,
    request: ReviseStyleGuideRequest,
    user: dict = Depends(get_current_user)
):
    """
    Request changes to the style guide based on user feedback.
    
    This regenerates the style guide incorporating the feedback.
    """
    try:
        session = await muse_agent.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session["session_status"] != "awaiting_approval":
            raise HTTPException(
                status_code=400, 
                detail="Session is not in awaiting_approval state"
            )
        
        # Get current version
        current_sg = await db.fetchrow(
            "SELECT version FROM muse_style_guides WHERE id = $1",
            session["approved_style_guide_id"]
        )
        new_version = (current_sg["version"] if current_sg else 0) + 1
        
        # Store the feedback in the session for reference
        await db.execute(
            """
            UPDATE muse_research_sessions 
            SET session_status = 'revising_design',
                current_phase = 'style_guide_revision',
                phase_message = $2
            WHERE id = $1
            """,
            session_id,
            f"Revising design based on feedback: {request.feedback[:100]}..."
        )
        
        # Emit event for real-time updates
        await db.execute(
            """
            INSERT INTO muse_research_events (session_id, event_type, event_data)
            VALUES ($1, 'revision_started', $2)
            """,
            session_id,
            json.dumps({"feedback_preview": request.feedback[:200]})
        )
        
        # Regenerate the style guide with the user's feedback incorporated
        new_style_guide = await muse_agent.generate_style_guide(
            session_id,
            revision_feedback=request.feedback
        )
        
        # Get the new style guide ID
        updated_session = await muse_agent.get_session(session_id)
        
        return {
            "success": True,
            "message": "Style guide revised successfully",
            "version": new_version,
            "style_guide_id": updated_session["approved_style_guide_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MUSE API] Failed to revise style guide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/approve")
async def approve_design(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Approve the design and prepare for Nicole handoff.
    
    This marks the research phase as complete and sends the design
    specification to Nicole for code generation.
    """
    try:
        handoff = await muse_agent.approve_design(session_id)
        
        return {
            "success": True,
            "message": "Design approved! Ready for coding phase.",
            "handoff": handoff,
            "next_step": "Start project in Enjineer dashboard - Nicole will use this design specification"
        }
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to approve design: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/handoff")
async def get_handoff(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """Get Nicole handoff data for an approved session."""
    session = await muse_agent.get_session(session_id)
    if not session or session["session_status"] not in ["approved", "handed_off"]:
        raise HTTPException(status_code=400, detail="Session not approved yet")
    
    return await muse_agent.get_nicole_handoff(session_id)


# ============================================================================
# STYLE GUIDE EXPORT
# ============================================================================

class ExportStyleGuideRequest(BaseModel):
    """Request to export a style guide."""
    format: str = Field(
        ..., 
        pattern="^(figma_tokens|css_variables|tailwind_config|design_tokens_json)$",
        description="Export format: figma_tokens, css_variables, tailwind_config, or design_tokens_json"
    )


class ExportStyleGuideResponse(BaseModel):
    """Response containing exported style guide."""
    format: str
    content: str
    filename: str
    content_type: str


@router.post("/style-guides/{style_guide_id}/export", response_model=ExportStyleGuideResponse)
async def export_style_guide(
    style_guide_id: int,
    request: ExportStyleGuideRequest,
    user: dict = Depends(get_current_user)
):
    """
    Export a style guide in the specified format.
    
    Supported formats:
    - figma_tokens: Figma design tokens JSON
    - css_variables: CSS custom properties
    - tailwind_config: Tailwind CSS configuration file
    - design_tokens_json: W3C Design Tokens format
    """
    try:
        # Verify user has access to this style guide
        sg = await db.fetchrow(
            """
            SELECT sg.*, s.project_id 
            FROM muse_style_guides sg
            JOIN muse_research_sessions s ON sg.session_id = s.id
            JOIN enjineer_projects p ON s.project_id = p.id
            WHERE sg.id = $1 AND p.user_id = $2
            """,
            style_guide_id,
            user["sub"]
        )
        
        if not sg:
            raise HTTPException(
                status_code=404,
                detail="Style guide not found or access denied"
            )
        
        # Export using Muse agent
        export_content = await muse_agent.export_style_guide(
            style_guide_id,
            request.format,
            user["sub"]
        )
        
        # Determine filename and content type
        format_info = {
            "figma_tokens": ("design-tokens.json", "application/json"),
            "css_variables": ("design-tokens.css", "text/css"),
            "tailwind_config": ("tailwind.config.ts", "text/typescript"),
            "design_tokens_json": ("tokens.json", "application/json")
        }
        
        filename, content_type = format_info.get(
            request.format,
            ("export.txt", "text/plain")
        )
        
        # Update last export timestamp
        timestamp_col = f"last_export_{request.format.replace('-', '_')}"
        if timestamp_col in ["last_export_figma_tokens", "last_export_css_variables", "last_export_tailwind_config"]:
            await db.execute(
                f"""
                UPDATE muse_style_guides 
                SET {timestamp_col} = NOW()
                WHERE id = $1
                """,
                style_guide_id
            )
        
        logger.info(f"[MUSE API] Exported style guide {style_guide_id} as {request.format}")
        
        return ExportStyleGuideResponse(
            format=request.format,
            content=export_content,
            filename=filename,
            content_type=content_type
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[MUSE API] Failed to export style guide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/style-guides/{style_guide_id}/exports")
async def get_style_guide_exports(
    style_guide_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Get export history for a style guide.
    """
    try:
        # Verify access
        sg = await db.fetchrow(
            """
            SELECT sg.id 
            FROM muse_style_guides sg
            JOIN muse_research_sessions s ON sg.session_id = s.id
            JOIN enjineer_projects p ON s.project_id = p.id
            WHERE sg.id = $1 AND p.user_id = $2
            """,
            style_guide_id,
            user["sub"]
        )
        
        if not sg:
            raise HTTPException(status_code=404, detail="Style guide not found")
        
        exports = await db.fetch(
            """
            SELECT id, export_format, created_at
            FROM muse_style_guide_exports
            WHERE style_guide_id = $1
            ORDER BY created_at DESC
            LIMIT 20
            """,
            style_guide_id
        )
        
        return {
            "style_guide_id": style_guide_id,
            "exports": [
                {
                    "id": e["id"],
                    "format": e["export_format"],
                    "created_at": e["created_at"].isoformat()
                }
                for e in exports
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MUSE API] Failed to get export history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/style-guide/export")
async def export_project_style_guide(
    project_id: int,
    format: str,
    user: dict = Depends(get_current_user)
):
    """
    Quick export endpoint - get current project's style guide in specified format.
    
    This is a convenience endpoint that finds the active style guide for a project
    and exports it in the requested format.
    """
    try:
        # Find the project's active style guide
        project = await db.fetchrow(
            """
            SELECT p.active_style_guide_id 
            FROM enjineer_projects p
            WHERE p.id = $1 AND p.user_id = $2
            """,
            project_id,
            user["sub"]
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project["active_style_guide_id"]:
            raise HTTPException(
                status_code=400,
                detail="No active style guide for this project. Complete design research first."
            )
        
        # Validate format
        valid_formats = ["figma_tokens", "css_variables", "tailwind_config", "design_tokens_json"]
        if format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Export using the style guide export endpoint logic
        export_content = await muse_agent.export_style_guide(
            project["active_style_guide_id"],
            format,
            user["sub"]
        )
        
        format_info = {
            "figma_tokens": ("design-tokens.json", "application/json"),
            "css_variables": ("design-tokens.css", "text/css"),
            "tailwind_config": ("tailwind.config.ts", "text/typescript"),
            "design_tokens_json": ("tokens.json", "application/json")
        }
        
        filename, content_type = format_info[format]
        
        return {
            "project_id": project_id,
            "format": format,
            "content": export_content,
            "filename": filename,
            "content_type": content_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MUSE API] Failed to export project style guide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SKIP RESEARCH (QUICK BUILD)
# ============================================================================

@router.post("/projects/{project_id}/skip-research")
async def skip_research(
    project_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Skip design research and go directly to code generation.
    
    Sets project to 'quick' mode without Muse research.
    """
    await db.execute(
        """
        UPDATE enjineer_projects 
        SET design_mode = 'quick'
        WHERE id = $1
        """,
        project_id
    )
    
    return {
        "success": True,
        "message": "Research skipped. Project set to quick build mode.",
        "design_mode": "quick"
    }


# ============================================================================
# DESIGN REPORT & EXPORT PACKAGE GENERATION
# ============================================================================

class GenerateReportRequest(BaseModel):
    """Request to generate a report."""
    report_type: str = Field(
        default="design_report",
        pattern="^(design_report|cursor_prompt|executive_summary|technical_spec)$"
    )

class ExportPackageRequest(BaseModel):
    """Request to generate export package."""
    format_type: str = Field(
        default="cursor_ready",
        pattern="^(full|cursor_ready|tokens_only)$"
    )

class GeneratedReportResponse(BaseModel):
    """Response with generated report."""
    report_type: str
    title: str
    content_markdown: str
    word_count: int
    generation_model: str
    generation_tokens: int = 0
    generation_duration_ms: int = 0

class ExportPackageResponse(BaseModel):
    """Response with export package info."""
    success: bool
    package_name: str
    format: str
    size_bytes: int
    files: List[str]
    zip_base64: str
    content_type: str = "application/zip"
    filename: str

class CursorPromptResponse(BaseModel):
    """Response for cursor prompt endpoint."""
    session_id: int
    title: str
    content: str
    word_count: int
    ready_for_implementation: bool = True


@router.post("/sessions/{session_id}/reports/generate", response_model=GeneratedReportResponse)
async def generate_report(
    session_id: int,
    request: GenerateReportRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a design report from a completed research session.
    """
    try:
        # Get project ID from session
        session = await muse_agent.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if request.report_type == "cursor_prompt":
            report = await report_generator.generate_cursor_prompt(
                session_id=session_id,
                project_id=session["project_id"]
            )
        else:
            report = await report_generator.generate_design_report(
                session_id=session_id,
                project_id=session["project_id"]
            )
            
        return GeneratedReportResponse(
            report_type=report.report_type,
            title=report.title,
            content_markdown=report.content_markdown,
            word_count=report.word_count,
            generation_model=report.generation_model,
            generation_tokens=report.generation_tokens,
            generation_duration_ms=report.generation_duration_ms
        )
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/cursor-prompt", response_model=CursorPromptResponse)
async def get_cursor_prompt(
    session_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Quick endpoint to get the cursor/implementation prompt.
    """
    try:
        session = await muse_agent.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        report = await report_generator.generate_cursor_prompt(
            session_id=session_id,
            project_id=session["project_id"]
        )
        
        return CursorPromptResponse(
            session_id=session_id,
            title=report.title,
            content=report.content_markdown,
            word_count=report.word_count
        )
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to get cursor prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/export-package", response_model=ExportPackageResponse)
async def generate_export_package(
    session_id: int,
    request: ExportPackageRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a ZIP package with all design documentation.
    """
    try:
        session = await muse_agent.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        package = await report_generator.generate_export_package(
            session_id=session_id,
            project_id=session["project_id"],
            format_type=request.format_type
        )
        
        import base64
        return ExportPackageResponse(
            success=True,
            package_name=package.package_name,
            format=package.package_format,
            size_bytes=package.size_bytes,
            files=package.contents_manifest.get("files", []),
            zip_base64=base64.b64encode(package.zip_data).decode("utf-8"),
            filename=f"{package.package_name}.zip"
        )
        
    except Exception as e:
        logger.error(f"[MUSE API] Failed to generate export package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


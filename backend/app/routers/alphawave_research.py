"""
Research API - Nicole's Deep Research Endpoints

Provides:
- Execute research requests via Gemini 3 Pro
- Stream research progress
- Get research results
- Vibe-specific inspiration search

Uses Google Search Grounding (FREE until Jan 2026).
"""

import logging
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.middleware.alphawave_auth import get_current_user
from app.services.alphawave_research_service import (
    research_orchestrator,
    ResearchStatus,
    ResearchStatusUpdate
)
from app.integrations.alphawave_gemini import ResearchType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ResearchRequest(BaseModel):
    """Research request body."""
    query: str = Field(..., min_length=5, max_length=1000, description="Research query")
    research_type: str = Field(
        default="general",
        description="Type: general, vibe_inspiration, competitor, technical"
    )
    project_id: Optional[int] = Field(default=None, description="Associated Vibe project ID")
    context: Optional[dict] = Field(default=None, description="Additional context")


class VibeInspirationRequest(BaseModel):
    """Vibe inspiration search request."""
    query: str = Field(..., min_length=3, max_length=500, description="Inspiration search query")
    project_brief: Optional[dict] = Field(default=None, description="Project brief for context")
    previous_feedback: Optional[list] = Field(default=None, description="Previous feedback for refinement")
    avoid_patterns: Optional[list] = Field(default=None, description="Patterns to avoid")


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class CompetitorRequest(BaseModel):
    """Competitor analysis request body."""
    competitor_url: str = Field(..., description="URL of competitor to analyze")
    analysis_focus: Optional[list] = Field(default=None, description="Specific aspects to focus on")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/execute", response_model=APIResponse)
async def execute_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """
    Execute a research request.
    
    Returns wrapped response with {success, data, error}.
    Use /research/{request_id} to poll for status updates.
    
    Research Types:
    - general: General web research
    - vibe_inspiration: Design inspiration for web projects
    - competitor: Competitor analysis
    - technical: Technical documentation research
    """
    try:
        # Map string to enum
        research_type = ResearchType(request.research_type)
    except ValueError:
        research_type = ResearchType.GENERAL
    
    # Execute research synchronously
    final_result = None
    async for update in research_orchestrator.execute_research(
        query=request.query,
        research_type=research_type,
        user_id=user.get("user_id", 0),
        project_id=request.project_id,
        context=request.context
    ):
        final_result = update
    
    if final_result and final_result.status == ResearchStatus.COMPLETE:
        return APIResponse(
            success=True,
            data=final_result.data
        )
    elif final_result:
        return APIResponse(
            success=False,
            error=final_result.message,
            data=final_result.data
        )
    
    return APIResponse(success=False, error="Research execution failed")


@router.get("/{request_id}/stream")
async def stream_research(
    request_id: int,
    user = Depends(get_current_user)
):
    """
    Stream research progress via SSE.
    
    Events:
    - pending: Request received
    - researching: Gemini executing search
    - synthesizing: Claude processing results
    - complete: Research finished
    - failed: Research failed
    """
    async def event_generator():
        # Get current status
        research = await research_orchestrator.get_research(request_id)
        
        if not research:
            yield f"data: {json.dumps({'status': 'failed', 'message': 'Research not found'})}\n\n"
            return
        
        yield f"data: {json.dumps({'status': research['status'], 'data': research})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get("/{request_id}", response_model=APIResponse)
async def get_research(
    request_id: int,
    user = Depends(get_current_user)
):
    """
    Get research results by request ID.
    
    Returns wrapped response with full research data including:
    - Query and type
    - Executive summary
    - Key findings with citations
    - Recommendations
    - Nicole's synthesis
    - Source URLs
    """
    research = await research_orchestrator.get_research(request_id)
    
    if not research:
        return APIResponse(success=False, error="Research not found")
    
    return APIResponse(success=True, data=research)


@router.post("/vibe/{project_id}/inspiration", response_model=APIResponse)
async def search_vibe_inspiration(
    project_id: int,
    request: VibeInspirationRequest,
    user = Depends(get_current_user)
):
    """
    Search for design inspiration for a Vibe project.
    
    Optimized for finding:
    - Website designs matching project brief
    - Color palettes and typography
    - Layout patterns and interactions
    - Competitor examples
    
    Uses Google Search Grounding to find real examples.
    """
    from app.integrations.alphawave_gemini import gemini_client
    
    result = await gemini_client.search_inspiration(
        query=request.query,
        project_brief=request.project_brief,
        previous_feedback=request.previous_feedback
    )
    
    if not result.get("success"):
        return APIResponse(
            success=False,
            error=result.get("error", "Inspiration search failed")
        )
    
    return APIResponse(
        success=True,
        data={
            "project_id": project_id,
            "query": request.query,
            "inspirations": result.get("results", {}).get("inspiration_images", []),
            "design_patterns": result.get("results", {}).get("design_patterns", []),
            "recommendations": result.get("results", {}).get("recommendations", []),
            "sources": result.get("sources", []),
            "metadata": result.get("metadata", {})
        }
    )


@router.post("/vibe/{project_id}/competitor", response_model=APIResponse)
async def analyze_competitor(
    project_id: int,
    request: CompetitorRequest,
    user = Depends(get_current_user)
):
    """
    Analyze a competitor website for a Vibe project.
    
    Provides:
    - Design analysis
    - Feature comparison
    - Strengths and weaknesses
    - Strategic recommendations
    """
    from app.integrations.alphawave_gemini import gemini_client
    
    result = await gemini_client.analyze_competitor(
        competitor_url=request.competitor_url,
        analysis_focus=request.analysis_focus
    )
    
    if not result.get("success"):
        return APIResponse(
            success=False,
            error=result.get("error", "Competitor analysis failed")
        )
    
    # Return full ResearchResponse-compatible structure
    parsed = result.get("results", {})
    return APIResponse(
        success=True,
        data={
            "request_id": 0,  # Competitor analyses aren't stored with an ID
            "query": f"Competitor: {request.competitor_url}",
            "research_type": "competitor",
            "executive_summary": parsed.get("executive_summary", ""),
            "findings": parsed.get("key_findings", []),
            "sources": result.get("sources", []),
            "recommendations": parsed.get("recommendations", []),
            "nicole_synthesis": parsed.get("nicole_synthesis", ""),
            "metadata": result.get("metadata", {}),
            "project_id": project_id,
            "competitor_url": request.competitor_url
        }
    )


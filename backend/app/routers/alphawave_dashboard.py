"""
Nicole V7 Dashboard Router

Comprehensive dashboard API for:
- Usage metrics and cost tracking
- System diagnostics
- Health monitoring
- Nicole self-awareness context

Production-grade endpoints for power users who need
detailed visibility into system performance and costs.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.database import db
from app.middleware.alphawave_auth import get_current_tiger_user_id
from app.services.alphawave_usage_service import usage_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class UsageResponse(BaseModel):
    """Response model for usage data."""
    period: Dict[str, Any]
    tokens: Dict[str, int]
    requests: Dict[str, int]
    costs: Dict[str, float]
    storage: Dict[str, Any]
    projections: Dict[str, Any]
    daily_breakdown: List[Dict[str, Any]]


class DiagnosticsResponse(BaseModel):
    """Response model for diagnostics data."""
    health: Dict[str, Any]
    memory_system: Dict[str, Any]
    api_health: Dict[str, Any]
    activity: Dict[str, Any]
    issues: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]


class DashboardContextResponse(BaseModel):
    """Response model for Nicole's dashboard awareness."""
    summary: str
    details: Dict[str, Any]
    recommendations: List[str]


# =============================================================================
# USAGE ENDPOINTS
# =============================================================================

@router.get("/usage")
async def get_usage(
    request: Request,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Get comprehensive usage metrics.
    
    Returns token usage, API costs, storage usage, and projections.
    Essential for monitoring system costs and planning.
    
    Args:
        days: Number of days to include (default 30)
        
    Returns:
        Complete usage summary with costs and projections
    """
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    logger.info(f"[DASHBOARD] Fetching usage for user {tiger_user_id}, {days} days")
    
    usage = await usage_service.get_usage_summary(tiger_user_id, days)
    
    return usage


@router.get("/diagnostics")
async def get_diagnostics(
    request: Request,
) -> Dict[str, Any]:
    """
    Get system diagnostics and health check.
    
    Identifies issues, warnings, and provides health scores for:
    - Memory system
    - API connectivity
    - Recent activity
    - Document processing
    
    Returns:
        Diagnostic information with issues and recommendations
    """
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    logger.info(f"[DASHBOARD] Fetching diagnostics for user {tiger_user_id}")
    
    diagnostics = await usage_service.get_diagnostics(tiger_user_id)
    
    return diagnostics


@router.get("/context")
async def get_dashboard_context(
    request: Request,
) -> Dict[str, Any]:
    """
    Get dashboard context for Nicole's self-awareness.
    
    This endpoint provides Nicole with information about her own
    system status, usage, and any issues she should be aware of.
    Used to help Nicole answer questions about her own performance.
    
    Returns:
        Summary, details, and recommendations for Nicole's awareness
    """
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get both usage and diagnostics
    usage = await usage_service.get_usage_summary(tiger_user_id, 30)
    diagnostics = await usage_service.get_diagnostics(tiger_user_id)
    
    # Build summary for Nicole
    recommendations = []
    
    # Check for issues
    for issue in diagnostics.get("issues", []):
        if issue["severity"] == "error":
            recommendations.append(f"Critical: {issue['message']}")
        elif issue["severity"] == "warning":
            recommendations.append(f"Warning: {issue['message']}")
    
    # Check cost trends
    if usage["projections"]["trend"] == "increasing":
        recommendations.append(
            f"API costs are trending up {usage['projections']['trend_percentage']}% - "
            f"current projection: ${usage['projections']['monthly_estimate']}/month"
        )
    
    # Check memory health
    if diagnostics["memory_system"]["avg_confidence"] < 0.5:
        recommendations.append(
            "Average memory confidence is low - consider reviewing and correcting memories"
        )
    
    # Build natural language summary
    health_emoji = "✅" if diagnostics["health"]["status"] == "healthy" else "⚠️"
    
    summary = (
        f"{health_emoji} System Health: {diagnostics['health']['status'].title()} "
        f"(Score: {diagnostics['health']['score']}/100)\n\n"
        f"📊 This Month's Usage:\n"
        f"  • Claude: {usage['tokens']['claude_input'] + usage['tokens']['claude_output']:,} tokens (${usage['costs']['claude']:.2f})\n"
        f"  • Embeddings: {usage['tokens']['openai_embedding']:,} tokens (${usage['costs']['openai']:.2f})\n"
        f"  • Storage: {usage['storage']['total_formatted']}\n"
        f"  • Total Cost: ${usage['costs']['total']:.2f}\n\n"
        f"📈 Projection: ${usage['projections']['monthly_estimate']:.2f}/month\n"
        f"📁 Data: {diagnostics['memory_system']['total_memories']} memories, "
        f"{usage['storage']['document_count']} documents"
    )
    
    if recommendations:
        summary += "\n\n⚡ Action Items:\n" + "\n".join(f"  • {r}" for r in recommendations)
    
    return {
        "summary": summary,
        "details": {
            "usage": usage,
            "diagnostics": diagnostics,
        },
        "recommendations": recommendations,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/overview")
async def get_dashboard_overview(
    request: Request,
) -> Dict[str, Any]:
    """
    Get complete dashboard overview with all data.
    
    Single endpoint that returns everything needed for the dashboard:
    - Memory stats
    - Usage metrics
    - Diagnostics
    - System health
    
    Optimized for the frontend to make a single call.
    """
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Fetch all data in parallel
    import asyncio
    
    usage_task = usage_service.get_usage_summary(tiger_user_id, 30)
    diagnostics_task = usage_service.get_diagnostics(tiger_user_id)
    
    usage, diagnostics = await asyncio.gather(usage_task, diagnostics_task)
    
    # Calculate health badge status
    health_score = diagnostics["health"]["score"]
    if health_score >= 90:
        health_badge = "excellent"
    elif health_score >= 70:
        health_badge = "healthy"
    elif health_score >= 50:
        health_badge = "fair"
    else:
        health_badge = "needs_attention"
    
    return {
        "health": {
            "score": health_score,
            "status": diagnostics["health"]["status"],
            "badge": health_badge,
        },
        "usage": usage,
        "diagnostics": diagnostics,
        "timestamp": datetime.utcnow().isoformat(),
    }


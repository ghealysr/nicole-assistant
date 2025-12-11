"""
Claude Skills API Router

Endpoints for discovering and accessing Claude Skills.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from app.services.alphawave_claude_skills_service import claude_skills_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["claude-skills"])


@router.get("/")
async def list_skills(category: Optional[str] = None):
    """
    List all available Claude skills.
    
    Args:
        category: Optional filter by category (development, business, creative, etc.)
    """
    skills = claude_skills_service.list_skills(category)
    return {
        "success": True,
        "total": len(skills),
        "category_filter": category,
        "skills": skills
    }


@router.get("/categories")
async def list_categories():
    """Get all skill categories with counts."""
    categories = claude_skills_service.categories
    return {
        "success": True,
        "categories": {k: len(v) for k, v in categories.items()},
        "total_skills": claude_skills_service.total_skills
    }


@router.get("/search")
async def search_skills(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(5, ge=1, le=20, description="Maximum results")
):
    """
    Search for skills matching a query.
    
    Args:
        q: Search query (natural language description)
        max_results: Maximum number of results (1-20)
    """
    results = claude_skills_service.search_skills(q, max_results)
    return {
        "success": True,
        "query": q,
        "count": len(results),
        "results": results
    }


@router.get("/summary")
async def get_skills_summary():
    """Get a summary of all skills suitable for AI context."""
    summary = claude_skills_service.get_skills_summary_for_prompt()
    return {
        "success": True,
        "summary": summary,
        "total_skills": claude_skills_service.total_skills
    }


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """
    Get detailed information about a specific skill.
    
    Args:
        skill_id: The skill identifier (e.g., 'lead-research-assistant')
    """
    skill = claude_skills_service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    
    return {
        "success": True,
        "skill": skill
    }


@router.get("/{skill_id}/instructions")
async def get_skill_instructions(skill_id: str):
    """
    Get just the instructions for a skill.
    
    Args:
        skill_id: The skill identifier
    """
    instructions = claude_skills_service.get_skill_instructions(skill_id)
    if not instructions:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    
    return {
        "success": True,
        "skill_id": skill_id,
        "instructions": instructions
    }


@router.get("/{skill_id}/activate")
async def get_skill_activation_prompt(skill_id: str):
    """
    Get the activation prompt for a skill.
    
    This provides the full context needed to apply the skill to a task.
    
    Args:
        skill_id: The skill identifier
    """
    prompt = claude_skills_service.get_skill_activation_prompt(skill_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    
    return {
        "success": True,
        "skill_id": skill_id,
        "activation_prompt": prompt
    }


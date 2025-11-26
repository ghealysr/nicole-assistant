"""
Projects router for Notion project domains.
"""

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/")
async def create_project(request: Request):
    """Create new project domain in Notion."""
    return {"message": "Create project - implementation pending"}


@router.get("/{project_id}")
async def get_project(request: Request, project_id: str):
    """Get project details."""
    return {"message": f"Project {project_id} - implementation pending"}


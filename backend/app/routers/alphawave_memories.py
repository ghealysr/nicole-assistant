"""
Memories router for memory management and retrieval.
"""

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_memories(request: Request):
    """List user memories."""
    return {"message": "Memories endpoint - implementation pending"}


@router.post("/")
async def create_memory(request: Request):
    """Create new memory."""
    return {"message": "Create memory - implementation pending"}


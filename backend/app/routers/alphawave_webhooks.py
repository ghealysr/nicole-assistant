"""
Webhooks router for external integrations.
"""

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/healthkit")
async def healthkit_webhook(request: Request):
    """Receive Apple HealthKit data."""
    return {"message": "HealthKit webhook - implementation pending"}


@router.post("/spotify")
async def spotify_webhook(request: Request):
    """Receive Spotify data."""
    return {"message": "Spotify webhook - implementation pending"}


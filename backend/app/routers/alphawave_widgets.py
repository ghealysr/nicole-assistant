"""
Widgets router for dashboard widget data endpoints.
"""

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/data/timeseries")
async def get_timeseries_data(request: Request):
    """Get timeseries data for charts."""
    return {"message": "Timeseries data - implementation pending"}


@router.get("/data/aggregate")
async def get_aggregate_data(request: Request):
    """Get aggregate statistics."""
    return {"message": "Aggregate data - implementation pending"}


"""
Journal Router for Nicole V7.
Handles daily journal entries and Nicole's responses.

QA NOTES:
- Users can submit one journal entry per day
- Nicole responds to entries at 11:59 PM (via background worker)
- Supports Spotify and HealthKit data integration
- Pattern detection across entries
"""

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import datetime
import logging
from uuid import UUID

from app.services.alphawave_journal_service import journal_service
from app.database import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


class JournalEntryCreate(BaseModel):
    """Request model for creating/updating a journal entry."""
    entry_date: Optional[datetime.date] = Field(None, description="Entry date (defaults to today)")
    content: str = Field(..., description="Journal entry text", min_length=1, max_length=10000)
    spotify_data: Optional[dict] = Field(None, description="Optional Spotify listening data")
    health_data: Optional[dict] = Field(None, description="Optional HealthKit data")


class JournalEntryResponse(BaseModel):
    """Response model for a journal entry."""
    id: Optional[str] = None
    date: str
    user_entry: str
    nicole_response: Optional[str] = None
    submitted_at: Optional[str] = None
    responded_at: Optional[str] = None
    spotify_data: Optional[dict] = None
    health_data: Optional[dict] = None


class JournalEntriesResponse(BaseModel):
    """Response model for listing entries."""
    entries: List[JournalEntryResponse]
    total: int
    has_more: bool


class PatternResponse(BaseModel):
    """Response model for detected patterns."""
    patterns: List[dict]
    analyzed_days: int


@router.post("/entry", response_model=JournalEntryResponse)
async def submit_journal_entry(request: Request, body: JournalEntryCreate):
    """
    Submit or update a daily journal entry.
    
    Only one entry per day per user. Submitting again will update
    the existing entry for that date.
    
    QA NOTE: Nicole will respond at 11:59 PM via background worker
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Use today if no date provided
    entry_date = body.entry_date or datetime.date.today()
    
    # Don't allow future entries
    if entry_date > datetime.date.today():
        raise HTTPException(
            status_code=400,
            detail="Cannot create journal entries for future dates"
        )
    
    try:
        # Create or update the entry
        result = await journal_service.create_or_update_entry(
            user_id=UUID(user_id),
            entry_date=entry_date,
            user_entry=body.content,
            spotify_data=body.spotify_data,
            health_data=body.health_data
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to save journal entry"
            )
        
        logger.info(f"Journal entry saved for user {user_id} on {entry_date}")
        
        return JournalEntryResponse(
            id=result.get("id"),
            date=result.get("date"),
            user_entry=result.get("user_entry"),
            nicole_response=result.get("nicole_response"),
            submitted_at=result.get("submitted_at"),
            responded_at=result.get("responded_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Journal entry error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save journal entry")


@router.get("/entry/{entry_date}", response_model=JournalEntryResponse)
async def get_journal_entry(request: Request, entry_date: datetime.date):
    """
    Get a specific journal entry by date.
    
    QA NOTE: Returns 404 if no entry exists for that date
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        entry = await journal_service.get_journal_entry(
            user_id=UUID(user_id),
            entry_date=entry_date
        )
        
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"No journal entry found for {entry_date}"
            )
        
        return JournalEntryResponse(
            id=entry.get("id"),
            date=entry.get("date"),
            user_entry=entry.get("user_entry"),
            nicole_response=entry.get("nicole_response"),
            submitted_at=entry.get("submitted_at"),
            responded_at=entry.get("responded_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get journal entry error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve entry")


@router.get("/entries", response_model=JournalEntriesResponse)
async def get_journal_entries(
    request: Request,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get journal entries history with pagination.
    
    Returns entries in reverse chronological order (newest first).
    
    QA NOTE: Maximum 100 entries per request
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        entries = await journal_service.get_all_entries(
            user_id=UUID(user_id),
            limit=limit + 1,  # Fetch one extra to check for more
            offset=offset
        )
        
        has_more = len(entries) > limit
        if has_more:
            entries = entries[:limit]
        
        return JournalEntriesResponse(
            entries=[
                JournalEntryResponse(
                    id=e.get("id"),
                    date=e.get("date"),
                    user_entry=e.get("user_entry"),
                    nicole_response=e.get("nicole_response"),
                    submitted_at=e.get("submitted_at"),
                    responded_at=e.get("responded_at")
                )
                for e in entries
            ],
            total=len(entries),
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Get journal entries error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve entries")


@router.get("/entries/recent", response_model=JournalEntriesResponse)
async def get_recent_entries(
    request: Request,
    days: int = Query(7, ge=1, le=30)
):
    """
    Get recent journal entries for the past N days.
    
    QA NOTE: Useful for dashboard widgets and pattern analysis
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        entries = await journal_service.get_recent_entries(
            user_id=UUID(user_id),
            days=days
        )
        
        return JournalEntriesResponse(
            entries=[
                JournalEntryResponse(
                    id=e.get("id"),
                    date=e.get("date"),
                    user_entry=e.get("user_entry"),
                    nicole_response=e.get("nicole_response"),
                    submitted_at=e.get("submitted_at"),
                    responded_at=e.get("responded_at")
                )
                for e in entries
            ],
            total=len(entries),
            has_more=False
        )
        
    except Exception as e:
        logger.error(f"Get recent entries error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve entries")


@router.get("/patterns", response_model=PatternResponse)
async def get_journal_patterns(
    request: Request,
    days: int = Query(30, ge=7, le=90)
):
    """
    Get detected patterns from journal entries.
    
    Analyzes mood, activity, and sleep patterns over time.
    
    QA NOTE: Requires at least 5 entries for meaningful patterns
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        patterns = await journal_service.detect_patterns(
            user_id=UUID(user_id),
            days=days
        )
        
        return PatternResponse(
            patterns=patterns,
            analyzed_days=days
        )
        
    except Exception as e:
        logger.error(f"Pattern detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze patterns")


@router.post("/entry/{entry_date}/respond")
async def trigger_nicole_response(request: Request, entry_date: datetime.date):
    """
    Manually trigger Nicole's response to a journal entry.
    
    Normally this happens automatically at 11:59 PM, but this endpoint
    allows triggering it immediately for testing or catch-up.
    
    QA NOTE: Useful for testing and for entries that missed the window
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get user info for personalization
    supabase = get_supabase()
    user_name = "friend"
    
    if supabase:
        try:
            user_response = supabase.table("users").select("name").eq(
                "id", user_id
            ).single().execute()
            if user_response.data:
                user_name = user_response.data.get("name", "friend")
        except Exception:
            pass
    
    try:
        response = await journal_service.generate_nicole_response(
            user_id=UUID(user_id),
            entry_date=entry_date,
            user_name=user_name
        )
        
        if not response:
            raise HTTPException(
                status_code=404,
                detail=f"No journal entry found for {entry_date} or response failed"
            )
        
        return {
            "success": True,
            "date": entry_date.isoformat(),
            "nicole_response": response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Nicole response error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate response")


@router.get("/today")
async def get_today_status(request: Request):
    """
    Get today's journal status.
    
    Returns whether the user has submitted today's entry
    and if Nicole has responded.
    
    QA NOTE: Useful for UI to show journal reminder
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        entry = await journal_service.get_journal_entry(
            user_id=UUID(user_id),
            entry_date=datetime.date.today()
        )
        
        return {
            "date": datetime.date.today().isoformat(),
            "has_entry": entry is not None,
            "has_response": entry.get("nicole_response") is not None if entry else False,
            "word_count": len(entry.get("user_entry", "").split()) if entry else 0
        }
        
    except Exception as e:
        logger.error(f"Today status error: {e}", exc_info=True)
        return {
            "date": datetime.date.today().isoformat(),
            "has_entry": False,
            "has_response": False,
            "word_count": 0
        }

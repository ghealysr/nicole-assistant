"""
Memory entry model for structured semantic memory system.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class AlphawaveMemoryEntry(BaseModel):
    """
    Memory entry for 3-tier memory system.
    
    Attributes:
        id: Unique memory identifier
        user_id: Memory owner
        memory_type: Type of memory (fact, preference, pattern, etc.)
        content: Memory content text
        context: Context in which memory was created
        confidence_score: Confidence (0-1, decays 3%/week if unused)
        importance_score: Importance (0-1, resists decay)
        access_count: Number of times memory was retrieved
        last_accessed: Last access timestamp (bumps confidence +2%)
        created_at: Creation timestamp
        archived_at: Optional archival timestamp (confidence < 0.2)
    """
    
    id: UUID
    user_id: UUID
    memory_type: Literal["fact", "preference", "pattern", "relationship", "goal", "correction"]
    content: str
    context: str
    confidence_score: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)
    importance_score: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)
    access_count: int = Field(default=0, ge=0)
    last_accessed: Optional[datetime] = None
    created_at: datetime
    archived_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlphawaveMemoryCreate(BaseModel):
    """Memory creation model."""
    memory_type: Literal["fact", "preference", "pattern", "relationship", "goal", "correction"]
    content: str
    context: str
    importance_score: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)


class AlphawaveMemoryUpdate(BaseModel):
    """Memory update model."""
    confidence_score: Optional[Decimal] = Field(default=None, ge=0, le=1)
    access_count: Optional[int] = Field(default=None, ge=0)
    last_accessed: Optional[datetime] = None
    archived_at: Optional[datetime] = None


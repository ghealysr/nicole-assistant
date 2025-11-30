"""
Memory entry models for structured semantic memory system.

Enhanced to support:
- Knowledge base organization
- Source tracking (user, nicole, system, extraction, consolidation)
- Sharing between family members
- Memory hierarchies (parent/child)
- Embedding status tracking
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from datetime import datetime
from decimal import Decimal


MemoryType = Literal["fact", "preference", "pattern", "relationship", "goal", "correction"]
MemorySource = Literal["user", "nicole", "system", "extraction", "consolidation"]
EmbeddingStatus = Literal["pending", "completed", "failed", "skipped"]


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
        
        NEW FIELDS:
        knowledge_base_id: Optional link to knowledge base
        source: Who/what created this memory
        is_shared: Whether memory is shared with family
        parent_memory_id: Parent memory (for elaborations/corrections)
        embedding_status: Vector storage state
    """
    
    id: int
    user_id: int
    memory_type: MemoryType
    content: str
    context: Optional[str]
    confidence_score: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)
    importance_score: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)
    access_count: int = Field(default=0, ge=0)
    last_accessed: Optional[datetime] = None
    created_at: datetime
    archived_at: Optional[datetime] = None
    
    # New fields
    knowledge_base_id: Optional[int] = None
    source: MemorySource = "user"
    is_shared: bool = False
    parent_memory_id: Optional[int] = None
    embedding_status: EmbeddingStatus = "pending"
    
    # Computed/expanded fields (populated by service)
    tags: List[str] = Field(default_factory=list)
    related_memory_ids: List[UUID] = Field(default_factory=list)
    knowledge_base_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlphawaveMemoryCreate(BaseModel):
    """Memory creation model."""
    memory_type: MemoryType
    content: str = Field(..., min_length=1, max_length=10000)
    context: Optional[str] = Field(None, max_length=2000)
    importance_score: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)
    
    # New optional fields
    knowledge_base_id: Optional[int] = None
    source: MemorySource = "user"
    is_shared: bool = False
    parent_memory_id: Optional[int] = None
    tag_ids: List[int] = Field(default_factory=list)


class AlphawaveMemoryUpdate(BaseModel):
    """Memory update model."""
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    context: Optional[str] = Field(None, max_length=2000)
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    importance_score: Optional[Decimal] = Field(None, ge=0, le=1)
    knowledge_base_id: Optional[int] = None
    is_shared: Optional[bool] = None
    archived_at: Optional[datetime] = None


class MemorySearchQuery(BaseModel):
    """Search query for memories."""
    query: str = Field(..., min_length=1, max_length=500)
    memory_types: Optional[List[MemoryType]] = None
    knowledge_base_id: Optional[int] = None
    min_confidence: float = Field(default=0.1, ge=0, le=1)
    include_shared: bool = True
    include_archived: bool = False
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MemorySearchResult(BaseModel):
    """Search result item."""
    memory: AlphawaveMemoryEntry
    score: float
    source: Literal["vector", "structured", "combined"]
    highlights: List[str] = Field(default_factory=list)


class MemorySearchResponse(BaseModel):
    """Search response with results and metadata."""
    results: List[MemorySearchResult]
    total_count: int
    query: str
    search_time_ms: float


class MemoryStats(BaseModel):
    """Memory statistics for a user."""
    total_memories: int
    by_type: dict[str, int]
    by_knowledge_base: dict[str, int]
    average_confidence: float
    average_importance: float
    total_accesses: int
    recent_additions: int
    archived_count: int
    shared_count: int
    last_updated: datetime


class BulkMemoryOperation(BaseModel):
    """Bulk operation on memories."""
    memory_ids: List[int]
    operation: Literal[
        "archive",
        "unarchive", 
        "move_to_kb",
        "add_tag",
        "remove_tag",
        "boost_confidence",
        "share",
        "unshare"
    ]
    # Operation-specific parameters
    knowledge_base_id: Optional[int] = None
    tag_id: Optional[int] = None
    confidence_boost: Optional[float] = None


class MemoryConsolidateRequest(BaseModel):
    """Request to consolidate multiple memories."""
    memory_ids: List[int] = Field(..., min_items=2)
    consolidation_type: Literal["merge", "summarize", "deduplicate"] = "merge"
    keep_originals: bool = True  # Archive originals or delete


class NicoleMemoryCreateRequest(BaseModel):
    """
    Request for Nicole to proactively create a memory.
    Used when Nicole wants to remember something without user message.
    """
    content: str = Field(..., min_length=1, max_length=10000)
    memory_type: MemoryType
    context: Optional[str] = None
    importance_score: float = Field(default=0.7, ge=0, le=1)
    knowledge_base_id: Optional[int] = None
    knowledge_base_name: Optional[str] = None  # Create new KB if doesn't exist
    reason: str  # Why Nicole is creating this memory
    tag_ids: List[int] = Field(default_factory=list)

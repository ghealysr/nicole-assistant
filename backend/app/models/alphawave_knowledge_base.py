"""
Knowledge Base models for memory organization system.

Knowledge bases allow Nicole and users to organize memories into
hierarchical projects, topics, and domains.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


KBType = Literal[
    'project',    # Work projects, coding projects
    'topic',      # Learning topics, interests
    'client',     # Client-specific knowledge
    'personal',   # Personal life organization
    'family',     # Family-related memories
    'health',     # Health and wellness
    'financial',  # Financial matters
    'system'      # Nicole's internal organization
]


class KnowledgeBaseCreate(BaseModel):
    """Create a new knowledge base."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: str = Field(default='📁', max_length=10)
    color: str = Field(default='#B8A8D4', pattern=r'^#[0-9A-Fa-f]{6}$')
    parent_id: Optional[UUID] = None
    kb_type: KBType = 'topic'
    is_shared: bool = False
    shared_with: List[UUID] = Field(default_factory=list)


class KnowledgeBaseUpdate(BaseModel):
    """Update an existing knowledge base."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    parent_id: Optional[UUID] = None
    kb_type: Optional[KBType] = None
    is_shared: Optional[bool] = None
    shared_with: Optional[List[UUID]] = None
    archived_at: Optional[datetime] = None


class KnowledgeBase(BaseModel):
    """Full knowledge base model."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    icon: str
    color: str
    parent_id: Optional[UUID]
    kb_type: KBType
    is_shared: bool
    shared_with: List[UUID]
    memory_count: int
    last_memory_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    
    # Computed fields (populated by service)
    children: List['KnowledgeBase'] = Field(default_factory=list)
    path: List[str] = Field(default_factory=list)  # Breadcrumb path
    
    class Config:
        from_attributes = True


class KnowledgeBaseTree(BaseModel):
    """Hierarchical tree of knowledge bases."""
    roots: List[KnowledgeBase]
    total_count: int
    total_memories: int


class KnowledgeBaseSummary(BaseModel):
    """Lightweight knowledge base summary for lists."""
    id: UUID
    name: str
    icon: str
    color: str
    kb_type: KBType
    memory_count: int
    has_children: bool


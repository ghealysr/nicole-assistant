"""
Knowledge Base models for memory organization system.

Knowledge bases allow Nicole and users to organize memories into
hierarchical projects, topics, and domains.

Note: Uses int IDs to match Tiger Postgres BIGINT primary keys.
Currently implemented using the `category` field on memory_entries.
Future enhancement: dedicated knowledge_bases table.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Union
from datetime import datetime


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
    parent_id: Optional[int] = None
    kb_type: KBType = 'topic'
    is_shared: bool = False
    shared_with: List[int] = Field(default_factory=list)


class KnowledgeBaseUpdate(BaseModel):
    """Update an existing knowledge base."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    parent_id: Optional[int] = None
    kb_type: Optional[KBType] = None
    is_shared: Optional[bool] = None
    shared_with: Optional[List[int]] = None
    archived_at: Optional[datetime] = None


class KnowledgeBase(BaseModel):
    """Full knowledge base model."""
    id: Union[int, str]  # Can be int or category name string
    user_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    icon: str = '📁'
    color: str = '#B8A8D4'
    parent_id: Optional[int] = None
    kb_type: KBType = 'topic'
    is_shared: bool = False
    shared_with: List[int] = Field(default_factory=list)
    memory_count: int = 0
    last_memory_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    # Computed fields (populated by service)
    children: List['KnowledgeBase'] = Field(default_factory=list)
    path: List[str] = Field(default_factory=list)  # Breadcrumb path
    
    class Config:
        from_attributes = True


class KnowledgeBaseTree(BaseModel):
    """Hierarchical tree of knowledge bases."""
    roots: List[KnowledgeBase] = Field(default_factory=list)
    total_count: int = 0
    total_memories: int = 0


class KnowledgeBaseSummary(BaseModel):
    """Lightweight knowledge base summary for lists."""
    id: Union[int, str]
    name: str
    icon: str = '📁'
    color: str = '#B8A8D4'
    kb_type: KBType = 'topic'
    memory_count: int = 0
    has_children: bool = False


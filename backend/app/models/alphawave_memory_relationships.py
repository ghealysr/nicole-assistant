"""
Memory Relationship models for linking related memories.

Relationships help Nicole understand how memories connect,
enabling better context and pattern detection.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


RelationshipType = Literal[
    'related_to',       # General relation
    'contradicts',      # Memory contradicts another (correction)
    'elaborates',       # Memory adds detail to another
    'supersedes',       # Memory replaces/updates another
    'derived_from',     # Memory was created from another
    'references',       # Memory references another
    'same_topic',       # Memories are about same topic
    'same_entity',      # Memories are about same person/thing
    'temporal_sequence' # Memories are part of a sequence
]

CreatedBy = Literal['user', 'nicole', 'system']


class MemoryRelationshipCreate(BaseModel):
    """Create a relationship between two memories."""
    source_memory_id: UUID
    target_memory_id: UUID
    relationship_type: RelationshipType = 'related_to'
    strength: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)
    created_by: CreatedBy = 'nicole'


class MemoryRelationship(BaseModel):
    """Full memory relationship model."""
    id: UUID
    source_memory_id: UUID
    target_memory_id: UUID
    relationship_type: RelationshipType
    strength: Decimal
    created_by: CreatedBy
    created_at: datetime
    
    class Config:
        from_attributes = True


class MemoryRelationshipExpanded(MemoryRelationship):
    """Relationship with expanded memory details."""
    source_memory_content: Optional[str] = None
    target_memory_content: Optional[str] = None
    source_memory_type: Optional[str] = None
    target_memory_type: Optional[str] = None


ConsolidationType = Literal[
    'merge',        # Multiple memories merged into one
    'summarize',    # Long memory summarized
    'deduplicate',  # Duplicate memories merged
    'upgrade'       # Memory updated with new information
]


class MemoryConsolidationCreate(BaseModel):
    """Create a consolidation record."""
    consolidated_memory_id: UUID
    source_memory_ids: List[UUID]
    consolidation_type: ConsolidationType
    reason: Optional[str] = None
    model_used: Optional[str] = None


class MemoryConsolidation(BaseModel):
    """Full consolidation record."""
    id: UUID
    consolidated_memory_id: UUID
    source_memory_ids: List[UUID]
    consolidation_type: ConsolidationType
    reason: Optional[str]
    model_used: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class NicoleActionType = Literal[
    'create_memory',
    'create_knowledge_base',
    'organize_memories',
    'consolidate_memories',
    'tag_memory',
    'link_memories',
    'archive_memory',
    'boost_confidence',
    'decay_memory'
]


class TargetType = Literal['memory', 'knowledge_base', 'tag', 'relationship']


class NicoleMemoryAction(BaseModel):
    """Record of Nicole's proactive memory management action."""
    id: UUID
    action_type: NicoleActionType
    target_type: TargetType
    target_id: UUID
    user_id: Optional[UUID]
    reason: Optional[str]
    context: Optional[dict]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class NicoleMemoryActionCreate(BaseModel):
    """Create a Nicole action record."""
    action_type: NicoleActionType
    target_type: TargetType
    target_id: UUID
    user_id: Optional[UUID] = None
    reason: Optional[str] = None
    context: Optional[dict] = None
    success: bool = True
    error_message: Optional[str] = None


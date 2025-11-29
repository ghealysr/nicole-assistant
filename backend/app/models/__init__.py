"""
Nicole V7 Pydantic Models

All data models for validation and serialization.
"""

from app.models.alphawave_memory import (
    AlphawaveMemoryEntry,
    AlphawaveMemoryCreate,
    AlphawaveMemoryUpdate,
    MemorySearchQuery,
    MemorySearchResult,
    MemorySearchResponse,
    MemoryStats,
    BulkMemoryOperation,
    MemoryConsolidateRequest,
    NicoleMemoryCreateRequest
)

from app.models.alphawave_knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseTree,
    KnowledgeBaseSummary
)

from app.models.alphawave_memory_tags import (
    MemoryTag,
    MemoryTagCreate,
    MemoryTagUpdate,
    TagAssignment,
    TagAssignmentCreate,
    BulkTagAssignment
)

from app.models.alphawave_memory_relationships import (
    MemoryRelationship,
    MemoryRelationshipCreate,
    MemoryRelationshipExpanded,
    MemoryConsolidation,
    MemoryConsolidationCreate,
    NicoleMemoryAction,
    NicoleMemoryActionCreate
)

__all__ = [
    # Memory
    "AlphawaveMemoryEntry",
    "AlphawaveMemoryCreate",
    "AlphawaveMemoryUpdate",
    "MemorySearchQuery",
    "MemorySearchResult",
    "MemorySearchResponse",
    "MemoryStats",
    "BulkMemoryOperation",
    "MemoryConsolidateRequest",
    "NicoleMemoryCreateRequest",
    
    # Knowledge Base
    "KnowledgeBase",
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseTree",
    "KnowledgeBaseSummary",
    
    # Tags
    "MemoryTag",
    "MemoryTagCreate",
    "MemoryTagUpdate",
    "TagAssignment",
    "TagAssignmentCreate",
    "BulkTagAssignment",
    
    # Relationships
    "MemoryRelationship",
    "MemoryRelationshipCreate",
    "MemoryRelationshipExpanded",
    "MemoryConsolidation",
    "MemoryConsolidationCreate",
    "NicoleMemoryAction",
    "NicoleMemoryActionCreate"
]


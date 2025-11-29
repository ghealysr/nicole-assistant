"""
Memory API Router - Nicole V7
Complete memory management endpoints.

Provides:
- CRUD operations for memories
- Knowledge base management
- Tag management
- Memory search and organization
- Nicole's proactive memory capabilities
- Memory statistics and insights

All endpoints require authentication via JWT.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
import logging

from app.services.alphawave_memory_service import memory_service
from app.middleware.alphawave_auth import get_current_user_id
from app.models.alphawave_memory import (
    AlphawaveMemoryCreate,
    AlphawaveMemoryUpdate,
    MemorySearchQuery,
    BulkMemoryOperation,
    MemoryConsolidateRequest,
    NicoleMemoryCreateRequest
)
from app.models.alphawave_knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate
)
from app.models.alphawave_memory_tags import (
    MemoryTagCreate,
    BulkTagAssignment
)
from app.models.alphawave_memory_relationships import (
    MemoryRelationshipCreate
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/")
async def list_memories(
    request: Request,
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    knowledge_base_id: Optional[UUID] = Query(None, description="Filter by knowledge base"),
    include_archived: bool = Query(False, description="Include archived memories"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List user's memories with optional filters.
    
    Returns paginated list of memories, sorted by creation date.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        memories = await memory_service.get_recent_memories(
            user_id=str(user_id),
            limit=limit,
            memory_type=memory_type,
            knowledge_base_id=str(knowledge_base_id) if knowledge_base_id else None
        )

        return {
            "memories": memories,
            "count": len(memories),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"[MEMORIES] List error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list memories")


@router.get("/{memory_id}")
async def get_memory(request: Request, memory_id: UUID):
    """
    Get a single memory by ID.
    
    Returns full memory details including tags and relationships.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    memory = await memory_service.get_memory(str(memory_id), str(user_id))

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.post("/")
async def create_memory(request: Request, memory_data: AlphawaveMemoryCreate):
    """
    Create a new memory.
    
    Automatically generates embeddings for vector search.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        memory = await memory_service.save_memory(
            user_id=str(user_id),
            memory_type=memory_data.memory_type,
            content=memory_data.content,
            context=memory_data.context,
            importance=float(memory_data.importance_score),
            knowledge_base_id=str(memory_data.knowledge_base_id) if memory_data.knowledge_base_id else None,
            source=memory_data.source,
            is_shared=memory_data.is_shared,
            parent_memory_id=str(memory_data.parent_memory_id) if memory_data.parent_memory_id else None,
            tag_ids=[str(t) for t in memory_data.tag_ids] if memory_data.tag_ids else None
        )

        if not memory:
            raise HTTPException(status_code=400, detail="Failed to create memory")

        return memory

    except Exception as e:
        logger.error(f"[MEMORIES] Create error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create memory")


@router.put("/{memory_id}")
async def update_memory(
    request: Request,
    memory_id: UUID,
    updates: AlphawaveMemoryUpdate
):
    """
    Update an existing memory.
    
    Re-generates embeddings if content changes.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        memory = await memory_service.update_memory(
            memory_id=str(memory_id),
            user_id=str(user_id),
            updates=updates.model_dump(exclude_unset=True)
        )

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found or update failed")

        return memory

    except Exception as e:
        logger.error(f"[MEMORIES] Update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update memory")


@router.delete("/{memory_id}")
async def delete_memory(request: Request, memory_id: UUID):
    """
    Delete (archive) a memory.
    
    Memories are soft-deleted (archived) not permanently removed.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    success = await memory_service.delete_memory(str(memory_id), str(user_id))

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"status": "archived", "memory_id": str(memory_id)}


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/search")
async def search_memories(request: Request, search_query: MemorySearchQuery):
    """
    Search memories using hybrid search (vector + structured).
    
    Combines semantic similarity with confidence-based ranking.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        import time
        start = time.time()

        results = await memory_service.search_memory(
            user_id=str(user_id),
            query=search_query.query,
            limit=search_query.limit,
            memory_types=search_query.memory_types,
            knowledge_base_id=str(search_query.knowledge_base_id) if search_query.knowledge_base_id else None,
            min_confidence=search_query.min_confidence,
            include_shared=search_query.include_shared,
            include_archived=search_query.include_archived
        )

        search_time = (time.time() - start) * 1000

        return {
            "results": results,
            "total_count": len(results),
            "query": search_query.query,
            "search_time_ms": round(search_time, 2)
        }

    except Exception as e:
        logger.error(f"[MEMORIES] Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/search/quick")
async def quick_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Quick search endpoint for autocomplete/suggestions.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    results = await memory_service.search_memory(
        user_id=str(user_id),
        query=q,
        limit=limit,
        min_confidence=0.3
    )

    return {
        "results": [{"id": r["id"], "content": r["content"][:100], "type": r["memory_type"]} for r in results],
        "query": q
    }


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/knowledge-bases")
async def list_knowledge_bases(
    request: Request,
    kb_type: Optional[str] = Query(None),
    include_shared: bool = Query(True)
):
    """
    List all knowledge bases for the user.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    kbs = await memory_service.get_knowledge_bases(
        user_id=str(user_id),
        include_shared=include_shared,
        kb_type=kb_type
    )

    return {"knowledge_bases": kbs, "count": len(kbs)}


@router.get("/knowledge-bases/tree")
async def get_knowledge_base_tree(request: Request):
    """
    Get hierarchical tree of knowledge bases.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    tree = await memory_service.get_knowledge_base_tree(str(user_id))
    return tree


@router.post("/knowledge-bases")
async def create_knowledge_base(request: Request, kb_data: KnowledgeBaseCreate):
    """
    Create a new knowledge base for organizing memories.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    kb = await memory_service.create_knowledge_base(
        user_id=str(user_id),
        name=kb_data.name,
        description=kb_data.description,
        kb_type=kb_data.kb_type,
        parent_id=str(kb_data.parent_id) if kb_data.parent_id else None,
        icon=kb_data.icon,
        color=kb_data.color,
        is_shared=kb_data.is_shared,
        created_by="user"
    )

    if not kb:
        raise HTTPException(status_code=400, detail="Failed to create knowledge base")

    return kb


@router.post("/knowledge-bases/{kb_id}/organize")
async def organize_memories(
    request: Request,
    kb_id: UUID,
    memory_ids: List[UUID]
):
    """
    Move memories into a knowledge base.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    count = await memory_service.organize_memories_into_kb(
        user_id=str(user_id),
        memory_ids=[str(m) for m in memory_ids],
        knowledge_base_id=str(kb_id),
        organized_by="user"
    )

    return {"organized": count, "knowledge_base_id": str(kb_id)}


# ═══════════════════════════════════════════════════════════════════════════════
# TAGS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tags")
async def list_tags(
    request: Request,
    include_system: bool = Query(True)
):
    """
    List available tags (system + user's custom tags).
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    tags = await memory_service.get_tags(
        user_id=str(user_id),
        include_system=include_system
    )

    return {"tags": tags, "count": len(tags)}


@router.post("/tags")
async def create_tag(request: Request, tag_data: MemoryTagCreate):
    """
    Create a custom tag.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    tag = await memory_service.create_tag(
        user_id=str(user_id),
        name=tag_data.name,
        description=tag_data.description,
        color=tag_data.color,
        icon=tag_data.icon,
        tag_type=tag_data.tag_type
    )

    if not tag:
        raise HTTPException(status_code=400, detail="Failed to create tag")

    return tag


@router.post("/{memory_id}/tags")
async def tag_memory(
    request: Request,
    memory_id: UUID,
    tag_assignment: BulkTagAssignment
):
    """
    Assign tags to a memory.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    count = await memory_service.tag_memory(
        memory_id=str(memory_id),
        tag_ids=[str(t) for t in tag_assignment.tag_ids],
        assigned_by=tag_assignment.assigned_by
    )

    return {"assigned": count, "memory_id": str(memory_id)}


@router.delete("/{memory_id}/tags/{tag_id}")
async def untag_memory(request: Request, memory_id: UUID, tag_id: UUID):
    """
    Remove a tag from a memory.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    success = await memory_service.untag_memory(str(memory_id), str(tag_id))

    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove tag")

    return {"status": "removed"}


# ═══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIPS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/relationships")
async def link_memories(request: Request, relationship: MemoryRelationshipCreate):
    """
    Create a relationship between two memories.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    rel = await memory_service.link_memories(
        source_id=str(relationship.source_memory_id),
        target_id=str(relationship.target_memory_id),
        relationship_type=relationship.relationship_type,
        strength=float(relationship.strength),
        created_by=relationship.created_by
    )

    if not rel:
        raise HTTPException(status_code=400, detail="Failed to create relationship")

    return rel


@router.get("/{memory_id}/related")
async def get_related_memories(
    request: Request,
    memory_id: UUID,
    relationship_types: Optional[str] = Query(None, description="Comma-separated types")
):
    """
    Get memories related to a given memory.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    types = relationship_types.split(",") if relationship_types else None

    related = await memory_service.get_related_memories(
        memory_id=str(memory_id),
        relationship_types=types
    )

    return {"related": related, "count": len(related)}


# ═══════════════════════════════════════════════════════════════════════════════
# BULK OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/bulk")
async def bulk_operation(request: Request, operation: BulkMemoryOperation):
    """
    Perform bulk operations on multiple memories.
    
    Operations: archive, unarchive, move_to_kb, add_tag, remove_tag,
    boost_confidence, share, unshare
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        affected = 0
        memory_ids = [str(m) for m in operation.memory_ids]

        if operation.operation == "archive":
            for mid in memory_ids:
                if await memory_service.delete_memory(mid, str(user_id)):
                    affected += 1

        elif operation.operation == "move_to_kb" and operation.knowledge_base_id:
            affected = await memory_service.organize_memories_into_kb(
                str(user_id), memory_ids, str(operation.knowledge_base_id)
            )

        elif operation.operation == "add_tag" and operation.tag_id:
            for mid in memory_ids:
                count = await memory_service.tag_memory(mid, [str(operation.tag_id)], "user")
                affected += count

        elif operation.operation == "boost_confidence":
            boost = operation.confidence_boost or 0.1
            for mid in memory_ids:
                if await memory_service.bump_confidence(mid, boost):
                    affected += 1

        return {
            "operation": operation.operation,
            "affected": affected,
            "total_requested": len(memory_ids)
        }

    except Exception as e:
        logger.error(f"[MEMORIES] Bulk operation error: {e}")
        raise HTTPException(status_code=500, detail="Bulk operation failed")


@router.post("/consolidate")
async def consolidate_memories(request: Request, consolidate: MemoryConsolidateRequest):
    """
    Consolidate multiple memories into one.
    
    Uses AI to intelligently merge related memories.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        result = await memory_service.consolidate_memories(
            user_id=str(user_id),
            memory_ids=[str(m) for m in consolidate.memory_ids],
            consolidation_type=consolidate.consolidation_type,
            keep_originals=consolidate.keep_originals
        )

        if not result:
            raise HTTPException(status_code=400, detail="Consolidation failed")

        return {
            "consolidated_memory": result,
            "source_count": len(consolidate.memory_ids),
            "originals_archived": consolidate.keep_originals
        }

    except Exception as e:
        logger.error(f"[MEMORIES] Consolidate error: {e}")
        raise HTTPException(status_code=500, detail="Consolidation failed")


# ═══════════════════════════════════════════════════════════════════════════════
# NICOLE'S CAPABILITIES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/nicole/create")
async def nicole_create_memory(request: Request, memory_request: NicoleMemoryCreateRequest):
    """
    Nicole proactively creates a memory.
    
    Used when Nicole wants to remember something she's learned.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    memory = await memory_service.nicole_create_memory(
        user_id=str(user_id),
        content=memory_request.content,
        memory_type=memory_request.memory_type,
        reason=memory_request.reason,
        context=memory_request.context,
        importance=memory_request.importance_score,
        knowledge_base_name=memory_request.knowledge_base_name,
        tag_ids=[str(t) for t in memory_request.tag_ids] if memory_request.tag_ids else None
    )

    if not memory:
        raise HTTPException(status_code=400, detail="Failed to create memory")

    return {
        "memory": memory,
        "created_by": "nicole",
        "reason": memory_request.reason
    }


@router.post("/nicole/organize/{topic}")
async def nicole_organize_topic(
    request: Request,
    topic: str,
    create_kb: bool = Query(True)
):
    """
    Nicole organizes memories about a specific topic.
    
    Creates a knowledge base and links related memories.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await memory_service.nicole_organize_topic(
        user_id=str(user_id),
        topic=topic,
        create_kb=create_kb
    )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS & INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_memory_stats(request: Request):
    """
    Get comprehensive memory statistics.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    stats = await memory_service.get_memory_stats(str(user_id))

    if "error" in stats:
        raise HTTPException(status_code=500, detail=stats["error"])

    return stats


@router.post("/learn-correction")
async def learn_from_correction(
    request: Request,
    original: str,
    corrected: str,
    context: Optional[str] = None
):
    """
    Record a correction for learning.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    success = await memory_service.learn_from_correction(
        user_id=str(user_id),
        original_content=original,
        corrected_content=corrected,
        context=context
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to record correction")

    return {"status": "learned", "original": original[:50], "corrected": corrected[:50]}

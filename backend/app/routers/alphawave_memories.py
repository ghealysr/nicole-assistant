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
from typing import Optional, List, Tuple
import logging

from app.services.alphawave_memory_service import memory_service
from app.middleware.alphawave_auth import (
    get_current_user_id,
    get_current_tiger_user_id,
)
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


def _require_user_ids(request: Request) -> tuple[str, int]:
    """Ensure both Supabase and Tiger user identifiers are present."""
    supabase_user_id = get_current_user_id(request)
    tiger_user_id = get_current_tiger_user_id(request)

    if not supabase_user_id or tiger_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user context missing",
        )

    return str(supabase_user_id), int(tiger_user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/")
async def list_memories(
    request: Request,
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    knowledge_base_id: Optional[int] = Query(None, description="Filter by knowledge base"),
    include_archived: bool = Query(False, description="Include archived memories"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List user's memories with optional filters.
    
    Returns paginated list of memories, sorted by creation date.
    """
    _, tiger_user_id = _require_user_ids(request)

    try:
        memories = await memory_service.get_recent_memories(
            user_id=tiger_user_id,
            limit=limit,
            memory_type=memory_type,
            knowledge_base_id=knowledge_base_id,
            include_archived=include_archived,
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
async def get_memory(request: Request, memory_id: int):
    """
    Get a single memory by ID.
    
    Returns full memory details including tags and relationships.
    """
    _, tiger_user_id = _require_user_ids(request)

    memory = await memory_service.get_memory(memory_id, tiger_user_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.post("/")
async def create_memory(request: Request, memory_data: AlphawaveMemoryCreate):
    """
    Create a new memory.
    
    Automatically generates embeddings for vector search.
    """
    _, tiger_user_id = _require_user_ids(request)

    try:
        memory = await memory_service.save_memory(
            user_id=tiger_user_id,
            memory_type=memory_data.memory_type,
            content=memory_data.content,
            context=memory_data.context,
            importance=float(memory_data.importance_score),
            knowledge_base_id=memory_data.knowledge_base_id,
            source=memory_data.source,
            is_shared=memory_data.is_shared,
            parent_memory_id=memory_data.parent_memory_id,
            tag_ids=memory_data.tag_ids or None,
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
    memory_id: int,
    updates: AlphawaveMemoryUpdate,
):
    """
    Update an existing memory.
    
    Re-generates embeddings if content changes.
    """
    _, tiger_user_id = _require_user_ids(request)

    try:
        memory = await memory_service.update_memory(
            memory_id=memory_id,
            user_id=tiger_user_id,
            updates=updates.model_dump(exclude_unset=True),
        )

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found or update failed")

        return memory

    except Exception as e:
        logger.error(f"[MEMORIES] Update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update memory")


@router.delete("/{memory_id}")
async def delete_memory(request: Request, memory_id: int):
    """
    Delete (archive) a memory.
    
    Memories are soft-deleted (archived) not permanently removed.
    """
    _, tiger_user_id = _require_user_ids(request)

    success = await memory_service.delete_memory(memory_id, tiger_user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"status": "archived", "memory_id": memory_id}


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/search")
async def search_memories(request: Request, search_query: MemorySearchQuery):
    """
    Search memories using hybrid search (vector + structured).
    
    Combines semantic similarity with confidence-based ranking.
    """
    _, tiger_user_id = _require_user_ids(request)

    try:
        import time
        start = time.time()

        results = await memory_service.search_memory(
            user_id=tiger_user_id,
            query=search_query.query,
            limit=search_query.limit,
            memory_types=search_query.memory_types,
            knowledge_base_id=search_query.knowledge_base_id,
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
    _, tiger_user_id = _require_user_ids(request)

    results = await memory_service.search_memory(
        user_id=tiger_user_id,
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
    _, tiger_user_id = _require_user_ids(request)

    kbs = await memory_service.get_knowledge_bases(
        user_id=tiger_user_id,
        include_shared=include_shared,
        kb_type=kb_type
    )

    return {"knowledge_bases": kbs, "count": len(kbs)}


@router.get("/knowledge-bases/tree")
async def get_knowledge_base_tree(request: Request):
    """
    Get hierarchical tree of knowledge bases.
    """
    _, tiger_user_id = _require_user_ids(request)

    tree = await memory_service.get_knowledge_base_tree(tiger_user_id)
    return tree


@router.post("/knowledge-bases")
async def create_knowledge_base(request: Request, kb_data: KnowledgeBaseCreate):
    """
    Create a new knowledge base for organizing memories.
    """
    _, tiger_user_id = _require_user_ids(request)

    kb = await memory_service.create_knowledge_base(tiger_user_id, kb_data)

    if not kb:
        raise HTTPException(status_code=400, detail="Failed to create knowledge base")

    return kb


@router.post("/knowledge-bases/{kb_id}/organize")
async def organize_memories(
    request: Request,
    kb_id: int,
    memory_ids: List[int],
):
    """
    Move memories into a knowledge base.
    """
    _, tiger_user_id = _require_user_ids(request)

    count = await memory_service.organize_memories_into_kb(
        user_id=tiger_user_id,
        memory_ids=memory_ids,
        knowledge_base_id=kb_id,
        organized_by="user",
    )

    return {"organized": count, "knowledge_base_id": kb_id}


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
    _, tiger_user_id = _require_user_ids(request)

    tags = await memory_service.get_tags(
        user_id=tiger_user_id,
        include_system=include_system,
    )

    return {"tags": tags, "count": len(tags)}


@router.post("/tags")
async def create_tag(request: Request, tag_data: MemoryTagCreate):
    """
    Create a custom tag.
    """
    _, tiger_user_id = _require_user_ids(request)

    tag = await memory_service.create_tag(tiger_user_id, tag_data)

    if not tag:
        raise HTTPException(status_code=400, detail="Failed to create tag")

    return tag


@router.post("/{memory_id}/tags")
async def tag_memory(
    request: Request,
    memory_id: int,
    tag_assignment: BulkTagAssignment,
):
    """
    Assign tags to a memory.
    """
    _, tiger_user_id = _require_user_ids(request)

    count = await memory_service.tag_memory(
        memory_id=memory_id,
        tag_ids=[int(t) for t in tag_assignment.tag_ids],
        assigned_by=tag_assignment.assigned_by,
    )

    return {"assigned": count, "memory_id": memory_id}


@router.delete("/{memory_id}/tags/{tag_id}")
async def untag_memory(request: Request, memory_id: int, tag_id: int):
    """
    Remove a tag from a memory.
    """
    _, tiger_user_id = _require_user_ids(request)

    success = await memory_service.untag_memory(memory_id, tag_id)

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
    _, tiger_user_id = _require_user_ids(request)

    rel = await memory_service.link_memories(
        user_id=tiger_user_id,
        source_memory_id=relationship.source_memory_id,
        target_memory_id=relationship.target_memory_id,
        relationship_type=relationship.relationship_type,
        strength=float(relationship.strength),
        created_by=relationship.created_by,
    )

    if not rel:
        raise HTTPException(status_code=400, detail="Failed to create relationship")

    return rel


@router.get("/{memory_id}/related")
async def get_related_memories(
    request: Request,
    memory_id: int,
    relationship_types: Optional[str] = Query(None, description="Comma-separated types"),
):
    """
    Get memories related to a given memory.
    """
    _require_user_ids(request)
    types = relationship_types.split(",") if relationship_types else None

    related = await memory_service.get_related_memories(
        memory_id=memory_id,
        relationship_types=types,
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
    _, tiger_user_id = _require_user_ids(request)

    try:
        affected = 0
        memory_ids = operation.memory_ids

        if operation.operation == "archive":
            for mid in memory_ids:
                if await memory_service.delete_memory(mid, tiger_user_id):
                    affected += 1

        elif operation.operation == "move_to_kb" and operation.knowledge_base_id:
            affected = await memory_service.organize_memories_into_kb(
                tiger_user_id,
                memory_ids,
                operation.knowledge_base_id,
            )

        elif operation.operation == "add_tag" and operation.tag_id:
            for mid in memory_ids:
                count = await memory_service.tag_memory(mid, [operation.tag_id], "user")
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
    _, tiger_user_id = _require_user_ids(request)

    try:
        result = await memory_service.consolidate_memories(tiger_user_id, consolidate)

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
    _, tiger_user_id = _require_user_ids(request)

    memory = await memory_service.nicole_create_memory(tiger_user_id, memory_request)

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
    _, tiger_user_id = _require_user_ids(request)

    result = await memory_service.nicole_organize_topic(
        user_id=tiger_user_id,
        topic=topic,
        create_kb=create_kb,
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
    _, tiger_user_id = _require_user_ids(request)

    stats = await memory_service.get_memory_stats(tiger_user_id)

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
    _, tiger_user_id = _require_user_ids(request)

    success = await memory_service.learn_from_correction(
        user_id=tiger_user_id,
        original_content=original,
        corrected_content=corrected,
        context=context,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to record correction")

    return {"status": "learned", "original": original[:50], "corrected": corrected[:50]}

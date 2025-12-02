"""
Nicole V7 Memory Service - Tiger Postgres Native

Production-grade memory management with:
- Hybrid search (vector + keyword via pgvectorscale)
- Confidence decay and boosting
- Memory relationships and consolidation
- Nicole's proactive memory capabilities

All persistence uses Tiger Postgres with Redis caching.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Union

from app.database import db
from app.integrations.alphawave_openai import openai_client
from app.integrations.alphawave_claude import claude_client

logger = logging.getLogger(__name__)


# =============================================================================
# MEMORY SERVICE
# =============================================================================

class MemoryService:
    """
    Tiger-native memory service for Nicole V7.
    
    Provides:
    - CRUD operations for memories
    - Hybrid search (vector + keyword)
    - Knowledge base organization
    - Tag management
    - Memory relationships
    - Confidence/decay management
    - Nicole's proactive memory capabilities
    """
    
    def __init__(self) -> None:
        self.cache_ttl = 3600  # 1 hour
        self._embedding_dim = 1536
    
    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================
    
    def _normalize_id(self, value: Any) -> int:
        """Convert any ID format to integer for Tiger database."""
        if value is None:
            raise ValueError("Identifier is required")
        if isinstance(value, int):
            return value
        # Handle UUID strings or numeric strings
        try:
            return int(str(value).split('-')[0]) if '-' in str(value) else int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {value} to integer ID")
    
    def _safe_id(self, value: Any) -> Optional[int]:
        """Convert ID to integer, returning None if invalid."""
        if value is None:
            return None
        try:
            return self._normalize_id(value)
        except (ValueError, TypeError):
            return None
    
    def _format_memory(self, record: Any) -> Dict[str, Any]:
        """Format a database record into a standardized memory dict."""
        if not record:
            return {}
        
        data = dict(record)
        
        # Handle datetime serialization
        def serialize_dt(dt):
            if dt is None:
                return None
            if isinstance(dt, datetime):
                return dt.isoformat()
            return str(dt)
        
        return {
            "id": data.get("memory_id"),
            "memory_id": data.get("memory_id"),
            "user_id": data.get("user_id"),
            "memory_type": str(data.get("memory_type", "fact")),
            "content": data.get("content", ""),
            "context": data.get("category") or data.get("context"),
            "source_type": data.get("source_type", "chat"),
            "source_id": data.get("source_conversation_id") or data.get("source_id"),
            "confidence_score": float(data.get("confidence") or data.get("confidence_score") or 0.5),
            "importance_score": float(data.get("importance") or data.get("importance_score") or 0.5),
            "access_count": data.get("access_count", 0),
            "last_accessed": serialize_dt(data.get("last_accessed")),
            "tags": data.get("tags") or [],
            "metadata": data.get("metadata") or {},
            "created_at": serialize_dt(data.get("created_at")),
            "updated_at": serialize_dt(data.get("updated_at")),
            "archived_at": serialize_dt(data.get("archived_at")),
            # Search-specific fields (may not always be present)
            "vector_score": data.get("vector_score"),
            "keyword_score": data.get("keyword_score"),
            "composite_score": data.get("composite_score"),
        }
    
    async def _log_action(
        self,
        user_id: int,
        action_type: str,
        memory_id: Optional[int] = None,
        reason: Optional[str] = None,
        triggered_by: str = "nicole",
    ) -> None:
        """Log a memory action for audit trail."""
        try:
            await db.execute(
                """
                INSERT INTO corrections (
                    user_id,
                    memory_id,
                    old_content,
                    new_content,
                    correction_status,
                    created_at,
                    created_by
                ) VALUES ($1, $2, $3, $4, 'approved', NOW(), $5)
                """,
                user_id,
                memory_id,
                action_type,  # Using old_content to store action type
                reason or "",
                triggered_by,
            )
        except Exception as e:
            logger.debug(f"[MEMORY] Action log failed (non-critical): {e}")
    
    async def _is_duplicate(self, user_id: int, content: str) -> bool:
        """Check if an identical memory already exists."""
        content_normalized = content.strip().lower()
        
        row = await db.fetchrow(
            """
            SELECT 1 FROM memory_entries
            WHERE user_id = $1
              AND archived_at IS NULL
              AND LOWER(TRIM(content)) = $2
            LIMIT 1
            """,
            user_id,
            content_normalized,
        )
        return row is not None
    
    # =========================================================================
    # CORE MEMORY OPERATIONS
    # =========================================================================
    
    async def search_memory(
        self,
        user_id: Any,
        query: str,
        limit: int = 10,
        memory_types: Optional[List[str]] = None,
        knowledge_base_id: Optional[int] = None,
        min_confidence: float = 0.2,
        include_shared: bool = True,
        include_archived: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search memories using hybrid vector + keyword search.
        
        Args:
            user_id: User identifier (int or convertible)
            query: Search query text
            limit: Maximum results to return
            memory_types: Filter by memory types
            knowledge_base_id: Filter by knowledge base
            min_confidence: Minimum confidence threshold
            include_shared: Include shared family memories
            include_archived: Include archived memories
            
        Returns:
            List of memory dicts sorted by relevance
        """
        user_id_int = self._normalize_id(user_id)
        
        if not query or not query.strip():
            return []
        
        # Check cache first
        cache_key = f"memory:search:{user_id_int}:{hash(query) % 100000}"
        try:
            cached = await db.cache_get_json(cache_key)
            if cached:
                logger.debug(f"[MEMORY] Cache hit for search: {query[:30]}...")
                return cached[:limit]
        except Exception:
            pass  # Cache miss is fine
        
        try:
            # Generate embedding for query
            embedding = await openai_client.generate_embedding(query)
            
            # Format embedding as string for PostgreSQL vector type
            embedding_str = f'[{",".join(map(str, embedding))}]'
            
            # Call hybrid search function
            rows = await db.fetch(
                """
                SELECT * FROM search_memories_hybrid($1, $2::vector, $3, $4, $5)
                """,
                user_id_int,
                embedding_str,
                query,
                limit * 2,  # Get extra for filtering
                Decimal(str(min_confidence)),
            )
            
            memories = [self._format_memory(row) for row in rows]
            
        except Exception as e:
            logger.warning(f"[MEMORY] Hybrid search failed, falling back to basic: {e}")
            # Fallback to basic text search
            memories = await self._basic_text_search(user_id_int, query, limit * 2)
        
        # Apply filters
        if memory_types:
            memories = [m for m in memories if m.get("memory_type") in memory_types]
        
        if not include_archived:
            memories = [m for m in memories if not m.get("archived_at")]
        
        # Limit results
        memories = memories[:limit]
        
        # Cache results
        try:
            await db.cache_set_json(cache_key, memories, self.cache_ttl)
        except Exception:
            pass
        
        # Boost accessed memories in background
        for mem in memories[:5]:
            if mem.get("memory_id"):
                asyncio.create_task(self.bump_confidence(mem["memory_id"], 0.02))
        
        logger.info(f"[MEMORY] Search returned {len(memories)} results for: {query[:50]}...")
        return memories
    
    async def _basic_text_search(
        self,
        user_id: int,
        query: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fallback text search when hybrid search is unavailable."""
        rows = await db.fetch(
            """
            SELECT *
            FROM memory_entries
            WHERE user_id = $1
              AND archived_at IS NULL
              AND (
                  content ILIKE '%' || $2 || '%'
                  OR category ILIKE '%' || $2 || '%'
              )
            ORDER BY 
                confidence DESC,
                importance DESC,
                created_at DESC
            LIMIT $3
            """,
            user_id,
            query,
            limit,
        )
        return [self._format_memory(row) for row in rows]
    
    async def save_memory(
        self,
        user_id: Any,
        memory_type: str,
        content: str,
        context: Optional[str] = None,
        importance: float = 0.5,
        knowledge_base_id: Optional[Any] = None,
        source: str = "user",
        is_shared: bool = False,
        parent_memory_id: Optional[Any] = None,
        tag_ids: Optional[Sequence[Any]] = None,
        related_conversation: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Save a new memory with embedding.
        
        Args:
            user_id: User identifier
            memory_type: Type (fact, preference, pattern, relationship, goal, correction)
            content: Memory content text
            context: Additional context/category
            importance: Importance score 0-1
            knowledge_base_id: Optional KB to link to
            source: Source of memory (user, nicole, system)
            is_shared: Share with family
            parent_memory_id: Parent memory for hierarchies
            tag_ids: Tags to apply
            related_conversation: Associated conversation ID
            
        Returns:
            Created memory dict or None if duplicate
        """
        user_id_int = self._normalize_id(user_id)
        
        # Check for duplicates
        if await self._is_duplicate(user_id_int, content):
            logger.info(f"[MEMORY] Duplicate detected, skipping: {content[:50]}...")
            return None
        
        # Generate embedding
        embedding_str = None
        try:
            embedding = await openai_client.generate_embedding(content)
            # Format as string for PostgreSQL vector type
            embedding_str = f'[{",".join(map(str, embedding))}]'
        except Exception as e:
            logger.error(f"[MEMORY] Embedding generation failed: {e}")
        
        # Map memory_type to enum value
        type_mapping = {
            "fact": "identity",
            "preference": "preference", 
            "pattern": "workflow",
            "relationship": "relationship",
            "goal": "event",
            "correction": "insight",
            "document": "identity",
            "conversation": "event",
        }
        db_memory_type = type_mapping.get(memory_type, "identity")
        
        # Insert memory
        try:
            row = await db.fetchrow(
                """
                INSERT INTO memory_entries (
                    user_id,
                    content,
                    memory_type,
                    embedding,
                    category,
                    confidence,
                    importance,
                    source_conversation_id,
                    created_by,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3::memory_type_enum, $4::vector, $5, $6, $7, $8, $9, NOW(), NOW())
                RETURNING *
                """,
                user_id_int,
                content,
                db_memory_type,
                embedding_str,
                context,
                Decimal("1.0"),  # Start with full confidence
                Decimal(str(importance)),
                self._safe_id(related_conversation),
                source,
            )
            
            memory = self._format_memory(row)
            memory["memory_type"] = memory_type  # Return original type
            
            logger.info(f"[MEMORY] Saved: {memory_type} - {content[:50]}...")
            
            # Log action
            await self._log_action(user_id_int, "create", row["memory_id"], triggered_by=source)
            
            # Invalidate search cache
            try:
                await db.cache_delete(f"memory:search:{user_id_int}:*")
            except Exception:
                pass
            
            return memory
            
        except Exception as e:
            logger.error(f"[MEMORY] Save failed: {e}", exc_info=True)
            return None
    
    async def get_memory(
        self,
        memory_id: Any,
        user_id: Any,
    ) -> Optional[Dict[str, Any]]:
        """Get a single memory by ID."""
        user_id_int = self._normalize_id(user_id)
        memory_id_int = self._normalize_id(memory_id)
        
        row = await db.fetchrow(
            """
            SELECT * FROM memory_entries
            WHERE memory_id = $1 AND user_id = $2
            """,
            memory_id_int,
            user_id_int,
        )
        
        return self._format_memory(row) if row else None
    
    async def update_memory(
        self,
        memory_id: Any,
        user_id: Any,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update an existing memory."""
        user_id_int = self._normalize_id(user_id)
        memory_id_int = self._normalize_id(memory_id)
        
        # Map allowed fields to database columns
        field_mapping = {
            "content": "content",
            "context": "category",
            "confidence_score": "confidence",
            "importance_score": "importance",
            "archived_at": "archived_at",
        }
        
        update_data = {}
        for key, value in updates.items():
            if key in field_mapping:
                update_data[field_mapping[key]] = value
        
        if not update_data:
            return await self.get_memory(memory_id_int, user_id_int)
        
        # Build dynamic update query
        set_clauses = []
        values = []
        for i, (col, val) in enumerate(update_data.items(), start=1):
            set_clauses.append(f"{col} = ${i}")
            values.append(val)
        
        values.extend([memory_id_int, user_id_int])
        param_offset = len(update_data) + 1
        
        await db.execute(
            f"""
            UPDATE memory_entries
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE memory_id = ${param_offset} AND user_id = ${param_offset + 1}
            """,
            *values,
        )
        
        # Re-embed if content changed
        if "content" in update_data:
            try:
                embedding = await openai_client.generate_embedding(update_data["content"])
                # Format as string for PostgreSQL vector type
                embedding_str = f'[{",".join(map(str, embedding))}]'
                await db.execute(
                    "UPDATE memory_entries SET embedding = $1::vector WHERE memory_id = $2",
                    embedding_str,
                    memory_id_int,
                )
            except Exception as e:
                logger.warning(f"[MEMORY] Re-embedding failed: {e}")
        
        return await self.get_memory(memory_id_int, user_id_int)
    
    async def delete_memory(
        self,
        memory_id: Any,
        user_id: Any,
    ) -> bool:
        """Soft-delete (archive) a memory."""
        user_id_int = self._normalize_id(user_id)
        memory_id_int = self._normalize_id(memory_id)
        
        await db.execute(
            """
            UPDATE memory_entries
            SET archived_at = NOW(), updated_at = NOW()
            WHERE memory_id = $1 AND user_id = $2
            """,
            memory_id_int,
            user_id_int,
        )
        
        await self._log_action(user_id_int, "archive", memory_id_int, triggered_by="user")
        return True
    
    async def get_recent_memories(
        self,
        user_id: Any,
        limit: int = 20,
        memory_type: Optional[str] = None,
        knowledge_base_id: Optional[int] = None,
        since: Optional[datetime] = None,
        include_archived: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get recent memories with optional filters."""
        user_id_int = self._normalize_id(user_id)
        
        conditions = ["user_id = $1"]
        params: List[Any] = [user_id_int]
        param_idx = 2
        
        if not include_archived:
            conditions.append("archived_at IS NULL")
        
        if since:
            conditions.append(f"created_at >= ${param_idx}")
            params.append(since)
            param_idx += 1
        
        if memory_type:
            # Map to enum
            type_mapping = {
                "fact": "identity",
                "preference": "preference",
                "pattern": "workflow",
                "relationship": "relationship",
                "goal": "event",
                "correction": "insight",
            }
            db_type = type_mapping.get(memory_type, memory_type)
            conditions.append(f"memory_type = ${param_idx}::memory_type_enum")
            params.append(db_type)
            param_idx += 1
        
        params.append(limit)
        
        rows = await db.fetch(
            f"""
            SELECT * FROM memory_entries
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT ${param_idx}
            """,
            *params,
        )
        
        return [self._format_memory(row) for row in rows]
    
    # =========================================================================
    # CONFIDENCE & DECAY
    # =========================================================================
    
    async def bump_confidence(
        self,
        memory_id: Any,
        delta: float = 0.02,
    ) -> None:
        """Boost confidence when a memory is accessed."""
        memory_id_int = self._normalize_id(memory_id)
        
        try:
            await db.execute("SELECT boost_memory_access($1, $2)", memory_id_int, delta)
        except Exception:
            # Fallback if function doesn't exist
            await db.execute(
                """
                UPDATE memory_entries
                SET access_count = access_count + 1,
                    last_accessed = NOW(),
                    confidence = LEAST(1.0, confidence + $2),
                    updated_at = NOW()
                WHERE memory_id = $1 AND archived_at IS NULL
                """,
                memory_id_int,
                Decimal(str(delta)),
            )
    
    async def decay_memories(self) -> int:
        """Run memory decay (called by background job)."""
        try:
            row = await db.fetchrow("SELECT * FROM decay_unused_memories()")
            decayed = row["decayed_count"] if row else 0
            archived = row["archived_count"] if row else 0
            logger.info(f"[MEMORY] Decay job: {decayed} decayed, {archived} archived")
            return decayed + archived
        except Exception as e:
            logger.warning(f"[MEMORY] Decay function not available: {e}")
            # Fallback implementation
            result = await db.execute(
                """
                UPDATE memory_entries
                SET confidence = GREATEST(0.1, confidence - 0.05),
                    updated_at = NOW()
                WHERE archived_at IS NULL
                  AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '30 days')
                  AND confidence > 0.1
                """
            )
            return 0
    
    async def archive_low_confidence(self) -> int:
        """Archive memories below confidence threshold."""
        result = await db.fetchrow(
            """
            WITH archived AS (
                UPDATE memory_entries
                SET archived_at = NOW()
                WHERE confidence <= 0.15
                  AND importance < 0.7
                  AND archived_at IS NULL
                  AND created_at < NOW() - INTERVAL '7 days'
                RETURNING memory_id
            )
            SELECT COUNT(*) AS count FROM archived
            """
        )
        return result["count"] if result else 0
    
    # =========================================================================
    # MEMORY STATISTICS
    # =========================================================================
    
    async def get_memory_stats(self, user_id: Any) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        user_id_int = self._normalize_id(user_id)
        
        try:
            # Try the SQL function first
            result = await db.fetchval("SELECT get_memory_stats($1)", user_id_int)
            if result:
                return result
        except Exception:
            pass
        
        # Fallback to direct query
        row = await db.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE archived_at IS NULL) AS total_active,
                COUNT(*) FILTER (WHERE archived_at IS NOT NULL) AS total_archived,
                AVG(confidence) AS avg_confidence,
                AVG(importance) AS avg_importance,
                SUM(access_count) AS total_accesses,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') AS recent_count
            FROM memory_entries
            WHERE user_id = $1
            """,
            user_id_int,
        )
        
        return {
            "total_active": row["total_active"] or 0,
            "total_archived": row["total_archived"] or 0,
            "avg_confidence": float(row["avg_confidence"] or 0),
            "avg_importance": float(row["avg_importance"] or 0),
            "total_accesses": row["total_accesses"] or 0,
            "recent_count": row["recent_count"] or 0,
        }
    
    # =========================================================================
    # KNOWLEDGE BASES (Simplified - using category field)
    # =========================================================================
    
    async def get_knowledge_bases(
        self,
        user_id: Any,
        include_shared: bool = True,
        kb_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get distinct categories as knowledge bases."""
        user_id_int = self._normalize_id(user_id)
        
        rows = await db.fetch(
            """
            SELECT 
                category AS name,
                category AS id,
                COUNT(*) AS memory_count,
                MAX(created_at) AS last_memory_at
            FROM memory_entries
            WHERE user_id = $1 
              AND archived_at IS NULL
              AND category IS NOT NULL
            GROUP BY category
            ORDER BY memory_count DESC
            """,
            user_id_int,
        )
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "memory_count": row["memory_count"],
                "last_memory_at": row["last_memory_at"].isoformat() if row["last_memory_at"] else None,
            }
            for row in rows
        ]
    
    async def get_knowledge_base_tree(self, user_id: Any) -> Dict[str, Any]:
        """Get knowledge bases as a tree structure."""
        kbs = await self.get_knowledge_bases(user_id)
        return {"items": kbs}
    
    async def create_knowledge_base(
        self,
        user_id: Any,
        kb_data: Any,
    ) -> Optional[Dict[str, Any]]:
        """Create a knowledge base (category)."""
        name = getattr(kb_data, "name", None) or kb_data.get("name")
        description = getattr(kb_data, "description", None) or kb_data.get("description")
        
        # Knowledge bases are implemented as categories in this schema
        return {
            "id": name,
            "name": name,
            "description": description,
            "memory_count": 0,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    async def organize_memories_into_kb(
        self,
        user_id: Any,
        memory_ids: Sequence[Any],
        knowledge_base_id: Any,
        organized_by: str = "user",
    ) -> int:
        """Organize memories into a knowledge base (set category)."""
        user_id_int = self._normalize_id(user_id)
        category_name = str(knowledge_base_id)
        
        count = 0
        for mid in memory_ids:
            try:
                memory_id_int = self._normalize_id(mid)
                await db.execute(
                    """
                    UPDATE memory_entries
                    SET category = $1, updated_at = NOW()
                    WHERE memory_id = $2 AND user_id = $3
                    """,
                    category_name,
                    memory_id_int,
                    user_id_int,
                )
                count += 1
            except Exception as e:
                logger.warning(f"[MEMORY] Failed to organize memory {mid}: {e}")
        
        return count
    
    # =========================================================================
    # TAGS - Full database implementation
    # =========================================================================
    
    async def get_tags(
        self,
        user_id: Any,
        include_system: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get available tags for a user.
        
        Returns system tags (available to all) plus user's custom tags.
        """
        user_id_int = self._normalize_id(user_id)
        
        try:
            if include_system:
                rows = await db.fetch(
                    """
                    SELECT tag_id, name, description, color, icon, tag_type, usage_count
                    FROM memory_tags
                    WHERE user_id IS NULL OR user_id = $1
                    ORDER BY tag_type, usage_count DESC
                    """,
                    user_id_int
                )
            else:
                rows = await db.fetch(
                    """
                    SELECT tag_id, name, description, color, icon, tag_type, usage_count
                    FROM memory_tags
                    WHERE user_id = $1
                    ORDER BY usage_count DESC
                    """,
                    user_id_int
                )
            
            return [
                {
                    "id": row["tag_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "color": row["color"],
                    "icon": row["icon"],
                    "tag_type": str(row["tag_type"]) if row["tag_type"] else "custom",
                    "usage_count": row["usage_count"],
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"[MEMORY] Failed to get tags: {e}")
            # Fallback to hardcoded tags if table doesn't exist
            return [
                {"id": 1, "name": "important", "color": "#EF4444", "tag_type": "system"},
                {"id": 2, "name": "personal", "color": "#8B5CF6", "tag_type": "system"},
                {"id": 3, "name": "family", "color": "#EC4899", "tag_type": "system"},
                {"id": 4, "name": "work", "color": "#3B82F6", "tag_type": "system"},
                {"id": 5, "name": "health", "color": "#22C55E", "tag_type": "system"},
                {"id": 6, "name": "financial", "color": "#84CC16", "tag_type": "system"},
                {"id": 7, "name": "goal", "color": "#FBBF24", "tag_type": "system"},
            ]
    
    async def create_tag(
        self,
        user_id: Any,
        tag_data: Any,
    ) -> Optional[Dict[str, Any]]:
        """Create a custom tag for a user."""
        user_id_int = self._normalize_id(user_id)
        name = getattr(tag_data, "name", None) or tag_data.get("name")
        color = getattr(tag_data, "color", None) or tag_data.get("color", "#6366f1")
        description = getattr(tag_data, "description", None) or tag_data.get("description")
        icon = getattr(tag_data, "icon", None) or tag_data.get("icon")
        
        try:
            row = await db.fetchrow(
                """
                INSERT INTO memory_tags (user_id, name, description, color, icon, tag_type)
                VALUES ($1, $2, $3, $4, $5, 'custom')
                ON CONFLICT (user_id, name) DO UPDATE SET color = $4, description = $3
                RETURNING tag_id, name, description, color, icon, tag_type, created_at
                """,
                user_id_int,
                name,
                description,
                color,
                icon,
            )
            
            if row:
                return {
                    "id": row["tag_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "color": row["color"],
                    "icon": row["icon"],
                    "tag_type": "custom",
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
            return None
        except Exception as e:
            logger.warning(f"[MEMORY] Failed to create tag: {e}")
            return None
    
    async def tag_memory(
        self,
        memory_id: Any,
        tag_ids: Sequence[Any],
        assigned_by: str = "user",
    ) -> int:
        """Assign tags to a memory."""
        memory_id_int = self._normalize_id(memory_id)
        count = 0
        
        for tag_id in tag_ids:
            try:
                tag_id_int = self._normalize_id(tag_id)
                await db.execute(
                    """
                    INSERT INTO memory_tag_links (memory_id, tag_id, assigned_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (memory_id, tag_id) DO NOTHING
                    """,
                    memory_id_int,
                    tag_id_int,
                    assigned_by,
                )
                count += 1
            except Exception as e:
                logger.debug(f"[MEMORY] Failed to assign tag {tag_id}: {e}")
        
        return count
    
    async def untag_memory(
        self,
        memory_id: Any,
        tag_id: Any,
    ) -> bool:
        """Remove a tag from a memory."""
        memory_id_int = self._normalize_id(memory_id)
        tag_id_int = self._normalize_id(tag_id)
        
        try:
            await db.execute(
                "DELETE FROM memory_tag_links WHERE memory_id = $1 AND tag_id = $2",
                memory_id_int,
                tag_id_int,
            )
            return True
        except Exception as e:
            logger.warning(f"[MEMORY] Failed to remove tag: {e}")
            return False
    
    async def get_memory_tags(self, memory_id: Any) -> List[Dict[str, Any]]:
        """Get all tags assigned to a memory."""
        memory_id_int = self._normalize_id(memory_id)
        
        try:
            rows = await db.fetch(
                """
                SELECT t.tag_id, t.name, t.color, t.icon, mtl.assigned_by, mtl.confidence
                FROM memory_tag_links mtl
                JOIN memory_tags t ON t.tag_id = mtl.tag_id
                WHERE mtl.memory_id = $1
                ORDER BY mtl.assigned_at DESC
                """,
                memory_id_int
            )
            return [
                {
                    "id": row["tag_id"],
                    "name": row["name"],
                    "color": row["color"],
                    "icon": row["icon"],
                    "assigned_by": row["assigned_by"],
                    "confidence": float(row["confidence"]) if row["confidence"] else 1.0,
                }
                for row in rows
            ]
        except Exception as e:
            logger.debug(f"[MEMORY] Failed to get memory tags: {e}")
            return []
    
    # =========================================================================
    # MEMORY RELATIONSHIPS
    # =========================================================================
    
    async def link_memories(
        self,
        user_id: Any,
        source_memory_id: Any,
        target_memory_id: Any,
        relationship_type: str = "related_to",
        strength: float = 0.5,
        created_by: str = "nicole",
        reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a relationship between two memories.
        
        Args:
            user_id: User ID (for validation)
            source_memory_id: Source memory ID
            target_memory_id: Target memory ID
            relationship_type: Type of relationship (related_to, contradicts, elaborates, etc.)
            strength: Relationship strength 0-1
            created_by: Who created this (user, nicole, system)
            reasoning: Optional explanation for the relationship
            
        Returns:
            Created relationship dict
        """
        source_id = self._normalize_id(source_memory_id)
        target_id = self._normalize_id(target_memory_id)
        
        # Map common variations to enum values
        type_mapping = {
            "related": "related_to",
            "related_to": "related_to",
            "contradicts": "contradicts",
            "elaborates": "elaborates",
            "supersedes": "supersedes",
            "derived_from": "derived_from",
            "references": "references",
            "same_topic": "same_topic",
            "same_entity": "same_entity",
            "temporal_sequence": "temporal_sequence",
        }
        db_rel_type = type_mapping.get(relationship_type, "related_to")
        
        try:
            row = await db.fetchrow(
                """
                INSERT INTO memory_links (
                    source_memory_id,
                    target_memory_id,
                    relationship_type,
                    weight,
                    created_by,
                    reasoning,
                    created_at
                ) VALUES ($1, $2, $3::relationship_type_enum, $4, $5, $6, NOW())
                ON CONFLICT (source_memory_id, target_memory_id, relationship_type) 
                DO UPDATE SET weight = $4, reasoning = $6
                RETURNING link_id, source_memory_id, target_memory_id, relationship_type, weight, created_by, reasoning
                """,
                source_id,
                target_id,
                db_rel_type,
                Decimal(str(strength)),
                created_by,
                reasoning,
            )
            
            if row:
                return {
                    "id": row["link_id"],
                    "source_memory_id": row["source_memory_id"],
                    "target_memory_id": row["target_memory_id"],
                    "relationship_type": str(row["relationship_type"]),
                    "weight": float(row["weight"]),
                    "created_by": row["created_by"],
                    "reasoning": row["reasoning"],
                }
            return {}
        except Exception as e:
            logger.warning(f"[MEMORY] Link creation failed: {e}")
            return {}
    
    async def get_related_memories(
        self,
        memory_id: Any,
        relationship_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get memories related to a given memory."""
        memory_id_int = self._normalize_id(memory_id)
        
        conditions = ["ml.source_memory_id = $1"]
        params: List[Any] = [memory_id_int]
        
        if relationship_types:
            conditions.append("ml.relationship_type = ANY($2::text[])")
            params.append(relationship_types)
        
        rows = await db.fetch(
            f"""
            SELECT 
                ml.*,
                m.content AS related_content,
                m.memory_type AS related_type
            FROM memory_links ml
            JOIN memory_entries m ON m.memory_id = ml.target_memory_id
            WHERE {' AND '.join(conditions)}
            ORDER BY ml.weight DESC, ml.created_at DESC
            LIMIT {limit}
            """,
            *params,
        )
        
        return [dict(row) for row in rows]
    
    # =========================================================================
    # CONSOLIDATION
    # =========================================================================
    
    async def consolidate_memories(
        self,
        user_id: Any,
        consolidation_data: Any,
    ) -> Dict[str, Any]:
        """Consolidate multiple memories into one using AI."""
        user_id_int = self._normalize_id(user_id)
        source_ids = [self._normalize_id(mid) for mid in consolidation_data.source_memory_ids]
        
        # Fetch source memories
        memories = []
        for mid in source_ids:
            mem = await self.get_memory(mid, user_id_int)
            if mem:
                memories.append(mem)
        
        if len(memories) < 2:
            raise ValueError("Need at least two memories to consolidate")
        
        # Generate consolidated content with Claude
        prompt = "Merge the following memories into a single, clear statement:\n\n"
        prompt += "\n".join(f"- {m['content']}" for m in memories)
        prompt += "\n\nMerged memory:"
        
        merged_content = await claude_client.generate_response(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You combine redundant memories into one concise memory.",
        )
        
        # Create new consolidated memory
        new_memory = await self.save_memory(
            user_id=user_id_int,
            memory_type=memories[0]["memory_type"],
            content=merged_content.strip(),
            context=f"Consolidated from {len(memories)} memories",
            importance=max(m["importance_score"] for m in memories),
            source="nicole",
        )
        
        # Archive source memories
        for mid in source_ids:
            await self.delete_memory(mid, user_id_int)
        
        return new_memory or {}
    
    # =========================================================================
    # NICOLE'S PROACTIVE CAPABILITIES
    # =========================================================================
    
    async def nicole_create_memory(
        self,
        user_id: Any,
        payload: Any,
    ) -> Optional[Dict[str, Any]]:
        """Nicole proactively creates a memory."""
        return await self.save_memory(
            user_id=user_id,
            memory_type=payload.memory_type,
            content=payload.content,
            context=payload.context,
            importance=float(payload.importance_score or 0.6),
            knowledge_base_id=getattr(payload, "knowledge_base_id", None),
            source="nicole",
        )
    
    async def nicole_organize_topic(
        self,
        user_id: Any,
        topic: str,
        create_kb: bool = True,
    ) -> Dict[str, Any]:
        """Nicole organizes memories about a topic."""
        matches = await self.search_memory(user_id, topic, limit=25, min_confidence=0.2)
        
        if not matches:
            return {"organized": 0, "kb_created": False}
        
        # Set category for matching memories
        count = await self.organize_memories_into_kb(
            user_id,
            [m["memory_id"] for m in matches],
            topic.title(),
            organized_by="nicole",
        )
        
        return {
            "organized": count,
            "kb_created": create_kb,
            "kb_id": topic.title(),
        }
    
    # =========================================================================
    # LEARNING FROM CORRECTIONS
    # =========================================================================
    
    async def learn_from_correction(
        self,
        user_id: Any,
        original_content: str,
        corrected_content: str,
        context: Optional[str] = None,
    ) -> bool:
        """Record a correction for learning."""
        user_id_int = self._normalize_id(user_id)
        
        # Save as correction memory
        await self.save_memory(
            user_id=user_id_int,
            memory_type="correction",
            content=f"Correction: {corrected_content}",
            context=context or f"Original: {original_content}",
            importance=0.9,
            source="user",
        )
        
        # Also record in corrections table
        await db.execute(
            """
            INSERT INTO corrections (
                user_id,
                old_content,
                new_content,
                correction_status,
                created_at,
                created_by
            ) VALUES ($1, $2, $3, 'approved', NOW(), 'user')
            """,
            user_id_int,
            original_content,
            corrected_content,
        )
        
        return True


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

memory_service = MemoryService()

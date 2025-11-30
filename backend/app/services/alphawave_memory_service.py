"""
Enhanced Memory Service for Nicole V7.

Implements the complete 3-tier memory system with:
- Hybrid search (Redis → PostgreSQL → Qdrant)
- Knowledge base organization
- Tag management
- Memory relationships
- Memory consolidation
- Nicole's proactive memory management
- Memory decay and archival

Author: Nicole V7 Memory System
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from uuid import UUID, uuid4
from decimal import Decimal

from app.database import get_redis, get_qdrant, get_supabase
from app.integrations.alphawave_openai import openai_client
from app.integrations.alphawave_claude import claude_client

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Complete 3-tier memory system implementation for Nicole V7.

    Architecture:
    - Tier 1: Redis hot cache (recent, frequently accessed)
    - Tier 2: PostgreSQL structured (facts, preferences, patterns)
    - Tier 3: Qdrant vector search (semantic similarity)

    Features:
    - Automatic learning from corrections
    - Memory decay for unused information
    - Confidence-based ranking
    - Knowledge base organization
    - Tag-based categorization
    - Memory relationships and consolidation
    - Nicole's proactive memory management
    """

    QDRANT_COLLECTION = "nicole_memories"

    def __init__(self):
        self.redis_ttl = 3600  # 1 hour cache
        self.memory_decay_rate = 0.03  # 3% decay per week
        self._collection_initialized = False

    # ═══════════════════════════════════════════════════════════════════════════
    # CORE MEMORY OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def search_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        memory_types: Optional[List[str]] = None,
        knowledge_base_id: Optional[str] = None,
        min_confidence: float = 0.1,
        include_shared: bool = True,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search across all memory tiers with intelligent re-ranking.

        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results to return
            memory_types: Filter by memory types
            knowledge_base_id: Filter by knowledge base
            min_confidence: Minimum confidence threshold
            include_shared: Include shared family memories
            include_archived: Include archived memories

        Returns:
            Ranked list of relevant memories with scores
        """
        user_id_str = str(user_id) if user_id else None
        if not user_id_str:
            logger.warning("[MEMORY] Cannot search: user_id is None")
            return []

        logger.info(f"[MEMORY] Searching for user {user_id_str[:8]}...: '{query[:50]}...'")

        # Check Redis hot cache first
        cache_key = f"memory:{user_id_str}:{hash(query) % 10000}"
        redis_client = get_redis()

        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    cached_results = json.loads(cached)
                    filtered = self._filter_results(
                        cached_results, memory_types, min_confidence,
                        knowledge_base_id, include_archived
                    )
                    if filtered:
                        logger.info(f"[MEMORY] Cache hit: {len(filtered)} results")
                        return filtered[:limit]
            except Exception as e:
                logger.debug(f"[MEMORY] Cache check failed: {e}")

        # Perform hybrid search
        vector_results = await self._vector_search(user_id_str, query, limit * 2)
        structured_results = await self._structured_search(
            user_id_str, query, limit * 2, memory_types,
            knowledge_base_id, include_shared, include_archived
        )

        logger.info(f"[MEMORY] Results: {len(vector_results)} vector, {len(structured_results)} structured")

        # Combine and re-rank
        combined = self._rerank_results(vector_results, structured_results, query)

        # Apply filters
        filtered = self._filter_results(
            combined, memory_types, min_confidence,
            knowledge_base_id, include_archived
        )

        # Cache results
        if redis_client and filtered:
            try:
                redis_client.setex(cache_key, self.redis_ttl, json.dumps(filtered))
            except Exception as e:
                logger.debug(f"[MEMORY] Cache save failed: {e}")

        # Bump confidence for returned memories
        for mem in filtered[:limit]:
            asyncio.create_task(self.bump_confidence(mem["id"], 0.02))

        return filtered[:limit]

    async def save_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str,
        context: Optional[str] = None,
        importance: float = 0.5,
        knowledge_base_id: Optional[str] = None,
        source: str = "user",
        is_shared: bool = False,
        parent_memory_id: Optional[str] = None,
        tag_ids: Optional[List[str]] = None,
        related_conversation: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save new memory entry to all tiers.

        Args:
            user_id: User identifier
            memory_type: Type of memory
            content: Memory content
            context: Additional context
            importance: Importance score (0-1)
            knowledge_base_id: Optional knowledge base to organize under
            source: Who/what created this memory
            is_shared: Whether to share with family
            parent_memory_id: Parent memory for corrections/elaborations
            tag_ids: Tags to apply
            related_conversation: Related conversation ID

        Returns:
            Created memory entry or None
        """
        user_id_str = str(user_id) if user_id else None
        if not user_id_str:
            logger.error("[MEMORY] Cannot save: user_id is None")
            return None

        logger.info(f"[MEMORY] Saving for {user_id_str[:8]}...: type={memory_type}")

        try:
            supabase = get_supabase()
            if not supabase:
                logger.error("[MEMORY] Supabase unavailable")
                return None

            # Check for duplicates
            if await self._is_duplicate(user_id_str, content):
                logger.info("[MEMORY] Duplicate detected, skipping")
                return None

            # Generate embedding
            embedding = None
            try:
                embedding = await openai_client.generate_embedding(content)
            except Exception as e:
                logger.warning(f"[MEMORY] Embedding failed: {e}")

            # Build memory data
            memory_id = str(uuid4())
            context_full = context or ""
            if related_conversation:
                context_full += f" (conversation: {related_conversation})"

            memory_data = {
                "id": memory_id,
                "user_id": user_id_str,
                "memory_type": memory_type,
                "content": content,
                "context": context_full.strip() or None,
                "importance_score": min(max(importance, 0.0), 1.0),
                "confidence_score": 1.0,
                "access_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "source": source,
                "is_shared": is_shared,
                "embedding_status": "pending" if embedding else "skipped"
            }

            # Add optional fields
            if knowledge_base_id:
                memory_data["knowledge_base_id"] = knowledge_base_id
            if parent_memory_id:
                memory_data["parent_memory_id"] = parent_memory_id

            # Save to PostgreSQL
            result = supabase.table("memory_entries").insert(memory_data).execute()

            if not result.data:
                logger.error("[MEMORY] PostgreSQL insert failed")
                return None

            memory_id = result.data[0]["id"]
            logger.info(f"[MEMORY] ✅ Saved to PostgreSQL: {memory_id}")

            # Save to Qdrant if we have embedding
            if embedding:
                await self._save_to_qdrant(memory_id, user_id_str, content, memory_type, embedding)
                # Update embedding status
                supabase.table("memory_entries").update(
                    {"embedding_status": "completed"}
                ).eq("id", memory_id).execute()

            # Apply tags if provided
            if tag_ids:
                await self._apply_tags(memory_id, tag_ids, "system")

            # Update hot cache
            await self._update_hot_cache(user_id_str, result.data[0])

            # Log Nicole action if source is nicole
            if source == "nicole":
                await self._log_nicole_action(
                    "create_memory", "memory", memory_id,
                    user_id_str, "Proactive memory creation"
                )

            return result.data[0]

        except Exception as e:
            logger.error(f"[MEMORY] Save error: {e}", exc_info=True)
            return None

    async def get_memory(self, memory_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single memory by ID."""
        try:
            supabase = get_supabase()
            if not supabase:
                return None

            result = supabase.table("memory_entries").select(
                "*, knowledge_bases(name)"
            ).eq("id", memory_id).eq("user_id", str(user_id)).execute()

            if result.data:
                memory = result.data[0]
                # Get tags
                tags_result = supabase.table("memory_tag_assignments").select(
                    "memory_tags(name)"
                ).eq("memory_id", memory_id).execute()
                memory["tags"] = [t["memory_tags"]["name"] for t in tags_result.data or []]
                return memory

            return None
        except Exception as e:
            logger.error(f"[MEMORY] Get error: {e}")
            return None

    async def update_memory(
        self,
        memory_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing memory."""
        try:
            supabase = get_supabase()
            if not supabase:
                return None

            # Verify ownership
            existing = await self.get_memory(memory_id, user_id)
            if not existing:
                logger.warning(f"[MEMORY] Memory not found: {memory_id}")
                return None

            # Apply updates
            allowed_fields = {
                "content", "context", "confidence_score", "importance_score",
                "knowledge_base_id", "is_shared", "archived_at"
            }
            update_data = {k: v for k, v in updates.items() if k in allowed_fields}

            if not update_data:
                return existing

            result = supabase.table("memory_entries").update(
                update_data
            ).eq("id", memory_id).execute()

            # Re-embed if content changed
            if "content" in update_data:
                try:
                    embedding = await openai_client.generate_embedding(update_data["content"])
                    await self._save_to_qdrant(
                        memory_id, user_id, update_data["content"],
                        existing["memory_type"], embedding
                    )
                except Exception as e:
                    logger.warning(f"[MEMORY] Re-embedding failed: {e}")

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"[MEMORY] Update error: {e}")
            return None

    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Delete a memory (soft delete by archiving)."""
        try:
            supabase = get_supabase()
            if not supabase:
                return False

            result = supabase.table("memory_entries").update({
                "archived_at": datetime.utcnow().isoformat()
            }).eq("id", memory_id).eq("user_id", str(user_id)).execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"[MEMORY] Delete error: {e}")
            return False

    async def get_recent_memories(
        self,
        user_id: str,
        limit: int = 20,
        memory_type: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get recent memories for context."""
        try:
            supabase = get_supabase()
            if not supabase:
                return []

            query = (
                supabase.table("memory_entries")
                .select("*")
                .eq("user_id", str(user_id))
                .is_("archived_at", "null")
                .order("created_at", desc=True)
                .limit(limit)
            )

            if memory_type:
                query = query.eq("memory_type", memory_type)
            if knowledge_base_id:
                query = query.eq("knowledge_base_id", knowledge_base_id)
            if since:
                query = query.gte("created_at", since.isoformat())

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"[MEMORY] Get recent error: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════
    # KNOWLEDGE BASE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_knowledge_base(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        kb_type: str = "topic",
        parent_id: Optional[str] = None,
        icon: str = "📁",
        color: str = "#B8A8D4",
        is_shared: bool = False,
        created_by: str = "user"
    ) -> Optional[Dict[str, Any]]:
        """Create a new knowledge base for organizing memories."""
        try:
            supabase = get_supabase()
            if not supabase:
                return None

            kb_data = {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "name": name,
                "description": description,
                "kb_type": kb_type,
                "parent_id": parent_id,
                "icon": icon,
                "color": color,
                "is_shared": is_shared,
                "memory_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("knowledge_bases").insert(kb_data).execute()

            if result.data:
                logger.info(f"[MEMORY] Created KB: {name} ({kb_type})")

                # Log if Nicole created it
                if created_by == "nicole":
                    await self._log_nicole_action(
                        "create_knowledge_base", "knowledge_base",
                        result.data[0]["id"], user_id,
                        f"Created knowledge base: {name}"
                    )

                return result.data[0]

            return None

        except Exception as e:
            logger.error(f"[MEMORY] Create KB error: {e}")
            return None

    async def get_knowledge_bases(
        self,
        user_id: str,
        include_shared: bool = True,
        kb_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all knowledge bases for a user."""
        try:
            supabase = get_supabase()
            if not supabase:
                return []

            query = (
                supabase.table("knowledge_bases")
                .select("*")
                .is_("archived_at", "null")
                .order("name")
            )

            if include_shared:
                # Include user's own and shared KBs
                query = query.or_(f"user_id.eq.{user_id},shared_with.cs.{{{user_id}}}")
            else:
                query = query.eq("user_id", str(user_id))

            if kb_type:
                query = query.eq("kb_type", kb_type)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"[MEMORY] Get KBs error: {e}")
            return []

    async def get_knowledge_base_tree(self, user_id: str) -> Dict[str, Any]:
        """Get hierarchical tree of knowledge bases."""
        kbs = await self.get_knowledge_bases(user_id)

        # Build tree structure
        kb_map = {kb["id"]: {**kb, "children": []} for kb in kbs}
        roots = []

        for kb in kbs:
            if kb["parent_id"] and kb["parent_id"] in kb_map:
                kb_map[kb["parent_id"]]["children"].append(kb_map[kb["id"]])
            else:
                roots.append(kb_map[kb["id"]])

        total_memories = sum(kb["memory_count"] for kb in kbs)

        return {
            "roots": roots,
            "total_count": len(kbs),
            "total_memories": total_memories
        }

    async def organize_memories_into_kb(
        self,
        user_id: str,
        memory_ids: List[str],
        knowledge_base_id: str,
        organized_by: str = "user"
    ) -> int:
        """Move memories into a knowledge base."""
        try:
            supabase = get_supabase()
            if not supabase:
                return 0

            result = supabase.table("memory_entries").update({
                "knowledge_base_id": knowledge_base_id
            }).in_("id", memory_ids).eq("user_id", str(user_id)).execute()

            organized_count = len(result.data or [])

            if organized_by == "nicole" and organized_count > 0:
                await self._log_nicole_action(
                    "organize_memories", "knowledge_base",
                    knowledge_base_id, user_id,
                    f"Organized {organized_count} memories"
                )

            return organized_count

        except Exception as e:
            logger.error(f"[MEMORY] Organize error: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════════════════
    # TAG OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_tags(
        self,
        user_id: Optional[str] = None,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """Get available tags."""
        try:
            supabase = get_supabase()
            if not supabase:
                return []

            query = supabase.table("memory_tags").select("*").order("usage_count", desc=True)

            if user_id and include_system:
                query = query.or_(f"user_id.is.null,user_id.eq.{user_id}")
            elif user_id:
                query = query.eq("user_id", user_id)
            else:
                query = query.is_("user_id", "null")

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"[MEMORY] Get tags error: {e}")
            return []

    async def create_tag(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        color: str = "#9CA3AF",
        icon: Optional[str] = None,
        tag_type: str = "custom"
    ) -> Optional[Dict[str, Any]]:
        """Create a custom tag."""
        try:
            supabase = get_supabase()
            if not supabase:
                return None

            tag_data = {
                "id": str(uuid4()),
                "user_id": str(user_id) if tag_type != "system" else None,
                "name": name,
                "description": description,
                "color": color,
                "icon": icon,
                "tag_type": tag_type,
                "usage_count": 0,
                "created_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("memory_tags").insert(tag_data).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"[MEMORY] Create tag error: {e}")
            return None

    async def tag_memory(
        self,
        memory_id: str,
        tag_ids: List[str],
        assigned_by: str = "user"
    ) -> int:
        """Assign tags to a memory."""
        return await self._apply_tags(memory_id, tag_ids, assigned_by)

    async def untag_memory(self, memory_id: str, tag_id: str) -> bool:
        """Remove a tag from a memory."""
        try:
            supabase = get_supabase()
            if not supabase:
                return False

            supabase.table("memory_tag_assignments").delete().eq(
                "memory_id", memory_id
            ).eq("tag_id", tag_id).execute()

            return True
        except Exception as e:
            logger.error(f"[MEMORY] Untag error: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    async def link_memories(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str = "related_to",
        strength: float = 0.5,
        created_by: str = "nicole"
    ) -> Optional[Dict[str, Any]]:
        """Create a relationship between two memories."""
        try:
            supabase = get_supabase()
            if not supabase:
                return None

            rel_data = {
                "id": str(uuid4()),
                "source_memory_id": source_id,
                "target_memory_id": target_id,
                "relationship_type": relationship_type,
                "strength": strength,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("memory_relationships").insert(rel_data).execute()

            if result.data and created_by == "nicole":
                await self._log_nicole_action(
                    "link_memories", "relationship",
                    result.data[0]["id"], None,
                    f"Linked memories: {relationship_type}"
                )

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"[MEMORY] Link error: {e}")
            return None

    async def get_related_memories(
        self,
        memory_id: str,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get memories related to a given memory."""
        try:
            supabase = get_supabase()
            if not supabase:
                return []

            # Get relationships where this memory is source or target
            query = supabase.table("memory_relationships").select(
                "*, source:memory_entries!source_memory_id(*), target:memory_entries!target_memory_id(*)"
            ).or_(f"source_memory_id.eq.{memory_id},target_memory_id.eq.{memory_id}")

            if relationship_types:
                query = query.in_("relationship_type", relationship_types)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"[MEMORY] Get related error: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY CONSOLIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    async def consolidate_memories(
        self,
        user_id: str,
        memory_ids: List[str],
        consolidation_type: str = "merge",
        keep_originals: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Consolidate multiple memories into one.
        
        Uses Claude to intelligently merge/summarize the memories.
        """
        try:
            supabase = get_supabase()
            if not supabase:
                return None

            # Get the memories to consolidate
            memories = []
            for mid in memory_ids:
                mem = await self.get_memory(mid, user_id)
                if mem:
                    memories.append(mem)

            if len(memories) < 2:
                logger.warning("[MEMORY] Need at least 2 memories to consolidate")
                return None

            # Use Claude to generate consolidated content
            contents = [f"- {m['content']}" for m in memories]
            prompt = f"""Consolidate these related memories into a single, coherent memory entry.
Preserve all important information while removing redundancy.
Output ONLY the consolidated memory text, nothing else.

Memories to consolidate:
{chr(10).join(contents)}

Consolidated memory:"""

            consolidated_content = await claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are consolidating memories. Be concise but complete."
            )

            # Create the consolidated memory
            new_memory = await self.save_memory(
                user_id=user_id,
                memory_type=memories[0]["memory_type"],
                content=consolidated_content.strip(),
                context=f"Consolidated from {len(memories)} memories",
                importance=max(float(m["importance_score"]) for m in memories),
                source="consolidation",
                knowledge_base_id=memories[0].get("knowledge_base_id")
            )

            if not new_memory:
                return None

            # Record the consolidation
            consol_data = {
                "id": str(uuid4()),
                "consolidated_memory_id": new_memory["id"],
                "source_memory_ids": memory_ids,
                "consolidation_type": consolidation_type,
                "reason": f"Merged {len(memories)} related memories",
                "model_used": "claude-sonnet",
                "created_at": datetime.utcnow().isoformat()
            }

            supabase.table("memory_consolidations").insert(consol_data).execute()

            # Archive or delete originals
            if keep_originals:
                for mid in memory_ids:
                    await self.delete_memory(mid, user_id)
            else:
                # Hard delete
                supabase.table("memory_entries").delete().in_("id", memory_ids).execute()

            # Log Nicole action
            await self._log_nicole_action(
                "consolidate_memories", "memory",
                new_memory["id"], user_id,
                f"Consolidated {len(memories)} memories"
            )

            return new_memory

        except Exception as e:
            logger.error(f"[MEMORY] Consolidate error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════════
    # NICOLE'S PROACTIVE MEMORY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    async def nicole_create_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        reason: str,
        context: Optional[str] = None,
        importance: float = 0.7,
        knowledge_base_name: Optional[str] = None,
        tag_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Nicole proactively creates a memory without user message.
        
        This is used when Nicole wants to remember something she's
        learned or inferred, not from direct user input.
        """
        kb_id = None

        # Create or find knowledge base if specified
        if knowledge_base_name:
            kbs = await self.get_knowledge_bases(user_id)
            existing = next((kb for kb in kbs if kb["name"] == knowledge_base_name), None)

            if existing:
                kb_id = existing["id"]
            else:
                new_kb = await self.create_knowledge_base(
                    user_id, knowledge_base_name,
                    kb_type="system", created_by="nicole"
                )
                if new_kb:
                    kb_id = new_kb["id"]

        # Create the memory
        memory = await self.save_memory(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            context=context or f"Nicole's observation: {reason}",
            importance=importance,
            knowledge_base_id=kb_id,
            source="nicole",
            tag_ids=tag_ids
        )

        return memory

    async def nicole_organize_topic(
        self,
        user_id: str,
        topic: str,
        create_kb: bool = True
    ) -> Dict[str, Any]:
        """
        Nicole organizes memories about a specific topic.
        
        1. Searches for related memories
        2. Creates a knowledge base if needed
        3. Moves memories to the KB
        4. Links related memories together
        """
        # Search for topic-related memories
        related = await self.search_memory(
            user_id, topic, limit=50,
            min_confidence=0.2
        )

        if not related:
            return {"organized": 0, "kb_created": False}

        kb_id = None
        kb_created = False

        # Create KB if requested
        if create_kb:
            kb = await self.create_knowledge_base(
                user_id, f"📚 {topic.title()}",
                description=f"Memories related to {topic}",
                kb_type="topic", created_by="nicole"
            )
            if kb:
                kb_id = kb["id"]
                kb_created = True

        # Move memories to KB
        organized = 0
        if kb_id:
            memory_ids = [m["id"] for m in related]
            organized = await self.organize_memories_into_kb(
                user_id, memory_ids, kb_id, "nicole"
            )

        # Link highly related memories
        if len(related) > 1:
            for i, mem1 in enumerate(related[:10]):  # Limit to avoid too many links
                for mem2 in related[i+1:10]:
                    if mem1["score"] > 0.5 and mem2["score"] > 0.5:
                        await self.link_memories(
                            mem1["id"], mem2["id"],
                            "same_topic", 0.7, "nicole"
                        )

        return {
            "organized": organized,
            "kb_created": kb_created,
            "kb_id": kb_id,
            "topic": topic
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIDENCE AND DECAY
    # ═══════════════════════════════════════════════════════════════════════════

    async def bump_confidence(self, memory_id: str, boost: float = 0.1) -> bool:
        """Increase confidence for accessed memories."""
        try:
            supabase = get_supabase()
            if not supabase:
                return False

            result = supabase.table("memory_entries").select(
                "confidence_score, access_count"
            ).eq("id", memory_id).execute()

            if not result.data:
                return False

            current = result.data[0]
            new_confidence = min(float(current["confidence_score"]) + boost, 1.0)

            supabase.table("memory_entries").update({
                "confidence_score": new_confidence,
                "access_count": current["access_count"] + 1,
                "last_accessed": datetime.utcnow().isoformat()
            }).eq("id", memory_id).execute()

            return True

        except Exception as e:
            logger.error(f"[MEMORY] Bump confidence error: {e}")
            return False

    async def decay_memories(self) -> Dict[str, int]:
        """Apply weekly decay to unused memories."""
        try:
            supabase = get_supabase()
            if not supabase:
                return {"error": "Database unavailable"}

            cutoff = datetime.utcnow() - timedelta(days=7)

            result = supabase.table("memory_entries").select("*").lt(
                "last_accessed", cutoff.isoformat()
            ).is_("archived_at", "null").execute()

            if not result.data:
                return {"decayed": 0, "archived": 0}

            decayed = 0
            archived = 0

            for memory in result.data:
                current_conf = float(memory["confidence_score"])
                new_conf = current_conf * (1 - self.memory_decay_rate)

                if new_conf < 0.1:
                    # Archive
                    supabase.table("memory_entries").update({
                        "confidence_score": 0.0,
                        "archived_at": datetime.utcnow().isoformat()
                    }).eq("id", memory["id"]).execute()
                    archived += 1
                else:
                    supabase.table("memory_entries").update({
                        "confidence_score": new_conf
                    }).eq("id", memory["id"]).execute()
                    decayed += 1

            logger.info(f"[MEMORY] Decay: {decayed} decayed, {archived} archived")
            return {"decayed": decayed, "archived": archived}

        except Exception as e:
            logger.error(f"[MEMORY] Decay error: {e}")
            return {"error": str(e)}

    async def archive_low_confidence(self, threshold: float = 0.1) -> Dict[str, int]:
        """Archive memories below confidence threshold."""
        try:
            supabase = get_supabase()
            if not supabase:
                return {"error": "Database unavailable"}

            result = supabase.table("memory_entries").select("id").lt(
                "confidence_score", threshold
            ).is_("archived_at", "null").execute()

            if not result.data:
                return {"archived": 0}

            for memory in result.data:
                supabase.table("memory_entries").update({
                    "archived_at": datetime.utcnow().isoformat()
                }).eq("id", memory["id"]).execute()

            return {"archived": len(result.data)}

        except Exception as e:
            logger.error(f"[MEMORY] Archive error: {e}")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        try:
            supabase = get_supabase()
            if not supabase:
                return {"error": "Database unavailable"}

            # Get all memories
            result = supabase.table("memory_entries").select("*").eq(
                "user_id", str(user_id)
            ).execute()

            memories = result.data or []
            active = [m for m in memories if not m.get("archived_at")]
            archived = [m for m in memories if m.get("archived_at")]

            # Stats by type
            by_type = defaultdict(int)
            for m in active:
                by_type[m["memory_type"]] += 1

            # Stats by knowledge base
            kbs = await self.get_knowledge_bases(user_id)
            by_kb = {kb["name"]: kb["memory_count"] for kb in kbs}

            # Averages
            avg_conf = sum(float(m["confidence_score"]) for m in active) / len(active) if active else 0
            avg_imp = sum(float(m["importance_score"]) for m in active) / len(active) if active else 0
            total_acc = sum(m["access_count"] for m in active)

            # Recent
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent = len([m for m in active if datetime.fromisoformat(
                m["created_at"].replace('Z', '+00:00')
            ).replace(tzinfo=None) > week_ago])

            # Shared
            shared = len([m for m in active if m.get("is_shared")])

            return {
                "total_memories": len(active),
                "by_type": dict(by_type),
                "by_knowledge_base": by_kb,
                "average_confidence": round(avg_conf, 3),
                "average_importance": round(avg_imp, 3),
                "total_accesses": total_acc,
                "recent_additions": recent,
                "archived_count": len(archived),
                "shared_count": shared,
                "knowledge_base_count": len(kbs),
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[MEMORY] Stats error: {e}")
            return {"error": str(e)}

    async def learn_from_correction(
        self,
        user_id: str,
        original_content: str,
        corrected_content: str,
        context: Optional[str] = None
    ) -> bool:
        """Learn from user corrections."""
        try:
            # Save correction as memory
            correction = await self.save_memory(
                user_id=user_id,
                memory_type="correction",
                content=f"Correction: {corrected_content}",
                context=context or f"Original: {original_content}",
                importance=0.9,
                source="user"
            )

            if not correction:
                return False

            # Try to find and link to the original memory
            originals = await self.search_memory(
                user_id, original_content, limit=1
            )

            if originals:
                await self.link_memories(
                    correction["id"], originals[0]["id"],
                    "contradicts", 1.0, "system"
                )

            logger.info(f"[MEMORY] Learned correction: {original_content[:30]}... -> {corrected_content[:30]}...")
            return True

        except Exception as e:
            logger.error(f"[MEMORY] Learn correction error: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    async def _is_duplicate(self, user_id: str, content: str) -> bool:
        """Check if similar memory already exists."""
        try:
            # Simple check: exact match or very similar
            supabase = get_supabase()
            if not supabase:
                return False

            result = supabase.table("memory_entries").select("id").eq(
                "user_id", user_id
            ).eq("content", content).is_("archived_at", "null").limit(1).execute()

            return bool(result.data)

        except Exception:
            return False

    async def _apply_tags(
        self,
        memory_id: str,
        tag_ids: List[str],
        assigned_by: str
    ) -> int:
        """Apply tags to a memory."""
        try:
            supabase = get_supabase()
            if not supabase:
                return 0

            applied = 0
            for tag_id in tag_ids:
                try:
                    supabase.table("memory_tag_assignments").insert({
                        "id": str(uuid4()),
                        "memory_id": memory_id,
                        "tag_id": tag_id,
                        "assigned_by": assigned_by,
                        "assigned_at": datetime.utcnow().isoformat()
                    }).execute()
                    applied += 1
                except Exception:
                    pass  # Likely duplicate

            return applied

        except Exception as e:
            logger.error(f"[MEMORY] Apply tags error: {e}")
            return 0

    async def _save_to_qdrant(
        self,
        memory_id: str,
        user_id: str,
        content: str,
        memory_type: str,
        embedding: List[float]
    ) -> bool:
        """Save memory embedding to Qdrant."""
        try:
            qdrant = get_qdrant()
            if not qdrant:
                return False

            from qdrant_client.models import PointStruct

            qdrant.upsert(
                collection_name=self.QDRANT_COLLECTION,
                points=[PointStruct(
                    id=memory_id,
                    vector=embedding,
                    payload={
                        "content": content,
                        "memory_type": memory_type,
                        "user_id": user_id,
                        "memory_id": memory_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )]
            )

            logger.debug(f"[MEMORY] Saved to Qdrant: {memory_id[:8]}...")
            return True

        except Exception as e:
            logger.error(f"[MEMORY] Qdrant save error: {e}")
            return False

    async def _vector_search(
        self,
        user_id: str,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform vector search in Qdrant."""
        try:
            qdrant = get_qdrant()
            if not qdrant:
                return []

            embedding = await openai_client.generate_embedding(query)

            from qdrant_client.models import Filter, FieldCondition, MatchValue

            results = qdrant.search(
                collection_name=self.QDRANT_COLLECTION,
                query_vector=embedding,
                query_filter=Filter(must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                ]),
                limit=limit,
                score_threshold=0.1
            )

            return [{
                "id": str(r.id),
                "content": r.payload.get("content", ""),
                "memory_type": r.payload.get("memory_type", "unknown"),
                "score": r.score,
                "source": "vector"
            } for r in results]

        except Exception as e:
            logger.error(f"[MEMORY] Vector search error: {e}")
            return []

    async def _structured_search(
        self,
        user_id: str,
        query: str,
        limit: int,
        memory_types: Optional[List[str]],
        knowledge_base_id: Optional[str],
        include_shared: bool,
        include_archived: bool
    ) -> List[Dict[str, Any]]:
        """Perform structured search in PostgreSQL."""
        try:
            supabase = get_supabase()
            if not supabase:
                logger.warning("[MEMORY] Supabase unavailable for structured search")
                return []

            logger.info(f"[MEMORY] Structured search: user={user_id[:8]}..., query='{query[:30]}...'")

            # Simpler query - just get user's memories directly
            query_builder = (
                supabase.table("memory_entries")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit * 3)  # Get more to allow filtering
            )

            if not include_archived:
                query_builder = query_builder.is_("archived_at", "null")

            if memory_types:
                query_builder = query_builder.in_("memory_type", memory_types)

            if knowledge_base_id:
                query_builder = query_builder.eq("knowledge_base_id", knowledge_base_id)

            result = query_builder.execute()
            
            all_memories = result.data or []
            logger.info(f"[MEMORY] Found {len(all_memories)} total memories for user")

            if not all_memories:
                return []

            # Keyword relevance scoring
            query_words = set(query.lower().split())
            scored = []

            for m in all_memories:
                content_lower = m["content"].lower()
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                relevance = overlap / max(len(query_words), 1)

                # Check for any keyword match (including partial)
                has_keyword_match = overlap > 0 or any(w in content_lower for w in query_words if len(w) > 2)
                
                if has_keyword_match:
                    conf = float(m.get("confidence_score", 0.5) or 0.5)
                    scored.append({
                        **m,
                        "score": conf * (0.5 + relevance * 0.5),
                        "source": "structured"
                    })
                    logger.debug(f"[MEMORY] Match: overlap={overlap}, content='{m['content'][:40]}...'")

            # If no keyword matches, return ALL memories as fallback (user has few memories)
            if not scored and len(all_memories) <= 20:
                logger.info(f"[MEMORY] No keyword matches, returning all {len(all_memories)} memories as context")
                for m in all_memories:
                    conf = float(m.get("confidence_score", 0.5) or 0.5)
                    scored.append({
                        **m,
                        "score": conf * 0.4,  # Lower score for fallback
                        "source": "structured_fallback"
                    })

            scored.sort(key=lambda x: x["score"], reverse=True)
            logger.info(f"[MEMORY] Returning {min(limit, len(scored))} scored memories")
            return scored[:limit]

        except Exception as e:
            logger.error(f"[MEMORY] Structured search error: {e}", exc_info=True)
            return []

    def _rerank_results(
        self,
        vector_results: List[Dict[str, Any]],
        structured_results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """Re-rank combined search results."""
        seen = set()
        combined = []

        for r in vector_results + structured_results:
            if r["id"] not in seen:
                seen.add(r["id"])
                combined.append(r)

        # Score: 50% similarity, 25% confidence/importance, 15% recency, 10% access
        for r in combined:
            score = 0.0

            # Similarity
            if r["source"] == "vector":
                score += r["score"] * 0.5
            else:
                score += r.get("confidence_score", 0.5) * 0.3

            # Confidence/importance
            conf = float(r.get("confidence_score", 0.5))
            imp = float(r.get("importance_score", 0.5))
            score += ((conf + imp) / 2) * 0.25

            # Recency
            if r.get("created_at"):
                try:
                    created = datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))
                    days = (datetime.utcnow() - created.replace(tzinfo=None)).days
                    score += max(0, 1 - days/30) * 0.15
                except:
                    score += 0.075

            # Access frequency
            access = r.get("access_count", 0)
            score += min(1.0, access / 10) * 0.1

            r["final_score"] = score

        combined.sort(key=lambda x: x["final_score"], reverse=True)

        for r in combined:
            r.pop("final_score", None)

        return combined

    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        memory_types: Optional[List[str]],
        min_confidence: float,
        knowledge_base_id: Optional[str],
        include_archived: bool
    ) -> List[Dict[str, Any]]:
        """Filter results by criteria."""
        filtered = []

        for r in results:
            if float(r.get("confidence_score", 0)) < min_confidence:
                continue
            if memory_types and r.get("memory_type") not in memory_types:
                continue
            if knowledge_base_id and r.get("knowledge_base_id") != knowledge_base_id:
                continue
            if not include_archived and r.get("archived_at"):
                continue
            filtered.append(r)

        return filtered

    async def _update_hot_cache(self, user_id: str, memory: Dict[str, Any]) -> None:
        """Update Redis hot cache."""
        try:
            redis = get_redis()
            if not redis:
                return

            key = f"recent_memories:{user_id}"
            redis.lpush(key, str(memory["id"]))
            redis.ltrim(key, 0, 9)
            redis.expire(key, self.redis_ttl)

        except Exception as e:
            logger.debug(f"[MEMORY] Cache update error: {e}")

    async def _log_nicole_action(
        self,
        action_type: str,
        target_type: str,
        target_id: str,
        user_id: Optional[str],
        reason: str
    ) -> None:
        """Log Nicole's memory management action."""
        try:
            supabase = get_supabase()
            if not supabase:
                return

            supabase.table("nicole_memory_actions").insert({
                "id": str(uuid4()),
                "action_type": action_type,
                "target_type": target_type,
                "target_id": target_id,
                "user_id": user_id,
                "reason": reason,
                "success": True,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        except Exception as e:
            logger.debug(f"[MEMORY] Log action error: {e}")


# Global instance
memory_service = MemoryService()

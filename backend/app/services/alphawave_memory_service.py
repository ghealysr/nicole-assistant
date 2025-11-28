import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.database import get_redis, get_qdrant, get_supabase
from app.integrations.alphawave_openai import openai_client
from app.models.alphawave_memory import AlphawaveMemoryCreate

logger = logging.getLogger(__name__)


class MemoryService:
    """
    3-tier memory system implementation for Nicole V7.

    Provides persistent memory across conversations with hybrid search:
    - Tier 1: Redis hot cache (recent, frequently accessed)
    - Tier 2: PostgreSQL structured (facts, preferences, patterns)
    - Tier 3: Qdrant vector search (semantic similarity)

    Features:
    - Automatic learning from corrections
    - Memory decay for unused information
    - Confidence-based ranking
    - Multi-modal retrieval (text, semantic, temporal)
    """

    # Global collection name for all users (filter by user_id in payload)
    QDRANT_COLLECTION = "nicole_memories"

    def __init__(self):
        self.redis_ttl = 3600  # 1 hour cache
        self.memory_decay_rate = 0.03  # 3% decay per week for unused memories
        self._collection_initialized = False

    async def search_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        memory_types: Optional[List[str]] = None,
        min_confidence: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search across all memory tiers with intelligent re-ranking.

        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results to return
            memory_types: Filter by memory types (fact, preference, etc.)
            min_confidence: Minimum confidence threshold

        Returns:
            Ranked list of relevant memories
        """
        
        # Ensure user_id is a string
        user_id_str = str(user_id) if user_id else None
        if not user_id_str:
            logger.warning("[MEMORY] Cannot search memories: user_id is None or invalid")
            return []
            
        logger.info(f"[MEMORY] Searching memories for user {user_id_str[:8]}...: query='{query[:50]}...'")

        cache_key = f"memory:{user_id_str}:{hash(query) % 10000}"
        redis_client = get_redis()

        # Check Redis hot cache first
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    cached_results = json.loads(cached)
                    # Filter by confidence and types if specified
                    filtered = self._filter_results(cached_results, memory_types, min_confidence)
                    if filtered:
                        logger.info(f"[MEMORY] Found {len(filtered)} cached results")
                        return filtered[:limit]
            except Exception as cache_err:
                logger.debug(f"[MEMORY] Cache check failed: {cache_err}")

        # Perform hybrid search
        vector_results = await self._vector_search(user_id_str, query, limit * 2)
        structured_results = await self._structured_search(user_id_str, query, limit * 2, memory_types)

        logger.info(f"[MEMORY] Search results: {len(vector_results)} vector, {len(structured_results)} structured")

        # Combine and re-rank results
        combined = self._rerank_results(vector_results, structured_results, query)

        # Apply filters
        filtered_combined = self._filter_results(combined, memory_types, min_confidence)

        logger.info(f"[MEMORY] After filtering: {len(filtered_combined)} memories")

        # Cache results (if we have any)
        if redis_client and filtered_combined:
            try:
                redis_client.setex(cache_key, self.redis_ttl, json.dumps(filtered_combined))
            except Exception as cache_err:
                logger.debug(f"[MEMORY] Cache save failed: {cache_err}")

        return filtered_combined[:limit]

    async def save_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str,
        context: Optional[str] = None,
        importance: float = 0.5,
        related_conversation: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save new memory entry to all tiers.

        Args:
            user_id: User identifier
            memory_type: Type of memory (fact, preference, pattern, etc.)
            content: Memory content
            context: Additional context
            importance: Importance score (0-1)
            related_conversation: Related conversation ID

        Returns:
            Created memory entry or None if failed
        """

        # Ensure user_id is a string
        user_id_str = str(user_id) if user_id else None
        if not user_id_str:
            logger.error("[MEMORY] Cannot save memory: user_id is None or invalid")
            return None
            
        logger.info(f"[MEMORY] Saving memory for user {user_id_str[:8]}...: type={memory_type}, content={content[:50]}...")

        try:
            supabase = get_supabase()
            if not supabase:
                logger.error(f"[MEMORY] Supabase unavailable for memory save: {user_id_str}")
                return None

            # Generate embedding for vector storage (optional - don't fail if OpenAI unavailable)
            embedding = None
            try:
                embedding = await openai_client.generate_embedding(content)
                logger.debug(f"[MEMORY] Generated embedding for memory")
            except Exception as embed_err:
                logger.warning(f"[MEMORY] Could not generate embedding (continuing without): {embed_err}")

            # Save to PostgreSQL (structured) - this is the primary storage
            # Note: related_conversations column doesn't exist in current schema,
            # so we store conversation context in the 'context' field instead
            memory_data = {
                "user_id": user_id_str,
                "memory_type": memory_type,
                "content": content,
                "context": f"{context} (conversation: {related_conversation})" if related_conversation and context else (context or f"From conversation {related_conversation}" if related_conversation else None),
                "importance_score": min(max(importance, 0.0), 1.0),
                "confidence_score": 1.0,  # New memories start with full confidence
                "access_count": 0,
                "created_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("memory_entries").insert(memory_data).execute()

            if not result.data:
                logger.error(f"[MEMORY] Failed to save memory to PostgreSQL: {user_id}")
                return None

            memory_id = result.data[0]["id"]
            logger.info(f"[MEMORY] ✅ Saved to PostgreSQL: {memory_id}")

            # Save to Qdrant (vector) - only if we have embedding
            if embedding:
                await self._queue_vector_embedding(memory_id, content, embedding)

            # Update hot cache
            await self._update_hot_cache(user_id_str, result.data[0])

            logger.info(f"[MEMORY] Memory saved successfully: {memory_id} for user {user_id_str[:8]}...")
            return result.data[0]

        except Exception as e:
            logger.error(f"[MEMORY] Error saving memory: {e}", exc_info=True)
            return None

    async def get_recent_memories(
        self,
        user_id: str,
        limit: int = 20,
        memory_type: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories for context.

        Args:
            user_id: User identifier
            limit: Maximum memories to return
            memory_type: Filter by memory type
            since: Only memories since this time

        Returns:
            Recent memory entries
        """

        try:
            supabase = get_supabase()
            if not supabase:
                return []

            query = (
                supabase.table("memory_entries")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
            )

            if memory_type:
                query = query.eq("memory_type", memory_type)

            if since:
                query = query.gte("created_at", since.isoformat())

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Error getting recent memories: {e}")
            return []

    async def bump_confidence(self, memory_id: str, confidence_boost: float = 0.1) -> bool:
        """
        Increase confidence for frequently accessed memories (use-on-touch).

        Args:
            memory_id: Memory entry identifier
            confidence_boost: Amount to increase confidence

        Returns:
            Success status
        """

        try:
            supabase = get_supabase()
            if not supabase:
                return False

            # Get current confidence
            result = supabase.table("memory_entries").select("confidence_score").eq("id", memory_id).execute()

            if not result.data:
                return False

            current_confidence = result.data[0]["confidence_score"]
            new_confidence = min(current_confidence + confidence_boost, 1.0)

            # Update confidence and access tracking
            update_data = {
                "confidence_score": new_confidence,
                "access_count": supabase.table("memory_entries").select("access_count").eq("id", memory_id).execute().data[0]["access_count"] + 1,
                "last_accessed": datetime.utcnow().isoformat()
            }

            supabase.table("memory_entries").update(update_data).eq("id", memory_id).execute()

            logger.debug(f"Memory confidence bumped: {memory_id} ({current_confidence:.2f} -> {new_confidence:.2f})")
            return True

        except Exception as e:
            logger.error(f"Error bumping memory confidence: {e}")
            return False

    async def decay_memories(self) -> Dict[str, int]:
        """
        Apply memory decay to unused memories (weekly job).

        Returns:
            Summary of decayed memories
        """

        try:
            supabase = get_supabase()
            if not supabase:
                return {"error": "Database unavailable"}

            # Find memories that haven't been accessed in 7+ days
            cutoff_date = datetime.utcnow() - timedelta(days=7)

            result = supabase.table("memory_entries").select("*").lt("last_accessed", cutoff_date.isoformat()).execute()

            if not result.data:
                return {"decayed": 0, "errors": 0}

            decayed_count = 0
            errors = 0

            for memory in result.data:
                try:
                    current_confidence = memory["confidence_score"]
                    new_confidence = current_confidence * (1 - self.memory_decay_rate)

                    # Archive if confidence drops below threshold
                    if new_confidence < 0.1:
                        supabase.table("memory_entries").update({
                            "confidence_score": 0.0,
                            "archived_at": datetime.utcnow().isoformat(),
                            "decay_applied": True
                        }).eq("id", memory["id"]).execute()
                    else:
                        supabase.table("memory_entries").update({
                            "confidence_score": new_confidence,
                            "decay_applied": True
                        }).eq("id", memory["id"]).execute()

                    decayed_count += 1

                except Exception as e:
                    logger.error(f"Error decaying memory {memory['id']}: {e}")
                    errors += 1

            logger.info(f"Memory decay completed: {decayed_count} memories decayed, {errors} errors")
            return {"decayed": decayed_count, "errors": errors}

        except Exception as e:
            logger.error(f"Error in memory decay process: {e}")
            return {"error": str(e)}

    async def archive_low_confidence(self, min_confidence: float = 0.1) -> Dict[str, int]:
        """
        Archive memories with very low confidence scores.

        Args:
            min_confidence: Confidence threshold for archiving

        Returns:
            Summary of archived memories
        """

        try:
            supabase = get_supabase()
            if not supabase:
                return {"error": "Database unavailable"}

            # Find low confidence memories
            result = supabase.table("memory_entries").select("*").lt("confidence_score", min_confidence).is_("archived_at", None).execute()

            if not result.data:
                return {"archived": 0}

            archived_count = 0

            for memory in result.data:
                try:
                    supabase.table("memory_entries").update({
                        "archived_at": datetime.utcnow().isoformat()
                    }).eq("id", memory["id"]).execute()
                    archived_count += 1

                except Exception as e:
                    logger.error(f"Error archiving memory {memory['id']}: {e}")

            logger.info(f"Memory archiving completed: {archived_count} memories archived")
            return {"archived": archived_count}

        except Exception as e:
            logger.error(f"Error in memory archiving: {e}")
            return {"error": str(e)}

    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Memory usage statistics
        """

        try:
            supabase = get_supabase()
            if not supabase:
                return {"error": "Database unavailable"}

            # Get overall statistics
            stats_result = supabase.table("memory_entries").select(
                "memory_type",
                "confidence_score",
                "importance_score",
                "access_count",
                "created_at"
            ).eq("user_id", user_id).execute()

            if not stats_result.data:
                return {
                    "total_memories": 0,
                    "by_type": {},
                    "average_confidence": 0.0,
                    "average_importance": 0.0,
                    "total_accesses": 0
                }

            # Calculate statistics
            memories = stats_result.data
            total_memories = len(memories)

            # Group by type
            by_type = defaultdict(int)
            for memory in memories:
                by_type[memory["memory_type"]] += 1

            # Calculate averages
            avg_confidence = sum(m["confidence_score"] for m in memories) / total_memories
            avg_importance = sum(m["importance_score"] for m in memories) / total_memories
            total_accesses = sum(m["access_count"] for m in memories)

            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_result = supabase.table("memory_entries").select("id").eq("user_id", user_id).gte("created_at", week_ago.isoformat()).execute()
            recent_count = len(recent_result.data or [])

            return {
                "total_memories": total_memories,
                "by_type": dict(by_type),
                "average_confidence": round(avg_confidence, 3),
                "average_importance": round(avg_importance, 3),
                "total_accesses": total_accesses,
                "recent_additions": recent_count,
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}

    async def learn_from_correction(
        self,
        user_id: str,
        original_content: str,
        corrected_content: str,
        context: Optional[str] = None
    ) -> bool:
        """
        Learn from user corrections to improve future responses.

        Args:
            user_id: User identifier
            original_content: Original incorrect information
            corrected_content: Corrected information
            context: Context where correction occurred

        Returns:
            Success status
        """

        try:
            # Save correction to database
            correction_data = {
                "user_id": user_id,
                "memory_type": "correction",
                "content": f"Correction: {corrected_content}",
                "context": context or f"Original: {original_content}",
                "importance_score": 0.9,  # High importance for corrections
                "confidence_score": 1.0,
                "created_at": datetime.utcnow().isoformat()
            }

            supabase = get_supabase()
            if not supabase:
                return False

            result = supabase.table("memory_entries").insert(correction_data).execute()

            if not result.data:
                logger.error(f"Failed to save correction for user {user_id}")
                return False

            # Generate embedding for vector search
            corrected_embedding = await openai_client.generate_embedding(corrected_content)

            # Queue for vector storage
            await self._queue_vector_embedding(result.data[0]["id"], corrected_content, corrected_embedding)

            logger.info(f"Correction learned for user {user_id}: {original_content} -> {corrected_content}")
            return True

        except Exception as e:
            logger.error(f"Error learning from correction: {e}")
            return False

    # Private helper methods

    async def _vector_search(self, user_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform vector search in Qdrant."""
        try:
            qdrant_client = get_qdrant()
            if not qdrant_client:
                logger.debug("[MEMORY] Qdrant not available, skipping vector search")
                return []

            # Generate embedding for the query
            try:
                query_embedding = await openai_client.generate_embedding(query)
            except Exception as embed_err:
                logger.warning(f"[MEMORY] Failed to generate embedding: {embed_err}")
                return []

            # Import filter for Qdrant
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Search with user_id filter
            results = qdrant_client.search(
                collection_name=self.QDRANT_COLLECTION,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=limit,
                score_threshold=0.1  # Minimum relevance threshold
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": str(result.id),
                    "content": result.payload.get("content", ""),
                    "memory_type": result.payload.get("memory_type", "unknown"),
                    "confidence_score": result.payload.get("confidence_score", 0.5),
                    "importance_score": result.payload.get("importance_score", 0.5),
                    "score": result.score,
                    "source": "vector"
                })

            logger.info(f"[MEMORY] Vector search found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"[MEMORY] Vector search failed: {e}")
            return []

    async def _structured_search(
        self,
        user_id: str,
        query: str,
        limit: int,
        memory_types: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Perform structured search in PostgreSQL."""
        try:
            supabase = get_supabase()
            if not supabase:
                logger.debug("[MEMORY] Supabase not available for structured search")
                return []

            # Ensure user_id is a string for database query
            user_id_str = str(user_id) if user_id else None
            if not user_id_str:
                logger.warning("[MEMORY] Cannot search: user_id is None")
                return []
                
            logger.info(f"[MEMORY] Structured search: user_id={user_id_str[:8]}..., query='{query[:30]}...'")
                
            # First, try to get all memories for this user (simpler approach)
            # Full-text search might not be configured in Supabase
            query_builder = (
                supabase.table("memory_entries")
                .select("*")
                .eq("user_id", user_id_str)
                .is_("archived_at", "null")  # Not archived
                .order("created_at", desc=True)
                .limit(limit * 2)  # Get more, then filter
            )

            if memory_types:
                query_builder = query_builder.in_("memory_type", memory_types)

            result = query_builder.execute()

            # Simple keyword matching as fallback (since textSearch may not work)
            query_words = set(query.lower().split())
            
            # Format and filter results
            formatted_results = []
            for memory in result.data or []:
                content_lower = memory["content"].lower()
                
                # Calculate simple relevance score based on word overlap
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                relevance = overlap / max(len(query_words), 1)
                
                # Include if any query word is in content
                if overlap > 0 or any(word in content_lower for word in query_words):
                    formatted_results.append({
                        "id": memory["id"],
                        "content": memory["content"],
                        "memory_type": memory["memory_type"],
                        "confidence_score": memory["confidence_score"],
                        "importance_score": memory["importance_score"],
                        "access_count": memory.get("access_count", 0),
                        "last_accessed": memory.get("last_accessed"),
                        "created_at": memory.get("created_at"),
                        "score": memory["confidence_score"] * (0.5 + relevance * 0.5),
                        "source": "structured"
                    })

            # Sort by score
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            
            logger.info(f"[MEMORY] Structured search found {len(formatted_results)} results from {len(result.data or [])} total memories")
            return formatted_results[:limit]

        except Exception as e:
            logger.error(f"[MEMORY] Structured search failed: {e}")
            return []

    def _rerank_results(
        self,
        vector_results: List[Dict[str, Any]],
        structured_results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Re-rank search results using multiple factors.

        Ranking algorithm (weighted scoring):
        - Semantic similarity: 50% (from vector search scores)
        - User feedback/importance: 25% (confidence + importance scores)
        - Recency: 15% (newer memories prioritized)
        - Access frequency: 10% (frequently accessed memories prioritized)
        """

        # Combine results and remove duplicates
        seen_ids = set()
        combined = []

        for result in vector_results + structured_results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                combined.append(result)

        # Calculate re-ranking scores
        for result in combined:
            score = 0.0

            # Semantic similarity (50%)
            if result["source"] == "vector":
                score += result["score"] * 0.5
            else:
                # For structured results, use confidence as semantic proxy
                score += result["confidence_score"] * 0.3

            # User feedback/importance (25%)
            importance_weight = (result["confidence_score"] + result["importance_score"]) / 2
            score += importance_weight * 0.25

            # Recency (15%)
            if result.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(result["created_at"].replace('Z', '+00:00'))
                    days_old = (datetime.utcnow() - created_at.replace(tzinfo=None)).days
                    recency_score = max(0, 1 - (days_old / 30))  # Decay over 30 days
                    score += recency_score * 0.15
                except:
                    score += 0.5 * 0.15  # Default recency score

            # Access frequency (10%)
            access_count = result.get("access_count", 0)
            access_score = min(1.0, access_count / 10)  # Cap at 10 accesses
            score += access_score * 0.1

            result["rerank_score"] = score

        # Sort by re-ranking score
        combined.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Remove temporary rerank_score field
        for result in combined:
            result.pop("rerank_score", None)

        return combined

    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        memory_types: Optional[List[str]],
        min_confidence: float
    ) -> List[Dict[str, Any]]:
        """Filter results by type and confidence."""
        filtered = []

        for result in results:
            # Check confidence threshold
            if result.get("confidence_score", 0) < min_confidence:
                continue

            # Check memory type filter
            if memory_types and result.get("memory_type") not in memory_types:
                continue

            filtered.append(result)

        return filtered

    async def _update_hot_cache(self, user_id: str, memory: Dict[str, Any]) -> None:
        """Update Redis hot cache with new memory."""
        try:
            redis_client = get_redis()
            if not redis_client:
                return

            # Add to recent memories cache
            cache_key = f"recent_memories:{user_id}"
            recent_memories = redis_client.lrange(cache_key, 0, 9)  # Last 10

            # Check if memory is already in cache
            if str(memory["id"]).encode() not in recent_memories:
                redis_client.lpush(cache_key, str(memory["id"]))
                redis_client.ltrim(cache_key, 0, 9)  # Keep only last 10
                redis_client.expire(cache_key, self.redis_ttl)

        except Exception as e:
            logger.warning(f"Failed to update hot cache: {e}")

    async def _queue_vector_embedding(self, memory_id: str, content: str, embedding: List[float]) -> None:
        """Queue vector embedding for background processing."""
        try:
            # In production, this would queue to a background job
            # For now, save directly to Qdrant
            qdrant_client = get_qdrant()
            if not qdrant_client:
                logger.debug("[MEMORY] Qdrant not available, skipping vector storage")
                return

            # Get full memory data for payload
            supabase = get_supabase()
            if supabase:
                result = supabase.table("memory_entries").select("*").eq("id", memory_id).execute()
                if result.data:
                    memory = result.data[0]

                    # Import PointStruct for Qdrant
                    from qdrant_client.models import PointStruct
                    import uuid

                    # Convert memory_id to a valid Qdrant point ID (must be int or UUID)
                    try:
                        point_id = str(uuid.UUID(memory_id))
                    except (ValueError, TypeError):
                        point_id = str(uuid.uuid4())

                    # Save to global Qdrant collection with user_id in payload for filtering
                    qdrant_client.upsert(
                        collection_name=self.QDRANT_COLLECTION,
                        points=[
                            PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload={
                                    "content": content,
                                    "memory_type": memory["memory_type"],
                                    "confidence_score": memory["confidence_score"],
                                    "importance_score": memory["importance_score"],
                                    "created_at": memory["created_at"],
                                    "user_id": memory["user_id"],
                                    "memory_id": memory_id
                                }
                            )
                        ]
                    )
                    logger.info(f"[MEMORY] Saved vector embedding for memory {memory_id[:8]}...")

        except Exception as e:
            logger.error(f"[MEMORY] Failed to queue vector embedding: {e}")

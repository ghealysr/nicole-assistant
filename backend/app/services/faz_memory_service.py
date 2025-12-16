"""
Faz Code Memory Service

Letta/Mem0-style memory system for learning and context retrieval.
Provides:
- Semantic search over past learnings
- Error solution retrieval
- Artifact search
- User preference management
"""

import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database import db
from app.config import settings

logger = logging.getLogger(__name__)


class FazMemoryService:
    """
    Memory service for Faz Code learning system.
    
    Features:
    - Vector similarity search (via pgvector)
    - Error-solution matching
    - Artifact retrieval
    - Preference tracking
    - Memory consolidation
    """
    
    def __init__(self):
        """Initialize memory service."""
        self._embedding_client = None
    
    async def _get_embedding_client(self):
        """Get embedding client."""
        if self._embedding_client is None:
            from app.services.alphawave_embedding_service import embedding_service
            self._embedding_client = embedding_service
        return self._embedding_client
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        try:
            client = await self._get_embedding_client()
            return await client.get_embedding(text)
        except Exception as e:
            logger.error(f"[FazMemory] Embedding failed: {e}")
            return []
    
    # =========================================================================
    # MEMORY OPERATIONS
    # =========================================================================
    
    async def store_memory(
        self,
        user_id: int,
        content: str,
        memory_type: str = "conversation",
        memory_tier: str = "session",
        project_id: Optional[int] = None,
        source_agent: Optional[str] = None,
        importance: float = 0.5,
    ) -> int:
        """
        Store a memory entry.
        
        Args:
            user_id: User ID
            content: Memory content
            memory_type: Type (conversation, decision, pattern, preference, context, error, success)
            memory_tier: Tier (session, project, global)
            project_id: Optional project association
            source_agent: Which agent created this memory
            importance: Importance score (0-1)
            
        Returns:
            Memory ID
        """
        try:
            # Get embedding
            embedding = await self.get_embedding(content)
            
            memory_id = await db.fetchval(
                """
                INSERT INTO faz_code_memories
                    (user_id, project_id, content, memory_type, memory_tier, 
                     embedding, source_agent, importance_score)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING memory_id
                """,
                user_id,
                project_id,
                content,
                memory_type,
                memory_tier,
                embedding if embedding else None,
                source_agent,
                importance,
            )
            
            logger.info(f"[FazMemory] Stored memory {memory_id}: {content[:50]}...")
            return memory_id
            
        except Exception as e:
            logger.error(f"[FazMemory] Failed to store memory: {e}")
            return 0
    
    async def search_memories(
        self,
        query: str,
        user_id: int,
        project_id: Optional[int] = None,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity.
        
        Args:
            query: Search query
            user_id: User ID
            project_id: Optional project filter
            memory_types: Optional type filter
            limit: Max results
            
        Returns:
            List of matching memories
        """
        try:
            embedding = await self.get_embedding(query)
            
            if not embedding:
                # Fallback to text search
                return await self._text_search_memories(query, user_id, project_id, limit)
            
            # Build query
            where_parts = ["user_id = $1"]
            params = [user_id]
            param_idx = 2
            
            if project_id:
                where_parts.append(f"(project_id = ${param_idx} OR memory_tier = 'global')")
                params.append(project_id)
                param_idx += 1
            
            if memory_types:
                where_parts.append(f"memory_type = ANY(${param_idx})")
                params.append(memory_types)
                param_idx += 1
            
            params.append(embedding)
            params.append(limit)
            
            results = await db.fetch(
                f"""
                SELECT 
                    memory_id,
                    content,
                    memory_type,
                    memory_tier,
                    importance_score,
                    source_agent,
                    created_at,
                    1 - (embedding <=> ${param_idx}) AS similarity
                FROM faz_code_memories
                WHERE {' AND '.join(where_parts)}
                    AND embedding IS NOT NULL
                ORDER BY embedding <=> ${param_idx}
                LIMIT ${param_idx + 1}
                """,
                *params,
            )
            
            # Update access counts
            memory_ids = [r["memory_id"] for r in results]
            if memory_ids:
                await db.execute(
                    """
                    UPDATE faz_code_memories
                    SET access_count = access_count + 1,
                        last_accessed_at = NOW()
                    WHERE memory_id = ANY($1)
                    """,
                    memory_ids,
                )
            
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error(f"[FazMemory] Search failed: {e}")
            return []
    
    async def _text_search_memories(
        self,
        query: str,
        user_id: int,
        project_id: Optional[int],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fallback text search."""
        try:
            results = await db.fetch(
                """
                SELECT 
                    memory_id, content, memory_type, memory_tier,
                    importance_score, source_agent, created_at
                FROM faz_code_memories
                WHERE user_id = $1
                    AND content ILIKE '%' || $2 || '%'
                ORDER BY importance_score DESC, created_at DESC
                LIMIT $3
                """,
                user_id,
                query,
                limit,
            )
            return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"[FazMemory] Text search failed: {e}")
            return []
    
    # =========================================================================
    # ERROR SOLUTIONS
    # =========================================================================
    
    async def find_similar_errors(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        framework: str = "nextjs",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find similar past errors and their solutions.
        
        Args:
            error_message: The error to match
            error_type: Optional error type filter
            framework: Framework filter
            limit: Max results
            
        Returns:
            List of error solutions
        """
        try:
            embedding = await self.get_embedding(error_message)
            
            if embedding:
                # Vector search
                results = await db.fetch(
                    """
                    SELECT 
                        solution_id, error_type, error_message, solution_description,
                        solution_steps, code_before, code_after, times_accepted,
                        1 - (error_embedding <=> $1) AS similarity
                    FROM faz_error_solutions
                    WHERE framework = $2
                        AND error_embedding IS NOT NULL
                    ORDER BY error_embedding <=> $1
                    LIMIT $3
                    """,
                    embedding,
                    framework,
                    limit,
                )
            else:
                # Text fallback
                results = await db.fetch(
                    """
                    SELECT 
                        solution_id, error_type, error_message, solution_description,
                        solution_steps, code_before, code_after, times_accepted
                    FROM faz_error_solutions
                    WHERE framework = $1
                        AND (error_message ILIKE '%' || $2 || '%' OR error_type = $3)
                    ORDER BY times_accepted DESC
                    LIMIT $4
                    """,
                    framework,
                    error_message[:100],
                    error_type,
                    limit,
                )
            
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error(f"[FazMemory] Error search failed: {e}")
            return []
    
    async def store_error_solution(
        self,
        error_type: str,
        error_message: str,
        solution_description: str,
        code_before: Optional[str] = None,
        code_after: Optional[str] = None,
        file_path: Optional[str] = None,
        framework: str = "nextjs",
    ) -> int:
        """Store a new error solution."""
        try:
            embedding = await self.get_embedding(f"{error_type}: {error_message}")
            
            solution_id = await db.fetchval(
                """
                INSERT INTO faz_error_solutions
                    (error_type, error_message, solution_description, code_before,
                     code_after, file_path, framework, error_embedding)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING solution_id
                """,
                error_type,
                error_message,
                solution_description,
                code_before,
                code_after,
                file_path,
                framework,
                embedding if embedding else None,
            )
            
            logger.info(f"[FazMemory] Stored error solution {solution_id}")
            return solution_id
            
        except Exception as e:
            logger.error(f"[FazMemory] Failed to store error solution: {e}")
            return 0
    
    async def record_solution_feedback(
        self,
        solution_id: int,
        accepted: bool,
    ):
        """Record whether a suggested solution was accepted."""
        try:
            column = "times_accepted" if accepted else "times_rejected"
            await db.execute(
                f"""
                UPDATE faz_error_solutions
                SET {column} = {column} + 1,
                    last_used_at = NOW()
                WHERE solution_id = $1
                """,
                solution_id,
            )
        except Exception as e:
            logger.error(f"[FazMemory] Failed to record feedback: {e}")
    
    # =========================================================================
    # ARTIFACTS
    # =========================================================================
    
    async def search_artifacts(
        self,
        query: str,
        artifact_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search reusable code artifacts.
        
        Args:
            query: Search query
            artifact_type: Type filter (component, hook, utility, etc.)
            category: Category filter
            limit: Max results
            
        Returns:
            List of matching artifacts
        """
        try:
            embedding = await self.get_embedding(query)
            
            where_parts = ["is_latest = true"]
            params = []
            param_idx = 1
            
            if artifact_type:
                where_parts.append(f"artifact_type = ${param_idx}")
                params.append(artifact_type)
                param_idx += 1
            
            if category:
                where_parts.append(f"category = ${param_idx}")
                params.append(category)
                param_idx += 1
            
            if embedding:
                params.append(embedding)
                params.append(limit)
                
                results = await db.fetch(
                    f"""
                    SELECT 
                        artifact_id, name, artifact_type, code, description, 
                        category, usage_example, times_used,
                        1 - (description_embedding <=> ${param_idx}) AS similarity
                    FROM faz_code_artifacts
                    WHERE {' AND '.join(where_parts)}
                        AND description_embedding IS NOT NULL
                    ORDER BY description_embedding <=> ${param_idx}
                    LIMIT ${param_idx + 1}
                    """,
                    *params,
                )
            else:
                params.append(query)
                params.append(limit)
                
                results = await db.fetch(
                    f"""
                    SELECT 
                        artifact_id, name, artifact_type, code, description,
                        category, usage_example, times_used
                    FROM faz_code_artifacts
                    WHERE {' AND '.join(where_parts)}
                        AND (name ILIKE '%' || ${param_idx} || '%' 
                             OR description ILIKE '%' || ${param_idx} || '%')
                    ORDER BY times_used DESC
                    LIMIT ${param_idx + 1}
                    """,
                    *params,
                )
            
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error(f"[FazMemory] Artifact search failed: {e}")
            return []
    
    async def store_artifact(
        self,
        name: str,
        artifact_type: str,
        code: str,
        description: str,
        category: Optional[str] = None,
        usage_example: Optional[str] = None,
        source_project_id: Optional[int] = None,
    ) -> int:
        """Store a reusable artifact."""
        try:
            # Get embeddings
            desc_embedding = await self.get_embedding(description)
            code_embedding = await self.get_embedding(code[:2000])
            
            slug = name.lower().replace(" ", "-")
            
            artifact_id = await db.fetchval(
                """
                INSERT INTO faz_code_artifacts
                    (artifact_type, name, slug, code, description, category,
                     usage_example, source_project_id, description_embedding, code_embedding)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING artifact_id
                """,
                artifact_type,
                name,
                slug,
                code,
                description,
                category,
                usage_example,
                source_project_id,
                desc_embedding if desc_embedding else None,
                code_embedding if code_embedding else None,
            )
            
            logger.info(f"[FazMemory] Stored artifact {artifact_id}: {name}")
            return artifact_id
            
        except Exception as e:
            logger.error(f"[FazMemory] Failed to store artifact: {e}")
            return 0
    
    # =========================================================================
    # USER PREFERENCES
    # =========================================================================
    
    async def get_user_preferences(
        self,
        user_id: int,
        preference_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get user preferences.
        
        Args:
            user_id: User ID
            preference_type: Optional type filter
            
        Returns:
            Dict of preferences by type
        """
        try:
            where_parts = ["user_id = $1"]
            params = [user_id]
            
            if preference_type:
                where_parts.append("preference_type = $2")
                params.append(preference_type)
            
            results = await db.fetch(
                f"""
                SELECT preference_type, preference_key, preference_value, 
                       confidence_score, observation_count
                FROM faz_user_preferences
                WHERE {' AND '.join(where_parts)}
                ORDER BY confidence_score DESC
                """,
                *params,
            )
            
            # Group by type
            preferences = {}
            for r in results:
                ptype = r["preference_type"]
                if ptype not in preferences:
                    preferences[ptype] = {}
                preferences[ptype][r["preference_key"]] = {
                    "value": r["preference_value"],
                    "confidence": r["confidence_score"],
                    "observations": r["observation_count"],
                }
            
            return preferences
            
        except Exception as e:
            logger.error(f"[FazMemory] Failed to get preferences: {e}")
            return {}
    
    async def update_preference(
        self,
        user_id: int,
        preference_type: str,
        key: str,
        value: str,
        confidence: float = 0.5,
    ):
        """Update or create a user preference."""
        try:
            await db.execute(
                """
                INSERT INTO faz_user_preferences
                    (user_id, preference_type, preference_key, preference_value, confidence_score)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, preference_type, preference_key)
                DO UPDATE SET
                    preference_value = $4,
                    confidence_score = GREATEST(faz_user_preferences.confidence_score, $5),
                    observation_count = faz_user_preferences.observation_count + 1,
                    updated_at = NOW()
                """,
                user_id,
                preference_type,
                key,
                value,
                confidence,
            )
        except Exception as e:
            logger.error(f"[FazMemory] Failed to update preference: {e}")
    
    # =========================================================================
    # SKILLS
    # =========================================================================
    
    async def search_skills(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search learned skills."""
        try:
            embedding = await self.get_embedding(query)
            
            where_parts = []
            params = []
            param_idx = 1
            
            if category:
                where_parts.append(f"skill_category = ${param_idx}")
                params.append(category)
                param_idx += 1
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            if embedding:
                params.append(embedding)
                params.append(limit)
                
                results = await db.fetch(
                    f"""
                    SELECT 
                        skill_id, skill_name, skill_category, description,
                        approach, pitfalls, verification_strategy, times_applied,
                        1 - (skill_embedding <=> ${param_idx}) AS similarity
                    FROM faz_skill_library
                    WHERE {where_clause}
                        AND skill_embedding IS NOT NULL
                    ORDER BY skill_embedding <=> ${param_idx}
                    LIMIT ${param_idx + 1}
                    """,
                    *params,
                )
            else:
                params.append(query)
                params.append(limit)
                
                results = await db.fetch(
                    f"""
                    SELECT 
                        skill_id, skill_name, skill_category, description,
                        approach, pitfalls, verification_strategy, times_applied
                    FROM faz_skill_library
                    WHERE {where_clause}
                        AND (skill_name ILIKE '%' || ${param_idx} || '%'
                             OR description ILIKE '%' || ${param_idx} || '%')
                    ORDER BY times_successful DESC
                    LIMIT ${param_idx + 1}
                    """,
                    *params,
                )
            
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error(f"[FazMemory] Skill search failed: {e}")
            return []


# Global instance
faz_memory = FazMemoryService()


"""
Qdrant Integration for Nicole V7.
Handles vector storage and semantic search for the memory system.

QA NOTES:
- Qdrant is used for semantic/vector search in the 3-tier memory system
- Collections are user-scoped for data isolation
- Embeddings are 1536 dimensions (OpenAI text-embedding-3-small)
- Falls back gracefully when Qdrant unavailable
- Supports filtering by metadata (memory_type, importance, etc.)
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue, Range,
    UpdateStatus
)

from app.config import settings

logger = logging.getLogger(__name__)

# Vector configuration
EMBEDDING_DIMENSIONS = 1536
COLLECTION_NAME_PREFIX = "nicole_memories"


class AlphawaveQdrantClient:
    """
    Client for Qdrant vector database operations.
    
    Features:
    - Create and manage memory collections
    - Store and retrieve vector embeddings
    - Semantic similarity search
    - Metadata filtering
    - User data isolation
    """
    
    def __init__(self):
        """Initialize the Qdrant client."""
        self.client: Optional[QdrantClient] = None
        self.available = False
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize connection to Qdrant."""
        try:
            self.client = QdrantClient(url=settings.QDRANT_URL)
            # Test connection
            self.client.get_collections()
            self.available = True
            logger.info("Qdrant client initialized successfully")
        except Exception as e:
            logger.warning(f"Qdrant not available: {e}")
            self.client = None
            self.available = False
    
    def _get_collection_name(self, user_id: UUID) -> str:
        """Get the collection name for a user."""
        return f"{COLLECTION_NAME_PREFIX}_{str(user_id)[:8]}"
    
    async def ensure_collection(self, user_id: UUID) -> bool:
        """
        Ensure a collection exists for the user.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            True if collection exists or was created
            
        QA NOTE: Collections are created per-user for isolation
        """
        if not self.available or not self.client:
            return False
        
        collection_name = self._get_collection_name(user_id)
        
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            
            if not exists:
                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSIONS,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {collection_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}", exc_info=True)
            return False
    
    async def upsert_memory(
        self,
        user_id: UUID,
        memory_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Insert or update a memory vector.
        
        Args:
            user_id: The user's UUID
            memory_id: Unique identifier for the memory
            embedding: The embedding vector (1536 dimensions)
            metadata: Additional metadata (memory_type, content, importance, etc.)
            
        Returns:
            True if successful
            
        QA NOTE: Uses upsert for idempotent updates
        """
        if not self.available or not self.client:
            logger.warning("Qdrant not available for upsert")
            return False
        
        if len(embedding) != EMBEDDING_DIMENSIONS:
            logger.error(f"Invalid embedding dimensions: {len(embedding)}")
            return False
        
        collection_name = self._get_collection_name(user_id)
        
        # Ensure collection exists
        if not await self.ensure_collection(user_id):
            return False
        
        try:
            # Create point
            point = PointStruct(
                id=memory_id,
                vector=embedding,
                payload={
                    "user_id": str(user_id),
                    **metadata
                }
            )
            
            # Upsert
            result = self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            success = result.status == UpdateStatus.COMPLETED
            if success:
                logger.debug(f"Upserted memory {memory_id} to Qdrant")
            
            return success
            
        except Exception as e:
            logger.error(f"Qdrant upsert error: {e}", exc_info=True)
            return False
    
    async def search_memories(
        self,
        user_id: UUID,
        query_embedding: List[float],
        limit: int = 10,
        min_score: float = 0.7,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using vector similarity.
        
        Args:
            user_id: The user's UUID
            query_embedding: The query embedding vector
            limit: Maximum results to return
            min_score: Minimum similarity score (0-1)
            memory_type: Optional filter by memory type
            min_importance: Optional minimum importance score
            
        Returns:
            List of matching memories with scores
            
        QA NOTE: Returns memories sorted by similarity descending
        """
        if not self.available or not self.client:
            logger.warning("Qdrant not available for search")
            return []
        
        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            logger.error(f"Invalid query embedding dimensions: {len(query_embedding)}")
            return []
        
        collection_name = self._get_collection_name(user_id)
        
        # Build filters
        filter_conditions = []
        
        if memory_type:
            filter_conditions.append(
                FieldCondition(
                    key="memory_type",
                    match=MatchValue(value=memory_type)
                )
            )
        
        if min_importance is not None:
            filter_conditions.append(
                FieldCondition(
                    key="importance_score",
                    range=Range(gte=min_importance)
                )
            )
        
        query_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score,
                query_filter=query_filter
            )
            
            memories = []
            for result in results:
                memory = {
                    "id": result.id,
                    "score": result.score,
                    **result.payload
                }
                memories.append(memory)
            
            logger.debug(f"Found {len(memories)} memories in Qdrant")
            return memories
            
        except Exception as e:
            logger.error(f"Qdrant search error: {e}", exc_info=True)
            return []
    
    async def delete_memory(
        self,
        user_id: UUID,
        memory_id: str
    ) -> bool:
        """
        Delete a memory from the vector store.
        
        Args:
            user_id: The user's UUID
            memory_id: The memory ID to delete
            
        Returns:
            True if successful
        """
        if not self.available or not self.client:
            return False
        
        collection_name = self._get_collection_name(user_id)
        
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=[memory_id]
            )
            logger.debug(f"Deleted memory {memory_id} from Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant delete error: {e}", exc_info=True)
            return False
    
    async def get_collection_stats(
        self,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a user's collection.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            Collection stats dict or None
        """
        if not self.available or not self.client:
            return None
        
        collection_name = self._get_collection_name(user_id)
        
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value
            }
        except Exception as e:
            logger.warning(f"Error getting collection stats: {e}")
            return None
    
    async def backup_collection(
        self,
        user_id: UUID
    ) -> Optional[str]:
        """
        Create a snapshot of a user's collection.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            Snapshot name or None
            
        QA NOTE: Used by background worker for daily backups
        """
        if not self.available or not self.client:
            return None
        
        collection_name = self._get_collection_name(user_id)
        
        try:
            snapshot = self.client.create_snapshot(
                collection_name=collection_name
            )
            logger.info(f"Created snapshot for {collection_name}: {snapshot.name}")
            return snapshot.name
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return None


# Global client instance
qdrant_client = AlphawaveQdrantClient()


# Convenience functions
async def search_similar(
    user_id: UUID,
    embedding: List[float],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Search for similar memories."""
    return await qdrant_client.search_memories(user_id, embedding, limit)


async def store_memory(
    user_id: UUID,
    memory_id: str,
    embedding: List[float],
    metadata: Dict[str, Any]
) -> bool:
    """Store a memory embedding."""
    return await qdrant_client.upsert_memory(user_id, memory_id, embedding, metadata)


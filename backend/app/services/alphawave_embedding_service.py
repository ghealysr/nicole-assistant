"""
Embedding Service for Nicole V7.
Generates vector embeddings using OpenAI's text-embedding-3-small model.

QA NOTES:
- Uses OpenAI embeddings (not Anthropic - Claude doesn't have embedding API)
- Embeddings are 1536 dimensions (text-embedding-3-small default)
- Batch processing supported for efficiency
- Caches embeddings in Redis when available
- Falls back gracefully when Redis unavailable
"""

import hashlib
import json
import logging
from typing import List, Optional, Dict, Any

import openai

from app.config import settings
from app.database import get_redis

logger = logging.getLogger(__name__)

# OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class AlphawaveEmbeddingService:
    """
    Service for generating and managing text embeddings.
    
    Uses OpenAI's text-embedding-3-small for semantic similarity search.
    Integrates with Redis for caching and Qdrant for vector storage.
    """
    
    def __init__(self):
        """Initialize the embedding service with OpenAI client."""
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = EMBEDDING_MODEL
        self.dimensions = EMBEDDING_DIMENSIONS
        self._cache_ttl = 86400  # 24 hours cache
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for the text."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"embedding:{text_hash}"
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding vector, or None on error
            
        QA NOTE: Returns 1536-dimensional vector from OpenAI
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        # Check Redis cache first
        redis = get_redis()
        if redis:
            cache_key = self._get_cache_key(text)
            try:
                cached = redis.get(cache_key)
                if cached:
                    logger.debug(f"Embedding cache hit for key: {cache_key[:20]}...")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")
        
        # Generate new embedding
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # Cache the result
            if redis:
                try:
                    redis.setex(
                        cache_key,
                        self._cache_ttl,
                        json.dumps(embedding)
                    )
                except Exception as e:
                    logger.warning(f"Redis cache write error: {e}")
            
            logger.debug(f"Generated embedding for text ({len(text)} chars)")
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation error: {e}", exc_info=True)
            return None
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        max_batch_size: int = 100
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            max_batch_size: Maximum texts per API call (default 100)
            
        Returns:
            List of embedding vectors (None for failed texts)
            
        QA NOTE: Batching reduces API calls and costs
        """
        if not texts:
            return []
        
        results: List[Optional[List[float]]] = []
        redis = get_redis()
        
        # Check cache for all texts
        texts_to_embed = []
        text_indices = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append(None)
                continue
            
            # Check cache
            cached_embedding = None
            if redis:
                cache_key = self._get_cache_key(text)
                try:
                    cached = redis.get(cache_key)
                    if cached:
                        cached_embedding = json.loads(cached)
                except Exception:
                    pass
            
            if cached_embedding:
                results.append(cached_embedding)
            else:
                results.append(None)  # Placeholder
                texts_to_embed.append(text.strip())
                text_indices.append(i)
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            try:
                # Process in batches
                for batch_start in range(0, len(texts_to_embed), max_batch_size):
                    batch_end = min(batch_start + max_batch_size, len(texts_to_embed))
                    batch_texts = texts_to_embed[batch_start:batch_end]
                    batch_indices = text_indices[batch_start:batch_end]
                    
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=batch_texts,
                        encoding_format="float"
                    )
                    
                    # Store results and cache
                    for j, embedding_data in enumerate(response.data):
                        embedding = embedding_data.embedding
                        original_index = batch_indices[j]
                        results[original_index] = embedding
                        
                        # Cache
                        if redis:
                            cache_key = self._get_cache_key(texts[original_index])
                            try:
                                redis.setex(
                                    cache_key,
                                    self._cache_ttl,
                                    json.dumps(embedding)
                                )
                            except Exception:
                                pass
                
                logger.info(f"Generated {len(texts_to_embed)} embeddings in batch")
                
            except Exception as e:
                logger.error(f"Batch embedding error: {e}", exc_info=True)
        
        return results
    
    async def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
            
        QA NOTE: Cosine similarity is standard for semantic search
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        if len(embedding1) != len(embedding2):
            logger.error("Embedding dimension mismatch")
            return 0.0
        
        # Compute cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def find_similar_texts(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[Dict[str, Any]],
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find the most similar texts from a list of candidates.
        
        Args:
            query_embedding: The embedding to search for
            candidate_embeddings: List of dicts with 'id', 'embedding', and optional metadata
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of matched candidates with similarity scores
            
        QA NOTE: For large-scale search, use Qdrant instead of this method
        """
        if not query_embedding or not candidate_embeddings:
            return []
        
        scored_candidates = []
        
        for candidate in candidate_embeddings:
            embedding = candidate.get("embedding")
            if not embedding:
                continue
            
            similarity = await self.compute_similarity(query_embedding, embedding)
            
            if similarity >= min_similarity:
                result = {
                    "id": candidate.get("id"),
                    "similarity": similarity,
                    **{k: v for k, v in candidate.items() if k not in ["embedding", "id"]}
                }
                scored_candidates.append(result)
        
        # Sort by similarity descending
        scored_candidates.sort(key=lambda x: x["similarity"], reverse=True)
        
        return scored_candidates[:top_k]


# Global service instance
embedding_service = AlphawaveEmbeddingService()


# Convenience functions for direct import
async def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for a single text."""
    return await embedding_service.generate_embedding(text)


async def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """Generate embeddings for multiple texts."""
    return await embedding_service.generate_embeddings_batch(texts)


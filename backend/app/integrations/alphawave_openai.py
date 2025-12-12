"""
OpenAI integration for embeddings and O1-mini research.

Features:
- Embedding generation with retry + jitter
- Batch embedding support
- O1-mini for deep research
"""

from typing import List, Optional
import openai
import logging
import asyncio
import random

from app.config import settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 10.0
JITTER_FACTOR = 0.3


class AlphawaveOpenAIClient:
    """
    OpenAI client wrapper.
    
    Handles embeddings (text-embedding-3-small) and O1-mini for research mode.
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = "text-embedding-3-small"
        self.research_model = "o1-mini"
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        max_retries: int = MAX_RETRIES
    ) -> List[float]:
        """
        Generate embedding vector for text with retry + jitter.
        
        Args:
            text: Text to embed
            model: Model to use (defaults to text-embedding-3-small)
            max_retries: Maximum retry attempts (default: 3)
            
        Returns:
            Embedding vector (1536 dimensions)
        """
        
        if model is None:
            model = self.embedding_model
        
        last_error: Optional[Exception] = None
        
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.embeddings.create(
                    model=model,
                    input=text
                )
                
                if response.data and len(response.data) > 0:
                    return response.data[0].embedding
                
                raise ValueError("No embedding returned from OpenAI")
                
            except Exception as e:
                last_error = e
                
                # Don't retry on final attempt
                if attempt >= max_retries:
                    break
                
                # Calculate delay with exponential backoff + jitter
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                jitter = delay * JITTER_FACTOR * random.uniform(-1, 1)
                final_delay = max(0.1, delay + jitter)
                
                logger.warning(
                    f"OpenAI embedding error (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {final_delay:.2f}s: {e}"
                )
                await asyncio.sleep(final_delay)
        
        logger.error(f"OpenAI embedding failed after {max_retries + 1} attempts: {last_error}", exc_info=True)
        raise last_error or ValueError("Embedding generation failed")
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        max_retries: int = MAX_RETRIES
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch) with retry + jitter.
        
        Args:
            texts: List of texts to embed
            model: Model to use (defaults to text-embedding-3-small)
            max_retries: Maximum retry attempts (default: 3)
            
        Returns:
            List of embedding vectors
        """
        
        if model is None:
            model = self.embedding_model
        
        last_error: Optional[Exception] = None
        
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.embeddings.create(
                    model=model,
                    input=texts
                )
                
                if response.data:
                    return [item.embedding for item in response.data]
                
                raise ValueError("No embeddings returned from OpenAI")
                
            except Exception as e:
                last_error = e
                
                # Don't retry on final attempt
                if attempt >= max_retries:
                    break
                
                # Calculate delay with exponential backoff + jitter
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                jitter = delay * JITTER_FACTOR * random.uniform(-1, 1)
                final_delay = max(0.1, delay + jitter)
                
                logger.warning(
                    f"OpenAI batch embedding error (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {final_delay:.2f}s: {e}"
                )
                await asyncio.sleep(final_delay)
        
        logger.error(f"OpenAI batch embedding failed after {max_retries + 1} attempts: {last_error}", exc_info=True)
        raise last_error or ValueError("Batch embedding generation failed")
    
    async def research_with_o1(
        self,
        prompt: str,
        max_tokens: int = 8000
    ) -> str:
        """
        Deep research with O1-mini (cost-effective extended thinking).
        
        Args:
            prompt: Research prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Research synthesis
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.research_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            
            return ""
            
        except Exception as e:
            logger.error(f"O1-mini research error: {e}", exc_info=True)
            raise


# Global client instance
openai_client = AlphawaveOpenAIClient()


"""
OpenAI integration for embeddings and O1-mini research.
"""

from typing import List, Optional
import openai
import logging

from app.config import settings

logger = logging.getLogger(__name__)


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
        model: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
            model: Model to use (defaults to text-embedding-3-small)
            
        Returns:
            Embedding vector (1536 dimensions)
        """
        
        if model is None:
            model = self.embedding_model
        
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text
            )
            
            if response.data and len(response.data) > 0:
                return response.data[0].embedding
            
            raise ValueError("No embedding returned from OpenAI")
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}", exc_info=True)
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch).
        
        Args:
            texts: List of texts to embed
            model: Model to use (defaults to text-embedding-3-small)
            
        Returns:
            List of embedding vectors
        """
        
        if model is None:
            model = self.embedding_model
        
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            if response.data:
                return [item.embedding for item in response.data]
            
            raise ValueError("No embeddings returned from OpenAI")
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}", exc_info=True)
            raise
    
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


"""
OpenAI integration for embeddings, research, and GPT Image 1.5.

Features:
- Embedding generation with retry + jitter
- Batch embedding support
- O1-mini for deep research
- GPT Image 1.5 (gpt-image-1) for fast, precise image generation

GPT Image 1.5 Capabilities (Dec 2025):
- 4x faster than GPT Image 1
- Precise editing with maintained facial likeness
- Improved text rendering
- Up to 16 input images for multi-image workflows
"""

from typing import List, Optional, Dict, Any
import openai
import logging
import asyncio
import random
import base64

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
    
    Handles:
    - Embeddings (text-embedding-3-small)
    - O1-mini for research mode
    - GPT Image 1.5 for fast image generation
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = "text-embedding-3-small"
        self.research_model = "o1-mini"
        self.image_model = getattr(settings, "OPENAI_IMAGE_MODEL", "gpt-image-1")
    
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
    
    # =========================================================================
    # GPT IMAGE 1.5 - Fast, precise image generation
    # =========================================================================
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "high",
        style: Optional[str] = None,
        num_images: int = 1,
        max_retries: int = MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Generate image(s) using GPT Image 1.5 (gpt-image-1).
        
        GPT Image 1.5 is OpenAI's latest image model (Dec 2025):
        - 4x faster than previous versions
        - Better instruction adherence
        - Improved text rendering
        - Precise editing capabilities
        
        Args:
            prompt: Image description
            size: Output size (1024x1024, 1792x1024, 1024x1792)
            quality: Image quality ("standard", "high", "hd")
            style: Style preset (optional)
            num_images: Number of images to generate (1-4)
            max_retries: Maximum retry attempts
            
        Returns:
            Dict with success, images (base64), urls, metadata
        """
        last_error: Optional[Exception] = None
        
        # Map quality to API format
        quality_map = {
            "standard": "standard",
            "high": "hd",
            "hd": "hd",
            "low": "standard"
        }
        api_quality = quality_map.get(quality, "hd")
        
        # Add style to prompt if provided
        full_prompt = prompt
        if style:
            full_prompt = f"[Style: {style}] {prompt}"
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"[OPENAI] Generating {num_images} image(s) with {self.image_model}, size={size}")
                
                response = await self.client.images.generate(
                    model=self.image_model,
                    prompt=full_prompt,
                    size=size,
                    quality=api_quality,
                    n=min(num_images, 4),
                    response_format="b64_json"  # Get base64 data
                )
                
                if not response.data:
                    raise ValueError("No images returned from OpenAI")
                
                images = []
                urls = []
                
                for img in response.data:
                    if hasattr(img, 'b64_json') and img.b64_json:
                        images.append({
                            "data": img.b64_json,
                            "mime_type": "image/png"
                        })
                    if hasattr(img, 'url') and img.url:
                        urls.append(img.url)
                    if hasattr(img, 'revised_prompt'):
                        logger.info(f"[OPENAI] Revised prompt: {img.revised_prompt[:100]}...")
                
                logger.info(f"[OPENAI] Generated {len(images)} image(s) successfully")
                
                return {
                    "success": True,
                    "images": images,
                    "image_data": images[0]["data"] if images else None,
                    "urls": urls,
                    "count": len(images),
                    "model": self.image_model,
                    "prompt": prompt,
                    "size": size,
                    "quality": api_quality
                }
                
            except openai.RateLimitError as e:
                last_error = e
                if attempt >= max_retries:
                    break
                    
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                jitter = delay * JITTER_FACTOR * random.uniform(-1, 1)
                final_delay = max(0.1, delay + jitter)
                
                logger.warning(
                    f"[OPENAI] Rate limit (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {final_delay:.2f}s"
                )
                await asyncio.sleep(final_delay)
                
            except openai.BadRequestError as e:
                # Content policy violation or invalid request - don't retry
                logger.error(f"[OPENAI] Bad request (content policy?): {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "prompt": prompt,
                    "policy_violation": True
                }
                
            except Exception as e:
                last_error = e
                if attempt >= max_retries:
                    break
                    
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                jitter = delay * JITTER_FACTOR * random.uniform(-1, 1)
                final_delay = max(0.1, delay + jitter)
                
                logger.warning(
                    f"[OPENAI] Image generation error (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {final_delay:.2f}s: {e}"
                )
                await asyncio.sleep(final_delay)
        
        logger.error(f"[OPENAI] Image generation failed after {max_retries + 1} attempts: {last_error}")
        return {
            "success": False,
            "error": str(last_error) if last_error else "Unknown error",
            "prompt": prompt
        }
    
    async def edit_image(
        self,
        image: bytes,
        prompt: str,
        mask: Optional[bytes] = None,
        size: str = "1024x1024",
        num_images: int = 1
    ) -> Dict[str, Any]:
        """
        Edit an image using GPT Image 1.5.
        
        Args:
            image: Original image bytes (PNG)
            prompt: Edit instructions
            mask: Optional mask image (transparent areas will be edited)
            size: Output size
            num_images: Number of variations to generate
            
        Returns:
            Dict with success, edited images
        """
        try:
            logger.info(f"[OPENAI] Editing image with {self.image_model}")
            
            # Create file-like objects for the API
            import io
            image_file = io.BytesIO(image)
            image_file.name = "image.png"
            
            kwargs = {
                "model": self.image_model,
                "image": image_file,
                "prompt": prompt,
                "size": size,
                "n": min(num_images, 4),
                "response_format": "b64_json"
            }
            
            if mask:
                mask_file = io.BytesIO(mask)
                mask_file.name = "mask.png"
                kwargs["mask"] = mask_file
            
            response = await self.client.images.edit(**kwargs)
            
            if not response.data:
                raise ValueError("No edited images returned from OpenAI")
            
            images = []
            for img in response.data:
                if hasattr(img, 'b64_json') and img.b64_json:
                    images.append({
                        "data": img.b64_json,
                        "mime_type": "image/png"
                    })
            
            logger.info(f"[OPENAI] Edited image, generated {len(images)} result(s)")
            
            return {
                "success": True,
                "images": images,
                "image_data": images[0]["data"] if images else None,
                "count": len(images),
                "model": self.image_model,
                "prompt": prompt
            }
            
        except Exception as e:
            logger.error(f"[OPENAI] Image edit error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt
            }


# Global client instance
openai_client = AlphawaveOpenAIClient()


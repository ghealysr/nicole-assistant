"""
Replicate Integration for Nicole V7.
Handles FLUX Pro image generation and Whisper speech-to-text.

QA NOTES:
- FLUX Pro 1.1 for high-quality image generation
- Whisper for speech transcription (via Replicate API)
- Rate limited per user (image_limit_weekly in users table)
- Falls back gracefully when API unavailable
- Images stored in DO Spaces after generation
"""

import logging
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.config import settings
from app.database import get_supabase

logger = logging.getLogger(__name__)

# Replicate API endpoints and models
REPLICATE_API_URL = "https://api.replicate.com/v1"
FLUX_MODEL = "black-forest-labs/flux-1.1-pro"
WHISPER_MODEL = "openai/whisper:large-v3"


class AlphawaveReplicateClient:
    """
    Client for Replicate API (FLUX and Whisper).
    
    Features:
    - Generate images with FLUX Pro 1.1
    - Transcribe audio with Whisper
    - Track user image limits
    - Async prediction handling
    """
    
    def __init__(self):
        """Initialize the Replicate client."""
        self.api_token = settings.REPLICATE_API_TOKEN
        self.available = bool(self.api_token)
        self.supabase = get_supabase()
        
        if not self.available:
            logger.warning("Replicate API token not configured")
    
    def _get_headers(self) -> dict:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def generate_image(
        self,
        user_id: UUID,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_outputs: int = 1,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 28
    ) -> Optional[List[str]]:
        """
        Generate images using FLUX Pro 1.1.
        
        Args:
            user_id: The user's UUID (for rate limiting)
            prompt: Text prompt for image generation
            width: Image width (default 1024)
            height: Image height (default 1024)
            num_outputs: Number of images to generate (1-4)
            guidance_scale: How closely to follow the prompt
            num_inference_steps: Quality vs speed tradeoff
            
        Returns:
            List of image URLs or None on error
            
        QA NOTE: Checks user's weekly image limit before generating
        """
        if not self.available:
            logger.warning("Replicate not available for image generation")
            return None
        
        # Check user's image limit
        if not await self._check_image_limit(user_id):
            logger.warning(f"User {user_id} has exceeded weekly image limit")
            return None
        
        try:
            # Create prediction
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{REPLICATE_API_URL}/predictions",
                    headers=self._get_headers(),
                    json={
                        "version": "latest",
                        "model": FLUX_MODEL,
                        "input": {
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "num_outputs": min(num_outputs, 4),
                            "guidance_scale": guidance_scale,
                            "num_inference_steps": num_inference_steps,
                            "output_format": "webp",
                            "output_quality": 90
                        }
                    },
                    timeout=30.0
                )
                
                if response.status_code != 201:
                    logger.error(f"Replicate API error: {response.status_code}")
                    return None
                
                prediction = response.json()
                prediction_id = prediction.get("id")
            
            # Poll for completion
            result = await self._wait_for_prediction(prediction_id)
            
            if result and result.get("status") == "succeeded":
                images = result.get("output", [])
                
                # Update user's image count
                await self._increment_image_count(user_id, len(images))
                
                logger.info(f"Generated {len(images)} images for user {user_id}")
                return images
            
            return None
            
        except Exception as e:
            logger.error(f"Image generation error: {e}", exc_info=True)
            return None
    
    async def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_url: URL to the audio file
            language: Optional language code (auto-detected if not provided)
            
        Returns:
            Transcription result dict or None on error
            
        QA NOTE: Returns text, segments, and detected language
        """
        if not self.available:
            logger.warning("Replicate not available for transcription")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                input_data = {
                    "audio": audio_url,
                    "transcription": "plain text",
                    "translate": False
                }
                
                if language:
                    input_data["language"] = language
                
                response = await client.post(
                    f"{REPLICATE_API_URL}/predictions",
                    headers=self._get_headers(),
                    json={
                        "version": "latest",
                        "model": WHISPER_MODEL,
                        "input": input_data
                    },
                    timeout=30.0
                )
                
                if response.status_code != 201:
                    logger.error(f"Replicate API error: {response.status_code}")
                    return None
                
                prediction = response.json()
                prediction_id = prediction.get("id")
            
            # Poll for completion
            result = await self._wait_for_prediction(prediction_id, timeout=120)
            
            if result and result.get("status") == "succeeded":
                output = result.get("output", {})
                return {
                    "text": output.get("transcription", ""),
                    "segments": output.get("segments", []),
                    "language": output.get("detected_language", "en")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return None
    
    async def _wait_for_prediction(
        self,
        prediction_id: str,
        timeout: int = 60,
        poll_interval: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Poll for prediction completion."""
        url = f"{REPLICATE_API_URL}/predictions/{prediction_id}"
        elapsed = 0
        
        async with httpx.AsyncClient() as client:
            while elapsed < timeout:
                try:
                    response = await client.get(
                        url,
                        headers=self._get_headers(),
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        status = result.get("status")
                        
                        if status in ["succeeded", "failed", "canceled"]:
                            return result
                    
                except Exception as e:
                    logger.warning(f"Polling error: {e}")
                
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
        
        logger.error(f"Prediction {prediction_id} timed out")
        return None
    
    async def _check_image_limit(self, user_id: UUID) -> bool:
        """Check if user has remaining image quota."""
        if not self.supabase:
            return True  # Allow if can't check
        
        try:
            # Get user's limit and current count
            response = self.supabase.table("users").select(
                "image_limit_weekly"
            ).eq("id", str(user_id)).single().execute()
            
            if not response.data:
                return True
            
            limit = response.data.get("image_limit_weekly", 5)
            
            # Count images generated this week
            from datetime import datetime, timedelta
            week_start = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            count_response = self.supabase.table("generated_artifacts").select(
                "id", count="exact"
            ).eq(
                "user_id", str(user_id)
            ).eq(
                "artifact_type", "image"
            ).gte(
                "created_at", week_start
            ).execute()
            
            current_count = count_response.count or 0
            
            return current_count < limit
            
        except Exception as e:
            logger.warning(f"Error checking image limit: {e}")
            return True
    
    async def _increment_image_count(
        self,
        user_id: UUID,
        count: int
    ) -> None:
        """Record generated images in the database."""
        if not self.supabase:
            return
        
        try:
            for _ in range(count):
                self.supabase.table("generated_artifacts").insert({
                    "user_id": str(user_id),
                    "artifact_type": "image"
                }).execute()
        except Exception as e:
            logger.warning(f"Error recording image: {e}")
    
    async def enhance_prompt(
        self,
        basic_prompt: str
    ) -> str:
        """
        Enhance a basic prompt for better image generation.
        
        Args:
            basic_prompt: Simple user prompt
            
        Returns:
            Enhanced prompt with style details
            
        QA NOTE: Adds artistic style hints for better FLUX results
        """
        # Add quality and style modifiers
        enhancements = [
            "high quality",
            "detailed",
            "professional",
            "8k resolution"
        ]
        
        enhanced = f"{basic_prompt}, {', '.join(enhancements)}"
        
        # Don't exceed reasonable length
        if len(enhanced) > 500:
            enhanced = enhanced[:500]
        
        return enhanced


# Global client instance
replicate_client = AlphawaveReplicateClient()


# Convenience functions
async def generate_image(
    user_id: UUID,
    prompt: str,
    **kwargs
) -> Optional[List[str]]:
    """Generate images with FLUX Pro."""
    return await replicate_client.generate_image(user_id, prompt, **kwargs)


async def transcribe(audio_url: str) -> Optional[Dict[str, Any]]:
    """Transcribe audio with Whisper."""
    return await replicate_client.transcribe_audio(audio_url)


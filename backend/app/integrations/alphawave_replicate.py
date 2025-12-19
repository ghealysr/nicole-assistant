"""
⚠️ PARTIALLY DEPRECATED ⚠️

Image generation has been migrated to:
- backend/app/services/alphawave_image_generation_service.py

This file ONLY maintains Whisper audio transcription for voice features.
DO NOT use this file for image generation.
"""

import logging
import httpx
import asyncio
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# Replicate API endpoints
REPLICATE_API_URL = "https://api.replicate.com/v1"
WHISPER_MODEL = "openai/whisper:large-v3"


class AlphawaveReplicateClient:
    """
    Minimal Replicate client for Whisper audio transcription ONLY.
    
    Image generation has been moved to alphawave_image_generation_service.py
    """
    
    def __init__(self):
        """Initialize the Replicate client."""
        self.api_token = settings.REPLICATE_API_TOKEN
        self.available = bool(self.api_token)
        
        if not self.available:
            logger.warning("Replicate API token not configured - voice features disabled")
    
    def _get_headers(self) -> dict:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using Whisper via Replicate.
        
        Args:
            audio_url: URL to the audio file
            language: Optional language code (e.g., 'en', 'es')
            
        Returns:
            Dict with transcription text and metadata
        """
        if not self.available:
            logger.warning("Replicate not available for transcription")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{REPLICATE_API_URL}/predictions",
                    headers=self._get_headers(),
                    json={
                        "version": "latest",
                        "model": WHISPER_MODEL,
                        "input": {
                            "audio": audio_url,
                            "language": language,
                            "task": "transcribe"
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
                transcription = result.get("output", {})
                logger.info("Audio transcription completed")
                return transcription
            
            return None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return None
    
    async def _wait_for_prediction(
        self,
        prediction_id: str,
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Poll Replicate API until prediction completes.
        
        Args:
            prediction_id: The prediction ID to monitor
            timeout: Max seconds to wait
            poll_interval: Seconds between polls
            
        Returns:
            Final prediction result or None on timeout/error
        """
        start_time = asyncio.get_event_loop().time()
        
        async with httpx.AsyncClient() as client:
            while True:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.error(f"Prediction {prediction_id} timed out")
                    return None
                
                try:
                    response = await client.get(
                        f"{REPLICATE_API_URL}/predictions/{prediction_id}",
                        headers=self._get_headers(),
                        timeout=10.0
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to get prediction status: {response.status_code}")
                        return None
                    
                    prediction = response.json()
                    status = prediction.get("status")
                    
                    if status == "succeeded":
                        return prediction
                    elif status == "failed":
                        error = prediction.get("error", "Unknown error")
                        logger.error(f"Prediction failed: {error}")
                        return None
                    elif status == "canceled":
                        logger.warning(f"Prediction {prediction_id} was canceled")
                        return None
                    
                    # Still processing, wait and retry
                    await asyncio.sleep(poll_interval)
                    
                except Exception as e:
                    logger.error(f"Error polling prediction: {e}")
                    return None


# Global client instance for voice features
replicate_client = AlphawaveReplicateClient()

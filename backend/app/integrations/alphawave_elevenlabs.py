"""
ElevenLabs Integration for Nicole V7.
Handles text-to-speech synthesis for Nicole's voice.

QA NOTES:
- Uses ElevenLabs API for high-quality TTS
- Nicole has a cloned voice (voice ID in settings)
- Supports streaming audio for real-time playback
- Falls back gracefully when API unavailable
- Audio format: mp3 by default
"""

import logging
from typing import Optional, AsyncIterator
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ElevenLabs API endpoints
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Default voice settings for Nicole
DEFAULT_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.5,
    "use_speaker_boost": True
}


class AlphawaveElevenLabsClient:
    """
    Client for ElevenLabs text-to-speech API.
    
    Features:
    - Text-to-speech synthesis with Nicole's cloned voice
    - Streaming audio generation
    - Voice settings customization
    - Usage tracking
    """
    
    def __init__(self):
        """Initialize the ElevenLabs client."""
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = settings.NICOLE_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"  # Default voice
        self.available = bool(self.api_key)
        
        if not self.available:
            logger.warning("ElevenLabs API key not configured - TTS disabled")
    
    def _get_headers(self) -> dict:
        """Get request headers with API key."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
    
    async def synthesize_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_turbo_v2_5",
        output_format: str = "mp3_44100_128"
    ) -> Optional[bytes]:
        """
        Synthesize speech from text.
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID (defaults to Nicole's voice)
            model_id: ElevenLabs model to use
            output_format: Audio output format
            
        Returns:
            Audio bytes or None on error
            
        QA NOTE: Returns MP3 audio data
        """
        if not self.available:
            logger.warning("ElevenLabs not available")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text provided for synthesis")
            return None
        
        voice = voice_id or self.voice_id
        url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice}"
        
        payload = {
            "text": text.strip(),
            "model_id": model_id,
            "voice_settings": DEFAULT_VOICE_SETTINGS,
            "output_format": output_format
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Synthesized {len(text)} chars of text")
                    return response.content
                else:
                    logger.error(
                        f"ElevenLabs API error: {response.status_code} - "
                        f"{response.text[:200]}"
                    )
                    return None
                    
        except httpx.TimeoutException:
            logger.error("ElevenLabs request timed out")
            return None
        except Exception as e:
            logger.error(f"ElevenLabs error: {e}", exc_info=True)
            return None
    
    async def synthesize_speech_streaming(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_turbo_v2_5"
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized speech chunks.
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID
            model_id: ElevenLabs model to use
            
        Yields:
            Audio chunks as they're generated
            
        QA NOTE: Use for real-time playback
        """
        if not self.available:
            logger.warning("ElevenLabs not available for streaming")
            return
        
        if not text or not text.strip():
            return
        
        voice = voice_id or self.voice_id
        url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice}/stream"
        
        payload = {
            "text": text.strip(),
            "model_id": model_id,
            "voice_settings": DEFAULT_VOICE_SETTINGS
        }
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=120.0
                ) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_bytes(chunk_size=1024):
                            yield chunk
                    else:
                        logger.error(f"ElevenLabs streaming error: {response.status_code}")
                        
        except Exception as e:
            logger.error(f"ElevenLabs streaming error: {e}", exc_info=True)
    
    async def get_voices(self) -> list:
        """
        Get available voices from ElevenLabs.
        
        Returns:
            List of voice objects
        """
        if not self.available:
            return []
        
        url = f"{ELEVENLABS_BASE_URL}/voices"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"xi-api-key": self.api_key},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("voices", [])
                    
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
        
        return []
    
    async def get_subscription_info(self) -> Optional[dict]:
        """
        Get subscription/usage information.
        
        Returns:
            Subscription info dict or None
        """
        if not self.available:
            return None
        
        url = f"{ELEVENLABS_BASE_URL}/user/subscription"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"xi-api-key": self.api_key},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                    
        except Exception as e:
            logger.error(f"Error fetching subscription: {e}")
        
        return None
    
    async def detect_emotion_from_text(self, text: str) -> str:
        """
        Detect emotion from text for voice modulation.
        
        Args:
            text: The text to analyze
            
        Returns:
            Emotion string (happy, sad, neutral, excited, concerned)
            
        QA NOTE: Simple heuristic - could be enhanced with sentiment analysis
        """
        text_lower = text.lower()
        
        # Happy/excited indicators
        if any(word in text_lower for word in ["excited", "happy", "great", "wonderful", "amazing", "love", "!", "yay"]):
            return "happy"
        
        # Sad/concerned indicators
        if any(word in text_lower for word in ["sorry", "sad", "unfortunately", "worried", "concerned", "difficult"]):
            return "concerned"
        
        # Excited indicators
        if text.count("!") > 1 or any(word in text_lower for word in ["wow", "incredible", "awesome"]):
            return "excited"
        
        return "neutral"


# Global client instance
elevenlabs_client = AlphawaveElevenLabsClient()


# Convenience functions
async def synthesize(text: str) -> Optional[bytes]:
    """Synthesize speech from text."""
    return await elevenlabs_client.synthesize_speech(text)


async def synthesize_streaming(text: str) -> AsyncIterator[bytes]:
    """Stream synthesized speech."""
    async for chunk in elevenlabs_client.synthesize_speech_streaming(text):
        yield chunk


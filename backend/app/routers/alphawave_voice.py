"""
Voice Router for Nicole V7.
Handles speech-to-text (Whisper) and text-to-speech (ElevenLabs).

QA NOTES:
- STT uses Replicate's Whisper model via audio URL
- TTS uses ElevenLabs with Nicole's cloned voice
- Supports streaming TTS for real-time playback
- Audio files are temporarily stored and cleaned up
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import logging
import base64
from uuid import UUID

from app.integrations.alphawave_elevenlabs import elevenlabs_client
from app.integrations.alphawave_replicate import replicate_client
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class TranscribeRequest(BaseModel):
    """Request model for audio transcription."""
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio data")
    language: Optional[str] = Field(None, description="Language code (e.g., 'en', 'es')")


class TranscribeResponse(BaseModel):
    """Response model for transcription."""
    text: str
    language: str
    segments: Optional[list] = None


class SynthesizeRequest(BaseModel):
    """Request model for speech synthesis."""
    text: str = Field(..., description="Text to convert to speech", max_length=5000)
    voice_id: Optional[str] = Field(None, description="Voice ID (defaults to Nicole)")
    stream: bool = Field(False, description="Whether to stream the audio")


class SynthesizeResponse(BaseModel):
    """Response model for synthesis."""
    audio_base64: str
    duration_seconds: Optional[float] = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: Request, body: TranscribeRequest):
    """
    Transcribe audio to text using Whisper.
    
    Accepts either:
    - audio_url: URL to an audio file
    - audio_base64: Base64 encoded audio data
    
    QA NOTE: Uses Replicate's Whisper model
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate input
    if not body.audio_url and not body.audio_base64:
        raise HTTPException(
            status_code=400, 
            detail="Either audio_url or audio_base64 is required"
        )
    
    # Check if Replicate is available
    if not replicate_client.available:
        raise HTTPException(
            status_code=503, 
            detail="Voice transcription is temporarily unavailable"
        )
    
    try:
        # If base64 provided, we'd need to upload to a temp URL first
        # For now, require URL
        if body.audio_base64 and not body.audio_url:
            raise HTTPException(
                status_code=400,
                detail="Base64 audio upload not yet supported. Please provide audio_url"
            )
        
        # Transcribe via Replicate
        result = await replicate_client.transcribe_audio(
            audio_url=body.audio_url,
            language=body.language
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Transcription failed. Please try again."
            )
        
        logger.info(f"Transcribed audio for user {user_id}: {len(result.get('text', ''))} chars")
        
        return TranscribeResponse(
            text=result.get("text", ""),
            language=result.get("language", "en"),
            segments=result.get("segments")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Transcription failed")


@router.post("/transcribe/upload")
async def transcribe_uploaded_audio(
    request: Request,
    file: UploadFile = File(...),
    language: Optional[str] = None
):
    """
    Transcribe an uploaded audio file.
    
    Accepts audio files (mp3, wav, m4a, webm, etc.)
    
    QA NOTE: File is read into memory, so there's a size limit (~25MB)
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate file type
    allowed_types = {
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
        "audio/m4a", "audio/x-m4a", "audio/webm", "audio/ogg"
    }
    
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file.content_type}"
        )
    
    # Check file size (25MB limit)
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Audio file too large. Maximum size is 25MB"
        )
    
    # For now, return a placeholder since we need URL-based upload
    # In production, we'd upload to Supabase Storage and get a public URL
    return {
        "message": "File upload transcription requires storage integration",
        "file_size": len(content),
        "file_type": file.content_type
    }


@router.post("/synthesize")
async def synthesize_speech(request: Request, body: SynthesizeRequest):
    """
    Convert text to speech using ElevenLabs.
    
    Returns either:
    - Base64 encoded audio (if stream=false)
    - Streaming audio response (if stream=true)
    
    QA NOTE: Uses Nicole's cloned voice by default
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    
    # Check if ElevenLabs is available
    if not elevenlabs_client.available:
        raise HTTPException(
            status_code=503,
            detail="Voice synthesis is temporarily unavailable. Please check API key configuration."
        )
    
    try:
        if body.stream:
            # Return streaming audio response
            return StreamingResponse(
                elevenlabs_client.synthesize_speech_streaming(
                    text=body.text,
                    voice_id=body.voice_id
                ),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "attachment; filename=nicole_speech.mp3"
                }
            )
        else:
            # Return base64 encoded audio
            audio_bytes = await elevenlabs_client.synthesize_speech(
                text=body.text,
                voice_id=body.voice_id
            )
            
            if not audio_bytes:
                raise HTTPException(
                    status_code=500,
                    detail="Speech synthesis failed. Please try again."
                )
            
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            
            logger.info(f"Synthesized speech for user {user_id}: {len(body.text)} chars")
            
            return SynthesizeResponse(
                audio_base64=audio_b64,
                duration_seconds=None  # Could calculate from audio length
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Speech synthesis failed")


@router.get("/voices")
async def list_voices(request: Request):
    """
    List available voices from ElevenLabs.
    
    QA NOTE: Includes Nicole's cloned voice if configured
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not elevenlabs_client.available:
        return {
            "voices": [],
            "message": "Voice service unavailable"
        }
    
    try:
        voices = await elevenlabs_client.get_voices()
        
        # Add Nicole's voice at the top if configured
        nicole_voice = {
            "id": settings.NICOLE_VOICE_ID or "default",
            "name": "Nicole (Default)",
            "description": "Nicole's primary voice"
        }
        
        return {
            "voices": [nicole_voice] + [
                {
                    "id": v.get("voice_id"),
                    "name": v.get("name"),
                    "description": v.get("description", "")
                }
                for v in voices[:10]  # Limit to 10 voices
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        return {"voices": [], "error": "Failed to fetch voices"}


@router.get("/usage")
async def get_voice_usage(request: Request):
    """
    Get voice service usage/quota information.
    
    QA NOTE: Useful for monitoring ElevenLabs character limits
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not elevenlabs_client.available:
        return {
            "available": False,
            "message": "Voice service not configured"
        }
    
    try:
        subscription = await elevenlabs_client.get_subscription_info()
        
        if subscription:
            return {
                "available": True,
                "character_count": subscription.get("character_count", 0),
                "character_limit": subscription.get("character_limit", 0),
                "tier": subscription.get("tier", "unknown")
            }
        
        return {
            "available": True,
            "message": "Usage info unavailable"
        }
        
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        return {"available": False, "error": "Failed to fetch usage"}

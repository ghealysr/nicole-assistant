"""
Gemini AI Client for Muse Design Research Agent.

Provides integration with Google's Gemini 2.5 Pro and Flash models
for multimodal design research, image analysis, and creative generation.
"""

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Model identifiers - Using Gemini 3 Pro Preview (latest multimodal model)
GEMINI_PRO = "gemini-3-pro-preview"  # Gemini 3 Pro Preview - latest with advanced reasoning
GEMINI_PRO_LATEST = "gemini-3-pro-preview"  # Alias for clarity
GEMINI_FLASH = "gemini-2.5-flash-preview-05-20"  # Latest flash model for cost-efficient tasks

# Pricing (per 1M tokens)
GEMINI_PRO_INPUT_COST = 2.50    # $2.50 per 1M input tokens
GEMINI_PRO_OUTPUT_COST = 10.00  # $10.00 per 1M output tokens
GEMINI_FLASH_INPUT_COST = 0.125  # $0.125 per 1M input tokens
GEMINI_FLASH_OUTPUT_COST = 0.50  # $0.50 per 1M output tokens


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class GeminiResponse:
    """Structured response from Gemini API."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    finish_reason: str = ""
    
    @property
    def estimated_cost(self) -> float:
        """Calculate estimated cost in USD."""
        if "pro" in self.model.lower():
            input_cost = (self.input_tokens / 1_000_000) * GEMINI_PRO_INPUT_COST
            output_cost = (self.output_tokens / 1_000_000) * GEMINI_PRO_OUTPUT_COST
        else:
            input_cost = (self.input_tokens / 1_000_000) * GEMINI_FLASH_INPUT_COST
            output_cost = (self.output_tokens / 1_000_000) * GEMINI_FLASH_OUTPUT_COST
        return input_cost + output_cost


@dataclass
class ImagePart:
    """Image content for multimodal requests."""
    data: str  # Base64 encoded image data
    mime_type: str = "image/jpeg"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "inline_data": {
                "mime_type": self.mime_type,
                "data": self.data
            }
        }


@dataclass
class TextPart:
    """Text content for requests."""
    text: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text}


# ============================================================================
# GEMINI CLIENT
# ============================================================================

class GeminiClient:
    """
    Async client for Google Gemini API.
    
    Supports:
    - Text generation (Pro and Flash)
    - Multimodal (images + text)
    - JSON structured output
    - Streaming responses
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        self.client = httpx.AsyncClient(timeout=120.0)
        
        if not self.api_key:
            logger.warning("[GEMINI] No API key configured - Muse features disabled")
    
    @property
    def is_available(self) -> bool:
        """Check if Gemini is properly configured."""
        return bool(self.api_key)
    
    async def generate(
        self,
        prompt: str,
        model: str = GEMINI_PRO,
        system_instruction: Optional[str] = None,
        images: Optional[List[ImagePart]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: Optional[str] = None  # "json" for JSON mode
    ) -> GeminiResponse:
        """
        Generate content from Gemini.
        
        Args:
            prompt: The user prompt
            model: Model to use (GEMINI_PRO or GEMINI_FLASH)
            system_instruction: System-level instructions
            images: List of images for multimodal requests
            max_tokens: Maximum output tokens
            temperature: Creativity level (0.0-2.0)
            response_format: "json" for structured JSON output
            
        Returns:
            GeminiResponse with text and token usage
        """
        if not self.api_key:
            raise ValueError("Gemini API key not configured")
        
        url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
        
        # Build content parts
        parts = []
        
        # Add images first if multimodal
        if images:
            for img in images:
                parts.append(img.to_dict())
        
        # Add text prompt
        parts.append({"text": prompt})
        
        # Build request body
        body: Dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }
        
        # Add system instruction if provided
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # JSON mode
        if response_format == "json":
            body["generationConfig"]["responseMimeType"] = "application/json"
        
        try:
            response = await self.client.post(
                url,
                params={"key": self.api_key},
                json=body
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract response
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("[GEMINI] No candidates in response")
                return GeminiResponse(text="", model=model, finish_reason="no_candidates")
            
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            text = parts[0].get("text", "") if parts else ""
            
            # Extract usage
            usage = data.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", 0)
            output_tokens = usage.get("candidatesTokenCount", 0)
            
            return GeminiResponse(
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                model=model,
                finish_reason=candidate.get("finishReason", "STOP")
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[GEMINI] HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[GEMINI] Error: {e}")
            raise
    
    async def generate_json(
        self,
        prompt: str,
        model: str = GEMINI_PRO,
        system_instruction: Optional[str] = None,
        images: Optional[List[ImagePart]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> tuple[Dict[str, Any], GeminiResponse]:
        """
        Generate structured JSON response.
        
        Returns:
            Tuple of (parsed JSON dict, full response)
        """
        response = await self.generate(
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            images=images,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format="json"
        )
        
        try:
            parsed = json.loads(response.text)
            return parsed, response
        except json.JSONDecodeError as e:
            logger.warning(f"[GEMINI] Failed to parse JSON: {e}")
            # Try to extract JSON from text
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            try:
                parsed = json.loads(text.strip())
                return parsed, response
            except:
                return {}, response
    
    async def analyze_image(
        self,
        image_data: str,
        prompt: str,
        mime_type: str = "image/jpeg",
        model: str = GEMINI_PRO,
        json_output: bool = False
    ) -> Union[str, Dict[str, Any]]:
        """
        Analyze an image with Gemini Vision.
        
        Args:
            image_data: Base64 encoded image
            prompt: Analysis prompt
            mime_type: Image MIME type
            model: Model to use
            json_output: Return JSON structure
            
        Returns:
            Analysis text or JSON dict
        """
        images = [ImagePart(data=image_data, mime_type=mime_type)]
        
        if json_output:
            result, _ = await self.generate_json(
                prompt=prompt,
                model=model,
                images=images,
                max_tokens=4096
            )
            return result
        else:
            response = await self.generate(
                prompt=prompt,
                model=model,
                images=images,
                max_tokens=4096
            )
            return response.text
    
    async def analyze_multiple_images(
        self,
        images: List[Dict[str, str]],  # [{"data": "base64...", "mime_type": "image/..."}]
        prompt: str,
        model: str = GEMINI_PRO
    ) -> GeminiResponse:
        """
        Analyze multiple images together.
        
        Useful for comparing inspiration images and finding patterns.
        """
        image_parts = [
            ImagePart(data=img["data"], mime_type=img.get("mime_type", "image/jpeg"))
            for img in images
        ]
        
        return await self.generate(
            prompt=prompt,
            model=model,
            images=image_parts,
            max_tokens=8192  # Larger for multi-image analysis
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# ============================================================================
# GLOBAL CLIENT INSTANCE
# ============================================================================

gemini_client = GeminiClient()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    mime_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    return mime_types.get(ext, "image/jpeg")


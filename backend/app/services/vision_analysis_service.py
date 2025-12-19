"""
Vision Analysis Service for Reference Image Processing

Uses Claude 3.5 Sonnet's vision capabilities to analyze reference images
and extract actionable insights for image generation.

Author: AlphaWave Tech
Quality Standard: Anthropic Engineer Level
"""

import asyncio
import base64
import logging
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any

from anthropic import Anthropic, AsyncAnthropic
from PIL import Image
import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class ImageSource(str, Enum):
    """Source type for reference images"""
    UPLOAD = "upload"
    URL = "url"
    PATH = "path"


@dataclass
class ColorPalette:
    """Extracted color palette from reference image"""
    dominant_colors: List[str]  # Hex codes
    color_harmony: str  # e.g., "complementary", "analogous", "triadic"
    temperature: str  # "warm", "cool", "neutral"
    saturation_level: str  # "vibrant", "muted", "desaturated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dominant_colors": self.dominant_colors,
            "color_harmony": self.color_harmony,
            "temperature": self.temperature,
            "saturation_level": self.saturation_level,
        }


@dataclass
class CompositionAnalysis:
    """Visual composition and structure analysis"""
    layout_type: str  # "rule_of_thirds", "centered", "symmetrical", etc.
    focal_points: List[str]
    depth: str  # "shallow", "medium", "deep"
    perspective: str  # "eye_level", "birds_eye", "worms_eye", etc.
    balance: str  # "symmetrical", "asymmetrical", "radial"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_type": self.layout_type,
            "focal_points": self.focal_points,
            "depth": self.depth,
            "perspective": self.perspective,
            "balance": self.balance,
        }


@dataclass
class StyleAnalysis:
    """Artistic style and aesthetic analysis"""
    primary_style: str  # "photorealistic", "impressionist", "minimalist", etc.
    secondary_styles: List[str]
    art_movement: Optional[str]  # "Art Deco", "Bauhaus", etc.
    medium: str  # "digital", "oil_painting", "watercolor", etc.
    technical_approach: str  # "detailed", "loose", "graphic", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_style": self.primary_style,
            "secondary_styles": self.secondary_styles,
            "art_movement": self.art_movement,
            "medium": self.medium,
            "technical_approach": self.technical_approach,
        }


@dataclass
class MoodAnalysis:
    """Emotional and atmospheric analysis"""
    primary_mood: str
    atmosphere: str
    energy_level: str  # "calm", "dynamic", "intense", etc.
    emotional_tone: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_mood": self.primary_mood,
            "atmosphere": self.atmosphere,
            "energy_level": self.energy_level,
            "emotional_tone": self.emotional_tone,
        }


@dataclass
class SubjectAnalysis:
    """Subject matter and content analysis"""
    main_subjects: List[str]
    environment: Optional[str]
    time_of_day: Optional[str]
    season: Optional[str]
    notable_elements: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "main_subjects": self.main_subjects,
            "environment": self.environment,
            "time_of_day": self.time_of_day,
            "season": self.season,
            "notable_elements": self.notable_elements,
        }


@dataclass
class VisionAnalysisResult:
    """Complete vision analysis result for a single image"""
    image_id: str
    style: StyleAnalysis
    composition: CompositionAnalysis
    colors: ColorPalette
    mood: MoodAnalysis
    subject: SubjectAnalysis
    prompt_suggestions: List[str]
    technical_notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "style": self.style.to_dict(),
            "composition": self.composition.to_dict(),
            "colors": self.colors.to_dict(),
            "mood": self.mood.to_dict(),
            "subject": self.subject.to_dict(),
            "prompt_suggestions": self.prompt_suggestions,
            "technical_notes": self.technical_notes,
        }


@dataclass
class MultiImageAnalysis:
    """Analysis results for multiple reference images"""
    individual_analyses: List[VisionAnalysisResult]
    common_themes: List[str]
    unified_style_guidance: str
    combined_prompt_enhancement: str
    consistency_notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "individual_analyses": [a.to_dict() for a in self.individual_analyses],
            "common_themes": self.common_themes,
            "unified_style_guidance": self.unified_style_guidance,
            "combined_prompt_enhancement": self.combined_prompt_enhancement,
            "consistency_notes": self.consistency_notes,
        }


class VisionAnalysisService:
    """
    Production-grade vision analysis service using Claude 3.5 Sonnet.
    
    Handles reference image analysis with comprehensive error handling,
    retries, and structured output parsing.
    """
    
    # Model configuration
    MODEL = "claude-sonnet-4-5-20250929"  # Latest Claude 4.5 Sonnet
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3  # Lower for more consistent structured output
    
    # Image processing
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    SUPPORTED_FORMATS = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    RESIZE_MAX_DIMENSION = 1568  # Claude's optimal size
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    def __init__(self):
        """Initialize the vision analysis service"""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.sync_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info("VisionAnalysisService initialized")
    
    def _get_analysis_prompt(self, user_prompt: Optional[str] = None) -> str:
        """
        Generate the system prompt for vision analysis.
        
        Args:
            user_prompt: Optional user's intended generation prompt for context
            
        Returns:
            Structured prompt for Claude
        """
        base_prompt = """You are an expert art director and visual analyst specializing in image generation guidance.

Analyze the provided reference image(s) with extreme precision and attention to detail. Your analysis will guide AI image generation, so be specific and actionable.

Provide your analysis in the following JSON structure:

{
  "style": {
    "primary_style": "specific style descriptor",
    "secondary_styles": ["style1", "style2"],
    "art_movement": "if applicable, e.g., Art Deco, Bauhaus",
    "medium": "perceived medium (digital, oil, watercolor, 3D render, etc.)",
    "technical_approach": "detailed/loose/graphic/textured/clean"
  },
  "composition": {
    "layout_type": "rule_of_thirds/centered/asymmetrical/golden_ratio/etc.",
    "focal_points": ["describe each focal point"],
    "depth": "shallow/medium/deep",
    "perspective": "eye_level/birds_eye/worms_eye/low_angle/high_angle",
    "balance": "symmetrical/asymmetrical/radial"
  },
  "colors": {
    "dominant_colors": ["#HEX1", "#HEX2", "#HEX3"],
    "color_harmony": "complementary/analogous/triadic/monochromatic",
    "temperature": "warm/cool/neutral",
    "saturation_level": "vibrant/muted/desaturated/high_contrast"
  },
  "mood": {
    "primary_mood": "specific mood descriptor",
    "atmosphere": "describe the atmospheric quality",
    "energy_level": "calm/dynamic/intense/serene/chaotic",
    "emotional_tone": ["tone1", "tone2"]
  },
  "subject": {
    "main_subjects": ["list all main subjects"],
    "environment": "describe setting/environment if applicable",
    "time_of_day": "morning/afternoon/evening/night/golden_hour/blue_hour",
    "season": "spring/summer/fall/winter if discernible",
    "notable_elements": ["unique features worth noting"]
  },
  "prompt_suggestions": [
    "Specific prompt phrase 1 that captures style",
    "Specific prompt phrase 2 for composition",
    "Specific prompt phrase 3 for mood/atmosphere",
    "Specific technical terms that would help reproduce this"
  ],
  "technical_notes": [
    "Lighting technique observations",
    "Rendering/texture notes",
    "Special effects or techniques used"
  ]
}

Be extremely specific in your descriptions. Instead of "modern", say "minimalist flat design with geometric shapes". Instead of "colorful", say "high-saturation complementary color scheme with cyan and orange".

Think like you're briefing an AI image generator with precise technical instructions."""

        if user_prompt:
            base_prompt += f"\n\nUser's intended generation prompt: \"{user_prompt}\"\n\nTailor your analysis to help achieve this vision."
        
        return base_prompt
    
    def _get_multi_image_synthesis_prompt(self) -> str:
        """Generate prompt for synthesizing multiple image analyses"""
        return """You are synthesizing analysis from multiple reference images to create unified guidance.

Analyze the common themes, consistent styles, and patterns across all images. Provide:

{
  "common_themes": ["theme1", "theme2", "theme3"],
  "unified_style_guidance": "A cohesive description combining all style elements",
  "combined_prompt_enhancement": "A single, powerful prompt enhancement that captures all references",
  "consistency_notes": ["What's consistent", "What varies", "Recommendations"]
}

Focus on what's COMMON and CONSISTENT across images, while noting important variations."""
    
    async def _encode_image(
        self,
        image_source: str,
        source_type: ImageSource = ImageSource.UPLOAD
    ) -> tuple[str, str]:
        """
        Encode image to base64 for Claude API.
        
        Args:
            image_source: File path, URL, or base64 data
            source_type: Type of image source
            
        Returns:
            Tuple of (base64_data, media_type)
            
        Raises:
            ValueError: If image format unsupported or size exceeded
            httpx.HTTPError: If URL download fails
        """
        try:
            # Handle different source types
            if source_type == ImageSource.URL:
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_source, timeout=10.0)
                    response.raise_for_status()
                    image_data = response.content
                    content_type = response.headers.get("content-type", "image/jpeg")
            
            elif source_type == ImageSource.PATH:
                with open(image_source, "rb") as f:
                    image_data = f.read()
                
                # Detect content type from extension
                suffix = Path(image_source).suffix.lower()
                content_type_map = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".webp": "image/webp",
                    ".gif": "image/gif"
                }
                content_type = content_type_map.get(suffix, "image/jpeg")
            
            else:  # UPLOAD - assume base64
                if "base64," in image_source:
                    # Extract base64 data and content type
                    header, data = image_source.split("base64,", 1)
                    content_type = header.split(":")[1].split(";")[0]
                    return data, content_type
                else:
                    image_data = base64.b64decode(image_source)
                    content_type = "image/jpeg"
            
            # Validate content type
            if content_type not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported image format: {content_type}")
            
            # Validate and potentially resize image
            image = Image.open(BytesIO(image_data))
            
            # Resize if necessary
            width, height = image.size
            max_dim = max(width, height)
            
            if max_dim > self.RESIZE_MAX_DIMENSION:
                scale = self.RESIZE_MAX_DIMENSION / max_dim
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Re-encode
                output = BytesIO()
                image_format = content_type.split("/")[1].upper()
                if image_format == "JPEG":
                    image.save(output, format="JPEG", quality=85, optimize=True)
                else:
                    image.save(output, format=image_format, optimize=True)
                
                image_data = output.getvalue()
                logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
            
            # Check size limit
            if len(image_data) > self.MAX_IMAGE_SIZE:
                raise ValueError(f"Image size {len(image_data)} exceeds maximum {self.MAX_IMAGE_SIZE}")
            
            # Encode to base64
            base64_data = base64.b64encode(image_data).decode("utf-8")
            
            return base64_data, content_type
            
        except Exception as e:
            logger.error(f"Failed to encode image: {str(e)}")
            raise
    
    async def analyze_single_image(
        self,
        image_source: str,
        source_type: ImageSource = ImageSource.UPLOAD,
        user_prompt: Optional[str] = None,
        image_id: Optional[str] = None
    ) -> VisionAnalysisResult:
        """
        Analyze a single reference image.
        
        Args:
            image_source: Image data (path, URL, or base64)
            source_type: Type of image source
            user_prompt: Optional user's generation prompt for context
            image_id: Optional identifier for the image
            
        Returns:
            Structured vision analysis result
            
        Raises:
            Exception: On analysis failure after retries
        """
        if image_id is None:
            image_id = f"ref_{hash(image_source) % 10000:04d}"
        
        logger.info(f"Analyzing image: {image_id}")
        
        # Encode image
        base64_data, media_type = await self._encode_image(image_source, source_type)
        
        # Construct message with vision
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_data,
                        }
                    },
                    {
                        "type": "text",
                        "text": "Analyze this reference image and provide detailed JSON output as specified."
                    }
                ]
            }
        ]
        
        # Retry logic
        last_exception = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    system=self._get_analysis_prompt(user_prompt),
                    messages=messages
                )
                
                # Extract and parse response
                response_text = response.content[0].text
                
                # Parse JSON response
                import json
                
                # Try to extract JSON from markdown code blocks if present
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                else:
                    json_text = response_text.strip()
                
                data = json.loads(json_text)
                
                # Construct structured result
                result = VisionAnalysisResult(
                    image_id=image_id,
                    style=StyleAnalysis(
                        primary_style=data["style"]["primary_style"],
                        secondary_styles=data["style"]["secondary_styles"],
                        art_movement=data["style"].get("art_movement"),
                        medium=data["style"]["medium"],
                        technical_approach=data["style"]["technical_approach"]
                    ),
                    composition=CompositionAnalysis(
                        layout_type=data["composition"]["layout_type"],
                        focal_points=data["composition"]["focal_points"],
                        depth=data["composition"]["depth"],
                        perspective=data["composition"]["perspective"],
                        balance=data["composition"]["balance"]
                    ),
                    colors=ColorPalette(
                        dominant_colors=data["colors"]["dominant_colors"],
                        color_harmony=data["colors"]["color_harmony"],
                        temperature=data["colors"]["temperature"],
                        saturation_level=data["colors"]["saturation_level"]
                    ),
                    mood=MoodAnalysis(
                        primary_mood=data["mood"]["primary_mood"],
                        atmosphere=data["mood"]["atmosphere"],
                        energy_level=data["mood"]["energy_level"],
                        emotional_tone=data["mood"]["emotional_tone"]
                    ),
                    subject=SubjectAnalysis(
                        main_subjects=data["subject"]["main_subjects"],
                        environment=data["subject"].get("environment"),
                        time_of_day=data["subject"].get("time_of_day"),
                        season=data["subject"].get("season"),
                        notable_elements=data["subject"]["notable_elements"]
                    ),
                    prompt_suggestions=data["prompt_suggestions"],
                    technical_notes=data["technical_notes"]
                )
                
                logger.info(f"Successfully analyzed image: {image_id}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {str(e)}")
                
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        
        # All retries failed
        logger.error(f"Failed to analyze image after {self.MAX_RETRIES} attempts")
        raise last_exception
    
    async def analyze_multiple_images(
        self,
        image_sources: List[tuple[str, ImageSource]],
        user_prompt: Optional[str] = None
    ) -> MultiImageAnalysis:
        """
        Analyze multiple reference images and synthesize results.
        
        Args:
            image_sources: List of (image_source, source_type) tuples
            user_prompt: Optional user's generation prompt for context
            
        Returns:
            Combined multi-image analysis
            
        Raises:
            Exception: If any analysis fails
        """
        logger.info(f"Analyzing {len(image_sources)} reference images")
        
        # Analyze all images concurrently
        tasks = [
            self.analyze_single_image(
                source,
                source_type,
                user_prompt,
                f"ref_{i+1:02d}"
            )
            for i, (source, source_type) in enumerate(image_sources)
        ]
        
        individual_analyses = await asyncio.gather(*tasks)
        
        # Synthesize results
        synthesis_text = self._create_synthesis_text(individual_analyses)
        
        # Call Claude to synthesize
        response = await self.client.messages.create(
            model=self.MODEL,
            max_tokens=2048,
            temperature=self.TEMPERATURE,
            system=self._get_multi_image_synthesis_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": synthesis_text
                }
            ]
        )
        
        # Parse synthesis
        import json
        response_text = response.content[0].text
        
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text.strip()
        
        synthesis_data = json.loads(json_text)
        
        result = MultiImageAnalysis(
            individual_analyses=individual_analyses,
            common_themes=synthesis_data["common_themes"],
            unified_style_guidance=synthesis_data["unified_style_guidance"],
            combined_prompt_enhancement=synthesis_data["combined_prompt_enhancement"],
            consistency_notes=synthesis_data["consistency_notes"]
        )
        
        logger.info("Successfully synthesized multi-image analysis")
        return result
    
    def _create_synthesis_text(self, analyses: List[VisionAnalysisResult]) -> str:
        """Create text summary of all analyses for synthesis"""
        summary_parts = []
        
        for i, analysis in enumerate(analyses, 1):
            summary = f"""
Image {i} ({analysis.image_id}):
- Style: {analysis.style.primary_style} ({analysis.style.medium})
- Mood: {analysis.mood.primary_mood}, {analysis.mood.atmosphere}
- Colors: {analysis.colors.temperature} temperature, {analysis.colors.saturation_level}
- Composition: {analysis.composition.layout_type}, {analysis.composition.perspective}
- Subjects: {', '.join(analysis.subject.main_subjects)}
"""
            summary_parts.append(summary)
        
        return "\n".join(summary_parts)


# Global service instance
_vision_service: Optional[VisionAnalysisService] = None


def get_vision_service() -> VisionAnalysisService:
    """Get or create the global vision analysis service instance"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionAnalysisService()
    return _vision_service


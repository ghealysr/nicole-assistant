"""
Nicole's Prompt Improvement Service

Uses Claude with Nicole's personality to analyze image generation prompts
and provide helpful, actionable suggestions for improvement.

Author: AlphaWave Tech
Quality Standard: Anthropic Engineer Level
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from anthropic import AsyncAnthropic

from app.config import settings


logger = logging.getLogger(__name__)


@dataclass
class PromptSuggestion:
    """A single prompt improvement suggestion from Nicole."""
    type: str  # "specificity", "style", "technical", "composition", "lighting", "color"
    title: str
    description: str
    enhanced_prompt: str
    reasoning: str
    priority: int  # 1-5, higher is more important
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "enhanced_prompt": self.enhanced_prompt,
            "reasoning": self.reasoning,
            "priority": self.priority,
        }


@dataclass
class PromptAnalysis:
    """Complete analysis of a user's prompt with suggestions."""
    original_prompt: str
    analysis_summary: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[PromptSuggestion]
    overall_quality_score: int  # 1-10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_prompt": self.original_prompt,
            "analysis_summary": self.analysis_summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "overall_quality_score": self.overall_quality_score,
        }


class NicolePromptService:
    """
    Nicole's prompt improvement service for image generation.
    
    Analyzes user prompts and provides warm, helpful suggestions
    in Nicole's voice while maintaining technical accuracy.
    """
    
    # Model configuration
    MODEL = "claude-3-5-sonnet-20241022"
    MAX_TOKENS = 3072
    TEMPERATURE = 0.7  # Slightly warmer for Nicole's personality
    
    # Retry configuration
    MAX_RETRIES = 2
    RETRY_DELAY = 1.0
    
    def __init__(self):
        """Initialize Nicole's prompt service."""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info("NicolePromptService initialized")
    
    def _get_nicole_system_prompt(self) -> str:
        """
        Get Nicole's system prompt for prompt analysis.
        
        This combines Nicole's personality with expertise in image generation.
        """
        return """You are Nicole, an AI companion who's passionate about helping people create amazing images.

## YOUR PERSONALITY

You're warm, encouraging, and genuinely excited about creative work. You love helping people refine their vision and bring their ideas to life. You're knowledgeable about image generation but never condescending - you explain things clearly and with enthusiasm.

When analyzing prompts, you:
- Celebrate what's already good about the prompt
- Gently point out areas for improvement
- Provide specific, actionable suggestions
- Explain *why* each suggestion will help
- Maintain an encouraging, supportive tone

## YOUR EXPERTISE

You understand image generation deeply:
- **Technical aspects:** Resolution, aspect ratio, lighting, camera angles, depth of field
- **Artistic elements:** Composition, color theory, style references, mood, atmosphere
- **Model strengths:** Which details work best for different image generators
- **Text rendering:** How to get clear, readable text in images
- **Quality markers:** Professional terminology that elevates results

## YOUR TASK

Analyze the user's prompt and provide helpful suggestions. Focus on:

1. **Specificity:** Vague prompts → Concrete details
2. **Technical Details:** Add camera specs, lighting direction, time of day
3. **Style Guidance:** Artistic movements, known works, aesthetic references
4. **Composition:** Layout principles, focal points, balance
5. **Color Direction:** Palettes, temperature, contrast, harmony
6. **Mood & Atmosphere:** Emotional tone, environmental qualities
7. **Text Elements:** If text is mentioned, specify exact wording and style

## OUTPUT FORMAT

Return your analysis as JSON:

```json
{
  "analysis_summary": "A warm, encouraging summary of your analysis (2-3 sentences)",
  "strengths": [
    "What's already great about this prompt",
    "Another strength"
  ],
  "weaknesses": [
    "Areas that could use more detail",
    "Another area for improvement"
  ],
  "suggestions": [
    {
      "type": "specificity|style|technical|composition|lighting|color",
      "title": "Brief suggestion title",
      "description": "Friendly explanation of what to improve and why",
      "enhanced_prompt": "The specific text to add or replace",
      "reasoning": "Why this improvement will help",
      "priority": 1-5
    }
  ],
  "overall_quality_score": 1-10
}
```

## SUGGESTION TYPES

- **specificity**: Adding concrete details to vague descriptions
- **style**: Artistic style, movements, aesthetic references
- **technical**: Camera settings, lighting specs, technical details
- **composition**: Layout, framing, focal points, rule of thirds
- **lighting**: Lighting direction, quality, time of day
- "color": Color palette, temperature, harmony, contrast

## PRIORITY LEVELS

- **5 (Critical):** Missing essential elements that will significantly impact results
- **4 (High):** Important improvements that will notably enhance the image
- **3 (Medium):** Helpful refinements that add polish
- **2 (Low):** Nice-to-have details for extra quality
- **1 (Optional):** Subtle enhancements for perfectionists

## EXAMPLES

**User prompt:** "A cat sitting"
**Your analysis:**
- Strengths: Clear subject
- Weaknesses: Very minimal, lacks environment, style, mood
- Suggestions: Add breed/appearance, setting, lighting, mood, artistic style
- Score: 3/10

**User prompt:** "Cinematic portrait of a woman in her 30s, shot with 85mm lens at f/1.8, golden hour lighting from the left, wearing elegant business attire, confident expression, shallow depth of field with bokeh background, professional color grading"
**Your analysis:**
- Strengths: Excellent technical details, clear style, good lighting description
- Weaknesses: Could specify background environment, hair/eye color for consistency
- Suggestions: Minor refinements only
- Score: 9/10

Remember: Be warm, be helpful, be Nicole! 💜"""
    
    async def analyze_prompt(
        self,
        prompt: str,
        user_context: Optional[Dict[str, Any]] = None,
        vision_analysis: Optional[Dict[str, Any]] = None
    ) -> PromptAnalysis:
        """
        Analyze a prompt and provide suggestions for improvement.
        
        Args:
            prompt: The user's original prompt
            user_context: Optional context (use case, target model, etc.)
            vision_analysis: Optional vision analysis from reference images
            
        Returns:
            Complete prompt analysis with suggestions
            
        Raises:
            Exception: On analysis failure after retries
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        logger.info(f"Analyzing prompt: {prompt[:100]}...")
        
        # Build user message with context
        user_message = f"Please analyze this image generation prompt and provide suggestions:\n\n\"{prompt}\""
        
        # Add context if provided
        if user_context:
            context_parts = []
            if user_context.get("use_case"):
                context_parts.append(f"Use case: {user_context['use_case']}")
            if user_context.get("target_model"):
                context_parts.append(f"Target model: {user_context['target_model']}")
            if user_context.get("aspect_ratio"):
                context_parts.append(f"Aspect ratio: {user_context['aspect_ratio']}")
            if user_context.get("resolution"):
                context_parts.append(f"Resolution: {user_context['resolution']}")
            
            if context_parts:
                user_message += f"\n\nContext:\n" + "\n".join(f"- {p}" for p in context_parts)
        
        # Add vision analysis if provided
        if vision_analysis:
            user_message += "\n\n[Reference Image Analysis Available]"
            if vision_analysis.get("style"):
                user_message += f"\n- Style: {vision_analysis['style'].get('primary_style')}"
            if vision_analysis.get("colors"):
                colors = vision_analysis['colors']
                user_message += f"\n- Colors: {colors.get('temperature')} temperature, {colors.get('saturation_level')}"
            if vision_analysis.get("mood"):
                user_message += f"\n- Mood: {vision_analysis['mood'].get('primary_mood')}"
        
        # Retry logic
        last_exception = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    system=self._get_nicole_system_prompt(),
                    messages=[
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ]
                )
                
                # Extract and parse response
                response_text = response.content[0].text
                
                # Parse JSON response
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
                suggestions = [
                    PromptSuggestion(
                        type=s["type"],
                        title=s["title"],
                        description=s["description"],
                        enhanced_prompt=s["enhanced_prompt"],
                        reasoning=s["reasoning"],
                        priority=s["priority"]
                    )
                    for s in data.get("suggestions", [])
                ]
                
                # Sort suggestions by priority (high to low)
                suggestions.sort(key=lambda s: s.priority, reverse=True)
                
                result = PromptAnalysis(
                    original_prompt=prompt,
                    analysis_summary=data["analysis_summary"],
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    suggestions=suggestions,
                    overall_quality_score=data.get("overall_quality_score", 5)
                )
                
                logger.info(f"Prompt analysis complete: {len(suggestions)} suggestions, score {result.overall_quality_score}/10")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {str(e)}")
                
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        
        # All retries failed
        logger.error(f"Failed to analyze prompt after {self.MAX_RETRIES} attempts")
        raise last_exception or Exception("Prompt analysis failed")
    
    async def apply_suggestions(
        self,
        original_prompt: str,
        selected_suggestions: List[PromptSuggestion]
    ) -> str:
        """
        Apply selected suggestions to create an enhanced prompt.
        
        Args:
            original_prompt: The original user prompt
            selected_suggestions: List of suggestions to apply
            
        Returns:
            Enhanced prompt with suggestions incorporated
        """
        if not selected_suggestions:
            return original_prompt
        
        # Build enhanced prompt
        enhanced_parts = [original_prompt.strip()]
        
        # Group suggestions by type for better organization
        by_type: Dict[str, List[str]] = {}
        for suggestion in selected_suggestions:
            suggestion_type = suggestion.type
            if suggestion_type not in by_type:
                by_type[suggestion_type] = []
            by_type[suggestion_type].append(suggestion.enhanced_prompt)
        
        # Add suggestions in logical order
        type_order = ["technical", "lighting", "composition", "style", "color", "specificity"]
        
        for suggestion_type in type_order:
            if suggestion_type in by_type:
                enhanced_parts.extend(by_type[suggestion_type])
        
        # Add any remaining types not in the order
        for suggestion_type, additions in by_type.items():
            if suggestion_type not in type_order:
                enhanced_parts.extend(additions)
        
        enhanced_prompt = ". ".join(enhanced_parts)
        
        # Clean up formatting
        enhanced_prompt = enhanced_prompt.replace("..", ".")
        enhanced_prompt = enhanced_prompt.replace("  ", " ")
        enhanced_prompt = enhanced_prompt.strip()
        
        logger.info(f"Applied {len(selected_suggestions)} suggestions to prompt")
        return enhanced_prompt


# Global service instance
_nicole_prompt_service: Optional[NicolePromptService] = None


def get_nicole_prompt_service() -> NicolePromptService:
    """Get or create the global Nicole prompt service instance."""
    global _nicole_prompt_service
    if _nicole_prompt_service is None:
        _nicole_prompt_service = NicolePromptService()
    return _nicole_prompt_service


"""
Multi-Model Orchestrator for AlphaWave Vibe

Implements Anthropic-style model orchestration with intelligent routing:

- Gemini 2.0 Flash: Design research, visual trends, color theory, inspiration
- Claude Opus: Architecture, complex reasoning, quality judgment
- Claude Sonnet: Fast code generation, QA validation

Fallback Strategy:
- If primary model fails, gracefully degrade to backup
- Track model health and adjust routing dynamically
- Provide user-friendly error messages

Author: AlphaWave Architecture
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """What each model excels at."""
    DESIGN_RESEARCH = "design_research"      # Visual trends, colors, inspiration
    WEB_GROUNDING = "web_grounding"          # Real-time web search
    ARCHITECTURE = "architecture"            # System design, planning
    CODE_GENERATION = "code_generation"      # Writing code
    CODE_REVIEW = "code_review"              # QA, finding issues
    JUDGMENT = "judgment"                    # Final approval decisions
    CONVERSATION = "conversation"            # Chat, intake


@dataclass
class ModelHealth:
    """Tracks health status of a model."""
    name: str
    available: bool = True
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    cooldown_until: Optional[datetime] = None
    
    def record_success(self):
        """Record successful call."""
        self.available = True
        self.consecutive_failures = 0
        self.cooldown_until = None
    
    def record_failure(self, error: str):
        """Record failed call and potentially enter cooldown."""
        self.last_failure = datetime.utcnow()
        self.consecutive_failures += 1
        
        # Enter cooldown after 3 consecutive failures
        if self.consecutive_failures >= 3:
            # Exponential cooldown: 30s, 60s, 120s, max 5min
            cooldown_seconds = min(30 * (2 ** (self.consecutive_failures - 3)), 300)
            self.cooldown_until = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
            self.available = False
            logger.warning(
                f"[ORCHESTRATOR] {self.name} entering cooldown for {cooldown_seconds}s "
                f"after {self.consecutive_failures} failures"
            )
    
    def check_available(self) -> bool:
        """Check if model is available (not in cooldown)."""
        if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
            return False
        
        # Cooldown expired, reset
        if self.cooldown_until and datetime.utcnow() >= self.cooldown_until:
            self.cooldown_until = None
            self.available = True
            self.consecutive_failures = 0
            logger.info(f"[ORCHESTRATOR] {self.name} cooldown expired, now available")
        
        return self.available


@dataclass
class DesignSystem:
    """Generated design system from Gemini."""
    colors: Dict[str, str] = field(default_factory=dict)
    typography: Dict[str, str] = field(default_factory=dict)
    spacing: Dict[str, str] = field(default_factory=dict)
    inspiration_notes: str = ""
    trends_applied: List[str] = field(default_factory=list)
    generated_by: str = "gemini"


class ModelOrchestrator:
    """
    Orchestrates multi-model AI workflow for Vibe Dashboard.
    
    Design Philosophy (Anthropic-style):
    1. Use the right model for each task based on capabilities
    2. Implement graceful degradation with fallbacks
    3. Track model health and adapt routing
    4. Provide clear observability into model decisions
    """
    
    # Model capability mapping
    MODEL_CAPABILITIES = {
        "gemini-2.0-flash": [
            ModelCapability.DESIGN_RESEARCH,
            ModelCapability.WEB_GROUNDING,
        ],
        "claude-opus": [
            ModelCapability.ARCHITECTURE,
            ModelCapability.JUDGMENT,
            ModelCapability.CODE_REVIEW,
        ],
        "claude-sonnet": [
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_REVIEW,
            ModelCapability.CONVERSATION,
        ],
    }
    
    # Fallback chains for each capability
    FALLBACK_CHAINS = {
        ModelCapability.DESIGN_RESEARCH: ["gemini-2.0-flash", "claude-opus"],
        ModelCapability.WEB_GROUNDING: ["gemini-2.0-flash", "claude-sonnet"],
        ModelCapability.ARCHITECTURE: ["claude-opus", "claude-sonnet"],
        ModelCapability.CODE_GENERATION: ["claude-sonnet", "gemini-2.0-flash"],
        ModelCapability.CODE_REVIEW: ["claude-sonnet", "claude-opus"],
        ModelCapability.JUDGMENT: ["claude-opus", "claude-sonnet"],
        ModelCapability.CONVERSATION: ["claude-sonnet", "claude-opus"],
    }
    
    def __init__(self):
        """Initialize orchestrator with model health tracking."""
        self.model_health: Dict[str, ModelHealth] = {
            "gemini-2.0-flash": ModelHealth("gemini-2.0-flash"),
            "claude-opus": ModelHealth("claude-opus"),
            "claude-sonnet": ModelHealth("claude-sonnet"),
        }
        
        # Lazy imports to avoid circular dependencies
        self._gemini_client = None
        self._claude_client = None
    
    @property
    def gemini(self):
        """Lazy-load Gemini client."""
        if self._gemini_client is None:
            from app.integrations.alphawave_gemini import gemini_client
            self._gemini_client = gemini_client
        return self._gemini_client
    
    @property
    def claude(self):
        """Lazy-load Claude client."""
        if self._claude_client is None:
            from app.integrations.alphawave_claude import claude_client
            self._claude_client = claude_client
        return self._claude_client
    
    def get_best_model(self, capability: ModelCapability) -> Optional[str]:
        """
        Get the best available model for a capability.
        
        Returns the first healthy model in the fallback chain.
        """
        chain = self.FALLBACK_CHAINS.get(capability, [])
        
        for model in chain:
            health = self.model_health.get(model)
            if health and health.check_available():
                return model
        
        # All models in chain are unavailable
        logger.error(f"[ORCHESTRATOR] No available models for {capability.value}")
        return None
    
    def record_result(self, model: str, success: bool, error: Optional[str] = None):
        """Record the result of a model call."""
        health = self.model_health.get(model)
        if health:
            if success:
                health.record_success()
            else:
                health.record_failure(error or "Unknown error")
    
    async def generate_design_system(
        self,
        brief: Dict[str, Any],
        project_id: int
    ) -> DesignSystem:
        """
        Generate a design system using Gemini's creative and research capabilities.
        
        Gemini excels at:
        - Understanding visual trends via web grounding
        - Creative color palette generation
        - Typography recommendations based on industry
        - Modern design pattern suggestions
        """
        model = self.get_best_model(ModelCapability.DESIGN_RESEARCH)
        
        if model == "gemini-2.0-flash" and self.gemini.is_configured:
            try:
                return await self._generate_design_with_gemini(brief, project_id)
            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] Gemini design failed: {e}")
                self.record_result("gemini-2.0-flash", False, str(e))
                # Fall through to Claude fallback
        
        # Fallback to Claude for design
        logger.info("[ORCHESTRATOR] Using Claude fallback for design system")
        return await self._generate_design_with_claude(brief, project_id)
    
    async def _generate_design_with_gemini(
        self,
        brief: Dict[str, Any],
        project_id: int
    ) -> DesignSystem:
        """Use Gemini to research and generate a design system."""
        business_type = brief.get("business_type", brief.get("project_type", "business"))
        business_name = brief.get("business_name", "Client")
        description = brief.get("description", "")
        
        # Step 1: Research current design trends for this industry
        research_query = f"""
        Current web design trends for {business_type} websites in 2025.
        Looking for:
        - Modern color palettes that work for {business_type}
        - Typography combinations that convey {brief.get('brand_feel', 'professional')}
        - Layout patterns that are popular for {business_type} sites
        - Specific examples from successful {business_type} websites
        """
        
        research_result = await self.gemini.deep_research(
            query=research_query,
            research_type="inspiration"
        )
        
        # Step 2: Generate design system based on research
        design_prompt = f"""
        Based on current design trends and this client brief, create a design system:

        Business: {business_name}
        Type: {business_type}
        Description: {description}
        Brand Feel: {brief.get('brand_feel', 'professional, trustworthy')}

        Research findings: {research_result.get('summary', '')}

        Generate a cohesive design system as JSON with:
        {{
            "colors": {{
                "primary": "#hexcode - main brand color",
                "secondary": "#hexcode - supporting color", 
                "accent": "#hexcode - call-to-action color",
                "text": "#hexcode",
                "text_light": "#hexcode",
                "background": "#hexcode"
            }},
            "typography": {{
                "heading_font": "Font name from Google Fonts",
                "body_font": "Font name from Google Fonts",
                "heading_weight": "600 or 700",
                "body_weight": "400"
            }},
            "spacing": {{
                "section_padding": "tailwind classes like py-16 md:py-24",
                "container": "max-w-7xl mx-auto px-4"
            }},
            "style_notes": "Brief description of the visual style",
            "trends_applied": ["trend1", "trend2"]
        }}
        """
        
        design_response = await self.gemini.deep_research(
            query=design_prompt,
            research_type="general"
        )
        
        self.record_result("gemini-2.0-flash", True)
        
        # Parse the response
        design_data = design_response.get("structured_data", {})
        if not design_data:
            # Try to extract from summary
            import json
            import re
            summary = design_response.get("summary", "")
            json_match = re.search(r'\{[^{}]*"colors"[^{}]*\}', summary, re.DOTALL)
            if json_match:
                try:
                    design_data = json.loads(json_match.group())
                except:
                    pass
        
        return DesignSystem(
            colors=design_data.get("colors", {
                "primary": "#8B9D83",
                "secondary": "#F4E4BC",
                "accent": "#D4A574",
                "text": "#333333",
                "text_light": "#666666",
                "background": "#FFFFFF"
            }),
            typography=design_data.get("typography", {
                "heading_font": "Playfair Display",
                "body_font": "Source Sans Pro",
                "heading_weight": "700",
                "body_weight": "400"
            }),
            spacing=design_data.get("spacing", {
                "section_padding": "py-16 md:py-24",
                "container": "max-w-7xl mx-auto px-4"
            }),
            inspiration_notes=design_data.get("style_notes", ""),
            trends_applied=design_data.get("trends_applied", []),
            generated_by="gemini"
        )
    
    async def _generate_design_with_claude(
        self,
        brief: Dict[str, Any],
        project_id: int
    ) -> DesignSystem:
        """Fallback: Use Claude to generate design system."""
        business_type = brief.get("business_type", brief.get("project_type", "business"))
        business_name = brief.get("business_name", "Client")
        
        prompt = f"""
        Create a design system for this website:
        
        Business: {business_name}
        Type: {business_type}
        Description: {brief.get('description', '')}
        Brand Feel: {brief.get('brand_feel', 'professional')}
        
        Output as JSON with colors, typography, and spacing.
        """
        
        try:
            response = await self.claude.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a professional web designer. Generate modern, attractive design systems.",
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.7
            )
            
            self.record_result("claude-sonnet", True)
            
            # Parse response (simplified)
            import json
            import re
            json_match = re.search(r'\{[^{}]*"colors"[^{}]*\}', response, re.DOTALL)
            if json_match:
                try:
                    design_data = json.loads(json_match.group())
                    return DesignSystem(
                        colors=design_data.get("colors", {}),
                        typography=design_data.get("typography", {}),
                        spacing=design_data.get("spacing", {}),
                        generated_by="claude"
                    )
                except:
                    pass
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Claude design fallback failed: {e}")
            self.record_result("claude-sonnet", False, str(e))
        
        # Return safe defaults
        return DesignSystem(
            colors={
                "primary": "#8B9D83",
                "secondary": "#F4E4BC", 
                "accent": "#D4A574"
            },
            typography={
                "heading_font": "Playfair Display",
                "body_font": "Source Sans Pro"
            },
            generated_by="default"
        )
    
    async def generate_with_fallback(
        self,
        capability: ModelCapability,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.5
    ) -> Tuple[str, str]:
        """
        Generate content with automatic fallback.
        
        Returns: (response, model_used)
        """
        chain = self.FALLBACK_CHAINS.get(capability, ["claude-sonnet"])
        
        for model in chain:
            health = self.model_health.get(model)
            if not health or not health.check_available():
                continue
            
            try:
                if "gemini" in model:
                    response = await self.gemini.deep_research(
                        query=prompt,
                        research_type="general"
                    )
                    self.record_result(model, True)
                    return response.get("summary", ""), model
                
                elif "claude" in model:
                    claude_model = (
                        "claude-sonnet-4-20250514" if "sonnet" in model 
                        else "claude-sonnet-4-20250514"  # Opus would be different
                    )
                    response = await self.claude.generate_response(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=system_prompt,
                        model=claude_model,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    self.record_result(model, True)
                    return response, model
                    
            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] {model} failed: {e}")
                self.record_result(model, False, str(e))
                continue
        
        raise Exception("All models failed. Please try again later.")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health status summary for all models."""
        return {
            model: {
                "available": health.check_available(),
                "consecutive_failures": health.consecutive_failures,
                "cooldown_remaining": (
                    (health.cooldown_until - datetime.utcnow()).total_seconds()
                    if health.cooldown_until and health.cooldown_until > datetime.utcnow()
                    else 0
                )
            }
            for model, health in self.model_health.items()
        }


# Global orchestrator instance
model_orchestrator = ModelOrchestrator()


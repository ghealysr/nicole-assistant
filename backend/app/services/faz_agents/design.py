"""
Design Agent - Faz Code Designer

Creates design systems, color palettes, and typography.
Uses Gemini 3 Pro for creative design decisions.
"""

from typing import Any, Dict
import json
import logging

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class DesignAgent(BaseAgent):
    """
    The Design Agent creates visual systems and design tokens.
    
    Responsibilities:
    - Create color palettes
    - Select typography
    - Define spacing and layout systems
    - Create design tokens for Tailwind
    """
    
    agent_id = "design"
    agent_name = "Design Agent"
    agent_role = "Designer - Creates color palettes, typography, and design systems"
    model_provider = "google"
    model_name = "gemini-3-pro-preview"
    temperature = 0.8  # Higher for creativity
    max_tokens = 4096
    
    capabilities = [
        "color_theory",
        "typography",
        "component_design",
        "responsive_layout",
        "design_tokens",
        "tailwind_config"
    ]
    
    available_tools = ["brave_web_search"]
    valid_handoff_targets = ["coding"]
    receives_handoffs_from = ["nicole", "planning", "research"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Design Agent for Faz Code, a world-class UI/UX designer.

## YOUR ROLE
Create stunning, professional design systems that make websites look like they cost $50,000.

## DESIGN PHILOSOPHY
- Bold but tasteful color choices
- Typography that commands attention
- Generous whitespace
- Micro-interactions and subtle animations
- Mobile-first responsive design

## OUTPUT FORMAT
```json
{
  "design_philosophy": "One paragraph describing the visual direction and why",
  "colors": {
    "primary": "#hex - main brand color",
    "primary_dark": "#hex - darker shade for hover",
    "secondary": "#hex - supporting color",
    "accent": "#hex - call-to-action, highlights",
    "background": "#hex - main background",
    "background_alt": "#hex - alternate/card backgrounds",
    "text": "#hex - primary text",
    "text_light": "#hex - secondary text",
    "border": "#hex - borders and dividers",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error": "#EF4444"
  },
  "typography": {
    "heading_font": "Font Name (from Google Fonts)",
    "body_font": "Font Name (from Google Fonts)",
    "heading_weights": ["600", "700", "800"],
    "body_weights": ["400", "500", "600"],
    "base_size": "16px",
    "scale": {
      "xs": "0.75rem",
      "sm": "0.875rem",
      "base": "1rem",
      "lg": "1.125rem",
      "xl": "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem",
      "5xl": "3rem",
      "6xl": "3.75rem"
    }
  },
  "spacing": {
    "section_padding": "py-20 md:py-32",
    "container": "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
    "card_padding": "p-6 md:p-8",
    "gap": {
      "sm": "gap-4",
      "md": "gap-6",
      "lg": "gap-8",
      "xl": "gap-12"
    }
  },
  "effects": {
    "border_radius": {
      "sm": "rounded",
      "md": "rounded-lg",
      "lg": "rounded-xl",
      "full": "rounded-full"
    },
    "shadows": {
      "sm": "shadow-sm",
      "md": "shadow-md",
      "lg": "shadow-lg",
      "xl": "shadow-xl"
    },
    "transitions": "transition-all duration-300 ease-in-out"
  },
  "tailwind_extend": {
    "colors": {},
    "fontFamily": {}
  }
}
```

## COLOR THEORY TIPS
- Law firms: Deep blues, grays, gold accents
- Tech startups: Vibrant gradients, electric blues/purples
- Healthcare: Calming blues, greens, clean whites
- E-commerce: Brand-forward with strong CTAs
- Creative agencies: Bold, unexpected color combinations

## HANDOFF
After design tokens are ready, hand off to **coding** for implementation."""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for design system generation."""
        prompt_parts = []
        
        original = state.get("original_prompt", "")
        prompt_parts.append(f"## PROJECT REQUEST\n{original}")
        
        # Research context
        research_results = state.get("research_results") or state.get("data", {}).get("research_results")
        if research_results:
            prompt_parts.append(f"\n## RESEARCH FINDINGS")
            
            if research_results.get("industry"):
                prompt_parts.append(f"Industry: {research_results['industry']}")
            
            if research_results.get("trends"):
                prompt_parts.append(f"Trends: {', '.join(research_results['trends'][:3])}")
            
            if research_results.get("color_recommendations"):
                prompt_parts.append(f"Color suggestions: {json.dumps(research_results['color_recommendations'])}")
            
            if research_results.get("typography_recommendations"):
                prompt_parts.append(f"Typography suggestions: {json.dumps(research_results['typography_recommendations'])}")
        
        # Inspiration image analysis from Research Agent
        inspiration_analysis = state.get("inspiration_analysis") or state.get("data", {}).get("inspiration_analysis")
        if inspiration_analysis:
            prompt_parts.append(f"\n## USER INSPIRATION IMAGES\nThe user provided inspiration images with notes. Here's the analysis:\n{inspiration_analysis}")
            prompt_parts.append("\n**IMPORTANT**: Incorporate elements the user highlighted from their inspiration images into your design system.")
        
        # Architecture context
        if state.get("architecture"):
            arch = state["architecture"]
            if arch.get("project_summary"):
                prompt_parts.append(f"\n## PROJECT SUMMARY\n{json.dumps(arch['project_summary'], indent=2)}")
        
        prompt_parts.append("""
## YOUR TASK
Create a complete design system JSON with:
1. Color palette (primary, secondary, accent, backgrounds, text)
2. Typography (heading font, body font, scale)
3. Spacing system
4. Effects (shadows, borders, transitions)
5. Tailwind configuration extensions
6. If user provided inspiration images, incorporate their desired elements

Make it look premium and professional.""")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse design tokens from response."""
        try:
            design_tokens = self.extract_json(response)
            
            if not design_tokens:
                logger.warning("[Design] Could not extract design tokens JSON")
                # Create default tokens
                design_tokens = self._get_default_tokens()
            
            # Validate required sections
            required = ["colors", "typography"]
            for req in required:
                if req not in design_tokens:
                    design_tokens[req] = self._get_default_tokens()[req]
            
            return AgentResult(
                success=True,
                message=f"Design system created: {design_tokens.get('design_philosophy', 'Modern and professional')[:100]}",
                data={
                    "design_tokens": design_tokens,
                    "colors": design_tokens.get("colors", {}),
                    "typography": design_tokens.get("typography", {}),
                },
                next_agent="coding",
            )
            
        except Exception as e:
            logger.error(f"[Design] Parse error: {e}")
            return AgentResult(
                success=True,  # Still successful, just use defaults
                message="Design system created with defaults",
                data={"design_tokens": self._get_default_tokens()},
                next_agent="coding",
            )
    
    def _get_default_tokens(self) -> Dict[str, Any]:
        """Return sensible default design tokens."""
        return {
            "design_philosophy": "Clean, modern design with strong visual hierarchy and thoughtful use of whitespace.",
            "colors": {
                "primary": "#3B82F6",
                "primary_dark": "#2563EB",
                "secondary": "#1E40AF",
                "accent": "#F59E0B",
                "background": "#FFFFFF",
                "background_alt": "#F8FAFC",
                "text": "#1F2937",
                "text_light": "#6B7280",
                "border": "#E5E7EB",
                "success": "#22C55E",
                "warning": "#F59E0B",
                "error": "#EF4444"
            },
            "typography": {
                "heading_font": "Inter",
                "body_font": "Inter",
                "heading_weights": ["600", "700", "800"],
                "body_weights": ["400", "500", "600"],
                "base_size": "16px"
            },
            "spacing": {
                "section_padding": "py-20 md:py-32",
                "container": "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
            },
            "effects": {
                "border_radius": {"md": "rounded-lg"},
                "shadows": {"md": "shadow-md"},
                "transitions": "transition-all duration-300 ease-in-out"
            }
        }


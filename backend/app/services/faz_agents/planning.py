"""
Planning Agent - Faz Code Architect

Creates project architecture, file structure, and component breakdown.
Uses Claude Opus 4.5 for complex architectural reasoning.
"""

from typing import Any, Dict
import json
import logging

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    """
    The Planning Agent creates the technical blueprint for the project.
    
    Responsibilities:
    - Analyze requirements and create architecture
    - Define file structure
    - Break down components
    - Plan SEO strategy
    - Define design tokens structure
    """
    
    agent_id = "planning"
    agent_name = "Planning Agent"
    agent_role = "Architect - Creates project architecture and component structure"
    model_provider = "anthropic"
    model_name = "claude-sonnet-4-20250514"
    temperature = 0.5  # Lower for more consistent architecture
    max_tokens = 8192
    
    capabilities = [
        "architecture",
        "file_structure",
        "component_breakdown",
        "api_design",
        "seo_strategy"
    ]
    
    available_tools = ["memory_search"]
    valid_handoff_targets = ["design", "coding"]
    receives_handoffs_from = ["nicole", "research"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Planning Agent for Faz Code, an expert software architect.

## YOUR ROLE
Create comprehensive technical architectures for web projects. Your output becomes the blueprint that the Coding Agent follows.

## OUTPUT FORMAT
You MUST output valid JSON with this exact structure:

```json
{
  "project_summary": {
    "name": "Project Name",
    "description": "Brief description",
    "target_audience": "Who this is for",
    "key_features": ["feature1", "feature2"]
  },
  "tech_stack": {
    "framework": "nextjs",
    "styling": "tailwind",
    "ui_library": "shadcn",
    "animations": "framer-motion"
  },
  "pages": [
    {
      "path": "/",
      "name": "Homepage",
      "components": ["Hero", "Features", "Testimonials", "CTA", "Footer"],
      "seo": {
        "title": "Page Title | Site Name",
        "description": "Meta description under 160 chars"
      }
    }
  ],
  "components": [
    {
      "name": "Hero",
      "type": "section",
      "description": "Full-width hero with headline, subheadline, and CTA",
      "props": ["title", "subtitle", "ctaText", "ctaLink"],
      "responsive": true
    }
  ],
  "design_tokens": {
    "colors": {
      "primary": "#3B82F6",
      "secondary": "#1E40AF",
      "accent": "#F59E0B",
      "background": "#FFFFFF",
      "text": "#1F2937"
    },
    "typography": {
      "heading_font": "Inter",
      "body_font": "Inter",
      "base_size": "16px"
    },
    "spacing": {
      "section_padding": "py-20 md:py-32",
      "container": "max-w-7xl mx-auto px-6"
    }
  },
  "file_structure": [
    "app/layout.tsx",
    "app/page.tsx",
    "app/globals.css",
    "components/Hero.tsx",
    "components/Features.tsx",
    "tailwind.config.ts"
  ],
  "seo": {
    "title": "Site Title",
    "description": "Site description",
    "keywords": ["keyword1", "keyword2"]
  }
}
```

## QUALITY STANDARDS
- Every component must have a clear purpose
- Use semantic HTML structure
- Plan for mobile-first responsive design
- Include accessibility considerations
- Make the Coding Agent's job crystal clear

## HANDOFF
After creating the architecture, hand off to either:
- **design**: If user needs custom colors/typography
- **coding**: If architecture is ready for implementation (default)"""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for architecture generation."""
        prompt_parts = []
        
        # Original request
        original = state.get("original_prompt", state.get("current_prompt", ""))
        prompt_parts.append(f"## USER REQUEST\n{original}")
        
        # Nicole's instructions if any
        if state.get("data", {}).get("agent_instructions"):
            prompt_parts.append(f"\n## ORCHESTRATOR INSTRUCTIONS\n{state['data']['agent_instructions']}")
        
        # Design context if available
        if state.get("design_tokens"):
            prompt_parts.append(f"\n## DESIGN TOKENS (from Design Agent)\n```json\n{json.dumps(state['design_tokens'], indent=2)}\n```")
        
        # Research context if available
        if state.get("research_results"):
            prompt_parts.append(f"\n## RESEARCH FINDINGS\n{state['research_results'][:2000]}")
        
        # Relevant memories
        if state.get("relevant_memories"):
            memories = state["relevant_memories"][:3]
            memory_text = "\n".join([f"- {m.get('content', '')[:200]}" for m in memories])
            prompt_parts.append(f"\n## RELEVANT PAST LEARNINGS\n{memory_text}")
        
        # Relevant skills
        if state.get("relevant_skills"):
            skills = state["relevant_skills"][:2]
            skills_text = "\n".join([f"- {s.get('skill_name', '')}: {s.get('approach', '')[:150]}" for s in skills])
            prompt_parts.append(f"\n## APPLICABLE SKILLS\n{skills_text}")
        
        prompt_parts.append("\n## YOUR TASK\nCreate a complete architecture JSON for this project. Include all pages, components, design tokens, and file structure.")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse architecture from response."""
        try:
            # Extract JSON
            architecture = self.extract_json(response)
            
            if not architecture:
                logger.warning("[Planning] Could not extract JSON architecture")
                return AgentResult(
                    success=False,
                    message="Failed to generate valid architecture",
                    error="Could not parse architecture JSON from response",
                    next_agent=None,
                )
            
            # Validate required fields
            required_fields = ["pages", "components", "file_structure"]
            missing = [f for f in required_fields if f not in architecture]
            
            if missing:
                logger.warning(f"[Planning] Missing fields: {missing}")
                # Try to add defaults for missing fields
                if "pages" not in architecture:
                    architecture["pages"] = [{"path": "/", "name": "Homepage", "components": ["Hero"]}]
                if "components" not in architecture:
                    architecture["components"] = [{"name": "Hero", "type": "section"}]
                if "file_structure" not in architecture:
                    architecture["file_structure"] = ["app/layout.tsx", "app/page.tsx"]
            
            # Create summary
            page_count = len(architecture.get("pages", []))
            component_count = len(architecture.get("components", []))
            
            # Determine next agent
            # If no design tokens or user asked for design → design
            # Otherwise → coding
            if not architecture.get("design_tokens") and "design" in state.get("original_prompt", "").lower():
                next_agent = "design"
            else:
                next_agent = "coding"
            
            return AgentResult(
                success=True,
                message=f"Architecture complete: {page_count} pages, {component_count} components",
                data={
                    "architecture": architecture,
                    "page_count": page_count,
                    "component_count": component_count,
                },
                next_agent=next_agent,
            )
            
        except Exception as e:
            logger.exception(f"[Planning] Parse error: {e}")
            return AgentResult(
                success=False,
                message="Failed to parse architecture",
                error=str(e),
            )


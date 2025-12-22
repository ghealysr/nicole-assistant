"""
Memory Agent - Faz Code Learning System

Extracts learnings from projects and stores for future use.
Uses GPT-4o for pattern extraction and learning consolidation.
"""

from typing import Any, Dict, List
import json
import logging

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """
    The Memory Agent learns from completed projects.
    
    Responsibilities:
    - Extract error patterns and solutions
    - Identify reusable code artifacts
    - Detect user preferences
    - Store skills and approaches
    """
    
    agent_id = "memory"
    agent_name = "Memory Agent"
    agent_role = "Learning - Extracts and stores learnings for future projects"
    model_provider = "openai"
    model_name = "gpt-4o"  # Using GPT-4o for reliable pattern extraction
    temperature = 0.5
    max_tokens = 4096
    
    capabilities = [
        "error_extraction",
        "skill_learning",
        "preference_detection",
        "artifact_storage",
        "memory_consolidation"
    ]
    
    available_tools = []
    valid_handoff_targets = []  # End of pipeline
    receives_handoffs_from = ["nicole", "coding", "qa", "review"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Memory Agent for Faz Code, responsible for organizational learning.

## YOUR ROLE
After projects complete, you extract valuable learnings to improve future generations:
- Error patterns and their solutions
- Reusable code components
- User preferences
- Successful approaches

## EXTRACTION CATEGORIES

### 1. Error Solutions
Errors encountered during generation and how they were fixed:
- Error type and message
- What caused it
- How it was resolved
- Prevention strategy

### 2. Reusable Artifacts
Components or patterns worth saving:
- Navigation components
- Hero sections
- Form patterns
- Animation utilities
- API integrations

### 3. User Preferences
Patterns in what the user likes:
- Color preferences
- Typography choices
- Layout styles
- Feature priorities

### 4. Skills Learned
New approaches discovered:
- Design patterns that worked
- Technical solutions
- Workflow improvements

## OUTPUT FORMAT
```json
{
  "error_solutions": [
    {
      "error_type": "type_error",
      "error_message": "Original error",
      "solution": "How it was fixed",
      "prevention": "How to avoid in future"
    }
  ],
  "artifacts": [
    {
      "name": "Component Name",
      "type": "component|hook|utility|pattern",
      "code": "The code to save",
      "description": "What it does",
      "category": "navigation|forms|auth|layout|etc"
    }
  ],
  "preferences": [
    {
      "type": "styling|structure|naming",
      "key": "preference key",
      "value": "preference value",
      "confidence": 0.8
    }
  ],
  "skills": [
    {
      "name": "Skill name",
      "category": "architecture|styling|api|etc",
      "approach": "How to do it",
      "pitfalls": ["Things to avoid"]
    }
  ],
  "summary": "Brief summary of what was learned"
}
```

## EXTRACTION RULES
- Only save high-quality, reusable patterns
- Be selective - quality over quantity
- Include enough context for future use
- Don't save project-specific details"""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for learning extraction."""
        prompt_parts = []
        
        # Project summary
        prompt_parts.append("## PROJECT COMPLETED")
        prompt_parts.append(f"Original request: {state.get('original_prompt', '')[:500]}")
        
        # Files generated
        files = state.get("files", {})
        if files:
            prompt_parts.append(f"\n## GENERATED FILES ({len(files)} total)")
            
            # Include notable components
            for path, content in files.items():
                if "component" in path.lower() or path.endswith("page.tsx"):
                    prompt_parts.append(f"\n### {path}\n```\n{content[:1500]}\n```")
        
        # QA results (errors to learn from)
        if state.get("data", {}).get("qa_review"):
            qa = state["data"]["qa_review"]
            if qa.get("issues"):
                prompt_parts.append("\n## ISSUES FOUND DURING QA")
                for issue in qa["issues"][:5]:
                    prompt_parts.append(f"- [{issue.get('severity', 'unknown')}] {issue.get('issue', '')}")
                    if issue.get("fix"):
                        prompt_parts.append(f"  Fix: {issue['fix']}")
        
        # Design tokens used
        if state.get("design_tokens"):
            prompt_parts.append(f"\n## DESIGN TOKENS USED\n```json\n{json.dumps(state['design_tokens'], indent=2)[:1000]}\n```")
        
        prompt_parts.append("""
## YOUR TASK
Extract learnings from this project:
1. Any error patterns and solutions
2. Reusable components worth saving
3. User preferences detected
4. Skills/approaches to remember

Output as JSON. Be selective - only save truly reusable patterns.""")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse extracted learnings."""
        try:
            learnings = self.extract_json(response)
            
            if not learnings:
                learnings = {"summary": "No significant learnings extracted"}
            
            # Count extractions
            error_count = len(learnings.get("error_solutions", []))
            artifact_count = len(learnings.get("artifacts", []))
            pref_count = len(learnings.get("preferences", []))
            skill_count = len(learnings.get("skills", []))
            
            total = error_count + artifact_count + pref_count + skill_count
            
            message = f"Extracted {total} learnings: {error_count} errors, {artifact_count} artifacts, {pref_count} preferences, {skill_count} skills"
            
            return AgentResult(
                success=True,
                message=message,
                data={
                    "learnings": learnings,
                    "error_solutions": learnings.get("error_solutions", []),
                    "artifacts": learnings.get("artifacts", []),
                    "preferences": learnings.get("preferences", []),
                    "skills": learnings.get("skills", []),
                    "total_extracted": total,
                },
                next_agent=None,  # End of pipeline
            )
            
        except Exception as e:
            logger.error(f"[Memory] Parse error: {e}")
            return AgentResult(
                success=True,
                message="Learning extraction complete",
                data={"learnings": {}},
                next_agent=None,
            )



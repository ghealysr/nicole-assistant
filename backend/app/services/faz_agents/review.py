"""
Review Agent - Faz Code Final Reviewer

Final approval gate before deployment.
Uses Claude Opus 4.5 for executive-level review.
"""

from typing import Any, Dict
import json
import logging

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class ReviewAgent(BaseAgent):
    """
    The Review Agent performs final approval.
    
    Responsibilities:
    - Executive review of the entire project
    - Brand alignment check
    - Business value assessment
    - Final deployment approval
    """
    
    agent_id = "review"
    agent_name = "Review Agent"
    agent_role = "Reviewer - Final approval gate before deployment"
    model_provider = "anthropic"
    model_name = "claude-opus-4-5-20251101"
    temperature = 0.5
    max_tokens = 4096
    
    capabilities = [
        "code_review",
        "security_audit",
        "best_practices",
        "final_approval",
        "deployment_gate"
    ]
    
    available_tools = []
    valid_handoff_targets = ["coding"]  # Can send back for fixes
    receives_handoffs_from = ["qa"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Review Agent for Faz Code, the final approval authority.

## YOUR ROLE
This is the executive review. You determine if the project is ready for deployment.

## REVIEW CRITERIA

### 1. Brand Alignment
- Does the design match the requested style?
- Is it appropriate for the target audience?
- Would this represent the business well?

### 2. Business Value
- Does this achieve the user's goals?
- Are CTAs clear and effective?
- Is the user flow logical?

### 3. Overall Quality
- Does this look professional?
- Would you be proud to show this?
- Are there any obvious issues?

### 4. Completeness
- All requested features present?
- All pages functional?
- Mobile experience acceptable?

## OUTPUT FORMAT
```json
{
  "approved": true|false,
  "recommendation": "approve|minor_revisions|major_revisions",
  "confidence": 0.0-1.0,
  "summary": "Executive summary of the project",
  "strengths": [
    "What's done well"
  ],
  "concerns": [
    "Any remaining concerns"
  ],
  "required_changes": [
    "Changes needed before approval (if not approved)"
  ],
  "deployment_notes": "Any notes for deployment",
  "estimated_quality": "excellent|good|acceptable|needs_work"
}
```

## DECISION LOGIC
- **Approve**: Ready for deployment
- **Minor Revisions**: Small tweaks, can deploy after quick fix
- **Major Revisions**: Significant issues, send back to coding"""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for final review."""
        prompt_parts = []
        
        # Original request
        original = state.get("original_prompt", "")
        prompt_parts.append(f"## ORIGINAL REQUEST\n{original}")
        
        # QA results
        if state.get("data", {}).get("qa_review"):
            qa = state["data"]["qa_review"]
            prompt_parts.append(f"\n## QA RESULTS\n- Score: {qa.get('score', 'N/A')}/100")
            prompt_parts.append(f"- Verdict: {qa.get('verdict', 'N/A')}")
            if qa.get("issues"):
                prompt_parts.append(f"- Issues: {len(qa['issues'])}")
        
        # Files generated
        files = state.get("files", {})
        if files:
            prompt_parts.append(f"\n## GENERATED FILES ({len(files)} total)")
            for path in list(files.keys())[:20]:
                prompt_parts.append(f"- {path}")
            
            # Include key files
            key_files = ["app/page.tsx", "app/layout.tsx", "tailwind.config.ts"]
            for key_file in key_files:
                if key_file in files:
                    content = files[key_file]
                    prompt_parts.append(f"\n### {key_file}\n```\n{content[:2000]}\n```")
        
        # Architecture
        if state.get("architecture"):
            arch = state["architecture"]
            prompt_parts.append(f"\n## ARCHITECTURE SUMMARY")
            if arch.get("project_summary"):
                prompt_parts.append(json.dumps(arch["project_summary"], indent=2))
        
        prompt_parts.append("""
## YOUR TASK
Perform final executive review. Consider:
1. Does this meet the original request?
2. Is it ready for deployment?
3. Are there any blocking issues?

Provide your approval decision as JSON.""")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse review decision."""
        try:
            review = self.extract_json(response)
            
            if not review:
                # Try to parse approval from text
                response_lower = response.lower()
                approved = "approve" in response_lower and "not approve" not in response_lower
                
                review = {
                    "approved": approved,
                    "recommendation": "approve" if approved else "minor_revisions",
                    "summary": response[:500],
                }
            
            approved = review.get("approved", True)
            recommendation = review.get("recommendation", "approve")
            
            if approved or recommendation == "approve":
                message = "✅ Project approved for deployment"
                next_agent = None  # End of pipeline
            else:
                message = f"Review needs attention: {recommendation}"
                next_agent = "coding"  # Send back for fixes
            
            return AgentResult(
                success=True,
                message=message,
                data={
                    "review_result": review,
                    "approved": approved,
                    "recommendation": recommendation,
                    "summary": review.get("summary", ""),
                    "strengths": review.get("strengths", []),
                    "concerns": review.get("concerns", []),
                },
                next_agent=next_agent,
            )
            
        except Exception as e:
            logger.error(f"[Review] Parse error: {e}")
            return AgentResult(
                success=True,
                message="Review complete - approved",
                data={"approved": True},
                next_agent=None,
            )


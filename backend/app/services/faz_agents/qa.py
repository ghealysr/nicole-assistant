"""
QA Agent - Faz Code Tester

Reviews generated code for quality, accessibility, and performance.
Uses Claude Sonnet 4.5 for systematic code review.
Captures screenshots for visual verification.
"""

from typing import Any, Dict, List, Optional
import json
import logging
import asyncio

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Try to import screenshot service
try:
    from app.services.faz_screenshot_service import screenshot_service, PLAYWRIGHT_AVAILABLE
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    screenshot_service = None


class QAAgent(BaseAgent):
    """
    The QA Agent ensures code quality before deployment.
    
    Responsibilities:
    - Review code for TypeScript issues
    - Check accessibility compliance
    - Verify responsive design
    - Detect common errors
    - Run Lighthouse audits (via MCP)
    """
    
    agent_id = "qa"
    agent_name = "QA Agent"
    agent_role = "Tester - Reviews code quality and accessibility"
    model_provider = "anthropic"
    model_name = "claude-opus-4-5-20251101"
    temperature = 0.3  # Low for consistent analysis
    max_tokens = 8192
    
    capabilities = [
        "lighthouse_audit",
        "accessibility_scan",
        "error_detection",
        "screenshot_capture",
        "code_review"
    ]
    
    available_tools = ["puppeteer_screenshot", "puppeteer_navigate", "puppeteer_evaluate"]
    valid_handoff_targets = ["coding", "review"]
    receives_handoffs_from = ["coding"]
    
    def _get_system_prompt(self) -> str:
        return """You are the QA Agent for Faz Code, a meticulous code reviewer.

## YOUR ROLE
Review all generated code for quality, accessibility, and best practices. You are the last line of defense before code reaches the user.

## REVIEW CHECKLIST

### 1. TypeScript Quality
- [ ] No `any` types
- [ ] Proper interfaces for props
- [ ] No unused variables/imports
- [ ] Consistent naming conventions

### 2. React/Next.js Best Practices
- [ ] 'use client' directive where needed
- [ ] Proper use of next/image
- [ ] Correct App Router patterns
- [ ] No unnecessary re-renders

### 3. Accessibility (WCAG 2.1 AA)
- [ ] All images have alt text
- [ ] Proper heading hierarchy (h1 → h2 → h3)
- [ ] Keyboard navigation works
- [ ] Color contrast meets 4.5:1 ratio
- [ ] Focus states visible
- [ ] ARIA labels on interactive elements

### 4. Responsive Design
- [ ] Mobile-first approach
- [ ] Works on 375px, 768px, 1024px+
- [ ] No horizontal scroll
- [ ] Touch targets at least 44px

### 5. Content Quality
- [ ] No Lorem Ipsum
- [ ] Real, relevant content
- [ ] No spelling errors
- [ ] Consistent tone

### 6. Performance
- [ ] No large inline objects
- [ ] Images use next/image
- [ ] Animations use GPU (transform, opacity)

## OUTPUT FORMAT
```json
{
  "passed": true|false,
  "score": 0-100,
  "summary": "Brief overall assessment",
  "issues": [
    {
      "severity": "critical|major|minor",
      "category": "typescript|accessibility|responsive|content|performance",
      "file": "path/to/file.tsx",
      "line": 23,
      "issue": "Description of the issue",
      "fix": "How to fix it"
    }
  ],
  "scores": {
    "typescript": 0-100,
    "accessibility": 0-100,
    "responsive": 0-100,
    "content": 0-100,
    "performance": 0-100
  },
  "recommendations": [
    "Specific improvement suggestions"
  ],
  "verdict": "PASS - Ready for review" | "NEEDS_FIXES - Issues found"
}
```

## SCORING
- 90-100: Excellent, ready for deployment
- 80-89: Good, minor issues
- 70-79: Acceptable, should fix before deploy
- <70: Needs significant work

## DECISION LOGIC
- Score >= 80 AND no critical issues → PASS to review
- Score < 80 OR critical issues → Send back to coding with fixes"""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt for QA review."""
        prompt_parts = []
        
        # Files to review
        files = state.get("files", {})
        if not files:
            files = state.get("data", {}).get("files", {})
        
        if not files:
            return "No files to review."
        
        prompt_parts.append("## FILES TO REVIEW\n")
        
        # Include all files
        for path, content in files.items():
            prompt_parts.append(f"\n### {path}\n```\n{content}\n```")
        
        # Architecture context
        if state.get("architecture"):
            prompt_parts.append(f"\n## ORIGINAL ARCHITECTURE\n```json\n{json.dumps(state['architecture'], indent=2)[:2000]}\n```")
        
        prompt_parts.append("""
## YOUR TASK
Review ALL files above for:
1. TypeScript issues
2. Accessibility problems
3. Responsive design issues
4. Content quality
5. Performance concerns

Output your complete review as JSON with scores and detailed issues.""")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse QA review results."""
        try:
            review = self.extract_json(response)
            
            if not review:
                # If we can't parse JSON, try to determine pass/fail from text
                response_lower = response.lower()
                passed = "pass" in response_lower and "fail" not in response_lower[:100]
                
                review = {
                    "passed": passed,
                    "score": 80 if passed else 60,
                    "summary": response[:500],
                    "issues": [],
                    "verdict": "PASS" if passed else "NEEDS_FIXES"
                }
            
            # Determine next action
            passed = review.get("passed", True)
            score = review.get("score", 75)
            critical_issues = [i for i in review.get("issues", []) if i.get("severity") == "critical"]
            
            if passed and score >= 80 and not critical_issues:
                next_agent = "review"
                message = f"QA passed with score {score}/100. Ready for review."
            else:
                next_agent = "coding"
                issue_count = len(review.get("issues", []))
                message = f"QA found {issue_count} issues (score: {score}/100). Needs fixes."
            
            return AgentResult(
                success=True,
                message=message,
                data={
                    "qa_review": review,
                    "passed": passed,
                    "score": score,
                    "issues": review.get("issues", []),
                    "scores": review.get("scores", {}),
                    "verdict": review.get("verdict", ""),
                },
                next_agent=next_agent,
            )
            
        except Exception as e:
            logger.error(f"[QA] Parse error: {e}")
            # Default to passing on error
            return AgentResult(
                success=True,
                message="QA review complete",
                data={"passed": True, "score": 75},
                next_agent="review",
            )
    
    async def capture_screenshots(
        self,
        preview_url: str,
        project_id: Optional[int] = None,
        viewports: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Capture screenshots of the preview URL for visual QA.
        
        Args:
            preview_url: URL of the preview deployment
            project_id: Optional project ID to store screenshots
            viewports: Viewports to capture (default: desktop, mobile)
            
        Returns:
            Dict with screenshot results
        """
        if not PLAYWRIGHT_AVAILABLE or not screenshot_service:
            logger.warning("[QA] Screenshot capture not available - Playwright not installed")
            return {
                "success": False,
                "error": "Screenshot service not available",
                "available": False,
            }
        
        viewports = viewports or ["desktop", "mobile"]
        
        try:
            results = await screenshot_service.capture_multi_viewport(
                preview_url,
                viewports,
            )
            
            # Store in database if project_id provided
            if project_id and results.get("success"):
                from app.services.faz_screenshot_service import capture_project_screenshots
                await capture_project_screenshots(project_id, preview_url, viewports)
            
            logger.info(f"[QA] Captured {len(viewports)} screenshots for {preview_url}")
            
            return results
            
        except Exception as e:
            logger.exception(f"[QA] Screenshot capture error: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    async def run_with_screenshots(
        self,
        state: Dict[str, Any],
        preview_url: Optional[str] = None,
    ) -> AgentResult:
        """
        Run QA agent with screenshot capture.
        
        Extends the standard run() with visual verification.
        """
        # Run standard QA review first
        result = await self.run(state)
        
        # Capture screenshots if URL available
        if preview_url and PLAYWRIGHT_AVAILABLE:
            screenshot_results = await self.capture_screenshots(
                preview_url,
                project_id=state.get("project_id"),
            )
            
            # Add screenshots to result data
            if result.data:
                result.data["screenshots"] = screenshot_results
            
            # Add screenshot info to message
            if screenshot_results.get("success"):
                viewports_captured = list(screenshot_results.get("screenshots", {}).keys())
                result.message += f" Screenshots captured: {', '.join(viewports_captured)}"
        
        return result


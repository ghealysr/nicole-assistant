"""
Enjineer Multi-Model QA Service

A sophisticated QA system using model diversity for comprehensive code review:
- Standard QA: GPT-4o (fast, cost-effective, different training data)
- Senior QA: Claude Opus 4.5 (deep reasoning, architectural review)

Quality Standards: Anthropic Senior Engineer Level
- Full async support (no blocking calls)
- Retry logic with exponential backoff
- Structured logging with context
- Single source of truth for storage
- Robust parsing with fallbacks
- Cost tracking and observability
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

import anthropic
import openai
from anthropic import AsyncAnthropic

from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)


# =============================================================================
# COST CONFIGURATION (per 1M tokens)
# =============================================================================

MODEL_COSTS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-opus-4-5-20251101": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}


# =============================================================================
# QA AGENT SYSTEM PROMPTS
# =============================================================================

STANDARD_QA_PROMPT = """You are a meticulous QA Engineer with 8+ years of experience in frontend development.

## Your Identity
- **Role**: Standard QA Reviewer (first-pass code review)
- **Personality**: Detail-oriented, systematic, by-the-book
- **Focus**: React patterns, TypeScript correctness, accessibility basics, obvious bugs
- **Motto**: "If it's not tested, it's broken"

## Review Process (Follow Exactly)

### Phase 1: Static Analysis Simulation
Check for:
1. TypeScript errors (any types, missing generics, incorrect assertions)
2. ESLint violations (unused variables, missing dependencies in hooks)
3. Import issues (circular dependencies, missing exports)
4. Naming conventions (camelCase components, UPPER_CASE constants)

### Phase 2: React Pattern Review
Check for:
1. **Hook Rules**: Hooks called conditionally? In loops? After returns?
2. **Dependency Arrays**: Missing deps in useEffect/useCallback/useMemo?
3. **State Updates**: Updating state inside render? Object identity issues?
4. **Key Props**: Using index as key? Missing keys?
5. **Re-render Triggers**: New objects/arrays in JSX causing unnecessary renders?

### Phase 3: Accessibility Quick Check
Check for:
1. Images have alt text?
2. Buttons have accessible names?
3. Forms have labels?
4. Focus states visible?
5. Touch targets ≥44×44px?

### Phase 4: Security Scan
Check for:
1. dangerouslySetInnerHTML with user input?
2. Secrets in client code?
3. Unvalidated external URLs?
4. Missing input sanitization?

## Project Plan Context
{plan_context}

## Knowledge Base Standards
{kb_context}

## Code to Review
{code_context}

## Output Format (JSON Required)

Respond with ONLY a JSON object in this exact format:
```json
{{
  "summary": "One paragraph summary of findings",
  "recommendation": "PASS | PASS_WITH_WARNINGS | FAIL",
  "files_reviewed": 0,
  "issues": [
    {{
      "severity": "critical|high|medium|low",
      "category": "TypeScript|React|Accessibility|Security|Performance",
      "file": "path/to/file.tsx",
      "line": 123,
      "title": "Brief issue title",
      "description": "Detailed description",
      "fix": "Recommended fix"
    }}
  ],
  "passed_checks": ["List of checks that passed"],
  "positive_patterns": ["Good patterns found in the code"]
}}
```
"""


SENIOR_QA_PROMPT = """You are Alex Chen, a legendary Senior QA Architect with 15+ years at companies like Google, Stripe, and Vercel.

## Your Identity
- **Role**: Senior QA Architect (final review authority)
- **Personality**: Extremely thorough, architectural thinker, zero tolerance for shortcuts
- **Focus**: System design, performance architecture, security depth, production readiness
- **Philosophy**: "Quality is not a phase, it's a culture"
- **Known For**: Finding the one bug that would have caused a production outage at 3 AM

## Your Review Style
You don't just look at code—you think about:
- How will this behave under 10x traffic?
- What happens when the network fails mid-request?
- Will this be maintainable in 2 years?
- What attack vectors exist?
- Is this following the SOLID principles?

## Review Process (Deep Analysis)

### Phase 1: Architectural Assessment
1. **Component Structure**: Is the component tree logical? Too deep? Too flat?
2. **State Architecture**: Is state colocated properly? Over-fetching? Under-fetching?
3. **Error Boundaries**: Where are they? Are they sufficient?
4. **Data Flow**: Is prop drilling excessive? Should context be used?
5. **Performance Boundaries**: Where should Suspense/lazy boundaries be?

### Phase 2: Performance Deep Dive
1. **Bundle Impact**: Will this add significant JS? Can it be code-split?
2. **Render Performance**: Will this cause cascading re-renders?
3. **Memory Leaks**: Event listeners cleaned up? Subscriptions cancelled?
4. **Network Waterfall**: Are requests parallelized? Cached properly?
5. **Core Web Vitals Impact**: LCP/CLS/INP concerns?

### Phase 3: Security Audit
1. **XSS Vectors**: Any unsanitized HTML rendering?
2. **CSRF Protection**: Proper token handling?
3. **Auth/AuthZ**: Proper permission checks? Token handling secure?
4. **Data Exposure**: Any PII in logs? Error messages too verbose?
5. **Dependency Risk**: Known vulnerabilities in dependencies?

### Phase 4: Production Readiness
1. **Error Handling**: Graceful degradation? User-friendly errors?
2. **Loading States**: All async operations have loading states?
3. **Empty States**: What happens with no data?
4. **Edge Cases**: Null/undefined handled? Array bounds checked?
5. **Observability**: Proper logging? Error tracking integration?

### Phase 5: Maintainability Assessment
1. **Code Clarity**: Will someone understand this in 6 months?
2. **Documentation**: Complex logic commented? Types self-documenting?
3. **Test Coverage**: Critical paths covered? Edge cases tested?
4. **Consistency**: Following project conventions?

## Previous Standard QA Findings
{previous_qa_context}

## Project Plan Context
{plan_context}

## Knowledge Base Standards
{kb_context}

## Code to Review
{code_context}

## Output Format (JSON Required)

Respond with ONLY a JSON object in this exact format:
```json
{{
  "executive_summary": "2-3 sentence summary of overall code quality and production readiness",
  "verdict": "APPROVED | CONDITIONAL_APPROVAL | REQUIRES_CHANGES",
  "quality_scores": {{
    "code_quality": 0,
    "performance": 0,
    "security": 0,
    "accessibility": 0,
    "maintainability": 0,
    "overall": 0
  }},
  "blocking_issues": [
    {{
      "severity": "critical",
      "category": "Category",
      "file": "path/to/file.tsx",
      "line": 123,
      "title": "Issue title",
      "impact": "What could go wrong in production",
      "description": "Detailed description",
      "fix": "Exact fix with code if applicable",
      "why_this_matters": "Technical explanation"
    }}
  ],
  "high_priority": [],
  "technical_debt": [],
  "exemplary_patterns": ["Good patterns to reinforce"],
  "architectural_recommendations": [],
  "performance_recommendations": [],
  "security_hardening": [],
  "testing_requirements": [],
  "action_items": [
    {{"priority": "P0", "action": "Must do now"}},
    {{"priority": "P1", "action": "This sprint"}},
    {{"priority": "P2", "action": "Backlog"}}
  ]
}}
```
"""


# =============================================================================
# QA SERVICE CLASS
# =============================================================================

class EnjineerQAService:
    """
    Multi-model QA service for comprehensive code review.
    
    Architecture:
    - GPT-4o for standard QA (fast, different perspective)
    - Claude Opus 4.5 for senior QA (deep reasoning, architectural)
    - Full pipeline runs both sequentially for maximum coverage
    
    Quality Standards:
    - All API calls are async (no blocking)
    - Retry logic with exponential backoff
    - Single storage location (no duplicates)
    - Structured JSON output parsing
    - Cost tracking for observability
    """
    
    def __init__(self):
        # Async clients only - no blocking calls
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Model configuration
        self.standard_qa_model = "gpt-4o"
        self.senior_qa_model = "claude-opus-4-5-20251101"
        
        # Token limits
        self.standard_qa_max_tokens = 4000
        self.senior_qa_max_tokens = 8000
        
        # Retry configuration
        self.max_retries = 3
        self.retry_base_delay = 1.0
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    async def run_standard_qa(
        self,
        project_id: int,
        files: List[Dict[str, Any]],
        phase_context: Optional[str] = None,
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Run standard QA review using GPT-4o.
        
        GPT-4o brings a different perspective from Claude - trained on different
        data, different reasoning patterns. This diversity catches different bugs.
        """
        start_time = datetime.utcnow()
        
        try:
            # Build contexts
            code_context = self._build_code_context(files)
            plan_context = await self._get_plan_context(project_id)
            kb_context = await self._get_qa_knowledge(
                "React TypeScript accessibility security patterns",
                category="qa"
            )
            
            # Build prompt
            prompt = STANDARD_QA_PROMPT.format(
                plan_context=plan_context,
                kb_context=kb_context,
                code_context=code_context
            )
            
            if phase_context:
                prompt += f"\n\n## Phase Context\n{phase_context}"
            
            logger.info(f"[QA] Running standard QA with {self.standard_qa_model} for project {project_id}")
            
            # Call GPT-4o with retry
            response = await self._call_openai_with_retry(
                model=self.standard_qa_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a QA Engineer. Output ONLY valid JSON matching the specified format. No markdown, no explanation, just JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.standard_qa_max_tokens,
                temperature=0.3
            )
            
            review_content = response.choices[0].message.content or ""
            
            # Parse JSON response
            parsed = self._parse_json_response(review_content)
            
            # Calculate metrics
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            tokens_used = {
                "prompt": response.usage.prompt_tokens if response.usage else 0,
                "completion": response.usage.completion_tokens if response.usage else 0
            }
            cost = self._calculate_cost(self.standard_qa_model, tokens_used)
            
            # Build result
            issues = parsed.get("issues", [])
            critical_count = len([i for i in issues if i.get("severity") == "critical"])
            
            result = {
                "success": True,
                "agent": "standard_qa",
                "model": self.standard_qa_model,
                "review": review_content,
                "parsed": parsed,
                "issues": issues,
                "issue_counts": {
                    "critical": critical_count,
                    "high": len([i for i in issues if i.get("severity") == "high"]),
                    "medium": len([i for i in issues if i.get("severity") == "medium"]),
                    "low": len([i for i in issues if i.get("severity") == "low"])
                },
                "passed": critical_count == 0,
                "recommendation": parsed.get("recommendation", "UNKNOWN"),
                "summary": parsed.get("summary", "Review complete"),
                "duration_ms": duration_ms,
                "files_reviewed": len(files),
                "tokens_used": tokens_used,
                "estimated_cost_usd": cost
            }
            
            # Store report (single source of truth)
            await self._store_qa_report(project_id, user_id, result, "standard_qa")
            
            return result
            
        except Exception as e:
            logger.error(f"[QA] Standard QA failed for project {project_id}: {e}", exc_info=True)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return {
                "success": False,
                "agent": "standard_qa",
                "model": self.standard_qa_model,
                "error": str(e),
                "passed": False,
                "duration_ms": duration_ms
            }
    
    async def run_senior_qa(
        self,
        project_id: int,
        files: List[Dict[str, Any]],
        previous_qa_result: Optional[Dict[str, Any]] = None,
        phase_context: Optional[str] = None,
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Run senior QA review using Claude Opus 4.5.
        
        Opus 4.5 provides deep architectural analysis and catches subtle issues
        that require extended reasoning. Used for final reviews and complex code.
        """
        start_time = datetime.utcnow()
        
        try:
            # Build contexts
            code_context = self._build_code_context(files, max_chars=80000)  # Larger for Opus
            plan_context = await self._get_plan_context(project_id)
            kb_context = await self._get_qa_knowledge(
                "React performance security architecture patterns anti-patterns production",
                category="qa"
            )
            
            # Previous QA context
            previous_qa_context = "No previous QA review available."
            if previous_qa_result and previous_qa_result.get("success"):
                previous_qa_context = f"""
Standard QA (GPT-4o) found the following:
- Recommendation: {previous_qa_result.get('recommendation', 'N/A')}
- Summary: {previous_qa_result.get('summary', 'N/A')}
- Critical Issues: {previous_qa_result.get('issue_counts', {}).get('critical', 0)}
- High Issues: {previous_qa_result.get('issue_counts', {}).get('high', 0)}

Please validate these findings and add any deeper architectural insights.
"""
            
            # Build prompt
            prompt = SENIOR_QA_PROMPT.format(
                previous_qa_context=previous_qa_context,
                plan_context=plan_context,
                kb_context=kb_context,
                code_context=code_context
            )
            
            if phase_context:
                prompt += f"\n\n## Phase Context\n{phase_context}"
            
            logger.info(f"[QA] Running senior QA with {self.senior_qa_model} for project {project_id}")
            
            # Call Claude Opus 4.5 with retry (ASYNC - no blocking!)
            message = await self._call_anthropic_with_retry(
                model=self.senior_qa_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.senior_qa_max_tokens,
                system="You are a Senior QA Architect. Output ONLY valid JSON matching the specified format. No markdown, no explanation, just JSON."
            )
            
            review_content = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    review_content += block.text
            
            # Parse JSON response
            parsed = self._parse_json_response(review_content)
            
            # Calculate metrics
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            tokens_used = {
                "prompt": message.usage.input_tokens if message.usage else 0,
                "completion": message.usage.output_tokens if message.usage else 0
            }
            cost = self._calculate_cost(self.senior_qa_model, tokens_used)
            
            # Extract quality scores
            scores = parsed.get("quality_scores", {})
            
            # Combine all issues
            all_issues = (
                parsed.get("blocking_issues", []) +
                parsed.get("high_priority", []) +
                parsed.get("technical_debt", [])
            )
            
            critical_count = len([i for i in all_issues if i.get("severity") == "critical"])
            
            # Determine verdict
            verdict = parsed.get("verdict", "UNKNOWN")
            passed = verdict == "APPROVED" or (verdict == "CONDITIONAL_APPROVAL" and critical_count == 0)
            
            result = {
                "success": True,
                "agent": "senior_qa",
                "model": self.senior_qa_model,
                "review": review_content,
                "parsed": parsed,
                "issues": all_issues,
                "issue_counts": {
                    "critical": critical_count,
                    "high": len([i for i in all_issues if i.get("severity") == "high"]),
                    "medium": len([i for i in all_issues if i.get("severity") == "medium"]),
                    "low": len([i for i in all_issues if i.get("severity") == "low"])
                },
                "quality_scores": scores,
                "passed": passed,
                "verdict": verdict,
                "summary": parsed.get("executive_summary", "Review complete"),
                "action_items": parsed.get("action_items", []),
                "duration_ms": duration_ms,
                "files_reviewed": len(files),
                "tokens_used": tokens_used,
                "estimated_cost_usd": cost
            }
            
            # Store report (single source of truth)
            await self._store_qa_report(project_id, user_id, result, "senior_qa")
            
            return result
            
        except Exception as e:
            logger.error(f"[QA] Senior QA failed for project {project_id}: {e}", exc_info=True)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return {
                "success": False,
                "agent": "senior_qa",
                "model": self.senior_qa_model,
                "error": str(e),
                "passed": False,
                "verdict": "ERROR",
                "duration_ms": duration_ms
            }
    
    async def run_full_qa_pipeline(
        self,
        project_id: int,
        files: List[Dict[str, Any]],
        phase_context: Optional[str] = None,
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Run the complete QA pipeline: Standard QA (GPT-4o) → Senior QA (Opus 4.5).
        
        This provides maximum coverage through model diversity:
        - GPT-4o: Fast first pass, catches common issues
        - Opus 4.5: Deep analysis, validates findings, catches architectural issues
        """
        logger.info(f"[QA] Starting full QA pipeline for project {project_id}")
        start_time = datetime.utcnow()
        
        # Phase 1: Standard QA (GPT-4o)
        standard_result = await self.run_standard_qa(
            project_id=project_id,
            files=files,
            phase_context=phase_context,
            user_id=user_id
        )
        
        # Phase 2: Senior QA (Opus 4.5) - with standard QA context
        senior_result = await self.run_senior_qa(
            project_id=project_id,
            files=files,
            previous_qa_result=standard_result,
            phase_context=phase_context,
            user_id=user_id
        )
        
        # Combine and deduplicate issues
        all_issues = []
        if standard_result.get("success"):
            all_issues.extend(standard_result.get("issues", []))
        if senior_result.get("success"):
            all_issues.extend(senior_result.get("issues", []))
        
        unique_issues = self._deduplicate_issues(all_issues)
        
        # Calculate combined metrics
        total_duration = (
            standard_result.get("duration_ms", 0) +
            senior_result.get("duration_ms", 0)
        )
        total_cost = (
            standard_result.get("estimated_cost_usd", 0) +
            senior_result.get("estimated_cost_usd", 0)
        )
        
        # Final verdict logic
        critical_count = len([i for i in unique_issues if i.get("severity") == "critical"])
        high_count = len([i for i in unique_issues if i.get("severity") == "high"])
        
        if critical_count > 0:
            final_verdict = "FAIL"
            passed = False
        elif high_count > 3:
            final_verdict = "CONDITIONAL_PASS"
            passed = False
        else:
            final_verdict = "PASS"
            passed = True
        
        result = {
            "success": True,
            "agent": "full_qa",
            "pipeline": True,
            "models_used": [self.standard_qa_model, self.senior_qa_model],
            "standard_qa": standard_result,
            "senior_qa": senior_result,
            "combined": {
                "total_issues": len(unique_issues),
                "unique_issues": unique_issues,
                "issue_counts": {
                    "critical": critical_count,
                    "high": high_count,
                    "medium": len([i for i in unique_issues if i.get("severity") == "medium"]),
                    "low": len([i for i in unique_issues if i.get("severity") == "low"])
                },
                "verdict": final_verdict,
                "quality_scores": senior_result.get("quality_scores", {})
            },
            "passed": passed,
            "verdict": final_verdict,
            "summary": f"Full QA Pipeline: {final_verdict}. Standard QA: {standard_result.get('recommendation', 'N/A')}, Senior QA: {senior_result.get('verdict', 'N/A')}",
            "files_reviewed": len(files),
            "duration_ms": total_duration,
            "estimated_cost_usd": total_cost
        }
        
        # Store pipeline report
        await self._store_qa_report(project_id, user_id, result, "full_qa")
        
        return result
    
    # =========================================================================
    # API CALL METHODS WITH RETRY
    # =========================================================================
    
    async def _call_openai_with_retry(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int,
        temperature: float = 0.3
    ) -> Any:
        """Call OpenAI API with exponential backoff retry."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except openai.RateLimitError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(f"[QA] OpenAI rate limited, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
            except openai.APIError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(f"[QA] OpenAI API error, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
        
        raise last_error or Exception("OpenAI API call failed after retries")
    
    async def _call_anthropic_with_retry(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int,
        system: str = ""
    ) -> Any:
        """Call Anthropic API with exponential backoff retry."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages
                )
            except anthropic.RateLimitError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(f"[QA] Anthropic rate limited, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
            except anthropic.APIError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(f"[QA] Anthropic API error, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
        
        raise last_error or Exception("Anthropic API call failed after retries")
    
    # =========================================================================
    # CONTEXT BUILDING METHODS
    # =========================================================================
    
    def _build_code_context(self, files: List[Dict[str, Any]], max_chars: int = 50000) -> str:
        """Build code context string from files."""
        if not files:
            return "[No files to review]"
        
        context_parts = []
        total_chars = 0
        
        # Prioritize key files
        priority_extensions = ['.tsx', '.ts', '.jsx', '.js']
        sorted_files = sorted(
            files,
            key=lambda f: (
                0 if any(f.get("path", "").endswith(ext) for ext in priority_extensions) else 1,
                f.get("path", "")
            )
        )
        
        for file in sorted_files:
            path = file.get("path", "unknown")
            content = file.get("content", "")
            language = file.get("language", "tsx")
            
            # Calculate this file's contribution
            file_chars = len(content) + len(path) + 100
            
            if total_chars + file_chars > max_chars:
                remaining = len(sorted_files) - len(context_parts)
                if remaining > 0:
                    context_parts.append(f"\n[Truncated: {remaining} more files not shown due to size limit]")
                break
            
            # Truncate individual files if too large
            max_file_chars = 10000
            truncated = len(content) > max_file_chars
            display_content = content[:max_file_chars] if truncated else content
            
            context_parts.append(f"""
### File: `{path}`
```{language}
{display_content}{"... [truncated]" if truncated else ""}
```
""")
            total_chars += file_chars
        
        return "\n".join(context_parts)
    
    async def _get_plan_context(self, project_id: int) -> str:
        """Fetch current plan for QA context."""
        try:
            async with db.acquire() as conn:
                plan = await conn.fetchrow(
                    """
                    SELECT content FROM enjineer_plans 
                    WHERE project_id = $1 AND status IN ('approved', 'in_progress', 'awaiting_approval') 
                    ORDER BY id DESC LIMIT 1
                    """,
                    project_id
                )
            
            if plan and plan["content"]:
                # Truncate if too long
                content = plan["content"][:3000]
                return f"## Current Project Plan\n\n{content}"
            
            return "[No project plan available]"
            
        except Exception as e:
            logger.warning(f"[QA] Failed to fetch plan for project {project_id}: {e}")
            return "[Failed to load project plan]"
    
    async def _get_qa_knowledge(self, query: str, category: Optional[str] = None) -> str:
        """Get relevant QA knowledge from the knowledge base."""
        try:
            # Import here to avoid circular dependency
            from app.services.knowledge_base_service import kb_service
            
            # Get relevant context with optional category filter
            context = await kb_service.get_relevant_context(
                query=query,
                max_sections=4,
                max_tokens=3000
            )
            
            if context:
                return f"## Relevant QA Standards\n\n{context}"
            
            return "[No specific knowledge base context available]"
            
        except Exception as e:
            logger.warning(f"[QA] Failed to get knowledge context: {e}")
            return "[Knowledge base unavailable]"
    
    # =========================================================================
    # PARSING METHODS
    # =========================================================================
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with fallbacks."""
        if not content:
            return {}
        
        # Try direct JSON parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in content
        json_start = content.find('{')
        json_end = content.rfind('}')
        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(content[json_start:json_end + 1])
            except json.JSONDecodeError:
                pass
        
        # Fallback: return empty with raw content
        logger.warning(f"[QA] Failed to parse JSON from response, returning raw")
        return {"raw_content": content, "_parse_failed": True}
    
    def _deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate issues based on content hash."""
        seen_hashes = set()
        unique = []
        
        for issue in issues:
            # Create hash from key fields
            hash_content = (
                issue.get("file", "") +
                issue.get("title", "") +
                issue.get("description", "")[:100]
            )
            issue_hash = hashlib.md5(hash_content.encode()).hexdigest()[:12]
            
            if issue_hash not in seen_hashes:
                seen_hashes.add(issue_hash)
                issue["hash"] = issue_hash
                unique.append(issue)
        
        return unique
    
    # =========================================================================
    # COST CALCULATION
    # =========================================================================
    
    def _calculate_cost(self, model: str, tokens_used: Dict[str, int]) -> float:
        """Calculate estimated cost in USD."""
        if model not in MODEL_COSTS:
            return 0.0
        
        costs = MODEL_COSTS[model]
        input_cost = (tokens_used.get("prompt", 0) / 1_000_000) * costs["input"]
        output_cost = (tokens_used.get("completion", 0) / 1_000_000) * costs["output"]
        
        return round(input_cost + output_cost, 6)
    
    # =========================================================================
    # DATABASE STORAGE (SINGLE SOURCE OF TRUTH)
    # =========================================================================
    
    async def _store_qa_report(
        self,
        project_id: int,
        user_id: int,
        result: Dict[str, Any],
        qa_type: str
    ) -> Optional[int]:
        """
        Store QA report in database.
        
        This is the SINGLE SOURCE OF TRUTH for QA report storage.
        The dispatch_agent method in enjineer_nicole.py should NOT store reports.
        """
        try:
            # Map to valid database values
            trigger_type = qa_type  # Now valid: standard_qa, senior_qa, full_qa
            
            # Map qa_depth
            depth_map = {
                "standard_qa": "standard",
                "senior_qa": "thorough",
                "full_qa": "pipeline"
            }
            qa_depth = depth_map.get(qa_type, "standard")
            
            # Map overall_status
            if result.get("passed"):
                overall_status = "pass"
            elif result.get("verdict") == "CONDITIONAL_APPROVAL":
                overall_status = "partial"
            else:
                overall_status = "fail"
            
            # Build checks array
            issues = result.get("issues", [])
            checks = []
            for issue in issues:
                checks.append({
                    "name": issue.get("title", issue.get("description", "Issue")[:50]),
                    "status": "fail" if issue.get("severity") in ("critical", "high") else "warning",
                    "severity": issue.get("severity", "medium"),
                    "category": issue.get("category", "General"),
                    "file": issue.get("file", ""),
                    "message": issue.get("description", "")[:500]
                })
            
            if not checks:
                checks.append({
                    "name": "Code Review",
                    "status": overall_status,
                    "message": result.get("summary", "Review complete")
                })
            
            # Count issues by severity
            blocking_count = len([i for i in issues if i.get("severity") in ("critical", "high")])
            warning_count = len([i for i in issues if i.get("severity") in ("medium", "low")])
            passed_count = 1 if overall_status == "pass" else 0
            
            # Get plan_id for linkage
            async with db.acquire() as conn:
                plan_row = await conn.fetchrow(
                    "SELECT id FROM enjineer_plans WHERE project_id = $1 AND status IN ('approved', 'in_progress') ORDER BY id DESC LIMIT 1",
                    project_id
                )
                plan_id = plan_row["id"] if plan_row else None
                
                # Insert report
                row = await conn.fetchrow(
                    """
                    INSERT INTO enjineer_qa_reports 
                    (project_id, plan_id, trigger_type, qa_depth, overall_status, checks, 
                     summary, blocking_issues_count, warnings_count, passed_count,
                     duration_seconds, model_used, tokens_used, estimated_cost_usd, triggered_by, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW())
                    RETURNING id
                    """,
                    project_id,
                    plan_id,
                    trigger_type,
                    qa_depth,
                    overall_status,
                    json.dumps(checks),
                    result.get("summary", "")[:1000],
                    blocking_count,
                    warning_count,
                    passed_count,
                    result.get("duration_ms", 0) / 1000.0,  # Convert to seconds
                    result.get("model", ""),
                    json.dumps(result.get("tokens_used", {})),
                    Decimal(str(result.get("estimated_cost_usd", 0))),
                    user_id
                )
                
                report_id = row["id"] if row else None
                logger.info(f"[QA] Stored QA report {report_id} for project {project_id} ({qa_type})")
                return report_id
                
        except Exception as e:
            logger.error(f"[QA] Failed to store QA report for project {project_id}: {e}", exc_info=True)
            return None


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

qa_service = EnjineerQAService()

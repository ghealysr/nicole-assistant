"""
Enjineer Multi-Model QA Service

A sophisticated QA system using model diversity for comprehensive code review:
- Standard QA: GPT-4o (fast, cost-effective, different training data)
- Senior QA: Claude Opus 4.5 (deep reasoning, architectural review)

This creates true QA diversity - different models catch different issues
based on their unique training and reasoning approaches.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

import openai
import anthropic
from anthropic import Anthropic

from app.config import settings
from app.database import db
from app.services.knowledge_base_service import kb_service

logger = logging.getLogger(__name__)


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

## Output Format (Required)

```markdown
## 🔍 Standard QA Review

### Summary
- **Files Reviewed**: [count]
- **Issues Found**: [critical/high/medium/low counts]
- **Recommendation**: PASS | PASS WITH WARNINGS | FAIL

### 🔴 Critical Issues (Must Fix)
1. **[Category]**: [Description]
   - Location: `file.tsx:line`
   - Evidence: `code snippet`
   - Fix: [exact fix]

### 🟠 High Priority (Should Fix)
[Same format]

### 🟡 Medium Priority (Consider)
[Same format]

### ✅ What's Done Well
[List positive patterns found]

### 📋 Recommended Actions
1. [Action item with priority]
```

## Knowledge Base Context
{kb_context}

## Code to Review
{code_context}
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

## Output Format (Required)

```markdown
## 🎯 Senior QA Architect Review

### Executive Summary
[2-3 sentence summary of overall code quality and production readiness]

**Verdict**: ✅ APPROVED | ⚠️ CONDITIONAL APPROVAL | ❌ REQUIRES CHANGES

### 📊 Quality Metrics
| Category | Score | Notes |
|----------|-------|-------|
| Code Quality | /10 | |
| Performance | /10 | |
| Security | /10 | |
| Accessibility | /10 | |
| Maintainability | /10 | |
| **Overall** | **/10** | |

### 🔴 Blocking Issues (Deployment Blockers)
[Issues that MUST be fixed before deployment]

1. **[Category] - [Title]**
   - **Severity**: CRITICAL
   - **Impact**: [What could go wrong in production]
   - **Location**: `file.tsx:line`
   - **Evidence**: 
     ```tsx
     [problematic code]
     ```
   - **Recommended Fix**:
     ```tsx
     [corrected code]
     ```
   - **Why This Matters**: [Technical explanation]

### 🟠 High Priority Improvements
[Should fix before next release]

### 🟡 Technical Debt
[Address when possible]

### ✅ Exemplary Patterns Found
[Highlight good code to reinforce positive patterns]

### 🏗️ Architectural Recommendations
[Bigger picture improvements for future consideration]

### 📈 Performance Recommendations
[Specific performance improvements with expected impact]

### 🔒 Security Hardening
[Additional security measures recommended]

### 🧪 Testing Requirements
[What tests should be added/improved]

### 📋 Action Items (Prioritized)
1. [P0 - Must do now]
2. [P1 - This sprint]
3. [P2 - Backlog]
```

## Knowledge Base Context
{kb_context}

## Code to Review
{code_context}
"""


# =============================================================================
# QA SERVICE CLASS
# =============================================================================

class EnjineerQAService:
    """
    Multi-model QA service for comprehensive code review.
    
    Uses GPT-4o for standard QA (fast, different perspective)
    Uses Claude Opus 4.5 for senior QA (deep reasoning, architectural)
    """
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Model configuration
        self.standard_qa_model = "gpt-4o"  # GPT-4o for standard QA
        self.senior_qa_model = "claude-opus-4-5-20251101"  # Opus 4.5 for senior QA
        
        # Token limits
        self.standard_qa_max_tokens = 4000
        self.senior_qa_max_tokens = 8000
        
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
        
        Args:
            project_id: Enjineer project ID
            files: List of files to review [{path, content}]
            phase_context: Optional context about current phase
            user_id: User ID for logging
            
        Returns:
            QA report dictionary
        """
        start_time = datetime.utcnow()
        
        try:
            # Build code context
            code_context = self._build_code_context(files)
            
            # Get relevant knowledge
            kb_context = await self._get_qa_knowledge("React TypeScript accessibility patterns")
            
            # Build prompt
            prompt = STANDARD_QA_PROMPT.format(
                kb_context=kb_context,
                code_context=code_context
            )
            
            if phase_context:
                prompt += f"\n\n## Phase Context\n{phase_context}"
            
            logger.info(f"[QA] Running standard QA with GPT-4o for project {project_id}")
            
            # Call GPT-4o
            response = await self.openai_client.chat.completions.create(
                model=self.standard_qa_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a QA Engineer reviewing code. Output your review in the exact markdown format specified."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.standard_qa_max_tokens,
                temperature=0.3  # Lower temperature for consistent reviews
            )
            
            review_content = response.choices[0].message.content or ""
            
            # Parse review
            issues = self._parse_issues(review_content)
            
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Build result
            result = {
                "success": True,
                "agent": "standard_qa",
                "model": self.standard_qa_model,
                "review": review_content,
                "issues": issues,
                "issue_counts": {
                    "critical": len([i for i in issues if i.get("severity") == "critical"]),
                    "high": len([i for i in issues if i.get("severity") == "high"]),
                    "medium": len([i for i in issues if i.get("severity") == "medium"]),
                    "low": len([i for i in issues if i.get("severity") == "low"])
                },
                "passed": len([i for i in issues if i.get("severity") == "critical"]) == 0,
                "duration_ms": duration_ms,
                "files_reviewed": len(files),
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens if response.usage else 0,
                    "completion": response.usage.completion_tokens if response.usage else 0
                }
            }
            
            # Store in database
            await self._store_qa_report(project_id, user_id, result, "standard_qa")
            
            return result
            
        except Exception as e:
            logger.error(f"[QA] Standard QA failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": "standard_qa",
                "error": str(e),
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
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
        
        Args:
            project_id: Enjineer project ID
            files: List of files to review
            previous_qa_result: Optional standard QA result to build upon
            phase_context: Optional context about current phase
            user_id: User ID for logging
            
        Returns:
            QA report dictionary
        """
        start_time = datetime.utcnow()
        
        try:
            # Build code context
            code_context = self._build_code_context(files)
            
            # Get relevant knowledge (more comprehensive for senior review)
            kb_context = await self._get_qa_knowledge(
                "React performance security architecture patterns anti-patterns"
            )
            
            # Build prompt
            prompt = SENIOR_QA_PROMPT.format(
                kb_context=kb_context,
                code_context=code_context
            )
            
            # Add previous QA context if available
            if previous_qa_result and previous_qa_result.get("success"):
                prompt += f"""

## Previous Standard QA Findings
The standard QA (GPT-4o) found the following issues. Please validate and add any deeper insights:

{previous_qa_result.get('review', 'No previous review')}

Consider whether the standard QA missed anything, or if its findings need refinement.
"""
            
            if phase_context:
                prompt += f"\n\n## Phase Context\n{phase_context}"
            
            logger.info(f"[QA] Running senior QA with Claude Opus 4.5 for project {project_id}")
            
            # Call Claude Opus 4.5 (using sync client in async wrapper)
            message = self.anthropic_client.messages.create(
                model=self.senior_qa_model,
                max_tokens=self.senior_qa_max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            review_content = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    review_content += block.text
            
            # Parse review
            issues = self._parse_issues(review_content)
            
            # Extract quality scores
            scores = self._extract_quality_scores(review_content)
            
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Build result
            result = {
                "success": True,
                "agent": "senior_qa",
                "model": self.senior_qa_model,
                "review": review_content,
                "issues": issues,
                "issue_counts": {
                    "critical": len([i for i in issues if i.get("severity") == "critical"]),
                    "high": len([i for i in issues if i.get("severity") == "high"]),
                    "medium": len([i for i in issues if i.get("severity") == "medium"]),
                    "low": len([i for i in issues if i.get("severity") == "low"])
                },
                "quality_scores": scores,
                "passed": len([i for i in issues if i.get("severity") == "critical"]) == 0,
                "verdict": self._extract_verdict(review_content),
                "duration_ms": duration_ms,
                "files_reviewed": len(files),
                "tokens_used": {
                    "prompt": message.usage.input_tokens if message.usage else 0,
                    "completion": message.usage.output_tokens if message.usage else 0
                }
            }
            
            # Store in database
            await self._store_qa_report(project_id, user_id, result, "senior_qa")
            
            return result
            
        except Exception as e:
            logger.error(f"[QA] Senior QA failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": "senior_qa",
                "error": str(e),
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
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
        
        Args:
            project_id: Enjineer project ID
            files: List of files to review
            phase_context: Optional context about current phase
            user_id: User ID for logging
            
        Returns:
            Combined QA report
        """
        logger.info(f"[QA] Starting full QA pipeline for project {project_id}")
        
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
        
        # Combine results
        all_issues = []
        if standard_result.get("success"):
            all_issues.extend(standard_result.get("issues", []))
        if senior_result.get("success"):
            all_issues.extend(senior_result.get("issues", []))
        
        # Deduplicate issues by hash
        unique_issues = self._deduplicate_issues(all_issues)
        
        # Final verdict
        critical_count = len([i for i in unique_issues if i.get("severity") == "critical"])
        high_count = len([i for i in unique_issues if i.get("severity") == "high"])
        
        if critical_count > 0:
            final_verdict = "FAIL"
        elif high_count > 3:
            final_verdict = "CONDITIONAL_PASS"
        else:
            final_verdict = "PASS"
        
        return {
            "success": True,
            "pipeline": "full",
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
                "quality_scores": senior_result.get("quality_scores", {}),
                "models_used": [self.standard_qa_model, self.senior_qa_model]
            },
            "files_reviewed": len(files),
            "total_duration_ms": (
                standard_result.get("duration_ms", 0) + 
                senior_result.get("duration_ms", 0)
            )
        }
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _build_code_context(self, files: List[Dict[str, Any]], max_chars: int = 50000) -> str:
        """Build code context string from files."""
        context_parts = []
        total_chars = 0
        
        for file in files:
            path = file.get("path", "unknown")
            content = file.get("content", "")
            
            # Skip if we'd exceed limit
            file_chars = len(content) + len(path) + 50
            if total_chars + file_chars > max_chars:
                context_parts.append(f"\n[Truncated: {len(files) - len(context_parts)} more files...]")
                break
            
            context_parts.append(f"""
### File: `{path}`
```tsx
{content[:8000]}{"... [truncated]" if len(content) > 8000 else ""}
```
""")
            total_chars += file_chars
        
        return "\n".join(context_parts)
    
    async def _get_qa_knowledge(self, query: str) -> str:
        """Get relevant QA knowledge from the knowledge base."""
        try:
            # Search for QA-related knowledge
            context = await kb_service.get_relevant_context(
                query=query,
                max_sections=4,
                max_tokens=3000
            )
            
            if context:
                return f"""
## Relevant QA Standards

{context}
"""
            return "[No specific knowledge base context available]"
        except Exception as e:
            logger.warning(f"[QA] Failed to get knowledge context: {e}")
            return "[Knowledge base unavailable]"
    
    def _parse_issues(self, review_content: str) -> List[Dict[str, Any]]:
        """Parse issues from review content."""
        issues = []
        
        # Look for issue patterns
        import re
        
        # Critical issues
        critical_section = re.search(
            r'(?:🔴|Critical|Blocking).*?(?=(?:🟠|🟡|🟢|High|Medium|Low|##|$))',
            review_content, 
            re.DOTALL | re.IGNORECASE
        )
        if critical_section:
            issues.extend(self._extract_issues_from_section(critical_section.group(), "critical"))
        
        # High priority
        high_section = re.search(
            r'(?:🟠|High Priority).*?(?=(?:🟡|🟢|Medium|Low|##|$))',
            review_content, 
            re.DOTALL | re.IGNORECASE
        )
        if high_section:
            issues.extend(self._extract_issues_from_section(high_section.group(), "high"))
        
        # Medium priority
        medium_section = re.search(
            r'(?:🟡|Medium Priority).*?(?=(?:🟢|Low|##|$))',
            review_content, 
            re.DOTALL | re.IGNORECASE
        )
        if medium_section:
            issues.extend(self._extract_issues_from_section(medium_section.group(), "medium"))
        
        return issues
    
    def _extract_issues_from_section(self, section: str, severity: str) -> List[Dict[str, Any]]:
        """Extract individual issues from a section."""
        issues = []
        
        # Split by numbered items or bullet points
        import re
        items = re.split(r'\n(?:\d+\.|[-*•])\s+', section)
        
        for item in items[1:]:  # Skip first (header)
            if len(item.strip()) > 20:  # Meaningful content
                issues.append({
                    "severity": severity,
                    "description": item.strip()[:500],
                    "hash": hashlib.md5(item.strip()[:200].encode()).hexdigest()[:8]
                })
        
        return issues
    
    def _extract_quality_scores(self, review_content: str) -> Dict[str, int]:
        """Extract quality scores from senior review."""
        scores = {}
        
        import re
        
        # Look for score table
        patterns = [
            (r'Code Quality.*?(\d+)/10', 'code_quality'),
            (r'Performance.*?(\d+)/10', 'performance'),
            (r'Security.*?(\d+)/10', 'security'),
            (r'Accessibility.*?(\d+)/10', 'accessibility'),
            (r'Maintainability.*?(\d+)/10', 'maintainability'),
            (r'Overall.*?(\d+)/10', 'overall'),
        ]
        
        for pattern, key in patterns:
            match = re.search(pattern, review_content, re.IGNORECASE)
            if match:
                scores[key] = int(match.group(1))
        
        return scores
    
    def _extract_verdict(self, review_content: str) -> str:
        """Extract verdict from review."""
        if "APPROVED" in review_content.upper() and "❌" not in review_content:
            if "CONDITIONAL" in review_content.upper():
                return "CONDITIONAL_APPROVAL"
            return "APPROVED"
        elif "REQUIRES CHANGES" in review_content.upper() or "❌" in review_content:
            return "REQUIRES_CHANGES"
        return "UNKNOWN"
    
    def _deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate issues based on hash."""
        seen_hashes = set()
        unique = []
        
        for issue in issues:
            issue_hash = issue.get("hash", hashlib.md5(str(issue).encode()).hexdigest()[:8])
            if issue_hash not in seen_hashes:
                seen_hashes.add(issue_hash)
                unique.append(issue)
        
        return unique
    
    async def _store_qa_report(
        self,
        project_id: int,
        user_id: int,
        result: Dict[str, Any],
        qa_type: str
    ) -> None:
        """Store QA report in database."""
        try:
            async with db.acquire() as conn:
                await conn.execute("""
                    INSERT INTO enjineer_qa_reports
                    (project_id, trigger_type, qa_depth, overall_status, checks, triggered_by)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    project_id,
                    qa_type,
                    "full" if qa_type == "senior_qa" else "standard",
                    "pass" if result.get("passed") else "fail",
                    json.dumps(result),
                    user_id
                )
        except Exception as e:
            logger.warning(f"[QA] Failed to store QA report: {e}")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

qa_service = EnjineerQAService()


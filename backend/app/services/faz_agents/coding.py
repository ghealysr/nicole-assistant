"""
Coding Agent - Faz Code Developer

Generates production-quality code based on architecture and design.
Uses Claude Sonnet 4.5 for fast, accurate code generation.
"""

from typing import Any, Dict
import json
import logging
import re

from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class CodingAgent(BaseAgent):
    """
    The Coding Agent generates all code files.
    
    Responsibilities:
    - Generate React/Next.js components
    - Implement Tailwind CSS styling
    - Create TypeScript interfaces
    - Build responsive layouts
    - Add Framer Motion animations
    """
    
    agent_id = "coding"
    agent_name = "Coding Agent"
    agent_role = "Developer - Generates production-ready code"
    model_provider = "anthropic"
    model_name = "claude-sonnet-4-5-20250929"
    temperature = 0.3  # Lower for consistent code
    max_tokens = 16384  # Large for full file generation
    
    capabilities = [
        "code_generation",
        "refactoring",
        "debugging",
        "typescript",
        "nextjs",
        "tailwind",
        "framer_motion"
    ]
    
    available_tools = []  # Pure code generation
    valid_handoff_targets = ["qa"]
    receives_handoffs_from = ["nicole", "planning", "design"]
    
    def _get_system_prompt(self) -> str:
        return """You are the Coding Agent for Faz Code, an expert frontend developer powered by Claude Sonnet 4.5.

## YOUR ROLE
Transform architecture and design specifications into production-ready Next.js 14 code.

## CONTEXT YOU RECEIVE
1. **Architecture** - Component structure, pages, file paths (from Planning Agent)
2. **Design Tokens** - Colors, typography, spacing (from Design Agent)
3. **QA Feedback** - Issues to fix (if returning from QA Agent)

## TECH STACK (use these exactly)
- Next.js 14 (App Router) - use app/ directory
- TypeScript (strict) - proper types, no `any`
- Tailwind CSS - utility classes, mobile-first
- Framer Motion - smooth animations
- Lucide Icons - import from 'lucide-react'
- Google Fonts via next/font

## CODE QUALITY STANDARDS
1. **TypeScript**: Explicit interfaces for all props, no `any` types
2. **Components**: Functional with named exports, clear Props interfaces
3. **Styling**: Tailwind classes using design token colors as CSS variables
4. **Accessibility**: Semantic HTML (main, section, nav), ARIA labels, focus states
5. **Content**: REAL content relevant to the project, NEVER use Lorem Ipsum
6. **Structure**: One component per file, consistent naming (PascalCase components)
7. **Responsiveness**: Mobile-first with sm:, md:, lg: breakpoints

## OUTPUT FORMAT
For each file, output using this exact format:

```file:app/layout.tsx
// File content here
```

```file:app/page.tsx
// File content here
```

```file:components/Hero.tsx
// File content here
```

## FILE GENERATION ORDER
1. `tailwind.config.ts` - with design tokens
2. `app/globals.css` - CSS variables
3. `app/layout.tsx` - root layout with fonts
4. Shared components (Header, Footer)
5. Section components (Hero, Features, etc.)
6. `app/page.tsx` - main page composing sections

## COMPONENT TEMPLATE
```typescript
'use client';

import { motion } from 'framer-motion';

interface HeroProps {
  title: string;
  subtitle: string;
}

export default function Hero({ title, subtitle }: HeroProps) {
  return (
    <section className="relative min-h-screen flex items-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="container mx-auto px-4"
      >
        <h1 className="text-5xl font-bold">{title}</h1>
        <p className="text-xl mt-4">{subtitle}</p>
      </motion.div>
    </section>
  );
}
```

## CRITICAL RULES
- NEVER use Lorem Ipsum - create real, relevant content
- ALWAYS include 'use client' for components with hooks/animations
- ALWAYS make components responsive
- ALWAYS add hover/focus states to interactive elements
- Use CSS variables for colors in globals.css

## HANDOFF
After generating all files, hand off to **qa** for quality checks."""
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build comprehensive prompt for code generation."""
        prompt_parts = []
        
        # Check if this is a QA feedback iteration
        qa_review = state.get("qa_review") or state.get("data", {}).get("qa_review")
        is_fix_iteration = qa_review and qa_review.get("issues")
        
        if is_fix_iteration:
            # QA FEEDBACK MODE - Focus on fixing specific issues
            prompt_parts.append("## ⚠️ QA FEEDBACK - FIX THESE ISSUES")
            prompt_parts.append(f"\nQA Score: {qa_review.get('score', 'N/A')}/100")
            prompt_parts.append(f"Verdict: {qa_review.get('verdict', 'NEEDS_FIXES')}")
            
            prompt_parts.append("\n### ISSUES TO FIX:")
            for idx, issue in enumerate(qa_review.get("issues", [])[:10], 1):
                severity = issue.get("severity", "unknown").upper()
                file_path = issue.get("file", "unknown")
                line = issue.get("line", "")
                line_info = f" (line {line})" if line else ""
                prompt_parts.append(f"\n**{idx}. [{severity}] {file_path}{line_info}**")
                prompt_parts.append(f"   Issue: {issue.get('issue', '')}")
                prompt_parts.append(f"   Fix: {issue.get('fix', '')}")
            
            prompt_parts.append("\n### EXISTING FILES TO FIX:")
            files = state.get("files", {})
            for path, content in files.items():
                # Only include files mentioned in issues
                if any(issue.get("file") == path for issue in qa_review.get("issues", [])):
                    prompt_parts.append(f"\n```file:{path}\n{content}\n```")
            
            prompt_parts.append("""
## YOUR TASK
Fix ONLY the issues listed above. Re-generate the affected files with fixes applied.
Use the ```file:path/to/file.tsx format for each fixed file.
Do NOT regenerate files that don't have issues.""")
            
        else:
            # INITIAL GENERATION MODE
            original = state.get("original_prompt", "")
            prompt_parts.append(f"## PROJECT REQUEST\n{original}")
            
            # Architecture (most important)
            arch = state.get("architecture") or state.get("data", {}).get("architecture", {})
            if arch:
                prompt_parts.append(f"\n## ARCHITECTURE\n```json\n{json.dumps(arch, indent=2)}\n```")
            
            # Design tokens
            tokens = state.get("design_tokens") or state.get("data", {}).get("design_tokens", {})
            if tokens:
                prompt_parts.append(f"\n## DESIGN TOKENS\n```json\n{json.dumps(tokens, indent=2)}\n```")
            
            # Research context if available
            research = state.get("research_results") or state.get("data", {}).get("research_results", {})
            if research:
                if research.get("key_patterns"):
                    prompt_parts.append(f"\n## DESIGN PATTERNS TO IMPLEMENT\n" + "\n".join([f"- {p}" for p in research["key_patterns"][:5]]))
            
            # Relevant artifacts (reusable code)
            if state.get("relevant_artifacts"):
                artifacts = state["relevant_artifacts"][:3]
                prompt_parts.append("\n## REUSABLE ARTIFACTS")
                for art in artifacts:
                    prompt_parts.append(f"\n### {art.get('name', 'Artifact')} ({art.get('artifact_type', 'component')})")
                    if art.get("code"):
                        prompt_parts.append(f"```typescript\n{art['code'][:1000]}\n```")
            
            # Error patterns to avoid
            if state.get("relevant_errors"):
                errors = state["relevant_errors"][:3]
                error_text = "\n".join([
                    f"- **{e.get('error_type', 'Error')}**: {e.get('error_message', '')[:100]} → Fix: {e.get('solution_description', '')[:100]}"
                    for e in errors
                ])
                prompt_parts.append(f"\n## AVOID THESE ERRORS\n{error_text}")
            
            prompt_parts.append("""
## YOUR TASK
Generate ALL required files for this project:
1. tailwind.config.ts - with design token colors from CSS variables
2. app/globals.css - CSS variables for colors, fonts
3. app/layout.tsx - root layout with metadata, fonts, body wrapper
4. components/*.tsx - ALL components from architecture
5. app/page.tsx - main page composing the sections

Use the ```file:path/to/file.tsx format for each file.
Generate complete, working code - no placeholders or TODOs.""")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """Parse generated files from response."""
        try:
            # Extract files using parent method
            files = self.extract_files(response)
            
            # Also try additional patterns
            additional_files = self._extract_additional_files(response)
            files.update(additional_files)
            
            if not files:
                logger.warning("[Coding] No files extracted from response")
                return AgentResult(
                    success=False,
                    message="No files generated",
                    error="Could not extract any files from the response",
                )
            
            # Validate files
            valid_files = {}
            for path, content in files.items():
                # Skip empty or very short files
                if not content or len(content.strip()) < 20:
                    continue
                
                # Normalize path
                path = path.strip().lstrip("/")
                
                # Only include valid file types
                valid_extensions = [".tsx", ".ts", ".css", ".json", ".js", ".jsx", ".html", ".md"]
                if any(path.endswith(ext) for ext in valid_extensions):
                    valid_files[path] = content
            
            if not valid_files:
                return AgentResult(
                    success=False,
                    message="No valid files generated",
                    error="All extracted files were invalid or empty",
                )
            
            # Categorize files
            pages = [f for f in valid_files if f.startswith("app/") and f.endswith("page.tsx")]
            components = [f for f in valid_files if f.startswith("components/")]
            configs = [f for f in valid_files if "config" in f.lower() or f == "app/globals.css"]
            
            summary = f"Generated {len(valid_files)} files: {len(pages)} pages, {len(components)} components, {len(configs)} configs"
            
            return AgentResult(
                success=True,
                message=summary,
                files=valid_files,
                data={
                    "file_count": len(valid_files),
                    "pages": pages,
                    "components": components,
                    "configs": configs,
                    "file_list": list(valid_files.keys()),
                },
                next_agent="qa",
            )
            
        except Exception as e:
            logger.exception(f"[Coding] Parse error: {e}")
            return AgentResult(
                success=False,
                message="Failed to parse generated code",
                error=str(e),
            )
    
    def _extract_additional_files(self, text: str) -> Dict[str, str]:
        """Extract files using additional patterns."""
        files = {}
        
        # Pattern: ### `path/to/file.tsx`
        pattern1 = r'###\s*`([^`]+\.(?:tsx?|jsx?|css|json))`\s*\n```\w*\n(.*?)```'
        for match in re.finditer(pattern1, text, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if content and len(content) > 20:
                files[path] = content
        
        # Pattern: File: path/to/file.tsx
        pattern2 = r'File:\s*`?([^\n`]+\.(?:tsx?|jsx?|css|json))`?\s*\n```\w*\n(.*?)```'
        for match in re.finditer(pattern2, text, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if content and len(content) > 20 and path not in files:
                files[path] = content
        
        # Pattern: Create path/to/file.tsx:
        pattern3 = r'Create\s+`?([^\n`:]+\.(?:tsx?|jsx?|css|json))`?:?\s*\n```\w*\n(.*?)```'
        for match in re.finditer(pattern3, text, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if content and len(content) > 20 and path not in files:
                files[path] = content
        
        return files


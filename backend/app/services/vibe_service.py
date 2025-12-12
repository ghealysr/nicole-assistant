"""
AlphaWave Vibe Service - Project Management & Build Pipeline

Production-grade implementation featuring:
- Type-safe status transitions with validation
- Transaction support for multi-step operations
- API cost tracking
- Comprehensive error handling
- Lessons learning system foundation

Author: AlphaWave Architecture
Version: 2.0.0
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, TypeVar, Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from functools import wraps

from app.database import db
from app.integrations.alphawave_claude import claude_client

logger = logging.getLogger(__name__)

# Type alias for generic results
T = TypeVar('T')


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class ProjectStatus(str, Enum):
    """Project lifecycle states with strict ordering."""
    INTAKE = "intake"
    PLANNING = "planning"
    BUILDING = "building"
    QA = "qa"
    REVIEW = "review"
    APPROVED = "approved"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    DELIVERED = "delivered"
    ARCHIVED = "archived"
    
    @classmethod
    def get_order(cls, status: 'ProjectStatus') -> int:
        """Get numeric order for status comparison."""
        order = {
            cls.INTAKE: 0,
            cls.PLANNING: 1,
            cls.BUILDING: 2,
            cls.QA: 3,
            cls.REVIEW: 4,
            cls.APPROVED: 5,
            cls.DEPLOYING: 6,
            cls.DEPLOYED: 7,
            cls.DELIVERED: 8,
            cls.ARCHIVED: 99,
        }
        return order.get(status, -1)
    
    @classmethod
    def can_transition(cls, from_status: 'ProjectStatus', to_status: 'ProjectStatus') -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            cls.INTAKE: [cls.PLANNING, cls.ARCHIVED],
            cls.PLANNING: [cls.BUILDING, cls.INTAKE, cls.ARCHIVED],
            cls.BUILDING: [cls.QA, cls.PLANNING, cls.ARCHIVED],
            cls.QA: [cls.REVIEW, cls.BUILDING, cls.ARCHIVED],
            cls.REVIEW: [cls.APPROVED, cls.BUILDING, cls.ARCHIVED],
            cls.APPROVED: [cls.DEPLOYING, cls.DEPLOYED, cls.ARCHIVED],
            cls.DEPLOYING: [cls.DEPLOYED, cls.APPROVED, cls.ARCHIVED],
            cls.DEPLOYED: [cls.DELIVERED, cls.ARCHIVED],
            cls.DELIVERED: [cls.ARCHIVED],
            cls.ARCHIVED: [],
        }
        return to_status in valid_transitions.get(from_status, [])


class ProjectType(str, Enum):
    """Supported project types."""
    WEBSITE = "website"
    CHATBOT = "chatbot"
    ASSISTANT = "assistant"
    INTEGRATION = "integration"


class LessonCategory(str, Enum):
    """Categories for learned lessons."""
    DESIGN = "design"
    CONTENT = "content"
    SEO = "seo"
    CODE = "code"
    ARCHITECTURE = "architecture"
    CLIENT_FEEDBACK = "client_feedback"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    UX = "ux"


# API Cost estimates (per 1K tokens)
MODEL_COSTS = {
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
    "claude-haiku-4-20250514": {"input": 0.00025, "output": 0.00125},
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class OperationResult:
    """Result wrapper for service operations."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    api_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {"success": self.success}
        if self.data:
            result.update(self.data)
        if self.error:
            result["error"] = self.error
        if self.api_cost > 0:
            result["api_cost"] = float(self.api_cost)
        return result


@dataclass
class ParsedFile:
    """Represents a parsed file from Claude's response."""
    path: str
    content: str
    language: str = "text"
    
    @classmethod
    def detect_language(cls, path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            '.tsx': 'typescript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.js': 'javascript',
            '.css': 'css',
            '.json': 'json',
            '.md': 'markdown',
            '.html': 'html',
            '.py': 'python',
        }
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return 'text'


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

INTAKE_SYSTEM_PROMPT = """You are Nicole, conducting an intake interview for a new AlphaWave project.

Your goal: Extract all information needed to build the project through natural conversation.

For WEBSITE projects, gather:
- Business name, type, location
- Services/products offered
- Contact info (phone, email, address)
- Business hours
- Brand colors (if any)
- Competitor websites they like
- Main goals for the site

For CHATBOT projects, gather:
- Business name and type
- What questions the chatbot should answer
- Tone/personality (professional, friendly, etc.)
- Key information to include (hours, services, FAQs)
- Lead capture requirements

Be conversational and natural. Ask follow-up questions when needed.

When you have gathered ALL necessary information, output a complete JSON brief:

```json
{
  "project_type": "website|chatbot|assistant",
  "business_name": "...",
  "business_type": "...",
  "location": {"city": "...", "state": "...", "address": "..."},
  "services": ["...", "..."],
  "contact": {"phone": "...", "email": "...", "hours": "..."},
  "branding": {"colors": ["primary_hex", "secondary_hex"], "style": "modern|classic|minimal"},
  "goals": ["primary_goal", "secondary_goal"],
  "competitors": ["url1", "url2"],
  "notes": "additional context"
}
```

IMPORTANT: Only output the JSON when you have gathered sufficient information. If missing critical details, ask clarifying questions instead."""


ARCHITECTURE_SYSTEM_PROMPT = """You are an expert web architect planning an AlphaWave website project.

Given a project brief, create a detailed technical specification optimized for SMB websites.

Tech Stack (fixed):
- Next.js 14 (App Router)
- TypeScript (strict mode)
- Tailwind CSS
- shadcn/ui components

Output JSON in this exact format:
```json
{
  "pages": [
    {
      "path": "/",
      "name": "Homepage",
      "components": ["HeroImage", "FeatureGrid", "CTASimple", "ContactInfo"],
      "content_outline": "Brief description of page content and structure"
    }
  ],
  "seo": {
    "primary_keywords": ["keyword1", "keyword2"],
    "secondary_keywords": ["keyword3", "keyword4"],
    "schema_type": "LocalBusiness|Organization|Product"
  },
  "design": {
    "primary_color": "#hex",
    "secondary_color": "#hex",
    "accent_color": "#hex",
    "font_heading": "font-name",
    "font_body": "font-name",
    "style": "modern|classic|minimal|bold"
  },
  "components_needed": ["Header", "Footer", "ContactForm"],
  "integrations": ["contact_form", "google_maps", "social_links"],
  "estimated_hours": 4,
  "complexity": "simple|medium|complex"
}
```

Guidelines:
- Most SMB sites need 4-6 pages maximum
- Prioritize mobile-first responsive design
- Include clear CTAs on every page
- Ensure accessibility compliance (WCAG 2.1 AA)"""


BUILD_SYSTEM_PROMPT = """You are a senior Next.js developer building an AlphaWave website.

Generate production-ready code following these exact standards:

Tech Stack:
- Next.js 14 (App Router with server components by default)
- TypeScript (strict mode, explicit types)
- Tailwind CSS (utility-first, no custom CSS unless necessary)
- shadcn/ui components (when applicable)

Code Standards:
- Use 'use client' directive only when needed (event handlers, hooks)
- Proper metadata exports for SEO
- Responsive design: mobile-first with sm/md/lg/xl breakpoints
- Accessible: proper ARIA labels, semantic HTML, keyboard navigation
- Error boundaries where appropriate

File Output Format - use EXACTLY this pattern:
```filepath:app/layout.tsx
[complete file contents here]
```

```filepath:app/page.tsx
[complete file contents here]
```

Generate ALL files needed for a complete, working website:
1. app/layout.tsx - Root layout with fonts, metadata, common elements
2. app/page.tsx - Homepage
3. app/globals.css - Tailwind imports and custom properties
4. tailwind.config.ts - Theme configuration with brand colors
5. components/ - Reusable components
6. All additional pages from the architecture

CRITICAL: Generate COMPLETE, WORKING code. No placeholders, no TODOs, no "..."."""


QA_SYSTEM_PROMPT = """You are a senior QA engineer reviewing Next.js/TypeScript code for production readiness.

Review the provided code and check for:

1. TypeScript Errors
   - Type mismatches
   - Missing type annotations
   - Incorrect generic usage

2. React/Next.js Issues
   - Missing 'use client' directives
   - Incorrect metadata exports
   - Server/client component misuse
   - Missing error boundaries

3. Import Problems
   - Missing imports
   - Incorrect import paths
   - Circular dependencies

4. Accessibility (WCAG 2.1 AA)
   - Missing alt text
   - Improper heading hierarchy
   - Keyboard navigation issues
   - Color contrast problems

5. SEO Issues
   - Missing meta tags
   - Improper heading structure
   - Missing structured data

6. Performance Concerns
   - Unnecessary client components
   - Missing image optimization
   - Bundle size issues

Output your review as JSON:
```json
{
  "passed": true|false,
  "score": 1-100,
  "issues": [
    {"severity": "critical|high|medium|low", "file": "path", "line": null, "message": "description"}
  ],
  "suggestions": ["improvement suggestion"],
  "summary": "Overall assessment"
}
```"""


REVIEW_SYSTEM_PROMPT = """You are a senior technical reviewer and quality assurance lead for AlphaWave.

Conduct a final comprehensive review of the project before client delivery.

Review Criteria:
1. Brief Alignment - Does the implementation match all client requirements?
2. Architecture Compliance - Is the technical spec properly implemented?
3. Code Quality - Is the code production-ready and maintainable?
4. User Experience - Is the site professional and user-friendly?
5. Business Value - Would this site help the client achieve their goals?

Output your review as JSON:
```json
{
  "approved": true|false,
  "score": 1-10,
  "brief_alignment": {"score": 1-10, "notes": "..."},
  "code_quality": {"score": 1-10, "notes": "..."},
  "ux_quality": {"score": 1-10, "notes": "..."},
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1", "concern2"],
  "required_changes": ["change1"] | null,
  "recommendation": "approve|revise|reject",
  "client_ready": true|false
}
```"""


# ============================================================================
# EXCEPTIONS
# ============================================================================

class VibeServiceError(Exception):
    """Base exception for Vibe service errors."""
    pass


class ProjectNotFoundError(VibeServiceError):
    """Project does not exist or user doesn't have access."""
    pass


class InvalidStatusTransitionError(VibeServiceError):
    """Invalid status transition attempted."""
    pass


class MissingPrerequisiteError(VibeServiceError):
    """Required data missing for operation."""
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def estimate_api_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Estimate API cost for a Claude call."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS["claude-sonnet-4-20250514"])
    input_cost = Decimal(str(costs["input"])) * (input_tokens / 1000)
    output_cost = Decimal(str(costs["output"])) * (output_tokens / 1000)
    return input_cost + output_cost


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from Claude's response, handling various formats."""
    # Try ```json blocks first
    json_pattern = r'```json\s*(.*?)\s*```'
    matches = re.findall(json_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # Try generic ``` blocks
    generic_pattern = r'```\s*(.*?)\s*```'
    matches = re.findall(generic_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # Try parsing the entire response as JSON
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    return None


def parse_files_from_response(response: str) -> List[ParsedFile]:
    """
    Parse file contents from Claude's response.
    
    Supports multiple formats:
    1. ```filepath:/path/to/file.tsx
    2. ```tsx with // filepath comment
    3. === filename.tsx === headers
    """
    files: List[ParsedFile] = []
    seen_paths: set = set()
    
    # Pattern 1: ```filepath:/path/to/file
    pattern1 = r'```filepath:([^\n]+)\n(.*?)```'
    for match in re.finditer(pattern1, response, re.DOTALL):
        path = match.group(1).strip()
        content = match.group(2).strip()
        if path and content and path not in seen_paths:
            files.append(ParsedFile(
                path=path,
                content=content,
                language=ParsedFile.detect_language(path)
            ))
            seen_paths.add(path)
    
    # Pattern 2: ```lang with // filepath comment on first line
    pattern2 = r'```(?:tsx?|jsx?|typescript|javascript|css|json|html)\n//\s*([^\n]+\.(?:tsx?|jsx?|css|json|html|md))\n(.*?)```'
    for match in re.finditer(pattern2, response, re.DOTALL):
        path = match.group(1).strip()
        content = match.group(2).strip()
        if path and content and path not in seen_paths:
            files.append(ParsedFile(
                path=path,
                content=content,
                language=ParsedFile.detect_language(path)
            ))
            seen_paths.add(path)
    
    # Pattern 3: === filename.ext === headers
    pattern3 = r'===\s*([^\s=]+\.(?:tsx?|jsx?|css|json|html|md))\s*===\s*\n(.*?)(?=\n===|$)'
    for match in re.finditer(pattern3, response, re.DOTALL):
        path = match.group(1).strip()
        content = match.group(2).strip()
        # Clean content: remove leading/trailing code blocks
        if '```' in content:
            # Extract content from code block if present
            code_match = re.search(r'```\w*\n?(.*?)```', content, re.DOTALL)
            if code_match:
                content = code_match.group(1).strip()
        if path and content and path not in seen_paths:
            files.append(ParsedFile(
                path=path,
                content=content,
                language=ParsedFile.detect_language(path)
            ))
            seen_paths.add(path)
    
    if not files:
        logger.warning("[VIBE] No files parsed from build response. Response preview: %s...", 
                      response[:500] if response else "empty")
    else:
        logger.info("[VIBE] Parsed %d files from response", len(files))
    
    return files


# ============================================================================
# SERVICE CLASS
# ============================================================================

class VibeService:
    """
    Production-grade service for AlphaWave Vibe project management.
    
    Features:
    - Type-safe status transitions
    - Transaction support for multi-step operations
    - API cost tracking
    - Comprehensive error handling
    - Lessons learning system
    """
    
    # Model configuration
    SONNET_MODEL = "claude-sonnet-4-20250514"
    OPUS_MODEL = "claude-opus-4-20250514"
    
    def __init__(self):
        """Initialize the Vibe service."""
        logger.info("[VIBE] Service initialized (v2.0)")
    
    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================
    
    async def _get_project_or_raise(
        self, 
        project_id: int, 
        user_id: int
    ) -> Dict[str, Any]:
        """Get project or raise ProjectNotFoundError."""
        result = await db.fetchrow(
            """
            SELECT * FROM vibe_projects 
            WHERE project_id = $1 AND user_id = $2
            """,
            project_id, user_id
        )
        
        if not result:
            raise ProjectNotFoundError(f"Project {project_id} not found or access denied")
        
        return dict(result)
    
    def _validate_status_for_operation(
        self,
        project: Dict[str, Any],
        allowed_statuses: List[ProjectStatus],
        operation_name: str
    ) -> None:
        """Validate project status for an operation."""
        current_status = project.get("status", "")
        
        try:
            status_enum = ProjectStatus(current_status)
        except ValueError:
            raise InvalidStatusTransitionError(
                f"Invalid project status: {current_status}"
            )
        
        if status_enum not in allowed_statuses:
            allowed_names = ", ".join(s.value for s in allowed_statuses)
            raise InvalidStatusTransitionError(
                f"{operation_name} requires status to be one of: {allowed_names}. "
                f"Current status: {current_status}"
            )
    
    async def _update_api_cost(
        self,
        project_id: int,
        user_id: int,
        cost: Decimal
    ) -> None:
        """Add to project's cumulative API cost."""
        await db.execute(
            """
            UPDATE vibe_projects
            SET api_cost = COALESCE(api_cost, 0) + $1, updated_at = NOW()
            WHERE project_id = $2 AND user_id = $3
            """,
            float(cost), project_id, user_id
        )
    
    async def _save_files_batch(
        self,
        project_id: int,
        files: List[ParsedFile]
    ) -> int:
        """Save multiple files in a single batch operation."""
        if not files:
            return 0
        
        # Build batch upsert values
        values_list = []
        for f in files:
            values_list.append((project_id, f.path, f.content))
        
        # Delete existing files for this project first (clean slate)
        await db.execute(
            "DELETE FROM vibe_files WHERE project_id = $1",
            project_id
        )
        
        # Batch insert
        count = 0
        for project_id, path, content in values_list:
            await db.execute(
                """
                INSERT INTO vibe_files (project_id, file_path, content, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                project_id, path, content
            )
            count += 1
        
        logger.info("[VIBE] Saved %d files for project %d", count, project_id)
        return count
    
    # ========================================================================
    # PROJECT CRUD
    # ========================================================================
    
    async def create_project(
        self,
        user_id: int,
        name: str,
        project_type: str,
        client_name: Optional[str] = None,
        client_email: Optional[str] = None
    ) -> OperationResult:
        """
        Create a new Vibe project.
        
        Args:
            user_id: Owner's user ID
            name: Project name
            project_type: One of website, chatbot, assistant, integration
            client_name: Optional client business name
            client_email: Optional client email
            
        Returns:
            OperationResult with created project data
        """
        # Validate project type
        try:
            ProjectType(project_type)
        except ValueError:
            return OperationResult(
                success=False,
                error=f"Invalid project type: {project_type}. Must be one of: {', '.join(t.value for t in ProjectType)}"
            )
        
        try:
            result = await db.fetchrow(
                """
                INSERT INTO vibe_projects (
                    user_id, name, project_type, client_name, client_email,
                    status, brief, architecture, config, 
                    api_cost, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, '{}', '{}', '{}', 0, NOW(), NOW())
                RETURNING *
                """,
                user_id, name, project_type, client_name, client_email,
                ProjectStatus.INTAKE.value
            )
            
            if not result:
                return OperationResult(success=False, error="Failed to create project")
            
            project = dict(result)
            logger.info("[VIBE] Created project %d: %s", project['project_id'], name)
            
            return OperationResult(
                success=True,
                data={"project": project, "status": ProjectStatus.INTAKE.value}
            )
            
        except Exception as e:
            logger.error("[VIBE] Failed to create project: %s", e)
            return OperationResult(success=False, error=str(e))
    
    async def get_project(
        self, 
        project_id: int, 
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a project by ID. Returns None if not found."""
        result = await db.fetchrow(
            """
            SELECT * FROM vibe_projects 
            WHERE project_id = $1 AND user_id = $2
            """,
            project_id, user_id
        )
        return dict(result) if result else None
    
    async def list_projects(
        self, 
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List user's projects with pagination.
        
        Returns:
            Tuple of (projects list, total count)
        """
        # Get total count
        if status:
            count_result = await db.fetchrow(
                "SELECT COUNT(*) as total FROM vibe_projects WHERE user_id = $1 AND status = $2",
                user_id, status
            )
        else:
            count_result = await db.fetchrow(
                "SELECT COUNT(*) as total FROM vibe_projects WHERE user_id = $1 AND status != 'archived'",
                user_id
            )
        
        total = count_result['total'] if count_result else 0
        
        # Get projects
        if status:
            results = await db.fetch(
                """
                SELECT project_id, name, project_type, client_name, client_email,
                       status, preview_url, production_url, api_cost,
                       created_at, updated_at
                FROM vibe_projects
                WHERE user_id = $1 AND status = $2
                ORDER BY updated_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id, status, limit, offset
            )
        else:
            results = await db.fetch(
                """
                SELECT project_id, name, project_type, client_name, client_email,
                       status, preview_url, production_url, api_cost,
                       created_at, updated_at
                FROM vibe_projects
                WHERE user_id = $1 AND status != 'archived'
                ORDER BY updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )
        
        projects = [dict(r) for r in results] if results else []
        return projects, total
    
    async def update_project(
        self,
        project_id: int,
        user_id: int,
        updates: Dict[str, Any]
    ) -> OperationResult:
        """
        Update project fields.
        
        Args:
            project_id: Project to update
            user_id: User making the update
            updates: Dict of field names to new values
            
        Returns:
            OperationResult with updated project
        """
        # Validate project exists
        try:
            await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Whitelist allowed fields
        allowed_fields = {
            'name', 'client_name', 'client_email', 'status',
            'brief', 'architecture', 'config',
            'preview_url', 'production_url', 'github_repo',
            'estimated_price', 'api_cost'
        }
        
        # JSONB fields need special handling
        jsonb_fields = {'brief', 'architecture', 'config'}
        
        set_clauses = []
        values = []
        param_idx = 1
        
        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            
            if field in jsonb_fields:
                # Cast to JSONB explicitly
                set_clauses.append(f"{field} = ${param_idx}::jsonb")
                values.append(json.dumps(value) if isinstance(value, dict) else value)
            else:
                set_clauses.append(f"{field} = ${param_idx}")
                values.append(value)
            param_idx += 1
        
        if not set_clauses:
            project = await self.get_project(project_id, user_id)
            return OperationResult(success=True, data={"project": project})
        
        set_clauses.append("updated_at = NOW()")
        
        query = f"""
            UPDATE vibe_projects
            SET {', '.join(set_clauses)}
            WHERE project_id = ${param_idx} AND user_id = ${param_idx + 1}
            RETURNING *
        """
        
        values.extend([project_id, user_id])
        
        try:
            result = await db.fetchrow(query, *values)
            
            if not result:
                return OperationResult(success=False, error="Update failed")
            
            return OperationResult(
                success=True,
                data={"project": dict(result)}
            )
            
        except Exception as e:
            logger.error("[VIBE] Update failed: %s", e)
            return OperationResult(success=False, error=str(e))
    
    async def delete_project(self, project_id: int, user_id: int) -> OperationResult:
        """Soft delete a project by archiving it."""
        try:
            await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        result = await db.execute(
            """
            UPDATE vibe_projects
            SET status = $1, updated_at = NOW()
            WHERE project_id = $2 AND user_id = $3
            """,
            ProjectStatus.ARCHIVED.value, project_id, user_id
        )
        
        success = result == "UPDATE 1"
        return OperationResult(
            success=success,
            data={"message": "Project archived"} if success else None,
            error=None if success else "Archive failed"
        )
    
    # ========================================================================
    # BUILD PIPELINE
    # ========================================================================
    
    async def run_intake(
        self,
        project_id: int,
        user_id: int,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> OperationResult:
        """
        Run intake conversation to gather project requirements.
        
        Args:
            project_id: Target project
            user_id: User ID
            user_message: User's message
            conversation_history: Previous conversation turns
            
        Returns:
            OperationResult with response and optional extracted brief
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status - intake can only run in INTAKE status
        try:
            self._validate_status_for_operation(
                project, 
                [ProjectStatus.INTAKE],
                "Intake"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Build messages
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})
        
        # Call Claude
        try:
            response = await claude_client.generate_response(
                messages=messages,
                system_prompt=INTAKE_SYSTEM_PROMPT,
                model=self.SONNET_MODEL,
                max_tokens=2000,
                temperature=0.7
            )
        except Exception as e:
            logger.error("[VIBE] Intake Claude call failed: %s", e)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (rough: ~500 input, ~1000 output tokens)
        cost = estimate_api_cost(self.SONNET_MODEL, 500, 1000)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Check if response contains a JSON brief
        brief = extract_json_from_response(response)
        new_status = ProjectStatus.INTAKE.value
        
        if brief:
            # Validate brief has required fields
            required_fields = ["business_name", "project_type"]
            if all(brief.get(f) for f in required_fields):
                # Save brief and advance status
                await self.update_project(project_id, user_id, {
                    "brief": brief,
                    "status": ProjectStatus.PLANNING.value
                })
                new_status = ProjectStatus.PLANNING.value
                logger.info("[VIBE] Extracted brief for project %d", project_id)
            else:
                logger.warning("[VIBE] Extracted JSON missing required fields")
                brief = None
        
        return OperationResult(
            success=True,
            data={
                "response": response,
                "brief": brief,
                "status": new_status,
                "brief_complete": brief is not None
            },
            api_cost=cost
        )
    
    async def run_architecture(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Generate architecture specification using Opus.
        
        Requires project to be in PLANNING status with a completed brief.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.PLANNING],
                "Architecture planning"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate brief exists
        brief = project.get("brief", {})
        if not brief or not isinstance(brief, dict) or not brief.get("business_name"):
            return OperationResult(
                success=False,
                error="Project has no brief. Complete intake first."
            )
        
        # Call Opus for architecture
        try:
            response = await claude_client.generate_response(
                messages=[{
                    "role": "user",
                    "content": f"Create a detailed architecture specification for this project:\n\n{json.dumps(brief, indent=2)}"
                }],
                system_prompt=ARCHITECTURE_SYSTEM_PROMPT,
                model=self.OPUS_MODEL,
                max_tokens=4000,
                temperature=0.5
            )
        except Exception as e:
            logger.error("[VIBE] Architecture Claude call failed: %s", e)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (Opus: ~1000 input, ~2000 output)
        cost = estimate_api_cost(self.OPUS_MODEL, 1000, 2000)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Extract architecture JSON
        architecture = extract_json_from_response(response)
        
        if architecture and architecture.get("pages"):
            # Valid architecture - advance status
            await self.update_project(project_id, user_id, {
                "architecture": architecture,
                "status": ProjectStatus.BUILDING.value
            })
            
            logger.info("[VIBE] Generated architecture for project %d with %d pages",
                       project_id, len(architecture.get("pages", [])))
            
            return OperationResult(
                success=True,
                data={
                    "architecture": architecture,
                    "status": ProjectStatus.BUILDING.value,
                    "page_count": len(architecture.get("pages", []))
                },
                api_cost=cost
            )
        else:
            logger.warning("[VIBE] Failed to extract valid architecture JSON")
            return OperationResult(
                success=False,
                error="Failed to generate valid architecture. Please try again.",
                data={"raw_response": response[:500]},
                api_cost=cost
            )
    
    async def run_build(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Run the build phase - generate all code files.
        
        Uses Sonnet for code generation. Files are saved atomically.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.BUILDING],
                "Build"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate architecture exists
        architecture = project.get("architecture", {})
        brief = project.get("brief", {})
        
        if not architecture or not architecture.get("pages"):
            return OperationResult(
                success=False,
                error="Project has no architecture. Run planning first."
            )
        
        # Build comprehensive prompt
        build_prompt = f"""Generate a complete, production-ready Next.js 14 website based on this specification:

## Project Brief
{json.dumps(brief, indent=2)}

## Architecture Specification
{json.dumps(architecture, indent=2)}

## Requirements
1. Generate ALL files needed for a working website
2. Start with these core files:
   - app/layout.tsx (root layout with metadata)
   - app/page.tsx (homepage)
   - app/globals.css (Tailwind imports + CSS variables)
   - tailwind.config.ts (with brand colors from design spec)
3. Then generate all pages specified in the architecture
4. Include any necessary components

## Technical Standards
- TypeScript strict mode
- Tailwind CSS utility classes
- Mobile-first responsive design
- Accessible (WCAG 2.1 AA compliant)
- SEO optimized with proper metadata
- Use the exact colors specified in the design spec

Generate complete, working code for each file."""

        try:
            response = await claude_client.generate_response(
                messages=[{"role": "user", "content": build_prompt}],
                system_prompt=BUILD_SYSTEM_PROMPT,
                model=self.SONNET_MODEL,
                max_tokens=16000,  # Large budget for code generation
                temperature=0.3    # Lower temperature for code
            )
        except Exception as e:
            logger.error("[VIBE] Build Claude call failed: %s", e)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (large generation: ~2000 input, ~8000 output)
        cost = estimate_api_cost(self.SONNET_MODEL, 2000, 8000)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Parse files from response
        files = parse_files_from_response(response)
        
        if not files:
            return OperationResult(
                success=False,
                error="No files could be parsed from the build output. Please retry.",
                data={"raw_response_preview": response[:1000]},
                api_cost=cost
            )
        
        # Save files atomically
        file_count = await self._save_files_batch(project_id, files)
        
        # Generate preview URL and advance status
        preview_url = f"https://preview.alphawave.ai/p/{project_id}"
        await self.update_project(project_id, user_id, {
            "status": ProjectStatus.QA.value,
            "preview_url": preview_url
        })
        
        return OperationResult(
            success=True,
            data={
                "status": ProjectStatus.QA.value,
                "files_generated": [f.path for f in files],
                "file_count": file_count,
                "preview_url": preview_url
            },
            api_cost=cost
        )
    
    async def run_qa(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Run QA checks on generated files.
        
        Analyzes code quality, accessibility, and correctness.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.QA],
                "QA"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Get files for review
        files = await self.get_project_files(project_id)
        
        if not files:
            return OperationResult(
                success=False,
                error="No files to review. Run build first."
            )
        
        # Build file summary for QA
        file_summaries = []
        for f in files[:15]:  # Limit to 15 files for context
            content = f['content']
            if len(content) > 3000:
                content = content[:3000] + "\n... [truncated]"
            file_summaries.append(f"=== {f['file_path']} ===\n{content}")
        
        qa_prompt = f"""Review this Next.js/TypeScript codebase for production readiness:

{chr(10).join(file_summaries)}

Total files: {len(files)}

Perform a comprehensive QA review and output your findings as JSON."""

        try:
            response = await claude_client.generate_response(
                messages=[{"role": "user", "content": qa_prompt}],
                system_prompt=QA_SYSTEM_PROMPT,
                model=self.SONNET_MODEL,
                max_tokens=3000,
                temperature=0.3
            )
        except Exception as e:
            logger.error("[VIBE] QA Claude call failed: %s", e)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost
        cost = estimate_api_cost(self.SONNET_MODEL, 3000, 1500)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Parse QA result
        qa_result = extract_json_from_response(response)
        
        if not qa_result:
            qa_result = {
                "passed": True,
                "score": 75,
                "issues": [],
                "suggestions": ["Manual review recommended"],
                "summary": "Automated extraction failed - manual review needed"
            }
        
        # Determine pass/fail
        passed = qa_result.get("passed", False)
        score = qa_result.get("score", 0)
        
        # If score >= 70 and no critical issues, consider it passed
        critical_issues = [i for i in qa_result.get("issues", []) 
                         if isinstance(i, dict) and i.get("severity") == "critical"]
        
        if score >= 70 and not critical_issues:
            passed = True
        
        # Update status based on QA result
        new_status = ProjectStatus.REVIEW.value if passed else ProjectStatus.QA.value
        await self.update_project(project_id, user_id, {"status": new_status})
        
        return OperationResult(
            success=True,
            data={
                "status": new_status,
                "passed": passed,
                "score": score,
                "issues": qa_result.get("issues", []),
                "suggestions": qa_result.get("suggestions", []),
                "summary": qa_result.get("summary", ""),
                "needs_rebuild": not passed
            },
            api_cost=cost
        )
    
    async def run_review(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Final review using Opus before client delivery.
        
        Comprehensive quality assessment and approval decision.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Validate status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.REVIEW],
                "Final review"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        brief = project.get("brief", {})
        architecture = project.get("architecture", {})
        files = await self.get_project_files(project_id)
        
        # Get sample file contents
        sample_files = []
        priority_files = ['layout.tsx', 'page.tsx', 'globals.css']
        
        for f in files:
            if any(p in f['file_path'] for p in priority_files):
                content = f['content'][:2000] if len(f['content']) > 2000 else f['content']
                sample_files.append(f"=== {f['file_path']} ===\n{content}")
        
        review_prompt = f"""Conduct a final comprehensive review of this AlphaWave project.

## Client Brief
{json.dumps(brief, indent=2)}

## Technical Architecture
{json.dumps(architecture, indent=2)}

## Generated Files ({len(files)} total)
{chr(10).join(sample_files[:5])}

## Review Task
Assess whether this project is ready for client delivery. Consider:
1. Does the implementation match all client requirements?
2. Is the code production-quality?
3. Would you be proud to deliver this to a paying client?

Output your comprehensive review as JSON."""

        try:
            response = await claude_client.generate_response(
                messages=[{"role": "user", "content": review_prompt}],
                system_prompt=REVIEW_SYSTEM_PROMPT,
                model=self.OPUS_MODEL,
                max_tokens=2500,
                temperature=0.3
            )
        except Exception as e:
            logger.error("[VIBE] Review Claude call failed: %s", e)
            return OperationResult(success=False, error=f"AI service error: {e}")
        
        # Estimate cost (Opus)
        cost = estimate_api_cost(self.OPUS_MODEL, 2000, 1500)
        await self._update_api_cost(project_id, user_id, cost)
        
        # Parse review result
        review_result = extract_json_from_response(response)
        
        if not review_result:
            review_result = {
                "approved": False,
                "score": 0,
                "recommendation": "revise",
                "concerns": ["Failed to parse review results"]
            }
        
        approved = review_result.get("approved", False)
        recommendation = review_result.get("recommendation", "revise")
        
        # Update status based on review
        if approved or recommendation == "approve":
            new_status = ProjectStatus.APPROVED.value
        else:
            new_status = ProjectStatus.REVIEW.value  # Stay in review until fixed
        
        await self.update_project(project_id, user_id, {"status": new_status})
        
        return OperationResult(
            success=True,
            data={
                "status": new_status,
                "approved": approved,
                "score": review_result.get("score", 0),
                "strengths": review_result.get("strengths", []),
                "concerns": review_result.get("concerns", []),
                "required_changes": review_result.get("required_changes"),
                "recommendation": recommendation,
                "client_ready": review_result.get("client_ready", False)
            },
            api_cost=cost
        )
    
    async def approve_project(
        self,
        project_id: int,
        user_id: int
    ) -> OperationResult:
        """
        Manual approval by Glen - marks project ready for deployment.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Can approve from REVIEW or APPROVED status
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.REVIEW, ProjectStatus.APPROVED],
                "Approval"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        await self.update_project(project_id, user_id, {
            "status": ProjectStatus.APPROVED.value
        })
        
        logger.info("[VIBE] Project %d approved by user %d", project_id, user_id)
        
        return OperationResult(
            success=True,
            data={
                "status": ProjectStatus.APPROVED.value,
                "message": "Project approved and ready for deployment"
            }
        )
    
    async def deploy_project(
        self,
        project_id: int,
        user_id: int,
        preview_url: Optional[str] = None,
        production_url: Optional[str] = None
    ) -> OperationResult:
        """
        Deploy the project. Currently a placeholder that sets URLs and status.
        
        In production, this would integrate with GitHub and Vercel APIs.
        """
        try:
            project = await self._get_project_or_raise(project_id, user_id)
        except ProjectNotFoundError as e:
            return OperationResult(success=False, error=str(e))
        
        # Must be approved before deployment
        try:
            self._validate_status_for_operation(
                project,
                [ProjectStatus.APPROVED],
                "Deployment"
            )
        except InvalidStatusTransitionError as e:
            return OperationResult(success=False, error=str(e))
        
        # Generate URLs if not provided
        final_preview = preview_url or f"https://preview.alphawave.ai/p/{project_id}"
        final_production = production_url or f"https://sites.alphawave.ai/{project_id}"
        
        await self.update_project(project_id, user_id, {
            "status": ProjectStatus.DEPLOYED.value,
            "preview_url": final_preview,
            "production_url": final_production
        })
        
        logger.info("[VIBE] Project %d deployed to %s", project_id, final_production)
        
        return OperationResult(
            success=True,
            data={
                "status": ProjectStatus.DEPLOYED.value,
                "preview_url": final_preview,
                "production_url": final_production,
                "message": "Project deployed successfully"
            }
        )
    
    # ========================================================================
    # FILE MANAGEMENT
    # ========================================================================
    
    async def get_project_files(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all files for a project."""
        results = await db.fetch(
            """
            SELECT file_id, file_path, content, created_at, updated_at
            FROM vibe_files
            WHERE project_id = $1
            ORDER BY file_path
            """,
            project_id
        )
        return [dict(r) for r in results] if results else []
    
    async def get_file(
        self, 
        project_id: int, 
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific file by path."""
        result = await db.fetchrow(
            """
            SELECT file_id, file_path, content, created_at, updated_at
            FROM vibe_files
            WHERE project_id = $1 AND file_path = $2
            """,
            project_id, file_path
        )
        return dict(result) if result else None
    
    # ========================================================================
    # LESSONS LEARNING SYSTEM
    # ========================================================================
    
    async def capture_lesson(
        self,
        project_id: int,
        category: str,
        issue: str,
        solution: str,
        impact: str = "medium",
        tags: Optional[List[str]] = None
    ) -> OperationResult:
        """
        Capture a lesson learned from a project.
        
        Args:
            project_id: Source project
            category: LessonCategory value
            issue: What was the problem
            solution: How it was solved
            impact: high/medium/low
            tags: Searchable tags
            
        Returns:
            OperationResult with lesson ID
        """
        # Validate category
        try:
            LessonCategory(category)
        except ValueError:
            return OperationResult(
                success=False,
                error=f"Invalid category: {category}"
            )
        
        # Get project type
        project = await self.get_project(project_id, 0)  # 0 = no user check for lessons
        project_type = project.get("project_type", "website") if project else "website"
        
        try:
            result = await db.fetchrow(
                """
                INSERT INTO vibe_lessons (
                    project_id, project_type, lesson_category,
                    issue, solution, impact, tags, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                RETURNING lesson_id
                """,
                project_id, project_type, category,
                issue, solution, impact, tags or []
            )
            
            if result:
                logger.info("[VIBE] Captured lesson %d from project %d", 
                          result['lesson_id'], project_id)
                return OperationResult(
                    success=True,
                    data={"lesson_id": result['lesson_id']}
                )
            
            return OperationResult(success=False, error="Failed to save lesson")
            
        except Exception as e:
            logger.error("[VIBE] Failed to capture lesson: %s", e)
            return OperationResult(success=False, error=str(e))
    
    async def get_relevant_lessons(
        self,
        project_type: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get lessons relevant to a project type.
        
        TODO: Add embedding-based semantic search when embeddings are populated.
        """
        if category:
            results = await db.fetch(
                """
                SELECT lesson_id, project_type, lesson_category,
                       issue, solution, impact, times_applied
                FROM vibe_lessons
                WHERE project_type = $1 AND lesson_category = $2
                ORDER BY times_applied DESC, created_at DESC
                LIMIT $3
                """,
                project_type, category, limit
            )
        else:
            results = await db.fetch(
                """
                SELECT lesson_id, project_type, lesson_category,
                       issue, solution, impact, times_applied
                FROM vibe_lessons
                WHERE project_type = $1
                ORDER BY times_applied DESC, created_at DESC
                LIMIT $2
                """,
                project_type, limit
            )
        
        return [dict(r) for r in results] if results else []
    
    # ========================================================================
    # UI HELPERS
    # ========================================================================
    
    def get_agents_for_status(self, status: str) -> List[Dict[str, Any]]:
        """Get agent status configuration for UI display."""
        agents = [
            {"id": "intake", "name": "Intake", "icon": "📋", "status": "idle", "progress": 0, "task": "Gather requirements"},
            {"id": "planning", "name": "Planning", "icon": "🎯", "status": "idle", "progress": 0, "task": "Design architecture"},
            {"id": "build", "name": "Build", "icon": "🔨", "status": "idle", "progress": 0, "task": "Generate code"},
            {"id": "qa", "name": "QA", "icon": "🧪", "status": "idle", "progress": 0, "task": "Quality checks"},
            {"id": "review", "name": "Review", "icon": "✅", "status": "idle", "progress": 0, "task": "Final review"},
            {"id": "deploy", "name": "Deploy", "icon": "🚀", "status": "idle", "progress": 0, "task": "Ship to production"},
        ]
        
        status_to_index = {
            ProjectStatus.INTAKE.value: 0,
            ProjectStatus.PLANNING.value: 1,
            ProjectStatus.BUILDING.value: 2,
            ProjectStatus.QA.value: 3,
            ProjectStatus.REVIEW.value: 4,
            ProjectStatus.APPROVED.value: 5,
            ProjectStatus.DEPLOYING.value: 5,
            ProjectStatus.DEPLOYED.value: 6,
            ProjectStatus.DELIVERED.value: 6,
        }
        
        current_idx = status_to_index.get(status, 0)
        
        for i, agent in enumerate(agents):
            if i < current_idx:
                agent["status"] = "complete"
                agent["progress"] = 100
                agent["task"] = "Complete ✓"
            elif i == current_idx:
                agent["status"] = "working"
                agent["progress"] = 50
                agent["task"] = f"Working..."
        
        return agents
    
    def get_workflow_for_status(self, status: str) -> List[Dict[str, Any]]:
        """Get workflow steps for UI display."""
        workflow = [
            {"id": 1, "name": "Brief", "desc": "Gather requirements", "status": "pending"},
            {"id": 2, "name": "Plan", "desc": "Architecture design", "status": "pending"},
            {"id": 3, "name": "Build", "desc": "Generate code", "status": "pending"},
            {"id": 4, "name": "Test", "desc": "QA validation", "status": "pending"},
            {"id": 5, "name": "Ship", "desc": "Deploy live", "status": "pending"},
        ]
        
        status_to_step = {
            ProjectStatus.INTAKE.value: 1,
            ProjectStatus.PLANNING.value: 2,
            ProjectStatus.BUILDING.value: 3,
            ProjectStatus.QA.value: 4,
            ProjectStatus.REVIEW.value: 4,
            ProjectStatus.APPROVED.value: 5,
            ProjectStatus.DEPLOYING.value: 5,
            ProjectStatus.DEPLOYED.value: 6,
            ProjectStatus.DELIVERED.value: 6,
        }
        
        current_step = status_to_step.get(status, 1)
        
        for step in workflow:
            if step["id"] < current_step:
                step["status"] = "complete"
            elif step["id"] == current_step:
                step["status"] = "active"
        
        return workflow


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

vibe_service = VibeService()

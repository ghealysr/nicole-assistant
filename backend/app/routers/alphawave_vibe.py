"""
AlphaWave Vibe Router - Project Management API

Production-grade REST API for:
- Project CRUD with pagination
- Build pipeline execution with progress tracking
- File management and retrieval
- Activity logging and audit trail
- Lessons learning system with semantic search
- Real-time SSE progress streaming

Security Features:
- JWT authentication on all endpoints
- User-scoped access validation
- Per-user rate limiting with TTL cleanup

Reliability Features:
- Transaction-wrapped multi-step operations
- Retry logic for AI service calls
- Optimistic locking for concurrent protection
- Graceful error handling with friendly messages

Author: AlphaWave Architecture
Version: 2.1.0 (CTO Remediation Release)
"""

import logging
import time
import json
import asyncio
from collections import defaultdict, deque
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator

from app.middleware.alphawave_auth import get_current_user
from app.services.vibe_service import (
    vibe_service,
    ProjectStatus,
    ProjectType,
    LessonCategory,
    ActivityType,
    ProjectNotFoundError,
    InvalidStatusTransitionError,
    MissingPrerequisiteError,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Simple in-memory rate limiting (per user, per endpoint) with TTL cleanup
# -----------------------------------------------------------------------------
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_CLEANUP_INTERVAL = 300  # Clean stale buckets every 5 minutes
# Higher limits for polling endpoints
RATE_LIMIT_POLLING_ENDPOINTS = {
    "GET:/vibe/projects/{id}/activities": 60,  # Allow more frequent activity polling
    "GET:/vibe/projects/{id}/files": 60,  # Files can be polled frequently too
}
_rate_limit_buckets: Dict[str, deque] = defaultdict(deque)
_rate_limit_last_cleanup: float = 0.0


def _rate_limit_key(user_id: int, path: str) -> str:
    return f"{user_id}:{path}"


def _cleanup_stale_buckets(now: float) -> None:
    """Remove buckets that haven't been accessed in CLEANUP_INTERVAL seconds."""
    global _rate_limit_last_cleanup
    
    if now - _rate_limit_last_cleanup < RATE_LIMIT_CLEANUP_INTERVAL:
        return
    
    _rate_limit_last_cleanup = now
    stale_keys = []
    
    for key, bucket in _rate_limit_buckets.items():
        # If bucket is empty or all timestamps are old, mark for removal
        if not bucket or (now - bucket[-1] > RATE_LIMIT_WINDOW_SECONDS * 2):
            stale_keys.append(key)
    
    for key in stale_keys:
        del _rate_limit_buckets[key]
    
    if stale_keys:
        logger.debug("[VIBE] Rate limit cleanup: removed %d stale buckets", len(stale_keys))


def enforce_rate_limit(user_id: int, path: str):
    now = time.time()
    
    # Periodic cleanup of stale buckets to prevent memory leak
    _cleanup_stale_buckets(now)
    
    key = _rate_limit_key(user_id, path)
    bucket = _rate_limit_buckets[key]

    # Drop timestamps outside window
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()

    # Use higher limit for polling endpoints
    max_requests = RATE_LIMIT_POLLING_ENDPOINTS.get(path, RATE_LIMIT_MAX_REQUESTS)
    
    if len(bucket) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down and try again shortly."
        )

    bucket.append(now)

router = APIRouter(prefix="/vibe", tags=["Vibe Dashboard"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProjectCreate(BaseModel):
    """Create project request."""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    project_type: str = Field(..., description="Project type: website, chatbot, assistant, integration")
    client_name: Optional[str] = Field(None, max_length=200, description="Client business name")
    client_email: Optional[str] = Field(None, description="Client email address")
    
    @field_validator('project_type')
    @classmethod
    def validate_project_type(cls, v: str) -> str:
        valid_types = [t.value for t in ProjectType]
        if v not in valid_types:
            raise ValueError(f"Invalid project_type. Must be one of: {', '.join(valid_types)}")
        return v


class ProjectUpdate(BaseModel):
    """Update project request."""
    name: Optional[str] = Field(None, max_length=200)
    client_name: Optional[str] = Field(None, max_length=200)
    client_email: Optional[str] = None
    estimated_price: Optional[float] = Field(None, ge=0)


class IntakeMessage(BaseModel):
    """Intake conversation message."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation turns"
    )


class LessonCreate(BaseModel):
    """Create lesson request."""
    project_id: int = Field(..., description="Source project ID")
    category: str = Field(..., description="Lesson category")
    issue: str = Field(..., min_length=10, max_length=2000, description="What was the problem")
    solution: str = Field(..., min_length=10, max_length=2000, description="How it was solved")
    impact: str = Field(default="medium", description="Impact level: high, medium, low")
    tags: Optional[List[str]] = Field(default=None, description="Searchable tags")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid_cats = [c.value for c in LessonCategory]
        if v not in valid_cats:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_cats)}")
        return v
    
    @field_validator('impact')
    @classmethod
    def validate_impact(cls, v: str) -> str:
        if v not in ['high', 'medium', 'low']:
            raise ValueError("Impact must be: high, medium, or low")
        return v


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_id(user) -> int:
    """Extract user_id from authenticated user context."""
    user_id = getattr(user, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    return user_id


def rate_limit(user_id: int, path: str) -> None:
    """Apply simple per-user rate limiting for this path."""
    enforce_rate_limit(user_id, path)


def api_response_from_result(result) -> APIResponse:
    """Build a consistent APIResponse from an OperationResult-like object."""
    meta: Dict[str, Any] = {}
    if getattr(result, "api_cost", 0):
        meta["api_cost"] = float(result.api_cost)
    return APIResponse(
        success=result.success,
        data=result.data,
        error=result.error,
        meta=meta or None
    )


def handle_service_error(e: Exception, context: str) -> HTTPException:
    """Convert service exceptions to appropriate HTTP responses."""
    if isinstance(e, ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(e))
    elif isinstance(e, InvalidStatusTransitionError):
        return HTTPException(status_code=400, detail=str(e))
    elif isinstance(e, MissingPrerequisiteError):
        return HTTPException(status_code=400, detail=str(e))
    else:
        logger.error("[VIBE] %s error: %s", context, e)
        return HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROJECT ENDPOINTS
# ============================================================================

@router.post("/projects", response_model=APIResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Create a new Vibe project.
    
    Creates a project in 'intake' status, ready for requirements gathering.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects")
    
    result = await vibe_service.create_project(
        user_id=user_id,
        name=data.name,
        project_type=data.project_type,
        client_name=data.client_name,
        client_email=data.client_email
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return api_response_from_result(result)


@router.get("/projects", response_model=APIResponse)
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results offset"),
    user = Depends(get_current_user)
) -> APIResponse:
    """
    List user's Vibe projects with pagination.
    
    Excludes archived projects by default. Use status='archived' to see them.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects")
    
    # Validate status if provided
    if status:
        valid_statuses = [s.value for s in ProjectStatus]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
    
    projects, total = await vibe_service.list_projects(
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return APIResponse(
        success=True,
        data={"projects": projects},
        meta={
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(projects) < total
        }
    )


@router.get("/projects/{project_id}", response_model=APIResponse)
async def get_project(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get project details including agents and workflow status.
    
    Returns full project data with UI helper configurations.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}")
    
    project = await vibe_service.get_project(project_id, user_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get UI state helpers
    status = project.get("status", ProjectStatus.INTAKE.value)
    agents = vibe_service.get_agents_for_status(status)
    workflow = vibe_service.get_workflow_for_status(status)
    
    return APIResponse(
        success=True,
        data={
            "project": project,
            "agents": agents,
            "workflow": workflow
        }
    )


@router.patch("/projects/{project_id}", response_model=APIResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Update project fields.
    
    Only updates provided fields. Cannot change status directly (use pipeline endpoints).
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "PATCH:/vibe/projects/{id}")
    
    updates = data.model_dump(exclude_none=True)
    
    if not updates:
        project = await vibe_service.get_project(project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return APIResponse(success=True, data={"project": project})
    
    result = await vibe_service.update_project(
        project_id=project_id,
        user_id=user_id,
        updates=updates
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return APIResponse(success=True, data=result.data)


@router.delete("/projects/{project_id}", response_model=APIResponse)
async def delete_project(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Archive (soft delete) a project.
    
    Project data is preserved but hidden from default list.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "DELETE:/vibe/projects/{id}")
    
    result = await vibe_service.delete_project(project_id, user_id)
    
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    
    return APIResponse(success=True, data={"message": "Project archived"})


# ============================================================================
# BUILD PIPELINE ENDPOINTS
# ============================================================================

@router.post("/projects/{project_id}/intake", response_model=APIResponse)
async def run_intake(
    project_id: int,
    data: IntakeMessage,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Send a message in the intake conversation.
    
    Nicole will gather requirements and extract a structured brief when ready.
    The brief is extracted automatically when sufficient information is gathered.
    """
    import traceback
    
    try:
        user_id = get_user_id(user)
        logger.info(f"[INTAKE] Starting intake for project {project_id}, user {user_id}")
        rate_limit(user_id, "POST:/vibe/projects/{id}/intake")
        
        result = await vibe_service.run_intake(
            project_id=project_id,
            user_id=user_id,
            user_message=data.message,
            conversation_history=data.conversation_history
        )
        
        if not result.success:
            logger.error(f"[INTAKE] Failed: {result.error}")
            status_code = 400 if "status" in str(result.error).lower() else 500
            raise HTTPException(status_code=status_code, detail=result.error)
        
        logger.info(f"[INTAKE] Success for project {project_id}")
        return api_response_from_result(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTAKE] Unexpected error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/projects/{project_id}/plan", response_model=APIResponse)
async def run_architecture(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Generate architecture specification using Opus.
    
    Requires project to have a completed brief (status: planning).
    Produces detailed technical specification for the build phase.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/plan")
    
    result = await vibe_service.run_architecture(
        project_id=project_id,
        user_id=user_id
    )
    
    if not result.success:
        status_code = 400 if "status" in str(result.error).lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/build", response_model=APIResponse)
async def run_build(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Run the build phase - generate all code files.
    
    Requires completed architecture (status: building).
    Generates complete Next.js project with all pages and components.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/build")
    
    result = await vibe_service.run_build(
        project_id=project_id,
        user_id=user_id
    )
    
    if not result.success:
        status_code = 400 if "status" in str(result.error).lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/qa", response_model=APIResponse)
async def run_qa(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Run QA checks on generated files.
    
    Analyzes code for TypeScript errors, accessibility issues, SEO problems,
    and other quality concerns. Returns pass/fail with detailed issues list.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/qa")
    
    result = await vibe_service.run_qa(
        project_id=project_id,
        user_id=user_id
    )
    
    if not result.success:
        status_code = 400 if "status" in str(result.error).lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/review", response_model=APIResponse)
async def run_review(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Run final review using Opus.
    
    Comprehensive assessment of project quality, brief alignment, and
    client-readiness. Returns approval recommendation.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/review")
    
    result = await vibe_service.run_review(
        project_id=project_id,
        user_id=user_id
    )
    
    if not result.success:
        status_code = 400 if "status" in str(result.error).lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/approve", response_model=APIResponse)
async def approve_project(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Manually approve the project for deployment.
    
    Glen's explicit approval, separate from AI review.
    Marks project ready for the deployment phase.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/approve")
    
    result = await vibe_service.approve_project(
        project_id=project_id,
        user_id=user_id
    )
    
    if not result.success:
        status_code = 404 if "not found" in str(result.error).lower() else 400
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/deploy", response_model=APIResponse)
async def deploy_project(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Deploy the project.
    
    Currently a placeholder that sets URLs and marks as deployed.
    Future: Integrates with GitHub for repo creation and Vercel for hosting.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/deploy")
    
    result = await vibe_service.deploy_project(
        project_id=project_id,
        user_id=user_id
    )
    
    if not result.success:
        status_code = 400 if "status" in str(result.error).lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/retry", response_model=APIResponse)
async def retry_project_phase(
    project_id: int,
    target_status: Optional[str] = Query(None, description="Optional status to reset to: planning, building, qa, review"),
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Retry a stuck project phase.
    
    Use this when a project is stuck in planning/building/qa/review.
    Optionally reset to a specific status before retrying.
    
    Examples:
    - POST /projects/123/retry - retry current phase
    - POST /projects/123/retry?target_status=planning - reset to planning and retry
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/retry")
    
    result = await vibe_service.retry_phase(
        project_id=project_id,
        user_id=user_id,
        target_status=target_status
    )
    
    if not result.success:
        status_code = 400 if "invalid" in str(result.error).lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


# ============================================================================
# FILE ENDPOINTS
# ============================================================================

@router.get("/projects/{project_id}/files", response_model=APIResponse)
async def get_project_files(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get all files for a project with file tree structure.
    
    Returns flat file list and hierarchical tree for UI rendering.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/files")
    
    # Verify project access
    project = await vibe_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    files = await vibe_service.get_project_files(project_id)
    
    # Build file tree structure
    file_tree = build_file_tree(files)
    
    return APIResponse(
        success=True,
        data={
            "files": files,
            "file_tree": file_tree
        },
        meta={"count": len(files)}
    )


@router.get("/projects/{project_id}/inspirations", response_model=APIResponse)
async def get_project_inspirations(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get all saved inspirations (screenshots, references) for a project.
    
    Returns inspiration items with URLs, descriptions, and image URLs.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/inspirations")
    
    # Verify project access
    project = await vibe_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    inspirations = await vibe_service.get_project_inspirations(project_id)
    
    return APIResponse(
        success=True,
        data={
            "inspirations": inspirations
        },
        meta={"count": len(inspirations)}
    )


@router.get("/projects/{project_id}/files/{file_path:path}", response_model=APIResponse)
async def get_file_content(
    project_id: int,
    file_path: str,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get content of a specific file.
    
    Returns file content with detected language for syntax highlighting.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/files/{path}")
    
    # Verify project access
    project = await vibe_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    file = await vibe_service.get_file(project_id, file_path)
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Detect language from extension
    language = detect_language(file_path)
    
    return APIResponse(
        success=True,
        data={
            "file": file,
            "language": language
        }
    )


@router.get("/projects/{project_id}/stackblitz", response_model=APIResponse)
async def get_stackblitz_data(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get project data formatted for StackBlitz SDK.
    
    Returns files and design tokens for creating an interactive
    StackBlitz preview with full Next.js runtime.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/stackblitz")
    
    # Verify project access
    project = await vibe_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    files = await vibe_service.get_project_files(project_id)
    
    if not files:
        return APIResponse(
            success=True,
            data={
                "files": {},
                "design": {},
                "project_name": project.get("name", "Project"),
                "ready": False
            }
        )
    
    # Extract design from architecture
    architecture = project.get("architecture", {})
    if isinstance(architecture, str):
        try:
            architecture = json.loads(architecture)
        except:
            architecture = {}
    
    design = architecture.get("design_system", architecture.get("design", {}))
    colors = design.get("colors", {})
    typography = design.get("typography", {})
    
    # Convert files to dict format
    files_dict = {}
    for f in files:
        path = f.get("file_path", "")
        if path.startswith("/"):
            path = path[1:]
        files_dict[path] = f.get("content", "")
    
    return APIResponse(
        success=True,
        data={
            "files": files_dict,
            "design": {
                "primary_color": colors.get("primary", "#8B9D83"),
                "secondary_color": colors.get("secondary", "#F4E4BC"),
                "accent_color": colors.get("accent", "#D4A574"),
                "heading_font": typography.get("heading_font", "Playfair Display"),
                "body_font": typography.get("body_font", "Source Sans Pro"),
            },
            "project_name": project.get("name", "AlphaWave Project"),
            "ready": True
        }
    )


@router.get("/projects/{project_id}/preview", response_model=APIResponse)
async def get_project_preview(
    project_id: int,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Generate a renderable HTML preview from project files.
    
    Combines CSS and page components into a static HTML preview
    that can be displayed in an iframe.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/preview")
    
    # Verify project access
    project = await vibe_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    files = await vibe_service.get_project_files(project_id)
    
    if not files:
        return APIResponse(
            success=True,
            data={
                "html": """
                <!DOCTYPE html>
                <html>
                <head><title>Preview</title></head>
                <body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;">
                    <div style="text-align:center;color:#666;">
                        <p style="font-size:48px;margin:0;">🔧</p>
                        <p>No files generated yet. Run the build pipeline first.</p>
                    </div>
                </body>
                </html>
                """,
                "generated": False
            }
        )
    
    # Extract CSS
    css_content = ""
    for f in files:
        if f.get("file_path", "").endswith("globals.css"):
            css_content = f.get("content", "")
            # Strip Tailwind directives since we'll use CDN
            css_content = "\n".join(
                line for line in css_content.split("\n") 
                if not line.strip().startswith("@tailwind")
            )
            break
    
    # Extract design info from architecture
    architecture = project.get("architecture", {})
    if isinstance(architecture, str):
        try:
            architecture = json.loads(architecture)
        except:
            architecture = {}
    
    design = architecture.get("design_system", architecture.get("design", {}))
    colors = design.get("colors", {})
    typography = design.get("typography", {})
    
    # Get page content (simplified extraction)
    page_content = ""
    for f in files:
        path = f.get("file_path", "")
        if path.endswith("page.tsx") and "app/page" in path:
            content = f.get("content", "")
            # Extract JSX from the return statement (simplified)
            if "return" in content:
                # This is a rough extraction - works for simple cases
                page_content = content
            break
    
    # Extract component names used
    components_used = []
    for f in files:
        path = f.get("file_path", "")
        if "/components/" in path and path.endswith(".tsx"):
            name = path.split("/")[-1].replace(".tsx", "")
            content = f.get("content", "")
            components_used.append({"name": name, "content": content})
    
    # Build a static HTML preview using Tailwind CDN
    heading_font = typography.get("heading_font", "Playfair Display")
    body_font = typography.get("body_font", "Source Sans Pro")
    primary_color = colors.get("primary", "#8B9D83")
    secondary_color = colors.get("secondary", "#F4E4BC")
    accent_color = colors.get("accent", "#D4A574")
    
    brief = project.get("brief", {})
    if isinstance(brief, str):
        try:
            brief = json.loads(brief)
        except:
            brief = {}
    
    business_name = brief.get("business_name", architecture.get("content", {}).get("business_name", "Preview"))
    
    preview_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business_name} - Preview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family={heading_font.replace(' ', '+')}:wght@400;600;700&family={body_font.replace(' ', '+')}:wght@300;400;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '{primary_color}',
                        secondary: '{secondary_color}',
                        accent: '{accent_color}',
                        sage: '{primary_color}',
                        cream: '{secondary_color}',
                        'warm-brown': '{accent_color}',
                    }},
                    fontFamily: {{
                        heading: ['{heading_font}', 'serif'],
                        body: ['{body_font}', 'sans-serif'],
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ font-family: '{body_font}', sans-serif; }}
        h1, h2, h3, h4, h5, h6 {{ font-family: '{heading_font}', serif; }}
        {css_content}
    </style>
</head>
<body class="bg-white text-gray-800">
    <div class="preview-notice bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-center py-2 text-sm">
        ✨ Live Preview - Generated by AlphaWave Vibe
    </div>
    
    <!-- Header -->
    <header class="bg-white shadow-sm sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <h1 class="font-heading text-2xl font-bold text-primary">{business_name}</h1>
            <nav class="hidden md:flex space-x-6">
                <a href="#" class="text-gray-600 hover:text-primary">Home</a>
                <a href="#services" class="text-gray-600 hover:text-primary">Services</a>
                <a href="#about" class="text-gray-600 hover:text-primary">About</a>
                <a href="#contact" class="text-gray-600 hover:text-primary">Contact</a>
            </nav>
            <button class="bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary/90">
                Book Now
            </button>
        </div>
    </header>
    
    <!-- Hero -->
    <section class="relative bg-gradient-to-b from-secondary/30 to-white py-20 lg:py-32">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <h2 class="font-heading text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
                {brief.get('tagline', 'Welcome to ' + business_name)}
            </h2>
            <p class="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
                {brief.get('description', 'Professional services tailored to your needs.')[:200]}
            </p>
            <div class="flex flex-col sm:flex-row gap-4 justify-center">
                <button class="bg-primary text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-primary/90">
                    Get Started
                </button>
                <button class="border-2 border-primary text-primary px-8 py-3 rounded-lg text-lg font-semibold hover:bg-primary/10">
                    Learn More
                </button>
            </div>
        </div>
    </section>
    
    <!-- Services Preview -->
    <section id="services" class="py-16 bg-white">
        <div class="max-w-7xl mx-auto px-4">
            <h3 class="font-heading text-3xl font-bold text-center mb-12">Our Services</h3>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="bg-secondary/20 rounded-2xl p-6 text-center">
                    <div class="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-3xl">✨</span>
                    </div>
                    <h4 class="font-heading text-xl font-semibold mb-2">Service One</h4>
                    <p class="text-gray-600">Professional service tailored to your needs.</p>
                </div>
                <div class="bg-secondary/20 rounded-2xl p-6 text-center">
                    <div class="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-3xl">💫</span>
                    </div>
                    <h4 class="font-heading text-xl font-semibold mb-2">Service Two</h4>
                    <p class="text-gray-600">Expert guidance every step of the way.</p>
                </div>
                <div class="bg-secondary/20 rounded-2xl p-6 text-center">
                    <div class="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-3xl">🌟</span>
                    </div>
                    <h4 class="font-heading text-xl font-semibold mb-2">Service Three</h4>
                    <p class="text-gray-600">Comprehensive support and care.</p>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Footer -->
    <footer class="bg-gray-900 text-white py-12">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <h5 class="font-heading text-2xl font-bold mb-4">{business_name}</h5>
            <p class="text-gray-400 mb-4">{brief.get('location', '')}</p>
            <p class="text-gray-500 text-sm">&copy; 2025 {business_name}. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>
"""
    
    return APIResponse(
        success=True,
        data={
            "html": preview_html,
            "generated": True,
            "file_count": len(files),
            "design": {
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "heading_font": heading_font,
                "body_font": body_font
            }
        }
    )


# ============================================================================
# ACTIVITY ENDPOINTS
# ============================================================================

@router.get("/projects/{project_id}/activities", response_model=APIResponse)
async def get_project_activities(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200, description="Max activities to return"),
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get activity timeline for a project.
    
    Returns all activities (audit log) for the project, newest first.
    Useful for displaying timeline of project events.
    Access validation is performed by the service layer.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/activities")
    
    try:
        activities = await vibe_service.get_project_activities(project_id, user_id, limit)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return APIResponse(
        success=True,
        data={
            "activities": activities,
            "total_count": len(activities)
        }
    )


@router.get("/projects/{project_id}/progress/stream")
async def stream_project_progress(
    project_id: int,
    user = Depends(get_current_user)
):
    """
    Minimal SSE-like progress stream for a project.
    
    Emits current status and latest activities for a short polling window.
    Intended for UX feedback during long operations.
    """
    from fastapi.responses import StreamingResponse
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/progress/stream")

    async def event_generator():
        for _ in range(30):  # ~60 seconds at 2s interval (long-running builds)
            project = await vibe_service.get_project(project_id, user_id)
            if not project:
                yield f"data: {json.dumps({'error': 'Project not found'})}\n\n"
                break
            try:
                activities = await vibe_service.get_project_activities(project_id, user_id, limit=10)
            except ProjectNotFoundError:
                activities = []
            payload = {
                "status": project.get("status") if project else None,
                "updated_at": project.get("updated_at") if project else None,
                "activities": activities
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============================================================================
# LESSONS ENDPOINTS
# ============================================================================

@router.post("/lessons", response_model=APIResponse, status_code=201)
async def create_lesson(
    data: LessonCreate,
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Capture a lesson learned from a project.
    
    Lessons are stored for retrieval during future project planning.
    """
    user_id = get_user_id(user)  # Verify authenticated
    rate_limit(user_id, "POST:/vibe/lessons")
    
    result = await vibe_service.capture_lesson(
        project_id=data.project_id,
        category=data.category,
        issue=data.issue,
        solution=data.solution,
        impact=data.impact,
        tags=data.tags
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return APIResponse(success=True, data=result.data)


@router.get("/lessons", response_model=APIResponse)
async def get_lessons(
    project_type: str = Query(..., description="Project type to get lessons for"),
    category: Optional[str] = Query(None, description="Filter by category"),
    query: Optional[str] = Query(None, description="Semantic search query (uses embeddings)"),
    limit: int = Query(10, ge=1, le=50),
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get lessons relevant to a project type.
    
    Supports both category-based filtering and semantic search via embeddings.
    Returns lessons ordered by relevance (if query provided) or by application frequency.
    """
    user_id = get_user_id(user)  # Verify authenticated
    rate_limit(user_id, "GET:/vibe/lessons")
    
    # Validate project type
    valid_types = [t.value for t in ProjectType]
    if project_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid project_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Validate category if provided
    if category:
        valid_cats = [c.value for c in LessonCategory]
        if category not in valid_cats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(valid_cats)}"
            )
    
    lessons, semantic_used = await vibe_service.get_relevant_lessons(
        project_type=project_type,
        category=category,
        query=query,
        limit=limit
    )
    
    return APIResponse(
        success=True,
        data={"lessons": lessons},
        meta={"count": len(lessons), "semantic_used": semantic_used}
    )


@router.post("/lessons/backfill_embeddings", response_model=APIResponse)
async def backfill_lesson_embeddings(
    limit: int = Query(100, ge=1, le=500),
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Backfill embeddings for lessons missing vectors.
    
    Useful when enabling semantic search after lessons were created.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/lessons/backfill_embeddings")
    
    result = await vibe_service.backfill_lesson_embeddings(limit=limit)
    return APIResponse(success=True, data=result)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_file_tree(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build a hierarchical file tree from flat file list.
    
    Converts:
        [{"file_path": "app/page.tsx"}, {"file_path": "app/layout.tsx"}]
    To:
        [{"name": "app", "type": "folder", "children": [...]}]
    """
    root: Dict[str, Any] = {"children": {}}
    
    for file in files:
        path = file.get("file_path", "")
        if not path:
            continue
        
        parts = path.split("/")
        current = root
        
        for i, part in enumerate(parts):
            if not part:
                continue
            
            is_file = (i == len(parts) - 1)
            
            if part not in current["children"]:
                # Detect file type from extension
                if is_file and "." in part:
                    ext = part.rsplit(".", 1)[-1]
                    file_type = ext
                else:
                    file_type = "folder" if not is_file else "file"
                
                current["children"][part] = {
                    "name": part,
                    "type": file_type,
                    "path": "/".join(parts[:i + 1]),
                    "children": {} if not is_file else None
                }
            
            if not is_file:
                current = current["children"][part]
    
    def convert_to_list(node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert children dict to sorted list."""
        result = []
        children = node.get("children", {})
        
        if not children:
            return result
        
        # Sort: folders first, then files alphabetically
        sorted_items = sorted(
            children.items(),
            key=lambda x: (0 if x[1].get("type") == "folder" else 1, x[0].lower())
        )
        
        for key, value in sorted_items:
            item = {
                "name": value["name"],
                "type": value["type"],
                "path": value.get("path", "")
            }
            
            if value.get("children"):
                item["children"] = convert_to_list(value)
            
            result.append(item)
        
        return result
    
    return convert_to_list(root)


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    if not file_path or "." not in file_path:
        return "text"
    
    ext = file_path.rsplit(".", 1)[-1].lower()
    
    language_map = {
        "tsx": "typescript",
        "ts": "typescript",
        "jsx": "javascript",
        "js": "javascript",
        "css": "css",
        "scss": "scss",
        "less": "less",
        "json": "json",
        "md": "markdown",
        "html": "html",
        "htm": "html",
        "py": "python",
        "yaml": "yaml",
        "yml": "yaml",
        "sh": "bash",
        "bash": "bash",
        "sql": "sql",
    }
    
    return language_map.get(ext, "text")


# ============================================================================
# MODEL HEALTH ENDPOINTS
# ============================================================================

@router.get("/models/health", response_model=APIResponse)
async def get_model_health(
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get health status of AI models.
    
    Returns availability and cooldown status for all models used
    in the Vibe pipeline (Gemini 3 Pro, Claude Opus, Claude Sonnet).
    """
    from app.services.model_orchestrator import model_orchestrator
    
    health_summary = model_orchestrator.get_health_summary()
    
    return APIResponse(
        success=True,
        data={
            "models": health_summary,
            "orchestrator_version": "2.0.0",
            "strategy": "gemini_3_pro_design_claude_architecture"
        }
    )


@router.get("/agents/status", response_model=APIResponse)
async def get_agent_status(
    user = Depends(get_current_user)
) -> APIResponse:
    """
    Get Nicole's agent orchestration status.
    
    Returns active tasks assigned to each agent and performance metrics.
    Nicole (Creative Director) maintains authority over all agents.
    """
    from app.services.model_orchestrator import nicole_authority, model_orchestrator
    from app.services.vibe_agents import AGENT_DEFINITIONS, AgentRole
    
    # Build agent info from definitions
    agents_info = {}
    for role, agent in AGENT_DEFINITIONS.items():
        agents_info[agent.role.value] = {
            "display_name": agent.display_name,
            "emoji": agent.emoji,
            "model": agent.model,
            "capabilities": agent.capabilities,
            "tools": agent.tools,
            "handoff_to": agent.handoff_to.value if agent.handoff_to else None
        }
    
    return APIResponse(
        success=True,
        data={
            "authority": "nicole",
            "authority_title": "Creative Director",
            "active_tasks": nicole_authority.get_active_tasks(),
            "agent_performance": nicole_authority.get_agent_performance(),
            "agent_health": model_orchestrator.get_health_summary(),
            "pipeline": ["design_agent", "architect_agent", "coding_agent", "qa_agent", "review_agent"],
            "agents": agents_info
        }
    )

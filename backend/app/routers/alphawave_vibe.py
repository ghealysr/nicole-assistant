"""
AlphaWave Vibe Router - Project Management API

Production-grade REST API for:
- Project CRUD with pagination
- Build pipeline execution with progress tracking
- File management and retrieval
- Lessons learning system

Author: AlphaWave Architecture
Version: 2.0.0
"""

import logging
import time
import json
import asyncio
from collections import defaultdict, deque
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator

from app.middleware.alphawave_auth import verify_jwt
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
# Simple in-memory rate limiting (per user, per endpoint)
# -----------------------------------------------------------------------------
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30
_rate_limit_buckets: Dict[str, deque] = defaultdict(deque)


def _rate_limit_key(user_id: int, path: str) -> str:
    return f"{user_id}:{path}"


def enforce_rate_limit(user_id: int, path: str):
    now = time.time()
    key = _rate_limit_key(user_id, path)
    bucket = _rate_limit_buckets[key]

    # Drop timestamps outside window
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
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

def get_user_id(user: dict) -> int:
    """Extract user_id from JWT payload with validation."""
    user_id = user.get("user_id")
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
) -> APIResponse:
    """
    Send a message in the intake conversation.
    
    Nicole will gather requirements and extract a structured brief when ready.
    The brief is extracted automatically when sufficient information is gathered.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "POST:/vibe/projects/{id}/intake")
    
    result = await vibe_service.run_intake(
        project_id=project_id,
        user_id=user_id,
        user_message=data.message,
        conversation_history=data.conversation_history
    )
    
    if not result.success:
        status_code = 400 if "status" in str(result.error).lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/plan", response_model=APIResponse)
async def run_architecture(
    project_id: int,
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
        status_code = 400 if "not found" in str(result.error).lower() else 400
        raise HTTPException(status_code=status_code, detail=result.error)
    
    return api_response_from_result(result)


@router.post("/projects/{project_id}/deploy", response_model=APIResponse)
async def deploy_project(
    project_id: int,
    user: dict = Depends(verify_jwt)
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


# ============================================================================
# FILE ENDPOINTS
# ============================================================================

@router.get("/projects/{project_id}/files", response_model=APIResponse)
async def get_project_files(
    project_id: int,
    user: dict = Depends(verify_jwt)
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


@router.get("/projects/{project_id}/files/{file_path:path}", response_model=APIResponse)
async def get_file_content(
    project_id: int,
    file_path: str,
    user: dict = Depends(verify_jwt)
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


# ============================================================================
# ACTIVITY ENDPOINTS
# ============================================================================

@router.get("/projects/{project_id}/activities", response_model=APIResponse)
async def get_project_activities(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200, description="Max activities to return"),
    user: dict = Depends(verify_jwt)
) -> APIResponse:
    """
    Get activity timeline for a project.
    
    Returns all activities (audit log) for the project, newest first.
    Useful for displaying timeline of project events.
    """
    user_id = get_user_id(user)
    rate_limit(user_id, "GET:/vibe/projects/{id}/activities")
    
    # Verify project access first
    project = await vibe_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    activities = await vibe_service.get_project_activities(project_id, limit)
    
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
    user: dict = Depends(verify_jwt)
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
        for _ in range(5):  # ~10 seconds at 2s interval
            project = await vibe_service.get_project(project_id, user_id)
            activities = await vibe_service.get_project_activities(project_id, limit=10)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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
    user: dict = Depends(verify_jwt)
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

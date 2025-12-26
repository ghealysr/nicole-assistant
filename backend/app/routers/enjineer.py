"""
Enjineer Router
AI-powered development environment endpoints
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

from app.database import db, get_tiger_pool
from app.middleware.alphawave_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enjineer", tags=["enjineer"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ProjectSettings(BaseModel):
    vercel_token: Optional[str] = None
    github_repo: Optional[str] = None
    budget_limit: Optional[float] = 50.0
    total_spent: Optional[float] = 0.0
    theme: Optional[str] = "dark"


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    tech_stack: Optional[dict] = Field(default_factory=dict)
    intake_data: Optional[dict] = Field(default_factory=dict)
    inspiration_images: Optional[List[str]] = Field(default_factory=list)  # Base64 data URLs
    design_mode: Optional[str] = Field(default="quick")  # 'quick' or 'research'


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[dict] = None


class CreateFileRequest(BaseModel):
    path: str = Field(..., min_length=1)
    content: str
    language: Optional[str] = None


class UpdateFileRequest(BaseModel):
    content: str
    commit_message: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    attachments: Optional[List[dict]] = Field(default_factory=list)


class ApprovalActionRequest(BaseModel):
    note: Optional[str] = None
    reason: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    tech_stack: dict
    status: str
    intake_data: dict
    settings: dict
    created_at: str
    updated_at: str
    design_mode: str = "quick"
    research_session_id: Optional[int] = None
    active_style_guide_id: Optional[int] = None


class FileResponse(BaseModel):
    id: int
    project_id: int
    path: str
    content: str
    language: str
    version: int
    modified_by: Optional[str]
    locked_by: Optional[str]
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    project_id: int
    role: str
    content: str
    attachments: list
    metadata: dict
    created_at: str


class ApprovalResponse(BaseModel):
    id: int
    project_id: int
    approval_type: str
    title: str
    description: Optional[str]
    status: str
    requested_at: str
    expires_at: Optional[str]


# ============================================================================
# Utility Functions
# ============================================================================

def detect_language(path: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".ts": "typescript",
        ".tsx": "typescriptreact",
        ".js": "javascript",
        ".jsx": "javascriptreact",
        ".py": "python",
        ".css": "css",
        ".scss": "scss",
        ".html": "html",
        ".json": "json",
        ".md": "markdown",
        ".sql": "sql",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    ext = os.path.splitext(path)[1].lower()
    return ext_map.get(ext, "plaintext")


def get_user_id_from_context(user) -> int:
    """Extract user ID from authenticated user context as integer."""
    # user is a UserContext object from alphawave_auth middleware
    # The middleware sets user.user_id = tiger_user_id (the integer from Tiger Postgres)
    if hasattr(user, 'user_id') and user.user_id:
        return user.user_id
    raise HTTPException(status_code=401, detail="Not authenticated - no user_id")


async def verify_project_access(pool, project_id: int, user_id: int) -> dict:
    """Verify user has access to project and return project data."""
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            "SELECT * FROM enjineer_projects WHERE id = $1 AND user_id = $2",
            project_id, user_id
        )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return dict(project)


# ============================================================================
# Project Endpoints
# ============================================================================

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    user = Depends(get_current_user)
):
    """Create a new Enjineer project with optional inspiration image analysis."""
    user_id = get_user_id_from_context(user)
    pool = await get_tiger_pool()
    
    # Build intake data with inspiration images
    intake_data = request.intake_data or {}
    
    # Store inspiration images and analyze them with Claude Vision
    if request.inspiration_images:
        intake_data["inspiration_images"] = request.inspiration_images
        
        # Analyze images with Claude Vision to extract design elements
        try:
            from anthropic import AsyncAnthropic
            import os
            
            client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            # Build image content for Claude
            image_content = []
            for img_data in request.inspiration_images[:3]:  # Limit to 3 images
                # Extract base64 and media type from data URL
                if img_data.startswith("data:"):
                    parts = img_data.split(",", 1)
                    if len(parts) == 2:
                        media_type = parts[0].split(":")[1].split(";")[0]
                        base64_data = parts[1]
                        image_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        })
            
            if image_content:
                # Ask Claude to analyze the inspiration images
                image_content.append({
                    "type": "text",
                    "text": """Analyze these design inspiration images and extract the following:

1. **Color Palette**: List the primary, secondary, and accent colors (include hex codes if determinable)
2. **Typography Style**: Describe the font styles (serif/sans-serif, weight, size hierarchy)
3. **Layout Patterns**: Describe the layout structure (grid, sections, spacing)
4. **UI Components**: List key UI elements visible (buttons, cards, forms, navigation)
5. **Design Style**: Overall aesthetic (minimal, bold, retro, modern, etc.)
6. **Visual Effects**: Any gradients, shadows, animations, or special effects
7. **Key Features**: Notable design patterns worth replicating

Format your response as JSON with these exact keys:
{
  "color_palette": {"primary": "#...", "secondary": "#...", "accent": "#...", "background": "#...", "text": "#..."},
  "typography": {"style": "...", "heading_font": "...", "body_font": "..."},
  "layout": "...",
  "components": ["...", "..."],
  "design_style": "...",
  "visual_effects": ["...", "..."],
  "key_features": ["...", "..."],
  "summary": "One paragraph summary of the overall design direction"
}"""
                })
                
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": image_content}]
                )
                
                # Parse the analysis
                analysis_text = response.content[0].text
                
                # Try to extract JSON from the response
                import json
                try:
                    # Find JSON in the response
                    json_start = analysis_text.find("{")
                    json_end = analysis_text.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        design_analysis = json.loads(analysis_text[json_start:json_end])
                        intake_data["design_analysis"] = design_analysis
                        logger.info(f"[Enjineer] Analyzed inspiration images: {design_analysis.get('design_style', 'unknown')}")
                except json.JSONDecodeError:
                    # Store raw analysis if JSON parsing fails
                    intake_data["design_analysis"] = {"raw": analysis_text}
                    logger.warning("[Enjineer] Could not parse design analysis as JSON, stored raw")
                    
        except Exception as e:
            logger.error(f"[Enjineer] Failed to analyze inspiration images: {e}")
            intake_data["design_analysis"] = {"error": str(e)}
    
    # Determine design mode
    design_mode = request.design_mode or "quick"
    if design_mode not in ("quick", "research"):
        design_mode = "quick"
    
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            """
            INSERT INTO enjineer_projects (user_id, name, description, tech_stack, intake_data, settings, design_mode)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            user_id,
            request.name,
            request.description,
            request.tech_stack or {},
            intake_data,
            {"budget_limit": 50.0, "total_spent": 0.0, "theme": "dark"},
            design_mode
        )
    
    logger.info(f"Created Enjineer project: {project['id']}")
    
    return ProjectResponse(
        id=project["id"],
        user_id=project["user_id"],
        name=project["name"],
        description=project["description"],
        tech_stack=project["tech_stack"] or {},
        status=project["status"],
        intake_data=project["intake_data"] or {},
        settings=project["settings"] or {},
        created_at=project["created_at"].isoformat(),
        updated_at=project["updated_at"].isoformat(),
        design_mode=project.get("design_mode") or "quick",
        research_session_id=project.get("research_session_id"),
        active_style_guide_id=project.get("active_style_guide_id")
    )


@router.get("/projects")
async def list_projects(
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user = Depends(get_current_user)
):
    """List user's Enjineer projects."""
    user_id = get_user_id_from_context(user)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        if status:
            projects = await conn.fetch(
                """
                SELECT * FROM enjineer_projects 
                WHERE user_id = $1 AND status = $2
                ORDER BY updated_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id, status, limit, offset
            )
        else:
            projects = await conn.fetch(
                """
                SELECT * FROM enjineer_projects 
                WHERE user_id = $1
                ORDER BY updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )
    
    return [
        ProjectResponse(
            id=p["id"],
            user_id=p["user_id"],
            name=p["name"],
            description=p["description"],
            tech_stack=p["tech_stack"] or {},
            status=p["status"],
            intake_data=p["intake_data"] or {},
            settings=p["settings"] or {},
            created_at=p["created_at"].isoformat(),
            updated_at=p["updated_at"].isoformat(),
            design_mode=p.get("design_mode") or "quick",
            research_session_id=p.get("research_session_id"),
            active_style_guide_id=p.get("active_style_guide_id")
        )
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    user = Depends(get_current_user)
):
    """Get project details with files and current plan."""
    user_id = get_user_id_from_context(user)
    project = await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        # Get files
        files = await conn.fetch(
            "SELECT * FROM enjineer_files WHERE project_id = $1 ORDER BY path",
            project_id
        )
        
        # Get current plan
        plan = await conn.fetchrow(
            """
            SELECT * FROM enjineer_plans 
            WHERE project_id = $1 AND status NOT IN ('abandoned', 'completed')
            ORDER BY created_at DESC LIMIT 1
            """,
            project_id
        )
        
        # Get pending approvals
        approvals = await conn.fetch(
            "SELECT * FROM enjineer_approvals WHERE project_id = $1 AND status = 'pending'",
            project_id
        )
    
    return {
        "project": ProjectResponse(
            id=project["id"],
            user_id=project["user_id"],
            name=project["name"],
            description=project["description"],
            tech_stack=project["tech_stack"] or {},
            status=project["status"],
            intake_data=project["intake_data"] or {},
            settings=project["settings"] or {},
            created_at=project["created_at"].isoformat(),
            updated_at=project["updated_at"].isoformat(),
            design_mode=project.get("design_mode") or "quick",
            research_session_id=project.get("research_session_id"),
            active_style_guide_id=project.get("active_style_guide_id")
        ),
        "files": [
            FileResponse(
                id=f["id"],
                project_id=f["project_id"],
                path=f["path"],
                content=f["content"] or "",
                language=f["language"] or "plaintext",
                version=f["version"],
                modified_by=f["modified_by"],
                locked_by=f["locked_by"],
                created_at=f["created_at"].isoformat(),
                updated_at=f["updated_at"].isoformat()
            )
            for f in files
        ],
        "plan": dict(plan) if plan else None,
        "pending_approvals": [
            ApprovalResponse(
                id=a["id"],
                project_id=a["project_id"],
                approval_type=a["approval_type"],
                title=a["title"],
                description=a["description"],
                status=a["status"],
                requested_at=a["requested_at"].isoformat(),
                expires_at=a["expires_at"].isoformat() if a["expires_at"] else None
            )
            for a in approvals
        ]
    }


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: int,
    request: UpdateProjectRequest,
    user = Depends(get_current_user)
):
    """Update project details."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    updates = []
    values = []
    param_count = 1
    
    if request.name is not None:
        updates.append(f"name = ${param_count}")
        values.append(request.name)
        param_count += 1
    
    if request.description is not None:
        updates.append(f"description = ${param_count}")
        values.append(request.description)
        param_count += 1
    
    if request.status is not None:
        if request.status not in ('active', 'paused', 'completed', 'abandoned'):
            raise HTTPException(status_code=400, detail="Invalid status")
        updates.append(f"status = ${param_count}")
        values.append(request.status)
        param_count += 1
    
    if request.settings is not None:
        updates.append(f"settings = settings || ${param_count}")
        values.append(request.settings)
        param_count += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    values.append(project_id)
    
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            f"""
            UPDATE enjineer_projects 
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING *
            """,
            *values
        )
    
    return ProjectResponse(
        id=project["id"],
        user_id=project["user_id"],
        name=project["name"],
        description=project["description"],
        tech_stack=project["tech_stack"] or {},
        status=project["status"],
        intake_data=project["intake_data"] or {},
        settings=project["settings"] or {},
        created_at=project["created_at"].isoformat(),
        updated_at=project["updated_at"].isoformat(),
        design_mode=project.get("design_mode") or "quick",
        research_session_id=project.get("research_session_id"),
        active_style_guide_id=project.get("active_style_guide_id")
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    user = Depends(get_current_user)
):
    """Soft delete a project (set status to abandoned)."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE enjineer_projects SET status = 'abandoned' WHERE id = $1",
            project_id
        )
    
    return {"success": True}


# ============================================================================
# File Endpoints
# ============================================================================

@router.get("/projects/{project_id}/files")
async def list_files(
    project_id: int,
    path_prefix: Optional[str] = None,
    user = Depends(get_current_user)
):
    """List project files."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        if path_prefix:
            files = await conn.fetch(
                """
                SELECT * FROM enjineer_files 
                WHERE project_id = $1 AND path LIKE $2
                ORDER BY path
                """,
                project_id, f"{path_prefix}%"
            )
        else:
            files = await conn.fetch(
                "SELECT * FROM enjineer_files WHERE project_id = $1 ORDER BY path",
                project_id
            )
    
    return [
        FileResponse(
            id=f["id"],
            project_id=f["project_id"],
            path=f["path"],
            content=f["content"] or "",
            language=f["language"] or "plaintext",
            version=f["version"],
            modified_by=f["modified_by"],
            locked_by=f["locked_by"],
            created_at=f["created_at"].isoformat(),
            updated_at=f["updated_at"].isoformat()
        )
        for f in files
    ]


@router.post("/projects/{project_id}/files")
async def create_file(
    project_id: int,
    request: CreateFileRequest,
    user = Depends(get_current_user)
):
    """Create a new file."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    language = request.language or detect_language(request.path)
    checksum = hashlib.sha256(request.content.encode()).hexdigest()
    
    async with pool.acquire() as conn:
        # Check if file exists
        existing = await conn.fetchrow(
            "SELECT id FROM enjineer_files WHERE project_id = $1 AND path = $2",
            project_id, request.path
        )
        
        if existing:
            raise HTTPException(status_code=409, detail="File already exists")
        
        # Create file
        file = await conn.fetchrow(
            """
            INSERT INTO enjineer_files (project_id, path, content, language, modified_by, checksum)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            project_id, request.path, request.content, language, "user", checksum
        )
        
        # Create initial version
        await conn.execute(
            """
            INSERT INTO enjineer_file_versions (file_id, version, content, modified_by, commit_message)
            VALUES ($1, 1, $2, $3, $4)
            """,
            file["id"], request.content, "user", "Initial creation"
        )
    
    logger.info(f"Created file: {request.path} in project {project_id}")
    
    return FileResponse(
        id=file["id"],
        project_id=file["project_id"],
        path=file["path"],
        content=file["content"] or "",
        language=file["language"] or "plaintext",
        version=file["version"],
        modified_by=file["modified_by"],
        locked_by=file["locked_by"],
        created_at=file["created_at"].isoformat(),
        updated_at=file["updated_at"].isoformat()
    )


@router.get("/projects/{project_id}/files/{file_path:path}")
async def get_file(
    project_id: int,
    file_path: str,
    user = Depends(get_current_user)
):
    """Get file content."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        file = await conn.fetchrow(
            "SELECT * FROM enjineer_files WHERE project_id = $1 AND path = $2",
            project_id, f"/{file_path}" if not file_path.startswith("/") else file_path
        )
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        id=file["id"],
        project_id=file["project_id"],
        path=file["path"],
        content=file["content"] or "",
        language=file["language"] or "plaintext",
        version=file["version"],
        modified_by=file["modified_by"],
        locked_by=file["locked_by"],
        created_at=file["created_at"].isoformat(),
        updated_at=file["updated_at"].isoformat()
    )


@router.put("/projects/{project_id}/files/{file_path:path}")
async def update_file(
    project_id: int,
    file_path: str,
    request: UpdateFileRequest,
    user = Depends(get_current_user)
):
    """Update file content."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    path = f"/{file_path}" if not file_path.startswith("/") else file_path
    checksum = hashlib.sha256(request.content.encode()).hexdigest()
    
    async with pool.acquire() as conn:
        file = await conn.fetchrow(
            "SELECT * FROM enjineer_files WHERE project_id = $1 AND path = $2",
            project_id, path
        )
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check lock
        if file["locked_by"] and file["locked_by"] != "user":
            if file["lock_expires_at"] and file["lock_expires_at"] > datetime.utcnow():
                raise HTTPException(
                    status_code=423, 
                    detail=f"File locked by {file['locked_by']}"
                )
        
        new_version = file["version"] + 1
        
        # Update file
        updated = await conn.fetchrow(
            """
            UPDATE enjineer_files 
            SET content = $1, version = $2, modified_by = $3, checksum = $4
            WHERE id = $5
            RETURNING *
            """,
            request.content, new_version, "user", checksum, file["id"]
        )
        
        # Create version record
        await conn.execute(
            """
            INSERT INTO enjineer_file_versions (file_id, version, content, modified_by, commit_message)
            VALUES ($1, $2, $3, $4, $5)
            """,
            file["id"], new_version, request.content, "user", 
            request.commit_message or f"Updated to version {new_version}"
        )
    
    return FileResponse(
        id=updated["id"],
        project_id=updated["project_id"],
        path=updated["path"],
        content=updated["content"] or "",
        language=updated["language"] or "plaintext",
        version=updated["version"],
        modified_by=updated["modified_by"],
        locked_by=updated["locked_by"],
        created_at=updated["created_at"].isoformat(),
        updated_at=updated["updated_at"].isoformat()
    )


@router.delete("/projects/{project_id}/files/{file_path:path}")
async def delete_file(
    project_id: int,
    file_path: str,
    force: bool = False,
    user = Depends(get_current_user)
):
    """Delete a file."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    path = f"/{file_path}" if not file_path.startswith("/") else file_path
    
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM enjineer_files WHERE project_id = $1 AND path = $2",
            project_id, path
        )
    
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"success": True}


# ============================================================================
# Chat Endpoints
# ============================================================================

@router.get("/projects/{project_id}/messages")
async def get_messages(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user = Depends(get_current_user)
):
    """Get chat messages for a project."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        messages = await conn.fetch(
            """
            SELECT id, project_id, role, content, attachments, metadata, created_at
            FROM enjineer_messages
            WHERE project_id = $1
            ORDER BY created_at ASC
            LIMIT $2 OFFSET $3
            """,
            project_id, limit, offset
        )
        
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM enjineer_messages WHERE project_id = $1",
            project_id
        )
    
    return {
        "messages": [
            MessageResponse(
                id=m["id"],
                project_id=m["project_id"],
                role=m["role"],
                content=m["content"] or "",
                attachments=m["attachments"] or [],
                metadata=m["metadata"] or {},
                created_at=m["created_at"].isoformat()
            )
            for m in messages
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/projects/{project_id}/chat")
async def send_message(
    project_id: int,
    request: SendMessageRequest,
    user = Depends(get_current_user)
):
    """Send message to Nicole and stream response."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    # Save user message
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO enjineer_messages (project_id, role, content, attachments, metadata)
            VALUES ($1, 'user', $2, $3, $4)
            """,
            project_id, request.message, request.attachments or [], {}
        )
    
    async def generate_response():
        """
        Generate Server-Sent Events (SSE) response stream.
        
        All events are properly JSON-encoded to ensure frontend parsing works correctly.
        Events follow the SSE specification: "data: <json>\n\n"
        """
        try:
            from app.services.enjineer_nicole import EnjineerNicole
            
            nicole = EnjineerNicole(project_id, user_id)
            full_response = ""
            
            async for event in nicole.process_message(request.message, request.attachments):
                event_type = event.get("type", "unknown")
                
                # Build SSE payload based on event type
                if event_type == "text":
                    content = event.get("content", "")
                    full_response += content
                    payload = {"type": "text", "content": content}
                    
                elif event_type == "thinking":
                    payload = {"type": "thinking", "content": event.get("content", "")}
                    
                elif event_type == "tool_use":
                    payload = {
                        "type": "tool_use",
                        "tool": event.get("tool", "unknown"),
                        "input": event.get("input", {}),
                        "status": event.get("status", "running")
                    }
                    
                elif event_type == "tool_result":
                    payload = {
                        "type": "tool_result",
                        "tool": event.get("tool", "unknown"),
                        "result": event.get("result", {})
                    }
                    
                elif event_type == "code":
                    payload = {
                        "type": "code",
                        "path": event.get("path", ""),
                        "content": event.get("content", ""),
                        "action": event.get("action", "created")
                    }
                    
                elif event_type == "approval_required":
                    payload = {
                        "type": "approval_required",
                        "approval_id": event.get("approval_id", ""),
                        "title": event.get("title", "Action requires approval")
                    }
                    
                elif event_type == "error":
                    payload = {"type": "error", "content": event.get("content", "Unknown error")}
                    
                elif event_type == "done":
                    # Final event - save the full response first
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO enjineer_messages (project_id, role, content, metadata)
                            VALUES ($1, 'assistant', $2, $3)
                            """,
                            project_id, full_response, {}
                        )
                    payload = {"type": "done"}
                    
                else:
                    # Pass through unknown events
                    payload = event
                
                # Emit properly JSON-encoded SSE event
                yield f"data: {json.dumps(payload)}\n\n"
            
        except Exception as e:
            logger.error(f"Error in Nicole response: {e}", exc_info=True)
            error_payload = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_payload)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/projects/{project_id}/chat/history")
async def get_chat_history(
    project_id: int,
    limit: int = Query(default=50, le=200),
    before: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get conversation history."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        if before:
            messages = await conn.fetch(
                """
                SELECT * FROM enjineer_messages 
                WHERE project_id = $1 AND created_at < $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                project_id, datetime.fromisoformat(before), limit
            )
        else:
            messages = await conn.fetch(
                """
                SELECT * FROM enjineer_messages 
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                project_id, limit
            )
    
    # Reverse to get chronological order
    messages = list(reversed(messages))
    
    return [
        MessageResponse(
            id=m["id"],
            project_id=m["project_id"],
            role=m["role"],
            content=m["content"],
            attachments=m["attachments"] or [],
            metadata=m["metadata"] or {},
            created_at=m["created_at"].isoformat()
        )
        for m in messages
    ]


# ============================================================================
# Approval Endpoints
# ============================================================================

@router.get("/projects/{project_id}/approvals/pending")
async def get_pending_approvals(
    project_id: int,
    user = Depends(get_current_user)
):
    """Get pending approvals for project."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        approvals = await conn.fetch(
            """
            SELECT * FROM enjineer_approvals 
            WHERE project_id = $1 AND status = 'pending'
            ORDER BY requested_at
            """,
            project_id
        )
    
    return [
        ApprovalResponse(
            id=a["id"],
            project_id=a["project_id"],
            approval_type=a["approval_type"],
            title=a["title"],
            description=a["description"],
            status=a["status"],
            requested_at=a["requested_at"].isoformat(),
            expires_at=a["expires_at"].isoformat() if a["expires_at"] else None
        )
        for a in approvals
    ]


@router.post("/projects/{project_id}/approvals/{approval_id}/approve")
async def approve_request(
    project_id: int,
    approval_id: int,
    request: ApprovalActionRequest,
    user = Depends(get_current_user)
):
    """Approve a pending request."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        approval = await conn.fetchrow(
            """
            UPDATE enjineer_approvals 
            SET status = 'approved', responded_at = NOW(), response_note = $1
            WHERE id = $2 AND project_id = $3 AND status = 'pending'
            RETURNING *
            """,
            request.note, approval_id, project_id
        )
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found or already resolved")
    
    logger.info(f"Approved: {approval['title']}")
    
    return ApprovalResponse(
        id=approval["id"],
        project_id=approval["project_id"],
        approval_type=approval["approval_type"],
        title=approval["title"],
        description=approval["description"],
        status=approval["status"],
        requested_at=approval["requested_at"].isoformat(),
        expires_at=approval["expires_at"].isoformat() if approval["expires_at"] else None
    )


@router.post("/projects/{project_id}/approvals/{approval_id}/reject")
async def reject_request(
    project_id: int,
    approval_id: int,
    request: ApprovalActionRequest,
    user = Depends(get_current_user)
):
    """Reject a pending request."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    if not request.reason:
        raise HTTPException(status_code=400, detail="Rejection reason required")
    
    async with pool.acquire() as conn:
        approval = await conn.fetchrow(
            """
            UPDATE enjineer_approvals 
            SET status = 'rejected', responded_at = NOW(), response_note = $1
            WHERE id = $2 AND project_id = $3 AND status = 'pending'
            RETURNING *
            """,
            request.reason, approval_id, project_id
        )
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found or already resolved")
    
    logger.info(f"Rejected: {approval['title']} - Reason: {request.reason}")
    
    return ApprovalResponse(
        id=approval["id"],
        project_id=approval["project_id"],
        approval_type=approval["approval_type"],
        title=approval["title"],
        description=approval["description"],
        status=approval["status"],
        requested_at=approval["requested_at"].isoformat(),
        expires_at=approval["expires_at"].isoformat() if approval["expires_at"] else None
    )


# ============================================================================
# Usage Tracking Endpoints
# ============================================================================

@router.get("/projects/{project_id}/usage")
async def get_project_usage(
    project_id: int,
    user = Depends(get_current_user)
):
    """Get token usage and cost information for a project."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        # Get usage from project metadata
        project = await conn.fetchrow(
            "SELECT metadata FROM enjineer_projects WHERE id = $1",
            project_id
        )
        
        if project and project["metadata"]:
            usage = project["metadata"].get("usage", {})
            return {
                "inputTokens": usage.get("total_input_tokens", 0),
                "outputTokens": usage.get("total_output_tokens", 0),
                "totalCost": float(usage.get("total_cost_usd", 0)),
                "lastUpdated": usage.get("last_updated")
            }
        
        return {
            "inputTokens": 0,
            "outputTokens": 0,
            "totalCost": 0,
            "lastUpdated": None
        }


# ============================================================================
# Plan Endpoints
# ============================================================================

@router.get("/projects/{project_id}/plan")
async def get_plan(
    project_id: int,
    user = Depends(get_current_user)
):
    """Get the current plan for a project."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        # Schema: enjineer_plans has 'version' and 'content', NOT 'name'
        plan = await conn.fetchrow(
            """
            SELECT id, project_id, version, content, status, current_phase_number,
                   created_at, approved_at, completed_at
            FROM enjineer_plans 
            WHERE project_id = $1 AND status NOT IN ('abandoned', 'completed')
            ORDER BY created_at DESC LIMIT 1
            """,
            project_id
        )
        
        if not plan:
            return {"plan": None, "phases": []}
        
        # Get phases for this plan
        # Schema: enjineer_plan_phases has 'phase_number' not 'phase_order'
        phases = await conn.fetch(
            """
            SELECT id, plan_id, phase_number, name, status, estimated_minutes,
                   actual_minutes, agents_required, qa_depth, qa_focus,
                   requires_approval, approval_status, started_at, completed_at,
                   approved_at, notes
            FROM enjineer_plan_phases 
            WHERE plan_id = $1 
            ORDER BY phase_number
            """,
            plan["id"]
        )
    
    return {
        "plan": {
            "id": plan["id"],
            "version": plan["version"],
            "status": plan["status"],
            "currentPhase": plan["current_phase_number"],
            "createdAt": plan["created_at"].isoformat(),
            "approvedAt": plan["approved_at"].isoformat() if plan["approved_at"] else None,
        },
        "phases": [
            {
                "id": str(p["id"]),
                "phaseNumber": p["phase_number"],
                "name": p["name"],
                "notes": p["notes"],
                "status": p["status"],
                "estimatedMinutes": p["estimated_minutes"],
                "actualMinutes": p["actual_minutes"],
                "agentsRequired": p["agents_required"] or [],
                "qaDepth": p["qa_depth"],
                "qaFocus": p["qa_focus"] or [],
                "requiresApproval": p["requires_approval"],
                "approvalStatus": p["approval_status"],
                "startedAt": p["started_at"].isoformat() if p["started_at"] else None,
                "completedAt": p["completed_at"].isoformat() if p["completed_at"] else None,
                "approvedAt": p["approved_at"].isoformat() if p["approved_at"] else None,
            }
            for p in phases
        ]
    }


@router.post("/projects/{project_id}/plan/{plan_id}/approve")
async def approve_plan(
    project_id: int,
    plan_id: int,
    user = Depends(get_current_user)
):
    """Approve a plan to start implementation."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        # Update plan status to in_progress (workflow: awaiting_approval -> approved/in_progress)
        result = await conn.execute(
            """
            UPDATE enjineer_plans 
            SET status = 'in_progress', approved_at = NOW(), current_phase_number = 1
            WHERE id = $1 AND project_id = $2
            """,
            plan_id, project_id
        )
        
        # Set first phase to in_progress
        await conn.execute(
            """
            UPDATE enjineer_plan_phases 
            SET status = 'in_progress', started_at = NOW()
            WHERE plan_id = $1 AND phase_number = 1
            """,
            plan_id
        )
    
    return {"success": True, "message": "Plan approved. Implementation can begin."}


@router.post("/projects/{project_id}/plan/phases/{phase_id}/approve")
async def approve_phase(
    project_id: int,
    phase_id: int,
    user = Depends(get_current_user)
):
    """Approve a phase that requires approval."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        # Get current phase status
        phase = await conn.fetchrow(
            "SELECT status FROM enjineer_plan_phases WHERE id = $1", phase_id
        )
        
        # If phase was awaiting_approval (work done, needs approval), mark complete
        # Otherwise mark in_progress so work can continue
        new_status = 'complete' if phase and phase['status'] == 'awaiting_approval' else 'in_progress'
        
        await conn.execute(
            """
            UPDATE enjineer_plan_phases 
            SET approval_status = 'approved', approved_at = NOW(), 
                status = $2,
                completed_at = CASE WHEN $2 = 'complete' THEN NOW() ELSE completed_at END
            WHERE id = $1
            """,
            phase_id, new_status
        )
    
    return {"success": True, "new_status": new_status}


@router.post("/projects/{project_id}/plan/phases/{phase_id}/reject")
async def reject_phase(
    project_id: int,
    phase_id: int,
    user = Depends(get_current_user)
):
    """Reject a phase that requires approval."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE enjineer_plan_phases 
            SET approval_status = 'rejected', status = 'pending'
            WHERE id = $1
            """,
            phase_id
        )
    
    return {"success": True}


# ============================================================================
# Agent Dispatch Endpoints
# ============================================================================

class AgentTaskRequest(BaseModel):
    task: str = Field(..., min_length=1)


@router.post("/projects/{project_id}/agents/{agent}")
async def dispatch_agent(
    project_id: int,
    agent: str,
    request: AgentTaskRequest,
    user = Depends(get_current_user)
):
    """Dispatch an agent to work on a task."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    
    # Validate agent type matches DB constraint
    valid_agents = ['engineer', 'qa', 'sr_qa', 'nicole']
    if agent not in valid_agents:
        raise HTTPException(status_code=400, detail=f"Invalid agent. Must be one of: {valid_agents}")
    
    pool = await get_tiger_pool()
    
    # Create agent execution record
    # Schema: instruction TEXT NOT NULL (not 'task')
    async with pool.acquire() as conn:
        execution = await conn.fetchrow(
            """
            INSERT INTO enjineer_agent_executions (project_id, agent_type, instruction, status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING id, status, created_at
            """,
            project_id, agent, request.task
        )
    
    logger.info(f"Dispatched {agent} agent for project {project_id}, execution_id={execution['id']}")
    
    return {
        "taskId": str(execution["id"]),
        "agent": agent,
        "status": execution["status"],
        "createdAt": execution["created_at"].isoformat()
    }


# ============================================================================
# Deploy Endpoints
# ============================================================================

class DeployRequest(BaseModel):
    environment: str = Field(default="preview")


@router.post("/projects/{project_id}/deploy")
async def deploy_project(
    project_id: int,
    request: DeployRequest,
    user = Depends(get_current_user)
):
    """Deploy the project to Vercel."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    
    # Validate environment matches DB constraint
    valid_environments = ['preview', 'staging', 'production']
    if request.environment not in valid_environments:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid environment. Must be one of: {valid_environments}"
        )
    
    pool = await get_tiger_pool()
    
    # Create deployment record
    # Schema requires: platform TEXT NOT NULL
    async with pool.acquire() as conn:
        deployment = await conn.fetchrow(
            """
            INSERT INTO enjineer_deployments (project_id, platform, environment, status)
            VALUES ($1, 'vercel', $2, 'pending')
            RETURNING id, status, created_at
            """,
            project_id, request.environment
        )
    
    logger.info(f"Started {request.environment} deployment for project {project_id}, deployment_id={deployment['id']}")
    
    return {
        "deploymentId": str(deployment["id"]),
        "platform": "vercel",
        "environment": request.environment,
        "status": deployment["status"],
        "url": None,
        "createdAt": deployment["created_at"].isoformat()
    }


# ============================================================================
# QA Reports Endpoints
# ============================================================================

@router.get("/projects/{project_id}/qa-reports")
async def get_qa_reports(
    project_id: int,
    limit: int = Query(default=10, le=50),
    status: Optional[str] = Query(default=None, description="Filter by status: pass, fail, partial"),
    user = Depends(get_current_user)
):
    """
    Retrieve QA reports for a project.
    
    Returns:
        - List of QA reports with issues, status, and recommendations
        - Grouped issues by severity for action planning
    """
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        if status:
            reports = await conn.fetch(
                """
                SELECT 
                    id, project_id, execution_id, plan_id, phase_number,
                    trigger_type, qa_depth, overall_status,
                    checks, summary,
                    blocking_issues_count, warnings_count, passed_count,
                    model_used, tokens_used, estimated_cost_usd,
                    duration_seconds, created_at
                FROM enjineer_qa_reports 
                WHERE project_id = $1 AND overall_status = $2
                ORDER BY created_at DESC 
                LIMIT $3
                """,
                project_id, status, limit
            )
        else:
            reports = await conn.fetch(
                """
                SELECT 
                    id, project_id, execution_id, plan_id, phase_number,
                    trigger_type, qa_depth, overall_status,
                    checks, summary,
                    blocking_issues_count, warnings_count, passed_count,
                    model_used, tokens_used, estimated_cost_usd,
                    duration_seconds, created_at
                FROM enjineer_qa_reports 
                WHERE project_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
                """,
                project_id, limit
            )
    
    formatted_reports = []
    for report in reports:
        # Parse checks JSONB
        checks = report["checks"]
        if isinstance(checks, str):
            try:
                checks = json.loads(checks)
            except json.JSONDecodeError:
                checks = []
        
        # Group issues by severity
        issues_by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        if checks and isinstance(checks, list):
            for check in checks:
                severity = check.get("severity", "medium").lower()
                issue_data = {
                    "category": check.get("category"),
                    "file": check.get("file"),
                    "line": check.get("line"),
                    "issue": check.get("issue") or check.get("message"),
                    "fix": check.get("fix") or check.get("suggestion"),
                    "status": check.get("status", "open")
                }
                if severity in issues_by_severity:
                    issues_by_severity[severity].append(issue_data)
                else:
                    issues_by_severity["medium"].append(issue_data)
        
        formatted_reports.append({
            "id": str(report["id"]),
            "executionId": str(report["execution_id"]) if report["execution_id"] else None,
            "planId": str(report["plan_id"]) if report["plan_id"] else None,
            "phaseNumber": report["phase_number"],
            "triggerType": report["trigger_type"],
            "qaDepth": report["qa_depth"],
            "status": report["overall_status"],
            "modelUsed": report.get("model_used"),
            "tokensUsed": report.get("tokens_used"),
            "estimatedCostUsd": float(report["estimated_cost_usd"]) if report.get("estimated_cost_usd") else None,
            "summary": report["summary"],
            "counts": {
                "blocking": report["blocking_issues_count"] or 0,
                "warnings": report["warnings_count"] or 0,
                "passed": report["passed_count"] or 0
            },
            "issues": issues_by_severity,
            "durationSeconds": report["duration_seconds"],
            "createdAt": report["created_at"].isoformat() if report["created_at"] else None
        })
    
    return {
        "reports": formatted_reports,
        "count": len(formatted_reports),
        "projectId": project_id
    }


@router.get("/projects/{project_id}/qa-reports/{report_id}")
async def get_qa_report_detail(
    project_id: int,
    report_id: str,
    user = Depends(get_current_user)
):
    """Get detailed QA report by ID."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        report = await conn.fetchrow(
            """
            SELECT * FROM enjineer_qa_reports 
            WHERE id = $1 AND project_id = $2
            """,
            int(report_id), project_id
        )
    
    if not report:
        raise HTTPException(status_code=404, detail="QA report not found")
    
    # Parse checks JSONB
    checks = report["checks"]
    if isinstance(checks, str):
        try:
            checks = json.loads(checks)
        except json.JSONDecodeError:
            checks = []
    
    return {
        "id": str(report["id"]),
        "projectId": str(report["project_id"]),
        "executionId": str(report["execution_id"]) if report["execution_id"] else None,
        "planId": str(report["plan_id"]) if report["plan_id"] else None,
        "phaseNumber": report["phase_number"],
        "triggerType": report["trigger_type"],
        "qaDepth": report["qa_depth"],
        "status": report["overall_status"],
        "modelUsed": report.get("model_used"),
        "tokensUsed": report.get("tokens_used"),
        "estimatedCostUsd": float(report["estimated_cost_usd"]) if report.get("estimated_cost_usd") else None,
        "summary": report["summary"],
        "checks": checks,
        "blockingIssuesCount": report["blocking_issues_count"] or 0,
        "warningsCount": report["warnings_count"] or 0,
        "passedCount": report["passed_count"] or 0,
        "screenshots": report.get("screenshots") or [],
        "durationSeconds": report["duration_seconds"],
        "createdAt": report["created_at"].isoformat() if report["created_at"] else None
    }


# ============================================================================
# Preview Endpoints
# ============================================================================

class PreviewBundle(BaseModel):
    """Bundled preview data for frontend rendering."""
    project_id: int
    project_type: str  # 'static', 'react', 'nextjs', 'html'
    entry_file: str
    files: dict  # path -> content
    dependencies: dict  # package name -> version


def detect_project_type(files: dict) -> tuple[str, str]:
    """
    Detect project type from file structure.
    Returns (project_type, entry_file)
    """
    file_paths = list(files.keys())
    
    # Check for package.json to detect React/Next.js
    if 'package.json' in file_paths or '/package.json' in file_paths:
        pkg_content = files.get('package.json') or files.get('/package.json', '{}')
        try:
            pkg = json.loads(pkg_content)
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            
            if 'next' in deps:
                # Next.js project
                for entry in ['/app/page.tsx', '/pages/index.tsx', '/pages/index.js', 
                              'app/page.tsx', 'pages/index.tsx']:
                    if entry in file_paths or entry.lstrip('/') in file_paths:
                        return ('nextjs', entry)
                return ('nextjs', '/app/page.tsx')
            
            if 'react' in deps:
                # React project
                for entry in ['/src/App.tsx', '/src/App.jsx', '/src/App.js',
                              'src/App.tsx', 'src/App.jsx', 'src/App.js',
                              '/App.tsx', '/App.jsx', '/App.js']:
                    if entry in file_paths or entry.lstrip('/') in file_paths:
                        return ('react', entry)
                return ('react', '/src/App.tsx')
        except json.JSONDecodeError:
            pass
    
    # Check for index.html (static site)
    for entry in ['/index.html', 'index.html', '/public/index.html']:
        if entry in file_paths or entry.lstrip('/') in file_paths:
            return ('static', entry)
    
    # Default to HTML with first HTML file found
    html_files = [f for f in file_paths if f.endswith('.html')]
    if html_files:
        return ('html', html_files[0])
    
    # If we have .tsx or .jsx files, assume React
    react_files = [f for f in file_paths if f.endswith(('.tsx', '.jsx'))]
    if react_files:
        return ('react', react_files[0])
    
    # Last resort: return first file
    return ('html', file_paths[0] if file_paths else '/index.html')


def extract_dependencies(files: dict) -> dict:
    """Extract dependencies from package.json if present."""
    pkg_content = files.get('package.json') or files.get('/package.json')
    if not pkg_content:
        return {}
    
    try:
        pkg = json.loads(pkg_content)
        return pkg.get('dependencies', {})
    except json.JSONDecodeError:
        return {}


@router.get("/projects/{project_id}/preview/bundle")
async def get_preview_bundle(
    project_id: int,
    user = Depends(get_current_user)
):
    """
    Get bundled project files for preview rendering.
    
    Returns all files, detected project type, and dependencies
    for client-side preview using Sandpack or direct iframe.
    """
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        files = await conn.fetch(
            "SELECT path, content FROM enjineer_files WHERE project_id = $1",
            project_id
        )
    
    if not files:
        return {
            "project_id": project_id,
            "project_type": "html",
            "entry_file": "/index.html",
            "files": {
                "/index.html": """<!DOCTYPE html>
<html>
<head><title>Empty Project</title></head>
<body><h1>No files yet</h1><p>Ask Nicole to create your project files.</p></body>
</html>"""
            },
            "dependencies": {}
        }
    
    # Build file map
    file_map = {}
    for f in files:
        path = f["path"]
        # Normalize path to start with /
        if not path.startswith('/'):
            path = '/' + path
        file_map[path] = f["content"] or ""
    
    project_type, entry_file = detect_project_type(file_map)
    dependencies = extract_dependencies(file_map)
    
    return {
        "project_id": project_id,
        "project_type": project_type,
        "entry_file": entry_file,
        "files": file_map,
        "dependencies": dependencies
    }


@router.get("/projects/{project_id}/preview/html")
async def get_preview_html(
    project_id: int,
    user = Depends(get_current_user)
):
    """
    Get a complete HTML preview for ANY project type.
    
    - Static HTML: Returns with CSS/JS inlined
    - React/Next.js: Returns a self-contained HTML with React CDN and Babel for JSX
    
    This allows previewing React/Next.js projects without deployment.
    """
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        files = await conn.fetch(
            "SELECT path, content FROM enjineer_files WHERE project_id = $1",
            project_id
        )
    
    if not files:
        return HTMLResponse("""<!DOCTYPE html>
<html>
<head><title>Empty Project</title></head>
<body style="font-family: system-ui; background: #0a0a0f; color: #e2e8f0; padding: 2rem;">
<h1>No files yet</h1><p>Ask Nicole to create your project files.</p></body>
</html>""")
    
    # Build file map
    file_map = {f["path"]: f["content"] or "" for f in files}
    
    # Detect project type
    project_type, entry_file = detect_project_type(file_map)
    
    # =========================================================================
    # STATIC HTML PROJECTS
    # =========================================================================
    if project_type in ['static', 'html']:
        html_content = None
        for path in ['/index.html', 'index.html', '/public/index.html']:
            if path in file_map:
                html_content = file_map[path]
                break
        
        if not html_content:
            for path, content in file_map.items():
                if path.endswith('.html'):
                    html_content = content
                    break
        
        if html_content:
            # Inline CSS files
            for path, content in file_map.items():
                if path.endswith('.css'):
                    css_inline = f'<style>/* {path} */\n{content}</style>'
                    if '</head>' in html_content:
                        html_content = html_content.replace('</head>', f'{css_inline}\n</head>')
            
            # Inline JS files
            for path, content in file_map.items():
                if path.endswith('.js') and not path.endswith('.min.js'):
                    js_inline = f'<script>/* {path} */\n{content}</script>'
                    if '</body>' in html_content:
                        html_content = html_content.replace('</body>', f'{js_inline}\n</body>')
            
            return HTMLResponse(html_content)
    
    # =========================================================================
    # REACT / NEXT.JS PROJECTS - Generate preview with React CDN + Babel
    # =========================================================================
    
    # Collect all CSS
    all_css = []
    for path, content in file_map.items():
        if path.endswith('.css'):
            all_css.append(f"/* {path} */\n{content}")
    
    # Find the main component to render
    main_component = None
    main_component_name = "App"
    
    # Priority order for finding main component
    component_paths = [
        '/app/page.tsx', '/app/page.jsx', '/app/page.js',
        '/pages/index.tsx', '/pages/index.jsx', '/pages/index.js',
        '/src/App.tsx', '/src/App.jsx', '/src/App.js',
        '/App.tsx', '/App.jsx', '/App.js',
        'app/page.tsx', 'app/page.jsx', 'app/page.js',
        'pages/index.tsx', 'pages/index.jsx', 'pages/index.js',
        'src/App.tsx', 'src/App.jsx', 'src/App.js',
        'App.tsx', 'App.jsx', 'App.js',
    ]
    
    for comp_path in component_paths:
        normalized = comp_path if comp_path.startswith('/') else f'/{comp_path}'
        if normalized in file_map or comp_path in file_map:
            main_component = file_map.get(normalized) or file_map.get(comp_path)
            # Determine component name based on path
            if 'page.' in comp_path:
                main_component_name = "Page"
            else:
                main_component_name = "App"
            break
    
    if not main_component:
        # Find any .tsx or .jsx file
        for path, content in file_map.items():
            if path.endswith(('.tsx', '.jsx', '.js')) and 'export' in content:
                main_component = content
                # Extract component name from export
                if 'export default function' in content:
                    match = re.search(r'export default function (\w+)', content)
                    if match:
                        main_component_name = match.group(1)
                elif 'export default' in content:
                    main_component_name = "App"
                break
    
    # For complex multi-file projects, show a styled file explorer instead of fragile in-browser rendering
    def create_file_explorer_html(files: dict, css_content: list) -> str:
        """Create a beautiful file explorer view for complex projects."""
        file_items = []
        for path in sorted(files.keys()):
            content = files[path]
            # Escape HTML in content
            escaped_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # Determine file type for syntax highlighting class
            ext = path.split('.')[-1] if '.' in path else 'txt'
            file_items.append(f'''
                <div class="file-card" onclick="toggleFile(this)">
                    <div class="file-header">
                        <span class="file-icon">{get_file_icon(ext)}</span>
                        <span class="file-name">{path}</span>
                        <span class="file-toggle">▶</span>
                    </div>
                    <pre class="file-content" style="display:none;"><code class="language-{ext}">{escaped_content}</code></pre>
                </div>
            ''')
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Preview</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'SF Mono', 'Fira Code', monospace; 
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #e2e8f0; 
            min-height: 100vh;
            padding: 2rem;
        }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #2d2d4d;
        }}
        .header h1 {{
            font-size: 1.5rem;
            color: #8b5cf6;
            margin-bottom: 0.5rem;
        }}
        .header p {{
            color: #64748b;
            font-size: 0.875rem;
        }}
        .file-count {{
            display: inline-block;
            background: #8b5cf620;
            color: #8b5cf6;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            margin-top: 0.5rem;
        }}
        .file-card {{
            background: #12121a;
            border: 1px solid #1e1e2e;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            overflow: hidden;
            transition: all 0.2s;
        }}
        .file-card:hover {{
            border-color: #8b5cf640;
        }}
        .file-header {{
            display: flex;
            align-items: center;
            padding: 0.75rem 1rem;
            cursor: pointer;
            user-select: none;
        }}
        .file-header:hover {{
            background: #1e1e2e;
        }}
        .file-icon {{
            font-size: 1.25rem;
            margin-right: 0.75rem;
        }}
        .file-name {{
            flex: 1;
            font-weight: 500;
            color: #e2e8f0;
        }}
        .file-toggle {{
            color: #64748b;
            transition: transform 0.2s;
        }}
        .file-card.open .file-toggle {{
            transform: rotate(90deg);
        }}
        .file-content {{
            background: #0d0d12;
            border-top: 1px solid #1e1e2e;
            padding: 1rem;
            overflow-x: auto;
            font-size: 0.8rem;
            line-height: 1.6;
            max-height: 400px;
            overflow-y: auto;
        }}
        .file-content code {{
            color: #a5b4fc;
        }}
        /* Simple syntax highlighting */
        .keyword {{ color: #c792ea; }}
        .string {{ color: #c3e88d; }}
        .comment {{ color: #546e7a; font-style: italic; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📂 Project Files</h1>
        <p>Click on any file to view its contents</p>
        <span class="file-count">{len(files)} files</span>
    </div>
    {''.join(file_items)}
    <script>
        function toggleFile(card) {{
            card.classList.toggle('open');
            var content = card.querySelector('.file-content');
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        }}
    </script>
</body>
</html>'''
    
    def get_file_icon(ext):
        icons = {
            'tsx': '⚛️', 'jsx': '⚛️', 'ts': '📘', 'js': '📒',
            'css': '🎨', 'html': '🌐', 'json': '📋', 'md': '📝',
            'py': '🐍', 'txt': '📄'
        }
        return icons.get(ext, '📄')
    
    # For ALL React/Next.js projects, show the file explorer
    # In-browser Babel transformation is too fragile and unreliable
    # This provides a consistent, working experience for code review
    if project_type in ['react', 'nextjs']:
        return HTMLResponse(create_file_explorer_html(file_map, all_css))
    
    if not main_component:
        # No component found - show file explorer
        return HTMLResponse(create_file_explorer_html(file_map, all_css))
    
    # Clean up the component code for browser execution
    def clean_component_code(code: str) -> str:
        """Remove imports, TypeScript syntax, and exports for browser execution."""
        lines = code.split('\n')
        cleaned_lines = []
        in_multiline_import = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines at the start
            if not stripped and not cleaned_lines:
                continue
            
            # Handle multiline imports
            if in_multiline_import:
                if ';' in line or ('}' in line and 'from' in line):
                    in_multiline_import = False
                continue
            
            # Skip import statements (single line)
            if stripped.startswith('import '):
                # Check if it's a multiline import (has { but no } or no ;)
                if '{' in line and '}' not in line:
                    in_multiline_import = True
                continue
            
            # Skip 'use client' and 'use server' directives
            if stripped in ('"use client"', "'use client'", '"use server"', "'use server'"):
                continue
            
            cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        
        # Remove TypeScript-specific syntax
        result = re.sub(r': React\.FC(<[^>]*>)?', '', result)
        result = re.sub(r': React\.ReactNode', '', result)
        result = re.sub(r': React\.CSSProperties', '', result)
        result = re.sub(r': string(\[\])?', '', result)
        result = re.sub(r': number(\[\])?', '', result)
        result = re.sub(r': boolean', '', result)
        result = re.sub(r': any', '', result)
        result = re.sub(r': void', '', result)
        result = re.sub(r': \w+Props', '', result)
        result = re.sub(r'<\w+Props>', '', result)
        result = re.sub(r'<[A-Z]\w*(\s*,\s*[A-Z]\w*)*>', '', result)  # Generic types
        result = re.sub(r'interface \w+ \{[^}]*\}', '', result, flags=re.DOTALL)
        result = re.sub(r'type \w+ = [^;]+;', '', result)
        
        # Handle export statements
        result = re.sub(r'export default function (\w+)', r'function \1', result)
        result = re.sub(r'export default ', '', result)
        result = re.sub(r'export function (\w+)', r'function \1', result)
        result = re.sub(r'export const (\w+)', r'const \1', result)
        result = re.sub(r'export \{[^}]*\};?', '', result)  # Remove export { } statements
        
        return result
    
    component_code = clean_component_code(main_component)
    
    # Collect any additional components that might be needed
    additional_components = []
    for path, content in file_map.items():
        if path.endswith(('.tsx', '.jsx')) and content != main_component:
            if 'export' in content and ('function' in content or 'const' in content):
                cleaned = clean_component_code(content)
                additional_components.append(f"// {path}\n{cleaned}")
    
    # Escape the code for safe inclusion in HTML
    # Replace problematic characters that could break the script
    def escape_for_html_script(code):
        # Don't escape - we need the code to run as-is
        # Just make sure there are no </script> tags that would break out
        return code.replace('</script>', '<\\/script>')
    
    escaped_component = escape_for_html_script(component_code)
    escaped_additional = [escape_for_html_script(c) for c in additional_components]
    
    # Build the preview HTML with error handling
    preview_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview</title>
    
    <!-- React CDN -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    
    <!-- Babel for JSX transformation -->
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    
    <!-- Tailwind CSS CDN for styling -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Lucide Icons (commonly used) -->
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
    
    <style>
        /* Reset */
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: system-ui, -apple-system, sans-serif; }}
        
        /* Error display */
        .preview-error {{
            padding: 2rem;
            background: #1a1a2e;
            color: #ff6b6b;
            font-family: monospace;
            white-space: pre-wrap;
            overflow: auto;
            height: 100vh;
        }}
        .preview-error h2 {{
            color: #ff6b6b;
            margin-bottom: 1rem;
        }}
        .preview-error pre {{
            background: #16213e;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
        }}
        
        /* Project CSS */
        {chr(10).join(all_css)}
    </style>
</head>
<body>
    <div id="root"></div>
    <div id="error-display" style="display:none;"></div>
    
    <script>
        // Global error handler
        window.onerror = function(msg, url, lineNo, columnNo, error) {{
            var fullMessage = msg;
            if (error && error.stack) {{
                fullMessage += '\\n\\nStack:\\n' + error.stack;
            }}
            showError('JavaScript Error', fullMessage + '\\n\\nLine: ' + lineNo + ', Column: ' + columnNo);
            return true;
        }};
        
        function showError(title, message) {{
            document.getElementById('root').style.display = 'none';
            var errorDiv = document.getElementById('error-display');
            errorDiv.style.display = 'block';
            errorDiv.className = 'preview-error';
            errorDiv.innerHTML = '<h2>' + title + '</h2><pre>' + escapeHtml(message) + '</pre>' +
                '<p style="color:#888;margin-top:2rem;">Check browser console (F12) for more details.</p>';
        }}
        
        function escapeHtml(text) {{
            var div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        // Override Babel's error handling to show detailed errors
        window.addEventListener('load', function() {{
            if (window.Babel) {{
                var originalTransform = window.Babel.transform;
                window.Babel.transform = function(code, options) {{
                    try {{
                        return originalTransform.call(this, code, options);
                    }} catch (e) {{
                        showError('Babel Transform Error', e.message + '\\n\\nThis usually means there is invalid JSX/JavaScript in the component code.');
                        throw e;
                    }}
                }};
            }}
        }});
    </script>
    
    <script type="text/babel" data-presets="react">
        try {{
            // Provide common hooks and utilities
            const {{ useState, useEffect, useRef, useCallback, useMemo, useContext, createContext, Fragment }} = React;
            
            // Mock Next.js components
            const Link = ({{ href, children, className, ...props }}) => (
                <a href={{href}} className={{className}} {{...props}}>{{children}}</a>
            );
            const Image = ({{ src, alt, width, height, className, fill, priority, ...props }}) => (
                <img 
                    src={{src}} 
                    alt={{alt || ''}} 
                    width={{width}} 
                    height={{height}} 
                    className={{className}} 
                    style={{fill ? {{ objectFit: 'cover', width: '100%', height: '100%' }} : {{}}}}
                    {{...props}} 
                />
            );
            const Head = ({{ children }}) => null;
            const Script = ({{ children }}) => null;
            
            // Mock framer-motion
            const motion = new Proxy({{}}, {{
                get: (target, prop) => React.forwardRef(({{ children, className, initial, animate, transition, whileHover, whileTap, variants, ...props }}, ref) => 
                    React.createElement(prop, {{ ref, className, ...props }}, children)
                )
            }});
            const AnimatePresence = ({{ children }}) => children;
            
            // Helper for cn (classnames utility)
            const cn = (...classes) => classes.filter(Boolean).join(' ');
            const clsx = cn;
            
            // Mock common icons as simple spans
            const IconPlaceholder = ({{ className }}) => <span className={{className}}>●</span>;
            
            // Additional components
            {chr(10).join(escaped_additional)}
            
            // Main component
            {escaped_component}
            
            // Render with error boundary
            class ErrorBoundary extends React.Component {{
                constructor(props) {{
                    super(props);
                    this.state = {{ hasError: false, error: null }};
                }}
                static getDerivedStateFromError(error) {{
                    return {{ hasError: true, error }};
                }}
                componentDidCatch(error, errorInfo) {{
                    console.error('React Error:', error, errorInfo);
                }}
                render() {{
                    if (this.state.hasError) {{
                        return (
                            <div className="preview-error">
                                <h2>React Render Error</h2>
                                <pre>{{this.state.error?.toString()}}</pre>
                                <p style={{{{color:'#888',marginTop:'2rem'}}}}>Check browser console (F12) for more details.</p>
                            </div>
                        );
                    }}
                    return this.props.children;
                }}
            }}
            
            const root = ReactDOM.createRoot(document.getElementById('root'));
            root.render(
                <ErrorBoundary>
                    <{main_component_name} />
                </ErrorBoundary>
            );
        }} catch (e) {{
            console.error('Preview initialization error:', e);
            showError('Preview Error', e.toString() + '\\n\\n' + (e.stack || ''));
        }}
    </script>
</body>
</html>"""
    
    return HTMLResponse(preview_html)


@router.get("/projects/{project_id}/preview/file/{file_path:path}")
async def get_preview_file(
    project_id: int,
    file_path: str,
    user = Depends(get_current_user)
):
    """
    Serve an individual file from the project.
    
    Used by preview iframe for loading assets, scripts, etc.
    """
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    path = f"/{file_path}" if not file_path.startswith("/") else file_path
    
    async with pool.acquire() as conn:
        file = await conn.fetchrow(
            "SELECT content, language FROM enjineer_files WHERE project_id = $1 AND path = $2",
            project_id, path
        )
    
    if not file:
        # Try without leading slash
        async with pool.acquire() as conn:
            file = await conn.fetchrow(
                "SELECT content, language FROM enjineer_files WHERE project_id = $1 AND path = $2",
                project_id, file_path
            )
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    content = file["content"] or ""
    
    # Determine content type from extension
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".tsx": "application/typescript",
        ".ts": "application/typescript",
        ".jsx": "application/javascript",
        ".md": "text/markdown",
    }
    
    content_type = content_types.get(ext, "text/plain")
    
    return Response(
        content=content.encode('utf-8'),
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )


# ============================================================================
# Preview Deployment (Vercel) - Persistent Project System
# ============================================================================

# Configuration
ENJINEER_PREVIEW_DOMAIN = "enjineer.alphawavetech.com"

# Binary file extensions that can't be properly generated by AI
BINARY_EXTENSIONS = {'.ico', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', 
                     '.woff', '.woff2', '.ttf', '.eot', '.mp3', '.mp4', '.wav', 
                     '.pdf', '.zip', '.tar', '.gz'}


class PreviewDeployRequest(BaseModel):
    """Request to deploy project for preview."""
    framework: Optional[str] = None  # Auto-detect if not provided


class ProductionDeployRequest(BaseModel):
    """Request to deploy project to production."""
    domain: Optional[str] = None  # Custom domain for production


def sanitize_project_name(name: str) -> str:
    """Convert project name to valid Vercel project name."""
    import re
    # Lowercase, replace spaces with dashes, remove special chars
    sanitized = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-').replace('_', '-'))
    # Remove consecutive dashes and trim
    sanitized = re.sub(r'-+', '-', sanitized).strip('-')
    # Ensure it's not empty and not too long
    if not sanitized:
        sanitized = 'project'
    return sanitized[:50]


@router.post("/projects/{project_id}/preview/deploy")
async def deploy_preview(
    project_id: int,
    request: PreviewDeployRequest = None,
    user = Depends(get_current_user)
):
    """
    Deploy project files to Vercel for live preview.
    
    This uses a PERSISTENT Vercel project per Enjineer project:
    - First deploy: Creates Vercel project + assigns domain alias
    - Subsequent deploys: Updates the same project
    - Domain is always: project-{id}.enjineer.alphawavetech.com
    
    Old deployments are automatically cleaned up (keeps last 3).
    """
    from app.integrations.vercel_service import get_vercel_service
    
    user_id = get_user_id_from_context(user)
    pool = await get_tiger_pool()
    
    # Verify project access
    await verify_project_access(pool, project_id, user_id)
    
    # Get project details including Vercel project info
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            """SELECT id, name, vercel_project_id, vercel_project_name, preview_domain 
               FROM enjineer_projects WHERE id = $1""",
            project_id
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all project files
        files = await conn.fetch(
            "SELECT path, content FROM enjineer_files WHERE project_id = $1",
            project_id
        )
    
    if not files:
        raise HTTPException(status_code=400, detail="No files to deploy")
    
    # Build file map, skipping binary files
    file_map = {}
    for f in files:
        path = f["path"]
        ext = os.path.splitext(path)[1].lower()
        if ext in BINARY_EXTENSIONS:
            logger.info(f"[PREVIEW] Skipping binary file: {path}")
            continue
        file_map[path] = f["content"] or ""
    
    if not file_map:
        raise HTTPException(status_code=400, detail="No deployable files (all files were binary)")
    
    # Inject vercel.json to allow iframe embedding in Nicole dashboard
    # Uses Content-Security-Policy frame-ancestors (X-Frame-Options ALLOW-FROM is deprecated)
    vercel_config = {
        "headers": [
            {
                "source": "/(.*)",
                "headers": [
                    {
                        "key": "Content-Security-Policy",
                        "value": "frame-ancestors 'self' https://*.alphawavetech.com https://*.vercel.app http://localhost:* https://localhost:*"
                    },
                    {
                        "key": "X-Frame-Options",
                        "value": "SAMEORIGIN"
                    }
                ]
            }
        ]
    }
    # Merge with existing vercel.json if present
    if "vercel.json" in file_map:
        try:
            existing = json.loads(file_map["vercel.json"])
            existing["headers"] = vercel_config["headers"]
            file_map["vercel.json"] = json.dumps(existing, indent=2)
        except:
            file_map["vercel.json"] = json.dumps(vercel_config, indent=2)
    else:
        file_map["vercel.json"] = json.dumps(vercel_config, indent=2)
    
    # Detect project type if not specified
    framework = request.framework if request else None
    if not framework:
        project_type, _ = detect_project_type(file_map)
        framework = project_type if project_type in ['nextjs', 'react'] else 'static'
    
    # Get Vercel service
    vercel = get_vercel_service()
    if not vercel.is_configured:
        raise HTTPException(
            status_code=503, 
            detail="Vercel is not configured. Set VERCEL_TOKEN in environment."
        )
    
    # Determine Vercel project name
    vercel_project_name = project["vercel_project_name"]
    preview_domain = project["preview_domain"]
    
    if not vercel_project_name:
        # First time deploying - create persistent Vercel project
        sanitized_name = sanitize_project_name(project["name"])
        vercel_project_name = f"enjineer-{project_id}-{sanitized_name}"
        preview_domain = f"project-{project_id}.{ENJINEER_PREVIEW_DOMAIN}"
        
        logger.info(f"[PREVIEW] Creating new Vercel project: {vercel_project_name}")
        
        # Create the Vercel project
        vercel_project = await vercel.create_project_for_files(
            name=vercel_project_name,
            framework=framework
        )
        
        if vercel_project:
            # Add the custom domain to the project
            domain_added = await vercel.add_domain(vercel_project_name, preview_domain)
            if domain_added:
                logger.info(f"[PREVIEW] Added domain {preview_domain} to project")
            else:
                logger.warning(f"[PREVIEW] Failed to add domain {preview_domain}")
            
            # Store Vercel project info in database
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE enjineer_projects 
                       SET vercel_project_id = $1, vercel_project_name = $2, preview_domain = $3
                       WHERE id = $4""",
                    vercel_project.id, vercel_project_name, preview_domain, project_id
                )
        else:
            logger.warning(f"[PREVIEW] Failed to create Vercel project, using direct deployment")
    
    # Deploy to the project
    deployment = await vercel.deploy_to_project(
        project_name=vercel_project_name,
        files=file_map,
        target="preview",
        framework=framework
    )
    
    if not deployment:
        # Fallback to direct deployment if project deployment fails
        logger.warning("[PREVIEW] Project deployment failed, trying direct deployment")
        deployment = await vercel.deploy_files(
            name=vercel_project_name,
            files=file_map,
            framework=framework
        )
    
    if not deployment:
        raise HTTPException(status_code=500, detail="Failed to create deployment")
    
    # Store deployment info
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO enjineer_deployments 
            (project_id, platform_deployment_id, url, platform, environment, status, domain_alias, is_preview)
            VALUES ($1, $2, $3, 'vercel', 'preview', 'building', $4, TRUE)
        """, project_id, deployment.id, deployment.url, preview_domain)
        
        # Update project with latest preview info
        await conn.execute(
            """UPDATE enjineer_projects 
               SET last_preview_deployment_id = $1, last_preview_url = $2, last_preview_at = NOW()
               WHERE id = $3""",
            deployment.id, deployment.url, project_id
        )
    
    # Assign the custom domain alias to this specific deployment
    # This is CRITICAL - without this, the custom domain won't point to the new deployment
    if preview_domain:
        try:
            alias_set = await vercel.set_deployment_alias(deployment.id, preview_domain)
            if alias_set:
                logger.info(f"[PREVIEW] Assigned alias {preview_domain} to deployment {deployment.id}")
            else:
                logger.warning(f"[PREVIEW] Failed to assign alias {preview_domain} to deployment")
        except Exception as e:
            logger.warning(f"[PREVIEW] Alias assignment failed (non-critical): {e}")
    
    # Cleanup old deployments in background (keep last 3)
    try:
        await vercel.cleanup_old_deployments(vercel_project_name, keep_count=3)
    except Exception as e:
        logger.warning(f"[PREVIEW] Cleanup failed (non-critical): {e}")
    
    logger.info(f"[PREVIEW] Deployed project {project_id} to {deployment.url}")
    logger.info(f"[PREVIEW] Custom domain: https://{preview_domain}")
    
    return {
        "deployment_id": deployment.id,
        "url": deployment.url,
        "preview_domain": f"https://{preview_domain}" if preview_domain else None,
        "status": deployment.state,
        "message": "Preview deployment started. It may take 30-60 seconds to build."
    }


@router.post("/projects/{project_id}/production/deploy")
async def deploy_production(
    project_id: int,
    request: ProductionDeployRequest = None,
    user = Depends(get_current_user)
):
    """
    Deploy project to production with optional custom domain.
    
    This promotes the current project state to a production deployment.
    If a custom domain is provided, it will be configured.
    """
    from app.integrations.vercel_service import get_vercel_service
    
    user_id = get_user_id_from_context(user)
    pool = await get_tiger_pool()
    
    await verify_project_access(pool, project_id, user_id)
    
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            """SELECT id, name, vercel_project_name, production_domain
               FROM enjineer_projects WHERE id = $1""",
            project_id
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        files = await conn.fetch(
            "SELECT path, content FROM enjineer_files WHERE project_id = $1",
            project_id
        )
    
    if not files:
        raise HTTPException(status_code=400, detail="No files to deploy")
    
    # Build file map
    file_map = {}
    for f in files:
        path = f["path"]
        ext = os.path.splitext(path)[1].lower()
        if ext in BINARY_EXTENSIONS:
            continue
        file_map[path] = f["content"] or ""
    
    if not file_map:
        raise HTTPException(status_code=400, detail="No deployable files")
    
    # Detect framework
    project_type, _ = detect_project_type(file_map)
    framework = project_type if project_type in ['nextjs', 'react'] else 'static'
    
    vercel = get_vercel_service()
    if not vercel.is_configured:
        raise HTTPException(status_code=503, detail="Vercel is not configured")
    
    vercel_project_name = project["vercel_project_name"]
    if not vercel_project_name:
        raise HTTPException(
            status_code=400, 
            detail="Deploy a preview first to create the Vercel project"
        )
    
    # Deploy to production
    deployment = await vercel.deploy_to_project(
        project_name=vercel_project_name,
        files=file_map,
        target="production",
        framework=framework
    )
    
    if not deployment:
        raise HTTPException(status_code=500, detail="Failed to create production deployment")
    
    # Handle custom domain if provided
    custom_domain = request.domain if request else None
    if custom_domain:
        domain_added = await vercel.add_domain(vercel_project_name, custom_domain)
        if domain_added:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE enjineer_projects SET production_domain = $1 WHERE id = $2",
                    custom_domain, project_id
                )
    
    # Store deployment info
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO enjineer_deployments 
            (project_id, platform_deployment_id, url, platform, environment, status, is_preview)
            VALUES ($1, $2, $3, 'vercel', 'production', 'building', FALSE)
        """, project_id, deployment.id, deployment.url)
        
        await conn.execute(
            """UPDATE enjineer_projects 
               SET last_production_deployment_id = $1, last_production_url = $2, last_production_at = NOW()
               WHERE id = $3""",
            deployment.id, deployment.url, project_id
        )
    
    logger.info(f"[PRODUCTION] Deployed project {project_id} to production: {deployment.url}")
    
    return {
        "deployment_id": deployment.id,
        "url": deployment.url,
        "custom_domain": f"https://{custom_domain}" if custom_domain else None,
        "status": deployment.state,
        "message": "Production deployment started."
    }


@router.get("/projects/{project_id}/preview")
async def get_preview_info(
    project_id: int,
    user = Depends(get_current_user)
):
    """
    Get the current preview status for a project.
    
    Returns the persistent preview domain and latest deployment info.
    """
    user_id = get_user_id_from_context(user)
    pool = await get_tiger_pool()
    
    await verify_project_access(pool, project_id, user_id)
    
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            """SELECT preview_domain, last_preview_deployment_id, last_preview_url, last_preview_at,
                      production_domain, last_production_url, last_production_at
               FROM enjineer_projects WHERE id = $1""",
            project_id
        )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "preview": {
            "domain": f"https://{project['preview_domain']}" if project["preview_domain"] else None,
            "last_deployment_id": project["last_preview_deployment_id"],
            "last_url": project["last_preview_url"],
            "last_deployed_at": project["last_preview_at"].isoformat() if project["last_preview_at"] else None
        },
        "production": {
            "domain": f"https://{project['production_domain']}" if project["production_domain"] else None,
            "last_url": project["last_production_url"],
            "last_deployed_at": project["last_production_at"].isoformat() if project["last_production_at"] else None
        }
    }


@router.delete("/projects/{project_id}/preview/cleanup")
async def cleanup_preview_deployments(
    project_id: int,
    keep_count: int = 1,
    user = Depends(get_current_user)
):
    """
    Clean up old preview deployments, keeping only the most recent ones.
    """
    from app.integrations.vercel_service import get_vercel_service
    
    user_id = get_user_id_from_context(user)
    pool = await get_tiger_pool()
    
    await verify_project_access(pool, project_id, user_id)
    
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            "SELECT vercel_project_name FROM enjineer_projects WHERE id = $1",
            project_id
        )
    
    if not project or not project["vercel_project_name"]:
        raise HTTPException(status_code=404, detail="No Vercel project found")
    
    vercel = get_vercel_service()
    if not vercel.is_configured:
        raise HTTPException(status_code=503, detail="Vercel is not configured")
    
    deleted = await vercel.cleanup_old_deployments(
        project["vercel_project_name"], 
        keep_count=max(1, keep_count)
    )
    
    return {"message": f"Cleaned up {deleted} old deployments"}


@router.get("/projects/{project_id}/preview/status/{deployment_id}")
async def get_preview_status(
    project_id: int,
    deployment_id: str,
    user = Depends(get_current_user)
):
    """
    Check the status of a preview deployment.
    
    Returns the current state: BUILDING, READY, ERROR, CANCELED
    """
    from app.integrations.vercel_service import get_vercel_service
    
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    
    vercel = get_vercel_service()
    if not vercel.is_configured:
        raise HTTPException(status_code=503, detail="Vercel is not configured")
    
    deployment = await vercel.get_deployment(deployment_id)
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Map Vercel status to schema-allowed values
    status_map = {
        'BUILDING': 'building',
        'READY': 'success',
        'ERROR': 'failed',
        'CANCELED': 'cancelled',
        'QUEUED': 'pending',
    }
    db_status = status_map.get(deployment.state, 'building')
    
    # Update stored status
    pool = await get_tiger_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE enjineer_deployments 
            SET status = $1, url = $2
            WHERE platform_deployment_id = $3
        """, db_status, deployment.url, deployment_id)
    
    return {
        "deployment_id": deployment.id,
        "url": deployment.url,
        "status": deployment.state,
        "ready": deployment.state == "READY"
    }


@router.delete("/projects/{project_id}/preview/{deployment_id}")
async def delete_preview(
    project_id: int,
    deployment_id: str,
    user = Depends(get_current_user)
):
    """
    Delete a preview deployment to clean up resources.
    """
    from app.integrations.vercel_service import get_vercel_service
    
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    
    vercel = get_vercel_service()
    if not vercel.is_configured:
        raise HTTPException(status_code=503, detail="Vercel is not configured")
    
    success = await vercel.delete_deployment(deployment_id)
    
    if success:
        # Remove from database
        pool = await get_tiger_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM enjineer_deployments WHERE platform_deployment_id = $1",
                deployment_id
            )
        return {"message": "Deployment deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete deployment")


# ============================================================================
# Knowledge Base Endpoints
# ============================================================================

from app.services.knowledge_base_service import kb_service


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = Field(None, pattern="^(patterns|animation|components|fundamentals|core)$")
    include_sections: bool = False
    limit: int = Field(10, ge=1, le=50)


class KnowledgeSearchResponse(BaseModel):
    files: List[dict]
    sections: List[dict]
    total_files: int
    total_sections: int
    query: str


@router.get("/knowledge/search")
async def search_knowledge_base(
    query: str = Query(..., min_length=1, max_length=500),
    category: Optional[str] = Query(None, pattern="^(patterns|animation|components|fundamentals|core)$"),
    include_sections: bool = Query(False),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """
    Search the design knowledge base.
    
    Returns files and optionally sections matching the query.
    Used by Nicole to retrieve design patterns and best practices.
    """
    try:
        # Search files
        file_results = await kb_service.search_fulltext(
            query=query,
            category=category,
            limit=limit
        )
        
        section_results = []
        if include_sections:
            section_results = await kb_service.search_sections(
                query=query,
                limit=limit * 2
            )
        
        # Log access for analytics
        if file_results:
            await kb_service.log_access(
                file_id=file_results[0]["id"],
                user_id=user.get("user_id", 1),
                query_text=query,
                access_method="api_search"
            )
        
        return {
            "success": True,
            "files": file_results,
            "sections": section_results,
            "total_files": len(file_results),
            "total_sections": len(section_results),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"[KB] Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/knowledge/files")
async def list_knowledge_files(
    category: Optional[str] = Query(None),
    user: dict = Depends(get_current_user)
):
    """
    List all knowledge base files.
    
    Optionally filter by category.
    """
    try:
        if category:
            files = await kb_service.get_by_category(category, limit=100)
        else:
            files = await kb_service.get_popular_files(limit=100)
        
        return {
            "success": True,
            "files": files,
            "total": len(files)
        }
        
    except Exception as e:
        logger.error(f"[KB] List failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/files/{slug}")
async def get_knowledge_file(
    slug: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a specific knowledge file by slug.
    
    Returns full content for detailed reference.
    """
    try:
        file_data = await kb_service.get_file_by_slug(slug)
        
        if not file_data:
            raise HTTPException(status_code=404, detail=f"Knowledge file '{slug}' not found")
        
        # Log access
        await kb_service.log_access(
            file_id=file_data["id"],
            user_id=user.get("user_id", 1),
            access_method="direct"
        )
        
        return {
            "success": True,
            "file": file_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KB] Get file failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/context")
async def get_knowledge_context(
    query: str = Query(..., min_length=1),
    max_sections: int = Query(5, ge=1, le=20),
    max_tokens: int = Query(4000, ge=500, le=10000),
    user: dict = Depends(get_current_user)
):
    """
    Get formatted knowledge context for Nicole's system prompt.
    
    Returns a markdown-formatted string with relevant sections,
    optimized for token budget.
    """
    try:
        context = await kb_service.get_relevant_context(
            query=query,
            max_sections=max_sections,
            max_tokens=max_tokens
        )
        
        return {
            "success": True,
            "context": context,
            "query": query
        }
        
    except Exception as e:
        logger.error(f"[KB] Get context failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/stats")
async def get_knowledge_stats(
    user: dict = Depends(get_current_user)
):
    """
    Get knowledge base usage statistics.
    """
    try:
        stats = await kb_service.get_usage_stats()
        popular = await kb_service.get_popular_files(limit=5)
        
        return {
            "success": True,
            "stats": stats,
            "popular_files": popular
        }
        
    except Exception as e:
        logger.error(f"[KB] Stats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket Endpoint
# ============================================================================

# Store active connections per project
active_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/projects/{project_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str
):
    """WebSocket for real-time project updates."""
    await websocket.accept()
    
    # Add to active connections
    if project_id not in active_connections:
        active_connections[project_id] = []
    active_connections[project_id].append(websocket)
    
    logger.info(f"WebSocket connected for project {project_id}")
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Echo back or handle commands
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        active_connections[project_id].remove(websocket)
        logger.info(f"WebSocket disconnected for project {project_id}")


async def broadcast_to_project(project_id: str, message: dict):
    """Broadcast message to all connected clients for a project."""
    if project_id in active_connections:
        import json
        for connection in active_connections[project_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass


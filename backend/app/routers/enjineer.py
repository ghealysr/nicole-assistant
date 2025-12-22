"""
Enjineer Router
AI-powered development environment endpoints
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
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
    # Use tiger_user_id (integer) from the Tiger Postgres users table
    if hasattr(user, 'tiger_user_id') and user.tiger_user_id:
        return user.tiger_user_id
    raise HTTPException(status_code=401, detail="Not authenticated - no tiger_user_id")


async def verify_project_access(pool, project_id: str, user_id: str) -> dict:
    """Verify user has access to project and return project data."""
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            "SELECT * FROM enjineer_projects WHERE id = $1 AND user_id = $2",
            int(project_id), user_id
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
    """Create a new Enjineer project."""
    user_id = get_user_id_from_context(user)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            """
            INSERT INTO enjineer_projects (user_id, name, description, tech_stack, intake_data, settings)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            user_id,
            request.name,
            request.description,
            request.tech_stack or {},
            request.intake_data or {},
            {"budget_limit": 50.0, "total_spent": 0.0, "theme": "dark"}
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
        updated_at=project["updated_at"].isoformat()
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
                LIMIT $3 OFFSET $4
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
            updated_at=p["updated_at"].isoformat()
        )
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
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
            int(project_id)
        )
        
        # Get current plan
        plan = await conn.fetchrow(
            """
            SELECT * FROM enjineer_plans 
            WHERE project_id = $1 AND status NOT IN ('abandoned', 'completed')
            ORDER BY created_at DESC LIMIT 1
            """,
            int(project_id)
        )
        
        # Get pending approvals
        approvals = await conn.fetch(
            "SELECT * FROM enjineer_approvals WHERE project_id = $1 AND status = 'pending'",
            int(project_id)
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
            updated_at=project["updated_at"].isoformat()
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
    project_id: str,
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
    
    values.append(int(project_id))
    
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
        updated_at=project["updated_at"].isoformat()
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user = Depends(get_current_user)
):
    """Soft delete a project (set status to abandoned)."""
    user_id = get_user_id_from_context(user)
    await verify_project_access(await get_tiger_pool(), project_id, user_id)
    pool = await get_tiger_pool()
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE enjineer_projects SET status = 'abandoned' WHERE id = $1",
            int(project_id)
        )
    
    return {"success": True}


# ============================================================================
# File Endpoints
# ============================================================================

@router.get("/projects/{project_id}/files")
async def list_files(
    project_id: str,
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
                int(project_id), f"{path_prefix}%"
            )
        else:
            files = await conn.fetch(
                "SELECT * FROM enjineer_files WHERE project_id = $1 ORDER BY path",
                int(project_id)
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
    project_id: str,
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
            int(project_id), request.path
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
            int(project_id), request.path, request.content, language, "user", checksum
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
    project_id: str,
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
            int(project_id), f"/{file_path}" if not file_path.startswith("/") else file_path
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
    project_id: str,
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
            int(project_id), path
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
    project_id: str,
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
            int(project_id), path
        )
    
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"success": True}


# ============================================================================
# Chat Endpoints
# ============================================================================

@router.post("/projects/{project_id}/chat")
async def send_message(
    project_id: str,
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
            int(project_id), request.message, request.attachments or [], {}
        )
    
    async def generate_response():
        """Generate SSE response stream."""
        try:
            # Import here to avoid circular dependency
            from app.services.enjineer_nicole import EnjineerNicole
            
            nicole = EnjineerNicole(int(project_id), user_id)
            
            full_response = ""
            
            async for event in nicole.process_message(request.message, request.attachments):
                if event["type"] == "text":
                    full_response += event["content"]
                    yield f"data: {{'type': 'text', 'content': {repr(event['content'])}}}\n\n"
                elif event["type"] == "thinking":
                    yield f"data: {{'type': 'thinking', 'content': {repr(event['content'])}}}\n\n"
                elif event["type"] == "tool_use":
                    yield f"data: {{'type': 'tool_use', 'tool': '{event['tool']}', 'input': {event['input']}}}\n\n"
                elif event["type"] == "code":
                    yield f"data: {{'type': 'code', 'path': '{event['path']}', 'content': {repr(event['content'])}}}\n\n"
                elif event["type"] == "approval_required":
                    yield f"data: {{'type': 'approval_required', 'approval_id': '{event['approval_id']}'}}\n\n"
            
            # Save assistant message
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO enjineer_messages (project_id, role, content, metadata)
                    VALUES ($1, 'assistant', $2, $3)
                    """,
                    int(project_id), full_response, {}
                )
            
            yield "data: {'type': 'done'}\n\n"
            
        except Exception as e:
            logger.error(f"Error in Nicole response: {e}")
            yield f"data: {{'type': 'error', 'message': {repr(str(e))}}}\n\n"
    
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
    project_id: str,
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
                int(project_id), datetime.fromisoformat(before), limit
            )
        else:
            messages = await conn.fetch(
                """
                SELECT * FROM enjineer_messages 
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                int(project_id), limit
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
    project_id: str,
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
            int(project_id)
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
    project_id: str,
    approval_id: str,
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
            request.note, int(approval_id), int(project_id)
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
    project_id: str,
    approval_id: str,
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
            request.reason, int(approval_id), int(project_id)
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


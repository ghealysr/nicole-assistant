"""
Faz Code Projects Router

API endpoints for project management:
- Create/list/get projects
- Run pipeline
- Get files
- Get activities
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging
import json
from datetime import datetime

from app.database import db
from app.middleware.alphawave_auth import get_current_user
from app.services.faz_orchestrator import FazOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faz", tags=["Faz Code"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ProjectCreate(BaseModel):
    """Create project request."""
    name: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=10, max_length=10000)
    design_preferences: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    """Project response."""
    project_id: int
    name: str
    slug: str
    status: str
    original_prompt: str
    current_agent: Optional[str] = None
    file_count: int = 0
    total_tokens_used: int = 0
    total_cost_cents: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Project list response."""
    projects: List[ProjectResponse]
    total: int


class RunPipelineRequest(BaseModel):
    """Run pipeline request."""
    prompt: Optional[str] = None  # Use project's original prompt if not provided
    start_agent: str = "nicole"


class FileResponse(BaseModel):
    """File response."""
    file_id: int
    path: str
    filename: str
    extension: Optional[str]
    content: str
    file_type: Optional[str]
    line_count: int
    generated_by: Optional[str]
    version: int
    status: str
    created_at: datetime


class ActivityResponse(BaseModel):
    """Activity response."""
    activity_id: int
    agent_name: str
    agent_model: str
    activity_type: str
    message: str
    content_type: str
    full_content: Optional[str]
    input_tokens: int
    output_tokens: int
    cost_cents: float
    status: str
    started_at: datetime
    completed_at: Optional[datetime]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_slug(name: str, project_id: int) -> str:
    """Generate URL-safe slug."""
    slug = name.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return f"{slug}-{project_id}"


# =============================================================================
# PROJECT CRUD
# =============================================================================

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    user = Depends(get_current_user),
):
    """Create a new Faz Code project."""
    try:
        # Create project
        project_id = await db.fetchval(
            """
            INSERT INTO faz_projects
                (user_id, name, slug, original_prompt, design_preferences, status)
            VALUES ($1, $2, '', $3, $4, 'intake')
            RETURNING project_id
            """,
            user.user_id,
            request.name,
            request.prompt,
            json.dumps(request.design_preferences or {}),
        )
        
        # Generate slug with ID
        slug = generate_slug(request.name, project_id)
        await db.execute(
            "UPDATE faz_projects SET slug = $1 WHERE project_id = $2",
            slug,
            project_id,
        )
        
        logger.info(f"[Faz] Created project {project_id}: {request.name}")
        
        # Get full project
        project = await db.fetchrow(
            """
            SELECT p.*, 
                   (SELECT COUNT(*) FROM faz_files WHERE project_id = p.project_id) as file_count
            FROM faz_projects p
            WHERE project_id = $1
            """,
            project_id,
        )
        
        return ProjectResponse(
            project_id=project["project_id"],
            name=project["name"],
            slug=project["slug"],
            status=project["status"],
            original_prompt=project["original_prompt"],
            current_agent=project["current_agent"],
            file_count=project["file_count"],
            total_tokens_used=project["total_tokens_used"] or 0,
            total_cost_cents=project["total_cost_cents"] or 0,
            created_at=project["created_at"],
            updated_at=project["updated_at"],
        )
        
    except Exception as e:
        logger.exception(f"[Faz] Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    user = Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List user's projects."""
    try:
        where_parts = ["user_id = $1"]
        params = [user.user_id]
        
        if status:
            where_parts.append("status = $2")
            params.append(status)
        
        # Get count
        total = await db.fetchval(
            f"SELECT COUNT(*) FROM faz_projects WHERE {' AND '.join(where_parts)}",
            *params,
        )
        
        # Get projects
        params.extend([limit, offset])
        projects = await db.fetch(
            f"""
            SELECT p.*,
                   (SELECT COUNT(*) FROM faz_files WHERE project_id = p.project_id) as file_count
            FROM faz_projects p
            WHERE {' AND '.join(where_parts)}
            ORDER BY updated_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
        
        return ProjectListResponse(
            projects=[
                ProjectResponse(
                    project_id=p["project_id"],
                    name=p["name"],
                    slug=p["slug"],
                    status=p["status"],
                    original_prompt=p["original_prompt"],
                    current_agent=p["current_agent"],
                    file_count=p["file_count"],
                    total_tokens_used=p["total_tokens_used"] or 0,
                    total_cost_cents=p["total_cost_cents"] or 0,
                    created_at=p["created_at"],
                    updated_at=p["updated_at"],
                )
                for p in projects
            ],
            total=total,
        )
        
    except Exception as e:
        logger.exception(f"[Faz] Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    user = Depends(get_current_user),
):
    """Get a specific project."""
    try:
        project = await db.fetchrow(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM faz_files WHERE project_id = p.project_id) as file_count
            FROM faz_projects p
            WHERE project_id = $1 AND user_id = $2
            """,
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(
            project_id=project["project_id"],
            name=project["name"],
            slug=project["slug"],
            status=project["status"],
            original_prompt=project["original_prompt"],
            current_agent=project["current_agent"],
            file_count=project["file_count"],
            total_tokens_used=project["total_tokens_used"] or 0,
            total_cost_cents=project["total_cost_cents"] or 0,
            created_at=project["created_at"],
            updated_at=project["updated_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    user = Depends(get_current_user),
):
    """Delete a project."""
    try:
        result = await db.execute(
            "DELETE FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if "DELETE 0" in result:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"success": True, "message": "Project deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to delete project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PIPELINE CONTROL
# =============================================================================

@router.post("/projects/{project_id}/run")
async def run_pipeline(
    project_id: int,
    request: RunPipelineRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user),
):
    """
    Start the agent pipeline for a project.
    
    This runs in the background and updates the project status.
    Use the WebSocket or polling to get real-time updates.
    """
    try:
        # Verify project exists and belongs to user
        project = await db.fetchrow(
            "SELECT * FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if already running
        if project["status"] in ["planning", "researching", "designing", "building", "qa", "review", "deploying"]:
            raise HTTPException(status_code=400, detail="Pipeline already running")
        
        # Update status to 'planning' (first pipeline stage)
        await db.execute(
            "UPDATE faz_projects SET status = 'planning', updated_at = NOW() WHERE project_id = $1",
            project_id,
        )
        
        # Get prompt
        prompt = request.prompt or project["original_prompt"]
        
        # Run pipeline in background
        async def run_in_background():
            try:
                orchestrator = FazOrchestrator(project_id, user.user_id)
                await orchestrator.run(prompt, request.start_agent)
            except Exception as e:
                logger.exception(f"[Faz] Pipeline failed for project {project_id}: {e}")
                await db.execute(
                    "UPDATE faz_projects SET status = 'failed', updated_at = NOW() WHERE project_id = $1",
                    project_id,
                )
        
        background_tasks.add_task(run_in_background)
        
        return {
            "success": True,
            "message": "Pipeline started",
            "project_id": project_id,
            "start_agent": request.start_agent,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to start pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/stop")
async def stop_pipeline(
    project_id: int,
    user = Depends(get_current_user),
):
    """Stop a running pipeline."""
    try:
        # Verify ownership
        project = await db.fetchrow(
            "SELECT project_id, status FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Cancel the running orchestrator if one exists
        from app.services.faz_orchestrator import cancel_orchestrator
        was_running = await cancel_orchestrator(project_id)
        
        # Update database status
        await db.execute(
            """
            UPDATE faz_projects 
            SET status = 'paused', 
                current_agent = NULL,
                updated_at = NOW()
            WHERE project_id = $1 AND user_id = $2
            """,
            project_id,
            user.user_id,
        )
        
        logger.info(f"[Faz] Pipeline stopped for project {project_id}, was_running={was_running}")
        
        return {
            "success": True, 
            "message": "Pipeline stopped",
            "was_running": was_running
        }
        
    except Exception as e:
        logger.exception(f"[Faz] Failed to stop pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FILES
# =============================================================================

@router.get("/projects/{project_id}/files", response_model=List[FileResponse])
async def get_project_files(
    project_id: int,
    user = Depends(get_current_user),
):
    """Get all files for a project."""
    try:
        # Verify access
        project = await db.fetchrow(
            "SELECT project_id FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        files = await db.fetch(
            """
            SELECT file_id, path, filename, extension, content, file_type,
                   line_count, generated_by, version, status, created_at
            FROM faz_files
            WHERE project_id = $1
            ORDER BY path
            """,
            project_id,
        )
        
        return [
            FileResponse(
                file_id=f["file_id"],
                path=f["path"],
                filename=f["filename"],
                extension=f["extension"],
                content=f["content"],
                file_type=f["file_type"],
                line_count=f["line_count"] or 0,
                generated_by=f["generated_by"],
                version=f["version"] or 1,
                status=f["status"] or "generated",
                created_at=f["created_at"],
            )
            for f in files
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to get files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/files/{file_id}")
async def get_file(
    project_id: int,
    file_id: int,
    user = Depends(get_current_user),
):
    """Get a specific file."""
    try:
        file = await db.fetchrow(
            """
            SELECT f.* 
            FROM faz_files f
            JOIN faz_projects p ON f.project_id = p.project_id
            WHERE f.file_id = $1 AND f.project_id = $2 AND p.user_id = $3
            """,
            file_id,
            project_id,
            user.user_id,
        )
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            file_id=file["file_id"],
            path=file["path"],
            filename=file["filename"],
            extension=file["extension"],
            content=file["content"],
            file_type=file["file_type"],
            line_count=file["line_count"] or 0,
            generated_by=file["generated_by"],
            version=file["version"] or 1,
            status=file["status"] or "generated",
            created_at=file["created_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to get file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ACTIVITIES
# =============================================================================

@router.get("/projects/{project_id}/activities", response_model=List[ActivityResponse])
async def get_project_activities(
    project_id: int,
    user = Depends(get_current_user),
    limit: int = 50,
    after_id: Optional[int] = None,
):
    """Get activities for a project (for real-time updates)."""
    try:
        # Verify access
        project = await db.fetchrow(
            "SELECT project_id FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        where_parts = ["project_id = $1"]
        params = [project_id]
        
        if after_id:
            where_parts.append("activity_id > $2")
            params.append(after_id)
        
        params.append(limit)
        
        activities = await db.fetch(
            f"""
            SELECT activity_id, agent_name, agent_model, activity_type, message,
                   content_type, full_content, input_tokens, output_tokens, 
                   cost_cents, status, started_at, completed_at
            FROM faz_agent_activities
            WHERE {' AND '.join(where_parts)}
            ORDER BY started_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
        
        return [
            ActivityResponse(
                activity_id=a["activity_id"],
                agent_name=a["agent_name"],
                agent_model=a["agent_model"],
                activity_type=a["activity_type"],
                message=a["message"],
                content_type=a["content_type"] or "status",
                full_content=a["full_content"],
                input_tokens=a["input_tokens"] or 0,
                output_tokens=a["output_tokens"] or 0,
                cost_cents=float(a["cost_cents"] or 0),
                status=a["status"] or "complete",
                started_at=a["started_at"],
                completed_at=a["completed_at"],
            )
            for a in activities
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to get activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ARCHITECTURE & DESIGN
# =============================================================================

@router.get("/projects/{project_id}/architecture")
async def get_project_architecture(
    project_id: int,
    user = Depends(get_current_user),
):
    """Get project architecture."""
    try:
        project = await db.fetchrow(
            """
            SELECT architecture, design_tokens, tech_stack
            FROM faz_projects
            WHERE project_id = $1 AND user_id = $2
            """,
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "architecture": project["architecture"] or {},
            "design_tokens": project["design_tokens"] or {},
            "tech_stack": project["tech_stack"] or {},
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to get architecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/architecture")
async def update_project_architecture(
    project_id: int,
    architecture: Dict[str, Any],
    user = Depends(get_current_user),
):
    """Update project architecture (manual edit)."""
    try:
        await db.execute(
            """
            UPDATE faz_projects
            SET architecture = $1, updated_at = NOW()
            WHERE project_id = $2 AND user_id = $3
            """,
            json.dumps(architecture),
            project_id,
            user.user_id,
        )
        
        return {"success": True, "message": "Architecture updated"}
        
    except Exception as e:
        logger.exception(f"[Faz] Failed to update architecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DEPLOYMENT
# =============================================================================

class DeployRequest(BaseModel):
    """Deploy request options."""
    skip_github: bool = False  # If True, only deploy to Vercel (requires existing repo)
    private_repo: bool = False  # Create private GitHub repo


@router.post("/projects/{project_id}/deploy")
async def deploy_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    request: Optional[DeployRequest] = None,
    user = Depends(get_current_user),
):
    """
    Deploy project to GitHub and Vercel.
    
    Steps:
    1. Create GitHub repository
    2. Commit all project files
    3. Create Vercel project linked to GitHub
    4. Trigger Vercel deployment
    """
    try:
        project = await db.fetchrow(
            "SELECT * FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Allow deployment from approved, review, or delivered states
        if project["status"] not in ["approved", "review", "delivered", "deployed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Project must be approved before deployment (current: {project['status']})"
            )
        
        # Check if we have files
        file_count = await db.fetchval(
            "SELECT COUNT(*) FROM faz_files WHERE project_id = $1",
            project_id,
        )
        
        if not file_count:
            raise HTTPException(status_code=400, detail="No files to deploy")
        
        # Update status
        await db.execute(
            "UPDATE faz_projects SET status = 'deploying', updated_at = NOW() WHERE project_id = $1",
            project_id,
        )
        
        # Deploy in background
        req = request or DeployRequest()
        
        async def deploy_in_background():
            try:
                from app.services.faz_github_service import deploy_project_to_github
                from app.services.faz_vercel_service import deploy_project_to_vercel
                
                # Step 1: Deploy to GitHub
                if not req.skip_github or not project.get("github_repo"):
                    github_result = await deploy_project_to_github(
                        project_id,
                        user.user_id,
                    )
                    
                    if github_result.get("error"):
                        logger.error(f"[Faz] GitHub deploy failed: {github_result['error']}")
                        await db.execute(
                            """UPDATE faz_projects 
                               SET status = 'failed', 
                                   status_history = status_history || $1::jsonb,
                                   updated_at = NOW() 
                               WHERE project_id = $2""",
                            json.dumps([{"status": "failed", "error": github_result["error"], 
                                       "stage": "github", "timestamp": datetime.utcnow().isoformat()}]),
                            project_id,
                        )
                        return
                    
                    github_repo = github_result.get("repo_name")
                    github_url = github_result.get("github_url")
                    logger.info(f"[Faz] GitHub deploy success: {github_url}")
                else:
                    github_repo = project.get("github_repo")
                    if "github.com" in github_repo:
                        github_repo = github_repo.replace("https://github.com/", "")
                
                # Step 2: Deploy to Vercel
                vercel_result = await deploy_project_to_vercel(
                    project_id,
                    user.user_id,
                    github_repo,
                )
                
                if vercel_result.get("error"):
                    logger.error(f"[Faz] Vercel deploy failed: {vercel_result['error']}")
                    await db.execute(
                        """UPDATE faz_projects 
                           SET status = 'failed', 
                               status_history = status_history || $1::jsonb,
                               updated_at = NOW() 
                           WHERE project_id = $2""",
                        json.dumps([{"status": "failed", "error": vercel_result["error"],
                                   "stage": "vercel", "timestamp": datetime.utcnow().isoformat()}]),
                        project_id,
                    )
                    return
                
                # Step 3: Update project with deployment info
                await db.execute(
                    """UPDATE faz_projects
                       SET status = 'deployed',
                           production_url = $1,
                           vercel_project_id = $2,
                           status_history = status_history || $3::jsonb,
                           updated_at = NOW()
                       WHERE project_id = $4""",
                    vercel_result.get("production_url"),
                    vercel_result.get("vercel_project_id"),
                    json.dumps([{
                        "status": "deployed",
                        "production_url": vercel_result.get("production_url"),
                        "github_repo": github_repo,
                        "timestamp": datetime.utcnow().isoformat(),
                    }]),
                    project_id,
                )
                
                logger.info(f"[Faz] Project {project_id} deployed to {vercel_result.get('production_url')}")
                
            except Exception as e:
                logger.exception(f"[Faz] Deployment failed for project {project_id}: {e}")
                await db.execute(
                    """UPDATE faz_projects 
                       SET status = 'failed', 
                           status_history = status_history || $1::jsonb,
                           updated_at = NOW() 
                       WHERE project_id = $2""",
                    json.dumps([{"status": "failed", "error": str(e),
                               "timestamp": datetime.utcnow().isoformat()}]),
                    project_id,
                )
        
        background_tasks.add_task(deploy_in_background)
        
        return {
            "success": True,
            "message": "Deployment started",
            "project_id": project_id,
            "status": "deploying",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to start deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/deploy/status")
async def get_deploy_status(
    project_id: int,
    user = Depends(get_current_user),
):
    """Get deployment status for a project."""
    try:
        project = await db.fetchrow(
            """SELECT project_id, status, github_repo, vercel_project_id, 
                      preview_url, production_url, status_history
               FROM faz_projects 
               WHERE project_id = $1 AND user_id = $2""",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # If deploying, check Vercel status
        live_status = None
        if project["status"] == "deploying" and project["vercel_project_id"]:
            from app.services.faz_vercel_service import check_deployment_status
            live_status = await check_deployment_status(project_id)
        
        return {
            "project_id": project_id,
            "status": project["status"],
            "github_repo": project["github_repo"],
            "vercel_project_id": project["vercel_project_id"],
            "preview_url": project["preview_url"],
            "production_url": project["production_url"],
            "deployment_status": live_status,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to get deploy status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


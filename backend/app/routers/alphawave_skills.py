"""
Nicole V7 - Skills API Router

PURPOSE:
    Provides REST endpoints for managing Nicole's skill system including:
    - Listing installed skills with status
    - Running health checks
    - Importing new skills
    - Viewing skill execution history
    - Manually updating skill status

INTEGRATION:
    These endpoints are designed to integrate with the Memory Dashboard UI,
    providing a "Skills" tab that shows skill status and management.

AUTHORIZATION:
    All endpoints require JWT authentication.
    Admin-only endpoints require elevated permissions.

Author: Nicole V7 Skills System
Date: December 5, 2025
"""

from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from datetime import datetime
from pathlib import Path

from app.middleware.alphawave_auth import (
    get_current_user_id,
    get_current_tiger_user_id,
)
from app.skills.registry import load_registry
from app.services.skill_health_service import skill_health_service

logger = logging.getLogger(__name__)
router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = PROJECT_ROOT / "skills" / "registry.json"


def _require_user_ids(request: Request) -> tuple[str, int]:
    """Ensure both Supabase and Tiger user identifiers are present."""
    supabase_user_id = get_current_user_id(request)
    tiger_user_id = get_current_tiger_user_id(request)

    if not supabase_user_id or tiger_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user context missing",
        )

    return str(supabase_user_id), int(tiger_user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SkillImportRequest(BaseModel):
    """Request to import a skill from a repository."""
    repo_url: str = Field(..., description="Git repository URL")
    skill_name: Optional[str] = Field(None, description="Override skill name")
    subpath: Optional[str] = Field(None, description="Path within repo to skill")


class SkillStatusUpdateRequest(BaseModel):
    """Request to manually update skill status."""
    setup_status: str = Field(..., description="New status: ready, needs_configuration, needs_verification, failed")
    notes: Optional[str] = Field(None, description="Reason for status change")


class HealthCheckRequest(BaseModel):
    """Request for skill health check."""
    run_tests: bool = Field(False, description="Run test suites")
    auto_install_deps: bool = Field(False, description="Auto-install missing dependencies")


# ═══════════════════════════════════════════════════════════════════════════════
# SKILL LISTING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/")
async def list_skills(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by setup_status"),
    executor_type: Optional[str] = Query(None, description="Filter by executor type"),
    include_manual: bool = Query(True, description="Include manual skills"),
):
    """
    List all installed skills with their current status.
    
    Returns skill metadata including:
    - Basic info (id, name, description, version)
    - Executor info (type, entrypoint)
    - Status info (setup_status, last_run_at, last_run_status)
    - Health info (last_health_check_at, health_notes)
    """
    _require_user_ids(request)
    
    try:
        registry = load_registry(REGISTRY_PATH)
        skills = registry.list_skills()
        
        # Apply filters
        result = []
        for skill in skills:
            exec_type = skill.executor.executor_type.lower()
            setup_status = getattr(skill, 'setup_status', 'unknown')
            
            # Filter by status
            if status and setup_status != status:
                continue
            
            # Filter by executor type
            if executor_type and exec_type != executor_type.lower():
                continue
            
            # Filter manual skills
            if not include_manual and exec_type == "manual":
                continue
            
            result.append({
                "id": skill.id,
                "name": skill.name,
                "vendor": skill.vendor,
                "description": skill.description,
                "version": skill.version,
                "status": skill.status,
                "setup_status": setup_status,
                "executor": {
                    "type": exec_type,
                    "entrypoint": skill.executor.entrypoint,
                    "timeout_seconds": skill.executor.timeout_seconds,
                    "requires_gpu": skill.executor.requires_gpu,
                },
                "capabilities": [
                    {
                        "domain": cap.domain,
                        "description": cap.description,
                        "tags": cap.tags,
                    }
                    for cap in skill.capabilities
                ],
                "safety": {
                    "risk_level": skill.safety.risk_level,
                    "review_status": skill.safety.review_status,
                },
                "last_run_at": getattr(skill, 'last_run_at', None),
                "last_run_status": getattr(skill, 'last_run_status', None),
                "last_health_check_at": getattr(skill, 'last_health_check_at', None),
                "health_notes": getattr(skill, 'health_notes', []),
                "knowledge_base_id": getattr(skill, 'knowledge_base_id', None),
                "install_path": skill.install_path,
                "source": {
                    "url": skill.source.url,
                    "imported_at": getattr(skill.source, 'imported_at', None),
                },
            })
        
        return {
            "skills": result,
            "count": len(result),
            "total_installed": len(skills),
        }
    
    except Exception as e:
        logger.error(f"[SKILLS API] List error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list skills")


@router.get("/summary")
async def get_skills_summary(request: Request):
    """
    Get summary statistics for the skills system.
    
    Returns:
    - Total skill count
    - Breakdown by status
    - Breakdown by executor type
    - List of skills needing attention
    """
    _require_user_ids(request)
    
    try:
        summary = skill_health_service.get_status_summary()
        return summary
    except Exception as e:
        logger.error(f"[SKILLS API] Summary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get skills summary")


@router.get("/{skill_id}")
async def get_skill(request: Request, skill_id: str):
    """
    Get detailed information about a specific skill.
    """
    _require_user_ids(request)
    
    try:
        registry = load_registry(REGISTRY_PATH)
        skill = registry.get_skill(skill_id)
        
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
        
        return {
            "id": skill.id,
            "name": skill.name,
            "vendor": skill.vendor,
            "description": skill.description,
            "version": skill.version,
            "checksum": skill.checksum,
            "status": skill.status,
            "setup_status": getattr(skill, 'setup_status', 'unknown'),
            "executor": {
                "type": skill.executor.executor_type,
                "entrypoint": skill.executor.entrypoint,
                "runtime": skill.executor.runtime,
                "timeout_seconds": skill.executor.timeout_seconds,
                "env": list(skill.executor.env.keys()) if skill.executor.env else [],
                "requires_gpu": skill.executor.requires_gpu,
            },
            "capabilities": [
                {
                    "domain": cap.domain,
                    "description": cap.description,
                    "trigger_phrases": cap.trigger_phrases,
                    "tags": cap.tags,
                }
                for cap in skill.capabilities
            ],
            "safety": {
                "risk_level": skill.safety.risk_level,
                "notes": skill.safety.notes,
                "review_status": skill.safety.review_status,
            },
            "usage_examples": skill.usage_examples,
            "dependencies": skill.dependencies,
            "tests": skill.tests,
            "install_path": skill.install_path,
            "last_run_at": getattr(skill, 'last_run_at', None),
            "last_run_status": getattr(skill, 'last_run_status', None),
            "last_health_check_at": getattr(skill, 'last_health_check_at', None),
            "health_notes": getattr(skill, 'health_notes', []),
            "knowledge_base_id": getattr(skill, 'knowledge_base_id', None),
            "source": {
                "url": skill.source.url,
                "repo": skill.source.repo,
                "ref": skill.source.ref,
                "license": skill.source.license,
                "imported_at": getattr(skill.source, 'imported_at', None),
            },
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SKILLS API] Get skill error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get skill")


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{skill_id}/health-check")
async def check_skill_health(
    request: Request,
    skill_id: str,
    options: Optional[HealthCheckRequest] = None,
):
    """
    Run health check on a specific skill.
    
    Verifies:
    - Installation directory exists
    - Entrypoint file exists
    - Dependencies are installed
    - Optional: test suite passes
    """
    _require_user_ids(request)
    options = options or HealthCheckRequest()
    
    try:
        result = await skill_health_service.check_skill(
            skill_id=skill_id,
            run_tests=options.run_tests,
            auto_install_deps=options.auto_install_deps,
        )
        
        return result.to_dict()
    
    except Exception as e:
        logger.error(f"[SKILLS API] Health check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/health-check-all")
async def check_all_skills_health(
    request: Request,
    background_tasks: BackgroundTasks,
    run_tests: bool = Query(False),
    async_mode: bool = Query(True, description="Run in background"),
):
    """
    Run health checks on all installed skills.
    
    In async mode, starts the check in the background and returns immediately.
    """
    _require_user_ids(request)
    
    if async_mode:
        # Run in background
        from app.services.skill_health_service import run_scheduled_health_checks
        background_tasks.add_task(run_scheduled_health_checks)
        return {
            "status": "started",
            "message": "Health checks started in background",
        }
    
    try:
        results = await skill_health_service.check_all_skills(
            run_tests=run_tests,
            skip_manual=True,
        )
        
        return {
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
        }
    
    except Exception as e:
        logger.error(f"[SKILLS API] Bulk health check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Health check failed")


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.put("/{skill_id}/status")
async def update_skill_status(
    request: Request,
    skill_id: str,
    update: SkillStatusUpdateRequest,
):
    """
    Manually update a skill's setup_status.
    
    Valid statuses:
    - ready: Skill is verified and ready for use
    - needs_configuration: Requires env vars or credential setup
    - needs_verification: Needs health check before use
    - failed: Health check or execution failed
    """
    _require_user_ids(request)
    
    valid_statuses = {"ready", "needs_configuration", "needs_verification", "failed"}
    if update.setup_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    try:
        if update.setup_status == "ready":
            success = await skill_health_service.mark_ready(skill_id, update.notes)
        elif update.setup_status == "failed":
            success = await skill_health_service.mark_failed(skill_id, update.notes or "Manually marked failed")
        else:
            # Generic status update
            registry = load_registry(REGISTRY_PATH)
            skill = registry.get_skill(skill_id)
            if not skill:
                raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
            
            skill.setup_status = update.setup_status
            skill.last_health_check_at = datetime.utcnow().isoformat()
            skill.health_notes = getattr(skill, 'health_notes', []) or []
            if update.notes:
                skill.health_notes.append(update.notes)
            registry.update_skill(skill)
            success = True
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
        
        return {
            "skill_id": skill_id,
            "new_status": update.setup_status,
            "message": f"Status updated to '{update.setup_status}'",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SKILLS API] Status update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update status")


# ═══════════════════════════════════════════════════════════════════════════════
# SKILL IMPORT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/import")
async def import_skill(
    request: Request,
    import_request: SkillImportRequest,
):
    """
    Import a new skill from a Git repository.
    
    The skill will be:
    1. Cloned from the repository
    2. Manifest detected and normalized
    3. Registered in the skill registry
    4. Set to 'needs_verification' status
    """
    _require_user_ids(request)
    
    try:
        from app.skills.skill_importer import skill_importer
        
        metadata = skill_importer.install_skill(
            repo_url=import_request.repo_url,
            skill_name=import_request.skill_name,
            subpath=import_request.subpath,
        )
        
        return {
            "status": "imported",
            "skill": {
                "id": metadata.id,
                "name": metadata.name,
                "vendor": metadata.vendor,
                "description": metadata.description,
                "setup_status": metadata.setup_status,
            },
            "message": f"Skill '{metadata.name}' imported successfully. Run health check to verify.",
        }
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[SKILLS API] Import error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION HISTORY ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{skill_id}/history")
async def get_skill_history(
    request: Request,
    skill_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get execution history for a specific skill.
    
    Returns recent runs from the skill_runs database table.
    """
    _, tiger_user_id = _require_user_ids(request)
    
    try:
        from app.database import db
        
        rows = await db.fetch(
            """
            SELECT 
                run_id, skill_id, user_id, status, 
                started_at, finished_at, duration_seconds,
                output_preview, error_message, created_at
            FROM skill_runs
            WHERE skill_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            skill_id, limit
        )
        
        history = []
        for row in rows:
            history.append({
                "run_id": str(row["run_id"]),
                "skill_id": row["skill_id"],
                "user_id": row["user_id"],
                "status": row["status"],
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
                "duration_seconds": float(row["duration_seconds"]) if row["duration_seconds"] else None,
                "output_preview": row["output_preview"],
                "error_message": row["error_message"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })
        
        return {
            "skill_id": skill_id,
            "history": history,
            "count": len(history),
        }
    
    except Exception as e:
        logger.error(f"[SKILLS API] History error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get skill history")


"""
Image Generation API - Nicole's Creative Studio

Endpoints for generating, managing, and organizing AI-generated images.
Supports multiple models: Recraft V3, FLUX Pro/Schnell, Ideogram V2.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from decimal import Decimal
import json
import logging

from app.middleware.alphawave_auth import get_current_user
from app.services.alphawave_image_generation_service import image_service

logger = logging.getLogger(__name__)


def serialize_for_json(obj: Any) -> Any:
    """Convert Decimal and other non-JSON-serializable types."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_json(v) for v in obj]
    return obj

router = APIRouter(tags=["images"])


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateRequest(BaseModel):
    """Request body for image generation."""
    prompt: str = Field(..., min_length=1, max_length=2000, description="Image description")
    model_key: str = Field(default="recraft", description="Model: recraft, flux_pro, flux_schnell, ideogram")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Model-specific parameters")
    batch_count: int = Field(default=1, ge=1, le=4, description="Number of variants (1-4)")
    job_id: Optional[int] = Field(default=None, description="Existing job ID to add variants to")
    project: Optional[str] = Field(default=None, description="Project name for organization")
    use_case: Optional[str] = Field(default=None, description="logo, hero, social, poster, icon")
    preset_key: Optional[str] = Field(default=None, description="Preset key to use")
    enhance_prompt: bool = Field(default=True, description="Enhance prompt via Claude")


class CreateJobRequest(BaseModel):
    """Request body for creating a new job."""
    title: str = Field(..., min_length=1, max_length=200)
    project: Optional[str] = None
    use_case: Optional[str] = None
    preset_used: Optional[str] = None


class CreatePresetRequest(BaseModel):
    """Request body for creating a preset."""
    preset_key: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z0-9_]+$')
    name: str = Field(..., min_length=1, max_length=100)
    model_key: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    batch_count: int = Field(default=1, ge=1, le=4)
    use_case: Optional[str] = None
    smart_prompt_enabled: bool = True


class FavoriteRequest(BaseModel):
    """Request body for toggling favorite."""
    is_favorite: bool


class RatingRequest(BaseModel):
    """Request body for rating a variant."""
    rating: int = Field(..., ge=1, le=5)


# ============================================================================
# Generation Endpoints
# ============================================================================

@router.post("/generate")
async def generate_image(
    request: GenerateRequest,
    user=Depends(get_current_user),
):
    """
    Generate image(s) using the specified model.
    
    Returns generated variants with URLs, metadata, and cost information.
    """
    try:
        logger.info(f"[IMAGE API] Generate request: model={request.model_key}, batch={request.batch_count}")
        
        # Load preset if specified
        parameters = dict(request.parameters)
        if request.preset_key:
            preset = await image_service.get_preset(request.preset_key, user.user_id)
            if preset:
                # Merge preset params with request params (request takes precedence)
                preset_params = preset.get("parameters", {})
                if isinstance(preset_params, str):
                    preset_params = json.loads(preset_params)
                parameters = {**preset_params, **parameters}
        
        result = await image_service.generate(
            user_id=user.user_id,
            prompt=request.prompt,
            model_key=request.model_key,
            parameters=parameters,
            batch_count=request.batch_count,
            job_id=request.job_id,
            project=request.project,
            use_case=request.use_case,
            preset_used=request.preset_key,
            enhance_prompt_enabled=request.enhance_prompt,
        )
        
        return {
            "success": True,
            **result,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"[IMAGE API] Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"[IMAGE API] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Image generation failed")


@router.post("/generate/stream")
async def generate_image_stream(
    request: GenerateRequest,
    user=Depends(get_current_user),
):
    """
    Generate image(s) with SSE progress streaming.
    
    Streams progress updates during generation:
    - {"status": "starting", "message": "..."}
    - {"status": "enhancing", "message": "..."}
    - {"status": "generating", "progress": 0.5}
    - {"status": "complete", "variants": [...]}
    - {"status": "error", "message": "..."}
    """
    async def event_stream():
        try:
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing generation...'})}\n\n"
            
            # Load preset if specified
            parameters = dict(request.parameters)
            if request.preset_key:
                preset = await image_service.get_preset(request.preset_key, user.user_id)
                if preset:
                    preset_params = preset.get("parameters", {})
                    if isinstance(preset_params, str):
                        preset_params = json.loads(preset_params)
                    parameters = {**preset_params, **parameters}
            
            if request.enhance_prompt:
                yield f"data: {json.dumps({'status': 'enhancing', 'message': 'Enhancing prompt with Claude...'})}\n\n"
            
            yield f"data: {json.dumps({'status': 'generating', 'message': f'Generating {request.batch_count} variant(s)...'})}\n\n"
            
            result = await image_service.generate(
                user_id=user.user_id,
                prompt=request.prompt,
                model_key=request.model_key,
                parameters=parameters,
                batch_count=request.batch_count,
                job_id=request.job_id,
                project=request.project,
                use_case=request.use_case,
                preset_used=request.preset_key,
                enhance_prompt_enabled=request.enhance_prompt,
            )
            
            yield f"data: {json.dumps(serialize_for_json({'status': 'complete', **result}))}\n\n"
            
        except Exception as e:
            logger.exception(f"[IMAGE API] Stream generation error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# Job Management Endpoints
# ============================================================================

@router.post("/jobs")
async def create_job(
    request: CreateJobRequest,
    user=Depends(get_current_user),
):
    """Create a new image job (container for variants)."""
    job = await image_service.create_job(
        user_id=user.user_id,
        title=request.title,
        project=request.project,
        use_case=request.use_case,
        preset_used=request.preset_used,
    )
    return {"success": True, "job": job}


@router.get("/jobs")
async def list_jobs(
    project: Optional[str] = Query(default=None),
    use_case: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """List image jobs with optional filters."""
    jobs = await image_service.list_jobs(
        user_id=user.user_id,
        project=project,
        use_case=use_case,
        limit=limit,
    )
    return {"success": True, "jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: int,
    user=Depends(get_current_user),
):
    """Get a single job with metadata."""
    job = await image_service.get_job(job_id, user.user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "job": job}


@router.get("/jobs/{job_id}/variants")
async def get_job_variants(
    job_id: int,
    user=Depends(get_current_user),
):
    """Get all variants for a job."""
    variants = await image_service.get_variants(job_id, user.user_id)
    return {"success": True, "variants": variants, "count": len(variants)}


# ============================================================================
# Variant Management Endpoints
# ============================================================================

@router.post("/variants/{variant_id}/favorite")
async def toggle_favorite(
    variant_id: int,
    request: FavoriteRequest,
    user=Depends(get_current_user),
):
    """Toggle favorite status on a variant."""
    success = await image_service.toggle_favorite(variant_id, user.user_id, request.is_favorite)
    if not success:
        raise HTTPException(status_code=404, detail="Variant not found")
    return {"success": True, "is_favorite": request.is_favorite}


@router.post("/variants/{variant_id}/rate")
async def rate_variant(
    variant_id: int,
    request: RatingRequest,
    user=Depends(get_current_user),
):
    """Rate a variant (1-5 stars)."""
    try:
        success = await image_service.rate_variant(variant_id, user.user_id, request.rating)
        if not success:
            raise HTTPException(status_code=404, detail="Variant not found")
        return {"success": True, "rating": request.rating}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/favorites")
async def list_favorites(
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(get_current_user),
):
    """List all favorited variants."""
    from app.database import db as db_manager
    
    rows = await db_manager.pool.fetch(
        """
        SELECT v.*, j.title as job_title, j.project
        FROM image_variants v
        JOIN image_jobs j ON v.job_id = j.job_id
        WHERE v.user_id = $1 AND v.is_favorite = TRUE
        ORDER BY v.created_at DESC
        LIMIT $2
        """,
        user.user_id,
        limit,
    )
    return {"success": True, "variants": [dict(r) for r in rows]}


# ============================================================================
# Preset Management Endpoints
# ============================================================================

@router.get("/presets")
async def list_presets(user=Depends(get_current_user)):
    """List all available presets (system + user-created)."""
    presets = await image_service.list_presets(user.user_id)
    return {"success": True, "presets": presets, "count": len(presets)}


@router.get("/presets/{preset_key}")
async def get_preset(
    preset_key: str,
    user=Depends(get_current_user),
):
    """Get a specific preset by key."""
    preset = await image_service.get_preset(preset_key, user.user_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"success": True, "preset": preset}


@router.post("/presets")
async def create_preset(
    request: CreatePresetRequest,
    user=Depends(get_current_user),
):
    """Create or update a user preset."""
    try:
        preset = await image_service.create_preset(
            user_id=user.user_id,
            preset_key=request.preset_key,
            name=request.name,
            model_key=request.model_key,
            parameters=request.parameters,
            batch_count=request.batch_count,
            use_case=request.use_case,
            smart_prompt_enabled=request.smart_prompt_enabled,
        )
        return {"success": True, "preset": preset}
    except Exception as e:
        logger.exception(f"[IMAGE API] Preset creation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/presets/{preset_key}")
async def delete_preset(
    preset_key: str,
    user=Depends(get_current_user),
):
    """Delete a user-created preset (cannot delete system presets)."""
    from app.database import db as db_manager
    
    result = await db_manager.pool.execute(
        """
        DELETE FROM image_presets
        WHERE preset_key = $1 AND user_id = $2 AND is_system = FALSE
        """,
        preset_key,
        user.user_id,
    )
    
    if "DELETE 0" in result:
        raise HTTPException(status_code=404, detail="Preset not found or cannot be deleted")
    
    return {"success": True, "deleted": preset_key}


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/models")
async def list_models():
    """List available models with their capabilities (public endpoint)."""
    models = []
    for key, cfg in image_service.MODEL_CONFIGS.items():
        models.append({
            "key": key,
            "name": cfg.get("name", key.replace("_", " ").title()),
            "mode": cfg.get("mode"),
            "supports_batch": cfg.get("supports_batch", False),
            "max_batch": cfg.get("max_batch", 1),
            "cost_per_image": image_service.MODEL_COSTS.get(key, 0),
            "styles": cfg.get("styles"),
            "style_types": cfg.get("style_types"),
            "default_params": cfg.get("default_params", {}),
        })
    return {"success": True, "models": models}


@router.get("/stats")
async def get_stats(user=Depends(get_current_user)):
    """Get usage statistics for the current user."""
    from app.database import db as db_manager
    
    stats = await db_manager.pool.fetchrow(
        """
        SELECT 
            COUNT(DISTINCT j.job_id) as total_jobs,
            COUNT(v.variant_id) as total_variants,
            SUM(v.cost_usd) as total_cost,
            COUNT(v.variant_id) FILTER (WHERE v.is_favorite) as favorites_count,
            AVG(v.generation_time_ms) as avg_generation_time_ms
        FROM image_jobs j
        LEFT JOIN image_variants v ON j.job_id = v.job_id
        WHERE j.user_id = $1
        """,
        user.user_id,
    )
    
    return {
        "success": True,
        "stats": {
            "total_jobs": stats["total_jobs"] or 0,
            "total_variants": stats["total_variants"] or 0,
            "total_cost_usd": float(stats["total_cost"] or 0),
            "favorites_count": stats["favorites_count"] or 0,
            "avg_generation_time_ms": float(stats["avg_generation_time_ms"] or 0),
        }
    }

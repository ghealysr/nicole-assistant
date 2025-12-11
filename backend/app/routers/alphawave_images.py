"""
Image generation API (current: synchronous). Future: SSE for progress.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any

from app.middleware.alphawave_auth import get_current_user
from app.services.alphawave_image_generation_service import image_service

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("/generate")
async def generate_image(
    prompt: str,
    model_key: str = "recraft",
    parameters: Dict[str, Any] = {},
    batch_count: int = 1,
    job_id: Optional[int] = None,
    project: Optional[str] = None,
    use_case: Optional[str] = None,
    preset_used: Optional[str] = None,
    user=Depends(get_current_user),
):
    """
    Generate image(s) synchronously.
    """
    try:
        return await image_service.generate(
            user_id=user.user_id,
            prompt=prompt,
            model_key=model_key,
            parameters=parameters,
            batch_count=batch_count,
            job_id=job_id,
            project=project,
            use_case=use_case,
            preset_used=preset_used,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs")
async def list_jobs(limit: int = 20, user=Depends(get_current_user)):
    from app.database import db_manager

    rows = await db_manager.pool.fetch(
        """
        SELECT j.*, COUNT(v.variant_id) as variant_count
        FROM image_jobs j
        LEFT JOIN image_variants v ON j.job_id = v.job_id
        WHERE j.user_id = $1
        GROUP BY j.job_id
        ORDER BY j.updated_at DESC
        LIMIT $2
        """,
        user.user_id,
        limit,
    )
    return [dict(r) for r in rows]


@router.get("/jobs/{job_id}/variants")
async def job_variants(job_id: int, user=Depends(get_current_user)):
    from app.database import db_manager

    rows = await db_manager.pool.fetch(
        """
        SELECT * FROM image_variants
        WHERE job_id = $1 AND user_id = $2
        ORDER BY version_number ASC
        """,
        job_id,
        user.user_id,
    )
    return [dict(r) for r in rows]

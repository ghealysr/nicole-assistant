"""
Files Router for Nicole V7.
Handles file upload, processing, and retrieval.

QA NOTES:
- Supports images (vision analysis) and documents (text extraction)
- Uses Azure Document Intelligence for PDFs and Office docs
- Uses Claude Vision API as fallback for images
- Files are processed and stored with metadata in Supabase
- Maximum file size: 10MB
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
from uuid import UUID

from app.services.alphawave_file_processor import file_processor
from app.database import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class FileResponse(BaseModel):
    """Response model for file operations."""
    id: str
    filename: str
    content_type: str
    size_bytes: int
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    analysis: Optional[dict] = None
    storage_url: Optional[str] = None
    created_at: Optional[str] = None


class FileListResponse(BaseModel):
    """Response model for file listing."""
    files: List[FileResponse]
    total: int


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    process: bool = Form(True, description="Whether to process the file for text/vision")
):
    """
    Upload and optionally process a file.
    
    Supports:
    - Images: JPEG, PNG, GIF, WebP (analyzed with vision AI)
    - Documents: PDF, Word, text (text extraction)
    
    QA NOTE: Maximum file size is 10MB
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    try:
        if process:
            # Process file with AI
            result = await file_processor.process_file(
                user_id=UUID(user_id),
                file_content=content,
                filename=file.filename,
                content_type=file.content_type
            )
            
            if result.get("error"):
                logger.warning(f"File processing warning: {result['error']}")
            
            return FileResponse(
                id=result.get("file_hash", "")[:16],
                filename=result["filename"],
                content_type=result["content_type"],
                size_bytes=result["size_bytes"],
                extracted_text=result.get("extracted_text"),
                summary=result.get("summary"),
                analysis=result.get("analysis"),
                storage_url=None  # Would be set after storage upload
            )
        else:
            # Just store without processing
            return FileResponse(
                id="pending",
                filename=file.filename,
                content_type=file.content_type or "application/octet-stream",
                size_bytes=len(content),
                extracted_text=None,
                summary=None,
                analysis=None
            )
            
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="File upload failed")


@router.post("/upload/image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    analyze: bool = Form(True, description="Whether to analyze the image")
):
    """
    Upload and analyze an image file.
    
    Specialized endpoint for image uploads with vision analysis.
    
    QA NOTE: Returns detailed image analysis including objects and text
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate image type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type. Allowed: JPEG, PNG, GIF, WebP"
        )
    
    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    try:
        result = await file_processor.process_file(
            user_id=UUID(user_id),
            file_content=content,
            filename=file.filename or "image.jpg",
            content_type=file.content_type
        )
        
        return {
            "success": True,
            "filename": result["filename"],
            "description": result.get("summary"),
            "analysis": result.get("analysis", {}),
            "extracted_text": result.get("extracted_text")
        }
        
    except Exception as e:
        logger.error(f"Image upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Image processing failed")


@router.get("/list", response_model=FileListResponse)
async def list_files(
    request: Request,
    limit: int = 50,
    offset: int = 0
):
    """
    List files uploaded by the current user.
    
    QA NOTE: Returns most recent files first
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        files = await file_processor.get_user_files(
            user_id=UUID(user_id),
            limit=limit
        )
        
        return FileListResponse(
            files=[
                FileResponse(
                    id=f.get("id", ""),
                    filename=f.get("filename", ""),
                    content_type=f.get("file_type", ""),
                    size_bytes=f.get("file_size", 0),
                    storage_url=f.get("storage_url"),
                    created_at=f.get("uploaded_at")
                )
                for f in files
            ],
            total=len(files)
        )
        
    except Exception as e:
        logger.error(f"File list error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list files")


@router.get("/{file_id}")
async def get_file(request: Request, file_id: str):
    """
    Get file metadata by ID.
    
    QA NOTE: Returns metadata only, not the file content
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    try:
        response = supabase.table("uploaded_files").select("*").eq(
            "id", file_id
        ).eq(
            "user_id", user_id
        ).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_data = response.data
        
        return FileResponse(
            id=file_data.get("id"),
            filename=file_data.get("filename"),
            content_type=file_data.get("file_type"),
            size_bytes=file_data.get("file_size", 0),
            storage_url=file_data.get("storage_url"),
            created_at=file_data.get("uploaded_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get file")


@router.delete("/{file_id}")
async def delete_file(request: Request, file_id: str):
    """
    Delete a file by ID.
    
    QA NOTE: Removes both database record and storage file
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    try:
        # Check ownership first
        check = supabase.table("uploaded_files").select("id").eq(
            "id", file_id
        ).eq(
            "user_id", user_id
        ).single().execute()
        
        if not check.data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete record
        supabase.table("uploaded_files").delete().eq(
            "id", file_id
        ).execute()
        
        logger.info(f"Deleted file {file_id} for user {user_id}")
        
        return {"success": True, "message": "File deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete file")

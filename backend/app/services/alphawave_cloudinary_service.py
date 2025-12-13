"""
Cloudinary Integration Service for Nicole V7

Provides image upload and management for:
- Screenshot storage from web scraping
- User-uploaded images
- Generated image storage
- Inspiration board assets

Features:
- Automatic optimization
- Folder organization by project
- Signed URLs for private assets
- Transformation on the fly
"""

import logging
import base64
from typing import Optional, Dict, Any
from datetime import datetime

import cloudinary
import cloudinary.uploader
import cloudinary.api

from app.config import settings

logger = logging.getLogger(__name__)


class CloudinaryService:
    """
    Cloudinary integration for Nicole's image storage needs.
    
    Usage:
        url = await cloudinary_service.upload_screenshot(base64_data, "project-name")
        url = await cloudinary_service.upload_image(file_bytes, "folder/filename")
    """
    
    def __init__(self):
        """Initialize Cloudinary with credentials."""
        self._configured = False
        self._configure()
    
    def _configure(self) -> None:
        """Configure Cloudinary SDK."""
        if not all([
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET
        ]):
            logger.warning("[CLOUDINARY] Missing credentials - service disabled")
            return
        
        try:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
            self._configured = True
            logger.info("[CLOUDINARY] Configured successfully")
        except Exception as e:
            logger.error(f"[CLOUDINARY] Configuration failed: {e}")
    
    @property
    def is_configured(self) -> bool:
        """Check if Cloudinary is properly configured."""
        return self._configured
    
    async def upload_screenshot(
        self,
        base64_data: str,
        project_name: str,
        description: Optional[str] = None,
        url_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a screenshot (base64) to Cloudinary.
        
        Args:
            base64_data: Base64-encoded image data
            project_name: Project name for folder organization
            description: Optional description for the screenshot
            url_source: Original URL that was screenshotted
            
        Returns:
            Dict with url, public_id, and metadata
        """
        if not self._configured:
            return {"error": "Cloudinary not configured", "success": False}
        
        try:
            # Clean base64 data (remove data URI prefix if present)
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder = f"nicole/screenshots/{project_name}"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                f"data:image/png;base64,{base64_data}",
                folder=folder,
                public_id=f"screenshot_{timestamp}",
                resource_type="image",
                context={
                    "description": description or "",
                    "source_url": url_source or "",
                    "captured_at": timestamp
                },
                tags=["screenshot", "nicole", project_name],
                # Auto-optimize for web
                transformation={
                    "quality": "auto:good",
                    "fetch_format": "auto"
                }
            )
            
            logger.info(f"[CLOUDINARY] Screenshot uploaded: {result.get('public_id')}")
            
            return {
                "success": True,
                "url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "bytes": result.get("bytes"),
                "folder": folder
            }
            
        except Exception as e:
            logger.error(f"[CLOUDINARY] Upload failed: {e}")
            return {"error": str(e), "success": False}
    
    async def upload_image(
        self,
        image_data: bytes,
        folder: str,
        filename: Optional[str] = None,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Upload an image file to Cloudinary.
        
        Args:
            image_data: Raw image bytes
            folder: Destination folder path
            filename: Optional custom filename
            tags: Optional list of tags
            
        Returns:
            Dict with url and metadata
        """
        if not self._configured:
            return {"error": "Cloudinary not configured", "success": False}
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            public_id = filename or f"image_{timestamp}"
            
            result = cloudinary.uploader.upload(
                image_data,
                folder=f"nicole/{folder}",
                public_id=public_id,
                resource_type="image",
                tags=tags or ["nicole"],
                transformation={
                    "quality": "auto:good",
                    "fetch_format": "auto"
                }
            )
            
            logger.info(f"[CLOUDINARY] Image uploaded: {result.get('public_id')}")
            
            return {
                "success": True,
                "url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "bytes": result.get("bytes")
            }
            
        except Exception as e:
            logger.error(f"[CLOUDINARY] Upload failed: {e}")
            return {"error": str(e), "success": False}
    
    async def upload_from_url(
        self,
        image_url: str,
        folder: str,
        filename: Optional[str] = None,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Upload an image directly from URL to Cloudinary.
        
        Args:
            image_url: URL of the image to upload
            folder: Destination folder path
            filename: Optional custom filename
            tags: Optional list of tags
            
        Returns:
            Dict with url and metadata
        """
        if not self._configured:
            return {"error": "Cloudinary not configured", "success": False}
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            public_id = filename or f"url_import_{timestamp}"
            
            result = cloudinary.uploader.upload(
                image_url,
                folder=f"nicole/{folder}",
                public_id=public_id,
                resource_type="image",
                tags=tags or ["nicole", "url_import"],
                transformation={
                    "quality": "auto:good",
                    "fetch_format": "auto"
                }
            )
            
            logger.info(f"[CLOUDINARY] URL image uploaded: {result.get('public_id')}")
            
            return {
                "success": True,
                "url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "source_url": image_url,
                "width": result.get("width"),
                "height": result.get("height")
            }
            
        except Exception as e:
            logger.error(f"[CLOUDINARY] URL upload failed: {e}")
            return {"error": str(e), "success": False}
    
    async def delete_image(self, public_id: str) -> bool:
        """Delete an image from Cloudinary."""
        if not self._configured:
            return False
        
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"[CLOUDINARY] Delete failed: {e}")
            return False
    
    async def get_folder_images(
        self,
        folder: str,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        List images in a Cloudinary folder.
        
        Args:
            folder: Folder path (e.g., "screenshots/project-name")
            max_results: Maximum number of results
            
        Returns:
            Dict with resources list
        """
        if not self._configured:
            return {"error": "Cloudinary not configured", "success": False}
        
        try:
            result = cloudinary.api.resources(
                type="upload",
                prefix=f"nicole/{folder}",
                max_results=max_results
            )
            
            return {
                "success": True,
                "images": [
                    {
                        "url": r.get("secure_url"),
                        "public_id": r.get("public_id"),
                        "created_at": r.get("created_at"),
                        "width": r.get("width"),
                        "height": r.get("height")
                    }
                    for r in result.get("resources", [])
                ],
                "total": len(result.get("resources", []))
            }
            
        except Exception as e:
            logger.error(f"[CLOUDINARY] List folder failed: {e}")
            return {"error": str(e), "success": False}


# Singleton instance
cloudinary_service = CloudinaryService()


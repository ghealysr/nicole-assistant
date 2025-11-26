"""
File Processor Service for Nicole V7.
Handles file uploads, processing, and extraction using Azure AI services.

QA NOTES:
- Supports images (vision analysis), PDFs, and documents
- Uses Azure Document Intelligence for text extraction
- Uses Azure Computer Vision for image analysis
- Falls back to Claude Vision API if Azure unavailable
- Files are stored in Supabase Storage / DO Spaces
"""

import base64
import hashlib
import logging
import mimetypes
from typing import Optional, Dict, Any, List
from uuid import UUID
import httpx

from app.config import settings
from app.database import get_supabase
from app.integrations.alphawave_claude import claude_client

logger = logging.getLogger(__name__)

# Supported file types
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
SUPPORTED_DOCUMENT_TYPES = {"application/pdf", "application/msword", 
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "text/plain", "text/markdown"}


class AlphawaveFileProcessor:
    """
    Service for processing uploaded files.
    
    Features:
    - Image analysis with Azure Computer Vision / Claude Vision
    - Document text extraction with Azure Document Intelligence
    - Automatic file type detection
    - Content summarization
    - File metadata management
    """
    
    def __init__(self):
        """Initialize the file processor."""
        self.supabase = get_supabase()
        self._azure_vision_available = bool(
            settings.AZURE_VISION_ENDPOINT and settings.AZURE_VISION_KEY
        )
        self._azure_document_available = bool(
            settings.AZURE_DOCUMENT_ENDPOINT and settings.AZURE_DOCUMENT_KEY
        )
    
    async def process_file(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an uploaded file and extract relevant information.
        
        Args:
            user_id: The user's UUID
            file_content: Raw file bytes
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            
        Returns:
            Dict with processing results including extracted text, analysis, etc.
            
        QA NOTE: Main entry point for file processing
        """
        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"
        
        # Generate file hash for deduplication
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        result = {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(file_content),
            "file_hash": file_hash,
            "extracted_text": None,
            "analysis": None,
            "summary": None,
            "error": None
        }
        
        try:
            # Route to appropriate processor
            if content_type in SUPPORTED_IMAGE_TYPES:
                analysis = await self._process_image(file_content, content_type)
                result["analysis"] = analysis
                result["extracted_text"] = analysis.get("text_content")
                result["summary"] = analysis.get("description")
                
            elif content_type in SUPPORTED_DOCUMENT_TYPES:
                extraction = await self._process_document(file_content, content_type)
                result["extracted_text"] = extraction.get("text")
                result["summary"] = await self._summarize_text(extraction.get("text", ""))
                result["analysis"] = {
                    "page_count": extraction.get("page_count"),
                    "word_count": len(extraction.get("text", "").split())
                }
                
            elif content_type == "text/plain":
                text = file_content.decode("utf-8", errors="replace")
                result["extracted_text"] = text
                result["summary"] = await self._summarize_text(text)
                result["analysis"] = {"word_count": len(text.split())}
                
            else:
                result["error"] = f"Unsupported file type: {content_type}"
                logger.warning(f"Unsupported file type: {content_type}")
            
            # Save file record to database
            await self._save_file_record(user_id, result)
            
        except Exception as e:
            logger.error(f"File processing error: {e}", exc_info=True)
            result["error"] = str(e)
        
        return result
    
    async def _process_image(
        self,
        image_bytes: bytes,
        content_type: str
    ) -> Dict[str, Any]:
        """
        Process an image file using Azure Vision or Claude Vision.
        
        QA NOTE: Tries Azure first, falls back to Claude if unavailable
        """
        # Try Azure Computer Vision first
        if self._azure_vision_available:
            try:
                return await self._analyze_with_azure_vision(image_bytes)
            except Exception as e:
                logger.warning(f"Azure Vision failed, falling back to Claude: {e}")
        
        # Fallback to Claude Vision
        return await self._analyze_with_claude_vision(image_bytes, content_type)
    
    async def _analyze_with_azure_vision(
        self,
        image_bytes: bytes
    ) -> Dict[str, Any]:
        """Analyze image using Azure Computer Vision."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AZURE_VISION_ENDPOINT}/vision/v3.2/analyze",
                params={
                    "visualFeatures": "Description,Tags,Objects,Read",
                    "language": "en"
                },
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_VISION_KEY,
                    "Content-Type": "application/octet-stream"
                },
                content=image_bytes,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "description": data.get("description", {}).get("captions", [{}])[0].get("text"),
                "tags": [tag["name"] for tag in data.get("tags", [])],
                "objects": [obj["object"] for obj in data.get("objects", [])],
                "text_content": self._extract_ocr_text(data.get("readResult", {})),
                "confidence": data.get("description", {}).get("captions", [{}])[0].get("confidence", 0)
            }
    
    async def _analyze_with_claude_vision(
        self,
        image_bytes: bytes,
        content_type: str
    ) -> Dict[str, Any]:
        """Analyze image using Claude Vision API."""
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # Use Claude's vision capability
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content_type,
                        "data": image_b64
                    }
                },
                {
                    "type": "text",
                    "text": """Analyze this image and provide:
1. A brief description (1-2 sentences)
2. Key objects or elements visible
3. Any text visible in the image
4. Relevant tags/categories

Format your response as:
DESCRIPTION: [description]
OBJECTS: [comma-separated list]
TEXT: [any visible text, or "none"]
TAGS: [comma-separated tags]"""
                }
            ]
        }]
        
        try:
            response = await claude_client.generate_response(
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse the response
            result = {
                "description": None,
                "objects": [],
                "text_content": None,
                "tags": [],
                "confidence": 0.8  # Claude doesn't provide confidence scores
            }
            
            if response:
                lines = response.strip().split("\n")
                for line in lines:
                    if line.startswith("DESCRIPTION:"):
                        result["description"] = line.replace("DESCRIPTION:", "").strip()
                    elif line.startswith("OBJECTS:"):
                        result["objects"] = [o.strip() for o in line.replace("OBJECTS:", "").split(",")]
                    elif line.startswith("TEXT:"):
                        text = line.replace("TEXT:", "").strip()
                        if text.lower() != "none":
                            result["text_content"] = text
                    elif line.startswith("TAGS:"):
                        result["tags"] = [t.strip() for t in line.replace("TAGS:", "").split(",")]
            
            return result
            
        except Exception as e:
            logger.error(f"Claude Vision error: {e}")
            return {"description": "Unable to analyze image", "error": str(e)}
    
    async def _process_document(
        self,
        doc_bytes: bytes,
        content_type: str
    ) -> Dict[str, Any]:
        """
        Process a document file using Azure Document Intelligence.
        
        QA NOTE: For PDFs and Office documents
        """
        if self._azure_document_available:
            try:
                return await self._extract_with_azure_document(doc_bytes)
            except Exception as e:
                logger.warning(f"Azure Document Intelligence failed: {e}")
        
        # Basic fallback for text-based documents
        if content_type == "text/plain":
            text = doc_bytes.decode("utf-8", errors="replace")
            return {"text": text, "page_count": 1}
        
        return {
            "text": "",
            "error": "Document extraction not available (Azure not configured)"
        }
    
    async def _extract_with_azure_document(
        self,
        doc_bytes: bytes
    ) -> Dict[str, Any]:
        """Extract text using Azure Document Intelligence."""
        async with httpx.AsyncClient() as client:
            # Start analysis
            response = await client.post(
                f"{settings.AZURE_DOCUMENT_ENDPOINT}/formrecognizer/documentModels/prebuilt-read:analyze",
                params={"api-version": "2023-07-31"},
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_DOCUMENT_KEY,
                    "Content-Type": "application/octet-stream"
                },
                content=doc_bytes,
                timeout=60.0
            )
            response.raise_for_status()
            
            # Get operation location
            operation_url = response.headers.get("Operation-Location")
            if not operation_url:
                raise ValueError("No operation URL returned")
            
            # Poll for results
            import asyncio
            for _ in range(30):  # Max 30 attempts
                await asyncio.sleep(2)
                result_response = await client.get(
                    operation_url,
                    headers={"Ocp-Apim-Subscription-Key": settings.AZURE_DOCUMENT_KEY}
                )
                result = result_response.json()
                
                if result.get("status") == "succeeded":
                    # Extract text from result
                    content = result.get("analyzeResult", {}).get("content", "")
                    pages = result.get("analyzeResult", {}).get("pages", [])
                    return {
                        "text": content,
                        "page_count": len(pages)
                    }
                elif result.get("status") == "failed":
                    raise ValueError(f"Analysis failed: {result.get('error')}")
            
            raise TimeoutError("Document analysis timed out")
    
    def _extract_ocr_text(self, read_result: Dict) -> Optional[str]:
        """Extract text from Azure OCR read result."""
        if not read_result:
            return None
        
        lines = []
        for page in read_result.get("pages", []):
            for line in page.get("lines", []):
                lines.append(line.get("text", ""))
        
        return "\n".join(lines) if lines else None
    
    async def _summarize_text(
        self,
        text: str,
        max_length: int = 200
    ) -> Optional[str]:
        """Generate a summary of extracted text using Claude."""
        if not text or len(text) < 100:
            return text[:max_length] if text else None
        
        try:
            response = await claude_client.generate_response(
                messages=[{
                    "role": "user",
                    "content": f"Summarize the following text in 2-3 sentences:\n\n{text[:3000]}"
                }],
                max_tokens=150,
                temperature=0.3
            )
            return response
        except Exception as e:
            logger.warning(f"Summarization failed: {e}")
            return text[:max_length] + "..."
    
    async def _save_file_record(
        self,
        user_id: UUID,
        result: Dict[str, Any]
    ) -> bool:
        """Save file metadata to database."""
        if not self.supabase:
            return False
        
        try:
            self.supabase.table("uploaded_files").insert({
                "user_id": str(user_id),
                "filename": result["filename"],
                "file_type": result["content_type"],
                "file_size": result["size_bytes"],
                "storage_url": f"processed/{result['file_hash'][:8]}/{result['filename']}"
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error saving file record: {e}")
            return False
    
    async def get_user_files(
        self,
        user_id: UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of files uploaded by a user."""
        if not self.supabase:
            return []
        
        try:
            response = self.supabase.table("uploaded_files").select("*").eq(
                "user_id", str(user_id)
            ).order(
                "uploaded_at", desc=True
            ).limit(limit).execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching user files: {e}")
            return []


# Global service instance
file_processor = AlphawaveFileProcessor()


"""
Documents Router for Nicole V7 (Tiger Native).
Production-grade document intelligence API.

Features:
- Upload and process documents (PDF, DOCX, images)
- Process URLs/links
- Search document content
- Retrieve document summaries
- List user documents

All documents are:
- Extracted with Azure Document Intelligence
- Analyzed with Claude for summaries and key points
- Chunked and embedded for semantic search (Tiger pgvectorscale)
- Saved to memory for persistent recall
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import logging
from uuid import UUID

from app.database import db
from app.middleware.alphawave_auth import get_current_tiger_user_id, get_current_user_id
from app.services.alphawave_document_service import document_service
from app.services.alphawave_link_processor import link_processor

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DocumentUploadResponse(BaseModel):
    """Response from document upload."""
    document_id: int
    title: str
    summary: Optional[str] = None
    key_points: List[str] = []
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    chunks_created: int = 0
    memories_created: int = 0
    status: str


class DocumentSearchRequest(BaseModel):
    """Request for document search."""
    query: str
    limit: int = 5


class DocumentSearchResult(BaseModel):
    """Single search result."""
    document_id: int
    title: str
    content: str
    score: float
    source: str


class DocumentSearchResponse(BaseModel):
    """Response from document search."""
    query: str
    results: List[DocumentSearchResult]
    total: int


class URLProcessRequest(BaseModel):
    """Request to process a URL."""
    url: HttpUrl


class DocumentListResponse(BaseModel):
    """Response from document listing."""
    documents: List[dict]
    total: int


class DocumentDetailResponse(BaseModel):
    """Detailed document response."""
    id: int
    title: str
    filename: Optional[str]
    source_type: str
    source_url: Optional[str]
    summary: Optional[str]
    key_points: List[str] = []
    full_text: Optional[str]
    page_count: Optional[int]
    word_count: Optional[int]
    status: str
    created_at: Optional[str]


# =============================================================================
# UPLOAD ENDPOINTS
# =============================================================================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
):
    """
    Upload and process a document.
    
    Supports:
    - PDF documents
    - Word documents (DOCX)
    - Plain text files
    - Images (with OCR)
    
    The document will be:
    1. Text extracted using Azure Document Intelligence
    2. Summarized and key points extracted with Claude
    3. Chunked and embedded for semantic search
    4. Saved to memory for persistent recall
    
    Returns processing results including summary and key points.
    """
    user_id = get_current_user_id(request)
    tiger_user_id = get_current_tiger_user_id(request)
    
    if not user_id or tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    # Read file content
    content = await file.read()
    
    # Validate size (50MB max)
    max_size = 50 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 50MB"
        )
    
    logger.info(
        f"[DOCUMENTS] Upload: {file.filename} ({len(content)} bytes) "
        f"for user {tiger_user_id}"
    )
    
    try:
        result = await document_service.process_document(
            user_id=str(user_id),
            tiger_user_id=tiger_user_id,
            content=content,
            filename=title or file.filename,
            content_type=file.content_type or "application/octet-stream",
            source_type="upload",
        )
        
        if result.get("status") == "failed":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Document processing failed")
            )
        
        return DocumentUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DOCUMENTS] Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Document upload failed")


@router.post("/url", response_model=DocumentUploadResponse)
async def process_url(
    request: Request,
    body: URLProcessRequest,
):
    """
    Process a URL and extract its content.
    
    Fetches the web page, extracts text content, and processes it
    the same way as an uploaded document.
    
    Great for:
    - Articles you want Nicole to remember
    - Documentation pages
    - Research materials
    """
    user_id = get_current_user_id(request)
    tiger_user_id = get_current_tiger_user_id(request)
    
    if not user_id or tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    url = str(body.url)
    
    logger.info(
        f"[DOCUMENTS] URL: {url[:50]}... for user {tiger_user_id}"
    )
    
    try:
        result = await document_service.process_url(
            user_id=str(user_id),
            url=url,
            tiger_user_id=tiger_user_id,
        )
        
        if result.get("status") == "failed":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "URL processing failed")
            )
        
        return DocumentUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DOCUMENTS] URL processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="URL processing failed")


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: Request,
    body: DocumentSearchRequest,
):
    """
    Search across all your documents.
    
    Uses semantic search to find the most relevant document chunks
    based on your query. Great for questions like:
    - "What did that contract say about payment terms?"
    - "Find information about the project timeline"
    - "What were the key recommendations?"
    """
    tiger_user_id = get_current_tiger_user_id(request)
    
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        results = await document_service.search_documents(
            user_id=tiger_user_id,
            query=body.query,
            limit=body.limit,
        )
        
        search_results = [
            DocumentSearchResult(
                document_id=r["document_id"],
                title=r.get("title", "Untitled"),
                content=r.get("content", "")[:500],  # Truncate content
                score=r.get("score", 0),
                source=r.get("source", "unknown"),
            )
            for r in results
        ]
        
        return DocumentSearchResponse(
            query=body.query,
            results=search_results,
            total=len(search_results),
        )
        
    except Exception as e:
        logger.error(f"[DOCUMENTS] Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


# =============================================================================
# LIST/GET ENDPOINTS
# =============================================================================

@router.get("/list", response_model=DocumentListResponse)
async def list_documents(
    request: Request,
    limit: int = 50,
    offset: int = 0,
):
    """
    List all your uploaded documents.
    
    Returns document metadata including title, summary, and status.
    Most recent documents first.
    """
    tiger_user_id = get_current_tiger_user_id(request)
    
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        documents = await document_service.list_documents(
            user_id=tiger_user_id,
            limit=limit,
            offset=offset,
        )
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents),
        )
        
    except Exception as e:
        logger.error(f"[DOCUMENTS] List failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    request: Request,
    document_id: int,
):
    """
    Get detailed information about a specific document.
    
    Returns full metadata including summary, key points, and optionally
    the extracted text.
    """
    tiger_user_id = get_current_tiger_user_id(request)
    
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        document = await document_service.get_document(
            user_id=tiger_user_id,
            document_id=document_id,
        )
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentDetailResponse(
            id=document["doc_id"],
            title=document.get("title", "Untitled"),
            filename=document.get("file_name"),
            source_type=document.get("upload_source", "upload"),
            source_url=document.get("source_url"),
            summary=document.get("summary"),
            key_points=document.get("key_points", []),
            full_text=document.get("full_text"),
            page_count=document.get("page_count"),
            word_count=document.get("word_count"),
            status="completed",
            created_at=document["created_at"].isoformat() if document.get("created_at") else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DOCUMENTS] Get document failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get document")


# =============================================================================
# DELETE ENDPOINT (Tiger Native)
# =============================================================================

@router.delete("/{document_id}")
async def delete_document(
    request: Request,
    document_id: int,
):
    """
    Delete a document and all its chunks.
    
    This will remove the document from the database and vector store.
    Memories created from the document will remain.
    """
    tiger_user_id = get_current_tiger_user_id(request)
    
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Verify ownership
        doc_row = await db.fetchrow(
            """
            SELECT doc_id FROM document_repository
            WHERE doc_id = $1 AND user_id = $2
            """,
            document_id,
            tiger_user_id,
        )
        
        if not doc_row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete chunks first (foreign key)
        await db.execute(
            "DELETE FROM document_chunks WHERE doc_id = $1",
            document_id,
        )
        
        # Delete document
        await db.execute(
            "DELETE FROM document_repository WHERE doc_id = $1",
            document_id,
        )
        
        logger.info(f"[DOCUMENTS] Deleted {document_id} for user {tiger_user_id}")
        
        return {"success": True, "message": "Document deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DOCUMENTS] Delete failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document")

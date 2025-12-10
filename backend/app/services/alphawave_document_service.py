"""
Nicole V7 Document Intelligence Service - Tiger Native

Production-grade document processing with:
- Azure Document Intelligence for text extraction
- Intelligent chunking for semantic search
- Vector embeddings stored in Tiger (pgvectorscale)
- Memory integration for persistent recall
- Link/URL processing
- Multi-format support (PDF, DOCX, images, web pages)

Architecture:
1. Extract → Azure Document Intelligence / Claude Vision
2. Chunk → Intelligent text splitting with overlap
3. Embed → OpenAI embeddings to Tiger Postgres
4. Remember → Create memories for key facts
5. Retrieve → Semantic search via pgvectorscale
"""

import asyncio
import base64
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from uuid import uuid4

import httpx

from app.config import settings
from app.database import db
from app.integrations.alphawave_openai import openai_client
from app.integrations.alphawave_claude import claude_client
from app.services.alphawave_memory_service import memory_service

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Chunk configuration
CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 200  # Overlap between chunks for context
MAX_CHUNKS_PER_DOCUMENT = 500  # Limit for very large documents

# Supported file types
SUPPORTED_DOCUMENT_TYPES = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/html": "html",
}

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


# =============================================================================
# DOCUMENT INTELLIGENCE SERVICE
# =============================================================================

class AlphawaveDocumentService:
    """
    Production-grade document intelligence service.
    
    Handles the complete pipeline from upload to searchable memory:
    - Text extraction (Azure Document Intelligence)
    - Content analysis (Claude)
    - Chunking and embedding
    - Memory integration
    - Semantic retrieval
    
    All data stored in Tiger Postgres with pgvectorscale.
    """
    
    def __init__(self):
        """Initialize document service."""
        self._azure_doc_available = bool(
            settings.AZURE_DOCUMENT_ENDPOINT and settings.AZURE_DOCUMENT_KEY
        )
        self._azure_vision_available = bool(
            getattr(settings, "AZURE_VISION_ENDPOINT", None) and 
            getattr(settings, "AZURE_VISION_KEY", None)
        )
        
        logger.info(
            f"[DOCUMENT] Service initialized. "
            f"Azure Doc: {self._azure_doc_available}, "
            f"Azure Vision: {self._azure_vision_available}"
        )
    
    # =========================================================================
    # MAIN PROCESSING PIPELINE
    # =========================================================================
    
    async def process_document(
        self,
        user_id: Any,
        content: bytes,
        filename: str,
        content_type: str,
        source_type: str = "upload",
        source_url: Optional[str] = None,
        conversation_id: Optional[str] = None,
        tiger_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process a document through the complete intelligence pipeline.
        
        Pipeline:
        1. Create document record in Tiger
        2. Extract text (Azure/Claude)
        3. Generate summary and key points
        4. Chunk and embed (stored in Tiger)
        5. Create memories
        
        Args:
            user_id: User identifier (Supabase UUID or Tiger ID)
            content: Raw file bytes
            filename: Original filename
            content_type: MIME type
            source_type: 'upload', 'url', or 'paste'
            source_url: Original URL if from web
            conversation_id: Associated conversation
            tiger_user_id: Tiger database user ID
            
        Returns:
            Document processing result with summary and status
        """
        # Resolve Tiger user ID
        effective_user_id = tiger_user_id
        if effective_user_id is None:
            try:
                effective_user_id = int(str(user_id).split('-')[0]) if '-' in str(user_id) else int(user_id)
            except (ValueError, TypeError):
                effective_user_id = 1  # Default user
        
        logger.info(
            f"[DOCUMENT] Processing: {filename} ({content_type}) "
            f"for user {effective_user_id}"
        )
        
        # Create document record
        title = self._generate_title(filename)
        
        try:
            # Insert into uploaded_files (Tiger schema)
            storage_path = f"documents/{effective_user_id}/{filename}"
            file_row = await db.fetchrow(
                """
                INSERT INTO uploaded_files (
                    user_id, filename, original_filename, file_type, file_size, 
                    storage_url, processing_status, metadata, uploaded_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                RETURNING file_id
                """,
                effective_user_id,
                filename,
                filename,  # original_filename
                content_type,
                len(content),
                storage_path,  # storage_url
                'processing',  # processing_status
                {'source_type': source_type, 'source_url': source_url},  # metadata
            )
            file_id = file_row["file_id"]
            
            # Insert into document_repository (Tiger schema)
            doc_row = await db.fetchrow(
                """
                INSERT INTO document_repository (
                    user_id, file_id, title, document_type, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, NOW(), NOW())
                RETURNING document_id
                """,
                effective_user_id,
                file_id,
                title,
                content_type.split("/")[-1],
            )
            document_id = doc_row["document_id"]
            
            logger.info(f"[DOCUMENT] Created record: document_id={document_id}, file_id={file_id}")
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Failed to create record: {e}")
            return {"error": str(e), "status": "failed"}
        
        try:
            # Step 1: Extract text
            if content_type in SUPPORTED_IMAGE_TYPES:
                extracted = await self._extract_from_image(content, content_type)
            elif content_type in SUPPORTED_DOCUMENT_TYPES:
                extracted = await self._extract_from_document(content, content_type)
            else:
                extracted = {"text": "", "error": f"Unsupported type: {content_type}"}
            
            full_text = extracted.get("text", "")
            page_count = extracted.get("page_count", 1)
            
            if not full_text:
                raise ValueError(extracted.get("error", "No text extracted"))
            
            logger.info(f"[DOCUMENT] Extracted {len(full_text)} chars, {page_count} pages")
            
            # Step 2: Generate summary and key points
            analysis = await self._analyze_document(full_text, title)
            summary = analysis.get("summary", "")
            key_points = analysis.get("key_points", [])
            
            logger.info(f"[DOCUMENT] Analysis complete: {len(key_points)} key points")
            
            # Step 3: Chunk and embed
            chunks = self._create_chunks(full_text, title)
            chunk_count = await self._embed_and_store_chunks(
                chunks, document_id, effective_user_id, title
            )
            
            logger.info(f"[DOCUMENT] Created {chunk_count} embedded chunks")
            
            # Step 4: Create memories for key facts
            memories_created = await self._create_document_memories(
                effective_user_id, title, summary, key_points, document_id
            )
            
            logger.info(f"[DOCUMENT] Created {memories_created} memories")
            
            # Update document record with results
            await db.execute(
                """
                UPDATE document_repository
                SET summary = $1, updated_at = NOW()
                WHERE document_id = $2
                """,
                summary,
                document_id,
            )
            
            # Update uploaded_files status
            await db.execute(
                """
                UPDATE uploaded_files
                SET processing_status = $1, processed_at = NOW()
                WHERE file_id = $2
                """,
                'completed',
                file_id,
            )
            
            return {
                "document_id": document_id,
                "file_id": file_id,
                "title": title,
                "summary": summary,
                "key_points": key_points,
                "page_count": page_count,
                "word_count": len(full_text.split()),
                "chunks_created": chunk_count,
                "memories_created": memories_created,
                "status": "completed",
            }
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Processing failed: {e}", exc_info=True)
            return {
                "document_id": document_id if 'document_id' in locals() else None,
                "error": str(e),
                "status": "failed",
            }
    
    async def process_url(
        self,
        user_id: str,
        url: str,
        conversation_id: Optional[str] = None,
        tiger_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process a URL/link by fetching and extracting content.
        
        Args:
            user_id: User UUID string
            url: URL to process
            conversation_id: Associated conversation
            tiger_user_id: Tiger database user ID
            
        Returns:
            Processing result with extracted content
        """
        logger.info(f"[DOCUMENT] Processing URL: {url[:50]}...")
        
        try:
            # Fetch URL content
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0
            ) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; NicoleBot/1.0)"},
                )
                response.raise_for_status()
                content = response.content
                content_type = response.headers.get("content-type", "text/html").split(";")[0]
            
            # Generate filename from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            filename = parsed.path.split("/")[-1] or parsed.netloc
            if not filename.endswith((".html", ".htm", ".pdf")):
                filename += ".html"
            
            # Process as document
            return await self.process_document(
                user_id=user_id,
                content=content,
                filename=filename,
                content_type=content_type,
                source_type="url",
                source_url=url,
                conversation_id=conversation_id,
                tiger_user_id=tiger_user_id,
            )
            
        except Exception as e:
            logger.error(f"[DOCUMENT] URL processing failed: {e}")
            return {"error": str(e), "status": "failed", "url": url}
    
    # =========================================================================
    # TEXT EXTRACTION
    # =========================================================================
    
    async def _extract_from_document(
        self,
        content: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """Extract text from document using Azure Document Intelligence."""
        
        # Try Azure Document Intelligence
        if self._azure_doc_available:
            try:
                return await self._azure_document_extract(content)
            except Exception as e:
                logger.warning(f"[DOCUMENT] Azure failed, using fallback: {e}")
        
        # Fallback for plain text
        if content_type in ("text/plain", "text/markdown"):
            text = content.decode("utf-8", errors="replace")
            return {"text": text, "page_count": 1}
        
        # Fallback for HTML
        if content_type == "text/html":
            return self._extract_from_html(content)
        
        return {"text": "", "error": "Document extraction not available"}
    
    async def _azure_document_extract(self, content: bytes) -> Dict[str, Any]:
        """Extract text using Azure Document Intelligence API."""
        
        async with httpx.AsyncClient() as client:
            # Start analysis job
            response = await client.post(
                f"{settings.AZURE_DOCUMENT_ENDPOINT}/formrecognizer/documentModels/prebuilt-read:analyze",
                params={"api-version": "2023-07-31"},
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_DOCUMENT_KEY,
                    "Content-Type": "application/octet-stream",
                },
                content=content,
                timeout=60.0,
            )
            response.raise_for_status()
            
            # Get operation URL
            operation_url = response.headers.get("Operation-Location")
            if not operation_url:
                raise ValueError("No operation URL returned from Azure")
            
            # Poll for completion
            for attempt in range(60):
                await asyncio.sleep(2)
                
                result_response = await client.get(
                    operation_url,
                    headers={"Ocp-Apim-Subscription-Key": settings.AZURE_DOCUMENT_KEY},
                    timeout=30.0,
                )
                result = result_response.json()
                
                status = result.get("status")
                if status == "succeeded":
                    analyze_result = result.get("analyzeResult", {})
                    return {
                        "text": analyze_result.get("content", ""),
                        "page_count": len(analyze_result.get("pages", [])),
                    }
                elif status == "failed":
                    error = result.get("error", {})
                    raise ValueError(f"Azure analysis failed: {error}")
            
            raise TimeoutError("Azure document analysis timed out")
    
    async def _extract_from_image(
        self,
        content: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """Extract text and description from image."""
        
        # Try Azure Vision for OCR
        if self._azure_vision_available:
            try:
                return await self._azure_vision_extract(content)
            except Exception as e:
                logger.warning(f"[DOCUMENT] Azure Vision failed: {e}")
        
        # Fallback to Claude Vision
        return await self._claude_vision_extract(content, content_type)
    
    async def _azure_vision_extract(self, content: bytes) -> Dict[str, Any]:
        """Extract text from image using Azure Computer Vision."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AZURE_VISION_ENDPOINT}/vision/v3.2/read/analyze",
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_VISION_KEY,
                    "Content-Type": "application/octet-stream",
                },
                content=content,
                timeout=30.0,
            )
            response.raise_for_status()
            
            operation_url = response.headers.get("Operation-Location")
            if not operation_url:
                raise ValueError("No operation URL from Azure Vision")
            
            for _ in range(30):
                await asyncio.sleep(1)
                
                result_response = await client.get(
                    operation_url,
                    headers={"Ocp-Apim-Subscription-Key": settings.AZURE_VISION_KEY},
                )
                result = result_response.json()
                
                if result.get("status") == "succeeded":
                    lines = []
                    for page in result.get("analyzeResult", {}).get("readResults", []):
                        for line in page.get("lines", []):
                            lines.append(line.get("text", ""))
                    
                    return {"text": "\n".join(lines), "page_count": 1}
                elif result.get("status") == "failed":
                    raise ValueError("Azure Vision OCR failed")
            
            raise TimeoutError("Azure Vision OCR timed out")
    
    async def _claude_vision_extract(
        self,
        content: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """Extract text and description using Claude Vision."""
        
        image_b64 = base64.b64encode(content).decode("utf-8")
        
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content_type,
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": """Analyze this image and extract:
1. ALL visible text (transcribe exactly)
2. A brief description of the image content

Format:
TEXT: [all visible text]
DESCRIPTION: [brief description]""",
                },
            ],
        }]
        
        try:
            response = await claude_client.generate_response(
                messages=messages,
                max_tokens=2000,
                temperature=0.2,
            )
            
            text = ""
            description = ""
            
            if response:
                if "TEXT:" in response:
                    text_start = response.find("TEXT:") + 5
                    text_end = response.find("DESCRIPTION:")
                    if text_end == -1:
                        text_end = len(response)
                    text = response[text_start:text_end].strip()
                
                if "DESCRIPTION:" in response:
                    desc_start = response.find("DESCRIPTION:") + 12
                    description = response[desc_start:].strip()
            
            full_text = f"{text}\n\n[Image: {description}]" if description else text
            
            return {"text": full_text, "page_count": 1, "description": description}
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Claude Vision failed: {e}")
            return {"text": "", "error": str(e)}
    
    def _extract_from_html(self, content: bytes) -> Dict[str, Any]:
        """Extract text from HTML content."""
        
        try:
            html = content.decode("utf-8", errors="replace")
            
            # Remove script and style elements
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return {"text": text, "page_count": 1}
            
        except Exception as e:
            logger.error(f"[DOCUMENT] HTML extraction failed: {e}")
            return {"text": "", "error": str(e)}
    
    # =========================================================================
    # DOCUMENT ANALYSIS
    # =========================================================================
    
    async def _analyze_document(self, text: str, title: str) -> Dict[str, Any]:
        """Generate summary and key points using Claude."""
        
        analysis_text = text[:15000] if len(text) > 15000 else text
        
        prompt = f"""Analyze this document titled "{title}":

{analysis_text}

Provide:
1. SUMMARY: 2-4 sentence summary
2. KEY_POINTS: 3-7 bullet points of important information

Format:
SUMMARY: [your summary]

KEY_POINTS:
- [point 1]
- [point 2]
..."""

        try:
            response = await claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3,
            )
            
            result = {"summary": "", "key_points": []}
            
            if response:
                if "SUMMARY:" in response:
                    start = response.find("SUMMARY:") + 8
                    end = response.find("KEY_POINTS:")
                    if end == -1:
                        end = len(response)
                    result["summary"] = response[start:end].strip()
                
                if "KEY_POINTS:" in response:
                    start = response.find("KEY_POINTS:") + 11
                    points_text = response[start:].strip()
                    points = [
                        p.strip().lstrip("- •")
                        for p in points_text.split("\n")
                        if p.strip() and p.strip().startswith(("-", "•"))
                    ]
                    result["key_points"] = points[:10]
            
            return result
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Analysis failed: {e}")
            return {
                "summary": text[:500] + "..." if len(text) > 500 else text,
                "key_points": [],
            }
    
    # =========================================================================
    # CHUNKING AND EMBEDDING (Tiger Native)
    # =========================================================================
    
    def _create_chunks(self, text: str, title: str) -> List[Dict[str, Any]]:
        """Split document into overlapping chunks for embedding."""
        
        if not text:
            return []
        
        chunks = []
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 1 > CHUNK_SIZE:
                if current_chunk:
                    chunks.append({
                        "index": chunk_index,
                        "content": current_chunk.strip(),
                        "title": title,
                    })
                    chunk_index += 1
                    
                    # Overlap
                    words = current_chunk.split()
                    overlap_words = words[-CHUNK_OVERLAP // 5:] if len(words) > CHUNK_OVERLAP // 5 else []
                    current_chunk = " ".join(overlap_words) + " " + para
                else:
                    current_chunk = para
            else:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para
            
            if chunk_index >= MAX_CHUNKS_PER_DOCUMENT:
                break
        
        if current_chunk.strip() and chunk_index < MAX_CHUNKS_PER_DOCUMENT:
            chunks.append({
                "index": chunk_index,
                "content": current_chunk.strip(),
                "title": title,
            })
        
        return chunks
    
    async def _embed_and_store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: int,
        user_id: int,
        title: str,
    ) -> int:
        """Create embeddings for chunks and store in Tiger."""
        
        if not chunks:
            return 0
        
        count = 0
        batch_size = 10
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            try:
                # Generate embeddings
                texts = [f"Document: {c['title']}\n\n{c['content']}" for c in batch]
                embeddings = await openai_client.generate_embeddings_batch(texts)
                
                # Store in Tiger (using correct Tiger schema column names)
                for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                    await db.execute(
                        """
                        INSERT INTO document_chunks (
                            document_id, user_id, chunk_index, chunk_text, embedding, created_at
                        ) VALUES ($1, $2, $3, $4, $5, NOW())
                        """,
                        document_id,
                        user_id,
                        chunk["index"],
                        chunk["content"],
                        embedding,
                    )
                    count += 1
                    
            except Exception as e:
                logger.error(f"[DOCUMENT] Embedding batch failed: {e}")
        
        return count
    
    # =========================================================================
    # MEMORY INTEGRATION
    # =========================================================================
    
    async def _create_document_memories(
        self,
        user_id: int,
        title: str,
        summary: str,
        key_points: List[str],
        document_id: int,
    ) -> int:
        """Create memories from document for persistent recall."""
        
        memories_created = 0
        
        try:
            # Memory for document summary
            if summary:
                await memory_service.save_memory(
                    user_id=user_id,
                    memory_type="fact",
                    content=f"Document '{title}': {summary}",
                    context=f"From document {document_id}",
                    importance=0.7,
                    source="system",
                )
                memories_created += 1
            
            # Memories for key points (max 5)
            for point in key_points[:5]:
                if point:
                    await memory_service.save_memory(
                        user_id=user_id,
                        memory_type="fact",
                        content=f"From '{title}': {point}",
                        context=f"Key point from document {document_id}",
                        importance=0.6,
                        source="system",
                    )
                    memories_created += 1
                    
        except Exception as e:
            logger.error(f"[DOCUMENT] Memory creation failed: {e}")
        
        return memories_created
    
    # =========================================================================
    # RETRIEVAL (Tiger Native)
    # =========================================================================
    
    async def search_documents(
        self,
        user_id: Any,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search user's documents using semantic search in Tiger.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Max results to return
            
        Returns:
            List of relevant document chunks with scores
        """
        # Resolve user ID
        try:
            user_id_int = int(str(user_id).split('-')[0]) if '-' in str(user_id) else int(user_id)
        except (ValueError, TypeError):
            return []
        
        results = []
        
        try:
            # Generate query embedding
            query_embedding = await openai_client.generate_embedding(query)
            # Format as string for PostgreSQL vector type
            embedding_str = f'[{",".join(map(str, query_embedding))}]'
            
            # Vector search in Tiger
            rows = await db.fetch(
                """
                SELECT 
                    dc.chunk_id,
                    dc.document_id,
                    dc.chunk_text,
                    dr.title,
                    1 - (dc.embedding <=> $1::vector) AS score
                FROM document_chunks dc
                JOIN document_repository dr ON dr.document_id = dc.document_id
                WHERE dr.user_id = $2
                  AND dc.embedding IS NOT NULL
                ORDER BY dc.embedding <=> $1::vector
                LIMIT $3
                """,
                embedding_str,
                user_id_int,
                limit,
            )
            
            for row in rows:
                if row["score"] > 0.3:  # Minimum relevance threshold
                    results.append({
                        "document_id": row["document_id"],
                        "chunk_id": row["chunk_id"],
                        "title": row["title"],
                        "content": row["chunk_text"],
                        "score": float(row["score"]),
                        "source": "vector",
                    })
                    
        except Exception as e:
            logger.error(f"[DOCUMENT] Vector search failed: {e}")
        
        # Fallback to text search if needed
        if len(results) < limit:
            try:
                text_rows = await db.fetch(
                    """
                    SELECT 
                        dr.document_id,
                        dr.title,
                        dr.summary AS content,
                        0.5 AS score
                    FROM document_repository dr
                    WHERE dr.user_id = $1
                      AND (
                          dr.title ILIKE '%' || $2 || '%'
                          OR dr.summary ILIKE '%' || $2 || '%'
                      )
                    LIMIT $3
                    """,
                    user_id_int,
                    query,
                    limit - len(results),
                )
                
                for row in text_rows:
                    if not any(r["document_id"] == row["document_id"] for r in results):
                        results.append({
                            "document_id": row["document_id"],
                            "title": row["title"],
                            "content": row["content"] or "",
                            "score": float(row["score"]),
                            "source": "fulltext",
                        })
                        
            except Exception as e:
                logger.debug(f"[DOCUMENT] Text search failed: {e}")
        
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]
    
    async def get_document(
        self,
        user_id: Any,
        document_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        
        try:
            user_id_int = int(str(user_id).split('-')[0]) if '-' in str(user_id) else int(user_id)
        except (ValueError, TypeError):
            return None
        
        try:
            row = await db.fetchrow(
                """
                SELECT dr.*, uf.filename, uf.file_type, uf.file_size
                FROM document_repository dr
                LEFT JOIN uploaded_files uf ON uf.file_id = dr.file_id
                WHERE dr.document_id = $1 AND dr.user_id = $2
                """,
                document_id,
                user_id_int,
            )
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Get document failed: {e}")
            return None
    
    async def list_documents(
        self,
        user_id: Any,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List user's documents."""
        
        try:
            user_id_int = int(str(user_id).split('-')[0]) if '-' in str(user_id) else int(user_id)
        except (ValueError, TypeError):
            return []
        
        try:
            rows = await db.fetch(
                """
                SELECT 
                    dr.document_id,
                    dr.title,
                    dr.document_type,
                    dr.summary,
                    dr.created_at,
                    uf.filename,
                    uf.file_size,
                    (SELECT COUNT(*) FROM document_chunks WHERE document_id = dr.document_id) as chunks_count
                FROM document_repository dr
                LEFT JOIN uploaded_files uf ON uf.file_id = dr.file_id
                WHERE dr.user_id = $1
                ORDER BY dr.created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id_int,
                limit,
                offset,
            )
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[DOCUMENT] List documents failed: {e}")
            return []
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _generate_title(self, filename: str) -> str:
        """Generate a readable title from filename."""
        
        title = filename.rsplit(".", 1)[0] if "." in filename else filename
        title = title.replace("_", " ").replace("-", " ")
        title = title.title()
        
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

document_service = AlphawaveDocumentService()

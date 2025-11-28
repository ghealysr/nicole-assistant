"""
Document Intelligence Service for Nicole V7.
Production-grade document processing with perfect recall.

Features:
- Azure Document Intelligence for text extraction
- Intelligent chunking for semantic search
- Vector embeddings for retrieval
- Memory integration for persistent recall
- Link/URL processing
- Multi-format support (PDF, DOCX, images, web pages)

Architecture:
1. Extract → Azure Document Intelligence / Claude Vision
2. Chunk → Intelligent text splitting with overlap
3. Embed → OpenAI embeddings to Qdrant
4. Remember → Create memories for key facts
5. Retrieve → Semantic search for questions
"""

import asyncio
import base64
import hashlib
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx

from app.config import settings
from app.database import get_supabase, get_qdrant
from app.integrations.alphawave_openai import openai_client
from app.integrations.alphawave_claude import claude_client
from app.services.alphawave_memory_service import MemoryService

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

# Qdrant collection for documents
DOCUMENT_COLLECTION = "nicole_documents"


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
    """
    
    def __init__(self):
        """Initialize document service."""
        self.memory_service = MemoryService()
        self._azure_doc_available = bool(
            settings.AZURE_DOCUMENT_ENDPOINT and settings.AZURE_DOCUMENT_KEY
        )
        self._azure_vision_available = bool(
            settings.AZURE_VISION_ENDPOINT and settings.AZURE_VISION_KEY
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
        user_id: str,
        content: bytes,
        filename: str,
        content_type: str,
        source_type: str = "upload",
        source_url: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a document through the complete intelligence pipeline.
        
        Pipeline:
        1. Create document record
        2. Extract text (Azure/Claude)
        3. Generate summary and key points
        4. Chunk and embed
        5. Create memories
        
        Args:
            user_id: User UUID string
            content: Raw file bytes
            filename: Original filename
            content_type: MIME type
            source_type: 'upload', 'url', or 'paste'
            source_url: Original URL if from web
            conversation_id: Associated conversation
            
        Returns:
            Document processing result with summary and status
        """
        logger.info(
            f"[DOCUMENT] Processing: {filename} ({content_type}) "
            f"for user {user_id[:8]}..."
        )
        
        supabase = get_supabase()
        if not supabase:
            return {"error": "Database unavailable", "status": "failed"}
        
        # Create document record
        doc_id = str(uuid4())
        title = self._generate_title(filename)
        
        try:
            # Insert initial record
            supabase.table("document_repository").insert({
                "id": doc_id,
                "user_id": user_id,
                "title": title,
                "filename": filename,
                "source_type": source_type,
                "source_url": source_url,
                "content_type": content_type,
                "file_size_bytes": len(content),
                "status": "processing",
                "conversation_id": conversation_id,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
            
            logger.info(f"[DOCUMENT] Created record: {doc_id}")
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Failed to create record: {e}")
            return {"error": str(e), "status": "failed"}
        
        try:
            # Step 0: Upload to Supabase Storage for persistence
            storage_path = await self._upload_to_storage(
                content, doc_id, filename, user_id
            )
            if storage_path:
                logger.info(f"[DOCUMENT] Stored at: {storage_path}")
            
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
            
            logger.info(
                f"[DOCUMENT] Extracted {len(full_text)} chars, "
                f"{page_count} pages"
            )
            
            # Step 2: Generate summary and key points
            analysis = await self._analyze_document(full_text, title)
            summary = analysis.get("summary", "")
            key_points = analysis.get("key_points", [])
            entities = analysis.get("entities", {})
            
            logger.info(
                f"[DOCUMENT] Analysis complete: "
                f"{len(key_points)} key points"
            )
            
            # Step 3: Chunk and embed
            chunks = self._create_chunks(full_text, title)
            chunk_ids = await self._embed_chunks(
                chunks, doc_id, user_id, title
            )
            
            logger.info(
                f"[DOCUMENT] Created {len(chunk_ids)} embeddings"
            )
            
            # Step 4: Save chunks to database
            await self._save_chunks(chunks, doc_id, user_id, chunk_ids)
            
            # Step 5: Create memories for key facts
            memories_created = await self._create_document_memories(
                user_id, title, summary, key_points, doc_id
            )
            
            logger.info(
                f"[DOCUMENT] Created {memories_created} memories"
            )
            
            # Update document record with results
            update_data = {
                "status": "completed",
                "full_text": full_text,
                "summary": summary,
                "key_points": key_points,
                "entities": entities,
                "page_count": page_count,
                "word_count": len(full_text.split()),
                "processed_at": datetime.utcnow().isoformat(),
            }
            if storage_path:
                update_data["storage_path"] = storage_path
            
            supabase.table("document_repository").update(update_data).eq("id", doc_id).execute()
            
            return {
                "document_id": doc_id,
                "title": title,
                "summary": summary,
                "key_points": key_points,
                "page_count": page_count,
                "word_count": len(full_text.split()),
                "chunks_created": len(chunk_ids),
                "memories_created": memories_created,
                "status": "completed",
            }
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Processing failed: {e}", exc_info=True)
            
            # Update status to failed
            supabase.table("document_repository").update({
                "status": "failed",
                "error_message": str(e),
            }).eq("id", doc_id).execute()
            
            return {
                "document_id": doc_id,
                "error": str(e),
                "status": "failed",
            }
    
    async def process_url(
        self,
        user_id: str,
        url: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a URL/link by fetching and extracting content.
        
        Args:
            user_id: User UUID string
            url: URL to process
            conversation_id: Associated conversation
            
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
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; NicoleBot/1.0)"
                    }
                )
                response.raise_for_status()
                content = response.content
                content_type = response.headers.get(
                    "content-type", "text/html"
                ).split(";")[0]
            
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
    
    async def _azure_document_extract(
        self,
        content: bytes,
    ) -> Dict[str, Any]:
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
            for attempt in range(60):  # Max 2 minutes
                await asyncio.sleep(2)
                
                result_response = await client.get(
                    operation_url,
                    headers={
                        "Ocp-Apim-Subscription-Key": settings.AZURE_DOCUMENT_KEY
                    },
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
                result = await self._azure_vision_extract(content)
                return result
            except Exception as e:
                logger.warning(f"[DOCUMENT] Azure Vision failed: {e}")
        
        # Fallback to Claude Vision
        return await self._claude_vision_extract(content, content_type)
    
    async def _azure_vision_extract(
        self,
        content: bytes,
    ) -> Dict[str, Any]:
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
            
            # Get operation URL
            operation_url = response.headers.get("Operation-Location")
            if not operation_url:
                raise ValueError("No operation URL from Azure Vision")
            
            # Poll for results
            for _ in range(30):
                await asyncio.sleep(1)
                
                result_response = await client.get(
                    operation_url,
                    headers={
                        "Ocp-Apim-Subscription-Key": settings.AZURE_VISION_KEY
                    },
                )
                result = result_response.json()
                
                if result.get("status") == "succeeded":
                    # Extract text from read result
                    lines = []
                    for page in result.get("analyzeResult", {}).get("readResults", []):
                        for line in page.get("lines", []):
                            lines.append(line.get("text", ""))
                    
                    return {
                        "text": "\n".join(lines),
                        "page_count": 1,
                    }
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
                    "text": """Please analyze this image and extract:
1. ALL visible text (transcribe exactly as shown)
2. A detailed description of the image content
3. Any key information or data visible

Format your response as:
TEXT:
[All visible text, preserving layout where possible]

DESCRIPTION:
[Detailed description]

KEY_INFO:
[Important facts or data from the image]""",
                },
            ],
        }]
        
        try:
            response = await claude_client.generate_response(
                messages=messages,
                max_tokens=2000,
                temperature=0.2,
            )
            
            # Parse response
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
                    desc_end = response.find("KEY_INFO:")
                    if desc_end == -1:
                        desc_end = len(response)
                    description = response[desc_start:desc_end].strip()
            
            # Combine text and description
            full_text = f"{text}\n\n[Image Description: {description}]" if description else text
            
            return {
                "text": full_text,
                "page_count": 1,
                "description": description,
            }
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Claude Vision failed: {e}")
            return {"text": "", "error": str(e)}
    
    def _extract_from_html(
        self,
        content: bytes,
    ) -> Dict[str, Any]:
        """Extract text from HTML content."""
        
        try:
            html = content.decode("utf-8", errors="replace")
            
            # Simple HTML text extraction
            # Remove script and style elements
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return {"text": text, "page_count": 1}
            
        except Exception as e:
            logger.error(f"[DOCUMENT] HTML extraction failed: {e}")
            return {"text": "", "error": str(e)}
    
    # =========================================================================
    # DOCUMENT ANALYSIS
    # =========================================================================
    
    async def _analyze_document(
        self,
        text: str,
        title: str,
    ) -> Dict[str, Any]:
        """
        Analyze document content to generate summary and key points.
        
        Uses Claude for intelligent extraction.
        """
        
        # Truncate for analysis if too long
        analysis_text = text[:15000] if len(text) > 15000 else text
        
        prompt = f"""Analyze the following document titled "{title}" and provide:

1. SUMMARY: A comprehensive 2-4 sentence summary capturing the main points
2. KEY_POINTS: 3-7 bullet points of the most important information
3. ENTITIES: Extract any important names, dates, numbers, or specific items mentioned

Document content:
---
{analysis_text}
---

Respond in this exact format:

SUMMARY:
[Your summary here]

KEY_POINTS:
- [Point 1]
- [Point 2]
- [Point 3]
...

ENTITIES:
- Names: [list of names]
- Dates: [list of dates]
- Numbers: [list of important numbers/amounts]
- Organizations: [list of organizations]
- Locations: [list of locations]"""

        try:
            response = await claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3,
            )
            
            # Parse response
            result = {
                "summary": "",
                "key_points": [],
                "entities": {},
            }
            
            if response:
                # Extract summary
                if "SUMMARY:" in response:
                    start = response.find("SUMMARY:") + 8
                    end = response.find("KEY_POINTS:")
                    if end == -1:
                        end = len(response)
                    result["summary"] = response[start:end].strip()
                
                # Extract key points
                if "KEY_POINTS:" in response:
                    start = response.find("KEY_POINTS:") + 11
                    end = response.find("ENTITIES:")
                    if end == -1:
                        end = len(response)
                    points_text = response[start:end].strip()
                    # Parse bullet points
                    points = [
                        p.strip().lstrip("- •")
                        for p in points_text.split("\n")
                        if p.strip() and p.strip().startswith(("-", "•"))
                    ]
                    result["key_points"] = points[:10]  # Max 10 points
                
                # Extract entities (simplified parsing)
                if "ENTITIES:" in response:
                    start = response.find("ENTITIES:") + 9
                    entities_text = response[start:].strip()
                    
                    # Parse each entity type
                    for entity_type in ["Names", "Dates", "Numbers", "Organizations", "Locations"]:
                        if f"{entity_type}:" in entities_text:
                            type_start = entities_text.find(f"{entity_type}:") + len(entity_type) + 1
                            type_end = entities_text.find("\n-", type_start)
                            if type_end == -1:
                                type_end = len(entities_text)
                            type_text = entities_text[type_start:type_end].strip()
                            # Split by comma and clean
                            items = [
                                item.strip()
                                for item in type_text.split(",")
                                if item.strip() and item.strip() not in ("none", "None", "N/A")
                            ]
                            if items:
                                result["entities"][entity_type.lower()] = items
            
            return result
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Analysis failed: {e}")
            # Return basic analysis
            return {
                "summary": text[:500] + "..." if len(text) > 500 else text,
                "key_points": [],
                "entities": {},
            }
    
    # =========================================================================
    # CHUNKING AND EMBEDDING
    # =========================================================================
    
    def _create_chunks(
        self,
        text: str,
        title: str,
    ) -> List[Dict[str, Any]]:
        """
        Split document into overlapping chunks for embedding.
        
        Uses intelligent splitting that respects sentence boundaries.
        """
        
        if not text:
            return []
        
        chunks = []
        
        # Split into paragraphs first
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) + 1 > CHUNK_SIZE:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append({
                        "index": chunk_index,
                        "content": current_chunk.strip(),
                        "title": title,
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    # Take last portion of current chunk
                    words = current_chunk.split()
                    overlap_words = words[-CHUNK_OVERLAP // 5:] if len(words) > CHUNK_OVERLAP // 5 else []
                    current_chunk = " ".join(overlap_words) + " " + para
                else:
                    current_chunk = para
            else:
                # Add paragraph to current chunk
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para
            
            # Check if we've hit max chunks
            if chunk_index >= MAX_CHUNKS_PER_DOCUMENT:
                break
        
        # Don't forget the last chunk
        if current_chunk.strip() and chunk_index < MAX_CHUNKS_PER_DOCUMENT:
            chunks.append({
                "index": chunk_index,
                "content": current_chunk.strip(),
                "title": title,
            })
        
        return chunks
    
    async def _embed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str,
        user_id: str,
        title: str,
    ) -> List[str]:
        """
        Create embeddings for chunks and store in Qdrant.
        
        Returns list of embedding IDs.
        """
        
        if not chunks:
            return []
        
        qdrant = get_qdrant()
        if not qdrant:
            logger.warning("[DOCUMENT] Qdrant not available, skipping embeddings")
            return []
        
        # Ensure collection exists
        try:
            await self._ensure_collection(qdrant)
        except Exception as e:
            logger.error(f"[DOCUMENT] Collection setup failed: {e}")
            return []
        
        chunk_ids = []
        
        # Process in batches
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            try:
                # Generate embeddings
                texts = [
                    f"Document: {c['title']}\n\n{c['content']}"
                    for c in batch
                ]
                
                embeddings = await openai_client.generate_embeddings_batch(texts)
                
                # Store in Qdrant
                from qdrant_client.models import PointStruct
                
                points = []
                for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                    point_id = str(uuid4())
                    chunk_ids.append(point_id)
                    
                    points.append(PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "document_id": doc_id,
                            "user_id": user_id,
                            "title": title,
                            "chunk_index": chunk["index"],
                            "content": chunk["content"],
                            "type": "document_chunk",
                        },
                    ))
                
                qdrant.upsert(
                    collection_name=DOCUMENT_COLLECTION,
                    points=points,
                )
                
            except Exception as e:
                logger.error(f"[DOCUMENT] Embedding batch failed: {e}")
        
        return chunk_ids
    
    async def _ensure_collection(self, qdrant) -> None:
        """Ensure Qdrant collection exists with correct schema."""
        
        try:
            qdrant.get_collection(DOCUMENT_COLLECTION)
        except Exception:
            # Collection doesn't exist, create it
            from qdrant_client.models import Distance, VectorParams
            
            qdrant.create_collection(
                collection_name=DOCUMENT_COLLECTION,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"[DOCUMENT] Created collection: {DOCUMENT_COLLECTION}")
    
    async def _save_chunks(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str,
        user_id: str,
        chunk_ids: List[str],
    ) -> None:
        """Save chunk records to database."""
        
        supabase = get_supabase()
        if not supabase or not chunks:
            return
        
        try:
            records = []
            for i, chunk in enumerate(chunks):
                embedding_id = chunk_ids[i] if i < len(chunk_ids) else None
                records.append({
                    "id": str(uuid4()),
                    "document_id": doc_id,
                    "user_id": user_id,
                    "chunk_index": chunk["index"],
                    "content": chunk["content"],
                    "token_count": len(chunk["content"].split()),
                    "embedding_id": embedding_id,
                    "created_at": datetime.utcnow().isoformat(),
                })
            
            # Insert in batches
            batch_size = 50
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                supabase.table("document_chunks").insert(batch).execute()
                
        except Exception as e:
            logger.error(f"[DOCUMENT] Failed to save chunks: {e}")
    
    # =========================================================================
    # MEMORY INTEGRATION
    # =========================================================================
    
    async def _create_document_memories(
        self,
        user_id: str,
        title: str,
        summary: str,
        key_points: List[str],
        doc_id: str,
    ) -> int:
        """
        Create memories from document for persistent recall.
        
        Creates:
        - One memory for the document summary
        - One memory for each key point (up to 5)
        """
        
        memories_created = 0
        
        try:
            # Memory for document summary
            if summary:
                await self.memory_service.save_memory(
                    user_id=user_id,
                    memory_type="fact",
                    content=f"Document '{title}': {summary}",
                    context=f"From document {doc_id}",
                    importance=0.7,
                )
                memories_created += 1
            
            # Memories for key points (max 5)
            for point in key_points[:5]:
                if point:
                    await self.memory_service.save_memory(
                        user_id=user_id,
                        memory_type="fact",
                        content=f"From '{title}': {point}",
                        context=f"Key point from document {doc_id}",
                        importance=0.6,
                    )
                    memories_created += 1
                    
        except Exception as e:
            logger.error(f"[DOCUMENT] Memory creation failed: {e}")
        
        return memories_created
    
    # =========================================================================
    # RETRIEVAL
    # =========================================================================
    
    async def search_documents(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search user's documents using semantic search.
        
        Args:
            user_id: User UUID string
            query: Search query
            limit: Max results to return
            
        Returns:
            List of relevant document chunks with scores
        """
        
        results = []
        
        # Try Qdrant semantic search
        qdrant = get_qdrant()
        if qdrant:
            try:
                # Generate query embedding
                query_embedding = await openai_client.generate_embedding(query)
                
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                
                search_results = qdrant.search(
                    collection_name=DOCUMENT_COLLECTION,
                    query_vector=query_embedding,
                    query_filter=Filter(
                        must=[
                            FieldCondition(
                                key="user_id",
                                match=MatchValue(value=user_id),
                            ),
                        ],
                    ),
                    limit=limit,
                    score_threshold=0.3,
                )
                
                for result in search_results:
                    results.append({
                        "document_id": result.payload.get("document_id"),
                        "title": result.payload.get("title"),
                        "content": result.payload.get("content"),
                        "score": result.score,
                        "source": "vector",
                    })
                    
            except Exception as e:
                logger.error(f"[DOCUMENT] Vector search failed: {e}")
        
        # Also try PostgreSQL full-text search
        supabase = get_supabase()
        if supabase and len(results) < limit:
            try:
                response = supabase.table("document_repository").select(
                    "id, title, summary, key_points"
                ).eq("user_id", user_id).textSearch(
                    "full_text", query
                ).limit(limit).execute()
                
                for doc in response.data or []:
                    # Avoid duplicates
                    if not any(r.get("document_id") == doc["id"] for r in results):
                        results.append({
                            "document_id": doc["id"],
                            "title": doc["title"],
                            "content": doc.get("summary", ""),
                            "score": 0.5,  # Lower score for text search
                            "source": "fulltext",
                        })
                        
            except Exception as e:
                logger.debug(f"[DOCUMENT] Full-text search failed: {e}")
        
        # Sort by score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return results[:limit]
    
    async def get_document(
        self,
        user_id: str,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table("document_repository").select(
                "*"
            ).eq("id", document_id).eq("user_id", user_id).single().execute()
            
            if response.data:
                # Update last accessed
                supabase.table("document_repository").update({
                    "last_accessed": datetime.utcnow().isoformat(),
                }).eq("id", document_id).execute()
                
            return response.data
            
        except Exception as e:
            logger.error(f"[DOCUMENT] Get document failed: {e}")
            return None
    
    async def list_documents(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List user's documents."""
        
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            response = supabase.table("document_repository").select(
                "id, title, filename, source_type, summary, status, "
                "page_count, word_count, created_at"
            ).eq("user_id", user_id).order(
                "created_at", desc=True
            ).range(offset, offset + limit - 1).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"[DOCUMENT] List documents failed: {e}")
            return []
    
    # =========================================================================
    # STORAGE
    # =========================================================================
    
    async def _upload_to_storage(
        self,
        content: bytes,
        doc_id: str,
        filename: str,
        user_id: str,
    ) -> Optional[str]:
        """
        Upload document to Supabase Storage for persistence.
        
        Args:
            content: File bytes
            doc_id: Document UUID
            filename: Original filename
            user_id: User UUID
            
        Returns:
            Storage path or None if upload failed
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            # Create storage path: documents/{user_id}/{doc_id}/{filename}
            storage_path = f"documents/{user_id}/{doc_id}/{filename}"
            
            # Get file extension for content type
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            content_type = {
                "pdf": "application/pdf",
                "doc": "application/msword",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "txt": "text/plain",
                "md": "text/markdown",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "gif": "image/gif",
                "webp": "image/webp",
            }.get(ext, "application/octet-stream")
            
            # Upload to Supabase Storage
            # Note: Requires 'documents' bucket to exist in Supabase
            result = supabase.storage.from_("documents").upload(
                path=storage_path,
                file=content,
                file_options={"content-type": content_type}
            )
            
            if hasattr(result, 'error') and result.error:
                logger.warning(f"[DOCUMENT] Storage upload failed: {result.error}")
                return None
            
            logger.info(f"[DOCUMENT] Uploaded to storage: {storage_path}")
            return storage_path
            
        except Exception as e:
            # Storage is optional - don't fail the whole process
            logger.warning(f"[DOCUMENT] Storage upload error (continuing): {e}")
            return None
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _generate_title(self, filename: str) -> str:
        """Generate a readable title from filename."""
        
        # Remove extension
        title = filename.rsplit(".", 1)[0] if "." in filename else filename
        
        # Replace underscores and dashes with spaces
        title = title.replace("_", " ").replace("-", " ")
        
        # Title case
        title = title.title()
        
        # Limit length
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

document_service = AlphawaveDocumentService()


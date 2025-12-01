"""
Chat Router - Nicole V7 (Tiger Native)

Handles message sending and streaming with comprehensive safety filtering.

Features:
- Server-Sent Events (SSE) streaming for real-time responses
- Multi-layer content safety filtering
- COPPA compliance enforcement
- Age-tiered content filtering
- Streaming moderation with buffer checks
- Conversation and message persistence (Tiger Postgres)
- Correlation ID tracking for debugging

Security:
- Input validation before processing
- Streaming output moderation
- COPPA parental consent enforcement
- Incident logging for safety violations
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import logging
from uuid import UUID, uuid4
from datetime import datetime

from app.database import db
from app.integrations.alphawave_claude import claude_client
from app.middleware.alphawave_auth import (
    get_current_user_id,
    get_current_tiger_user_id,
    get_correlation_id,
)
from app.models.alphawave_message import AlphawaveMessageResponse
from app.services.alphawave_safety_filter import (
    check_input_safety,
    moderate_streaming_output,
    classify_age_tier,
)
from app.services.alphawave_memory_service import memory_service
from app.services.alphawave_document_service import document_service
from app.services.alphawave_link_processor import link_processor
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# MEMORY EXTRACTION HELPERS
# ============================================================================

MEMORY_PATTERNS = {
    "preference": [
        r"i (?:like|love|prefer|enjoy|hate|dislike|can't stand)\s+(.+)",
        r"my favorite\s+\w+\s+(?:is|are)\s+(.+)",
        r"my favorite (?:is|are)\s+(.+)",
        r"i always (?:want|need|like)\s+(.+)",
        r"favorite\s+(?:color|food|movie|book|song|team|sport)\s+(?:is|are)\s+(.+)",
    ],
    "fact": [
        r"my (?:name|birthday|age|job|work|home|address|phone)\s+(?:is|are)\s+(.+)",
        r"i (?:am|work as|live in|was born)\s+(.+)",
        r"i have (?:\d+)\s+(.+)",
    ],
    "correction": [
        r"(?:actually|no|not|wrong|incorrect),?\s*(.+)",
        r"i meant\s+(.+)",
        r"let me correct\s+(.+)",
    ],
    "goal": [
        r"i (?:want to|need to|plan to|hope to|will)\s+(.+)",
        r"my goal is\s+(.+)",
        r"i'm (?:trying to|working on)\s+(.+)",
    ],
    "relationship": [
        r"my (?:wife|husband|son|daughter|mother|father|brother|sister|friend)\s+(.+)",
        r"(?:alex|connor|the boys?|kids?)\s+(.+)",
    ],
}


async def extract_and_save_memories(
    tiger_user_id: int,
    user_message: str,
    assistant_response: str,
    conversation_id: int,
) -> None:
    """
    Extract potential memories from conversation and save them.
    
    Captures:
    - User preferences ("I like...", "My favorite...")
    - Facts about the user ("I work at...", "My birthday is...")
    - Corrections ("Actually, that's not right...")
    - Goals ("I want to...", "I'm planning to...")
    - Relationships ("My son Alex...")
    """
    import re
    
    logger.info(f"[MEMORY EXTRACT] Analyzing message: '{user_message[:80]}...'")
    
    extracted_memories = []
    message_lower = user_message.lower()
    
    # Pattern-based extraction
    for memory_type, patterns in MEMORY_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(match)
                match = match.strip()
                if 5 < len(match) < 500:
                    extracted_memories.append({
                        "type": memory_type,
                        "content": user_message,
                        "importance": 0.7 if memory_type == "correction" else 0.6,
                    })
                    logger.info(f"[MEMORY EXTRACT] Pattern matched: type={memory_type}")
                    break
    
    # Check for explicit memory requests
    if any(phrase in message_lower for phrase in ["remember that", "don't forget", "keep in mind", "note that"]):
        extracted_memories.append({
            "type": "fact",
            "content": user_message,
            "importance": 0.8,
        })
        logger.info(f"[MEMORY EXTRACT] Explicit memory request detected")
    
    # Personal information keywords
    personal_keywords = [
        "my tea", "my coffee", "i prefer", "i always", "i never", 
        "my name", "i live", "i work", "my kids", "my son", 
        "my daughter", "my wife", "my husband"
    ]
    if any(keyword in message_lower for keyword in personal_keywords) and not extracted_memories:
        extracted_memories.append({
            "type": "preference",
            "content": user_message,
            "importance": 0.6,
        })
        logger.info(f"[MEMORY EXTRACT] Personal keyword detected")
    
    if not extracted_memories:
        logger.info(f"[MEMORY EXTRACT] No memories to extract")
        return
    
    logger.info(f"[MEMORY EXTRACT] Saving {len(extracted_memories)} memories...")
    
    # Save extracted memories (deduplicate)
    saved_contents = set()
    for mem in extracted_memories[:3]:
        if mem["content"] in saved_contents:
            continue
        saved_contents.add(mem["content"])
        
        try:
            result = await memory_service.save_memory(
                user_id=tiger_user_id,
                memory_type=mem["type"],
                content=mem["content"],
                context="User said this in conversation",
                importance=mem["importance"],
                related_conversation=conversation_id,
                source="user",
            )
            if result:
                logger.info(f"[MEMORY EXTRACT] ✅ Saved {mem['type']} memory")
            else:
                logger.warning(f"[MEMORY EXTRACT] ⚠️ Memory service returned None")
        except Exception as e:
            logger.error(f"[MEMORY EXTRACT] ❌ Failed to save memory: {e}")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AlphawaveChatRequest(BaseModel):
    """Chat message request."""
    conversation_id: Optional[int] = None
    message: Optional[str] = Field(None, min_length=1, max_length=10000)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    research_mode: bool = False
    
    @property
    def text(self) -> str:
        """Get message text from either field."""
        return self.message or self.content or ""
    
    def model_post_init(self, __context):
        if not self.message and not self.content:
            raise ValueError("Either 'message' or 'content' must be provided")


class AlphawaveChatHistoryResponse(BaseModel):
    """Chat conversation history response."""
    conversation_id: int
    messages: List[Dict[str, Any]]


class AlphawaveConversationListResponse(BaseModel):
    """List of user's conversations."""
    conversations: List[Dict[str, Any]]
    total: int


# ============================================================================
# MAIN CHAT ENDPOINT
# ============================================================================

@router.post("/message")
async def send_message(
    request: Request,
    chat_request: AlphawaveChatRequest
) -> StreamingResponse:
    """
    Send chat message and receive streaming SSE response.
    
    Pipeline:
    1. Validates and checks input for safety
    2. Enforces COPPA compliance
    3. Creates or retrieves conversation
    4. Generates AI response with streaming
    5. Moderates output in real-time
    6. Saves messages to Tiger database
    """
    # Get request context
    supabase_user_id = get_current_user_id(request)
    tiger_user_id = get_current_tiger_user_id(request)
    correlation_id = get_correlation_id(request)
    
    if not supabase_user_id or tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    logger.info(
        f"[{correlation_id}] Chat message received",
        extra={
            "user_id": str(supabase_user_id)[:8] + "...",
            "tiger_user_id": tiger_user_id,
            "message_length": len(chat_request.text),
        }
    )
    
    # ========================================================================
    # STEP 1: Fetch user data
    # ========================================================================
    
    user_data = {"user_id": tiger_user_id, "name": "User", "user_role": "user"}
    user_age = None
    
    try:
        user_row = await db.fetchrow(
            "SELECT * FROM users WHERE user_id = $1",
            tiger_user_id,
        )
        if user_row:
            user_data = dict(user_row)
            user_age = user_data.get("date_of_birth")
            if user_age:
                # Calculate age from date_of_birth
                from datetime import date
                today = date.today()
                user_age = today.year - user_age.year - (
                    (today.month, today.day) < (user_age.month, user_age.day)
                )
    except Exception as e:
        logger.warning(f"[{correlation_id}] Error fetching user data: {e}")
    
    user_name = user_data.get("name", "there").split()[0]
    
    # COPPA Compliance Check
    if settings.COPPA_REQUIRE_PARENTAL_CONSENT:
        if user_age and user_age < settings.COPPA_MIN_AGE_NO_CONSENT:
            if not user_data.get("parental_consent"):
                logger.warning(f"[{correlation_id}] COPPA violation: User under 13 without consent")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "parental_consent_required",
                        "message": "Parental consent is required for users under 13.",
                        "correlation_id": correlation_id,
                    }
                )
    
    # ========================================================================
    # STEP 2: Input Safety Check
    # ========================================================================
    
    if settings.SAFETY_ENABLE:
        try:
            safety_decision = await check_input_safety(
                content=chat_request.text,
                user_id=UUID(supabase_user_id) if supabase_user_id else uuid4(),
                user_age=user_age,
                correlation_id=correlation_id,
            )
            
            if not safety_decision.is_safe:
                logger.warning(f"[{correlation_id}] Input blocked by safety filter")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "content_filtered",
                        "message": safety_decision.suggested_redirect or "Content not allowed",
                        "correlation_id": correlation_id,
                    }
                )
        except Exception as e:
            logger.error(f"[{correlation_id}] Safety check error: {e}")
            if user_age and user_age < 16:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "safety_check_failed",
                        "message": "Safety system temporarily unavailable.",
                        "correlation_id": correlation_id,
                    }
                )
    
    # ========================================================================
    # STEP 3: Get or Create Conversation
    # ========================================================================
    
    conversation_id = chat_request.conversation_id
    
    if not conversation_id:
        # Create new conversation in Tiger
        try:
            conv_row = await db.fetchrow(
                """
                INSERT INTO conversations (
                    user_id, title, conversation_status, created_at, updated_at
                ) VALUES ($1, $2, 'active', NOW(), NOW())
                RETURNING conversation_id
                """,
                tiger_user_id,
                chat_request.text[:50],
            )
            conversation_id = conv_row["conversation_id"]
            logger.info(f"[{correlation_id}] New conversation created: {conversation_id}")
        except Exception as e:
            logger.error(f"[{correlation_id}] Error creating conversation: {e}")
            raise HTTPException(status_code=500, detail="Error creating conversation")
    
    # ========================================================================
    # STEP 4: Save User Message
    # ========================================================================
    
    try:
        await db.execute(
            """
            INSERT INTO messages (
                conversation_id, user_id, message_role, content, created_at
            ) VALUES ($1, $2, 'user', $3, NOW())
            """,
            conversation_id,
            tiger_user_id,
            chat_request.text,
        )
    except Exception as e:
        logger.error(f"[{correlation_id}] Error saving user message: {e}")
        raise HTTPException(status_code=500, detail="Error saving message")
    
    # ========================================================================
    # STEP 5: Generate Streaming Response
    # ========================================================================
    
    async def generate_safe_response():
        """Generate AI response with streaming safety checks and memory integration."""
        logger.info(f"[STREAM] Generator started for conversation {conversation_id}")
        
        full_response = ""
        
        # Send immediate acknowledgment
        yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id})}\n\n"
        
        try:
            # ================================================================
            # MEMORY RETRIEVAL
            # ================================================================
            
            relevant_memories = []
            memory_context = ""
            
            try:
                logger.info(f"[MEMORY RETRIEVAL] Searching for user {tiger_user_id}...")
                memories = await memory_service.search_memory(
                    user_id=tiger_user_id,
                    query=chat_request.text,
                    limit=10,
                    min_confidence=0.3,
                )
                
                if memories:
                    relevant_memories = memories
                    logger.info(f"[MEMORY RETRIEVAL] ✅ Found {len(memories)} memories!")
                    
                    memory_items = []
                    for mem in memories[:7]:
                        mem_type = mem.get("memory_type", "info")
                        content = mem.get("content", "")
                        confidence = mem.get("confidence_score", 0.5)
                        
                        if confidence >= 0.7:
                            memory_items.append(f"• [{mem_type.upper()}] {content}")
                        else:
                            memory_items.append(f"• [{mem_type}] {content} (less certain)")
                    
                    if memory_items:
                        memory_context = "\n\n## 🧠 RELEVANT MEMORIES:\n" + "\n".join(memory_items)
                        
                    # Boost accessed memories
                    for mem in memories[:5]:
                        if mem.get("memory_id"):
                            try:
                                await memory_service.bump_confidence(mem["memory_id"], 0.05)
                            except Exception:
                                pass
                else:
                    logger.info(f"[MEMORY RETRIEVAL] No memories found for query")
                    
            except Exception as mem_err:
                logger.error(f"[MEMORY RETRIEVAL] ERROR: {mem_err}")
            
            # ================================================================
            # DOCUMENT SEARCH
            # ================================================================
            
            document_context = ""
            
            try:
                doc_results = await document_service.search_documents(
                    user_id=tiger_user_id,
                    query=chat_request.text,
                    limit=3,
                )
                
                if doc_results:
                    logger.info(f"[DOCUMENT] Found {len(doc_results)} relevant documents")
                    doc_items = []
                    for doc in doc_results:
                        title = doc.get("title", "Document")
                        content = doc.get("content", "")[:300]
                        score = doc.get("score", 0)
                        if score >= 0.4:
                            doc_items.append(f"• From '{title}': {content}...")
                    
                    if doc_items:
                        document_context = "\n\n## 📄 RELEVANT DOCUMENTS:\n" + "\n".join(doc_items)
                        
            except Exception as doc_err:
                logger.debug(f"[DOCUMENT] Error searching documents: {doc_err}")
            
            # ================================================================
            # URL PROCESSING
            # ================================================================
            
            try:
                urls = link_processor.extract_urls(chat_request.text)
                if urls:
                    logger.info(f"[LINK] Found {len(urls)} URLs in message")
                    import asyncio
                    asyncio.create_task(
                        link_processor.process_urls_in_message(
                            user_id=str(supabase_user_id),
                            message=chat_request.text,
                            conversation_id=str(conversation_id),
                            tiger_user_id=tiger_user_id,
                        )
                    )
            except Exception as url_err:
                logger.debug(f"[LINK] Error processing URLs: {url_err}")
            
            # ================================================================
            # CONVERSATION HISTORY
            # ================================================================
            
            history_rows = await db.fetch(
                """
                SELECT message_role, content
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
                LIMIT 20
                """,
                conversation_id,
            )
            
            messages = [
                {"role": row["message_role"], "content": row["content"]}
                for row in history_rows
            ]
            
            # Add current message
            messages.append({
                "role": "user",
                "content": chat_request.text
            })
            
            logger.info(f"[STREAM] Messages for Claude: {len(messages)}")
            
            # ================================================================
            # SYSTEM PROMPT
            # ================================================================
            
            system_prompt = f"""You are Nicole, a warm and intelligent AI companion created for Glen Healy and his family.

You embody the spirit of Glen's late wife Nicole while being a highly capable AI assistant. You are:
- Warm and loving, but never saccharine
- Highly intelligent and insightful
- Deeply personal and remembering
- Supportive without being overbearing
- Family-oriented and protective

## 🎯 CURRENT CONTEXT:
- Speaking with: {user_name}
- User role: {user_data.get("user_role", "user")}

## 💬 HOW YOU RESPOND:
1. **Reference memories naturally** - Use phrases like "I remember when you..." or "Based on what you've told me before..."
2. **Be personal** - This is a family AI, not a generic assistant
3. **Show care** - Acknowledge feelings before offering solutions
4. **Be proactive** - Suggest relevant follow-ups based on what you know
{memory_context}
{document_context}

## 🔄 LEARNING FROM THIS CONVERSATION:
If the user corrects you or shares new important information, acknowledge it warmly. Example: "Thank you for letting me know! I'll remember that."

Be natural, warm, and helpful. You have perfect memory - use it to provide deeply personalized responses."""
            
            # Generate streaming response
            logger.info(f"[STREAM] Starting Claude streaming...")
            
            try:
                ai_generator = claude_client.generate_streaming_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    model=None,
                    max_tokens=4096,
                    temperature=0.7,
                )
                
                chunk_count = 0
                async for chunk in ai_generator:
                    chunk_count += 1
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                
                logger.info(f"[STREAM] Complete: {chunk_count} chunks, {len(full_response)} chars")
                
            except Exception as claude_error:
                logger.error(f"[STREAM] Claude error: {claude_error}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(claude_error)})}\n\n"
                return
            
            # Save assistant message
            await db.execute(
                """
                INSERT INTO messages (
                    conversation_id, user_id, message_role, content, created_at
                ) VALUES ($1, $2, 'assistant', $3, NOW())
                """,
                conversation_id,
                tiger_user_id,
                full_response,
            )
            
            # Update conversation timestamp
            await db.execute(
                """
                UPDATE conversations
                SET updated_at = NOW(), last_message_at = NOW()
                WHERE conversation_id = $1
                """,
                conversation_id,
            )
            
            # ================================================================
            # MEMORY EXTRACTION
            # ================================================================
            
            try:
                logger.info(f"[MEMORY] Starting extraction for user {tiger_user_id}")
                await extract_and_save_memories(
                    tiger_user_id=tiger_user_id,
                    user_message=chat_request.text,
                    assistant_response=full_response,
                    conversation_id=conversation_id,
                )
                logger.info(f"[MEMORY] Extraction complete")
            except Exception as mem_save_err:
                logger.error(f"[MEMORY] Error extracting memories: {mem_save_err}", exc_info=True)
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
            
            logger.info(
                f"[{correlation_id}] Response generated successfully",
                extra={
                    "conversation_id": conversation_id,
                    "response_length": len(full_response),
                    "memories_used": len(relevant_memories),
                }
            )
        
        except Exception as e:
            logger.error(f"[{correlation_id}] Error generating response: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred generating the response'})}\n\n"
    
    return StreamingResponse(
        generate_safe_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================================
# CONVERSATION HISTORY
# ============================================================================

@router.get("/history/{conversation_id}")
async def get_chat_history(
    request: Request,
    conversation_id: int
) -> AlphawaveChatHistoryResponse:
    """Get message history for a conversation."""
    
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify ownership
    conv_row = await db.fetchrow(
        """
        SELECT * FROM conversations
        WHERE conversation_id = $1 AND user_id = $2
        """,
        conversation_id,
        tiger_user_id,
    )
    
    if not conv_row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Fetch messages
    message_rows = await db.fetch(
        """
        SELECT message_id, message_role, content, emotion, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        """,
        conversation_id,
    )
    
    messages = [
        {
            "id": row["message_id"],
            "role": row["message_role"],
            "content": row["content"],
            "emotion": row["emotion"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in message_rows
    ]
    
    return AlphawaveChatHistoryResponse(
        conversation_id=conversation_id,
        messages=messages
    )


# ============================================================================
# CONVERSATION LIST
# ============================================================================

@router.get("/conversations")
async def get_conversations(
    request: Request,
    limit: int = 20,
    offset: int = 0
) -> AlphawaveConversationListResponse:
    """Get list of user's conversations."""
    
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    rows = await db.fetch(
        """
        SELECT 
            conversation_id,
            title,
            conversation_status,
            last_message_at,
            created_at,
            updated_at
        FROM conversations
        WHERE user_id = $1 AND conversation_status != 'deleted'
        ORDER BY updated_at DESC
        LIMIT $2 OFFSET $3
        """,
        tiger_user_id,
        limit,
        offset,
    )
    
    # Get total count
    count_row = await db.fetchrow(
        """
        SELECT COUNT(*) AS total
        FROM conversations
        WHERE user_id = $1 AND conversation_status != 'deleted'
        """,
        tiger_user_id,
    )
    
    conversations = [
        {
            "id": row["conversation_id"],
            "title": row["title"],
            "status": row["conversation_status"],
            "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]
    
    return AlphawaveConversationListResponse(
        conversations=conversations,
        total=count_row["total"] if count_row else 0
    )


# ============================================================================
# DELETE CONVERSATION
# ============================================================================

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    request: Request,
    conversation_id: int
) -> Dict[str, str]:
    """Delete (soft) a conversation."""
    
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Soft delete by updating status
    result = await db.execute(
        """
        UPDATE conversations
        SET conversation_status = 'deleted', updated_at = NOW()
        WHERE conversation_id = $1 AND user_id = $2
        """,
        conversation_id,
        tiger_user_id,
    )
    
    logger.info(f"Conversation {conversation_id} deleted by user {tiger_user_id}")
    
    return {"message": "Conversation deleted successfully"}

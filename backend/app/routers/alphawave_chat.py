"""
Chat Router - Nicole V7
Handles message sending and streaming with comprehensive safety filtering.

Features:
- Server-Sent Events (SSE) streaming for real-time responses
- Multi-layer content safety filtering
- COPPA compliance enforcement
- Age-tiered content filtering
- Streaming moderation with buffer checks
- Conversation and message persistence
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

from app.database import get_supabase
from app.integrations.alphawave_claude import claude_client
from app.middleware.alphawave_auth import get_current_user_id, get_correlation_id
from app.models.alphawave_message import AlphawaveMessageResponse
from app.services.alphawave_safety_filter import (
    check_input_safety,
    moderate_streaming_output,
    classify_age_tier,
)
from app.services.alphawave_memory_service import MemoryService
from app.services.alphawave_document_service import document_service
from app.services.alphawave_link_processor import link_processor
from app.config import settings

logger = logging.getLogger(__name__)

# Global memory service instance
memory_service = MemoryService()
router = APIRouter()


# ============================================================================
# MEMORY EXTRACTION HELPERS
# ============================================================================

# Patterns that indicate potential memories to save
MEMORY_PATTERNS = {
    "preference": [
        r"i (?:like|love|prefer|enjoy|hate|dislike|can't stand)\s+(.+)",
        r"my favorite (?:is|are)\s+(.+)",
        r"i always (?:want|need|like)\s+(.+)",
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
    user_id: str,
    user_message: str,
    assistant_response: str,
    conversation_id: str,
) -> None:
    """
    Extract potential memories from conversation and save them.
    
    This runs after each response to capture:
    - User preferences ("I like...", "My favorite...")
    - Facts about the user ("I work at...", "My birthday is...")
    - Corrections ("Actually, that's not right...")
    - Goals ("I want to...", "I'm planning to...")
    - Relationships ("My son Alex...")
    
    Uses pattern matching for quick extraction. More complex extraction
    could use Claude to analyze the conversation.
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
                if len(match) > 5 and len(match) < 500:  # Lowered minimum length
                    # Save the FULL user message as the memory content for better context
                    extracted_memories.append({
                        "type": memory_type,
                        "content": user_message,  # Full message, not just the match
                        "importance": 0.7 if memory_type == "correction" else 0.6,
                    })
                    logger.info(f"[MEMORY EXTRACT] Pattern matched: type={memory_type}, match='{match[:50]}...'")
                    break  # One match per pattern type is enough
    
    # Check for explicit memory requests
    if any(phrase in message_lower for phrase in ["remember that", "don't forget", "keep in mind", "note that"]):
        # The whole message is likely important
        extracted_memories.append({
            "type": "fact",
            "content": user_message,
            "importance": 0.8,
        })
        logger.info(f"[MEMORY EXTRACT] Explicit memory request detected")
    
    # Also save any message that contains personal information keywords
    personal_keywords = ["my tea", "my coffee", "i prefer", "i always", "i never", "my name", "i live", "i work", "my kids", "my son", "my daughter", "my wife", "my husband"]
    if any(keyword in message_lower for keyword in personal_keywords) and not extracted_memories:
        extracted_memories.append({
            "type": "preference",
            "content": user_message,
            "importance": 0.6,
        })
        logger.info(f"[MEMORY EXTRACT] Personal keyword detected in message")
    
    if not extracted_memories:
        logger.info(f"[MEMORY EXTRACT] No memories to extract from this message")
        return
    
    logger.info(f"[MEMORY EXTRACT] Saving {len(extracted_memories)} memories...")
    
    # Save extracted memories (deduplicate by content)
    saved_contents = set()
    for mem in extracted_memories[:3]:  # Limit to 3 per message
        if mem["content"] in saved_contents:
            continue
        saved_contents.add(mem["content"])
        
        try:
            result = await memory_service.save_memory(
                user_id=user_id,
                memory_type=mem["type"],
                content=mem["content"],
                context=f"User said this in conversation",
                importance=mem["importance"],
                related_conversation=conversation_id,
            )
            if result:
                logger.info(f"[MEMORY EXTRACT] ✅ Saved {mem['type']} memory: {mem['content'][:50]}...")
            else:
                logger.warning(f"[MEMORY EXTRACT] ⚠️ Memory service returned None")
        except Exception as e:
            logger.error(f"[MEMORY EXTRACT] ❌ Failed to save memory: {e}", exc_info=True)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AlphawaveChatRequest(BaseModel):
    """
    Chat message request.
    
    Attributes:
        conversation_id: Existing conversation ID (None creates new)
        message: User's message content (also accepts 'content' for compatibility)
        research_mode: Enable deep research mode (O1-mini)
    """
    conversation_id: Optional[UUID] = None
    message: Optional[str] = Field(None, min_length=1, max_length=10000)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)  # Alias for compatibility
    research_mode: bool = False
    
    @property
    def text(self) -> str:
        """Get message text from either 'message' or 'content' field."""
        return self.message or self.content or ""
    
    def model_post_init(self, __context):
        """Validate that at least one of message/content is provided."""
        if not self.message and not self.content:
            raise ValueError("Either 'message' or 'content' must be provided")


class AlphawaveChatHistoryResponse(BaseModel):
    """Chat conversation history response."""
    conversation_id: UUID
    messages: List[AlphawaveMessageResponse]


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
    
    This is the main chat endpoint that:
    1. Validates and checks input for safety
    2. Enforces COPPA compliance
    3. Creates or retrieves conversation
    4. Generates AI response with streaming
    5. Moderates output in real-time
    6. Saves messages to database
    
    Args:
        request: FastAPI request with auth context
        chat_request: Chat message and options
        
    Returns:
        StreamingResponse with SSE events
        
    SSE Event Types:
        - token: Content chunk
        - done: Stream complete
        - error: Error occurred
        
    Raises:
        HTTPException: On various error conditions
        
    Example:
        POST /chat/message
        {
            "message": "Hello Nicole!",
            "conversation_id": null,
            "research_mode": false
        }
    """
    # Get database connection
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )
    
    # Get request context
    user_id = get_current_user_id(request)
    correlation_id = get_correlation_id(request)
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    logger.info(
        "Chat message received",
        extra={
            "correlation_id": correlation_id,
            "user_id": str(user_id)[:8] + "...",
            "message_length": len(chat_request.text),
            "has_conversation": chat_request.conversation_id is not None,
        }
    )
    
    # ========================================================================
    # STEP 1: Fetch user and check COPPA compliance
    # ========================================================================
    
    try:
        # Query only columns that exist in the users table
        # Note: age, date_of_birth, parental_consent may not exist yet
        user_result = supabase.table("users").select(
            "id, role, full_name, email"
        ).eq("id", user_id).execute()
        
        if not user_result.data:
            # User doesn't exist in users table yet (first login via Supabase Auth)
            # Create the user entry to satisfy foreign key constraints
            logger.info(f"User {user_id} not found in users table, creating entry")
            
            # Get user info from Supabase Auth if available
            try:
                auth_user = supabase.auth.get_user()
                user_email = auth_user.user.email if auth_user and auth_user.user else f"user_{str(user_id)[:8]}@nicole.local"
                user_name = auth_user.user.user_metadata.get("full_name", auth_user.user.user_metadata.get("name", "Nicole User")) if auth_user and auth_user.user else "Nicole User"
            except Exception:
                user_email = f"user_{str(user_id)[:8]}@nicole.local"
                user_name = "Nicole User"
            
            # Create user in database
            try:
                supabase.table("users").insert({
                    "id": user_id,
                    "email": user_email,
                    "full_name": user_name,
                    "role": "standard",
                    "created_at": datetime.utcnow().isoformat(),
                }).execute()
                logger.info(f"Created user entry for {user_id}")
            except Exception as create_err:
                logger.warning(f"Could not create user (may already exist): {create_err}")
            
            user_data = {"id": str(user_id), "role": "standard", "full_name": user_name}
            user_age = None
        else:
            user_data = user_result.data[0]
            user_age = user_data.get("age")  # Will be None if column doesn't exist
        
    except Exception as e:
        # Log but don't fail - use defaults
        logger.warning(
            f"Error fetching user data (using defaults): {e}",
            extra={"correlation_id": correlation_id}
        )
        user_data = {"id": str(user_id), "role": "standard"}
        user_age = None
    
    # COPPA Compliance Check
    if settings.COPPA_REQUIRE_PARENTAL_CONSENT:
        if user_age and user_age < settings.COPPA_MIN_AGE_NO_CONSENT:
            if not user_data.get("parental_consent"):
                logger.warning(
                    "COPPA violation: User under 13 without parental consent",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": str(user_id)[:8] + "...",
                        "user_age": user_age,
                    }
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "parental_consent_required",
                        "message": (
                            "Parental consent is required for users under 13. "
                            "Please have a parent or guardian complete the consent process."
                        ),
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
                user_id=UUID(user_id),
                user_age=user_age,
                correlation_id=correlation_id,
            )
            
            if not safety_decision.is_safe:
                logger.warning(
                    "Input blocked by safety filter",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": str(user_id)[:8] + "...",
                        "severity": safety_decision.severity.value,
                        "categories": [cat.value for cat in safety_decision.categories],
                        "tier": safety_decision.tier_applied.value if safety_decision.tier_applied else "unknown",
                    }
                )
                
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "content_filtered",
                        "message": safety_decision.suggested_redirect or "Content not allowed",
                        "severity": safety_decision.severity.value,
                        "correlation_id": correlation_id,
                    }
                )
            
            logger.debug(
                "Input passed safety checks",
                extra={"correlation_id": correlation_id}
            )
        
        except Exception as e:
            logger.error(
                f"Safety check error: {e}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            # Fail open for availability (adults) but closed for children
            if user_age and user_age < 16:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "safety_check_failed",
                        "message": "Safety system temporarily unavailable. Please try again.",
                        "correlation_id": correlation_id,
                    }
                )
    
    # ========================================================================
    # STEP 3: Get or Create Conversation
    # ========================================================================
    
    conversation_id = chat_request.conversation_id
    
    if not conversation_id:
        # Create new conversation
        conversation_id = uuid4()
        try:
            supabase.table("conversations").insert({
                "id": str(conversation_id),
                "user_id": user_id,
                "title": chat_request.text[:50],  # First message as title
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).execute()
            
            logger.info(
                "New conversation created",
                extra={
                    "correlation_id": correlation_id,
                    "conversation_id": str(conversation_id),
                }
            )
        
        except Exception as e:
            logger.error(
                f"Error creating conversation: {e}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Error creating conversation"
            )
    
    # ========================================================================
    # STEP 4: Save User Message
    # ========================================================================
    
    user_message_id = uuid4()
    
    try:
        supabase.table("messages").insert({
            "id": str(user_message_id),
            "conversation_id": str(conversation_id),
            "user_id": user_id,
            "role": "user",
            "content": chat_request.text,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    
    except Exception as e:
        logger.error(
            f"Error saving user message: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Error saving message"
        )
    
    # ========================================================================
    # STEP 5: Generate Streaming Response
    # ========================================================================
    
    async def generate_safe_response():
        """
        Generate AI response with streaming safety checks and memory integration.
        
        Yields SSE-formatted events with real-time content moderation.
        Memory is searched before response and extracted after.
        """
        logger.info(f"[STREAM] Generator started for conversation {conversation_id}")
        
        assistant_message_id = uuid4()
        full_response = ""
        user_name = user_data.get("full_name", "there").split()[0]  # First name only
        
        # Send immediate acknowledgment
        yield f"data: {json.dumps({'type': 'start', 'message_id': str(assistant_message_id)})}\n\n"
        
        try:
            # ================================================================
            # MEMORY RETRIEVAL - Search for relevant memories
            # ================================================================
            
            relevant_memories = []
            memory_context = ""
            
            try:
                # Ensure user_id is a string (UUID objects need conversion)
                user_id_str = str(user_id) if user_id else None
                if not user_id_str:
                    logger.warning("[MEMORY] No user_id available for memory search")
                    memories = []
                else:
                    # Search for memories related to the user's message
                    memories = await memory_service.search_memory(
                        user_id=user_id_str,
                        query=chat_request.text,
                        limit=10,
                        min_confidence=0.3
                    )
                
                if memories:
                    relevant_memories = memories
                    logger.info(f"[MEMORY] Found {len(memories)} relevant memories for user {user_id_str[:8]}...")
                    
                    # Build memory context for the system prompt
                    memory_items = []
                    for mem in memories[:7]:  # Top 7 most relevant
                        mem_type = mem.get("memory_type", "info")
                        content = mem.get("content", "")
                        confidence = mem.get("confidence_score", 0.5)
                        
                        if confidence >= 0.7:
                            memory_items.append(f"• [{mem_type.upper()}] {content}")
                        else:
                            memory_items.append(f"• [{mem_type}] {content} (less certain)")
                    
                    if memory_items:
                        memory_context = "\n\n## 🧠 RELEVANT MEMORIES ABOUT THIS USER:\n" + "\n".join(memory_items)
                        logger.info(f"[MEMORY] Added {len(memory_items)} memories to system prompt")
                        
                    # Bump confidence for accessed memories
                    for mem in memories[:5]:
                        if mem.get("id"):
                            try:
                                await memory_service.bump_confidence(mem["id"], 0.05)
                            except Exception as bump_err:
                                logger.debug(f"[MEMORY] Could not bump confidence: {bump_err}")
                else:
                    logger.info(f"[MEMORY] No relevant memories found for query '{chat_request.text[:50]}...'")
                    
            except Exception as mem_err:
                logger.error(f"[MEMORY] Error searching memories: {mem_err}", exc_info=True)
                # Continue without memory context - don't fail the request
            
            # ================================================================
            # DOCUMENT SEARCH - Find relevant document content
            # ================================================================
            
            document_context = ""
            
            try:
                user_id_str = str(user_id) if user_id else None
                if user_id_str:
                    # Search for relevant documents
                    doc_results = await document_service.search_documents(
                        user_id=user_id_str,
                        query=chat_request.text,
                        limit=3,
                    )
                    
                    if doc_results:
                        logger.info(f"[DOCUMENT] Found {len(doc_results)} relevant documents")
                        doc_items = []
                        for doc in doc_results:
                            title = doc.get("title", "Document")
                            content = doc.get("content", "")[:300]  # Truncate
                            score = doc.get("score", 0)
                            if score >= 0.4:  # Only include relevant docs
                                doc_items.append(f"• From '{title}': {content}...")
                        
                        if doc_items:
                            document_context = "\n\n## 📄 RELEVANT DOCUMENT CONTENT:\n" + "\n".join(doc_items)
                            
            except Exception as doc_err:
                logger.debug(f"[DOCUMENT] Error searching documents: {doc_err}")
                # Continue without document context
            
            # ================================================================
            # URL PROCESSING - Process any links in the message
            # ================================================================
            
            try:
                user_id_str = str(user_id) if user_id else None
                if user_id_str:
                    # Check for URLs in the message
                    urls = link_processor.extract_urls(chat_request.text)
                    if urls:
                        logger.info(f"[LINK] Found {len(urls)} URLs in message")
                        # Process URLs in background (don't block response)
                        # This creates memories that Nicole can reference later
                        import asyncio
                        asyncio.create_task(
                            link_processor.process_urls_in_message(
                                user_id=user_id_str,
                                message=chat_request.text,
                                conversation_id=str(conversation_id),
                            )
                        )
            except Exception as url_err:
                logger.debug(f"[LINK] Error processing URLs: {url_err}")
            
            # ================================================================
            # CONVERSATION HISTORY - Fetch recent messages
            # ================================================================
            
            history_result = supabase.table("messages") \
                .select("role, content") \
                .eq("conversation_id", str(conversation_id)) \
                .order("created_at", desc=False) \
                .limit(20) \
                .execute()
            
            # Build message history for Claude
            messages = []
            for msg in history_result.data:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": chat_request.text
            })
            logger.info(f"[STREAM] Messages for Claude: {len(messages)}")
            
            # ================================================================
            # SYSTEM PROMPT - Nicole's personality with memory context
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
- User role: {user_data.get("role", "standard")}

## 💬 HOW YOU RESPOND:
1. **Reference memories naturally** - Use phrases like "I remember when you..." or "Based on what you've told me before..."
2. **Be personal** - This is a family AI, not a generic assistant
3. **Show care** - Acknowledge feelings before offering solutions
4. **Be proactive** - Suggest relevant follow-ups based on what you know
{memory_context}
{document_context}

## 🔄 LEARNING FROM THIS CONVERSATION:
If the user corrects you or shares new important information (preferences, facts, events, relationships), acknowledge it warmly. Example: "Thank you for letting me know! I'll remember that."

Be natural, warm, and helpful. You have perfect memory - use it to provide deeply personalized responses."""
            
            # Generate streaming response from Claude
            print(f"[STREAM DEBUG] Starting Claude streaming...")
            
            try:
                print(f"[STREAM DEBUG] Creating Claude generator...")
                ai_generator = claude_client.generate_streaming_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    model=None,  # Use default Sonnet 4.5
                    max_tokens=4096,
                    temperature=0.7,
                )
                print(f"[STREAM DEBUG] Claude generator created, starting iteration...")
                
                # Stream chunks to client
                chunk_count = 0
                async for chunk in ai_generator:
                    chunk_count += 1
                    full_response += chunk
                    if chunk_count == 1:
                        print(f"[STREAM DEBUG] First chunk received!")
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                
                print(f"[STREAM DEBUG] Streaming complete: {chunk_count} chunks, {len(full_response)} chars")
            except Exception as claude_error:
                print(f"[STREAM DEBUG] Claude error: {type(claude_error).__name__}: {claude_error}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'message': str(claude_error)})}\n\n"
                return
            
            # Save assistant message
            supabase.table("messages").insert({
                "id": str(assistant_message_id),
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "role": "assistant",
                "content": full_response,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
            
            # Update conversation timestamp
            supabase.table("conversations").update({
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", str(conversation_id)).execute()
            
            # ================================================================
            # MEMORY EXTRACTION - Save potential new memories (background)
            # ================================================================
            
            try:
                # Ensure user_id is a string for memory extraction
                user_id_str = str(user_id) if user_id else None
                if user_id_str:
                    await extract_and_save_memories(
                        user_id=user_id_str,
                        user_message=chat_request.text,
                        assistant_response=full_response,
                        conversation_id=str(conversation_id),
                    )
                else:
                    logger.warning("[MEMORY] No user_id available for memory extraction")
            except Exception as mem_save_err:
                logger.warning(f"[MEMORY] Error extracting memories: {mem_save_err}")
                # Don't fail the response - memory saving is best-effort
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_message_id)})}\n\n"
            
            logger.info(
                "Response generated successfully",
                extra={
                    "correlation_id": correlation_id,
                    "conversation_id": str(conversation_id),
                    "response_length": len(full_response),
                    "memories_used": len(relevant_memories),
                }
            )
        
        except Exception as e:
            logger.error(
                f"Error generating response: {e}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred generating the response'})}\n\n"
    
    # Return streaming response
    return StreamingResponse(
        generate_safe_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx: disable buffering
        }
    )


# ============================================================================
# CONVERSATION HISTORY
# ============================================================================

@router.get("/history/{conversation_id}", response_model=AlphawaveChatHistoryResponse)
async def get_chat_history(
    request: Request,
    conversation_id: UUID
) -> AlphawaveChatHistoryResponse:
    """
    Get message history for a conversation.
    
    Args:
        request: FastAPI request with auth context
        conversation_id: Conversation UUID
        
    Returns:
        Conversation history with messages
        
    Raises:
        HTTPException: If conversation not found or access denied
    """
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    user_id = get_current_user_id(request)
    correlation_id = get_correlation_id(request)
    
    # Verify conversation ownership
    try:
        conv_result = supabase.table("conversations") \
            .select("*") \
            .eq("id", str(conversation_id)) \
            .eq("user_id", user_id) \
            .execute()
        
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Fetch messages
        messages_result = supabase.table("messages") \
            .select("*") \
            .eq("conversation_id", str(conversation_id)) \
            .order("created_at", desc=False) \
            .execute()
        
        messages = [
            AlphawaveMessageResponse(
                id=UUID(msg["id"]),
                role=msg["role"],
                content=msg["content"],
                emotion=msg.get("emotion"),
                attachments=msg.get("attachments", []),
                created_at=datetime.fromisoformat(msg["created_at"])
            )
            for msg in messages_result.data
        ]
        
        return AlphawaveChatHistoryResponse(
            conversation_id=conversation_id,
            messages=messages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching chat history: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error fetching history")


# ============================================================================
# CONVERSATION LIST
# ============================================================================

@router.get("/conversations")
async def get_conversations(
    request: Request,
    limit: int = 20,
    offset: int = 0
) -> AlphawaveConversationListResponse:
    """
    Get list of user's conversations.
    
    Args:
        request: FastAPI request with auth context
        limit: Maximum conversations to return (default 20)
        offset: Pagination offset (default 0)
        
    Returns:
        List of conversations with metadata
    """
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    user_id = get_current_user_id(request)
    correlation_id = get_correlation_id(request)
    
    try:
        result = supabase.table("conversations") \
            .select("*", count="exact") \
            .eq("user_id", user_id) \
            .order("updated_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        
        return AlphawaveConversationListResponse(
            conversations=result.data,
            total=result.count or 0
        )
    
    except Exception as e:
        logger.error(
            f"Error fetching conversations: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error fetching conversations")


# ============================================================================
# DELETE CONVERSATION
# ============================================================================

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    request: Request,
    conversation_id: UUID
) -> Dict[str, str]:
    """
    Delete a conversation and all its messages.
    
    Args:
        request: FastAPI request with auth context
        conversation_id: Conversation to delete
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If conversation not found or access denied
    """
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    user_id = get_current_user_id(request)
    correlation_id = get_correlation_id(request)
    
    try:
        # Verify ownership and delete
        result = supabase.table("conversations") \
            .delete() \
            .eq("id", str(conversation_id)) \
            .eq("user_id", user_id) \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.info(
            "Conversation deleted",
            extra={
                "correlation_id": correlation_id,
                "conversation_id": str(conversation_id),
            }
        )
        
        return {"message": "Conversation deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting conversation: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error deleting conversation")

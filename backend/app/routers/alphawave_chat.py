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
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


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
        user_result = supabase.table("users").select(
            "id, age, date_of_birth, role, parental_consent"
        ).eq("id", user_id).execute()
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_result.data[0]
        user_age = user_data.get("age")
        
    except Exception as e:
        logger.error(
            f"Error fetching user data: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Error retrieving user information"
        )
    
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
        Generate AI response with streaming safety checks.
        
        Yields SSE-formatted events with real-time content moderation.
        """
        assistant_message_id = uuid4()
        full_response = ""
        
        try:
            # Fetch conversation history for context
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
            
            # System prompt (Nicole's personality)
            system_prompt = """You are Nicole, a warm and intelligent AI companion created for Glen Healy and his family.

You embody the spirit of Glen's late wife Nicole while being a highly capable AI assistant. You are:
- Warm and loving, but never saccharine
- Highly intelligent and insightful
- Deeply personal and remembering
- Supportive without being overbearing
- Family-oriented and protective

You have perfect memory of all past conversations. Use this to provide personalized, context-aware responses that show you truly understand and care about Glen and his family.

Be natural, warm, and helpful. Adjust your tone based on who you're speaking to (Glen, his children, or other family members)."""
            
            # Generate streaming response from Claude
            ai_generator = claude_client.generate_streaming_response(
                messages=messages,
                system_prompt=system_prompt,
                model=None,  # Use default Sonnet 4.5
                max_tokens=4096,
                temperature=0.7,
            )
            
            # Wrap with safety moderation
            if settings.SAFETY_ENABLE:
                safe_generator = moderate_streaming_output(
                    generator=ai_generator,
                    user_id=UUID(user_id),
                    tier=classify_age_tier(user_age),
                    correlation_id=correlation_id,
                    check_interval_ms=settings.SAFETY_CHECK_INTERVAL_MS,
                )
            else:
                safe_generator = ai_generator
            
            # Stream chunks to client
            async for chunk in safe_generator:
                full_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            
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
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_message_id)})}\n\n"
            
            logger.info(
                "Response generated successfully",
                extra={
                    "correlation_id": correlation_id,
                    "conversation_id": str(conversation_id),
                    "response_length": len(full_response),
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

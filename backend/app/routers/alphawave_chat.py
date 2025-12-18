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
from app.services.memory_intelligence import memory_intelligence, MemoryAnalysis
from app.prompts.nicole_system_prompt import (
    build_nicole_system_prompt,
    build_memory_context,
    build_document_context,
)
from app.config import settings
from app.services.agent_orchestrator import agent_orchestrator

logger = logging.getLogger(__name__)


# ============================================================================
# AGENT CONFIGURATION
# ============================================================================

# Feature flags - Now configured via settings
from app.config import settings
ENABLE_AGENT_TOOLS = settings.AGENT_TOOLS_ENABLED
ENABLE_EXTENDED_THINKING = settings.EXTENDED_THINKING_ENABLED

router = APIRouter()


# ============================================================================
# INTELLIGENT MEMORY PROCESSING
# ============================================================================

async def process_memories_intelligently(
    tiger_user_id: int,
    user_message: str,
    assistant_response: str,
    conversation_id: int,
    user_name: str = "User",
) -> int:
    """
    Intelligently process conversation for memory extraction using AI.
    
    This function:
    1. Uses Claude to analyze the conversation for meaningful memories
    2. Generates appropriate tags dynamically
    3. Creates relationships between related memories
    4. Handles corrections by updating existing memories
    5. Creates knowledge bases when patterns emerge
    
    This replaces the old pattern-based extraction with intelligent analysis.
    """
    try:
        # Step 1: Analyze the message with AI
        logger.info(f"[MEMORY INTEL] Analyzing message for user {tiger_user_id}...")
        
        analysis: MemoryAnalysis = await memory_intelligence.analyze_message_for_memories(
            user_id=tiger_user_id,
            user_message=user_message,
            assistant_response=assistant_response,
            conversation_id=conversation_id,
            user_name=user_name,
        )
        
        if not analysis.should_save:
            logger.info(f"[MEMORY INTEL] No memories to save: {analysis.analysis_reasoning}")
            return 0
        
        logger.info(f"[MEMORY INTEL] Found {len(analysis.memories)} memories to save")
        saved_count = 0
        
        # Step 2: Process each extracted memory
        for extracted_mem in analysis.memories:
            try:
                # Save the memory
                saved_memory = await memory_service.save_memory(
                    user_id=tiger_user_id,
                    memory_type=extracted_mem.memory_type,
                    content=extracted_mem.content,
                    context=extracted_mem.context,
                    importance=extracted_mem.importance,
                    related_conversation=conversation_id,
                    source="user",
                )
                
                if not saved_memory:
                    logger.debug(f"[MEMORY INTEL] Memory not saved (likely duplicate)")
                    continue
                
                saved_count += 1
                memory_id = saved_memory.get("memory_id") or saved_memory.get("id")
                logger.info(f"[MEMORY INTEL] ✅ Saved memory {memory_id}: {extracted_mem.content[:50]}...")
                
                # Step 3: Generate and apply tags
                if extracted_mem.suggested_tags:
                    tags = await memory_intelligence.generate_tags_for_memory(
                        user_id=tiger_user_id,
                        content=extracted_mem.content,
                        memory_type=extracted_mem.memory_type,
                        suggested_tags=extracted_mem.suggested_tags,
                    )
                    
                    for tag in tags:
                        try:
                            await db.execute(
                                """
                                INSERT INTO memory_tag_links (memory_id, tag_id, assigned_by, confidence)
                                VALUES ($1, $2, 'nicole', $3)
                                ON CONFLICT (memory_id, tag_id) DO NOTHING
                                """,
                                memory_id,
                                tag["tag_id"],
                                0.9 if not tag["is_new"] else 0.7,
                            )
                        except Exception as tag_err:
                            logger.debug(f"[MEMORY INTEL] Tag link failed: {tag_err}")
                
                # Step 4: Create relationships
                if extracted_mem.should_link_to or extracted_mem.entities:
                    relationships = await memory_intelligence.find_and_create_relationships(
                        user_id=tiger_user_id,
                        new_memory_id=memory_id,
                        content=extracted_mem.content,
                        entities=extracted_mem.entities,
                        suggested_links=extracted_mem.should_link_to,
                    )
                    
                    if relationships:
                        saved_rels = await memory_intelligence.save_relationships(tiger_user_id, relationships)
                        logger.info(f"[MEMORY INTEL] Created {saved_rels} relationships")
                
            except Exception as mem_err:
                logger.error(f"[MEMORY INTEL] Failed to process memory: {mem_err}")
        
        # Step 5: Handle corrections
        if analysis.detected_correction and analysis.correction_target:
            try:
                # Archive the old memory and link to the new one
                await db.execute(
                    """
                    UPDATE memory_entries 
                    SET archived_at = NOW(), 
                        updated_at = NOW()
                    WHERE memory_id = $1 AND user_id = $2
                    """,
                    analysis.correction_target,
                    tiger_user_id,
                )
                logger.info(f"[MEMORY INTEL] Archived corrected memory {analysis.correction_target}")
            except Exception as corr_err:
                logger.warning(f"[MEMORY INTEL] Correction handling failed: {corr_err}")
        
        # Step 6: Check if we should create a knowledge base
        if analysis.suggested_kb:
            should_create = await memory_intelligence.should_create_knowledge_base(
                tiger_user_id, 
                analysis.suggested_kb,
                threshold=3  # Need at least 3 memories about the topic
            )
            
            if should_create:
                kb_id = await memory_intelligence.create_knowledge_base(
                    user_id=tiger_user_id,
                    name=analysis.suggested_kb,
                    kb_type="topic",
                )
                
                if kb_id:
                    # Organize existing memories into the new KB
                    organized = await memory_intelligence.organize_memories_into_kb(
                        tiger_user_id, kb_id, analysis.suggested_kb
                    )
                    logger.info(f"[MEMORY INTEL] Created KB '{analysis.suggested_kb}' with {organized} memories")
        
        logger.info(f"[MEMORY INTEL] Memory processing complete - saved {saved_count} memories")
        return saved_count
        
    except Exception as e:
        logger.error(f"[MEMORY INTEL] Intelligent processing failed: {e}", exc_info=True)
        # Don't raise - memory processing shouldn't break chat
        return 0


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
# DEBUG: Streaming Test Endpoint
# ============================================================================

@router.get("/stream-test")
async def stream_test():
    """Test endpoint to verify SSE streaming works with no buffering."""
    import time
    import asyncio
    
    async def generate():
        for i in range(5):
            yield f"data: {json.dumps({'type': 'tick', 'count': i, 'time': time.time()})}\n\n"
            await asyncio.sleep(1)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


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
            # Handle both UUID (Supabase) and non-UUID (Google OAuth sub) user IDs
            try:
                safety_user_id = UUID(supabase_user_id) if supabase_user_id else uuid4()
            except (ValueError, AttributeError):
                # Google OAuth sub is not a UUID - generate deterministic UUID from it
                import hashlib
                hash_bytes = hashlib.md5(supabase_user_id.encode()).digest()
                safety_user_id = UUID(bytes=hash_bytes)
            
            safety_decision = await check_input_safety(
                content=chat_request.text,
                user_id=safety_user_id,
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
    is_new_conversation = False
    
    if not conversation_id:
        # Create new conversation in Tiger
        is_new_conversation = True
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
        import sys
        print(f"[STREAM] ========== NEW REQUEST ==========", file=sys.stderr, flush=True)
        print(f"[STREAM] Generator started for conversation {conversation_id}", file=sys.stderr, flush=True)
        logger.info(f"[STREAM] ========== NEW REQUEST ==========")
        logger.info(f"[STREAM] Generator started for conversation {conversation_id}")
        logger.info(f"[STREAM] is_new_conversation: {is_new_conversation}")
        logger.info(f"[STREAM] user_message: {chat_request.text[:50]}...")
        
        full_response = ""
        
        # Send immediate acknowledgment - this should appear instantly
        yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id})}\n\n"
        
        # DEBUG: Send a test event to verify streaming works
        import time as time_module
        print(f"[STREAM] Yielding status event at {time_module.time()}", file=sys.stderr, flush=True)
        yield f"data: {json.dumps({'type': 'status', 'text': 'Stream connected at ' + str(time_module.time())})}\n\n"
        
        try:
            import time as perf_time
            import asyncio
            
            # ================================================================
            # PARALLEL CONTEXT GATHERING (memory + documents in parallel)
            # ================================================================
            # These both call OpenAI for embeddings, so parallelizing saves ~5-10s
            
            relevant_memories = []
            memory_context = ""
            document_context = ""
            
            yield f"data: {json.dumps({'type': 'status', 'text': 'Gathering context...'})}\n\n"
            
            context_start = perf_time.time()
            
            async def fetch_memories():
                """Fetch relevant memories for the query."""
                try:
                    memories = await memory_service.search_memory(
                        user_id=tiger_user_id,
                        query=chat_request.text,
                        limit=10,
                        min_confidence=0.3,
                    )
                    return memories or []
                except Exception as e:
                    logger.error(f"[MEMORY RETRIEVAL] ERROR: {e}")
                    return []
            
            async def fetch_documents():
                """Fetch relevant documents for the query."""
                try:
                    docs = await document_service.search_documents(
                        user_id=tiger_user_id,
                        query=chat_request.text,
                        limit=3,
                    )
                    return docs or []
                except Exception as e:
                    logger.debug(f"[DOCUMENT] Error searching documents: {e}")
                    return []
            
            # Run both searches in parallel
            print(f"[STREAM] Starting parallel context fetch...", file=sys.stderr, flush=True)
            memories, doc_results = await asyncio.gather(
                fetch_memories(),
                fetch_documents(),
                return_exceptions=True
            )
            
            # Handle exceptions from gather
            if isinstance(memories, Exception):
                logger.error(f"[MEMORY] Parallel fetch failed: {memories}")
                print(f"[ERROR] Memory fetch failed: {memories}", file=sys.stderr, flush=True)
                memories = []
            if isinstance(doc_results, Exception):
                logger.debug(f"[DOCUMENT] Parallel fetch failed: {doc_results}")
                doc_results = []
            
            fetch_duration = perf_time.time() - context_start
            print(f"[PERF] Parallel context fetch took {fetch_duration:.2f}s (memories: {len(memories)}, docs: {len(doc_results)})", file=sys.stderr, flush=True)
            logger.info(f"[PERF] Parallel context fetch took {fetch_duration:.2f}s (memories: {len(memories)}, docs: {len(doc_results)})")
            
            # Process memories
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
                    
                # Boost accessed memories (fire and forget)
                for mem in memories[:5]:
                    if mem.get("memory_id"):
                        try:
                            asyncio.create_task(memory_service.bump_confidence(mem["memory_id"], 0.05))
                        except Exception:
                            pass
            else:
                logger.info(f"[MEMORY RETRIEVAL] No memories found for query")
            
            # Process documents
            try:
                
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
            # CONVERSATION HISTORY (Last 25 messages for context)
            # ================================================================
            # 
            # Context window strategy:
            # - Load last 25 messages to maintain conversation flow
            # - This ensures Nicole has enough context to avoid repetitive questions
            # - Older context is captured in memory system for long-term recall
            #
            
            hist_start = perf_time.time()
            history_rows = await db.fetch(
                f"""
                SELECT message_role, content, created_at
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT {settings.CONVERSATION_HISTORY_LIMIT}
                """,
                conversation_id,
            )
            logger.info(f"[PERF] History fetch took {perf_time.time() - hist_start:.2f}s")
            
            logger.info(f"[STREAM] Raw history rows fetched: {len(history_rows)} for conversation {conversation_id}")
            
            # Reverse to chronological order (oldest first)
            history_rows = list(reversed(history_rows))
            
            messages = [
                {"role": row["message_role"], "content": row["content"]}
                for row in history_rows
            ]
            
            # FALLBACK: If history is empty (race condition), add current message directly
            # This ensures Claude always has at least the user's message
            if not messages:
                logger.warning(f"[STREAM] History empty for conversation {conversation_id} - adding message directly")
                messages = [{"role": "user", "content": chat_request.text}]
            
            logger.info(f"[STREAM] Messages for Claude: {len(messages)} (context window: 25)")
            
            # ================================================================
            # SYSTEM PROMPT - Nicole's Complete Personality & Memory System
            # ================================================================
            
            # Build formatted memory context (document context already built above)
            formatted_memory_context = build_memory_context(relevant_memories) if relevant_memories else ""
            # Use document_context that was already built in the DOCUMENT SEARCH section
            formatted_document_context = document_context
            
            # Detect relevant skills for this request
            active_skill = None
            skills_summary = ""
            try:
                skill_context = agent_orchestrator.get_skill_context(chat_request.text)
                if skill_context:
                    active_skill = skill_context
                    logger.info(f"[STREAM] Activated skill for request")
                else:
                    # Get general skills summary for awareness
                    skills_summary = agent_orchestrator.get_skills_summary()
            except Exception as e:
                logger.warning(f"[STREAM] Skill detection failed: {e}")
            
            # Build family context from user data if available
            family_context = None
            if "family_members" in user_data:
                family_context = {"members": user_data["family_members"]}
            
            # Build the complete system prompt
            system_prompt = build_nicole_system_prompt(
                user_name=user_name,
                user_role=user_data.get("user_role", "user"),
                user_data=user_data,
                memory_context=formatted_memory_context,
                document_context=formatted_document_context,
                family_context=family_context,
                skills_context=skills_summary,
                active_skill=active_skill,
            )
            
            # Generate streaming response
            logger.info(f"[STREAM] Starting Claude streaming...")
            yield f"data: {json.dumps({'type': 'status', 'text': 'Connecting to Claude...'})}\n\n"
            
            
            # Send conversation_id for new conversations so frontend can track
            if is_new_conversation:
                yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conversation_id})}\n\n"
            
            try:
                # ============================================================
                # AGENT TOOLS INTEGRATION
                # ============================================================
                if ENABLE_AGENT_TOOLS:
                    # Start agent session for tracking
                    session_id = f"chat_{conversation_id}_{datetime.utcnow().timestamp()}"
                    agent_orchestrator.start_session(
                        session_id=session_id,
                        user_id=tiger_user_id,
                        conversation_id=conversation_id
                    )
                    
                    # Get core tools (Think, Tool Search, Memory, Document)
                    tools = agent_orchestrator.get_core_tools()
                    
                    # Get tool executor bound to this user/session
                    tool_executor = agent_orchestrator.get_tool_executor(
                        user_id=tiger_user_id,
                        session_id=session_id
                    )
                    
                    logger.info(f"[STREAM] Using agent tools: {[t['name'] for t in tools]}")
                    
                    # Use streaming with tools + extended thinking
                    chunk_count = 0
                    async for event in claude_client.generate_streaming_response_with_tools(
                        messages=messages,
                        tools=tools,
                        tool_executor=tool_executor,
                        system_prompt=system_prompt,
                        model=None,
                        max_tokens=16000,
                        temperature=0.7,
                        enable_thinking=ENABLE_EXTENDED_THINKING,
                        thinking_budget=settings.EXTENDED_THINKING_BUDGET,
                    ):
                        event_type = event.get("type", "")
                        
                        # Extended thinking events
                        if event_type == "thinking_start":
                            yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                        
                        elif event_type == "thinking_delta":
                            # Stream thinking content (fast - no delay)
                            yield f"data: {json.dumps({'type': 'thinking_delta', 'content': event.get('content', '')})}\n\n"
                        
                        elif event_type == "thinking_stop":
                            yield f"data: {json.dumps({'type': 'thinking_stop', 'duration': event.get('duration', 0)})}\n\n"
                        
                        elif event_type == "text":
                            content = event.get("content", "")
                            chunk_count += 1
                            full_response += content
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                        
                        elif event_type == "tool_use_start":
                            yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': event.get('tool_name', '')})}\n\n"
                        
                        elif event_type == "tool_use_complete":
                            yield f"data: {json.dumps({'type': 'tool_complete', 'tool_name': event.get('tool_name', ''), 'success': event.get('success', True)})}\n\n"
                        
                        elif event_type == "error":
                            logger.error(f"[STREAM] Agent error: {event.get('message', '')}")
                            yield f"data: {json.dumps({'type': 'error', 'message': event.get('message', 'An error occurred')})}\n\n"
                            return
                        
                        elif event_type == "done":
                            break
                    
                    # End agent session
                    session_summary = agent_orchestrator.end_session(session_id)
                    if session_summary:
                        logger.info(f"[STREAM] Session had {len(session_summary.get('tool_calls', []))} tool calls, {len(session_summary.get('thinking_steps', []))} thinking steps")
                    
                    logger.info(f"[STREAM] Complete: {chunk_count} chunks, {len(full_response)} chars")
                
                else:
                    # Fallback: Simple streaming with extended thinking
                    logger.info(f"[STREAM] Calling Claude with {len(messages)} messages")
                    
                    if ENABLE_EXTENDED_THINKING:
                        # Use extended thinking for better reasoning
                        logger.info("[STREAM] Using extended thinking mode")
                        
                        async for event in claude_client.generate_streaming_response_with_thinking(
                            messages=messages,
                            system_prompt=system_prompt,
                            model=None,
                            max_tokens=16000,
                            thinking_budget=8000,
                        ):
                            event_type = event.get("type", "")
                            
                            if event_type == "thinking_start":
                                yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                            
                            elif event_type == "thinking_delta":
                                # Stream thinking content (fast)
                                yield f"data: {json.dumps({'type': 'thinking_delta', 'content': event.get('content', '')})}\n\n"
                            
                            elif event_type == "thinking_stop":
                                yield f"data: {json.dumps({'type': 'thinking_stop', 'duration': event.get('duration', 0)})}\n\n"
                            
                            elif event_type == "text_delta":
                                # Stream response content
                                content = event.get("content", "")
                                full_response += content
                                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                            
                            elif event_type == "error":
                                yield f"data: {json.dumps({'type': 'error', 'message': event.get('message', 'Unknown error')})}\n\n"
                                return
                            
                            elif event_type == "done":
                                break
                        
                        logger.info(f"[STREAM] Complete with thinking: {len(full_response)} chars")
                    
                    else:
                        # Standard streaming without thinking
                        ai_generator = claude_client.generate_streaming_response(
                            messages=messages,
                            system_prompt=system_prompt,
                            model=None,
                            max_tokens=4096,
                            temperature=0.7,
                        )
                        
                        chunk_count = 0
                        async for chunk in ai_generator:
                            if chunk_count == 0:
                                logger.info(f"[STREAM] First chunk received!")
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
            # INTELLIGENT MEMORY PROCESSING
            # ================================================================
            
            try:
                logger.info(f"[MEMORY] Starting intelligent processing for user {tiger_user_id}")
                # Use the new intelligent memory processing
                memories_saved = await process_memories_intelligently(
                    tiger_user_id=tiger_user_id,
                    user_message=chat_request.text,
                    assistant_response=full_response,
                    conversation_id=conversation_id,
                    user_name=user_name,
                )
                logger.info(f"[MEMORY] Intelligent processing complete - saved {memories_saved} memories")
                
                # Emit memory saved event if any were saved
                if memories_saved > 0:
                    yield f"data: {json.dumps({'type': 'memory_saved', 'count': memories_saved})}\n\n"
                    
            except Exception as mem_save_err:
                logger.error(f"[MEMORY] Error in intelligent memory processing: {mem_save_err}", exc_info=True)
            
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
        SELECT message_id, message_role, content, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        """,
        conversation_id,
    )
    
    messages = [
        {
            "id": row["message_id"],
            "role": row["message_role"],  # Map DB column to API response field
            "content": row["content"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in message_rows
    ]
    
    return AlphawaveChatHistoryResponse(
        conversation_id=conversation_id,
        messages=messages
    )


# Alias endpoint for frontend compatibility
@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    request: Request,
    conversation_id: int
) -> AlphawaveChatHistoryResponse:
    """
    Get message history for a conversation.
    Alias for /history/{conversation_id} to match frontend expectations.
    """
    return await get_chat_history(request, conversation_id)


# ============================================================================
# CONVERSATION LIST
# ============================================================================

@router.get("/conversations")
async def get_conversations(
    request: Request,
    limit: int = 30,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get list of user's conversations with pinning support.
    
    Returns conversations sorted by:
    1. Pinned conversations first (by pin_order)
    2. Then recent conversations (by last_message_at or created_at)
    """
    
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
            updated_at,
            COALESCE(is_pinned, FALSE) as is_pinned,
            pin_order,
            COALESCE(message_count, 0) as message_count
        FROM conversations
        WHERE user_id = $1 AND conversation_status != 'deleted'
        ORDER BY 
            is_pinned DESC NULLS LAST,
            CASE WHEN is_pinned = TRUE THEN pin_order ELSE NULL END ASC NULLS LAST,
            COALESCE(last_message_at, created_at) DESC
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
            "conversation_id": row["conversation_id"],
            "title": row["title"] or "New Conversation",
            "status": row["conversation_status"],
            "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "is_pinned": row["is_pinned"],
            "pin_order": row["pin_order"],
            "message_count": row["message_count"],
        }
        for row in rows
    ]
    
    return {
        "conversations": conversations,
        "total": count_row["total"] if count_row else 0
    }


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


# ============================================================================
# PIN/UNPIN CONVERSATION
# ============================================================================

class PinRequest(BaseModel):
    is_pinned: bool


@router.post("/conversations/{conversation_id}/pin")
async def pin_conversation(
    request: Request,
    conversation_id: int,
    pin_request: PinRequest
) -> Dict[str, Any]:
    """Pin or unpin a conversation."""
    
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if pin_request.is_pinned:
        # Check pin limit (max 5)
        count_row = await db.fetchrow(
            """
            SELECT COUNT(*) as pinned_count
            FROM conversations
            WHERE user_id = $1 AND is_pinned = TRUE
            """,
            tiger_user_id,
        )
        
        if count_row and count_row["pinned_count"] >= 5:
            raise HTTPException(status_code=400, detail="Maximum 5 pinned conversations allowed")
        
        # Get next pin order
        max_order_row = await db.fetchrow(
            """
            SELECT COALESCE(MAX(pin_order), -1) + 1 as next_order
            FROM conversations
            WHERE user_id = $1 AND is_pinned = TRUE
            """,
            tiger_user_id,
        )
        next_order = max_order_row["next_order"] if max_order_row else 0
        
        await db.execute(
            """
            UPDATE conversations
            SET is_pinned = TRUE, pin_order = $3, updated_at = NOW()
            WHERE conversation_id = $1 AND user_id = $2
            """,
            conversation_id,
            tiger_user_id,
            next_order,
        )
    else:
        # Unpin
        await db.execute(
            """
            UPDATE conversations
            SET is_pinned = FALSE, pin_order = NULL, updated_at = NOW()
            WHERE conversation_id = $1 AND user_id = $2
            """,
            conversation_id,
            tiger_user_id,
        )
    
    logger.info(f"Conversation {conversation_id} {'pinned' if pin_request.is_pinned else 'unpinned'} by user {tiger_user_id}")
    
    return {"message": "Pin status updated", "is_pinned": pin_request.is_pinned}


# ============================================================================
# REORDER PINNED CONVERSATIONS
# ============================================================================

class ReorderPinsRequest(BaseModel):
    order: List[Dict[str, int]]  # [{"conversation_id": 1, "pin_order": 0}, ...]


@router.post("/conversations/reorder-pins")
async def reorder_pinned_conversations(
    request: Request,
    reorder_request: ReorderPinsRequest
) -> Dict[str, str]:
    """Reorder pinned conversations via drag-and-drop."""
    
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    for item in reorder_request.order:
        await db.execute(
            """
            UPDATE conversations
            SET pin_order = $3, updated_at = NOW()
            WHERE conversation_id = $1 AND user_id = $2 AND is_pinned = TRUE
            """,
            item["conversation_id"],
            tiger_user_id,
            item["pin_order"],
        )
    
    logger.info(f"Pinned conversations reordered by user {tiger_user_id}")
    
    return {"message": "Pin order updated"}


# ============================================================================
# CLEANUP SHORT CONVERSATIONS (Called by background job)
# ============================================================================

@router.post("/conversations/cleanup")
async def cleanup_short_conversations(request: Request) -> Dict[str, Any]:
    """
    Delete short conversations (≤3 messages) older than 3 days.
    This is typically called by a scheduled background job.
    """
    
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Call the database function
    result = await db.fetchval(
        "SELECT cleanup_short_conversations($1)",
        tiger_user_id,
    )
    
    deleted_count = result if result else 0
    logger.info(f"Cleaned up {deleted_count} short conversations for user {tiger_user_id}")
    
    return {"message": f"Cleaned up {deleted_count} conversations", "deleted_count": deleted_count}

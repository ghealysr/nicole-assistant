"""
Faz Code Chat Router

WebSocket and HTTP endpoints for real-time chat and activity streaming.
Includes authentication for WebSocket connections.
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging
import json
import asyncio
from datetime import datetime

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.database import db
from app.middleware.alphawave_auth import get_current_user
from app.config import settings
from app.services.tiger_user_service import tiger_user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faz", tags=["Faz Code Chat"])


# =============================================================================
# WEBSOCKET AUTHENTICATION
# =============================================================================

async def verify_ws_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Google OAuth ID token for WebSocket connections.
    
    Args:
        token: Google OAuth ID token
        
    Returns:
        User info dict if valid, None otherwise
    """
    if not token:
        return None
    
    try:
        google_client_id = settings.GOOGLE_CLIENT_ID
        if not google_client_id:
            logger.error("[Faz WS] GOOGLE_CLIENT_ID not configured")
            return None
        
        # Verify ID token with Google
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            google_client_id
        )
        
        # Verify issuer
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            logger.warning(f"[Faz WS] Invalid token issuer: {idinfo.get('iss')}")
            return None
        
        # Extract user info
        user_id = idinfo.get("sub")
        user_email = idinfo.get("email")
        email_verified = idinfo.get("email_verified", False)
        
        if not user_id or not email_verified:
            return None
        
        # Get or create Tiger user (for database user_id)
        tiger_user = await tiger_user_service.get_or_create_user(
            google_id=user_id,
            email=user_email,
            name=idinfo.get("name", ""),
            picture=idinfo.get("picture", "")
        )
        
        if not tiger_user:
            return None
        
        return {
            "user_id": tiger_user.get("user_id"),
            "google_id": user_id,
            "email": user_email,
            "name": idinfo.get("name", ""),
        }
        
    except Exception as e:
        logger.error(f"[Faz WS] Token verification failed: {e}")
        return None


async def verify_project_access(user_id: int, project_id: int) -> bool:
    """
    Verify user has access to the project.
    
    Args:
        user_id: Tiger database user ID
        project_id: Project ID to check
        
    Returns:
        True if user owns the project, False otherwise
    """
    try:
        result = await db.fetchval(
            "SELECT 1 FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user_id
        )
        return result is not None
    except Exception as e:
        logger.error(f"[Faz WS] Project access check failed: {e}")
        return False


# =============================================================================
# SCHEMAS
# =============================================================================

class ChatMessage(BaseModel):
    """Chat message."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    agent_name: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request."""
    project_id: int
    message: str
    run_pipeline: bool = False  # If True, runs the agent pipeline


class ChatResponse(BaseModel):
    """Chat response."""
    message_id: int
    role: str
    content: str
    agent_name: Optional[str]
    model_used: Optional[str]
    created_at: datetime


# =============================================================================
# WEBSOCKET CONNECTION MANAGER
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections per project."""
    
    def __init__(self):
        # project_id -> list of WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: int):
        """Accept and track connection."""
        await websocket.accept()
        
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        
        self.active_connections[project_id].append(websocket)
        logger.info(f"[Faz WS] Client connected to project {project_id}")
    
    def disconnect(self, websocket: WebSocket, project_id: int):
        """Remove connection."""
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        
        logger.info(f"[Faz WS] Client disconnected from project {project_id}")
    
    async def broadcast_to_project(self, project_id: int, message: Dict[str, Any]):
        """Broadcast message to all connections for a project."""
        if project_id not in self.active_connections:
            return
        
        dead_connections = []
        
        for connection in self.active_connections[project_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for dead in dead_connections:
            self.disconnect(dead, project_id)
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"[Faz WS] Failed to send: {e}")


# Global connection manager
manager = ConnectionManager()


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/projects/{project_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: int,
    token: Optional[str] = Query(None, description="Google OAuth ID token for authentication"),
):
    """
    WebSocket for real-time project updates.
    
    Authentication:
    - Pass token as query parameter: /projects/{id}/ws?token=<google_id_token>
    
    Receives:
    - {"type": "chat", "message": "user message"} - Send chat message
    - {"type": "run", "start_agent": "nicole"} - Run pipeline
    - {"type": "ping"} - Keep-alive
    
    Sends:
    - {"type": "activity", ...} - Agent activity updates
    - {"type": "chat", ...} - Chat messages
    - {"type": "status", ...} - Project status changes
    - {"type": "file", ...} - File generation events
    - {"type": "error", ...} - Error messages
    """
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    
    # Verify token
    user_info = await verify_ws_token(token) if token else None
    
    if not user_info:
        logger.warning(f"[Faz WS] Unauthorized connection attempt for project {project_id}")
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    user_id = user_info["user_id"]
    
    # Verify project access
    has_access = await verify_project_access(user_id, project_id)
    
    if not has_access:
        logger.warning(f"[Faz WS] User {user_id} denied access to project {project_id}")
        await websocket.close(code=4003, reason="Access denied to this project")
        return
    
    logger.info(f"[Faz WS] User {user_info['email']} authenticated for project {project_id}")
    
    # =========================================================================
    # CONNECTION SETUP
    # =========================================================================
    
    await manager.connect(websocket, project_id)
    
    # Start activity watcher
    activity_task = asyncio.create_task(watch_activities(websocket, project_id))
    
    # Store user_id for message context
    ws_user_id = user_id
    
    try:
        # Send initial state
        project = await db.fetchrow(
            "SELECT * FROM faz_projects WHERE project_id = $1",
            project_id,
        )
        
        if project:
            await manager.send_personal(websocket, {
                "type": "status",
                "status": project["status"],
                "current_agent": project["current_agent"],
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            # Send auth confirmation
            await manager.send_personal(websocket, {
                "type": "auth",
                "authenticated": True,
                "user": {
                    "user_id": user_info["user_id"],
                    "email": user_info["email"],
                    "name": user_info["name"],
                },
            })
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_json()
                
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await manager.send_personal(websocket, {"type": "pong"})
                    
                elif msg_type == "chat":
                    # Handle chat message
                    message = data.get("message", "")
                    if message:
                        await handle_chat_message(websocket, project_id, message, ws_user_id)
                
                elif msg_type == "run":
                    # Start pipeline
                    start_agent = data.get("start_agent", "nicole")
                    await handle_run_pipeline(websocket, project_id, start_agent, ws_user_id)
                
                else:
                    await manager.send_personal(websocket, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })
                    
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"[Faz WS] Error: {e}")
    finally:
        activity_task.cancel()
        manager.disconnect(websocket, project_id)


async def watch_activities(websocket: WebSocket, project_id: int):
    """Watch for new activities and broadcast them."""
    last_activity_id = 0
    
    while True:
        try:
            # Get new activities
            activities = await db.fetch(
                """
                SELECT activity_id, agent_name, agent_model, activity_type, 
                       message, content_type, full_content, status, started_at
                FROM faz_agent_activities
                WHERE project_id = $1 AND activity_id > $2
                ORDER BY activity_id
                LIMIT 20
                """,
                project_id,
                last_activity_id,
            )
            
            for activity in activities:
                await manager.send_personal(websocket, {
                    "type": "activity",
                    "activity_id": activity["activity_id"],
                    "agent": activity["agent_name"],
                    "model": activity["agent_model"],
                    "activity_type": activity["activity_type"],
                    "message": activity["message"],
                    "content_type": activity["content_type"],
                    "full_content": activity["full_content"],
                    "status": activity["status"],
                    "timestamp": activity["started_at"].isoformat() if activity["started_at"] else None,
                })
                
                last_activity_id = activity["activity_id"]
            
            # Check for status changes
            project = await db.fetchrow(
                "SELECT status, current_agent FROM faz_projects WHERE project_id = $1",
                project_id,
            )
            
            if project:
                await manager.send_personal(websocket, {
                    "type": "status",
                    "status": project["status"],
                    "current_agent": project["current_agent"],
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            # Poll interval
            await asyncio.sleep(1)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Faz WS] Activity watcher error: {e}")
            await asyncio.sleep(2)


async def handle_chat_message(websocket: WebSocket, project_id: int, message: str, user_id: int = None):
    """Handle incoming chat message."""
    try:
        # Store user message
        message_id = await db.fetchval(
            """
            INSERT INTO faz_conversations (project_id, role, content, user_id)
            VALUES ($1, 'user', $2, $3)
            RETURNING message_id
            """,
            project_id,
            message,
            user_id,
        )
        
        # Broadcast user message
        await manager.broadcast_to_project(project_id, {
            "type": "chat",
            "message_id": message_id,
            "role": "user",
            "content": message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Get project prompt
        project = await db.fetchrow(
            "SELECT original_prompt FROM faz_projects WHERE project_id = $1",
            project_id,
        )
        
        if not project:
            return
        
        # Generate response using Nicole
        from app.services.faz_agents import NicoleAgent
        
        nicole = NicoleAgent()
        
        # Build state for Nicole
        state = {
            "project_id": project_id,
            "original_prompt": project["original_prompt"],
            "current_prompt": message,
        }
        
        result = await nicole.run(state)
        
        # Store assistant message
        response_id = await db.fetchval(
            """
            INSERT INTO faz_conversations (project_id, role, content, agent_name, model_used)
            VALUES ($1, 'assistant', $2, 'nicole', $3)
            RETURNING message_id
            """,
            project_id,
            result.message,
            nicole.model_name,
        )
        
        # Broadcast response
        await manager.broadcast_to_project(project_id, {
            "type": "chat",
            "message_id": response_id,
            "role": "assistant",
            "content": result.message,
            "agent": "nicole",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # If Nicole wants to route to an agent, notify
        if result.next_agent:
            await manager.broadcast_to_project(project_id, {
                "type": "routing",
                "next_agent": result.next_agent,
                "intent": result.data.get("intent", ""),
                "timestamp": datetime.utcnow().isoformat(),
            })
            
    except Exception as e:
        logger.exception(f"[Faz WS] Chat error: {e}")
        await manager.send_personal(websocket, {
            "type": "error",
            "message": f"Chat failed: {str(e)}",
        })


async def handle_run_pipeline(websocket: WebSocket, project_id: int, start_agent: str, user_id: int = None):
    """Handle pipeline run request via WebSocket."""
    try:
        # Get project (with ownership check if user_id provided)
        if user_id:
            project = await db.fetchrow(
                "SELECT * FROM faz_projects WHERE project_id = $1 AND user_id = $2",
                project_id,
                user_id,
            )
        else:
            project = await db.fetchrow(
                "SELECT * FROM faz_projects WHERE project_id = $1",
                project_id,
            )
        
        if not project:
            await manager.send_personal(websocket, {
                "type": "error",
                "message": "Project not found or access denied",
            })
            return
        
        # Update status
        await db.execute(
            "UPDATE faz_projects SET status = 'processing', updated_at = NOW() WHERE project_id = $1",
            project_id,
        )
        
        await manager.broadcast_to_project(project_id, {
            "type": "status",
            "status": "processing",
            "current_agent": start_agent,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Run pipeline
        from app.services.faz_orchestrator import FazOrchestrator
        
        orchestrator = FazOrchestrator(project_id, project["user_id"])
        
        # Set callback for real-time updates
        async def activity_callback(activity: Dict[str, Any]):
            await manager.broadcast_to_project(project_id, {
                "type": "activity",
                **activity,
            })
        
        orchestrator.set_activity_callback(activity_callback)
        
        # Run
        final_state = await orchestrator.run(
            project["original_prompt"],
            start_agent,
        )
        
        # Broadcast completion
        await manager.broadcast_to_project(project_id, {
            "type": "complete",
            "status": final_state.get("status", "completed"),
            "file_count": len(final_state.get("files", {})),
            "total_tokens": final_state.get("total_tokens", 0),
            "total_cost_cents": final_state.get("total_cost_cents", 0),
            "timestamp": datetime.utcnow().isoformat(),
        })
        
    except Exception as e:
        logger.exception(f"[Faz WS] Pipeline error: {e}")
        
        await db.execute(
            "UPDATE faz_projects SET status = 'failed', updated_at = NOW() WHERE project_id = $1",
            project_id,
        )
        
        await manager.broadcast_to_project(project_id, {
            "type": "error",
            "message": f"Pipeline failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
        })


# =============================================================================
# HTTP ENDPOINTS
# =============================================================================

@router.get("/projects/{project_id}/chat", response_model=List[ChatResponse])
async def get_chat_history(
    project_id: int,
    user = Depends(get_current_user),
    limit: int = 50,
):
    """Get chat history for a project."""
    try:
        # Verify access
        project = await db.fetchrow(
            "SELECT project_id FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        messages = await db.fetch(
            """
            SELECT message_id, role, content, agent_name, model_used, created_at
            FROM faz_conversations
            WHERE project_id = $1
            ORDER BY created_at
            LIMIT $2
            """,
            project_id,
            limit,
        )
        
        return [
            ChatResponse(
                message_id=m["message_id"],
                role=m["role"],
                content=m["content"],
                agent_name=m["agent_name"],
                model_used=m["model_used"],
                created_at=m["created_at"],
            )
            for m in messages
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to get chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def send_chat_message(
    project_id: int,
    request: ChatRequest,
    user = Depends(get_current_user),
):
    """Send a chat message (non-WebSocket fallback)."""
    try:
        # Verify access
        project = await db.fetchrow(
            "SELECT * FROM faz_projects WHERE project_id = $1 AND user_id = $2",
            project_id,
            user.user_id,
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Store message
        message_id = await db.fetchval(
            """
            INSERT INTO faz_conversations (project_id, role, content)
            VALUES ($1, 'user', $2)
            RETURNING message_id
            """,
            project_id,
            request.message,
        )
        
        # Generate response
        from app.services.faz_agents import NicoleAgent
        
        nicole = NicoleAgent()
        
        state = {
            "project_id": project_id,
            "original_prompt": project["original_prompt"],
            "current_prompt": request.message,
        }
        
        result = await nicole.run(state)
        
        # Store response
        response_id = await db.fetchval(
            """
            INSERT INTO faz_conversations (project_id, role, content, agent_name, model_used)
            VALUES ($1, 'assistant', $2, 'nicole', $3)
            RETURNING message_id
            """,
            project_id,
            result.message,
            nicole.model_name,
        )
        
        return ChatResponse(
            message_id=response_id,
            role="assistant",
            content=result.message,
            agent_name="nicole",
            model_used=nicole.model_name,
            created_at=datetime.utcnow(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Faz] Failed to send chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


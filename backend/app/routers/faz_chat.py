"""
Faz Code Chat Router

WebSocket and HTTP endpoints for real-time chat and activity streaming.
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging
import json
import asyncio
from datetime import datetime

from app.database import db
from app.middleware.alphawave_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faz", tags=["Faz Code Chat"])


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
):
    """
    WebSocket for real-time project updates.
    
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
    await manager.connect(websocket, project_id)
    
    # Start activity watcher
    activity_task = asyncio.create_task(watch_activities(websocket, project_id))
    
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
                        await handle_chat_message(websocket, project_id, message)
                
                elif msg_type == "run":
                    # Start pipeline
                    start_agent = data.get("start_agent", "nicole")
                    await handle_run_pipeline(websocket, project_id, start_agent)
                
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


async def handle_chat_message(websocket: WebSocket, project_id: int, message: str):
    """Handle incoming chat message."""
    try:
        # Store user message
        message_id = await db.fetchval(
            """
            INSERT INTO faz_conversations (project_id, role, content)
            VALUES ($1, 'user', $2)
            RETURNING message_id
            """,
            project_id,
            message,
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


async def handle_run_pipeline(websocket: WebSocket, project_id: int, start_agent: str):
    """Handle pipeline run request via WebSocket."""
    try:
        # Get project
        project = await db.fetchrow(
            "SELECT * FROM faz_projects WHERE project_id = $1",
            project_id,
        )
        
        if not project:
            await manager.send_personal(websocket, {
                "type": "error",
                "message": "Project not found",
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


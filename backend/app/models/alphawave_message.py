"""
Message model for persistent chat storage.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from datetime import datetime
from uuid import UUID


class AlphawaveMessage(BaseModel):
    """
    Message model for chat persistence.
    
    Attributes:
        id: Unique message identifier
        conversation_id: Parent conversation ID
        user_id: Message owner (who sent or received it)
        role: Message role (user or assistant)
        content: Message text content
        emotion: Optional emotion for TTS (happy, concerned, etc.)
        attachments: Optional JSON list of file attachments
        tool_calls: Optional JSON list of MCP tool calls made
        created_at: Message timestamp
    """
    
    id: UUID
    conversation_id: UUID
    user_id: UUID
    role: Literal["user", "assistant"]
    content: str
    emotion: Optional[str] = None
    attachments: Optional[dict[str, Any]] = Field(default_factory=dict)
    tool_calls: Optional[dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlphawaveMessageCreate(BaseModel):
    """Message creation model."""
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    emotion: Optional[str] = None
    attachments: Optional[dict[str, Any]] = Field(default_factory=dict)
    tool_calls: Optional[dict[str, Any]] = Field(default_factory=dict)


class AlphawaveMessageResponse(BaseModel):
    """Message response for API endpoints."""
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    emotion: Optional[str] = None
    attachments: Optional[dict[str, Any]] = None
    created_at: datetime


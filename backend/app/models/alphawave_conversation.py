"""
Conversation model for thread-based chat history.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class AlphawaveConversation(BaseModel):
    """
    Conversation thread model.
    
    Attributes:
        id: Unique conversation identifier
        user_id: Owner user ID
        title: Conversation title (auto-generated or user-set)
        knowledge_base_id: Optional link to project domain (Notion)
        created_at: Creation timestamp
        updated_at: Last message timestamp
    """
    
    id: UUID
    user_id: UUID
    title: str = Field(default="New Conversation")
    knowledge_base_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlphawaveConversationCreate(BaseModel):
    """Conversation creation model."""
    title: Optional[str] = Field(default="New Conversation")
    knowledge_base_id: Optional[UUID] = None


class AlphawaveConversationUpdate(BaseModel):
    """Conversation update model."""
    title: Optional[str] = None
    updated_at: Optional[datetime] = None


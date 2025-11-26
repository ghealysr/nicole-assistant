"""
User model for Nicole V7 multi-user system.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class AlphawaveUser(BaseModel):
    """
    User model representing one of 8 family members.
    
    Attributes:
        id: Unique user identifier (UUID)
        email: User email address
        full_name: User's full name
        role: User role (admin, child, parent, standard)
        relationship: Relationship to Glen (creator, son, nicoles_mother, etc.)
        image_limit_weekly: Weekly FLUX image generation limit
        created_at: Account creation timestamp
        last_active: Last activity timestamp
    """
    
    id: UUID
    email: EmailStr
    full_name: str
    role: Literal["admin", "child", "parent", "standard"]
    relationship: Literal[
        "creator", "son", "nicoles_mother", "nicoles_father",
        "friend", "partner", "family"
    ]
    image_limit_weekly: int = Field(default=5, ge=0)
    created_at: datetime
    last_active: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlphawaveUserCreate(BaseModel):
    """User creation model."""
    email: EmailStr
    full_name: str
    password: str
    role: Literal["admin", "child", "parent", "standard"] = "standard"
    relationship: Literal[
        "creator", "son", "nicoles_mother", "nicoles_father",
        "friend", "partner", "family"
    ]
    image_limit_weekly: int = Field(default=5, ge=0)


class AlphawaveUserUpdate(BaseModel):
    """User update model."""
    full_name: Optional[str] = None
    image_limit_weekly: Optional[int] = Field(default=None, ge=0)
    last_active: Optional[datetime] = None


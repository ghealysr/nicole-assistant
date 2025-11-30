"""
Tiger user service

Bridges Supabase-authenticated users to Tiger Postgres `users` table.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from app.database import db


class TigerUserService:
    """Utility for ensuring Tiger users exist for each authenticated email."""

    async def get_or_create_user(
        self,
        email: str,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        relationship: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not email:
            raise ValueError("Email is required to resolve Tiger user")

        email = email.lower().strip()

        async with db.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT * FROM users WHERE LOWER(email) = $1",
                email,
            )
            if existing:
                return dict(existing)

            full_name = full_name or email.split("@")[0].replace(".", " ").title()
            role = role or "standard"
            relationship = relationship or "friend"

            result = await conn.fetchrow(
                """
                INSERT INTO users (
                    email,
                    full_name,
                    role,
                    relationship,
                    preferences,
                    created_at,
                    last_active
                ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                RETURNING *
                """,
                email,
                full_name,
                role,
                relationship,
                {},
            )
            return dict(result)

    async def touch_user_activity(self, user_id: int) -> None:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_active = $1 WHERE user_id = $2",
                datetime.utcnow(),
                user_id,
            )


tiger_user_service = TigerUserService()


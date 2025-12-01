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

            # Use full_name or generate from email
            name = full_name or email.split("@")[0].replace(".", " ").title()
            
            # Map role to enum value
            role_mapping = {
                "admin": "admin",
                "standard": "user",
                "user": "user",
                "family": "family_member",
                "family_member": "family_member",
                "child": "child",
            }
            db_role = role_mapping.get(role or "user", "user")

            result = await conn.fetchrow(
                """
                INSERT INTO users (
                    email,
                    name,
                    user_role,
                    preferences,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3::user_role_enum, $4, NOW(), NOW())
                RETURNING *
                """,
                email,
                name,
                db_role,
                {},
            )
            return dict(result)

    async def touch_user_activity(self, user_id: int) -> None:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE users SET updated_at = $1 WHERE user_id = $2",
                datetime.utcnow(),
                user_id,
            )


tiger_user_service = TigerUserService()

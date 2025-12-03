"""
Persists structured skill run history to Tiger Postgres.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from app.config import settings
from app.database import db
from app.skills.execution import SkillExecutionResult
from app.skills.registry import SkillMetadata

logger = logging.getLogger(__name__)


class SkillRunService:
    """Stores skill run telemetry in the database."""

    def __init__(self):
        self.environment = settings.ENVIRONMENT

    async def record_success(
        self,
        skill_meta: SkillMetadata,
        result: SkillExecutionResult,
        user_id: int,
        conversation_id: Optional[int],
    ) -> None:
        """Persist a successful skill execution."""
        preview = (result.output or "")[:500]
        await db.execute(
            """
            INSERT INTO skill_runs (
                run_id,
                skill_id,
                user_id,
                conversation_id,
                status,
                environment,
                started_at,
                finished_at,
                duration_seconds,
                log_path,
                output_preview,
                error_message,
                created_at
            ) VALUES (
                $1::uuid,
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8,
                $9,
                $10,
                $11,
                NULL,
                NOW()
            )
            """,
            uuid.UUID(result.run_id),
            skill_meta.id,
            user_id,
            conversation_id,
            result.status,
            self.environment,
            result.started_at,
            result.finished_at,
            result.duration_seconds,
            str(result.log_file),
            preview,
        )

    async def record_failure(
        self,
        skill_meta: SkillMetadata,
        user_id: int,
        conversation_id: Optional[int],
        error_message: str,
    ) -> None:
        """Persist a failed skill execution (e.g., validation/runtime error)."""
        run_id = uuid.uuid4()
        now = datetime.utcnow()
        await db.execute(
            """
            INSERT INTO skill_runs (
                run_id,
                skill_id,
                user_id,
                conversation_id,
                status,
                environment,
                started_at,
                finished_at,
                duration_seconds,
                log_path,
                output_preview,
                error_message,
                created_at
            ) VALUES (
                $1::uuid,
                $2,
                $3,
                $4,
                'failed',
                $5,
                $6,
                $6,
                0,
                NULL,
                NULL,
                $7,
                NOW()
            )
            """,
            run_id,
            skill_meta.id,
            user_id,
            conversation_id,
            self.environment,
            now,
            error_message[:500],
        )
        logger.warning(f"[SKILL RUN] Recorded failure for {skill_meta.id}: {error_message}")


skill_run_service = SkillRunService()


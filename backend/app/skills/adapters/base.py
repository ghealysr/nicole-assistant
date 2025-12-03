from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, List

from app.skills.execution import SkillExecutionContext, SkillExecutionResult
from app.skills.registry import SkillMetadata


class SkillExecutionError(Exception):
    """Raised when a skill execution fails."""


class BaseSkillAdapter:
    """Base adapter providing common helpers for running skill commands."""

    def __init__(self, metadata: SkillMetadata, context: SkillExecutionContext):
        self.metadata = metadata
        self.context = context

    def prepare(self) -> None:
        """Optional hook called before execution."""

    def cleanup(self) -> None:
        """Optional hook called after execution."""

    def execute(self, payload: Dict[str, Any]) -> SkillExecutionResult:
        raise NotImplementedError

    def _build_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env.update(self.context.env)
        return env

    def _run_command(self, command: List[str], payload: Dict[str, Any]) -> SkillExecutionResult:
        env = self._build_env()
        env["SKILL_INPUT"] = json.dumps(payload)
        started = time.monotonic()

        log_file = self.context.log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with log_file.open("a") as log:
            log.write(f"$ {' '.join(command)}\n")
            try:
                proc = subprocess.run(
                    command,
                    cwd=self.context.working_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=self.context.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                log.write(f"[timeout] {exc}\n")
                raise SkillExecutionError("Skill execution timed out") from exc

            log.write(proc.stdout or "")
            log.write(proc.stderr or "")

        finished = time.monotonic()
        finished_at = datetime.utcnow()

        return SkillExecutionResult(
            skill_id=self.context.skill_id,
            run_id=self.context.run_id,
            status="success" if proc.returncode == 0 else "failed",
            return_code=proc.returncode,
            output=proc.stdout,
            error=proc.stderr,
            log_file=log_file,
            started_at=self.context.start_time,
            finished_at=finished_at,
            duration_seconds=finished - started,
            metadata={},
        )


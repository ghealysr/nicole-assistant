"""
Skill runner orchestrates execution adapters.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4

from app.skills.registry import load_registry, SkillMetadata
from app.skills.execution import SkillExecutionContext, SkillExecutionResult
from app.skills.adapters import (
    PythonSkillAdapter,
    NodeSkillAdapter,
    CLISkillAdapter,
)
from app.skills.adapters.base import SkillExecutionError, BaseSkillAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = PROJECT_ROOT / "skills"
LOGS_ROOT = SKILLS_ROOT / "logs"
REGISTRY_PATH = SKILLS_ROOT / "registry.json"


class SkillRunner:
    """Executes installed skills safely."""

    def __init__(self):
        LOGS_ROOT.mkdir(parents=True, exist_ok=True)
        self.registry = load_registry(REGISTRY_PATH)

    def _select_adapter(self, metadata: SkillMetadata, context: SkillExecutionContext) -> BaseSkillAdapter:
        executor_type = metadata.executor.executor_type.lower()
        if executor_type in {"python", "python_script"}:
            return PythonSkillAdapter(metadata, context)
        if executor_type in {"node", "node_script"}:
            return NodeSkillAdapter(metadata, context)
        if executor_type in {"cli", "command"}:
            return CLISkillAdapter(metadata, context)
        raise SkillExecutionError(f"Unsupported executor type '{executor_type}' for skill {metadata.id}")

    def _prepare_working_dir(self, metadata: SkillMetadata) -> Path:
        if not metadata.install_path:
            raise SkillExecutionError("Skill missing install_path")
        install_dir = PROJECT_ROOT / metadata.install_path
        if not install_dir.exists():
            raise SkillExecutionError(f"Install directory not found: {install_dir}")

        temp_root = Path(tempfile.mkdtemp(prefix=f"skill-run-{metadata.id}-"))
        work_dir = temp_root / install_dir.name
        shutil.copytree(install_dir, work_dir)
        return work_dir

    def _create_context(
        self,
        metadata: SkillMetadata,
        user_id: int,
        conversation_id: Optional[int],
        timeout_override: Optional[int],
    ) -> SkillExecutionContext:
        run_id = uuid4().hex
        working_dir = self._prepare_working_dir(metadata)
        log_dir = LOGS_ROOT / metadata.id
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.utcnow().isoformat()}.{run_id}.log"
        timeout = timeout_override or metadata.executor.timeout_seconds or 300
        env = metadata.executor.env or {}
        return SkillExecutionContext(
            skill_id=metadata.id,
            user_id=user_id,
            conversation_id=conversation_id,
            run_id=run_id,
            working_dir=working_dir,
            log_file=log_file,
            timeout_seconds=timeout,
            env=env,
        )

    async def run(
        self,
        skill_id: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        user_id: int,
        conversation_id: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> SkillExecutionResult:
        """Execute a skill asynchronously."""
        payload = payload or {}
        self.registry.load()
        metadata = self.registry.get_skill(skill_id)
        if not metadata:
            raise SkillExecutionError(f"Skill '{skill_id}' not found")

        context = self._create_context(metadata, user_id, conversation_id, timeout)
        adapter = self._select_adapter(metadata, context)

        def _execute():
            adapter.prepare()
            try:
                return adapter.execute(payload)
            finally:
                adapter.cleanup()
                shutil.rmtree(context.working_dir.parent, ignore_errors=True)

        return await asyncio.to_thread(_execute)


skill_runner = SkillRunner()


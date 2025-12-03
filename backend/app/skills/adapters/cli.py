from __future__ import annotations

import shlex
from typing import Dict, Any

from app.skills.adapters.base import BaseSkillAdapter, SkillExecutionError


class CLISkillAdapter(BaseSkillAdapter):
    """Executes generic CLI commands defined by the skill."""

    def execute(self, payload: Dict[str, Any]):
        entrypoint = self.metadata.executor.entrypoint
        if not entrypoint:
            raise SkillExecutionError("CLI skill missing executor entrypoint")
        command = shlex.split(entrypoint)
        return self._run_command(command, payload)


from __future__ import annotations

import shlex
from typing import Dict, Any, List

from app.skills.adapters.base import BaseSkillAdapter, SkillExecutionError


class PythonSkillAdapter(BaseSkillAdapter):
    """Executes Python-based skills."""

    def execute(self, payload: Dict[str, Any]):
        entrypoint = self.metadata.executor.entrypoint or "main.py"
        command = ["python3"] + shlex.split(entrypoint)
        return self._run_command(command, payload)


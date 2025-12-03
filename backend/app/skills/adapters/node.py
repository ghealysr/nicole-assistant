from __future__ import annotations

import shlex
from typing import Dict, Any

from app.skills.adapters.base import BaseSkillAdapter


class NodeSkillAdapter(BaseSkillAdapter):
    """Executes Node.js based skills."""

    def execute(self, payload: Dict[str, Any]):
        entrypoint = self.metadata.executor.entrypoint or "index.js"
        command = ["node"] + shlex.split(entrypoint)
        return self._run_command(command, payload)


"""
Execution context and result models for skill runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class SkillExecutionContext:
    """Carries runtime metadata for a skill execution."""

    skill_id: str
    user_id: int
    conversation_id: Optional[int]
    run_id: str
    working_dir: Path
    log_file: Path
    timeout_seconds: int
    env: Dict[str, str] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SkillExecutionResult:
    """Normalized result returned to Nicole after executing a skill."""

    skill_id: str
    run_id: str
    status: str  # success, failed
    return_code: int
    output: Optional[str]
    error: Optional[str]
    log_file: Path
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)


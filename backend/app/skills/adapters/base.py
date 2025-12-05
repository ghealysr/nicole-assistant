"""
Nicole V7 - Base Skill Adapter

PURPOSE:
    Provides secure, isolated command execution for skills with:
    - Environment variable filtering (prevents secret leakage)
    - PII redaction in logs
    - Timeout enforcement
    - Structured result reporting

SECURITY:
    - Only allowlisted env vars are passed to skills
    - Skill-specific env vars from manifest are added
    - Sensitive patterns in output are redacted before logging
    - Working directory is isolated (temp copy)

Author: Nicole V7 Skills System
Date: December 5, 2025
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, List, Set

from app.skills.execution import SkillExecutionContext, SkillExecutionResult
from app.skills.registry import SkillMetadata


class SkillExecutionError(Exception):
    """Raised when a skill execution fails."""


# Environment variables that are SAFE to pass to skills
# Everything else is blocked by default
ENV_ALLOWLIST: Set[str] = {
    # System
    "PATH",
    "HOME",
    "USER",
    "SHELL",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TZ",
    
    # Python
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONUNBUFFERED",
    "VIRTUAL_ENV",
    
    # Node
    "NODE_ENV",
    "NODE_PATH",
    "NPM_CONFIG_PREFIX",
    
    # General dev
    "TMPDIR",
    "TEMP",
    "TMP",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
}

# Patterns to BLOCK from env var names (case-insensitive)
ENV_BLOCKLIST_PATTERNS = [
    r".*KEY.*",
    r".*SECRET.*",
    r".*TOKEN.*",
    r".*PASSWORD.*",
    r".*CREDENTIAL.*",
    r".*AUTH.*",
    r".*API.*",
    r".*DATABASE.*",
    r".*DB_.*",
    r".*REDIS.*",
    r".*SUPABASE.*",
    r".*TIGER.*",
    r".*AWS.*",
    r".*AZURE.*",
    r".*GCP.*",
    r".*GOOGLE.*",
    r".*OPENAI.*",
    r".*ANTHROPIC.*",
    r".*CLAUDE.*",
    r".*REPLICATE.*",
    r".*ELEVENLABS.*",
    r".*STRIPE.*",
    r".*TWILIO.*",
    r".*SENDGRID.*",
    r".*SLACK.*",
    r".*DISCORD.*",
    r".*GITHUB.*",
    r".*GITLAB.*",
    r".*NOTION.*",
    r".*PRIVATE.*",
]

# Compile blocklist patterns
_BLOCKLIST_COMPILED = [re.compile(p, re.IGNORECASE) for p in ENV_BLOCKLIST_PATTERNS]

# Patterns to redact from log output
LOG_REDACT_PATTERNS = [
    (re.compile(r'(api[_-]?key|apikey)["\s:=]+["\']?[\w\-]+["\']?', re.I), r'\1=***'),
    (re.compile(r'(password|passwd|pwd)["\s:=]+["\']?[^\s"\']+["\']?', re.I), r'\1=***'),
    (re.compile(r'(secret|token|bearer)["\s:=]+["\']?[\w\-\.]+["\']?', re.I), r'\1=***'),
    (re.compile(r'(authorization)["\s:]+["\']?bearer\s+[\w\-\.]+["\']?', re.I), r'\1: ***'),
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '***@***.***'),
    (re.compile(r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*'), '***JWT***'),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), 'sk-***'),
    (re.compile(r'ghp_[A-Za-z0-9]{36,}'), 'ghp_***'),
    (re.compile(r'gho_[A-Za-z0-9]{36,}'), 'gho_***'),
]


def _is_env_blocked(name: str) -> bool:
    """Check if an env var name matches any blocklist pattern."""
    for pattern in _BLOCKLIST_COMPILED:
        if pattern.match(name):
            return True
    return False


def _redact_log_content(text: str) -> str:
    """Redact sensitive patterns from log content."""
    if not text:
        return text
    
    result = text
    for pattern, replacement in LOG_REDACT_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class BaseSkillAdapter:
    """
    Base adapter providing secure command execution for skills.
    
    Security Features:
    - Environment filtering: Only allowlisted vars passed
    - Log redaction: Sensitive patterns masked
    - Timeout enforcement: Prevents runaway processes
    - Isolated working directory: Skills run in temp copy
    """

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
        """
        Build a filtered environment for skill execution.
        
        Security Policy:
        1. Start with empty env (not os.environ.copy())
        2. Add only allowlisted system vars
        3. Add skill-specific vars from manifest
        4. Add SKILL_* vars for skill communication
        
        Returns:
            Filtered environment dictionary
        """
        env = {}
        
        # Add allowlisted vars from current environment
        for var in ENV_ALLOWLIST:
            if var in os.environ:
                env[var] = os.environ[var]
        
        # Add skill-specific vars from manifest (these are explicitly declared)
        if self.context.env:
            for key, value in self.context.env.items():
                # Skip if it matches a blocklist pattern (safety check)
                if not _is_env_blocked(key):
                    env[key] = value
        
        return env

    def _run_command(self, command: List[str], payload: Dict[str, Any]) -> SkillExecutionResult:
        """
        Execute a command with security controls.
        
        Args:
            command: Command and arguments to execute
            payload: JSON payload passed via SKILL_INPUT env var
            
        Returns:
            SkillExecutionResult with status, output, and timing
        """
        env = self._build_env()
        
        # Add skill communication vars
        env["SKILL_INPUT"] = json.dumps(payload)
        env["SKILL_ID"] = self.context.skill_id
        env["SKILL_RUN_ID"] = self.context.run_id
        
        started = time.monotonic()

        log_file = self.context.log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with log_file.open("a") as log:
            # Log command (safe to show)
            log.write(f"[{datetime.utcnow().isoformat()}] Running: {' '.join(command)}\n")
            log.write(f"[Working Dir] {self.context.working_dir}\n")
            log.write(f"[Timeout] {self.context.timeout_seconds}s\n")
            log.write("-" * 40 + "\n")
            
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
                log.write(f"\n[TIMEOUT] Execution exceeded {self.context.timeout_seconds}s\n")
                raise SkillExecutionError(
                    f"Skill execution timed out after {self.context.timeout_seconds} seconds. "
                    "Consider increasing timeout_seconds in the skill manifest."
                ) from exc
            except FileNotFoundError as exc:
                log.write(f"\n[ERROR] Command not found: {command[0]}\n")
                raise SkillExecutionError(
                    f"Command '{command[0]}' not found. "
                    "Ensure the required runtime is installed."
                ) from exc
            except PermissionError as exc:
                log.write(f"\n[ERROR] Permission denied: {command[0]}\n")
                raise SkillExecutionError(
                    f"Permission denied executing '{command[0]}'. "
                    "Check file permissions on the entrypoint."
                ) from exc

            # Redact and log output
            redacted_stdout = _redact_log_content(proc.stdout or "")
            redacted_stderr = _redact_log_content(proc.stderr or "")
            
            log.write("-" * 40 + "\n")
            log.write("[STDOUT]\n")
            log.write(redacted_stdout)
            
            if redacted_stderr:
                log.write("\n[STDERR]\n")
                log.write(redacted_stderr)
            
            log.write(f"\n[Exit Code] {proc.returncode}\n")

        finished = time.monotonic()
        finished_at = datetime.utcnow()

        status = "success" if proc.returncode == 0 else "failed"
        
        return SkillExecutionResult(
            skill_id=self.context.skill_id,
            run_id=self.context.run_id,
            status=status,
            return_code=proc.returncode,
            output=proc.stdout,  # Original output (redaction happens at logging/DB layer)
            error=proc.stderr,
            log_file=log_file,
            started_at=self.context.start_time,
            finished_at=finished_at,
            duration_seconds=finished - started,
            metadata={
                "command": command,
                "env_vars_passed": len(env),
            },
        )

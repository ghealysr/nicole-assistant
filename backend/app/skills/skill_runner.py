"""
Nicole V7 - Skill Runner

PURPOSE:
    Orchestrates safe execution of installed skills with:
    - Runtime environment validation
    - GPU availability checking
    - Working directory isolation
    - Adapter selection based on executor type

SECURITY:
    - Skills run in temporary copied directories
    - Environment variables are filtered by adapters
    - Timeouts are enforced
    - Logs are captured and stored

RUNTIME REQUIREMENTS:
    - GPU skills only run if GPU is available
    - Node skills require Node.js installed
    - Python skills use isolated venvs (when configured)

Author: Nicole V7 Skills System
Date: December 5, 2025
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from uuid import uuid4
import logging

from app.skills.registry import load_registry, SkillMetadata
from app.skills.execution import SkillExecutionContext, SkillExecutionResult
from app.skills.adapters import (
    PythonSkillAdapter,
    NodeSkillAdapter,
    CLISkillAdapter,
)
from app.skills.adapters.base import SkillExecutionError, BaseSkillAdapter

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = PROJECT_ROOT / "skills"
LOGS_ROOT = SKILLS_ROOT / "logs"
REGISTRY_PATH = SKILLS_ROOT / "registry.json"

# Executor types that can be run automatically
EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}


class RuntimeChecker:
    """
    Validates runtime requirements before skill execution.
    
    Checks:
    - GPU availability (CUDA/MPS)
    - Required runtimes (Python, Node.js)
    - Memory constraints
    """
    
    _gpu_available: Optional[bool] = None
    _node_available: Optional[bool] = None
    _python_available: bool = True  # Always available (we're running Python)
    
    @classmethod
    def check_gpu(cls) -> Tuple[bool, str]:
        """
        Check if GPU is available for compute tasks.
        
        Returns:
            Tuple of (available, details_message)
        """
        if cls._gpu_available is not None:
            return cls._gpu_available, "cached"
        
        # Check NVIDIA GPU (CUDA)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                cls._gpu_available = True
                return True, f"NVIDIA GPU: {result.stdout.strip().split(chr(10))[0]}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check Apple Metal (MPS)
        try:
            import platform
            if platform.system() == "Darwin":
                # Check for Metal support on macOS
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if "Metal" in result.stdout:
                    cls._gpu_available = True
                    return True, "Apple Metal GPU available"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        cls._gpu_available = False
        return False, "No GPU detected (CUDA/Metal)"
    
    @classmethod
    def check_node(cls) -> Tuple[bool, str]:
        """
        Check if Node.js is available.
        
        Returns:
            Tuple of (available, version_or_error)
        """
        if cls._node_available is not None:
            return cls._node_available, "cached"
        
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                cls._node_available = True
                return True, f"Node.js {version}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        cls._node_available = False
        return False, "Node.js not installed"
    
    @classmethod
    def validate_runtime(cls, metadata: SkillMetadata) -> Tuple[bool, Optional[str]]:
        """
        Validate that all runtime requirements are met.
        
        Args:
            metadata: Skill metadata with runtime requirements
            
        Returns:
            Tuple of (valid, error_message_if_invalid)
        """
        executor_type = metadata.executor.executor_type.lower()
        
        # Check GPU requirement
        if metadata.executor.requires_gpu:
            gpu_ok, gpu_msg = cls.check_gpu()
            if not gpu_ok:
                return False, (
                    f"Skill '{metadata.id}' requires GPU but none available. "
                    f"Details: {gpu_msg}. "
                    "Install CUDA drivers or run on a GPU-enabled machine."
                )
            logger.info(f"[RUNTIME] GPU check passed for {metadata.id}: {gpu_msg}")
        
        # Check Node.js for Node skills
        if executor_type in {"node", "node_script"}:
            node_ok, node_msg = cls.check_node()
            if not node_ok:
                return False, (
                    f"Skill '{metadata.id}' requires Node.js but it's not installed. "
                    "Install Node.js: https://nodejs.org/"
                )
            logger.info(f"[RUNTIME] Node.js check passed for {metadata.id}: {node_msg}")
        
        return True, None


class SkillRunner:
    """
    Executes installed skills safely with full validation.
    
    Features:
    - Runtime requirement validation (GPU, Node.js)
    - Working directory isolation
    - Timeout enforcement
    - Comprehensive logging
    """

    def __init__(self):
        LOGS_ROOT.mkdir(parents=True, exist_ok=True)
        self.registry = load_registry(REGISTRY_PATH)
        logger.info("[SKILL RUNNER] Initialized")

    # Expose EXECUTABLE_TYPES for other modules
    EXECUTABLE_TYPES = EXECUTABLE_TYPES

    def _select_adapter(self, metadata: SkillMetadata, context: SkillExecutionContext) -> BaseSkillAdapter:
        """Select the appropriate adapter based on executor type."""
        executor_type = metadata.executor.executor_type.lower()
        
        if executor_type in {"python", "python_script"}:
            return PythonSkillAdapter(metadata, context)
        if executor_type in {"node", "node_script"}:
            return NodeSkillAdapter(metadata, context)
        if executor_type in {"cli", "command"}:
            return CLISkillAdapter(metadata, context)
        
        raise SkillExecutionError(
            f"Unsupported executor type '{executor_type}' for skill {metadata.id}. "
            f"Supported types: {', '.join(EXECUTABLE_TYPES)}"
        )

    def _prepare_working_dir(self, metadata: SkillMetadata) -> Path:
        """
        Create an isolated working directory for skill execution.
        
        Copies the skill's installation directory to a temp location
        to prevent side effects from skill execution.
        """
        if not metadata.install_path:
            raise SkillExecutionError(
                f"Skill '{metadata.id}' missing install_path. "
                "Re-import the skill or check registry.json."
            )
        
        install_dir = PROJECT_ROOT / metadata.install_path
        if not install_dir.exists():
            raise SkillExecutionError(
                f"Skill '{metadata.id}' installation directory not found: {install_dir}. "
                "The skill files may have been deleted. Re-import the skill."
            )

        temp_root = Path(tempfile.mkdtemp(prefix=f"skill-run-{metadata.id}-"))
        work_dir = temp_root / install_dir.name
        
        try:
            shutil.copytree(install_dir, work_dir)
            logger.debug(f"[SKILL RUNNER] Created working dir: {work_dir}")
        except Exception as e:
            raise SkillExecutionError(
                f"Failed to create working directory for skill '{metadata.id}': {e}"
            )
        
        return work_dir

    def _create_context(
        self,
        metadata: SkillMetadata,
        user_id: int,
        conversation_id: Optional[int],
        timeout_override: Optional[int],
    ) -> SkillExecutionContext:
        """Create execution context with all necessary parameters."""
        run_id = uuid4().hex
        working_dir = self._prepare_working_dir(metadata)
        
        log_dir = LOGS_ROOT / metadata.id
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{run_id[:8]}.log"
        
        # Use override, or skill timeout, or default 300s
        timeout = timeout_override or metadata.executor.timeout_seconds or 300
        
        # Environment vars from skill manifest (will be filtered by adapter)
        env = dict(metadata.executor.env or {})
        
        return SkillExecutionContext(
            skill_id=metadata.id,
            user_id=user_id,
            conversation_id=conversation_id,
            run_id=run_id,
            working_dir=working_dir,
            log_file=log_file,
            timeout_seconds=timeout,
            env=env,
            start_time=datetime.utcnow(),
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
        """
        Execute a skill asynchronously with full validation.
        
        Args:
            skill_id: ID of the skill to execute
            payload: JSON payload to pass to the skill
            user_id: User triggering execution
            conversation_id: Associated conversation (optional)
            timeout: Override default timeout (seconds)
            
        Returns:
            SkillExecutionResult with status, output, logs
            
        Raises:
            SkillExecutionError: If validation fails or execution errors
        """
        payload = payload or {}
        
        # Reload registry to get latest state
        self.registry.load()
        metadata = self.registry.get_skill(skill_id)
        
        if not metadata:
            raise SkillExecutionError(
                f"Skill '{skill_id}' not found in registry. "
                "Check the skill ID or import it first."
            )
        
        # Validate executor type
        executor_type = metadata.executor.executor_type.lower()
        if executor_type not in EXECUTABLE_TYPES:
            raise SkillExecutionError(
                f"Skill '{skill_id}' has executor type '{executor_type}' which cannot be run automatically. "
                "This is a manual skill - refer to its documentation for usage."
            )
        
        # Validate runtime requirements
        runtime_ok, runtime_error = RuntimeChecker.validate_runtime(metadata)
        if not runtime_ok:
            raise SkillExecutionError(runtime_error)
        
        # Create execution context
        context = self._create_context(metadata, user_id, conversation_id, timeout)
        
        # Select and run adapter
        adapter = self._select_adapter(metadata, context)
        
        logger.info(
            f"[SKILL RUNNER] Executing {skill_id} "
            f"(user={user_id}, run={context.run_id[:8]}, timeout={context.timeout_seconds}s)"
        )

        def _execute():
            adapter.prepare()
            try:
                result = adapter.execute(payload)
                logger.info(
                    f"[SKILL RUNNER] {skill_id} completed: status={result.status}, "
                    f"duration={result.duration_seconds:.2f}s"
                )
                return result
            finally:
                adapter.cleanup()
                # Clean up temp directory
                try:
                    shutil.rmtree(context.working_dir.parent, ignore_errors=True)
                except Exception as cleanup_err:
                    logger.warning(f"[SKILL RUNNER] Cleanup warning: {cleanup_err}")

        return await asyncio.to_thread(_execute)


# Global skill runner instance
skill_runner = SkillRunner()

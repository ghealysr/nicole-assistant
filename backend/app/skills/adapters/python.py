"""
Nicole V7 - Python Skill Adapter

PURPOSE:
    Executes Python-based skills with optional venv isolation:
    - Creates per-skill virtual environment for dependency isolation
    - Auto-installs requirements.txt if present
    - Falls back to system Python if isolation disabled
    - Caches venvs for performance

ISOLATION MODES:
    1. ISOLATED (default): Creates skill-specific venv
       - Safe for untrusted skills
       - Prevents dependency conflicts
       - Slightly slower first run (venv creation)
    
    2. SHARED: Uses system Python
       - Faster execution
       - Only for trusted internal skills
       - Risk of dependency conflicts

USAGE:
    The adapter automatically:
    1. Checks for existing skill venv
    2. Creates venv if needed
    3. Installs requirements.txt
    4. Executes with isolated Python

Author: Nicole V7 Skills System
Date: December 5, 2025
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from app.skills.adapters.base import BaseSkillAdapter, SkillExecutionError

logger = logging.getLogger(__name__)

# Directory for skill virtual environments
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SKILL_VENVS_DIR = PROJECT_ROOT / "skills" / ".venvs"

# Skills that are trusted and can run without isolation
TRUSTED_VENDORS = {"local", "internal", "nicole"}


class PythonSkillAdapter(BaseSkillAdapter):
    """
    Executes Python-based skills with dependency isolation.
    
    Features:
    - Per-skill virtual environment
    - Automatic requirements.txt installation
    - Venv caching for performance
    - Fallback to system Python for trusted skills
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._venv_path: Optional[Path] = None
        self._python_path: Optional[str] = None
        self._use_isolation = self._should_isolate()

    def _should_isolate(self) -> bool:
        """
        Determine if this skill should run in isolation.
        
        Isolation is enabled unless:
        - Skill vendor is in TRUSTED_VENDORS
        - Skill has no external dependencies (no requirements.txt)
        - Skill manifest explicitly sets requires_isolation: false
        """
        # Check vendor trust
        if self.metadata.vendor.lower() in TRUSTED_VENDORS:
            return False
        
        # Check for dependencies
        if self.metadata.install_path:
            install_dir = PROJECT_ROOT / self.metadata.install_path
            if (install_dir / "requirements.txt").exists():
                return True
        
        # Default: isolate external skills
        return True

    def _get_venv_path(self) -> Path:
        """Get the path to this skill's virtual environment."""
        # Use skill ID as venv name (sanitized)
        safe_name = self.metadata.id.replace("/", "-").replace("\\", "-")
        return SKILL_VENVS_DIR / safe_name

    def _venv_exists(self) -> bool:
        """Check if the skill's venv already exists and is valid."""
        venv_path = self._get_venv_path()
        python_path = venv_path / "bin" / "python"
        return python_path.exists()

    def _create_venv(self) -> Path:
        """
        Create a virtual environment for this skill.
        
        Returns:
            Path to the created venv
            
        Raises:
            SkillExecutionError if venv creation fails
        """
        venv_path = self._get_venv_path()
        
        logger.info(f"[PYTHON ADAPTER] Creating venv for {self.metadata.id} at {venv_path}")
        
        try:
            # Ensure parent directory exists
            SKILL_VENVS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create venv using current Python
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                raise SkillExecutionError(
                    f"Failed to create virtual environment: {result.stderr}"
                )
            
            logger.info(f"[PYTHON ADAPTER] Venv created: {venv_path}")
            return venv_path
            
        except subprocess.TimeoutExpired:
            raise SkillExecutionError("Venv creation timed out (60s)")
        except Exception as e:
            raise SkillExecutionError(f"Venv creation failed: {e}")

    def _install_requirements(self, venv_path: Path) -> None:
        """
        Install requirements.txt into the skill's venv.
        
        Args:
            venv_path: Path to the virtual environment
            
        Raises:
            SkillExecutionError if installation fails
        """
        if not self.metadata.install_path:
            return
        
        install_dir = PROJECT_ROOT / self.metadata.install_path
        requirements_file = install_dir / "requirements.txt"
        
        if not requirements_file.exists():
            logger.debug(f"[PYTHON ADAPTER] No requirements.txt for {self.metadata.id}")
            return
        
        pip_path = venv_path / "bin" / "pip"
        
        logger.info(f"[PYTHON ADAPTER] Installing requirements for {self.metadata.id}")
        
        try:
            result = subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_file), "-q"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for pip install
                cwd=install_dir,
            )
            
            if result.returncode != 0:
                logger.warning(
                    f"[PYTHON ADAPTER] pip install warnings/errors: {result.stderr}"
                )
                # Don't fail on pip warnings, only on critical errors
                if "error" in result.stderr.lower() and "warning" not in result.stderr.lower():
                    raise SkillExecutionError(
                        f"Failed to install requirements: {result.stderr[:200]}"
                    )
            
            logger.info(f"[PYTHON ADAPTER] Requirements installed for {self.metadata.id}")
            
        except subprocess.TimeoutExpired:
            raise SkillExecutionError(
                "Dependency installation timed out (300s). "
                "The skill may have too many dependencies."
            )

    def _get_python_executable(self) -> str:
        """
        Get the Python executable to use for this skill.
        
        Returns:
            Path to Python executable (venv or system)
        """
        if self._python_path:
            return self._python_path
        
        if not self._use_isolation:
            # Use system Python for trusted skills
            self._python_path = sys.executable
            return self._python_path
        
        venv_path = self._get_venv_path()
        
        # Create venv if it doesn't exist
        if not self._venv_exists():
            self._create_venv()
            self._install_requirements(venv_path)
        
        self._python_path = str(venv_path / "bin" / "python")
        return self._python_path

    def prepare(self) -> None:
        """
        Prepare the execution environment.
        
        This is called before execute() and handles:
        - Venv creation if needed
        - Dependency installation
        """
        if self._use_isolation:
            # Pre-create venv and install deps
            # This separates prep time from execution time
            self._get_python_executable()

    def execute(self, payload: Dict[str, Any]):
        """
        Execute the Python skill.
        
        Args:
            payload: JSON payload passed to the skill
            
        Returns:
            SkillExecutionResult with execution details
        """
        python_exe = self._get_python_executable()
        entrypoint = self.metadata.executor.entrypoint or "main.py"
        
        # Build command with the appropriate Python
        command = [python_exe] + shlex.split(entrypoint)
        
        return self._run_command(command, payload)

    def cleanup(self) -> None:
        """
        Cleanup after execution.
        
        Note: We don't delete the venv here as it's cached for future runs.
        Venv cleanup should be handled by a separate maintenance job.
        """
        pass

    @classmethod
    def cleanup_venv(cls, skill_id: str) -> bool:
        """
        Delete a skill's virtual environment.
        
        Use this when:
        - Skill is uninstalled
        - Venv is corrupted
        - Forcing dependency reinstall
        
        Args:
            skill_id: ID of the skill
            
        Returns:
            True if venv was deleted
        """
        import shutil
        
        safe_name = skill_id.replace("/", "-").replace("\\", "-")
        venv_path = SKILL_VENVS_DIR / safe_name
        
        if venv_path.exists():
            try:
                shutil.rmtree(venv_path)
                logger.info(f"[PYTHON ADAPTER] Deleted venv for {skill_id}")
                return True
            except Exception as e:
                logger.error(f"[PYTHON ADAPTER] Failed to delete venv: {e}")
                return False
        
        return False

    @classmethod
    def list_venvs(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all skill virtual environments.
        
        Returns:
            Dict mapping skill_id to venv info
        """
        result = {}
        
        if not SKILL_VENVS_DIR.exists():
            return result
        
        for venv_dir in SKILL_VENVS_DIR.iterdir():
            if venv_dir.is_dir():
                python_path = venv_dir / "bin" / "python"
                result[venv_dir.name] = {
                    "path": str(venv_dir),
                    "valid": python_path.exists(),
                    "size_mb": sum(
                        f.stat().st_size for f in venv_dir.rglob("*") if f.is_file()
                    ) / (1024 * 1024),
                }
        
        return result

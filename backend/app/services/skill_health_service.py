"""
Nicole V7 - Skill Health Check Service

PURPOSE:
    Provides automated and on-demand health verification for installed skills.
    Ensures skills are properly configured, dependencies are installed, and
    basic execution tests pass before marking skills as "ready".

HEALTH CHECK PROCESS:
    1. Verify skill files exist at install_path
    2. Verify entrypoint file exists (for executable skills)
    3. Check for unmet dependencies (requirements.txt, package.json)
    4. Optionally run skill's test suite
    5. Update setup_status based on results

SETUP STATUS TRANSITIONS:
    needs_configuration → ready (after config verified)
    needs_verification → ready (after health check passes)
    ready → failed (if health check fails)
    failed → ready (after issue resolved and recheck passes)
    manual_only → manual_only (never changes - not executable)

USAGE:
    # Check single skill
    result = await skill_health_service.check_skill("my-skill-id")
    
    # Check all skills
    results = await skill_health_service.check_all_skills()
    
    # Mark skill as ready (admin action)
    await skill_health_service.mark_ready("my-skill-id")

Author: Nicole V7 Skills System
Date: December 5, 2025
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.skills.registry import load_registry, SkillMetadata, SkillRegistry

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = PROJECT_ROOT / "skills"
REGISTRY_PATH = SKILLS_ROOT / "registry.json"

# Executor types that can be programmatically executed
EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}


@dataclass
class HealthCheckResult:
    """Result of a skill health check."""
    skill_id: str
    skill_name: str
    previous_status: str
    new_status: str
    passed: bool
    checks_performed: List[str] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "passed": self.passed,
            "checks_performed": self.checks_performed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "notes": self.notes,
            "timestamp": self.timestamp,
        }


class SkillHealthService:
    """
    Service for verifying and managing skill health status.
    
    Responsibilities:
    1. Verify skill installation integrity
    2. Check dependency availability
    3. Run basic validation tests
    4. Update setup_status based on results
    5. Record health check history
    """
    
    def __init__(self):
        self.registry: Optional[SkillRegistry] = None
        logger.info("[SKILL HEALTH] Service initialized")
    
    def _get_registry(self) -> SkillRegistry:
        """Get or reload the skill registry."""
        if self.registry is None:
            self.registry = load_registry(REGISTRY_PATH)
        else:
            self.registry.load()
        return self.registry
    
    async def check_skill(
        self,
        skill_id: str,
        run_tests: bool = False,
        auto_install_deps: bool = False,
    ) -> HealthCheckResult:
        """
        Perform comprehensive health check on a single skill.
        
        Args:
            skill_id: The skill to check
            run_tests: If True, run the skill's test suite
            auto_install_deps: If True, attempt to install missing dependencies
            
        Returns:
            HealthCheckResult with detailed check outcomes
        """
        registry = self._get_registry()
        skill = registry.get_skill(skill_id)
        
        if not skill:
            return HealthCheckResult(
                skill_id=skill_id,
                skill_name="Unknown",
                previous_status="not_found",
                new_status="not_found",
                passed=False,
                notes=[f"Skill '{skill_id}' not found in registry"],
            )
        
        result = HealthCheckResult(
            skill_id=skill_id,
            skill_name=skill.name,
            previous_status=getattr(skill, 'setup_status', 'unknown'),
            new_status=skill.setup_status,
            passed=True,
        )
        
        exec_type = skill.executor.executor_type.lower()
        
        # Manual skills are always "manual_only" - no checks needed
        if exec_type not in EXECUTABLE_TYPES:
            result.new_status = "manual_only"
            result.notes.append("Manual skill - no automated health checks applicable")
            result.passed = True
            await self._update_skill_health(skill, result)
            return result
        
        # Check 1: Installation directory exists
        result.checks_performed.append("install_directory")
        if skill.install_path:
            install_dir = PROJECT_ROOT / skill.install_path
            if install_dir.exists():
                result.checks_passed.append("install_directory")
            else:
                result.checks_failed.append("install_directory")
                result.notes.append(f"Install directory not found: {skill.install_path}")
                result.passed = False
        else:
            result.checks_failed.append("install_directory")
            result.notes.append("No install_path specified")
            result.passed = False
        
        # Check 2: Entrypoint exists
        if result.passed and skill.executor.entrypoint:
            result.checks_performed.append("entrypoint")
            install_dir = PROJECT_ROOT / skill.install_path
            entrypoint_file = skill.executor.entrypoint.split()[0]  # Get first word (filename)
            entrypoint_path = install_dir / entrypoint_file
            
            if entrypoint_path.exists():
                result.checks_passed.append("entrypoint")
            else:
                result.checks_failed.append("entrypoint")
                result.notes.append(f"Entrypoint not found: {entrypoint_file}")
                result.passed = False
        
        # Check 3: Dependencies
        if result.passed and skill.install_path:
            install_dir = PROJECT_ROOT / skill.install_path
            
            # Python dependencies
            requirements_txt = install_dir / "requirements.txt"
            if requirements_txt.exists():
                result.checks_performed.append("python_dependencies")
                deps_ok = await self._check_python_deps(requirements_txt, auto_install_deps)
                if deps_ok:
                    result.checks_passed.append("python_dependencies")
                else:
                    result.checks_failed.append("python_dependencies")
                    result.notes.append("Python dependencies not satisfied. Run: pip install -r requirements.txt")
                    result.passed = False
                    result.new_status = "needs_configuration"
            
            # Node dependencies
            package_json = install_dir / "package.json"
            if package_json.exists():
                result.checks_performed.append("node_dependencies")
                node_modules = install_dir / "node_modules"
                if node_modules.exists():
                    result.checks_passed.append("node_dependencies")
                else:
                    result.checks_failed.append("node_dependencies")
                    result.notes.append("Node modules not installed. Run: npm install")
                    result.passed = False
                    result.new_status = "needs_configuration"
        
        # Check 4: Environment variables
        if result.passed and skill.executor.env:
            result.checks_performed.append("environment_variables")
            import os
            missing_vars = [var for var in skill.executor.env.keys() if not os.environ.get(var)]
            if not missing_vars:
                result.checks_passed.append("environment_variables")
            else:
                result.checks_failed.append("environment_variables")
                result.notes.append(f"Missing environment variables: {', '.join(missing_vars)}")
                result.passed = False
                result.new_status = "needs_configuration"
        
        # Check 5: Run tests (optional)
        if result.passed and run_tests and skill.tests:
            result.checks_performed.append("test_suite")
            tests_passed = await self._run_skill_tests(skill)
            if tests_passed:
                result.checks_passed.append("test_suite")
            else:
                result.checks_failed.append("test_suite")
                result.notes.append("Test suite failed")
                result.passed = False
        
        # Determine final status
        if result.passed:
            result.new_status = "ready"
            result.notes.append("All checks passed - skill is ready for use")
        elif not result.checks_failed:
            result.new_status = "needs_verification"
        
        # Update skill metadata
        await self._update_skill_health(skill, result)
        
        return result
    
    async def check_all_skills(
        self,
        run_tests: bool = False,
        skip_manual: bool = True,
    ) -> List[HealthCheckResult]:
        """
        Run health checks on all installed skills.
        
        Args:
            run_tests: If True, run test suites
            skip_manual: If True, skip manual skills
            
        Returns:
            List of health check results
        """
        registry = self._get_registry()
        results = []
        
        for skill in registry.list_skills():
            if skip_manual:
                exec_type = skill.executor.executor_type.lower()
                if exec_type not in EXECUTABLE_TYPES:
                    continue
            
            try:
                result = await self.check_skill(skill.id, run_tests=run_tests)
                results.append(result)
            except Exception as e:
                logger.error(f"[SKILL HEALTH] Failed to check {skill.id}: {e}")
                results.append(HealthCheckResult(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    previous_status=getattr(skill, 'setup_status', 'unknown'),
                    new_status="failed",
                    passed=False,
                    notes=[f"Health check error: {str(e)}"],
                ))
        
        return results
    
    async def mark_ready(self, skill_id: str, notes: Optional[str] = None) -> bool:
        """
        Manually mark a skill as ready (admin action).
        
        Use this after manually verifying configuration.
        
        Args:
            skill_id: The skill to mark ready
            notes: Optional notes about why this was marked ready
            
        Returns:
            True if successful
        """
        registry = self._get_registry()
        skill = registry.get_skill(skill_id)
        
        if not skill:
            logger.warning(f"[SKILL HEALTH] Cannot mark ready: skill '{skill_id}' not found")
            return False
        
        exec_type = skill.executor.executor_type.lower()
        if exec_type not in EXECUTABLE_TYPES:
            logger.warning(f"[SKILL HEALTH] Cannot mark ready: skill '{skill_id}' is manual")
            return False
        
        skill.setup_status = "ready"
        skill.last_health_check_at = datetime.utcnow().isoformat()
        skill.health_notes = skill.health_notes or []
        skill.health_notes.append(f"Manually marked ready: {notes or 'Admin action'}")
        
        registry.update_skill(skill)
        logger.info(f"[SKILL HEALTH] Marked '{skill_id}' as ready")
        return True
    
    async def mark_failed(self, skill_id: str, reason: str) -> bool:
        """
        Mark a skill as failed.
        
        Args:
            skill_id: The skill to mark failed
            reason: Why the skill failed
            
        Returns:
            True if successful
        """
        registry = self._get_registry()
        skill = registry.get_skill(skill_id)
        
        if not skill:
            return False
        
        skill.setup_status = "failed"
        skill.last_health_check_at = datetime.utcnow().isoformat()
        skill.health_notes = skill.health_notes or []
        skill.health_notes.append(f"Marked failed: {reason}")
        
        registry.update_skill(skill)
        logger.info(f"[SKILL HEALTH] Marked '{skill_id}' as failed: {reason}")
        return True
    
    async def _update_skill_health(self, skill: SkillMetadata, result: HealthCheckResult) -> None:
        """Update skill metadata with health check results."""
        registry = self._get_registry()
        
        skill.setup_status = result.new_status
        skill.last_health_check_at = result.timestamp
        skill.health_notes = result.notes[-5:]  # Keep last 5 notes
        
        try:
            registry.update_skill(skill)
        except Exception as e:
            logger.error(f"[SKILL HEALTH] Failed to update skill {skill.id}: {e}")
    
    async def _check_python_deps(self, requirements_path: Path, auto_install: bool = False) -> bool:
        """Check if Python dependencies are installed."""
        try:
            # Use pip check to verify dependencies
            result = subprocess.run(
                ["pip", "check"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                return True
            
            if auto_install:
                logger.info(f"[SKILL HEALTH] Auto-installing deps from {requirements_path}")
                install_result = subprocess.run(
                    ["pip", "install", "-r", str(requirements_path)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return install_result.returncode == 0
            
            return False
        except Exception as e:
            logger.warning(f"[SKILL HEALTH] Dependency check failed: {e}")
            return False
    
    async def _run_skill_tests(self, skill: SkillMetadata) -> bool:
        """Run a skill's test suite."""
        if not skill.tests or not skill.install_path:
            return True
        
        install_dir = PROJECT_ROOT / skill.install_path
        
        for test_cmd in skill.tests:
            try:
                result = subprocess.run(
                    test_cmd.split(),
                    cwd=install_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    logger.warning(f"[SKILL HEALTH] Test failed for {skill.id}: {test_cmd}")
                    return False
            except Exception as e:
                logger.warning(f"[SKILL HEALTH] Test error for {skill.id}: {e}")
                return False
        
        return True
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of all skill statuses."""
        registry = self._get_registry()
        skills = registry.list_skills()
        
        summary = {
            "total": len(skills),
            "by_status": {},
            "by_executor_type": {},
            "ready_count": 0,
            "needs_attention": [],
        }
        
        for skill in skills:
            status = getattr(skill, 'setup_status', 'unknown')
            exec_type = skill.executor.executor_type.lower()
            
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            summary["by_executor_type"][exec_type] = summary["by_executor_type"].get(exec_type, 0) + 1
            
            if status == "ready":
                summary["ready_count"] += 1
            elif status not in ("manual_only",):
                summary["needs_attention"].append({
                    "skill_id": skill.id,
                    "name": skill.name,
                    "status": status,
                    "executor_type": exec_type,
                })
        
        return summary


# Global service instance
skill_health_service = SkillHealthService()


# Background job function for scheduler
async def run_scheduled_health_checks() -> None:
    """
    Background job to run periodic health checks on all skills.
    
    Should be scheduled to run daily during low-activity hours.
    """
    logger.info("[SKILL HEALTH] Starting scheduled health check")
    
    try:
        results = await skill_health_service.check_all_skills(
            run_tests=False,
            skip_manual=True,
        )
        
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        
        logger.info(f"[SKILL HEALTH] Scheduled check complete: {passed} passed, {failed} failed")
        
    except Exception as e:
        logger.error(f"[SKILL HEALTH] Scheduled check failed: {e}", exc_info=True)


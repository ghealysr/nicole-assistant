#!/usr/bin/env python3
"""
One-time helper to hydrate missing skill metadata fields.

Usage:
    PYTHONPATH=backend python3 backend/scripts/skill_registry_migrate.py
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from app.skills.registry import load_registry, SkillMetadata

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "skills" / "registry.json"
EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}


def determine_status(skill: SkillMetadata) -> str:
    """Infer the best setup status for existing skills."""
    exec_type = skill.executor.executor_type.lower()
    if exec_type not in EXECUTABLE_TYPES:
        return "manual_only"
    if skill.setup_status and skill.setup_status != "ready":
        return skill.setup_status
    if skill.executor.env or skill.tests:
        return "needs_configuration"
    return "needs_verification"


def migrate_registry() -> List[str]:
    registry = load_registry(REGISTRY_PATH)
    updated: List[str] = []

    for skill in registry.list_skills():
        original_status = skill.setup_status
        skill.setup_status = determine_status(skill)
        # Ensure fields exist even if None
        skill.last_health_check_at = skill.last_health_check_at or None
        skill.health_notes = list(skill.health_notes or [])
        skill.last_run_at = skill.last_run_at or None
        skill.last_run_status = skill.last_run_status or None
        if skill.setup_status != original_status:
            updated.append(f"{skill.id}: {original_status} -> {skill.setup_status}")

    registry.save()
    return updated


def main() -> None:
    if not REGISTRY_PATH.exists():
        raise SystemExit(f"Registry file not found at {REGISTRY_PATH}")

    updates = migrate_registry()
    print(f"✅ Skill registry migrated: {REGISTRY_PATH}")
    if updates:
        print("Updated setup statuses:")
        for line in updates:
            print(f"  - {line}")
    else:
        print("No setup status changes were required.")


if __name__ == "__main__":
    main()


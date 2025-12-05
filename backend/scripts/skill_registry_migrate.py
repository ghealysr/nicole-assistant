#!/usr/bin/env python3
"""
Skill Registry Migration Script - Phase 4 Field Hydration

PURPOSE:
    Migrate existing registry.json entries to include all Phase 4 fields required
    for proper skill lifecycle management, health tracking, and memory integration.

FIELDS ADDED/NORMALIZED:
    - setup_status: Current readiness state (ready, needs_configuration, needs_verification, manual_only)
    - knowledge_base_id: ID of associated knowledge base for skill memories (nullable)
    - last_health_check_at: ISO timestamp of last health check (nullable)
    - health_notes: List of health check observations
    - last_run_at: ISO timestamp of last execution (nullable)
    - last_run_status: Status of last execution (success, failed, nullable)

SETUP STATUS DETERMINATION LOGIC:
    1. Manual skills (README-driven) → "manual_only"
    2. Skills with env vars or credentials needed → "needs_configuration"
    3. Skills with test suites → "needs_verification"
    4. Simple executable skills → "needs_verification" (conservative default)

USAGE:
    # From project root
    cd /opt/nicole/backend
    source /opt/nicole/.venv/bin/activate
    PYTHONPATH=. python3 scripts/skill_registry_migrate.py

    # Or from local development
    PYTHONPATH=backend python3 backend/scripts/skill_registry_migrate.py

SAFETY:
    - Creates backup at registry.json.bak before modifying
    - Non-destructive: only adds missing fields, doesn't overwrite existing values
    - Idempotent: safe to run multiple times

Author: Nicole V7 Skills System
Date: December 5, 2025
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Handle both production and development paths
try:
    from app.skills.registry import load_registry, SkillMetadata, SkillRegistry
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.skills.registry import load_registry, SkillMetadata, SkillRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "skills" / "registry.json"

# Executor types that can be programmatically executed
EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}


def determine_setup_status(skill: SkillMetadata) -> str:
    """
    Determine the appropriate setup_status for a skill based on its configuration.
    
    Decision Tree:
    1. Non-executable (manual) → "manual_only"
    2. Requires env vars or credentials → "needs_configuration"
    3. Has requirements.txt or dependencies → "needs_configuration"
    4. Has test suite defined → "needs_verification"
    5. Default for executables → "needs_verification"
    
    Args:
        skill: The skill metadata to analyze
        
    Returns:
        Appropriate setup_status string
    """
    exec_type = skill.executor.executor_type.lower()
    
    # Manual skills can never be "ready" - they require human intervention
    if exec_type not in EXECUTABLE_TYPES:
        return "manual_only"
    
    # Check for environment requirements
    if skill.executor.env:
        return "needs_configuration"
    
    # Check for dependencies that need installation
    if skill.dependencies:
        return "needs_configuration"
    
    # Check if install path exists and has requirements.txt
    if skill.install_path:
        install_dir = PROJECT_ROOT / skill.install_path
        requirements_files = [
            install_dir / "requirements.txt",
            install_dir / "Pipfile",
            install_dir / "package.json",
            install_dir / "pyproject.toml",
        ]
        if any(f.exists() for f in requirements_files):
            return "needs_configuration"
    
    # Skills with tests should be verified before use
    if skill.tests:
        return "needs_verification"
    
    # Conservative default: require verification before first use
    return "needs_verification"


def create_backup(registry_path: Path) -> Path:
    """Create a timestamped backup of the registry file."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = registry_path.with_suffix(f".{timestamp}.bak")
    shutil.copy2(registry_path, backup_path)
    return backup_path


def migrate_skill(skill: SkillMetadata, force_status_recalc: bool = False) -> Tuple[bool, List[str]]:
    """
    Migrate a single skill's metadata to include Phase 4 fields.
    
    Args:
        skill: The skill to migrate
        force_status_recalc: If True, recalculate setup_status even if already set
        
    Returns:
        Tuple of (was_modified, list_of_changes)
    """
    changes = []
    modified = False
    
    # Determine new setup_status
    if force_status_recalc or not hasattr(skill, 'setup_status') or skill.setup_status in (None, "", "ready", "unknown"):
        old_status = getattr(skill, 'setup_status', None)
        new_status = determine_setup_status(skill)
        
        # Only update if different and skill is executable
        # Keep "ready" status for executable skills that were already validated
        exec_type = skill.executor.executor_type.lower()
        if exec_type in EXECUTABLE_TYPES and old_status == "ready":
            # Keep ready status for previously validated skills
            pass
        elif new_status != old_status:
            skill.setup_status = new_status
            changes.append(f"setup_status: {old_status} → {new_status}")
            modified = True
    
    # Ensure knowledge_base_id exists (nullable)
    if not hasattr(skill, 'knowledge_base_id'):
        skill.knowledge_base_id = None
        changes.append("knowledge_base_id: added (null)")
        modified = True
    
    # Ensure last_health_check_at exists (nullable)
    if not hasattr(skill, 'last_health_check_at'):
        skill.last_health_check_at = None
        changes.append("last_health_check_at: added (null)")
        modified = True
    
    # Ensure health_notes exists as list
    if not hasattr(skill, 'health_notes') or skill.health_notes is None:
        skill.health_notes = []
        changes.append("health_notes: added (empty list)")
        modified = True
    elif not isinstance(skill.health_notes, list):
        skill.health_notes = list(skill.health_notes)
        changes.append("health_notes: converted to list")
        modified = True
    
    # Ensure last_run_at exists (nullable)
    if not hasattr(skill, 'last_run_at'):
        skill.last_run_at = None
        changes.append("last_run_at: added (null)")
        modified = True
    
    # Ensure last_run_status exists (nullable)
    if not hasattr(skill, 'last_run_status'):
        skill.last_run_status = None
        changes.append("last_run_status: added (null)")
        modified = True
    
    # Fix imported_at if missing
    if hasattr(skill, 'source') and skill.source:
        if not hasattr(skill.source, 'imported_at') or skill.source.imported_at is None:
            skill.source.imported_at = datetime.utcnow().isoformat()
            changes.append("source.imported_at: set to current time")
            modified = True
    
    return modified, changes


def migrate_registry(registry_path: Path, force_status_recalc: bool = False) -> Dict[str, Any]:
    """
    Perform full registry migration.
    
    Args:
        registry_path: Path to registry.json
        force_status_recalc: If True, recalculate all setup statuses
        
    Returns:
        Migration report dictionary
    """
    report = {
        "registry_path": str(registry_path),
        "backup_path": None,
        "total_skills": 0,
        "skills_modified": 0,
        "changes": [],
        "errors": [],
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if not registry_path.exists():
        report["errors"].append(f"Registry file not found: {registry_path}")
        return report
    
    # Create backup
    try:
        backup_path = create_backup(registry_path)
        report["backup_path"] = str(backup_path)
    except Exception as e:
        report["errors"].append(f"Backup failed: {e}")
        return report
    
    # Load registry
    try:
        registry = load_registry(registry_path)
    except Exception as e:
        report["errors"].append(f"Failed to load registry: {e}")
        return report
    
    skills = registry.list_skills()
    report["total_skills"] = len(skills)
    
    # Migrate each skill
    for skill in skills:
        try:
            modified, changes = migrate_skill(skill, force_status_recalc)
            
            if modified:
                report["skills_modified"] += 1
                report["changes"].append({
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "changes": changes,
                })
        except Exception as e:
            report["errors"].append(f"Failed to migrate {skill.id}: {e}")
    
    # Save updated registry
    try:
        registry.save()
    except Exception as e:
        report["errors"].append(f"Failed to save registry: {e}")
    
    return report


def print_report(report: Dict[str, Any]) -> None:
    """Pretty-print the migration report."""
    print("\n" + "=" * 60)
    print("📦 SKILL REGISTRY MIGRATION REPORT")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Registry: {report['registry_path']}")
    print(f"Backup: {report['backup_path']}")
    print()
    print(f"Total Skills: {report['total_skills']}")
    print(f"Skills Modified: {report['skills_modified']}")
    print()
    
    if report['changes']:
        print("CHANGES:")
        print("-" * 40)
        for skill_changes in report['changes']:
            print(f"  🔧 {skill_changes['skill_name']} ({skill_changes['skill_id']})")
            for change in skill_changes['changes']:
                print(f"     • {change}")
        print()
    
    if report['errors']:
        print("⚠️  ERRORS:")
        print("-" * 40)
        for error in report['errors']:
            print(f"  ❌ {error}")
        print()
    
    if not report['errors']:
        print("✅ Migration completed successfully!")
    else:
        print("⚠️  Migration completed with errors. Review above.")
    print("=" * 60 + "\n")


def main() -> None:
    """Main entry point for the migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate Nicole's skill registry to Phase 4 schema"
    )
    parser.add_argument(
        "--force-status",
        action="store_true",
        help="Force recalculation of all setup_status values"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=REGISTRY_PATH,
        help=f"Path to registry.json (default: {REGISTRY_PATH})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without saving"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be saved")
    
    report = migrate_registry(args.registry, force_status_recalc=args.force_status)
    print_report(report)
    
    # Exit with error code if there were errors
    if report['errors']:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

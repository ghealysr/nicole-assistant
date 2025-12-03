#!/usr/bin/env python3
"""
Update a skill's setup_status in the registry.

Usage:
    PYTHONPATH=backend python3 backend/scripts/skill_set_status.py \
        --skill local-example-python-skill --status ready
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.skills.registry import load_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "skills" / "registry.json"
VALID_STATUSES = {"ready", "needs_configuration", "needs_verification", "manual_only", "disabled"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Update skill setup_status")
    parser.add_argument("--skill", required=True, help="Skill ID to update")
    parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    args = parser.parse_args()

    registry = load_registry(REGISTRY_PATH)
    skill = registry.get_skill(args.skill)
    if not skill:
        raise SystemExit(f"Skill '{args.skill}' not found in registry {REGISTRY_PATH}")

    previous = skill.setup_status
    skill.setup_status = args.status
    registry.update_skill(skill)

    print(
        f"Updated setup_status for {skill.id}: {previous or 'unset'} -> {skill.setup_status} "
        f"(registry: {REGISTRY_PATH})"
    )


if __name__ == "__main__":
    main()


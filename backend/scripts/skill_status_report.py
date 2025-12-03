#!/usr/bin/env python3
"""
Utility to inspect installed skills and current environment.

Usage:
    PYTHONPATH=backend python3 backend/scripts/skill_status_report.py
"""

from __future__ import annotations

import socket
from pathlib import Path

from app.config import settings
from app.skills.registry import load_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "skills" / "registry.json"


def main() -> None:
    registry = load_registry(REGISTRY_PATH)
    hostname = socket.gethostname()

    print("🔧 Skill Environment Report")
    print("===========================")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Host: {hostname}")
    print(f"Registry: {REGISTRY_PATH}")
    print()

    skills = registry.list_skills()
    if not skills:
        print("No skills installed.")
        return

    print(f"Found {len(skills)} skill(s):")
    for skill in skills:
        print(
            f"- {skill.id} "
            f"(executor={skill.executor.executor_type}, setup_status={skill.setup_status}, "
            f"last_run={skill.last_run_status or 'never'})"
        )


if __name__ == "__main__":
    main()


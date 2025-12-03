"""
Skill management package for Nicole V7.

This package provides:
- Skill registry and metadata management
- Skill importation from external repositories  
- Skill execution via adapters (Python, Node, CLI)
- Memory integration for skill learning
- History tracking for audit

Key Components:
- registry.py: SkillMetadata, SkillRegistry, load_registry
- skill_importer.py: SkillImporter for installing skills from repos
- skill_runner.py: SkillRunner for executing skills
- skill_memory.py: SkillMemoryManager for memory integration
- skill_history.py: append_history for audit trail
- adapters/: Execution adapters for different skill types
"""

from app.skills.registry import (
    SkillMetadata,
    SkillRegistry,
    SkillSource,
    SkillExecutor,
    SkillCapability,
    SkillSafety,
    load_registry,
)
from app.skills.execution import (
    SkillExecutionContext,
    SkillExecutionResult,
)
from app.skills.adapters.base import (
    BaseSkillAdapter,
    SkillExecutionError,
)

__all__ = [
    # Registry
    "SkillMetadata",
    "SkillRegistry",
    "SkillSource",
    "SkillExecutor",
    "SkillCapability",
    "SkillSafety",
    "load_registry",
    # Execution
    "SkillExecutionContext",
    "SkillExecutionResult",
    "BaseSkillAdapter",
    "SkillExecutionError",
]

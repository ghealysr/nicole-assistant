"""
Skill registry data models and helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import json


@dataclass
class SkillSource:
    url: str
    repo: str
    ref: str
    license: Optional[str] = None
    imported_at: Optional[str] = None


@dataclass
class SkillCapability:
    domain: str
    description: str
    trigger_phrases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class SkillExecutor:
    executor_type: str
    entrypoint: str
    runtime: Optional[str] = None
    timeout_seconds: int = 300
    env: Dict[str, str] = field(default_factory=dict)
    requires_gpu: bool = False


@dataclass
class SkillSafety:
    risk_level: str = "low"
    notes: List[str] = field(default_factory=list)
    review_status: str = "unreviewed"


@dataclass
class SkillMetadata:
    id: str
    name: str
    vendor: str
    description: str
    version: str
    checksum: str
    source: SkillSource
    executor: SkillExecutor
    capabilities: List[SkillCapability]
    safety: SkillSafety = field(default_factory=SkillSafety)
    usage_examples: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    install_path: Optional[str] = None
    status: str = "installed"
    setup_status: str = "ready"
    knowledge_base_id: Optional[int] = None
    last_health_check_at: Optional[str] = None
    health_notes: List[str] = field(default_factory=list)
    last_run_at: Optional[str] = None
    last_run_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillRegistry:
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self._skills: Dict[str, SkillMetadata] = {}

    def load(self) -> None:
        if not self.registry_path.exists():
            self._skills = {}
            return

        data = json.loads(self.registry_path.read_text())
        skills = {}
        for item in data.get("skills", []):
            metadata = SkillMetadata(
                id=item["id"],
                name=item["name"],
                vendor=item["vendor"],
                description=item["description"],
                version=item["version"],
                checksum=item["checksum"],
                source=SkillSource(**item["source"]),
                executor=SkillExecutor(**item["executor"]),
                capabilities=[SkillCapability(**cap) for cap in item.get("capabilities", [])],
                safety=SkillSafety(**item.get("safety", {})),
                usage_examples=item.get("usage_examples", []),
                dependencies=item.get("dependencies", []),
                tests=item.get("tests", []),
                install_path=item.get("install_path"),
                status=item.get("status", "installed"),
                setup_status=item.get("setup_status", "ready"),
                knowledge_base_id=item.get("knowledge_base_id"),
                last_health_check_at=item.get("last_health_check_at"),
                health_notes=item.get("health_notes", []),
                last_run_at=item.get("last_run_at"),
                last_run_status=item.get("last_run_status"),
            )
            skills[metadata.id] = metadata
        self._skills = skills

    def save(self) -> None:
        payload = {
            "updated_at": datetime.utcnow().isoformat(),
            "skills": [skill.to_dict() for skill in self._skills.values()],
        }
        self.registry_path.write_text(json.dumps(payload, indent=2))

    def list_skills(self) -> List[SkillMetadata]:
        return list(self._skills.values())

    def get_skill(self, skill_id: str) -> Optional[SkillMetadata]:
        return self._skills.get(skill_id)

    def register(self, metadata: SkillMetadata) -> None:
        self._skills[metadata.id] = metadata
        self.save()

    def skill_exists(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def update_skill(self, metadata: SkillMetadata) -> None:
        if metadata.id not in self._skills:
            raise KeyError(f"Skill {metadata.id} not registered")
        self._skills[metadata.id] = metadata
        self.save()


def load_registry(registry_path: Path) -> SkillRegistry:
    registry = SkillRegistry(registry_path)
    registry.load()
    return registry


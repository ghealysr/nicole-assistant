#!/usr/bin/env python3
"""
Install all skills from the awesome-claude-skills library into Nicole's skill system.
This script:
1. Parses each SKILL.md file
2. Creates registry entries
3. Copies skills to the installed directory
4. Updates the registry.json
"""

import json
import os
import shutil
import hashlib
import re
from pathlib import Path
from datetime import datetime

SKILLS_ROOT = Path(__file__).parent
LIBRARY_PATH = SKILLS_ROOT / "claude-skills-library"
INSTALLED_PATH = SKILLS_ROOT / "installed" / "claude-skills"
BACKEND_SKILLS_PATH = SKILLS_ROOT.parent / "backend" / "app" / "skills"
REGISTRY_PATH = SKILLS_ROOT / "registry.json"


def parse_skill_md(skill_path: Path) -> dict:
    """Parse a SKILL.md file and extract metadata."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return None
    
    content = skill_md.read_text()
    
    # Parse YAML frontmatter
    metadata = {
        "name": skill_path.name,
        "description": "",
        "license": "MIT",
    }
    
    # Check for YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip().strip('"').strip("'")
                    if key == "name":
                        metadata["name"] = value
                    elif key == "description":
                        metadata["description"] = value
                    elif key == "license":
                        metadata["license"] = value
    
    # If no description in frontmatter, try to extract from content
    if not metadata["description"]:
        # Look for first paragraph after frontmatter
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("#") and not line.startswith("##"):
                # Found title, look for description after
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        metadata["description"] = lines[j].strip()[:200]
                        break
                break
    
    return metadata


def compute_checksum(skill_path: Path) -> str:
    """Compute a checksum for the skill directory."""
    hasher = hashlib.sha256()
    for file in sorted(skill_path.rglob("*")):
        if file.is_file():
            hasher.update(file.read_bytes())
    return hasher.hexdigest()[:16]


def detect_executor_type(skill_path: Path) -> dict:
    """Detect the executor type based on files in the skill directory."""
    scripts_path = skill_path / "scripts"
    
    # Check for Python scripts
    if scripts_path.exists():
        py_files = list(scripts_path.glob("*.py"))
        if py_files:
            return {
                "executor_type": "python_script",
                "entrypoint": py_files[0].name,
                "runtime": "python3",
                "timeout_seconds": 300,
                "env": {},
                "requires_gpu": False,
            }
        
        # Check for Node.js scripts
        js_files = list(scripts_path.glob("*.js"))
        if js_files:
            return {
                "executor_type": "node_script",
                "entrypoint": js_files[0].name,
                "runtime": "node",
                "timeout_seconds": 300,
                "env": {},
                "requires_gpu": False,
            }
    
    # Check for shell scripts
    sh_files = list(skill_path.glob("*.sh"))
    if sh_files:
        return {
            "executor_type": "shell_script",
            "entrypoint": sh_files[0].name,
            "runtime": "bash",
            "timeout_seconds": 300,
            "env": {},
            "requires_gpu": False,
        }
    
    # Default to manual/documentation skill
    return {
        "executor_type": "manual",
        "entrypoint": "SKILL.md",
        "runtime": None,
        "timeout_seconds": 300,
        "env": {},
        "requires_gpu": False,
    }


def detect_category(skill_name: str, description: str) -> str:
    """Detect the category based on skill name and description."""
    name_lower = skill_name.lower()
    desc_lower = description.lower()
    
    if any(x in name_lower for x in ["xlsx", "pdf", "docx", "pptx", "document"]):
        return "documents"
    if any(x in name_lower for x in ["design", "canvas", "theme", "brand", "image"]):
        return "creative"
    if any(x in name_lower for x in ["code", "developer", "mcp", "webapp", "artifact"]):
        return "development"
    if any(x in name_lower for x in ["meeting", "lead", "invoice", "ads", "domain"]):
        return "business"
    if any(x in name_lower for x in ["file", "raffle", "organizer"]):
        return "productivity"
    if any(x in name_lower for x in ["content", "writer", "comms"]):
        return "communication"
    
    return "general"


def create_skill_entry(skill_path: Path, metadata: dict) -> dict:
    """Create a full skill registry entry."""
    skill_id = f"claude-skills-{skill_path.name}"
    
    executor = detect_executor_type(skill_path)
    category = detect_category(metadata["name"], metadata["description"])
    
    return {
        "id": skill_id,
        "name": metadata["name"],
        "vendor": "ComposioHQ/awesome-claude-skills",
        "description": metadata["description"],
        "version": "1.0.0",
        "checksum": compute_checksum(skill_path),
        "source": {
            "url": f"https://github.com/ComposioHQ/awesome-claude-skills/tree/master/{skill_path.name}",
            "repo": "ComposioHQ/awesome-claude-skills",
            "ref": "master",
            "license": metadata.get("license", "MIT"),
            "imported_at": datetime.utcnow().isoformat(),
        },
        "executor": executor,
        "capabilities": [
            {
                "domain": category,
                "description": metadata["description"][:100] if metadata["description"] else "Imported skill",
                "trigger_phrases": [],
                "tags": [category, skill_path.name],
            }
        ],
        "safety": {
            "risk_level": "low",
            "notes": ["Imported from awesome-claude-skills"],
            "review_status": "unreviewed",
        },
        "usage_examples": [],
        "dependencies": [],
        "tests": [],
        "install_path": f"skills/installed/claude-skills/{skill_path.name}",
        "status": "installed",
        "setup_status": "ready",
        "last_health_check_at": datetime.utcnow().isoformat(),
        "health_notes": ["Auto-imported from awesome-claude-skills"],
        "last_run_at": None,
        "last_run_status": None,
        "knowledge_base_id": None,
    }


def main():
    print("=" * 60)
    print("Installing Claude Skills from awesome-claude-skills")
    print("=" * 60)
    
    # Load existing registry
    if REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text())
    else:
        registry = {"updated_at": None, "skills": []}
    
    existing_ids = {s["id"] for s in registry["skills"]}
    
    # Create installed directory
    INSTALLED_PATH.mkdir(parents=True, exist_ok=True)
    
    # Find all skills
    skills_found = []
    skills_installed = []
    
    # Top-level skills
    for item in LIBRARY_PATH.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            skills_found.append(item)
    
    # Document skills (nested)
    doc_skills = LIBRARY_PATH / "document-skills"
    if doc_skills.exists():
        for item in doc_skills.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skills_found.append(item)
    
    print(f"\nFound {len(skills_found)} skills to install\n")
    
    for skill_path in sorted(skills_found):
        skill_name = skill_path.name
        skill_id = f"claude-skills-{skill_name}"
        
        # Skip if already installed
        if skill_id in existing_ids:
            print(f"  ⏭️  {skill_name} (already installed)")
            continue
        
        # Parse metadata
        metadata = parse_skill_md(skill_path)
        if not metadata:
            print(f"  ❌ {skill_name} (no SKILL.md)")
            continue
        
        # Create registry entry
        entry = create_skill_entry(skill_path, metadata)
        
        # Copy skill to installed directory
        dest_path = INSTALLED_PATH / skill_name
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(skill_path, dest_path)
        
        # Add to registry
        registry["skills"].append(entry)
        skills_installed.append(skill_name)
        
        print(f"  ✅ {skill_name}")
        print(f"      → {metadata['description'][:60]}..." if len(metadata.get('description', '')) > 60 else f"      → {metadata.get('description', 'No description')}")
    
    # Update registry
    registry["updated_at"] = datetime.utcnow().isoformat()
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))
    
    print("\n" + "=" * 60)
    print(f"Installation Complete!")
    print(f"  • Skills installed: {len(skills_installed)}")
    print(f"  • Total skills in registry: {len(registry['skills'])}")
    print(f"  • Registry updated: {REGISTRY_PATH}")
    print("=" * 60)
    
    # Also copy key skills to backend/app/skills for direct access
    key_skills = ["xlsx", "pdf", "docx", "pptx", "canvas-design", "frontend-design", "skill-creator"]
    
    print("\nCopying key skills to backend...")
    for skill_name in key_skills:
        src = INSTALLED_PATH / skill_name
        if not src.exists():
            # Try document-skills path
            src = LIBRARY_PATH / "document-skills" / skill_name
        
        if src.exists():
            dest = BACKEND_SKILLS_PATH / skill_name
            if not dest.exists():
                shutil.copytree(src, dest)
                print(f"  ✅ Copied {skill_name} to backend")
            else:
                print(f"  ⏭️  {skill_name} already in backend")
    
    print("\nDone!")


if __name__ == "__main__":
    main()



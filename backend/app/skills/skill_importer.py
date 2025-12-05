"""
Skill importer service.

Handles cloning/downloading external skill repositories, normalizing manifests,
and registering skills in Nicole's registry.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from app.skills.registry import (
    SkillMetadata,
    SkillSource,
    SkillExecutor,
    SkillCapability,
    SkillSafety,
    load_registry,
)

try:
    from app.services.tool_search_service import tool_search_service
except Exception:  # pragma: no cover - importer may run outside API context
    tool_search_service = None


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = PROJECT_ROOT / "skills"
REGISTRY_PATH = SKILLS_ROOT / "registry.json"
EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}


class SkillImporter:
    """Importer responsible for installing skills from remote repos."""

    def __init__(self):
        SKILLS_ROOT.mkdir(parents=True, exist_ok=True)
        (SKILLS_ROOT / "installed").mkdir(exist_ok=True)
        (SKILLS_ROOT / "sources").mkdir(exist_ok=True)
        (SKILLS_ROOT / "logs").mkdir(exist_ok=True)
        self.registry = load_registry(REGISTRY_PATH)

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

    def clone_repo(self, repo_url: str) -> Path:
        """Clone a repo into a temporary directory."""
        temp_dir = Path(tempfile.mkdtemp(prefix="skill-import-"))
        subprocess.run(["git", "clone", "--depth", "1", repo_url, str(temp_dir)], check=True)
        return temp_dir

    def detect_skill_manifest(self, repo_dir: Path, subpath: Optional[str] = None) -> Path:
        """Detect the skill manifest file."""
        candidate_dirs = [repo_dir]
        if subpath:
            candidate_dirs.insert(0, repo_dir / subpath)

        manifest_names = ["skill.yaml", "skill.yml", "skill.json", "SKILL.md", "manifest.json", "package.json"]
        for directory in candidate_dirs:
            for name in manifest_names:
                manifest = directory / name
                if manifest.exists():
                    return manifest
        raise FileNotFoundError("Could not find a skill manifest in repository")

    def compute_checksum(self, directory: Path) -> str:
        """Compute SHA256 of all files to detect changes."""
        sha256 = hashlib.sha256()
        for file in sorted(directory.rglob("*")):
            if file.is_file():
                sha256.update(file.read_bytes())
        return sha256.hexdigest()

    def _validate_entrypoint(self, executor: SkillExecutor, manifest_dir: Path) -> None:
        """Ensure executable skills reference a valid entrypoint."""
        exec_type = executor.executor_type.lower()
        if exec_type not in EXECUTABLE_TYPES:
            return

        if not executor.entrypoint:
            raise ValueError(f"Executable skill ({exec_type}) must declare an entrypoint command.")

        entry_command = shlex.split(executor.entrypoint)[0]
        entry_path = manifest_dir / entry_command
        if not entry_path.exists():
            raise FileNotFoundError(
                f"Entry point '{entry_command}' not found for executor_type={exec_type}"
            )

    def _determine_setup_status(
        self,
        executor: SkillExecutor,
        manifest: Dict[str, Any],
        manifest_dir: Path,
    ) -> str:
        """Decide initial setup status for a skill."""
        exec_type = executor.executor_type.lower()
        if exec_type not in EXECUTABLE_TYPES:
            return "manual_only"

        requirements_files = [
            manifest_dir / "requirements.txt",
            manifest_dir / "Pipfile",
            manifest_dir / "package.json",
        ]

        if executor.env or manifest.get("requires_credentials"):
            return "needs_configuration"
        if any(path.exists() for path in requirements_files):
            return "needs_configuration"
        if manifest.get("tests"):
            return "needs_verification"
        return "needs_verification"

    def normalize_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        """Load and normalize manifest data."""
        if manifest_path.suffix in [".yaml", ".yml"]:
            import yaml  # lazy import

            data = yaml.safe_load(manifest_path.read_text())
        elif manifest_path.suffix == ".json":
            data = json.loads(manifest_path.read_text())
        elif manifest_path.name.lower() == "skill.md":
            data = self._parse_skill_md(manifest_path)
        else:
            raise ValueError(f"Unsupported manifest format: {manifest_path}")

        return data

    def _parse_skill_md(self, manifest_path: Path) -> Dict[str, Any]:
        """
        Parse SKILL.md format with enhanced metadata extraction.
        
        Extracts:
        - Title from first H1 heading
        - Description from opening paragraph
        - Capabilities from "Features" or "Capabilities" section
        - Usage examples from "Usage" or "Examples" section
        - Trigger phrases from "Commands" or code blocks
        - Executor type inferred from file extensions
        
        SKILL.md Format (typical Claude Code skill):
        ```markdown
        # Skill Name
        
        Short description paragraph.
        
        ## Features
        - Feature 1
        - Feature 2
        
        ## Usage
        ```command
        example-command --flag
        ```
        ```
        """
        content = manifest_path.read_text()
        lines = content.splitlines()
        skill_dir = manifest_path.parent
        
        # Extract title
        title = None
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break
        title = title or skill_dir.name
        
        # Extract description (first paragraph after title)
        description = ""
        in_paragraph = False
        paragraph_lines = []
        for line in lines:
            if line.startswith("#"):
                if in_paragraph:
                    break
                continue
            
            stripped = line.strip()
            if not stripped:
                if paragraph_lines:
                    break
                continue
            
            paragraph_lines.append(stripped)
            in_paragraph = True
        
        description = " ".join(paragraph_lines) if paragraph_lines else f"Skill imported from {manifest_path.name}"
        
        # Extract features/capabilities from bullet points
        capabilities = []
        features_section = self._extract_section(content, ["features", "capabilities", "what it does"])
        if features_section:
            for line in features_section.splitlines():
                stripped = line.strip()
                if stripped.startswith(("-", "*", "•")):
                    feature = stripped.lstrip("-*• ").strip()
                    if feature and len(feature) > 5:
                        capabilities.append({
                            "domain": self._infer_domain(feature),
                            "description": feature,
                            "tags": self._extract_tags(feature),
                        })
        
        # Extract usage examples
        examples = []
        usage_section = self._extract_section(content, ["usage", "examples", "how to use"])
        if usage_section:
            # Find code blocks
            code_block_pattern = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
            for match in code_block_pattern.finditer(usage_section):
                code = match.group(1).strip()
                if code:
                    examples.append(code)
            
            # Also capture inline code
            inline_code_pattern = re.compile(r"`([^`]+)`")
            for match in inline_code_pattern.finditer(usage_section):
                code = match.group(1).strip()
                if code and len(code) > 3 and code not in examples:
                    examples.append(code)
        
        # Extract trigger phrases from commands section
        trigger_phrases = []
        commands_section = self._extract_section(content, ["commands", "triggers", "invocation"])
        if commands_section:
            for line in commands_section.splitlines():
                stripped = line.strip()
                if stripped.startswith(("-", "*", "•")):
                    trigger = stripped.lstrip("-*• ").strip()
                    if trigger:
                        trigger_phrases.append(trigger)
        
        # Infer executor type from files in directory
        executor_type, entrypoint = self._infer_executor(skill_dir)
        
        # Build normalized manifest
        data = {
            "name": title,
            "description": description[:500],  # Truncate if too long
            "executor": {
                "type": executor_type,
                "entrypoint": entrypoint,
            },
            "capabilities": capabilities if capabilities else [{
                "domain": self._infer_domain(description),
                "description": description,
                "tags": self._extract_tags(title + " " + description),
            }],
            "examples": examples[:5],  # Keep top 5 examples
        }
        
        # Add trigger phrases to first capability
        if trigger_phrases and data["capabilities"]:
            data["capabilities"][0]["trigger_phrases"] = trigger_phrases[:10]
        
        return data

    def _extract_section(self, content: str, headers: list) -> Optional[str]:
        """Extract content under a specific section header."""
        lines = content.splitlines()
        in_section = False
        section_lines = []
        
        for line in lines:
            stripped = line.strip().lower()
            
            # Check if we hit a new section
            if stripped.startswith("##"):
                section_name = stripped.lstrip("#").strip()
                if any(h in section_name for h in headers):
                    in_section = True
                    continue
                elif in_section:
                    break  # Hit next section
            
            if in_section:
                section_lines.append(line)
        
        return "\n".join(section_lines) if section_lines else None

    def _infer_executor(self, skill_dir: Path) -> tuple:
        """
        Infer executor type and entrypoint from files in directory.
        
        Returns:
            Tuple of (executor_type, entrypoint)
        """
        # Check for common entrypoints in order of preference
        entrypoint_checks = [
            ("main.py", "python"),
            ("index.py", "python"),
            ("run.py", "python"),
            ("__main__.py", "python"),
            ("index.js", "node"),
            ("main.js", "node"),
            ("index.ts", "node"),
            ("main.ts", "node"),
            ("cli.py", "python"),
            ("cli.js", "node"),
        ]
        
        for filename, exec_type in entrypoint_checks:
            if (skill_dir / filename).exists():
                return exec_type, filename
        
        # Check for shell scripts
        for ext in [".sh", ".bash"]:
            for f in skill_dir.glob(f"*{ext}"):
                return "cli", f.name
        
        # Fallback based on file extensions present
        py_files = list(skill_dir.glob("*.py"))
        js_files = list(skill_dir.glob("*.js")) + list(skill_dir.glob("*.ts"))
        
        if py_files:
            return "python", py_files[0].name
        if js_files:
            return "node", js_files[0].name
        
        # Default to manual if no executable found
        return "manual", "README-driven"

    def _infer_domain(self, text: str) -> str:
        """Infer capability domain from text."""
        text_lower = text.lower()
        
        domain_keywords = {
            "automation": ["automat", "browser", "playwright", "selenium", "puppeteer", "scrape"],
            "coding": ["code", "program", "debug", "refactor", "lint", "compile", "git"],
            "mobile": ["ios", "android", "mobile", "simulator", "emulator", "react native"],
            "communication": ["email", "slack", "discord", "telegram", "message", "notify"],
            "data": ["data", "database", "sql", "query", "csv", "json", "api"],
            "ai": ["ai", "ml", "model", "gpt", "claude", "embedding", "vector"],
            "filesystem": ["file", "directory", "folder", "path", "read", "write"],
            "devops": ["deploy", "docker", "kubernetes", "ci", "cd", "build", "server"],
            "security": ["security", "auth", "encrypt", "password", "token", "secret"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return domain
        
        return "general"

    def _extract_tags(self, text: str) -> list:
        """Extract relevant tags from text."""
        text_lower = text.lower()
        
        potential_tags = [
            "python", "javascript", "node", "typescript", "rust", "go",
            "browser", "automation", "testing", "api", "cli", "gui",
            "ios", "android", "mobile", "web", "desktop",
            "database", "sql", "nosql", "file", "filesystem",
            "ai", "ml", "llm", "gpt", "claude", "embedding",
            "security", "auth", "encryption",
            "docker", "kubernetes", "devops", "ci", "cd",
            "git", "github", "gitlab", "bitbucket",
            "email", "slack", "discord", "telegram",
        ]
        
        return [tag for tag in potential_tags if tag in text_lower][:5]  # Max 5 tags

    def install_skill(
        self,
        repo_url: str,
        skill_name: Optional[str] = None,
        subpath: Optional[str] = None,
    ) -> SkillMetadata:
        """
        Install a skill from the given repository.
        """
        repo_dir = self.clone_repo(repo_url)
        try:
            manifest_path = self.detect_skill_manifest(repo_dir, subpath=subpath)
            manifest = self.normalize_manifest(manifest_path)

            final_name = skill_name or manifest.get("name") or manifest_path.parent.name
            vendor = self._slugify(Path(repo_url).stem)
            skill_id = f"{vendor}-{self._slugify(final_name)}"
            install_dir = SKILLS_ROOT / "installed" / vendor / final_name
            install_dir.mkdir(parents=True, exist_ok=True)

            # Copy files
            src_dir = manifest_path.parent
            for item in src_dir.iterdir():
                dest = install_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            checksum = self.compute_checksum(install_dir)
            source_meta = SkillSource(
                url=repo_url,
                repo=repo_url,
                ref="main",
                license=manifest.get("license"),
                imported_at=datetime.utcnow().isoformat(),
            )

            executor = manifest.get("executor", {})
            executor_meta = SkillExecutor(
                executor_type=executor.get("type", "manual"),
                entrypoint=executor.get("entrypoint", ""),
                runtime=executor.get("runtime"),
                timeout_seconds=executor.get("timeout", 300),
                env=executor.get("env", {}),
                requires_gpu=executor.get("requires_gpu", False),
            )
            self._validate_entrypoint(executor_meta, src_dir)

            capabilities_data = manifest.get("capabilities", [])
            if isinstance(capabilities_data, dict):
                capabilities_data = [capabilities_data]
            capabilities = [
                SkillCapability(
                    domain=cap.get("domain", "general"),
                    description=cap.get("description", ""),
                    trigger_phrases=cap.get("trigger_phrases", []),
                    tags=cap.get("tags", []),
                )
                for cap in capabilities_data
            ]
            if not capabilities:
                capabilities = [
                    SkillCapability(
                        domain="general",
                        description=manifest.get("description", ""),
                    )
                ]

            metadata = SkillMetadata(
                id=skill_id,
                name=final_name,
                vendor=vendor,
                description=manifest.get("description", f"Skill imported from {repo_url}"),
                version=str(manifest.get("version", "0.1.0")),
                checksum=checksum,
                source=source_meta,
                executor=executor_meta,
                capabilities=capabilities,
                safety=SkillSafety(
                    risk_level=manifest.get("risk", "low"),
                    notes=manifest.get("safety_notes", []),
                    review_status="unreviewed",
                ),
                usage_examples=manifest.get("examples", []),
                dependencies=manifest.get("dependencies", []),
                tests=manifest.get("tests", []),
                install_path=str(install_dir.relative_to(PROJECT_ROOT)),
                setup_status=self._determine_setup_status(executor_meta, manifest, src_dir),
                last_health_check_at=None,
                health_notes=[],
                last_run_at=None,
                last_run_status=None,
            )

            self.registry.register(metadata)
            if tool_search_service:
                try:
                    tool_search_service.register_skill(metadata)
                except Exception as exc:
                    logger.warning(f"[SKILL IMPORT] Failed to register skill with tool search: {exc}")
            return metadata
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)


skill_importer = SkillImporter()


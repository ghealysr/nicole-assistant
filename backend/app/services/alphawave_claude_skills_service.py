"""
Claude Skills Service for Nicole

This service provides access to the Claude Skills library, enabling Nicole to:
1. Discover relevant skills based on user requests
2. Retrieve detailed skill instructions
3. Apply skill-specific knowledge to enhance responses

Skills are parsed from the ComposioHQ/awesome-claude-skills repository.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import lru_cache
import re

logger = logging.getLogger(__name__)


class ClaudeSkillsService:
    """Service for managing and accessing Claude Skills."""
    
    def __init__(self):
        self._index: Optional[Dict[str, Any]] = None
        self._lookup: Optional[Dict[str, Any]] = None
        self._loaded = False
        
        # Paths to skills data
        self.skills_dir = Path(__file__).parent.parent.parent.parent / 'skills'
        self.index_path = self.skills_dir / 'claude-skills-index' / 'skills_index.json'
        self.lookup_path = self.skills_dir / 'claude-skills-index' / 'skills_lookup.json'
        self.library_path = self.skills_dir / 'claude-skills-library'
    
    def load(self) -> bool:
        """Load the skills index and lookup tables."""
        if self._loaded:
            return True
        
        try:
            if self.index_path.exists():
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    self._index = json.load(f)
                logger.info(f"[SKILLS] Loaded {self._index.get('total_skills', 0)} Claude skills")
            else:
                logger.warning(f"[SKILLS] Skills index not found at {self.index_path}")
                self._index = {'skills': {}, 'categories': {}}
            
            if self.lookup_path.exists():
                with open(self.lookup_path, 'r', encoding='utf-8') as f:
                    self._lookup = json.load(f)
            else:
                self._lookup = {'by_keyword': {}, 'by_category': {}, 'by_use_case': {}}
            
            self._loaded = True
            return True
            
        except Exception as e:
            logger.error(f"[SKILLS] Failed to load skills: {e}")
            self._index = {'skills': {}, 'categories': {}}
            self._lookup = {'by_keyword': {}, 'by_category': {}, 'by_use_case': {}}
            return False
    
    @property
    def total_skills(self) -> int:
        """Get total number of available skills."""
        self.load()
        return self._index.get('total_skills', 0)
    
    @property
    def categories(self) -> Dict[str, List[str]]:
        """Get skills grouped by category."""
        self.load()
        return self._index.get('categories', {})
    
    def list_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available skills, optionally filtered by category.
        
        Args:
            category: Optional category filter (development, business, creative, etc.)
            
        Returns:
            List of skill summaries with id, name, description, and category
        """
        self.load()
        skills = self._index.get('skills', {})
        
        result = []
        for skill_id, skill in skills.items():
            if category and skill.get('category') != category:
                continue
            result.append({
                'id': skill_id,
                'name': skill.get('name', skill_id),
                'description': skill.get('description', '')[:200],
                'category': skill.get('category', 'general'),
                'use_cases': skill.get('use_cases', [])[:3],
            })
        
        return sorted(result, key=lambda x: x['name'])
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details of a specific skill.
        
        Args:
            skill_id: The skill identifier (e.g., 'lead-research-assistant')
            
        Returns:
            Full skill data including instructions, examples, and resources
        """
        self.load()
        return self._index.get('skills', {}).get(skill_id)
    
    def get_skill_instructions(self, skill_id: str) -> Optional[str]:
        """
        Get just the instructions for a skill.
        
        Args:
            skill_id: The skill identifier
            
        Returns:
            The skill's instructions text
        """
        skill = self.get_skill(skill_id)
        if skill:
            return skill.get('instructions', skill.get('full_content', ''))
        return None
    
    def search_skills(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant skills based on a query.
        
        Args:
            query: Search query (natural language description of need)
            max_results: Maximum number of results to return
            
        Returns:
            List of matching skills with relevance scores
        """
        self.load()
        
        query_lower = query.lower()
        words = re.findall(r'\b\w+\b', query_lower)
        
        # Score each skill based on matches
        scores: Dict[str, float] = {}
        skills = self._index.get('skills', {})
        
        for skill_id, skill in skills.items():
            score = 0.0
            
            # Check name match
            if any(w in skill.get('name', '').lower() for w in words):
                score += 5.0
            
            # Check description match
            desc = skill.get('description', '').lower()
            for word in words:
                if word in desc:
                    score += 2.0
            
            # Check keyword match
            keywords = [k.lower() for k in skill.get('keywords', [])]
            for word in words:
                if word in keywords:
                    score += 3.0
            
            # Check use case match
            use_cases = ' '.join(skill.get('use_cases', [])).lower()
            for word in words:
                if word in use_cases:
                    score += 2.5
            
            # Check category match
            if any(w in skill.get('category', '').lower() for w in words):
                score += 1.5
            
            if score > 0:
                scores[skill_id] = score
        
        # Sort by score and return top results
        sorted_skills = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for skill_id, score in sorted_skills[:max_results]:
            skill = skills[skill_id]
            results.append({
                'id': skill_id,
                'name': skill.get('name', skill_id),
                'description': skill.get('description', '')[:300],
                'category': skill.get('category', 'general'),
                'relevance_score': round(score, 2),
                'use_cases': skill.get('use_cases', [])[:3],
            })
        
        return results
    
    def find_skill_for_task(self, task_description: str) -> Optional[Dict[str, Any]]:
        """
        Find the best matching skill for a given task.
        
        Args:
            task_description: Description of what the user wants to accomplish
            
        Returns:
            Best matching skill or None if no good match found
        """
        results = self.search_skills(task_description, max_results=1)
        if results and results[0].get('relevance_score', 0) >= 3.0:
            return self.get_skill(results[0]['id'])
        return None
    
    def get_skill_resource_path(self, skill_id: str, resource_name: str) -> Optional[Path]:
        """
        Get the path to a skill's resource file.
        
        Args:
            skill_id: The skill identifier
            resource_name: Name of the resource file/directory
            
        Returns:
            Path to the resource or None if not found
        """
        resource_path = self.library_path / skill_id / resource_name
        if resource_path.exists():
            return resource_path
        return None
    
    def get_skills_summary_for_prompt(self) -> str:
        """
        Get a condensed summary of all skills for inclusion in system prompts.
        
        Returns:
            Markdown-formatted summary suitable for Claude's context
        """
        self.load()
        
        lines = [
            "## Available Specialized Skills",
            "",
            "I have access to specialized skills that enhance my capabilities:",
            ""
        ]
        
        for category, skill_ids in sorted(self.categories.items()):
            lines.append(f"### {category.title()}")
            for skill_id in skill_ids:
                skill = self.get_skill(skill_id)
                if skill:
                    lines.append(f"- **{skill.get('name', skill_id)}**: {skill.get('description', '')[:100]}...")
            lines.append("")
        
        lines.extend([
            "",
            "When a task matches one of these skills, I will automatically apply the relevant specialized knowledge.",
            "Ask me about any skill to learn more or request I use it for your task.",
        ])
        
        return '\n'.join(lines)
    
    def get_skill_activation_prompt(self, skill_id: str) -> Optional[str]:
        """
        Get the activation prompt for a skill (instructions + context).
        
        This is used to inject skill-specific instructions when Nicole
        recognizes a task that would benefit from the skill.
        
        Args:
            skill_id: The skill identifier
            
        Returns:
            Formatted prompt to activate the skill
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return None
        
        return f"""
## Activating Skill: {skill.get('name', skill_id)}

{skill.get('description', '')}

### Instructions
{skill.get('instructions', '')}

### Examples
{skill.get('examples', '')}

---
Apply this skill to the current task while maintaining my helpful, accurate, and honest approach.
"""


# Global instance
claude_skills_service = ClaudeSkillsService()


# Convenience functions for direct access
def get_skill(skill_id: str) -> Optional[Dict[str, Any]]:
    """Get a skill by ID."""
    return claude_skills_service.get_skill(skill_id)


def search_skills(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search for skills matching a query."""
    return claude_skills_service.search_skills(query, max_results)


def list_all_skills() -> List[Dict[str, Any]]:
    """List all available skills."""
    return claude_skills_service.list_skills()


def get_skills_for_prompt() -> str:
    """Get skills summary for system prompt."""
    return claude_skills_service.get_skills_summary_for_prompt()


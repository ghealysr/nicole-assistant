#!/usr/bin/env python3
"""
Parse Claude Skills from SKILL.md files and create a unified skills index.

This script parses all SKILL.md files from the awesome-claude-skills repository
and creates a JSON index that Nicole can use to understand and apply skills.
"""

import os
import json
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown content."""
    frontmatter = {}
    body = content
    
    # Check for YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
            except yaml.YAMLError:
                pass
    
    return frontmatter, body


def extract_sections(body: str) -> Dict[str, str]:
    """Extract sections from markdown body."""
    sections = {}
    current_section = "overview"
    current_content = []
    
    for line in body.split('\n'):
        if line.startswith('## '):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section
            current_section = line[3:].strip().lower().replace(' ', '_')
            current_content = []
        else:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def extract_keywords(body: str) -> List[str]:
    """Extract keywords from the skill body."""
    keywords = []
    
    # Look for explicit keywords
    keyword_match = re.search(r'\*\*Keywords?\*\*:?\s*(.+)', body, re.IGNORECASE)
    if keyword_match:
        keywords.extend([k.strip() for k in keyword_match.group(1).split(',')])
    
    return keywords


def extract_use_cases(body: str) -> List[str]:
    """Extract use cases from 'When to Use' sections."""
    use_cases = []
    
    # Look for "When to Use" section
    when_match = re.search(r'## When to Use.*?\n((?:[-*]\s+.+\n?)+)', body, re.IGNORECASE)
    if when_match:
        lines = when_match.group(1).strip().split('\n')
        for line in lines:
            cleaned = re.sub(r'^[-*]\s+', '', line.strip())
            if cleaned:
                use_cases.append(cleaned)
    
    return use_cases


def parse_skill_file(skill_path: Path) -> Optional[Dict[str, Any]]:
    """Parse a single SKILL.md file."""
    try:
        content = skill_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {skill_path}: {e}")
        return None
    
    frontmatter, body = parse_frontmatter(content)
    sections = extract_sections(body)
    keywords = extract_keywords(body)
    use_cases = extract_use_cases(body)
    
    # Get skill directory name
    skill_dir = skill_path.parent.name
    
    # Determine category based on README classification or directory name
    category = categorize_skill(skill_dir, frontmatter.get('description', ''))
    
    # Check for associated resources
    resources = []
    skill_parent = skill_path.parent
    for item in skill_parent.iterdir():
        if item.name != 'SKILL.md' and item.name != 'LICENSE.txt':
            resources.append({
                'name': item.name,
                'type': 'directory' if item.is_dir() else 'file',
                'path': str(item.relative_to(skill_parent))
            })
    
    return {
        'id': skill_dir,
        'name': frontmatter.get('name', skill_dir),
        'description': frontmatter.get('description', sections.get('overview', '')[:500]),
        'category': category,
        'keywords': keywords,
        'use_cases': use_cases,
        'instructions': sections.get('instructions', sections.get('overview', '')),
        'examples': sections.get('examples', ''),
        'has_resources': len(resources) > 0,
        'resources': resources,
        'source_path': str(skill_path.relative_to(skill_path.parent.parent.parent)),
        'full_content': body[:10000],  # Store first 10k chars for reference
    }


def categorize_skill(skill_id: str, description: str) -> str:
    """Categorize skill based on its ID and description."""
    desc_lower = description.lower()
    
    # Development & Code
    if any(term in skill_id or term in desc_lower for term in [
        'mcp', 'webapp', 'changelog', 'artifact', 'skill-creator', 'developer'
    ]):
        return 'development'
    
    # Business & Marketing
    if any(term in skill_id or term in desc_lower for term in [
        'lead', 'competitive', 'domain', 'brand', 'internal-comms', 'invoice'
    ]):
        return 'business'
    
    # Communication & Writing
    if any(term in skill_id or term in desc_lower for term in [
        'content', 'meeting', 'research-writer'
    ]):
        return 'communication'
    
    # Creative & Media
    if any(term in skill_id or term in desc_lower for term in [
        'canvas', 'image', 'slack-gif', 'theme', 'video', 'design'
    ]):
        return 'creative'
    
    # Productivity & Organization
    if any(term in skill_id or term in desc_lower for term in [
        'file-organizer', 'raffle', 'document'
    ]):
        return 'productivity'
    
    return 'general'


def find_all_skills(base_path: Path) -> List[Dict[str, Any]]:
    """Find and parse all SKILL.md files in the repository."""
    skills = []
    
    for skill_file in base_path.rglob('SKILL.md'):
        # Skip template skill
        if 'template-skill' in str(skill_file):
            continue
            
        skill = parse_skill_file(skill_file)
        if skill:
            skills.append(skill)
            print(f"  ✓ Parsed: {skill['name']}")
    
    return skills


def create_skills_index(skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create the final skills index with metadata."""
    # Group by category
    by_category = {}
    for skill in skills:
        cat = skill['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(skill['id'])
    
    return {
        'version': '1.0.0',
        'source': 'ComposioHQ/awesome-claude-skills',
        'parsed_at': datetime.utcnow().isoformat(),
        'total_skills': len(skills),
        'categories': by_category,
        'skills': {s['id']: s for s in skills}
    }


def create_skills_summary(skills: List[Dict[str, Any]]) -> str:
    """Create a human-readable summary of all skills."""
    summary_lines = [
        "# Nicole's Claude Skills Library",
        "",
        f"Total skills available: {len(skills)}",
        "",
        "## Skills by Category",
        ""
    ]
    
    # Group by category
    by_category = {}
    for skill in skills:
        cat = skill['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(skill)
    
    for category, cat_skills in sorted(by_category.items()):
        summary_lines.append(f"### {category.title()} ({len(cat_skills)} skills)")
        summary_lines.append("")
        for skill in sorted(cat_skills, key=lambda x: x['name']):
            summary_lines.append(f"- **{skill['name']}**: {skill['description'][:200]}...")
        summary_lines.append("")
    
    return '\n'.join(summary_lines)


def main():
    """Main entry point."""
    print("=" * 60)
    print("Claude Skills Parser for Nicole")
    print("=" * 60)
    
    # Define paths
    script_dir = Path(__file__).parent
    skills_repo = script_dir / 'claude-skills-library'
    output_dir = script_dir / 'claude-skills-index'
    
    if not skills_repo.exists():
        print(f"Error: Skills repository not found at {skills_repo}")
        print("Please clone https://github.com/ComposioHQ/awesome-claude-skills first")
        return 1
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nParsing skills from: {skills_repo}")
    print("-" * 40)
    
    # Find and parse all skills
    skills = find_all_skills(skills_repo)
    
    print("-" * 40)
    print(f"\nTotal skills parsed: {len(skills)}")
    
    # Create index
    index = create_skills_index(skills)
    
    # Save full index
    index_path = output_dir / 'skills_index.json'
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved skills index to: {index_path}")
    
    # Create and save summary
    summary = create_skills_summary(skills)
    summary_path = output_dir / 'skills_summary.md'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"✓ Saved skills summary to: {summary_path}")
    
    # Create a lightweight lookup for quick skill matching
    lookup = {
        'by_keyword': {},
        'by_category': {},
        'by_use_case': {},
    }
    
    for skill in skills:
        # Index by keywords
        for kw in skill.get('keywords', []):
            kw_lower = kw.lower()
            if kw_lower not in lookup['by_keyword']:
                lookup['by_keyword'][kw_lower] = []
            lookup['by_keyword'][kw_lower].append(skill['id'])
        
        # Index by category
        cat = skill['category']
        if cat not in lookup['by_category']:
            lookup['by_category'][cat] = []
        lookup['by_category'][cat].append(skill['id'])
        
        # Index by use case keywords
        for uc in skill.get('use_cases', []):
            words = re.findall(r'\b\w+\b', uc.lower())
            for word in words:
                if len(word) > 3:  # Skip short words
                    if word not in lookup['by_use_case']:
                        lookup['by_use_case'][word] = []
                    if skill['id'] not in lookup['by_use_case'][word]:
                        lookup['by_use_case'][word].append(skill['id'])
    
    lookup_path = output_dir / 'skills_lookup.json'
    with open(lookup_path, 'w', encoding='utf-8') as f:
        json.dump(lookup, f, indent=2)
    print(f"✓ Saved skills lookup to: {lookup_path}")
    
    print("\n" + "=" * 60)
    print("Skills parsing complete!")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    exit(main())


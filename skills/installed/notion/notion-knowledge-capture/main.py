#!/usr/bin/env python3
"""
Notion Knowledge Capture Skill

Transforms conversations and discussions into structured documentation pages in Notion.
Uses Notion MCP tools to search, create, and organize knowledge.
"""

import json
import os
import sys

def main():
    """Main entry point for knowledge capture skill."""
    raw_input = os.environ.get("SKILL_INPUT", "{}")
    
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError:
        payload = {}
    
    # Extract parameters
    content = payload.get("content", "")
    title = payload.get("title", "Knowledge Capture")
    destination = payload.get("destination", None)  # Page ID or database ID
    content_type = payload.get("content_type", "general")  # concept, how-to, decision, faq, etc.
    
    # This skill is a workflow guide - the actual execution happens via MCP tools
    # Nicole will use the Notion MCP tools (notion_search, notion_create_page, etc.)
    # based on the workflow described in SKILL.md
    
    result = {
        "success": True,
        "message": f"Knowledge capture workflow initiated for: {title}",
        "workflow": "notion-knowledge-capture",
        "instructions": [
            "1. Use notion_search to find appropriate destination",
            "2. Structure content based on type: " + content_type,
            "3. Use notion_create_page to save the documentation",
            "4. Link from relevant hub pages for discoverability"
        ],
        "parameters_received": {
            "title": title,
            "content_type": content_type,
            "has_destination": destination is not None,
            "content_length": len(content)
        },
        "next_steps": "Nicole will execute the workflow using Notion MCP tools"
    }
    
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())


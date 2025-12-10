#!/usr/bin/env python3
"""
Notion Meeting Intelligence Skill

Prepares meeting materials by gathering context from Notion, enriching with research,
and creating both internal pre-read and external agenda saved to Notion.
"""

import json
import os
import sys

def main():
    """Main entry point for meeting intelligence skill."""
    raw_input = os.environ.get("SKILL_INPUT", "{}")
    
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError:
        payload = {}
    
    # Extract parameters
    meeting_topic = payload.get("topic", "")
    attendees = payload.get("attendees", [])
    meeting_type = payload.get("type", "internal")  # internal, external, decision, status
    related_project = payload.get("project_id", None)
    
    result = {
        "success": True,
        "message": f"Meeting prep workflow initiated for: {meeting_topic}",
        "workflow": "notion-meeting-intelligence",
        "instructions": [
            "1. Use notion_search to find related project pages and previous meetings",
            "2. Use notion_get_page to fetch relevant context",
            "3. Create internal pre-read document with notion_create_page",
            "4. Create external agenda document with notion_create_page",
            "5. Link both documents to the project page"
        ],
        "parameters_received": {
            "topic": meeting_topic,
            "attendees_count": len(attendees) if isinstance(attendees, list) else 0,
            "meeting_type": meeting_type,
            "has_project": related_project is not None
        },
        "next_steps": "Nicole will execute the workflow using Notion MCP tools"
    }
    
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())


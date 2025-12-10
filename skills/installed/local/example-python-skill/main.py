#!/usr/bin/env python3
"""
Example Python Skill for Nicole V7

This skill demonstrates how Nicole can execute Python scripts.
It reads input from the SKILL_INPUT environment variable and returns
a structured response.

Usage:
    Ask Nicole: "Run the example python skill"
    Or: "Test the hello world skill with name John"
"""

import json
import os
import sys
from datetime import datetime

def main():
    """Main entry point for the skill."""
    # Read input payload from environment
    raw_input = os.environ.get("SKILL_INPUT", "{}")
    
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError:
        payload = {}
    
    # Extract parameters
    name = payload.get("name", "World")
    action = payload.get("action", "greet")
    
    # Perform the requested action
    if action == "greet":
        message = f"Hello, {name}! This is Nicole's example Python skill."
    elif action == "time":
        message = f"Hello {name}! The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    elif action == "echo":
        message = f"You said: {payload.get('message', '(nothing)')}"
    else:
        message = f"Unknown action '{action}'. Available actions: greet, time, echo"
    
    # Output structured result
    result = {
        "success": True,
        "message": message,
        "input_received": payload,
        "timestamp": datetime.utcnow().isoformat(),
        "skill_version": "1.0.0"
    }
    
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())

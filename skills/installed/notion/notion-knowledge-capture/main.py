#!/usr/bin/env python3
"""
Notion Knowledge Capture Skill

Creates or updates a page in Notion using the MCP tools exposed via the Docker gateway.
Returns links and a short summary so Nicole can report back in chat.
"""

import json
import os
import sys
import requests

MCP_RPC_URL = os.environ.get("MCP_RPC_URL", "http://127.0.0.1:3100/rpc")


def call_mcp_tool(name: str, arguments: dict) -> dict:
    """Call MCP tool via the HTTP bridge."""
    try:
        resp = requests.post(
            MCP_RPC_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            return {"error": data["error"].get("message", "unknown error")}
        return data.get("result", {})
    except Exception as e:
        return {"error": str(e)}


def main():
    raw_input = os.environ.get("SKILL_INPUT", "{}")
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError:
        payload = {}

    title = payload.get("title", "Knowledge Capture")
    content = payload.get("content", "")
    parent_id = payload.get("parent_id") or payload.get("destination")  # page or database
    content_type = payload.get("content_type", "general")

    # If no parent provided, try to find a page by title heuristic
    if not parent_id:
        search_res = call_mcp_tool(
            "notion_search",
            {"query": "Command Center", "page_size": 1},
        )
        if search_res.get("content"):
            parent_id = search_res["content"][0].get("id")

    if not parent_id:
        result = {
            "success": False,
            "message": "No parent page/database provided and none found. Please supply parent_id.",
        }
        print(json.dumps(result, indent=2))
        return 0

    # Create the page
    create_args = {
        "parent_id": parent_id,
        "parent_type": "page",  # if you pass a database id, change to 'database'
        "title": title,
        "content": f"Type: {content_type}\n\n{content}",
    }
    create_res = call_mcp_tool("notion_create_page", create_args)

    if "error" in create_res:
        result = {
            "success": False,
            "message": f"Failed to create page: {create_res['error']}",
        }
        print(json.dumps(result, indent=2))
        return 0

    created = create_res.get("content") or {}
    url = created.get("url") or created.get("public_url")

    result = {
        "success": True,
        "message": f"Created/updated knowledge page: {title}",
        "workflow": "notion-knowledge-capture",
        "parent_id": parent_id,
        "page_url": url,
        "content_length": len(content),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


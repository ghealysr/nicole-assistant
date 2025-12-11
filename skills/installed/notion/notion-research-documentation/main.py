#!/usr/bin/env python3
"""
Notion Research Documentation Skill

Searches Notion, pulls top matches, and creates a research doc with citations.
Returns the created page URL and a brief summary for chat.
"""

import json
import os
import sys
import requests

MCP_RPC_URL = os.environ.get("MCP_RPC_URL", "http://127.0.0.1:3100/rpc")


def call_mcp_tool(name: str, arguments: dict) -> dict:
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

    topic = payload.get("topic", "Research")
    parent_id = payload.get("parent_id")
    page_size = int(payload.get("page_size", 5))
    format_type = payload.get("format", "summary")

    # Find a parent if not provided
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
            "message": "No parent page provided and none found. Please supply parent_id.",
        }
        print(json.dumps(result, indent=2))
        return 0

    # Search for relevant pages
    search_res = call_mcp_tool(
        "notion_search",
        {"query": topic, "page_size": page_size},
    )
    if "error" in search_res:
        result = {"success": False, "message": f"Search failed: {search_res['error']}"}
        print(json.dumps(result, indent=2))
        return 0

    pages = search_res.get("content") or []
    summary_lines = []
    citations = []
    for p in pages:
        title = p.get("properties", {}).get("title", [{}])
        if isinstance(title, list) and title:
            title_text = title[0].get("plain_text") or title[0].get("text", {}).get("content")
        else:
            title_text = p.get("url", "Untitled")
        summary_lines.append(f"- {title_text}")
        citations.append(p.get("url"))

    summary_block = "\n".join(summary_lines) if summary_lines else "No pages found."
    citations_block = "\n".join([c for c in citations if c]) or "No citations."

    body = f"# Research: {topic}\n\nFormat: {format_type}\n\nFindings:\n{summary_block}\n\nCitations:\n{citations_block}"

    create_res = call_mcp_tool(
        "notion_create_page",
        {
            "parent_id": parent_id,
            "parent_type": "page",
            "title": f"Research - {topic}",
            "content": body,
        },
    )

    if "error" in create_res:
        result = {"success": False, "message": f"Create page failed: {create_res['error']}"}
        print(json.dumps(result, indent=2))
        return 0

    created = create_res.get("content") or {}
    url = created.get("url")

    result = {
        "success": True,
        "message": f"Research doc created for '{topic}'",
        "workflow": "notion-research-documentation",
        "parent_id": parent_id,
        "page_url": url,
        "found": len(pages),
        "summary": summary_block,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


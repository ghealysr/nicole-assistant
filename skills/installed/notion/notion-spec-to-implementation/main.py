#!/usr/bin/env python3
"""
Notion Spec to Implementation Skill

Takes a spec page, creates an implementation plan page, and (optionally) creates tasks
in a target database. Returns URLs so Nicole can report back in chat.
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

    spec_id = payload.get("spec_id")
    task_database_id = payload.get("task_database_id")
    parent_id = payload.get("parent_id")  # where to place the implementation plan
    plan_title = payload.get("plan_title", "Implementation Plan")

    # Resolve parent if not provided
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

    # Fetch spec (optional step just to verify)
    spec_url = None
    if spec_id:
        spec_res = call_mcp_tool("notion_get_page", {"page_id": spec_id})
        if "error" in spec_res:
            print(json.dumps({"success": False, "message": f"Failed to fetch spec: {spec_res['error']}"}, indent=2))
            return 0
        spec_url = (spec_res.get("content") or {}).get("url")

    # Create implementation plan page
    body = f"# Implementation Plan\n\nSpec: {spec_url or spec_id or 'not provided'}\n\nSections:\n- Requirements\n- Tasks\n- Acceptance Criteria\n- Milestones\n"
    plan_res = call_mcp_tool(
        "notion_create_page",
        {
            "parent_id": parent_id,
            "parent_type": "page",
            "title": plan_title,
            "content": body,
        },
    )
    if "error" in plan_res:
        print(json.dumps({"success": False, "message": f"Create plan failed: {plan_res['error']}"}, indent=2))
        return 0

    plan_url = (plan_res.get("content") or {}).get("url")

    # Optionally create tasks in a database
    created_tasks = []
    if task_database_id and isinstance(payload.get("tasks"), list):
        for t in payload["tasks"]:
            title = t.get("title") or "Task"
            props = t.get("properties") or {}
            # Minimal properties: Name
            db_item = call_mcp_tool(
                "notion_create_database_item",
                {
                    "database_id": task_database_id,
                    "properties": {
                        "Name": {"title": [{"text": {"content": title}}]},
                        **props,
                    },
                },
            )
            if "error" in db_item:
                created_tasks.append({"title": title, "error": db_item["error"]})
            else:
                created_tasks.append({"title": title, "status": "created"})

    result = {
        "success": True,
        "message": "Implementation plan created",
        "workflow": "notion-spec-to-implementation",
        "plan_url": plan_url,
        "spec_url": spec_url,
        "tasks_created": created_tasks,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


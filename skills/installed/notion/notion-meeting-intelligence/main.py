#!/usr/bin/env python3
"""
Notion Meeting Intelligence Skill

Creates meeting prep docs (pre-read + agenda) in Notion using MCP tools.
Returns links so Nicole can report back in chat.
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

    topic = payload.get("topic", "Meeting")
    attendees = payload.get("attendees", [])
    meeting_type = payload.get("type", "internal")
    project_id = payload.get("project_id")
    parent_id = payload.get("parent_id") or project_id

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
            "message": "No parent page/database provided and none found. Please supply parent_id or project_id.",
        }
        print(json.dumps(result, indent=2))
        return 0

    def create_page(title: str, body: str):
        return call_mcp_tool(
            "notion_create_page",
            {
                "parent_id": parent_id,
                "parent_type": "page",
                "title": title,
                "content": body,
            },
        )

    pre_read_title = f"{topic} - Pre-Read"
    agenda_title = f"{topic} - Agenda"

    attendees_text = ", ".join(attendees) if isinstance(attendees, list) else str(attendees)
    pre_read_body = f"Type: {meeting_type}\nAttendees: {attendees_text}\n\nContext:\n(Insert key background here)"
    agenda_body = f"Type: {meeting_type}\nAttendees: {attendees_text}\n\nAgenda:\n- Topic 1\n- Topic 2\n- Decisions\n- Next steps"

    pre_read = create_page(pre_read_title, pre_read_body)
    agenda = create_page(agenda_title, agenda_body)

    if "error" in pre_read or "error" in agenda:
        result = {
            "success": False,
            "message": f"Failed to create meeting docs: {pre_read.get('error') or agenda.get('error')}",
        }
        print(json.dumps(result, indent=2))
        return 0

    result = {
        "success": True,
        "message": f"Meeting docs created for {topic}",
        "workflow": "notion-meeting-intelligence",
        "parent_id": parent_id,
        "pre_read_url": (pre_read.get("content") or {}).get("url"),
        "agenda_url": (agenda.get("content") or {}).get("url"),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


import json
from typing import List
from anthropic import Anthropic

from app.config import settings


anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def keyword_route(query: str) -> List[str]:
    q = query.lower()
    agents = ["nicole_core"]
    if any(w in q for w in ["design", "mockup", "image", "logo"]):
        agents.append("design_agent")
    if any(w in q for w in ["client", "proposal", "pricing"]):
        agents.append("business_agent")
    if any(w in q for w in ["seo", "keywords", "optimize"]):
        agents.append("seo_agent")
    if any(w in q for w in ["bug", "error", "fix", "issue"]):
        agents.append("error_agent")
    return agents


async def route_to_agents(query: str, context: dict) -> List[str]:
    try:
        classification = await anthropic.messages.create(
            model="claude-haiku-4-5-20250514",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""Classify which agents are needed.
Available agents:
1 nicole_core - Base personality, general capability
2 design_agent - Web design, FLUX images, mockups
3 business_agent - Clients, pricing, proposals
4 code_review_agent - Security, performance
5 seo_agent - Keywords, optimization
6 error_agent - Debugging, troubleshooting
7 frontend_developer - React, UI implementation
8 code_reviewer - Code quality, standards
9 self_audit_agent - Nicole's weekly reflection

Query: {query}
Context: {json.dumps(context)}
Respond with JSON array of agent names."""
            }]
        )
        agents = json.loads(classification.content[0].text)
        return agents
    except Exception:
        return keyword_route(query)

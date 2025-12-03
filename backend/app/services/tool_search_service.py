"""
Nicole V7 - Tool Search Service

Implements Anthropic's Tool Search Tool pattern for dynamic tool discovery.

Problem: With 15-20+ MCP servers and 100+ potential tools, loading all tool
definitions into every Claude request wastes tokens and confuses the model.

Solution: A "meta-tool" that lets Nicole search for relevant tools dynamically.
Only tools actually needed for a request get loaded into context.

Impact: 85% reduction in tool-related tokens (Anthropic benchmark)

How it works:
1. Tools are registered with descriptions and tags (defer_loading=True)
2. Nicole receives ONLY the tool_search tool in her initial context
3. When she needs a capability, she searches: "send email" → finds google_gmail_send
4. Relevant tools are dynamically injected for that request

Author: Nicole V7 Architecture
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from pathlib import Path

from app.skills.registry import load_registry, SkillMetadata

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories for organizing tools."""
    COMMUNICATION = "communication"   # Email, SMS, messaging
    DOCUMENTS = "documents"           # File operations, document processing
    CALENDAR = "calendar"             # Scheduling, events
    MEMORY = "memory"                 # Memory operations
    SEARCH = "search"                 # Web search, knowledge lookup
    MEDIA = "media"                   # Images, audio, video
    AUTOMATION = "automation"         # Workflows, scheduled tasks
    INTEGRATION = "integration"       # External service connections
    DEVELOPMENT = "development"       # Code, debugging
    HEALTH = "health"                 # Health data, fitness
    SPORTS = "sports"                 # Sports data, predictions
    FINANCE = "finance"               # Financial data, budgets
    BROWSER = "browser"               # Web browsing, automation
    REASONING = "reasoning"           # Think tool, analysis


@dataclass
class RegisteredTool:
    """A tool registered for search."""
    name: str
    description: str
    category: ToolCategory
    tags: List[str] = field(default_factory=list)
    mcp_server: Optional[str] = None  # Which MCP server provides this
    examples: List[str] = field(default_factory=list)  # Example use cases
    schema: Optional[Dict[str, Any]] = None  # Full tool schema
    defer_loading: bool = True  # Whether to defer loading until needed
    usage_count: int = 0  # How often this tool is used
    last_used: Optional[datetime] = None
    
    def matches_query(self, query: str) -> float:
        """
        Calculate relevance score for a search query.
        Returns 0-1 score.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        score = 0.0
        
        # Exact name match (highest weight)
        if query_lower in self.name.lower():
            score += 0.5
        
        # Description contains query
        desc_lower = self.description.lower()
        if query_lower in desc_lower:
            score += 0.3
        
        # Word overlap with description
        desc_words = set(desc_lower.split())
        overlap = len(query_words & desc_words)
        if overlap > 0:
            score += 0.1 * min(overlap, 3)
        
        # Tag matching
        for tag in self.tags:
            if query_lower in tag.lower() or tag.lower() in query_lower:
                score += 0.2
        
        # Example matching
        for example in self.examples:
            if query_lower in example.lower():
                score += 0.15
        
        # Category matching (semantic)
        category_keywords = {
            ToolCategory.COMMUNICATION: ["send", "email", "message", "notify", "sms", "text"],
            ToolCategory.DOCUMENTS: ["file", "document", "read", "write", "pdf", "upload"],
            ToolCategory.CALENDAR: ["schedule", "event", "meeting", "calendar", "remind"],
            ToolCategory.MEMORY: ["remember", "recall", "memory", "store", "forget"],
            ToolCategory.SEARCH: ["search", "find", "lookup", "query", "google"],
            ToolCategory.MEDIA: ["image", "photo", "video", "audio", "generate"],
            ToolCategory.BROWSER: ["browse", "web", "page", "click", "navigate"],
            ToolCategory.HEALTH: ["health", "fitness", "workout", "calories", "sleep"],
            ToolCategory.SPORTS: ["sports", "game", "score", "team", "predict"],
        }
        
        if self.category in category_keywords:
            for keyword in category_keywords[self.category]:
                if keyword in query_lower:
                    score += 0.15
                    break
        
        # Boost recently used tools slightly
        if self.last_used and self.usage_count > 0:
            # Small boost for frequently used tools
            score += min(0.1, self.usage_count * 0.01)
        
        return min(1.0, score)


# The Tool Search Tool definition for Claude
TOOL_SEARCH_DEFINITION = {
    "name": "search_tools",
    "description": """Search for available tools based on what you need to accomplish.

Use this BEFORE attempting to use a tool you're not sure exists. This searches
Nicole's available capabilities and returns relevant tools with their descriptions.

Examples:
- "send email" → finds gmail_send, outlook_send tools
- "create image" → finds flux_generate, dalle_generate tools
- "check calendar" → finds google_calendar_list, google_calendar_create tools
- "web search" → finds google_search, brave_search tools

After finding a tool, you can use it in your next action.
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What capability are you looking for? Be specific."
            },
            "category": {
                "type": "string",
                "enum": [c.value for c in ToolCategory],
                "description": "Optional: Filter by category"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of tools to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILLS_REGISTRY_PATH = PROJECT_ROOT / "skills" / "registry.json"


class ToolSearchService:
    """
    Service for dynamic tool discovery and management.
    
    This service:
    1. Maintains a registry of all available tools
    2. Provides semantic search over tools
    3. Dynamically loads tool definitions when needed
    4. Tracks tool usage for optimization
    """
    
    def __init__(self):
        self._registry: Dict[str, RegisteredTool] = {}
        self._loaded_tools: Set[str] = set()  # Currently loaded tool names
        self._initialize_core_tools()
        self._load_skills_from_registry()
        logger.info(f"[TOOL SEARCH] Service initialized with {len(self._registry)} tools")
    
    def _initialize_core_tools(self):
        """Register core tools that are always available."""
        # Think tool is always available
        self.register_tool(
            name="think",
            description="Reason through complex decisions step by step. Use before multi-step operations.",
            category=ToolCategory.REASONING,
            tags=["reasoning", "planning", "decision", "analyze"],
            examples=[
                "Think through which tools to use for this request",
                "Reason about ambiguous user request",
                "Plan a multi-step workflow"
            ],
            defer_loading=False  # Always loaded
        )
        
        # Memory tools
        self.register_tool(
            name="memory_search",
            description="Search Nicole's memory for information about the user, their preferences, past conversations, and stored knowledge.",
            category=ToolCategory.MEMORY,
            tags=["memory", "remember", "recall", "history", "preference"],
            examples=[
                "What do I know about the user's favorite color?",
                "Search for past conversations about the project",
                "Recall user preferences"
            ],
            defer_loading=False  # Core functionality
        )
        
        self.register_tool(
            name="memory_store",
            description="Store new information in Nicole's memory for future recall.",
            category=ToolCategory.MEMORY,
            tags=["memory", "store", "save", "remember"],
            examples=[
                "Remember that the user's birthday is March 15",
                "Store this preference for future reference"
            ],
            defer_loading=False
        )
        
        # Document tools
        self.register_tool(
            name="document_search",
            description="Search through documents the user has uploaded to Nicole.",
            category=ToolCategory.DOCUMENTS,
            tags=["document", "file", "search", "pdf", "upload"],
            examples=[
                "Search uploaded documents for contract terms",
                "Find information in the user's files"
            ],
            defer_loading=False
        )
    
    def register_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        tags: Optional[List[str]] = None,
        mcp_server: Optional[str] = None,
        examples: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
        defer_loading: bool = True
    ) -> RegisteredTool:
        """
        Register a tool for search.
        
        Args:
            name: Tool name (must be unique)
            description: What the tool does
            category: Tool category
            tags: Searchable tags
            mcp_server: Which MCP server provides this
            examples: Example use cases
            schema: Full tool schema for Claude
            defer_loading: Whether to defer loading until needed
            
        Returns:
            The registered tool
        """
        if name in self._registry:
            logger.debug(f"[TOOL SEARCH] Tool {name} already registered, skipping duplicate registration")
            return self._registry[name]

        tool = RegisteredTool(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            mcp_server=mcp_server,
            examples=examples or [],
            schema=schema,
            defer_loading=defer_loading
        )
        
        self._registry[name] = tool
        
        if not defer_loading:
            self._loaded_tools.add(name)
        
        logger.debug(f"[TOOL SEARCH] Registered tool: {name} (defer: {defer_loading})")
        return tool
    
    def register_mcp_tools(
        self,
        mcp_server: str,
        tools: List[Dict[str, Any]]
    ) -> List[RegisteredTool]:
        """
        Register multiple tools from an MCP server.
        
        Args:
            mcp_server: MCP server name
            tools: List of tool definitions from MCP
            
        Returns:
            List of registered tools
        """
        registered = []
        
        for tool_def in tools:
            # Infer category from description
            category = self._infer_category(tool_def.get("description", ""))
            
            tool = self.register_tool(
                name=tool_def["name"],
                description=tool_def.get("description", ""),
                category=category,
                mcp_server=mcp_server,
                schema=tool_def,
                defer_loading=True
            )
            registered.append(tool)
        
        logger.info(f"[TOOL SEARCH] Registered {len(registered)} tools from {mcp_server}")
        return registered

    def _category_from_domain(self, domain: Optional[str]) -> ToolCategory:
        if not domain:
            return ToolCategory.INTEGRATION
        domain = domain.lower()
        mapping = {
            "docs": ToolCategory.DOCUMENTS,
            "document": ToolCategory.DOCUMENTS,
            "documents": ToolCategory.DOCUMENTS,
            "memory": ToolCategory.MEMORY,
            "automation": ToolCategory.AUTOMATION,
            "browser": ToolCategory.BROWSER,
            "media": ToolCategory.MEDIA,
            "image": ToolCategory.MEDIA,
            "research": ToolCategory.SEARCH,
            "search": ToolCategory.SEARCH,
            "development": ToolCategory.DEVELOPMENT,
            "engineering": ToolCategory.DEVELOPMENT,
            "sports": ToolCategory.SPORTS,
            "health": ToolCategory.HEALTH,
            "finance": ToolCategory.FINANCE,
        }
        return mapping.get(domain, ToolCategory.INTEGRATION)

    def register_skill(self, skill: SkillMetadata) -> Optional[RegisteredTool]:
        """Register a skill from the registry as a tool.
        
        Only registers skills that can be executed automatically.
        Manual skills (README-driven) are skipped.
        """
        # Executor types that can be run automatically
        EXECUTABLE_TYPES = {"python", "python_script", "node", "node_script", "cli", "command"}
        
        if skill.status != "installed":
            return None
        
        # Skip manual skills - they can't be executed programmatically
        if skill.executor.executor_type.lower() not in EXECUTABLE_TYPES:
            logger.debug(f"[TOOL SEARCH] Skipping manual skill: {skill.id}")
            return None
        if skill.setup_status not in {"ready"}:
            logger.debug(
                f"[TOOL SEARCH] Skill {skill.id} not registered (setup_status={skill.setup_status})"
            )
            return None

        description = f"{skill.description} (Skill)"
        tags = []
        domain = None
        examples = skill.usage_examples[:3]
        for cap in skill.capabilities:
            domain = domain or cap.domain
            tags.extend(cap.tags)
            if not examples and cap.description:
                examples.append(cap.description)

        category = self._category_from_domain(domain) if domain else self._infer_category(description)

        schema = {
            "name": skill.id,
            "description": description
            + ("\n\nExamples:\n- " + "\n- ".join(examples) if examples else ""),
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
                "description": (
                    "Parameters forwarded to the skill runner. "
                    "Consult the skill documentation before invoking."
                ),
            },
        }

        return self.register_tool(
            name=skill.id,
            description=description,
            category=category,
            tags=tags,
            examples=examples,
            schema=schema,
            defer_loading=True,
        )

    def _load_skills_from_registry(self) -> None:
        if not SKILLS_REGISTRY_PATH.exists():
            logger.info("[TOOL SEARCH] No skills registry found; skipping skill registration")
            return
        registry = load_registry(SKILLS_REGISTRY_PATH)
        count = 0
        for skill in registry.list_skills():
            if self.register_skill(skill):
                count += 1
        logger.info(f"[TOOL SEARCH] Registered {count} skills from registry")
    
    def _infer_category(self, description: str) -> ToolCategory:
        """Infer tool category from description."""
        desc_lower = description.lower()
        
        category_keywords = {
            ToolCategory.COMMUNICATION: ["email", "message", "send", "notify", "sms"],
            ToolCategory.DOCUMENTS: ["file", "document", "read", "write", "upload"],
            ToolCategory.CALENDAR: ["calendar", "schedule", "event", "meeting"],
            ToolCategory.BROWSER: ["browse", "web", "page", "click", "navigate"],
            ToolCategory.MEDIA: ["image", "photo", "video", "audio", "generate"],
            ToolCategory.HEALTH: ["health", "fitness", "workout", "medical"],
            ToolCategory.SPORTS: ["sports", "game", "score", "team"],
            ToolCategory.SEARCH: ["search", "find", "query", "lookup"],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                return category
        
        return ToolCategory.INTEGRATION
    
    def search_tools(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for tools matching a query.
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results
            
        Returns:
            List of matching tools with scores
        """
        results = []
        
        # Filter by category if provided
        tools_to_search = self._registry.values()
        if category:
            try:
                cat = ToolCategory(category)
                tools_to_search = [t for t in tools_to_search if t.category == cat]
            except ValueError:
                pass
        
        # Score each tool
        for tool in tools_to_search:
            score = tool.matches_query(query)
            if score > 0.1:  # Minimum threshold
                results.append((tool, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Format results
        formatted = []
        for tool, score in results[:limit]:
            formatted.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "mcp_server": tool.mcp_server,
                "relevance_score": round(score, 2),
                "examples": tool.examples[:2] if tool.examples else []
            })
        
        logger.info(f"[TOOL SEARCH] Query '{query}' found {len(formatted)} tools")
        return formatted
    
    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        """Get a registered tool by name."""
        return self._registry.get(name)
    
    def load_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load a tool's full schema for use.
        
        Marks the tool as loaded and updates usage stats.
        """
        tool = self._registry.get(name)
        if not tool:
            return None
        
        # Update usage stats
        tool.usage_count += 1
        tool.last_used = datetime.utcnow()
        self._loaded_tools.add(name)
        
        logger.debug(f"[TOOL SEARCH] Loaded tool: {name}")
        return tool.schema
    
    def get_tool_search_definition(self) -> Dict[str, Any]:
        """Get the Tool Search tool definition for Claude."""
        return TOOL_SEARCH_DEFINITION
    
    def get_always_loaded_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions that should always be in context."""
        tools = []
        
        for name, tool in self._registry.items():
            if not tool.defer_loading:
                if tool.schema:
                    tools.append(tool.schema)
                else:
                    # Generate basic schema
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    })
        
        return tools
    
    def get_prompt_injection(self) -> str:
        """
        Get the system prompt injection for tool search.
        
        This tells Nicole how to discover and use tools.
        """
        # Count available tools by category
        category_counts = {}
        for tool in self._registry.values():
            cat = tool.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        categories_summary = ", ".join([
            f"{cat}: {count}" for cat, count in sorted(category_counts.items())
        ])
        
        return f"""
## 🔧 TOOL DISCOVERY

You have access to {len(self._registry)} tools across these categories: {categories_summary}

Not all tools are loaded by default - use the `search_tools` tool to discover what's available.

**Before using a tool you're not sure about:**
1. Search for it: `search_tools(query="send email")`
2. Review the results to find the right tool
3. Use the tool by name

**Core tools always available:**
- `think` - Explicit reasoning (use liberally)
- `memory_search` - Search your memory
- `memory_store` - Store new memories
- `document_search` - Search uploaded documents
- `search_tools` - Find more tools

**Example workflow:**
1. User: "Send an email about the meeting"
2. You: `search_tools(query="send email")` → finds `gmail_send`
3. You: `gmail_send(to=..., subject=..., body=...)`
"""


# Global service instance
tool_search_service = ToolSearchService()


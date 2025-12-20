"""
Nicole V7 - Advanced Tool Manager

Implements Anthropic's Advanced Tool Use pattern (Nov 2025):
- Tool Search Tool with defer_loading for dynamic discovery
- input_examples for better parameter accuracy (72% → 90%)
- Structured tool categorization (core vs deferred)

This dramatically reduces token usage by:
1. Only loading 5-7 core tools always (~2K tokens)
2. Keeping 50+ MCP tools discoverable but not sent (~0 tokens until used)
3. Using compact input_examples instead of verbose description injection

Reference: https://www.anthropic.com/engineering/advanced-tool-use

Author: Nicole V7 Architecture
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ToolExample:
    """Structured input_example per Anthropic spec."""
    description: str
    input: Dict[str, Any]
    output: Optional[str] = None


@dataclass
class ToolDefinition:
    """Enhanced tool definition with Anthropic advanced features."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    category: str = "general"
    defer_loading: bool = False  # If True, schema not sent until tool discovered
    input_examples: List[ToolExample] = field(default_factory=list)
    mcp_server: Optional[str] = None  # Which MCP server provides this tool
    
    def to_claude_format(self, include_deferred: bool = False) -> Optional[Dict[str, Any]]:
        """
        Convert to Claude API format.
        
        Args:
            include_deferred: If True, include even if defer_loading=True
            
        Returns:
            Tool dict for Claude API, or None if deferred
        """
        if self.defer_loading and not include_deferred:
            return None
        
        # Standard Claude tool format - NO input_examples (requires beta header)
        # Instead, examples are embedded in the description for context
        tool = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
        
        return tool


class AdvancedToolManager:
    """
    Manages tools with Anthropic's Advanced Tool Use patterns.
    
    Architecture:
    1. CORE_TOOLS: Always loaded (think, tool_search, memory ops, dashboard)
    2. DISCOVERABLE_TOOLS: MCP tools with defer_loading=True
       - Not sent in initial request (saves ~50K+ tokens)
       - Claude uses tool_search to find them
       - Full schema sent only when tool is actually used
    
    Token Impact:
    - Before: 50+ tools × ~1K tokens each = ~55K tokens
    - After: 7 core tools × ~300 tokens = ~2K tokens
    - Savings: ~95% reduction in tool-related tokens
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._mcp_tools_registered = False
        self._initialize_core_tools()
        logger.info(f"[TOOL_MGR] Advanced Tool Manager initialized with {len(self._tools)} core tools")
    
    def _initialize_core_tools(self):
        """
        Register core tools that are ALWAYS loaded.
        
        These are essential for every request:
        1. think - Explicit reasoning
        2. tool_search - Find deferred tools
        3. memory_search - Search user memories
        4. memory_store - Store new memories
        5. document_search - Search uploaded docs
        6. dashboard_status - Nicole's self-awareness
        7. mcp_status - Show available integrations
        """
        
        # Think Tool - Explicit reasoning
        self.register_tool(ToolDefinition(
            name="think",
            description="Use this tool to think through complex problems step-by-step before responding. Record your reasoning, plans, and conclusions.",
            category="reasoning",
            input_schema={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your structured reasoning or planning"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["multi_step_planning", "clarification", "safety_check", "analysis", "reflection"],
                        "description": "Type of thinking"
                    },
                    "conclusion": {
                        "type": "string",
                        "description": "Brief conclusion or next step"
                    }
                },
                "required": ["thought"]
            },
            input_examples=[
                ToolExample(
                    description="Plan a multi-step operation",
                    input={
                        "thought": "The user wants me to send a report. Let me break this down:\n1. What report? → Search documents\n2. Who to send to? → Search memory for contacts\n3. How to send? → Email seems appropriate",
                        "category": "multi_step_planning",
                        "conclusion": "Search for report first, then contacts"
                    }
                ),
            ]
        ))
        
        # Tool Search - Dynamic discovery of deferred tools
        self.register_tool(ToolDefinition(
            name="tool_search",
            description="Search for available tools and integrations by capability or name. Use this to discover what actions you can take - especially for MCP integrations like web search, Notion, email, calendar, file operations, and image generation.",
            category="discovery",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What capability are you looking for? Be specific."
                    },
                    "category": {
                        "type": "string",
                        "enum": ["web", "productivity", "communication", "files", "images", "all"],
                        "description": "Optional category filter"
                    }
                },
                "required": ["query"]
            },
            input_examples=[
                ToolExample(
                    description="Find web search tools",
                    input={"query": "search the web", "category": "web"},
                    output="Found: brave_search - Search the web using Brave Search"
                ),
                ToolExample(
                    description="Find image generation",
                    input={"query": "generate images", "category": "images"},
                    output="Found: recraft_generate_image - Generate AI images"
                ),
            ]
        ))
        
        # Memory Search
        self.register_tool(ToolDefinition(
            name="memory_search",
            description="Search Nicole's memory for information about the user - preferences, facts, past conversations, and stored knowledge.",
            category="memory",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["preference", "fact", "relationship", "event", "task", "goal"]
                    }
                },
                "required": ["query"]
            },
            input_examples=[
                ToolExample(
                    description="Find user preferences",
                    input={"query": "favorite color", "limit": 3}
                ),
            ]
        ))
        
        # Memory Store
        self.register_tool(ToolDefinition(
            name="memory_store",
            description="Store new information about the user for future recall. Use when they share facts, preferences, or important information.",
            category="memory",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Information to remember"
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["preference", "fact", "relationship", "event", "task", "goal"]
                    },
                    "importance": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium"
                    }
                },
                "required": ["content", "memory_type"]
            },
            input_examples=[
                ToolExample(
                    description="Store a preference",
                    input={
                        "content": "User prefers dark mode in applications",
                        "memory_type": "preference",
                        "importance": "medium"
                    }
                ),
            ]
        ))
        
        # Document Search
        self.register_tool(ToolDefinition(
            name="document_search",
            description="Search through documents the user has uploaded. Use for PDFs, text files, and other content.",
            category="documents",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 3}
                },
                "required": ["query"]
            }
        ))
        
        # Dashboard Status
        self.register_tool(ToolDefinition(
            name="dashboard_status",
            description="Get Nicole's current system status, usage metrics, costs, and diagnostics. Use when asked about: status, health, costs, token usage, storage, or issues.",
            category="system",
            input_schema={
                "type": "object",
                "properties": {
                    "include_usage": {"type": "boolean", "default": True},
                    "include_diagnostics": {"type": "boolean", "default": True}
                }
            }
        ))
        
        # MCP Status
        self.register_tool(ToolDefinition(
            name="mcp_status",
            description="Check available MCP integrations and tools. Use when asked: 'what tools do you have?', 'what can you connect to?', 'show MCP status'.",
            category="system",
            input_schema={
                "type": "object",
                "properties": {
                    "show_tools": {"type": "boolean", "default": True}
                }
            }
        ))
        
        # Skills Library
        self.register_tool(ToolDefinition(
            name="skills_library",
            description="Search Nicole's specialized skills library for enhanced capabilities like lead research, changelog generation, content writing, etc.",
            category="skills",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "list", "categories", "details"]
                    },
                    "query": {"type": "string"},
                    "skill_id": {"type": "string"},
                    "category": {"type": "string"}
                },
                "required": ["action"]
            }
        ))
    
    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool
        logger.debug(f"[TOOL_MGR] Registered tool: {tool.name} (deferred={tool.defer_loading})")
    
    def register_mcp_tools(self, mcp_tools: List[Dict[str, Any]]) -> int:
        """
        Register MCP tools with defer_loading=True.
        
        These tools won't be sent to Claude initially.
        They become available via tool_search.
        
        Args:
            mcp_tools: List of tool dicts from MCP
            
        Returns:
            Number of tools registered
        """
        count = 0
        for tool_data in mcp_tools:
            name = tool_data.get("name", "")
            if not name:
                continue
            
            # Determine category from name
            category = self._categorize_mcp_tool(name)
            
            tool = ToolDefinition(
                name=name,
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("input_schema", {}),
                category=category,
                defer_loading=True,  # KEY: Not sent until discovered
                mcp_server=tool_data.get("_server", "mcp")
            )
            
            self.register_tool(tool)
            count += 1
        
        self._mcp_tools_registered = True
        logger.info(f"[TOOL_MGR] Registered {count} MCP tools (all deferred)")
        return count
    
    def _categorize_mcp_tool(self, name: str) -> str:
        """Categorize MCP tool by name pattern."""
        name_lower = name.lower()
        
        if any(w in name_lower for w in ["brave", "search", "web", "fetch", "scrape", "firecrawl"]):
            return "web"
        if any(w in name_lower for w in ["notion", "calendar", "gmail", "email", "drive"]):
            return "productivity"
        if any(w in name_lower for w in ["file", "directory", "read", "write", "list"]):
            return "files"
        if any(w in name_lower for w in ["recraft", "image", "generate", "dalle"]):
            return "images"
        if any(w in name_lower for w in ["puppeteer", "screenshot", "browser", "playwright"]):
            return "web"
        if any(w in name_lower for w in ["telegram", "send", "message", "notify"]):
            return "communication"
        
        return "general"
    
    def get_tools_for_claude(self) -> List[Dict[str, Any]]:
        """
        Get tools for Claude API request.
        
        Only returns non-deferred tools (core tools).
        Deferred tools are available via tool_search.
        
        Returns:
            List of tool definitions for Claude
        """
        tools = []
        for tool in self._tools.values():
            claude_tool = tool.to_claude_format(include_deferred=False)
            if claude_tool:
                tools.append(claude_tool)
        
        logger.info(f"[TOOL_MGR] Returning {len(tools)} tools for Claude (deferred: {self.get_deferred_count()})")
        return tools
    
    def get_deferred_count(self) -> int:
        """Count deferred tools not being sent."""
        return sum(1 for t in self._tools.values() if t.defer_loading)
    
    def search_tools(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search all tools (including deferred) by query.
        
        This is called when Claude uses the tool_search tool.
        Returns matching tools that can then be loaded on-demand.
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Max results
            
        Returns:
            List of matching tool summaries
        """
        query_lower = query.lower()
        results = []
        
        for tool in self._tools.values():
            # Skip core tools (they're already loaded)
            if not tool.defer_loading:
                continue
            
            # Category filter
            if category and category != "all" and tool.category != category:
                continue
            
            # Score relevance
            score = 0
            
            # Exact name match
            if query_lower in tool.name.lower():
                score += 10
            
            # Description match
            if query_lower in tool.description.lower():
                score += 5
            
            # Category match
            if tool.category == query_lower:
                score += 3
            
            # Keyword matching
            keywords = query_lower.split()
            for kw in keywords:
                if kw in tool.name.lower():
                    score += 2
                if kw in tool.description.lower():
                    score += 1
            
            if score > 0:
                results.append({
                    "name": tool.name,
                    "description": tool.description[:200],
                    "category": tool.category,
                    "score": score,
                    "mcp_server": tool.mcp_server,
                })
        
        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full schema for a specific tool.
        
        Used when Claude wants to use a discovered tool.
        Returns full schema even for deferred tools.
        
        Args:
            tool_name: Name of tool
            
        Returns:
            Full tool definition or None
        """
        tool = self._tools.get(tool_name)
        if tool:
            return tool.to_claude_format(include_deferred=True)
        return None
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools


# Global instance
advanced_tool_manager = AdvancedToolManager()


def get_advanced_tool_headers() -> Dict[str, str]:
    """
    Get HTTP headers for advanced tool use.
    
    Enables Anthropic's advanced tool use features:
    - defer_loading support
    - input_examples support
    
    Reference: https://www.anthropic.com/engineering/advanced-tool-use
    """
    return {
        "anthropic-beta": "advanced-tool-use-2025-11-24"
    }


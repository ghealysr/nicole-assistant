"""
Nicole V7 - MCP (Model Context Protocol) Integrations

This package provides MCP integrations for external services:
- Google Workspace (Gmail, Calendar, Drive)
- Notion (databases, pages)
- Telegram (messaging)
- Filesystem (safe file access)
- Sequential Thinking (reasoning visualization)
- Playwright (web automation)

Usage:
    from app.mcp import (
        mcp_manager,
        initialize_mcp,
        shutdown_mcp,
        get_mcp_tools,
        call_mcp_tool,
        google_mcp,
        notion_mcp,
        telegram_mcp,
        filesystem_mcp,
        sequential_thinking_mcp,
        playwright_mcp
    )

    # Initialize on startup
    await initialize_mcp()

    # Get tools for Claude
    tools = get_mcp_tools()

    # Call a tool
    result = await call_mcp_tool("gmail_search", {"query": "from:boss"})

    # Shutdown on app close
    await shutdown_mcp()
"""

# Core MCP manager
from app.mcp.alphawave_mcp_manager import (
    mcp_manager,
    AlphawaveMCPManager,
    FallbackMCPManager,
    MCPServerConfig,
    MCPServerStatus,
    MCPTool,
    initialize_mcp,
    shutdown_mcp,
    get_mcp_tools,
    call_mcp_tool
)

# Service-specific MCP wrappers
from app.mcp.alphawave_google_mcp import google_mcp, AlphawaveGoogleMCP
from app.mcp.alphawave_notion_mcp import notion_mcp, AlphawaveNotionMCP
from app.mcp.alphawave_telegram_mcp import telegram_mcp, AlphawaveTelegramMCP
from app.mcp.alphawave_filesystem_mcp import filesystem_mcp, AlphawaveFilesystemMCP
from app.mcp.alphawave_sequential_thinking_mcp import (
    sequential_thinking_mcp,
    AlphawaveSequentialThinkingMCP,
    ThinkingSession,
    ThinkingStep
)
from app.mcp.alphawave_playwright_mcp import playwright_mcp, AlphawavePlaywrightMCP


__all__ = [
    # Core
    "mcp_manager",
    "AlphawaveMCPManager",
    "FallbackMCPManager",
    "MCPServerConfig",
    "MCPServerStatus",
    "MCPTool",
    "initialize_mcp",
    "shutdown_mcp",
    "get_mcp_tools",
    "call_mcp_tool",
    
    # Service wrappers
    "google_mcp",
    "AlphawaveGoogleMCP",
    "notion_mcp",
    "AlphawaveNotionMCP",
    "telegram_mcp",
    "AlphawaveTelegramMCP",
    "filesystem_mcp",
    "AlphawaveFilesystemMCP",
    "sequential_thinking_mcp",
    "AlphawaveSequentialThinkingMCP",
    "ThinkingSession",
    "ThinkingStep",
    "playwright_mcp",
    "AlphawavePlaywrightMCP",
]


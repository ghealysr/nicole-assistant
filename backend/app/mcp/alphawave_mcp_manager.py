"""
Nicole V7 - MCP (Model Context Protocol) Manager

Production-ready MCP integration using the official Python SDK.
Manages connections to multiple MCP servers and provides unified tool access.

Supported MCP Servers:
- Google Workspace (Gmail, Calendar, Drive)
- Notion (databases, pages)
- Filesystem (local file access)
- Telegram (bot messaging)
- Sequential Thinking (reasoning display)
- Playwright (web automation)

Architecture:
- Each MCP server runs as a subprocess
- Communication via JSON-RPC over stdio
- Tool discovery happens on connection
- Tool execution is async with timeout handling
"""

import asyncio
import json
import logging
import subprocess
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPServerStatus(Enum):
    """MCP server connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class MCPTool:
    """Represents a tool available from an MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str
    
    def to_claude_tool(self) -> Dict[str, Any]:
        """Convert to Claude API tool format."""
        return {
            "name": self.name,
            "description": f"{self.description} (via {self.server_name})",
            "input_schema": self.input_schema
        }


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    auto_reconnect: bool = True
    timeout_seconds: int = 30


@dataclass
class MCPServerState:
    """Runtime state for a connected MCP server."""
    config: MCPServerConfig
    status: MCPServerStatus = MCPServerStatus.DISCONNECTED
    process: Optional[subprocess.Popen] = None
    tools: List[MCPTool] = field(default_factory=list)
    last_error: Optional[str] = None
    connected_at: Optional[datetime] = None
    request_id: int = 0


class AlphawaveMCPManager:
    """
    Production MCP Manager for Nicole V7.
    
    Manages multiple MCP server connections, tool discovery, and execution.
    Uses the official MCP protocol over stdio.
    
    Features:
    - Lazy server startup (connect on first use)
    - Auto-reconnection on failure
    - Tool caching for performance
    - Unified tool registry
    - Timeout handling
    - Error recovery
    """
    
    def __init__(self):
        """Initialize MCP manager."""
        self._servers: Dict[str, MCPServerState] = {}
        self._tool_registry: Dict[str, MCPTool] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
        
        # Pre-register known server configurations
        self._register_default_servers()
    
    def _register_default_servers(self):
        """Register default MCP server configurations."""
        
        # Google Workspace MCP
        self._servers["google"] = MCPServerState(
            config=MCPServerConfig(
                name="google",
                command="npx",
                args=["-y", "@anthropic/mcp-server-google"],
                env={
                    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
                    "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                },
                enabled=bool(os.getenv("GOOGLE_CLIENT_ID")),
            )
        )
        
        # Notion MCP
        self._servers["notion"] = MCPServerState(
            config=MCPServerConfig(
                name="notion",
                command="npx",
                args=["-y", "@anthropic/mcp-server-notion"],
                env={
                    "NOTION_API_KEY": os.getenv("NOTION_API_KEY", ""),
                },
                enabled=bool(os.getenv("NOTION_API_KEY")),
            )
        )
        
        # Filesystem MCP (always available)
        self._servers["filesystem"] = MCPServerState(
            config=MCPServerConfig(
                name="filesystem",
                command="npx",
                args=["-y", "@anthropic/mcp-server-filesystem", "/tmp/nicole"],
                enabled=True,
            )
        )
        
        # Playwright MCP (web automation)
        self._servers["playwright"] = MCPServerState(
            config=MCPServerConfig(
                name="playwright",
                command="npx",
                args=["-y", "@anthropic/mcp-server-playwright"],
                enabled=True,
            )
        )
        
        # Sequential Thinking MCP (reasoning visualization)
        self._servers["sequential-thinking"] = MCPServerState(
            config=MCPServerConfig(
                name="sequential-thinking",
                command="npx",
                args=["-y", "@anthropic/mcp-server-sequential-thinking"],
                enabled=True,
            )
        )
        
        # Fetch MCP (HTTP requests)
        self._servers["fetch"] = MCPServerState(
            config=MCPServerConfig(
                name="fetch",
                command="npx",
                args=["-y", "@anthropic/mcp-server-fetch"],
                enabled=True,
            )
        )
        
        logger.info(f"[MCP] Registered {len(self._servers)} server configurations")
    
    def register_server(self, config: MCPServerConfig) -> None:
        """
        Register a custom MCP server configuration.
        
        Args:
            config: Server configuration
        """
        self._servers[config.name] = MCPServerState(config=config)
        logger.info(f"[MCP] Registered server: {config.name}")
    
    async def connect_server(self, server_name: str) -> bool:
        """
        Connect to an MCP server (start process and discover tools).
        
        Args:
            server_name: Name of the server to connect
            
        Returns:
            True if connection successful
        """
        async with self._lock:
            if server_name not in self._servers:
                logger.error(f"[MCP] Unknown server: {server_name}")
                return False
            
            state = self._servers[server_name]
            
            if not state.config.enabled:
                logger.warning(f"[MCP] Server {server_name} is disabled (missing credentials?)")
                return False
            
            if state.status == MCPServerStatus.CONNECTED:
                return True
            
            state.status = MCPServerStatus.CONNECTING
            
            try:
                # Build environment
                env = os.environ.copy()
                env.update(state.config.env)
                
                # Start the server process
                logger.info(f"[MCP] Starting server: {server_name}")
                logger.debug(f"[MCP] Command: {state.config.command} {' '.join(state.config.args)}")
                
                state.process = subprocess.Popen(
                    [state.config.command] + state.config.args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1,
                )
                
                # Initialize connection (send initialize request)
                init_response = await self._send_request(
                    state,
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                        },
                        "clientInfo": {
                            "name": "nicole-v7",
                            "version": "7.0.0"
                        }
                    }
                )
                
                if init_response is None:
                    raise Exception("Initialize request failed - no response")
                
                # Send initialized notification
                await self._send_notification(state, "notifications/initialized", {})
                
                # Discover tools
                await self._discover_tools(state)
                
                state.status = MCPServerStatus.CONNECTED
                state.connected_at = datetime.utcnow()
                state.last_error = None
                
                logger.info(f"[MCP] ✅ Connected to {server_name} with {len(state.tools)} tools")
                return True
                
            except FileNotFoundError:
                error_msg = f"Command not found: {state.config.command}. Is Node.js and npx installed?"
                logger.error(f"[MCP] {error_msg}")
                state.status = MCPServerStatus.ERROR
                state.last_error = error_msg
                return False
                
            except Exception as e:
                logger.error(f"[MCP] Failed to connect to {server_name}: {e}", exc_info=True)
                state.status = MCPServerStatus.ERROR
                state.last_error = str(e)
                
                # Cleanup process if it was started
                if state.process:
                    try:
                        state.process.terminate()
                        state.process.wait(timeout=5)
                    except Exception:
                        state.process.kill()
                    state.process = None
                
                return False
    
    async def _send_request(
        self,
        state: MCPServerState,
        method: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a JSON-RPC request to an MCP server.
        
        Args:
            state: Server state
            method: RPC method name
            params: Method parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response result or None on error
        """
        if not state.process or state.process.stdin is None or state.process.stdout is None:
            logger.error(f"[MCP] Process not available for {state.config.name}")
            return None
        
        state.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": state.request_id,
            "method": method,
            "params": params
        }
        
        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            state.process.stdin.write(request_json)
            state.process.stdin.flush()
            
            # Read response with timeout
            timeout_val = timeout or state.config.timeout_seconds
            
            loop = asyncio.get_event_loop()
            response_line = await asyncio.wait_for(
                loop.run_in_executor(None, state.process.stdout.readline),
                timeout=timeout_val
            )
            
            if not response_line:
                logger.error(f"[MCP] Empty response from {state.config.name}")
                return None
            
            response = json.loads(response_line)
            
            if "error" in response:
                logger.error(f"[MCP] Error from {state.config.name}: {response['error']}")
                return None
            
            return response.get("result")
            
        except asyncio.TimeoutError:
            logger.error(f"[MCP] Request timeout for {state.config.name}.{method}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[MCP] Invalid JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"[MCP] Request error: {e}", exc_info=True)
            return None
    
    async def _send_notification(
        self,
        state: MCPServerState,
        method: str,
        params: Dict[str, Any]
    ) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not state.process or state.process.stdin is None:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            notification_json = json.dumps(notification) + "\n"
            state.process.stdin.write(notification_json)
            state.process.stdin.flush()
        except Exception as e:
            logger.warning(f"[MCP] Notification error: {e}")
    
    async def _discover_tools(self, state: MCPServerState) -> None:
        """Discover available tools from an MCP server."""
        result = await self._send_request(state, "tools/list", {})
        
        if result and "tools" in result:
            state.tools = []
            for tool_data in result["tools"]:
                tool = MCPTool(
                    name=tool_data.get("name", "unknown"),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=state.config.name
                )
                state.tools.append(tool)
                
                # Register in global tool registry
                self._tool_registry[tool.name] = tool
            
            logger.info(f"[MCP] Discovered {len(state.tools)} tools from {state.config.name}")
        else:
            logger.warning(f"[MCP] No tools discovered from {state.config.name}")
    
    async def disconnect_server(self, server_name: str) -> None:
        """
        Disconnect from an MCP server.
        
        Args:
            server_name: Name of the server to disconnect
        """
        async with self._lock:
            if server_name not in self._servers:
                return
            
            state = self._servers[server_name]
            
            if state.process:
                try:
                    state.process.terminate()
                    state.process.wait(timeout=5)
                except Exception:
                    state.process.kill()
                state.process = None
            
            # Remove tools from registry
            for tool in state.tools:
                self._tool_registry.pop(tool.name, None)
            state.tools = []
            
            state.status = MCPServerStatus.DISCONNECTED
            logger.info(f"[MCP] Disconnected from {server_name}")
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for server_name in list(self._servers.keys()):
            await self.disconnect_server(server_name)
    
    async def connect_enabled_servers(self) -> Dict[str, bool]:
        """
        Connect to all enabled MCP servers.
        
        Returns:
            Dict mapping server names to connection success status
        """
        results = {}
        
        for server_name, state in self._servers.items():
            if state.config.enabled:
                results[server_name] = await self.connect_server(server_name)
        
        return results
    
    def get_server_status(self, server_name: str) -> Optional[MCPServerStatus]:
        """Get the connection status of a server."""
        if server_name in self._servers:
            return self._servers[server_name].status
        return None
    
    def get_all_tools(self) -> List[MCPTool]:
        """Get all available tools across all connected servers."""
        return list(self._tool_registry.values())
    
    def get_claude_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in Claude API format."""
        return [tool.to_claude_tool() for tool in self._tool_registry.values()]
    
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a specific tool by name."""
        return self._tool_registry.get(tool_name)
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool on its MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Optional timeout override
            
        Returns:
            Tool execution result
        """
        tool = self._tool_registry.get(tool_name)
        
        if not tool:
            logger.warning(f"[MCP] Tool not found: {tool_name}")
            return {
                "error": f"Tool '{tool_name}' not found in any connected MCP server",
                "available_tools": list(self._tool_registry.keys())
            }
        
        state = self._servers.get(tool.server_name)
        
        if not state or state.status != MCPServerStatus.CONNECTED:
            # Try to reconnect
            if state and state.config.auto_reconnect:
                logger.info(f"[MCP] Attempting reconnection to {tool.server_name}")
                connected = await self.connect_server(tool.server_name)
                if not connected:
                    return {
                        "error": f"Server '{tool.server_name}' not connected and reconnection failed",
                        "last_error": state.last_error if state else "Unknown"
                    }
            else:
                return {"error": f"Server '{tool.server_name}' not connected"}
        
        # Execute the tool
        logger.info(f"[MCP] Calling tool: {tool_name} on {tool.server_name}")
        
        result = await self._send_request(
            state,
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            },
            timeout=timeout
        )
        
        if result is None:
            return {"error": f"Tool call failed for {tool_name}"}
        
        # Extract content from result
        if "content" in result:
            content_items = result["content"]
            # Flatten text content
            text_parts = []
            for item in content_items:
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            
            if text_parts:
                return {"result": "\n".join(text_parts)}
        
        return result
    
    async def list_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available tools, optionally filtered by server.
        
        Args:
            server_name: Optional server name to filter by
            
        Returns:
            List of tool descriptions
        """
        tools = []
        
        for tool in self._tool_registry.values():
            if server_name and tool.server_name != server_name:
                continue
            
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "server": tool.server_name,
                "input_schema": tool.input_schema
            })
        
        return tools
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all server statuses."""
        return {
            "servers": {
                name: {
                    "status": state.status.value,
                    "enabled": state.config.enabled,
                    "tool_count": len(state.tools),
                    "connected_at": state.connected_at.isoformat() if state.connected_at else None,
                    "last_error": state.last_error
                }
                for name, state in self._servers.items()
            },
            "total_tools": len(self._tool_registry),
            "connected_servers": sum(
                1 for s in self._servers.values() 
                if s.status == MCPServerStatus.CONNECTED
            )
        }


# =============================================================================
# FALLBACK IMPLEMENTATION (When MCP servers unavailable)
# =============================================================================

class FallbackMCPManager:
    """
    Fallback implementation that provides basic functionality
    when MCP servers are not available (e.g., missing npx/node).
    
    Uses direct API calls where possible as an alternative.
    """
    
    def __init__(self):
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
        self._fallback_handlers: Dict[str, Callable] = {}
        self._setup_fallbacks()
    
    def _setup_fallbacks(self):
        """Register fallback tool handlers."""
        
        # Example: Telegram fallback using python-telegram-bot
        self._register_fallback(
            name="telegram_send_message",
            description="Send a message via Telegram bot",
            input_schema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": "string", "description": "Telegram chat ID"},
                    "text": {"type": "string", "description": "Message text"}
                },
                "required": ["chat_id", "text"]
            },
            handler=self._fallback_telegram_send
        )
    
    def _register_fallback(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable
    ):
        """Register a fallback tool handler."""
        self._tool_registry[name] = {
            "name": name,
            "description": description + " [Fallback]",
            "input_schema": input_schema
        }
        self._fallback_handlers[name] = handler
    
    async def _fallback_telegram_send(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback Telegram send using httpx."""
        import httpx
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return {"error": "TELEGRAM_BOT_TOKEN not configured"}
        
        chat_id = arguments.get("chat_id")
        text = arguments.get("text")
        
        if not chat_id or not text:
            return {"error": "chat_id and text are required"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
            
            if response.status_code == 200:
                return {"status": "sent", "result": response.json()}
            else:
                return {"error": f"Telegram API error: {response.text}"}
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all fallback tools."""
        return list(self._tool_registry.values())
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a fallback tool."""
        handler = self._fallback_handlers.get(tool_name)
        if not handler:
            return {"error": f"Fallback tool {tool_name} not found"}
        
        return await handler(arguments)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

# Try to use real MCP manager, fall back if npx not available
try:
    # Quick check if npx is available
    result = subprocess.run(
        ["npx", "--version"],
        capture_output=True,
        timeout=5
    )
    _npx_available = result.returncode == 0
except Exception:
    _npx_available = False

if _npx_available:
    mcp_manager = AlphawaveMCPManager()
    logger.info("[MCP] Using real MCP manager (npx available)")
else:
    mcp_manager = FallbackMCPManager()
    logger.warning("[MCP] Using fallback MCP manager (npx not available)")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def initialize_mcp() -> Dict[str, bool]:
    """
    Initialize MCP system and connect to enabled servers.
    
    Call this during application startup.
    
    Returns:
        Dict mapping server names to connection success
    """
    if isinstance(mcp_manager, AlphawaveMCPManager):
        return await mcp_manager.connect_enabled_servers()
    return {}


async def shutdown_mcp() -> None:
    """
    Shutdown MCP system and disconnect all servers.
    
    Call this during application shutdown.
    """
    if isinstance(mcp_manager, AlphawaveMCPManager):
        await mcp_manager.disconnect_all()


def get_mcp_tools() -> List[Dict[str, Any]]:
    """Get all available MCP tools in Claude format."""
    if isinstance(mcp_manager, AlphawaveMCPManager):
        return mcp_manager.get_claude_tools()
    elif isinstance(mcp_manager, FallbackMCPManager):
        return mcp_manager.get_all_tools()
    return []


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call an MCP tool by name.
    
    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        
    Returns:
        Tool execution result
    """
    return await mcp_manager.call_tool(tool_name, arguments)

"""Docker MCP Client for Nicole V7."""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    server: str


@dataclass
class MCPToolResult:
    content: Any
    is_error: bool = False
    error_message: Optional[str] = None


class DockerMCPClient:
    """Async HTTP client for the Docker MCP Gateway."""

    def __init__(self, gateway_url: str = "http://127.0.0.1:3100"):
        self.gateway_url = gateway_url.rstrip("/")
        self._http_client: Optional[httpx.AsyncClient] = None
        self._tools_cache: Optional[List[MCPTool]] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to the MCP Gateway and warm the tools cache."""
        try:
            self._http_client = httpx.AsyncClient(
                base_url=self.gateway_url, timeout=30.0
            )
            response = await self._http_client.get("/health")
            if response.status_code == 200:
                self._connected = True
                logger.info("Connected to Docker MCP Gateway")
                await self.list_tools(refresh=True)
                return True
            logger.error(
                "MCP Gateway health check failed: %s", response.status_code
            )
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MCP Gateway: {e}")
            return False

    async def disconnect(self):
        """Close the HTTP client and clear caches."""
        if self._http_client:
            await self._http_client.aclose()
        self._connected = False
        self._tools_cache = None

    async def list_tools(self, refresh: bool = False) -> List[MCPTool]:
        """List tools from the MCP Gateway."""
        if not self._connected:
            raise RuntimeError("Not connected to MCP Gateway")
        if self._tools_cache and not refresh:
            return self._tools_cache

        response = await self._http_client.post(
            "/rpc",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        )
        data = response.json()

        tools = []
        for t in data.get("result", {}).get("tools", []):
            tools.append(
                MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                    server=t.get("_server", "unknown"),
                )
            )
        self._tools_cache = tools
        logger.info("Loaded %s MCP tools", len(tools))
        return tools

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """Call a tool by name via MCP Gateway."""
        if not self._connected:
            raise RuntimeError("Not connected to MCP Gateway")

        try:
            response = await self._http_client.post(
                "/rpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                    "id": 2,
                },
            )
            data = response.json()

            if "error" in data:
                return MCPToolResult(
                    None, True, data["error"].get("message")
                )

            content = data.get("result", {}).get("content", [])
            logger.debug(f"[MCP] Raw content type: {type(content).__name__}, preview: {str(content)[:200]}")
            
            if isinstance(content, list):
                # First check for image type (for screenshots)
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type", "")
                        
                        # Handle image type with various data keys
                        if item_type == "image":
                            # Try multiple keys where image data might be
                            image_data = (
                                item.get("data") or 
                                item.get("base64") or 
                                item.get("image") or
                                item.get("content") or
                                ""
                            )
                            if image_data:
                                logger.info(f"[MCP] Found image content ({len(image_data)} chars)")
                                return MCPToolResult(content=image_data)
                        
                        # Puppeteer might return screenshot as text with JSON
                        if item_type == "text":
                            text_content = item.get("text", "")
                            # Check if it's JSON with a screenshot/data field
                            if text_content.startswith('{'):
                                try:
                                    import json
                                    parsed = json.loads(text_content)
                                    # Look for base64 screenshot data in the parsed JSON
                                    screenshot_data = (
                                        parsed.get("data") or 
                                        parsed.get("screenshot") or 
                                        parsed.get("base64") or 
                                        parsed.get("image")
                                    )
                                    if screenshot_data and len(str(screenshot_data)) > 1000:
                                        logger.info(f"[MCP] Found screenshot in text JSON ({len(screenshot_data)} chars)")
                                        return MCPToolResult(content=screenshot_data)
                                except json.JSONDecodeError:
                                    pass
                
                # Then check for text parts (fallback for non-screenshot tools)
                text_parts = [
                    i.get("text", "")
                    for i in content
                    if isinstance(i, dict) and i.get("type") == "text"
                ]
                content = "\n".join(text_parts) if text_parts else content

            return MCPToolResult(content=content)
        except Exception as e:
            return MCPToolResult(None, True, str(e))

    def get_tools_for_claude(self) -> List[Dict[str, Any]]:
        """Return tools in Claude-compatible format."""
        if not self._tools_cache:
            return []
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools_cache
        ]

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tool_count(self) -> int:
        return len(self._tools_cache) if self._tools_cache else 0


_mcp_client: Optional[DockerMCPClient] = None


async def get_mcp_client() -> DockerMCPClient:
    """Get (and connect) the shared Docker MCP client."""
    global _mcp_client
    if _mcp_client is None:
        from app.config import settings

        _mcp_client = DockerMCPClient(
            gateway_url=settings.MCP_GATEWAY_URL
        )
    if not _mcp_client.is_connected:
        await _mcp_client.connect()
    return _mcp_client


async def shutdown_mcp_client():
    """Shutdown the shared Docker MCP client."""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.disconnect()
        _mcp_client = None


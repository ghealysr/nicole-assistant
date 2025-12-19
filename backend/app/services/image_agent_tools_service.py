"""
Image Generation Agent Tools Service

Provides MCP tools and skill execution capabilities to image generation agents.
Allows agents to enhance their work with web search, browser automation, 
asset management, and data processing.

Author: AlphaWave Tech
Quality Standard: Anthropic Engineer Level
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from app.mcp.alphawave_mcp_manager import mcp_manager, AlphawaveMCPManager
from app.config import settings


logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from executing a tool or skill."""
    success: bool
    tool_name: str
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class ImageAgentToolsService:
    """
    Provides tool and skill execution for image generation agents.
    
    Available Tools:
    - web_search: Search for visual references, inspiration, examples
    - web_browse: Extract images and content from URLs
    - digitalocean_mcp: Manage assets, droplets, databases
    - context7: Get documentation and examples
    - firecrawl: Scrape web content
    
    Features:
    - Lazy MCP connection (connect on first use)
    - Tool result caching
    - Error handling and recovery
    - Execution metrics
    """
    
    def __init__(self):
        """Initialize the image agent tools service."""
        self._tool_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        logger.info("ImageAgentToolsService initialized")
    
    async def search_web_for_references(
        self,
        query: str,
        max_results: int = 5
    ) -> ToolResult:
        """
        Search the web for visual references and inspiration.
        
        Args:
            query: Search query (e.g., "cyberpunk city photography inspiration")
            max_results: Maximum number of results to return
            
        Returns:
            ToolResult with search results
        """
        try:
            import time
            start = time.time()
            
            # Check cache
            cache_key = f"web_search:{query}:{max_results}"
            if cache_key in self._tool_cache:
                cached_result, cached_time = self._tool_cache[cache_key]
                if (time.time() - cached_time) < self._cache_ttl:
                    logger.info(f"[IMAGE TOOLS] Using cached web search results for: {query}")
                    return cached_result
            
            # Use Brave Search MCP if available
            if isinstance(mcp_manager, AlphawaveMCPManager):
                try:
                    result = await mcp_manager.execute_tool(
                        server_name="brave-search",
                        tool_name="brave_web_search",
                        arguments={"query": query, "count": max_results}
                    )
                    
                    execution_time = int((time.time() - start) * 1000)
                    tool_result = ToolResult(
                        success=True,
                        tool_name="web_search",
                        result=result,
                        execution_time_ms=execution_time
                    )
                    
                    # Cache the result
                    self._tool_cache[cache_key] = (tool_result, time.time())
                    
                    logger.info(f"[IMAGE TOOLS] Web search completed in {execution_time}ms")
                    return tool_result
                    
                except Exception as e:
                    logger.warning(f"[IMAGE TOOLS] Brave Search failed: {e}")
            
            # Fallback: Return helpful message
            execution_time = int((time.time() - start) * 1000)
            return ToolResult(
                success=False,
                tool_name="web_search",
                result=None,
                error="Web search not available - Brave Search MCP not connected",
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.exception(f"[IMAGE TOOLS] Web search error: {e}")
            return ToolResult(
                success=False,
                tool_name="web_search",
                result=None,
                error=str(e),
                execution_time_ms=0
            )
    
    async def browse_url_for_images(
        self,
        url: str,
        extract_images: bool = True
    ) -> ToolResult:
        """
        Browse a URL to extract content and images.
        
        Args:
            url: The URL to browse
            extract_images: Whether to extract image URLs
            
        Returns:
            ToolResult with page content and images
        """
        try:
            import time
            start = time.time()
            
            # Use Firecrawl MCP if available
            if isinstance(mcp_manager, AlphawaveMCPManager):
                try:
                    result = await mcp_manager.execute_tool(
                        server_name="firecrawl",
                        tool_name="scrape_url",
                        arguments={"url": url, "formats": ["markdown", "html"]}
                    )
                    
                    # Extract images if requested
                    if extract_images and result:
                        # Parse HTML for image URLs
                        # This is a simplified version - could be enhanced
                        images = []
                        if "html" in result:
                            import re
                            img_pattern = r'<img[^>]+src="([^"]+)"'
                            matches = re.findall(img_pattern, result["html"])
                            images = matches
                        
                        result["images"] = images
                    
                    execution_time = int((time.time() - start) * 1000)
                    tool_result = ToolResult(
                        success=True,
                        tool_name="browse_url",
                        result=result,
                        execution_time_ms=execution_time
                    )
                    
                    logger.info(f"[IMAGE TOOLS] URL browsing completed in {execution_time}ms")
                    return tool_result
                    
                except Exception as e:
                    logger.warning(f"[IMAGE TOOLS] Firecrawl failed: {e}")
            
            # Fallback: Return error
            execution_time = int((time.time() - start) * 1000)
            return ToolResult(
                success=False,
                tool_name="browse_url",
                result=None,
                error="URL browsing not available - Firecrawl MCP not connected",
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.exception(f"[IMAGE TOOLS] URL browsing error: {e}")
            return ToolResult(
                success=False,
                tool_name="browse_url",
                result=None,
                error=str(e),
                execution_time_ms=0
            )
    
    async def get_documentation(
        self,
        query: str,
        context: Optional[str] = None
    ) -> ToolResult:
        """
        Get documentation and examples using Context7.
        
        Args:
            query: Documentation query
            context: Optional context to narrow search
            
        Returns:
            ToolResult with documentation
        """
        try:
            import time
            start = time.time()
            
            # Use Context7 MCP if available
            if isinstance(mcp_manager, AlphawaveMCPManager):
                try:
                    result = await mcp_manager.execute_tool(
                        server_name="context7",
                        tool_name="search_docs",
                        arguments={"query": query, "context": context}
                    )
                    
                    execution_time = int((time.time() - start) * 1000)
                    tool_result = ToolResult(
                        success=True,
                        tool_name="get_documentation",
                        result=result,
                        execution_time_ms=execution_time
                    )
                    
                    logger.info(f"[IMAGE TOOLS] Documentation search completed in {execution_time}ms")
                    return tool_result
                    
                except Exception as e:
                    logger.warning(f"[IMAGE TOOLS] Context7 failed: {e}")
            
            # Fallback
            execution_time = int((time.time() - start) * 1000)
            return ToolResult(
                success=False,
                tool_name="get_documentation",
                result=None,
                error="Documentation search not available - Context7 MCP not connected",
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.exception(f"[IMAGE TOOLS] Documentation search error: {e}")
            return ToolResult(
                success=False,
                tool_name="get_documentation",
                result=None,
                error=str(e),
                execution_time_ms=0
            )
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools for agents.
        
        Returns:
            List of tool descriptions in Claude format
        """
        tools = []
        
        # Web Search Tool
        tools.append({
            "name": "search_web_for_references",
            "description": (
                "Search the web for visual references, inspiration, and examples. "
                "Use this to find: photography examples, design inspiration, color palette ideas, "
                "composition references, style examples, or any visual content to inform your recommendations."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'cyberpunk city night photography', 'vintage poster design examples')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (1-10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        })
        
        # URL Browsing Tool
        tools.append({
            "name": "browse_url_for_images",
            "description": (
                "Browse a specific URL to extract content and images. "
                "Use this when you have a specific website, Pinterest board, or gallery "
                "you want to analyze for visual references."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to browse and extract content from"
                    },
                    "extract_images": {
                        "type": "boolean",
                        "description": "Whether to extract image URLs from the page",
                        "default": True
                    }
                },
                "required": ["url"]
            }
        })
        
        # Documentation Tool
        tools.append({
            "name": "get_documentation",
            "description": (
                "Get documentation and examples for image generation techniques, "
                "prompt engineering, or specific visual styles. Use this to learn about "
                "best practices, advanced techniques, or get examples of successful prompts."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Documentation query (e.g., 'prompt engineering for photorealistic images')"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context to narrow search (e.g., 'FLUX Pro', 'Midjourney')"
                    }
                },
                "required": ["query"]
            }
        })
        
        return tools
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool by name with arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            ToolResult with execution result
        """
        try:
            if tool_name == "search_web_for_references":
                return await self.search_web_for_references(
                    query=arguments["query"],
                    max_results=arguments.get("max_results", 5)
                )
            elif tool_name == "browse_url_for_images":
                return await self.browse_url_for_images(
                    url=arguments["url"],
                    extract_images=arguments.get("extract_images", True)
                )
            elif tool_name == "get_documentation":
                return await self.get_documentation(
                    query=arguments["query"],
                    context=arguments.get("context")
                )
            else:
                return ToolResult(
                    success=False,
                    tool_name=tool_name,
                    result=None,
                    error=f"Unknown tool: {tool_name}",
                    execution_time_ms=0
                )
                
        except Exception as e:
            logger.exception(f"[IMAGE TOOLS] Tool execution error: {e}")
            return ToolResult(
                success=False,
                tool_name=tool_name,
                result=None,
                error=str(e),
                execution_time_ms=0
            )


# Global service instance
_image_agent_tools_service: Optional[ImageAgentToolsService] = None


def get_image_agent_tools_service() -> ImageAgentToolsService:
    """Get or create the global image agent tools service instance."""
    global _image_agent_tools_service
    if _image_agent_tools_service is None:
        _image_agent_tools_service = ImageAgentToolsService()
    return _image_agent_tools_service


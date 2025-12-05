"""
Playwright MCP Integration for Nicole V7

Provides web automation and browser control through MCP.

Available Tools (when connected):
- playwright_navigate: Navigate to URL
- playwright_screenshot: Take screenshot
- playwright_click: Click element
- playwright_fill: Fill form field
- playwright_get_text: Get text content
- playwright_evaluate: Run JavaScript
"""

from typing import Any, Dict, List, Optional
import logging
import base64

from app.mcp.alphawave_mcp_manager import mcp_manager, AlphawaveMCPManager

logger = logging.getLogger(__name__)


class AlphawavePlaywrightMCP:
    """
    Browser automation MCP integration (via Puppeteer).
    
    Note: Uses the official @modelcontextprotocol/server-puppeteer server.
    
    Provides browser automation capabilities:
    - Navigate to pages
    - Take screenshots
    - Interact with elements
    - Extract content
    - Fill forms
    """
    
    SERVER_NAME = "puppeteer"  # Uses puppeteer MCP server
    
    def __init__(self):
        """Initialize Playwright MCP."""
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if Playwright MCP server is connected."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            status = mcp_manager.get_server_status(self.SERVER_NAME)
            from app.mcp.alphawave_mcp_manager import MCPServerStatus
            return status == MCPServerStatus.CONNECTED
        return False
    
    async def connect(self) -> bool:
        """
        Connect to Playwright MCP server.
        
        Returns:
            True if connection successful
        """
        if isinstance(mcp_manager, AlphawaveMCPManager):
            self._connected = await mcp_manager.connect_server(self.SERVER_NAME)
            return self._connected
        
        logger.warning("[Playwright MCP] MCP manager not available")
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from Playwright MCP server."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            await mcp_manager.disconnect_server(self.SERVER_NAME)
        self._connected = False
    
    # =========================================================================
    # NAVIGATION
    # =========================================================================
    
    async def navigate(
        self,
        url: str,
        wait_until: str = "load"
    ) -> Dict[str, Any]:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
                       ('load', 'domcontentloaded', 'networkidle')
            
        Returns:
            Navigation result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        logger.info(f"[Playwright] Navigating to: {url}")
        
        return await mcp_manager.call_tool(
            "playwright_navigate",
            {"url": url, "waitUntil": wait_until}
        )
    
    async def go_back(self) -> Dict[str, Any]:
        """Navigate back in browser history."""
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool("playwright_go_back", {})
    
    async def go_forward(self) -> Dict[str, Any]:
        """Navigate forward in browser history."""
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool("playwright_go_forward", {})
    
    async def reload(self) -> Dict[str, Any]:
        """Reload current page."""
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool("playwright_reload", {})
    
    # =========================================================================
    # SCREENSHOTS
    # =========================================================================
    
    async def screenshot(
        self,
        selector: Optional[str] = None,
        full_page: bool = False,
        format: str = "png"
    ) -> Dict[str, Any]:
        """
        Take a screenshot of the page or element.
        
        Args:
            selector: CSS selector for specific element
            full_page: Capture full scrollable page
            format: Image format ('png' or 'jpeg')
            
        Returns:
            Screenshot data (base64 encoded)
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        params = {"fullPage": full_page, "type": format}
        
        if selector:
            params["selector"] = selector
        
        result = await mcp_manager.call_tool("playwright_screenshot", params)
        
        # Result should contain base64 image data
        return result
    
    # =========================================================================
    # INTERACTION
    # =========================================================================
    
    async def click(
        self,
        selector: str,
        button: str = "left",
        double_click: bool = False
    ) -> Dict[str, Any]:
        """
        Click an element.
        
        Args:
            selector: CSS selector
            button: Mouse button ('left', 'right', 'middle')
            double_click: Perform double-click
            
        Returns:
            Click result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        params = {"selector": selector, "button": button}
        
        if double_click:
            params["clickCount"] = 2
        
        return await mcp_manager.call_tool("playwright_click", params)
    
    async def fill(
        self,
        selector: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Fill a form field with text.
        
        Args:
            selector: CSS selector for input/textarea
            text: Text to fill
            
        Returns:
            Fill result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_fill",
            {"selector": selector, "value": text}
        )
    
    async def select(
        self,
        selector: str,
        value: str
    ) -> Dict[str, Any]:
        """
        Select an option from a dropdown.
        
        Args:
            selector: CSS selector for select element
            value: Value to select
            
        Returns:
            Select result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_select",
            {"selector": selector, "value": value}
        )
    
    async def type_text(
        self,
        selector: str,
        text: str,
        delay: int = 50
    ) -> Dict[str, Any]:
        """
        Type text character by character (with delay).
        
        Args:
            selector: CSS selector
            text: Text to type
            delay: Delay between keystrokes (ms)
            
        Returns:
            Type result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_type",
            {"selector": selector, "text": text, "delay": delay}
        )
    
    async def press(
        self,
        selector: str,
        key: str
    ) -> Dict[str, Any]:
        """
        Press a keyboard key on an element.
        
        Args:
            selector: CSS selector
            key: Key to press (e.g., 'Enter', 'Tab', 'Escape')
            
        Returns:
            Press result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_press",
            {"selector": selector, "key": key}
        )
    
    # =========================================================================
    # CONTENT EXTRACTION
    # =========================================================================
    
    async def get_text(
        self,
        selector: str
    ) -> Dict[str, Any]:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector
            
        Returns:
            Element text content
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_get_text",
            {"selector": selector}
        )
    
    async def get_attribute(
        self,
        selector: str,
        attribute: str
    ) -> Dict[str, Any]:
        """
        Get an attribute value from an element.
        
        Args:
            selector: CSS selector
            attribute: Attribute name
            
        Returns:
            Attribute value
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_get_attribute",
            {"selector": selector, "name": attribute}
        )
    
    async def get_page_content(self) -> Dict[str, Any]:
        """
        Get the full HTML content of the page.
        
        Returns:
            Page HTML content
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool("playwright_content", {})
    
    async def get_page_title(self) -> Dict[str, Any]:
        """Get the page title."""
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool("playwright_title", {})
    
    async def get_page_url(self) -> Dict[str, Any]:
        """Get the current page URL."""
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool("playwright_url", {})
    
    # =========================================================================
    # JAVASCRIPT EXECUTION
    # =========================================================================
    
    async def evaluate(
        self,
        script: str,
        args: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute JavaScript in the page context.
        
        Args:
            script: JavaScript code to execute
            args: Optional arguments to pass to the script
            
        Returns:
            Script result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        params = {"expression": script}
        if args:
            params["args"] = args
        
        return await mcp_manager.call_tool("playwright_evaluate", params)
    
    # =========================================================================
    # WAITING
    # =========================================================================
    
    async def wait_for_selector(
        self,
        selector: str,
        state: str = "visible",
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        Wait for an element to reach a state.
        
        Args:
            selector: CSS selector
            state: State to wait for ('attached', 'detached', 'visible', 'hidden')
            timeout: Timeout in milliseconds
            
        Returns:
            Wait result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_wait_for_selector",
            {"selector": selector, "state": state, "timeout": timeout}
        )
    
    async def wait_for_navigation(
        self,
        wait_until: str = "load",
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        Wait for navigation to complete.
        
        Args:
            wait_until: Navigation event to wait for
            timeout: Timeout in milliseconds
            
        Returns:
            Wait result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        return await mcp_manager.call_tool(
            "playwright_wait_for_navigation",
            {"waitUntil": wait_until, "timeout": timeout}
        )
    
    # =========================================================================
    # HIGH-LEVEL HELPERS
    # =========================================================================
    
    async def scrape_page(
        self,
        url: str,
        selectors: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Scrape data from a page using CSS selectors.
        
        Args:
            url: URL to scrape
            selectors: Dict mapping field names to CSS selectors
            
        Returns:
            Scraped data
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        # Navigate to page
        nav_result = await self.navigate(url)
        if "error" in nav_result:
            return nav_result
        
        # Extract data for each selector
        data = {}
        for field, selector in selectors.items():
            result = await self.get_text(selector)
            data[field] = result.get("result", result.get("text", ""))
        
        return {"url": url, "data": data}
    
    async def fill_form(
        self,
        fields: Dict[str, str],
        submit_selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fill a form with multiple fields.
        
        Args:
            fields: Dict mapping selectors to values
            submit_selector: Optional submit button selector
            
        Returns:
            Form fill result
        """
        if not self.is_connected:
            return {"error": "Playwright MCP not connected"}
        
        results = {}
        
        for selector, value in fields.items():
            result = await self.fill(selector, value)
            results[selector] = result
        
        if submit_selector:
            results["submit"] = await self.click(submit_selector)
        
        return {"fields_filled": len(fields), "results": results}


# Global instance
playwright_mcp = AlphawavePlaywrightMCP()


"""
Google Workspace MCP integration for Gmail, Calendar, and Drive.
"""

from typing import List, Dict, Any, Optional
import logging

from app.mcp.alphawave_mcp_manager import mcp_manager

logger = logging.getLogger(__name__)


class AlphawaveGoogleMCP:
    """
    Google Workspace MCP integration.
    
    Provides access to:
    - Gmail (search, read, send emails)
    - Google Calendar (list, create events)
    - Google Drive (search, read files)
    """
    
    def __init__(self):
        """Initialize Google Workspace MCP."""
        self.server_name = "google"
        self.connected = False
    
    async def connect(self, credentials_path: str) -> bool:
        """
        Connect to Google Workspace MCP server.
        
        Args:
            credentials_path: Path to Google credentials JSON
            
        Returns:
            True if connection successful
        """
        
        success = await mcp_manager.connect_server(
            name=self.server_name,
            command="mcp-server-google",
            args=["--credentials", credentials_path]
        )
        
        self.connected = success
        return success
    
    async def search_gmail(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Gmail using MCP tool.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            List of email results
        """
        
        if not self.connected:
            raise ValueError("Google MCP not connected")
        
        result = await mcp_manager.call_tool(
            server_name=self.server_name,
            tool_name="search_gmail",
            arguments={"query": query, "max_results": max_results}
        )
        
        return result
    
    async def list_calendar_events(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        List calendar events in date range.
        
        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            List of calendar events
        """
        
        if not self.connected:
            raise ValueError("Google MCP not connected")
        
        result = await mcp_manager.call_tool(
            server_name=self.server_name,
            tool_name="list_calendar_events",
            arguments={"start_date": start_date, "end_date": end_date}
        )
        
        return result
    
    async def search_drive(
        self,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Search Google Drive files.
        
        Args:
            query: Drive search query
            
        Returns:
            List of Drive file results
        """
        
        if not self.connected:
            raise ValueError("Google MCP not connected")
        
        result = await mcp_manager.call_tool(
            server_name=self.server_name,
            tool_name="search_drive",
            arguments={"query": query}
        )
        
        return result


# Global Google MCP instance
google_mcp = AlphawaveGoogleMCP()


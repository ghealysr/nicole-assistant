"""
Google Workspace MCP Integration for Nicole V7

Provides access to Gmail, Calendar, and Drive through MCP.

Available Tools (when connected):
- gmail_search: Search emails
- gmail_read: Read email content
- gmail_send: Send emails
- calendar_list: List events
- calendar_create: Create events
- drive_search: Search files
- drive_read: Read file content
"""

from typing import Any, Dict, List, Optional
import logging
from datetime import datetime, timedelta

from app.mcp.alphawave_mcp_manager import mcp_manager, AlphawaveMCPManager

logger = logging.getLogger(__name__)


class AlphawaveGoogleMCP:
    """
    Google Workspace MCP integration.
    
    Provides high-level methods for Gmail, Calendar, and Drive operations.
    Uses the central MCP manager for actual tool execution.
    """
    
    SERVER_NAME = "google"
    
    def __init__(self):
        """Initialize Google Workspace MCP."""
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if Google MCP server is connected."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            status = mcp_manager.get_server_status(self.SERVER_NAME)
            from app.mcp.alphawave_mcp_manager import MCPServerStatus
            return status == MCPServerStatus.CONNECTED
        return False
    
    async def connect(self) -> bool:
        """
        Connect to Google Workspace MCP server.
        
        Returns:
            True if connection successful
        """
        if isinstance(mcp_manager, AlphawaveMCPManager):
            self._connected = await mcp_manager.connect_server(self.SERVER_NAME)
            return self._connected
        
        logger.warning("[Google MCP] MCP manager not available")
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from Google Workspace MCP server."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            await mcp_manager.disconnect_server(self.SERVER_NAME)
        self._connected = False
    
    # =========================================================================
    # GMAIL OPERATIONS
    # =========================================================================
    
    async def search_gmail(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search Gmail messages.
        
        Args:
            query: Gmail search query (e.g., "from:user@example.com")
            max_results: Maximum number of results
            
        Returns:
            Search results with email metadata
        """
        if not self.is_connected:
            return {"error": "Google MCP not connected", "suggestion": "Call connect() first"}
        
        return await mcp_manager.call_tool(
            "gmail_search",
            {"query": query, "maxResults": max_results}
        )
    
    async def read_email(self, email_id: str) -> Dict[str, Any]:
        """
        Read a specific email's content.
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            Email content including body, attachments info
        """
        if not self.is_connected:
            return {"error": "Google MCP not connected"}
        
        return await mcp_manager.call_tool(
            "gmail_read",
            {"messageId": email_id}
        )
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            
        Returns:
            Send result with message ID
        """
        if not self.is_connected:
            return {"error": "Google MCP not connected"}
        
        params = {
            "to": to,
            "subject": subject,
            "body": body
        }
        
        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
        
        logger.info(f"[Google MCP] Sending email to {to}: {subject}")
        
        return await mcp_manager.call_tool("gmail_send", params)
    
    # =========================================================================
    # CALENDAR OPERATIONS
    # =========================================================================
    
    async def list_calendar_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        calendar_id: str = "primary",
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        List calendar events in a date range.
        
        Args:
            start_date: Start date (ISO format, defaults to today)
            end_date: End date (ISO format, defaults to 7 days from now)
            calendar_id: Calendar ID (default: primary)
            max_results: Maximum events to return
            
        Returns:
            List of calendar events
        """
        if not self.is_connected:
            return {"error": "Google MCP not connected"}
        
        # Default to next 7 days
        if not start_date:
            start_date = datetime.utcnow().isoformat() + "Z"
        if not end_date:
            end_date = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        
        return await mcp_manager.call_tool(
            "calendar_list",
            {
                "calendarId": calendar_id,
                "timeMin": start_date,
                "timeMax": end_date,
                "maxResults": max_results
            }
        )
    
    async def create_calendar_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Args:
            summary: Event title
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            calendar_id: Calendar ID (default: primary)
            
        Returns:
            Created event details
        """
        if not self.is_connected:
            return {"error": "Google MCP not connected"}
        
        params = {
            "calendarId": calendar_id,
            "summary": summary,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time}
        }
        
        if description:
            params["description"] = description
        if location:
            params["location"] = location
        if attendees:
            params["attendees"] = [{"email": e} for e in attendees]
        
        logger.info(f"[Google MCP] Creating event: {summary}")
        
        return await mcp_manager.call_tool("calendar_create", params)
    
    async def get_todays_events(self) -> Dict[str, Any]:
        """Get all events for today."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        return await self.list_calendar_events(
            start_date=today.isoformat() + "Z",
            end_date=tomorrow.isoformat() + "Z"
        )
    
    async def get_this_weeks_events(self) -> Dict[str, Any]:
        """Get all events for this week."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today + timedelta(days=7)
        
        return await self.list_calendar_events(
            start_date=today.isoformat() + "Z",
            end_date=week_end.isoformat() + "Z",
            max_results=50
        )
    
    # =========================================================================
    # DRIVE OPERATIONS
    # =========================================================================
    
    async def search_drive(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search Google Drive files.
        
        Args:
            query: Drive search query
            max_results: Maximum results
            
        Returns:
            List of matching files
        """
        if not self.is_connected:
            return {"error": "Google MCP not connected"}
        
        return await mcp_manager.call_tool(
            "drive_search",
            {"query": query, "maxResults": max_results}
        )
    
    async def read_drive_file(self, file_id: str) -> Dict[str, Any]:
        """
        Read content of a Google Drive file.
        
        Args:
            file_id: Drive file ID
            
        Returns:
            File content (text for docs, metadata for other types)
        """
        if not self.is_connected:
            return {"error": "Google MCP not connected"}
        
        return await mcp_manager.call_tool(
            "drive_read",
            {"fileId": file_id}
        )
    
    async def list_recent_files(self, max_results: int = 10) -> Dict[str, Any]:
        """List recently modified files in Drive."""
        return await self.search_drive(
            query="modifiedTime > '2024-01-01'",
            max_results=max_results
        )


# Global instance
google_mcp = AlphawaveGoogleMCP()

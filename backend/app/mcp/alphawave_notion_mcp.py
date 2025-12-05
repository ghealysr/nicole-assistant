"""
Notion MCP Integration for Nicole V7

Provides access to Notion databases and pages through MCP.

Available Tools (when connected):
- notion_search: Search across workspace
- notion_create_page: Create a new page
- notion_update_page: Update page properties
- notion_query_database: Query a database
- notion_create_database_item: Add item to database
"""

from typing import Any, Dict, List, Optional
import logging

from app.mcp.alphawave_mcp_manager import mcp_manager, AlphawaveMCPManager

logger = logging.getLogger(__name__)


class AlphawaveNotionMCP:
    """
    Notion MCP integration.
    
    Provides high-level methods for Notion workspace operations.
    Supports project management, task tracking, and knowledge bases.
    """
    
    SERVER_NAME = "notion"
    
    def __init__(self):
        """Initialize Notion MCP."""
        self._connected = False
        self._workspace_id = None
    
    @property
    def is_connected(self) -> bool:
        """Check if Notion MCP server is connected."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            status = mcp_manager.get_server_status(self.SERVER_NAME)
            from app.mcp.alphawave_mcp_manager import MCPServerStatus
            return status == MCPServerStatus.CONNECTED
        return False
    
    async def connect(self, workspace_id: Optional[str] = None) -> bool:
        """
        Connect to Notion MCP server.
        
        Args:
            workspace_id: Optional workspace ID override
            
        Returns:
            True if connection successful
        """
        if isinstance(mcp_manager, AlphawaveMCPManager):
            self._connected = await mcp_manager.connect_server(self.SERVER_NAME)
            self._workspace_id = workspace_id
            return self._connected
        
        logger.warning("[Notion MCP] MCP manager not available")
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from Notion MCP server."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            await mcp_manager.disconnect_server(self.SERVER_NAME)
        self._connected = False
    
    # =========================================================================
    # SEARCH & QUERY
    # =========================================================================
    
    async def search(
        self,
        query: str,
        filter_type: Optional[str] = None,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Search across Notion workspace.
        
        Args:
            query: Search query text
            filter_type: Filter by 'page' or 'database'
            page_size: Number of results
            
        Returns:
            Search results
        """
        if not self.is_connected:
            return {"error": "Notion MCP not connected", "suggestion": "Call connect() first"}
        
        params = {"query": query, "page_size": page_size}
        
        if filter_type:
            params["filter"] = {"value": filter_type, "property": "object"}
        
        return await mcp_manager.call_tool("notion_search", params)
    
    async def query_database(
        self,
        database_id: str,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Query a Notion database.
        
        Args:
            database_id: Database ID to query
            filter_conditions: Filter conditions (Notion filter format)
            sorts: Sort conditions
            page_size: Number of results
            
        Returns:
            Database query results
        """
        if not self.is_connected:
            return {"error": "Notion MCP not connected"}
        
        params = {
            "database_id": database_id,
            "page_size": page_size
        }
        
        if filter_conditions:
            params["filter"] = filter_conditions
        if sorts:
            params["sorts"] = sorts
        
        return await mcp_manager.call_tool("notion_query_database", params)
    
    # =========================================================================
    # PAGE OPERATIONS
    # =========================================================================
    
    async def create_page(
        self,
        parent_id: str,
        title: str,
        content: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        parent_type: str = "page"
    ) -> Dict[str, Any]:
        """
        Create a new page in Notion.
        
        Args:
            parent_id: Parent page or database ID
            title: Page title
            content: Optional markdown content
            properties: Optional properties (for database pages)
            parent_type: 'page' or 'database'
            
        Returns:
            Created page details
        """
        if not self.is_connected:
            return {"error": "Notion MCP not connected"}
        
        params = {
            "parent": {
                parent_type + "_id": parent_id
            },
            "properties": properties or {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        }
        
        if content:
            # Convert markdown to Notion blocks
            params["children"] = self._markdown_to_blocks(content)
        
        logger.info(f"[Notion MCP] Creating page: {title}")
        
        return await mcp_manager.call_tool("notion_create_page", params)
    
    async def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a page's properties.
        
        Args:
            page_id: Page ID to update
            properties: Properties to update
            
        Returns:
            Updated page details
        """
        if not self.is_connected:
            return {"error": "Notion MCP not connected"}
        
        return await mcp_manager.call_tool(
            "notion_update_page",
            {"page_id": page_id, "properties": properties}
        )
    
    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Get a page's content and properties.
        
        Args:
            page_id: Page ID
            
        Returns:
            Page content and metadata
        """
        if not self.is_connected:
            return {"error": "Notion MCP not connected"}
        
        return await mcp_manager.call_tool(
            "notion_get_page",
            {"page_id": page_id}
        )
    
    # =========================================================================
    # DATABASE ITEM OPERATIONS
    # =========================================================================
    
    async def create_database_item(
        self,
        database_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new item in a Notion database.
        
        Args:
            database_id: Database to add item to
            properties: Item properties matching database schema
            
        Returns:
            Created item details
        """
        if not self.is_connected:
            return {"error": "Notion MCP not connected"}
        
        return await mcp_manager.call_tool(
            "notion_create_database_item",
            {"database_id": database_id, "properties": properties}
        )
    
    # =========================================================================
    # PROJECT MANAGEMENT HELPERS
    # =========================================================================
    
    async def create_project(
        self,
        name: str,
        description: str,
        parent_page_id: str,
        project_type: str = "web_design"
    ) -> Dict[str, Any]:
        """
        Create a new project with standard structure.
        
        Creates a project page with sub-pages for:
        - Tasks
        - Notes
        - Files
        - Timeline
        
        Args:
            name: Project name
            description: Project description
            parent_page_id: Parent page for the project
            project_type: Type of project
            
        Returns:
            Created project structure
        """
        if not self.is_connected:
            return {"error": "Notion MCP not connected"}
        
        # Create main project page
        project = await self.create_page(
            parent_id=parent_page_id,
            title=name,
            content=f"# {name}\n\n{description}\n\n**Type:** {project_type}"
        )
        
        if "error" in project:
            return project
        
        project_id = project.get("id")
        
        # Create sub-pages
        sub_pages = []
        for section in ["Tasks", "Notes", "Files", "Timeline"]:
            sub_page = await self.create_page(
                parent_id=project_id,
                title=section,
                content=f"# {section}\n\n_{name} - {section}_"
            )
            sub_pages.append({"section": section, "result": sub_page})
        
        return {
            "project": project,
            "sub_pages": sub_pages
        }
    
    async def add_task(
        self,
        database_id: str,
        title: str,
        status: str = "Not Started",
        priority: str = "Medium",
        due_date: Optional[str] = None,
        assignee: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a task to a tasks database.
        
        Args:
            database_id: Tasks database ID
            title: Task title
            status: Task status
            priority: Task priority
            due_date: Due date (ISO format)
            assignee: Assignee name
            
        Returns:
            Created task
        """
        properties = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": status}},
            "Priority": {"select": {"name": priority}}
        }
        
        if due_date:
            properties["Due"] = {"date": {"start": due_date}}
        
        if assignee:
            properties["Assignee"] = {"rich_text": [{"text": {"content": assignee}}]}
        
        return await self.create_database_item(database_id, properties)
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Convert simple markdown to Notion blocks.
        
        Handles:
        - Paragraphs
        - Headers (# ## ###)
        - Bullet lists (- item)
        - Code blocks
        """
        blocks = []
        lines = markdown.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Headers
            if line.startswith('### '):
                blocks.append({
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('# '):
                blocks.append({
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            # Bullet lists
            elif line.startswith('- '):
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            # Code blocks
            elif line.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": '\n'.join(code_lines)}}],
                        "language": "plain text"
                    }
                })
            # Regular paragraph
            elif line.strip():
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })
            
            i += 1
        
        return blocks


# Global instance
notion_mcp = AlphawaveNotionMCP()


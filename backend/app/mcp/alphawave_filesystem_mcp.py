"""
Filesystem MCP Integration for Nicole V7

Provides safe file system access through MCP.

Available Tools (when connected):
- read_file: Read file contents
- write_file: Write to a file
- list_directory: List directory contents
- create_directory: Create a directory
- search_files: Search for files by pattern
"""

from typing import Any, Dict, List, Optional
import logging
import os

from app.mcp.alphawave_mcp_manager import mcp_manager, AlphawaveMCPManager

logger = logging.getLogger(__name__)


class AlphawaveFilesystemMCP:
    """
    Filesystem MCP integration.
    
    Provides safe, sandboxed file system access.
    Default root is /tmp/nicole for security.
    """
    
    SERVER_NAME = "filesystem"
    
    def __init__(self, root_path: str = "/tmp/nicole"):
        """
        Initialize Filesystem MCP.
        
        Args:
            root_path: Root directory for file operations
        """
        self._connected = False
        self._root_path = root_path
        
        # Ensure root directory exists
        os.makedirs(root_path, exist_ok=True)
    
    @property
    def is_connected(self) -> bool:
        """Check if Filesystem MCP server is connected."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            status = mcp_manager.get_server_status(self.SERVER_NAME)
            from app.mcp.alphawave_mcp_manager import MCPServerStatus
            return status == MCPServerStatus.CONNECTED
        return False
    
    @property
    def root_path(self) -> str:
        """Get the root path for file operations."""
        return self._root_path
    
    async def connect(self) -> bool:
        """
        Connect to Filesystem MCP server.
        
        Returns:
            True if connection successful
        """
        if isinstance(mcp_manager, AlphawaveMCPManager):
            self._connected = await mcp_manager.connect_server(self.SERVER_NAME)
            return self._connected
        
        # Fallback: just ensure directory exists
        os.makedirs(self._root_path, exist_ok=True)
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from Filesystem MCP server."""
        if isinstance(mcp_manager, AlphawaveMCPManager):
            await mcp_manager.disconnect_server(self.SERVER_NAME)
        self._connected = False
    
    def _resolve_path(self, path: str) -> str:
        """
        Resolve a path relative to root, preventing directory traversal.
        
        Args:
            path: Relative or absolute path
            
        Returns:
            Safe absolute path within root
        """
        # Normalize and make relative to root
        clean_path = os.path.normpath(path)
        
        # Remove leading slashes
        if clean_path.startswith('/'):
            clean_path = clean_path[1:]
        
        # Remove any .. components
        parts = clean_path.split(os.sep)
        safe_parts = [p for p in parts if p and p != '..']
        
        return os.path.join(self._root_path, *safe_parts)
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    async def read_file(self, path: str) -> Dict[str, Any]:
        """
        Read a file's contents.
        
        Args:
            path: File path (relative to root)
            
        Returns:
            File contents or error
        """
        if self.is_connected and isinstance(mcp_manager, AlphawaveMCPManager):
            return await mcp_manager.call_tool(
                "read_file",
                {"path": self._resolve_path(path)}
            )
        
        # Fallback: direct file read
        try:
            safe_path = self._resolve_path(path)
            with open(safe_path, 'r') as f:
                content = f.read()
            return {"content": content, "path": safe_path}
        except FileNotFoundError:
            return {"error": f"File not found: {path}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def write_file(
        self,
        path: str,
        content: str,
        create_dirs: bool = True
    ) -> Dict[str, Any]:
        """
        Write content to a file.
        
        Args:
            path: File path (relative to root)
            content: Content to write
            create_dirs: Create parent directories if needed
            
        Returns:
            Success status or error
        """
        if self.is_connected and isinstance(mcp_manager, AlphawaveMCPManager):
            return await mcp_manager.call_tool(
                "write_file",
                {"path": self._resolve_path(path), "content": content}
            )
        
        # Fallback: direct file write
        try:
            safe_path = self._resolve_path(path)
            
            if create_dirs:
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            
            with open(safe_path, 'w') as f:
                f.write(content)
            
            logger.info(f"[Filesystem] Wrote file: {safe_path}")
            return {"status": "success", "path": safe_path}
        except Exception as e:
            return {"error": str(e)}
    
    async def append_file(
        self,
        path: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Append content to a file.
        
        Args:
            path: File path
            content: Content to append
            
        Returns:
            Success status
        """
        try:
            safe_path = self._resolve_path(path)
            
            with open(safe_path, 'a') as f:
                f.write(content)
            
            return {"status": "success", "path": safe_path}
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        Args:
            path: File path
            
        Returns:
            Success status
        """
        try:
            safe_path = self._resolve_path(path)
            os.remove(safe_path)
            return {"status": "deleted", "path": safe_path}
        except FileNotFoundError:
            return {"error": f"File not found: {path}"}
        except Exception as e:
            return {"error": str(e)}
    
    # =========================================================================
    # DIRECTORY OPERATIONS
    # =========================================================================
    
    async def list_directory(
        self,
        path: str = ".",
        include_hidden: bool = False
    ) -> Dict[str, Any]:
        """
        List contents of a directory.
        
        Args:
            path: Directory path (relative to root)
            include_hidden: Include hidden files (starting with .)
            
        Returns:
            Directory listing
        """
        if self.is_connected and isinstance(mcp_manager, AlphawaveMCPManager):
            return await mcp_manager.call_tool(
                "list_directory",
                {"path": self._resolve_path(path)}
            )
        
        # Fallback: direct listing
        try:
            safe_path = self._resolve_path(path)
            entries = []
            
            for entry in os.listdir(safe_path):
                if not include_hidden and entry.startswith('.'):
                    continue
                
                entry_path = os.path.join(safe_path, entry)
                is_dir = os.path.isdir(entry_path)
                
                entries.append({
                    "name": entry,
                    "type": "directory" if is_dir else "file",
                    "size": os.path.getsize(entry_path) if not is_dir else None
                })
            
            return {"entries": entries, "path": safe_path}
        except FileNotFoundError:
            return {"error": f"Directory not found: {path}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def create_directory(self, path: str) -> Dict[str, Any]:
        """
        Create a directory.
        
        Args:
            path: Directory path to create
            
        Returns:
            Success status
        """
        if self.is_connected and isinstance(mcp_manager, AlphawaveMCPManager):
            return await mcp_manager.call_tool(
                "create_directory",
                {"path": self._resolve_path(path)}
            )
        
        try:
            safe_path = self._resolve_path(path)
            os.makedirs(safe_path, exist_ok=True)
            return {"status": "created", "path": safe_path}
        except Exception as e:
            return {"error": str(e)}
    
    async def search_files(
        self,
        pattern: str,
        path: str = "."
    ) -> Dict[str, Any]:
        """
        Search for files matching a pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.txt")
            path: Directory to search in
            
        Returns:
            Matching files
        """
        if self.is_connected and isinstance(mcp_manager, AlphawaveMCPManager):
            return await mcp_manager.call_tool(
                "search_files",
                {"pattern": pattern, "path": self._resolve_path(path)}
            )
        
        import glob
        
        try:
            safe_path = self._resolve_path(path)
            search_pattern = os.path.join(safe_path, "**", pattern)
            matches = glob.glob(search_pattern, recursive=True)
            
            # Make paths relative to root
            relative_matches = [
                os.path.relpath(m, self._root_path) for m in matches
            ]
            
            return {"matches": relative_matches, "count": len(matches)}
        except Exception as e:
            return {"error": str(e)}
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    async def save_artifact(
        self,
        name: str,
        content: str,
        artifact_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Save an artifact (code, document, etc.).
        
        Args:
            name: Artifact name
            content: Artifact content
            artifact_type: Type (text, code, json, markdown)
            
        Returns:
            Saved artifact path
        """
        # Determine extension
        ext_map = {
            "text": ".txt",
            "code": ".py",
            "json": ".json",
            "markdown": ".md",
            "html": ".html",
            "css": ".css",
            "js": ".js"
        }
        ext = ext_map.get(artifact_type, ".txt")
        
        # Clean filename
        safe_name = "".join(c for c in name if c.isalnum() or c in "._-")
        filename = f"artifacts/{safe_name}{ext}"
        
        return await self.write_file(filename, content)
    
    async def get_artifact(self, name: str) -> Dict[str, Any]:
        """
        Retrieve a saved artifact.
        
        Args:
            name: Artifact name
            
        Returns:
            Artifact content
        """
        # Try common extensions
        for ext in [".txt", ".py", ".json", ".md", ".html"]:
            result = await self.read_file(f"artifacts/{name}{ext}")
            if "error" not in result:
                return result
        
        return {"error": f"Artifact not found: {name}"}


# Global instance
filesystem_mcp = AlphawaveFilesystemMCP()


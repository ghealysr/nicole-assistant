"""
Faz Code GitHub Service

Handles GitHub repository creation, file commits, and management for Faz Code projects.
Uses GitHub's REST API for programmatic repository management.
"""

import logging
import base64
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx

from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)


class GitHubService:
    """
    Service for GitHub repository operations.
    
    Capabilities:
    - Create new repositories
    - Commit multiple files
    - Create branches
    - Get repository info
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None, org: Optional[str] = None):
        """
        Initialize GitHub service.
        
        Args:
            token: GitHub personal access token (or use from settings)
            org: GitHub organization (or use from settings)
        """
        self.token = token or settings.GITHUB_TOKEN
        self.org = org or settings.GITHUB_ORG
        
        if not self.token:
            logger.warning("[GitHub] No GitHub token configured")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    async def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new GitHub repository.
        
        Args:
            name: Repository name (will be slugified)
            description: Repository description
            private: Whether the repo should be private
            auto_init: Initialize with README
            
        Returns:
            Repository info dict with keys: name, full_name, html_url, clone_url, etc.
        """
        if not self.token:
            return {"error": "GitHub token not configured"}
        
        # Slugify name
        repo_name = name.lower().replace(" ", "-").replace("_", "-")
        
        # Create in org or user account
        if self.org:
            url = f"{self.BASE_URL}/orgs/{self.org}/repos"
        else:
            url = f"{self.BASE_URL}/user/repos"
        
        payload = {
            "name": repo_name,
            "description": description[:350] if description else "",
            "private": private,
            "auto_init": auto_init,
            "has_issues": True,
            "has_projects": False,
            "has_wiki": False,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )
                
                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"[GitHub] Created repo: {data.get('full_name')}")
                    return {
                        "success": True,
                        "name": data.get("name"),
                        "full_name": data.get("full_name"),
                        "html_url": data.get("html_url"),
                        "clone_url": data.get("clone_url"),
                        "ssh_url": data.get("ssh_url"),
                        "default_branch": data.get("default_branch", "main"),
                    }
                elif response.status_code == 422:
                    # Repository already exists
                    error_data = response.json()
                    if "name already exists" in str(error_data):
                        # Try to get existing repo
                        return await self.get_repository(repo_name)
                    return {"error": f"Validation failed: {error_data}"}
                else:
                    logger.error(f"[GitHub] Create repo failed: {response.status_code} {response.text}")
                    return {"error": f"GitHub API error: {response.status_code}"}
                    
        except Exception as e:
            logger.exception(f"[GitHub] Create repo error: {e}")
            return {"error": str(e)}
    
    async def get_repository(self, repo_name: str) -> Dict[str, Any]:
        """Get repository info."""
        if not self.token:
            return {"error": "GitHub token not configured"}
        
        owner = self.org or await self._get_username()
        url = f"{self.BASE_URL}/repos/{owner}/{repo_name}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "name": data.get("name"),
                        "full_name": data.get("full_name"),
                        "html_url": data.get("html_url"),
                        "clone_url": data.get("clone_url"),
                        "ssh_url": data.get("ssh_url"),
                        "default_branch": data.get("default_branch", "main"),
                    }
                else:
                    return {"error": f"Repository not found: {response.status_code}"}
                    
        except Exception as e:
            logger.exception(f"[GitHub] Get repo error: {e}")
            return {"error": str(e)}
    
    async def commit_files(
        self,
        repo_name: str,
        files: Dict[str, str],
        message: str = "Initial commit from Faz Code",
        branch: str = "main",
    ) -> Dict[str, Any]:
        """
        Commit multiple files to a repository.
        
        Uses the Git Data API to create a tree and commit for atomic multi-file commits.
        
        Args:
            repo_name: Repository name
            files: Dict of path -> content
            message: Commit message
            branch: Target branch
            
        Returns:
            Commit info with sha, url, etc.
        """
        if not self.token:
            return {"error": "GitHub token not configured"}
        
        owner = self.org or await self._get_username()
        
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Get the reference for the branch
                ref_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/refs/heads/{branch}"
                ref_response = await client.get(ref_url, headers=self.headers, timeout=15.0)
                
                if ref_response.status_code == 404:
                    # Branch doesn't exist, create initial commit
                    return await self._initial_commit(client, owner, repo_name, files, message, branch)
                elif ref_response.status_code != 200:
                    return {"error": f"Failed to get branch ref: {ref_response.status_code}"}
                
                ref_data = ref_response.json()
                latest_commit_sha = ref_data["object"]["sha"]
                
                # Step 2: Get the current tree
                tree_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/commits/{latest_commit_sha}"
                tree_response = await client.get(tree_url, headers=self.headers, timeout=15.0)
                
                if tree_response.status_code != 200:
                    return {"error": f"Failed to get commit: {tree_response.status_code}"}
                
                base_tree_sha = tree_response.json()["tree"]["sha"]
                
                # Step 3: Create blobs for each file
                tree_items = []
                for path, content in files.items():
                    blob_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/blobs"
                    blob_payload = {
                        "content": content,
                        "encoding": "utf-8",
                    }
                    
                    blob_response = await client.post(
                        blob_url,
                        headers=self.headers,
                        json=blob_payload,
                        timeout=30.0,
                    )
                    
                    if blob_response.status_code != 201:
                        logger.error(f"[GitHub] Failed to create blob for {path}")
                        continue
                    
                    blob_sha = blob_response.json()["sha"]
                    tree_items.append({
                        "path": path,
                        "mode": "100644",  # Regular file
                        "type": "blob",
                        "sha": blob_sha,
                    })
                
                if not tree_items:
                    return {"error": "No files were committed"}
                
                # Step 4: Create new tree
                new_tree_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/trees"
                new_tree_payload = {
                    "base_tree": base_tree_sha,
                    "tree": tree_items,
                }
                
                new_tree_response = await client.post(
                    new_tree_url,
                    headers=self.headers,
                    json=new_tree_payload,
                    timeout=30.0,
                )
                
                if new_tree_response.status_code != 201:
                    return {"error": f"Failed to create tree: {new_tree_response.status_code}"}
                
                new_tree_sha = new_tree_response.json()["sha"]
                
                # Step 5: Create commit
                commit_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/commits"
                commit_payload = {
                    "message": message,
                    "tree": new_tree_sha,
                    "parents": [latest_commit_sha],
                }
                
                commit_response = await client.post(
                    commit_url,
                    headers=self.headers,
                    json=commit_payload,
                    timeout=30.0,
                )
                
                if commit_response.status_code != 201:
                    return {"error": f"Failed to create commit: {commit_response.status_code}"}
                
                new_commit_sha = commit_response.json()["sha"]
                
                # Step 6: Update branch reference
                update_ref_payload = {"sha": new_commit_sha}
                
                update_ref_response = await client.patch(
                    ref_url,
                    headers=self.headers,
                    json=update_ref_payload,
                    timeout=15.0,
                )
                
                if update_ref_response.status_code != 200:
                    return {"error": f"Failed to update ref: {update_ref_response.status_code}"}
                
                logger.info(f"[GitHub] Committed {len(tree_items)} files to {repo_name}")
                
                return {
                    "success": True,
                    "commit_sha": new_commit_sha,
                    "files_committed": len(tree_items),
                    "branch": branch,
                    "commit_url": f"https://github.com/{owner}/{repo_name}/commit/{new_commit_sha}",
                }
                
        except Exception as e:
            logger.exception(f"[GitHub] Commit error: {e}")
            return {"error": str(e)}
    
    async def _initial_commit(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo_name: str,
        files: Dict[str, str],
        message: str,
        branch: str,
    ) -> Dict[str, Any]:
        """Create initial commit for empty repository."""
        try:
            # Create blobs
            tree_items = []
            for path, content in files.items():
                blob_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/blobs"
                blob_response = await client.post(
                    blob_url,
                    headers=self.headers,
                    json={"content": content, "encoding": "utf-8"},
                    timeout=30.0,
                )
                
                if blob_response.status_code == 201:
                    tree_items.append({
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_response.json()["sha"],
                    })
            
            # Create tree
            tree_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/trees"
            tree_response = await client.post(
                tree_url,
                headers=self.headers,
                json={"tree": tree_items},
                timeout=30.0,
            )
            
            if tree_response.status_code != 201:
                return {"error": "Failed to create initial tree"}
            
            tree_sha = tree_response.json()["sha"]
            
            # Create commit
            commit_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/commits"
            commit_response = await client.post(
                commit_url,
                headers=self.headers,
                json={"message": message, "tree": tree_sha, "parents": []},
                timeout=30.0,
            )
            
            if commit_response.status_code != 201:
                return {"error": "Failed to create initial commit"}
            
            commit_sha = commit_response.json()["sha"]
            
            # Create branch reference
            ref_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/git/refs"
            ref_response = await client.post(
                ref_url,
                headers=self.headers,
                json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
                timeout=15.0,
            )
            
            if ref_response.status_code != 201:
                return {"error": "Failed to create branch"}
            
            return {
                "success": True,
                "commit_sha": commit_sha,
                "files_committed": len(tree_items),
                "branch": branch,
                "commit_url": f"https://github.com/{owner}/{repo_name}/commit/{commit_sha}",
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_username(self) -> str:
        """Get authenticated user's username."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    headers=self.headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json().get("login", "")
        except Exception:
            pass
        return ""
    
    async def delete_repository(self, repo_name: str) -> Dict[str, Any]:
        """Delete a repository (requires admin permissions)."""
        if not self.token:
            return {"error": "GitHub token not configured"}
        
        owner = self.org or await self._get_username()
        url = f"{self.BASE_URL}/repos/{owner}/{repo_name}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 204:
                    logger.info(f"[GitHub] Deleted repo: {owner}/{repo_name}")
                    return {"success": True}
                else:
                    return {"error": f"Failed to delete: {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
github_service = GitHubService()


# =============================================================================
# DATABASE INTEGRATION
# =============================================================================

async def deploy_project_to_github(project_id: int, user_id: int) -> Dict[str, Any]:
    """
    Deploy a Faz Code project to GitHub.
    
    Creates a repository and commits all project files.
    
    Args:
        project_id: The project ID
        user_id: The user ID
        
    Returns:
        Deployment result with repo URL
    """
    try:
        # Get project
        project = await db.fetchrow(
            """SELECT name, slug, original_prompt, architecture 
               FROM faz_projects WHERE project_id = $1 AND user_id = $2""",
            project_id,
            user_id,
        )
        
        if not project:
            return {"error": "Project not found"}
        
        # Get files
        files = await db.fetch(
            "SELECT path, content FROM faz_files WHERE project_id = $1",
            project_id,
        )
        
        if not files:
            return {"error": "No files to deploy"}
        
        file_dict = {f["path"]: f["content"] for f in files}
        
        # Create repository
        repo_result = await github_service.create_repository(
            name=f"faz-{project['slug']}",
            description=f"Generated by Faz Code: {project['original_prompt'][:100]}...",
            private=False,
        )
        
        if repo_result.get("error"):
            return repo_result
        
        repo_name = repo_result["name"]
        
        # Commit files
        commit_result = await github_service.commit_files(
            repo_name=repo_name,
            files=file_dict,
            message=f"Initial commit - {project['name']}\n\nGenerated by Faz Code AI",
        )
        
        if commit_result.get("error"):
            return commit_result
        
        # Update project with GitHub info
        await db.execute(
            """UPDATE faz_projects 
               SET github_repo = $1, updated_at = NOW() 
               WHERE project_id = $2""",
            repo_result["html_url"],
            project_id,
        )
        
        logger.info(f"[GitHub] Deployed project {project_id} to {repo_result['html_url']}")
        
        return {
            "success": True,
            "github_url": repo_result["html_url"],
            "repo_name": repo_result["full_name"],
            "commit_sha": commit_result["commit_sha"],
            "files_committed": commit_result["files_committed"],
        }
        
    except Exception as e:
        logger.exception(f"[GitHub] Deploy error: {e}")
        return {"error": str(e)}


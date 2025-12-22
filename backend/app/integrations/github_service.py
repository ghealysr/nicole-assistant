"""
GitHub Integration Service for Vibe Dashboard

Enables Vibe projects to be deployed to GitHub repositories.
Supports:
- Repository creation
- File upload/commit
- Branch management
- Repository URL generation

Author: AlphaWave Architecture
Version: 1.0.0
"""

import base64
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GitHubFile:
    """Represents a file to commit."""
    path: str
    content: str


@dataclass
class GitHubRepo:
    """Represents a created repository."""
    name: str
    full_name: str
    html_url: str
    clone_url: str
    ssh_url: str


class GitHubService:
    """
    Async GitHub API client for repository management.
    
    Used by Vibe Dashboard to create repositories and deploy code.
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str, org: Optional[str] = None):
        """
        Initialize GitHub service.
        
        Args:
            token: Personal access token or GitHub App token
            org: Organization name (if None, uses authenticated user)
        """
        self.token = token
        self.org = org
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if GitHub is properly configured."""
        return bool(self.token)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = True,
        auto_init: bool = False
    ) -> Optional[GitHubRepo]:
        """
        Create a new repository.
        
        Args:
            name: Repository name (will be slugified)
            description: Repository description
            private: Whether repo is private
            auto_init: Initialize with README
            
        Returns:
            GitHubRepo on success, None on failure
        """
        if not self.is_configured:
            logger.warning("[GITHUB] Not configured, skipping repo creation")
            return None
        
        client = await self._get_client()
        
        # Use org endpoint if org is set, otherwise user endpoint
        if self.org:
            url = f"/orgs/{self.org}/repos"
        else:
            url = "/user/repos"
        
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        
        try:
            response = await client.post(url, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                repo = GitHubRepo(
                    name=data["name"],
                    full_name=data["full_name"],
                    html_url=data["html_url"],
                    clone_url=data["clone_url"],
                    ssh_url=data["ssh_url"],
                )
                logger.info("[GITHUB] Created repository: %s", repo.html_url)
                return repo
            elif response.status_code == 422:
                # Repository may already exist
                error = response.json()
                if "already exists" in str(error):
                    logger.info("[GITHUB] Repository already exists: %s", name)
                    return await self.get_repository(name)
                logger.error("[GITHUB] Validation error: %s", error)
                return None
            else:
                logger.error(
                    "[GITHUB] Failed to create repo: %s - %s",
                    response.status_code,
                    response.text
                )
                return None
                
        except Exception as e:
            logger.error("[GITHUB] Error creating repository: %s", e, exc_info=True)
            return None
    
    async def get_repository(self, name: str) -> Optional[GitHubRepo]:
        """Get repository details."""
        if not self.is_configured:
            return None
        
        client = await self._get_client()
        owner = self.org or (await self._get_authenticated_user())
        
        if not owner:
            return None
        
        try:
            response = await client.get(f"/repos/{owner}/{name}")
            
            if response.status_code == 200:
                data = response.json()
                return GitHubRepo(
                    name=data["name"],
                    full_name=data["full_name"],
                    html_url=data["html_url"],
                    clone_url=data["clone_url"],
                    ssh_url=data["ssh_url"],
                )
            return None
        except Exception as e:
            logger.error("[GITHUB] Error getting repository: %s", e)
            return None
    
    async def _get_authenticated_user(self) -> Optional[str]:
        """Get authenticated user's login."""
        client = await self._get_client()
        try:
            response = await client.get("/user")
            if response.status_code == 200:
                return response.json().get("login")
        except Exception:
            pass
        return None
    
    async def commit_files(
        self,
        repo_name: str,
        files: List[GitHubFile],
        message: str = "Initial commit from Vibe",
        branch: str = "main"
    ) -> bool:
        """
        Commit multiple files to a repository.
        
        Uses the Git Trees API for efficient multi-file commits.
        
        Args:
            repo_name: Repository name
            files: List of files to commit
            message: Commit message
            branch: Target branch
            
        Returns:
            True on success
        """
        if not self.is_configured:
            return False
        
        client = await self._get_client()
        owner = self.org or (await self._get_authenticated_user())
        
        if not owner:
            logger.error("[GITHUB] Could not determine repository owner")
            return False
        
        repo_path = f"/repos/{owner}/{repo_name}"
        
        try:
            # Step 1: Get the latest commit SHA from the branch
            ref_response = await client.get(f"{repo_path}/git/refs/heads/{branch}")
            
            if ref_response.status_code == 404:
                # Branch doesn't exist, create initial commit
                return await self._create_initial_commit(
                    client, repo_path, files, message, branch
                )
            
            if ref_response.status_code != 200:
                logger.error("[GITHUB] Failed to get ref: %s", ref_response.text)
                return False
            
            latest_commit_sha = ref_response.json()["object"]["sha"]
            
            # Step 2: Get the tree of the latest commit
            commit_response = await client.get(
                f"{repo_path}/git/commits/{latest_commit_sha}"
            )
            base_tree_sha = commit_response.json()["tree"]["sha"]
            
            # Step 3: Create blobs for each file
            tree_items = []
            for file in files:
                blob_response = await client.post(
                    f"{repo_path}/git/blobs",
                    json={
                        "content": base64.b64encode(file.content.encode()).decode(),
                        "encoding": "base64"
                    }
                )
                if blob_response.status_code != 201:
                    logger.error("[GITHUB] Failed to create blob for %s", file.path)
                    continue
                
                blob_sha = blob_response.json()["sha"]
                tree_items.append({
                    "path": file.path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                })
            
            # Step 4: Create new tree
            tree_response = await client.post(
                f"{repo_path}/git/trees",
                json={"base_tree": base_tree_sha, "tree": tree_items}
            )
            if tree_response.status_code != 201:
                logger.error("[GITHUB] Failed to create tree: %s", tree_response.text)
                return False
            
            new_tree_sha = tree_response.json()["sha"]
            
            # Step 5: Create commit
            commit_response = await client.post(
                f"{repo_path}/git/commits",
                json={
                    "message": message,
                    "tree": new_tree_sha,
                    "parents": [latest_commit_sha]
                }
            )
            if commit_response.status_code != 201:
                logger.error("[GITHUB] Failed to create commit: %s", commit_response.text)
                return False
            
            new_commit_sha = commit_response.json()["sha"]
            
            # Step 6: Update branch reference
            update_response = await client.patch(
                f"{repo_path}/git/refs/heads/{branch}",
                json={"sha": new_commit_sha}
            )
            if update_response.status_code != 200:
                logger.error("[GITHUB] Failed to update ref: %s", update_response.text)
                return False
            
            logger.info(
                "[GITHUB] Committed %d files to %s/%s",
                len(files), owner, repo_name
            )
            return True
            
        except Exception as e:
            logger.error("[GITHUB] Error committing files: %s", e, exc_info=True)
            return False
    
    async def _create_initial_commit(
        self,
        client: httpx.AsyncClient,
        repo_path: str,
        files: List[GitHubFile],
        message: str,
        branch: str
    ) -> bool:
        """Create initial commit for empty repository."""
        try:
            # Create blobs
            tree_items = []
            for file in files:
                blob_response = await client.post(
                    f"{repo_path}/git/blobs",
                    json={
                        "content": base64.b64encode(file.content.encode()).decode(),
                        "encoding": "base64"
                    }
                )
                if blob_response.status_code != 201:
                    continue
                
                tree_items.append({
                    "path": file.path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_response.json()["sha"]
                })
            
            # Create tree
            tree_response = await client.post(
                f"{repo_path}/git/trees",
                json={"tree": tree_items}
            )
            if tree_response.status_code != 201:
                return False
            
            tree_sha = tree_response.json()["sha"]
            
            # Create commit (no parents for initial)
            commit_response = await client.post(
                f"{repo_path}/git/commits",
                json={"message": message, "tree": tree_sha, "parents": []}
            )
            if commit_response.status_code != 201:
                return False
            
            commit_sha = commit_response.json()["sha"]
            
            # Create branch reference
            ref_response = await client.post(
                f"{repo_path}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": commit_sha}
            )
            
            return ref_response.status_code == 201
            
        except Exception as e:
            logger.error("[GITHUB] Error creating initial commit: %s", e)
            return False


# Global instance (lazy-loaded with settings)
_github_service: Optional[GitHubService] = None


def get_github_service() -> GitHubService:
    """Get the global GitHub service instance."""
    global _github_service
    if _github_service is None:
        from app.config import settings
        _github_service = GitHubService(
            token=settings.GITHUB_TOKEN,
            org=settings.GITHUB_ORG or None
        )
    return _github_service



"""
Vercel Integration Service for Vibe Dashboard

Enables Vibe projects to be deployed to Vercel from GitHub repositories.
Supports:
- Project creation
- Deployment triggering
- Deployment status checking
- Domain management

Author: AlphaWave Architecture
Version: 1.0.0
"""

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class VercelProject:
    """Represents a Vercel project."""
    id: str
    name: str
    account_id: str
    link: Optional[Dict[str, str]] = None


@dataclass
class VercelDeployment:
    """Represents a Vercel deployment."""
    id: str
    url: str
    state: str  # BUILDING, READY, ERROR, CANCELED
    created_at: int
    ready_at: Optional[int] = None


class VercelService:
    """
    Async Vercel API client for deployment management.
    
    Used by Vibe Dashboard to deploy Next.js projects.
    """
    
    BASE_URL = "https://api.vercel.com"
    
    def __init__(self, token: str, team_id: Optional[str] = None):
        """
        Initialize Vercel service.
        
        Args:
            token: Vercel API token
            team_id: Optional team ID for team deployments
        """
        self.token = token
        self.team_id = team_id
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Vercel is properly configured."""
        return bool(self.token)
    
    def _add_team_param(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add team ID to params if configured."""
        if self.team_id:
            params["teamId"] = self.team_id
        return params
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=60.0
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def create_project(
        self,
        name: str,
        github_repo: str,
        framework: str = "nextjs",
        build_command: str = "npm run build",
        output_directory: str = ".next",
        install_command: str = "npm install",
        root_directory: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Optional[VercelProject]:
        """
        Create a new Vercel project linked to a GitHub repository.
        
        Args:
            name: Project name
            github_repo: GitHub repo in format "owner/repo"
            framework: Framework preset (nextjs, react, etc.)
            build_command: Build command
            output_directory: Build output directory
            install_command: Install command
            root_directory: Subdirectory containing the project
            env_vars: Environment variables to set
            
        Returns:
            VercelProject on success, None on failure
        """
        if not self.is_configured:
            logger.warning("[VERCEL] Not configured, skipping project creation")
            return None
        
        client = await self._get_client()
        
        # Parse GitHub repo
        parts = github_repo.split("/")
        if len(parts) != 2:
            logger.error("[VERCEL] Invalid GitHub repo format: %s", github_repo)
            return None
        
        owner, repo = parts
        
        payload = {
            "name": name,
            "framework": framework,
            "gitRepository": {
                "type": "github",
                "repo": f"{owner}/{repo}",
            },
            "buildCommand": build_command,
            "outputDirectory": output_directory,
            "installCommand": install_command,
        }
        
        if root_directory:
            payload["rootDirectory"] = root_directory
        
        if env_vars:
            payload["environmentVariables"] = [
                {"key": k, "value": v, "type": "plain", "target": ["production", "preview"]}
                for k, v in env_vars.items()
            ]
        
        try:
            params = self._add_team_param({})
            response = await client.post("/v10/projects", json=payload, params=params)
            
            if response.status_code == 200:
                data = response.json()
                project = VercelProject(
                    id=data["id"],
                    name=data["name"],
                    account_id=data["accountId"],
                    link=data.get("link"),
                )
                logger.info("[VERCEL] Created project: %s", project.name)
                return project
            else:
                logger.error(
                    "[VERCEL] Failed to create project: %s - %s",
                    response.status_code,
                    response.text
                )
                return None
                
        except Exception as e:
            logger.error("[VERCEL] Error creating project: %s", e, exc_info=True)
            return None
    
    async def get_project(self, name: str) -> Optional[VercelProject]:
        """Get project by name."""
        if not self.is_configured:
            return None
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({})
            response = await client.get(f"/v9/projects/{name}", params=params)
            
            if response.status_code == 200:
                data = response.json()
                return VercelProject(
                    id=data["id"],
                    name=data["name"],
                    account_id=data["accountId"],
                    link=data.get("link"),
                )
            return None
        except Exception as e:
            logger.error("[VERCEL] Error getting project: %s", e)
            return None
    
    async def trigger_deployment(
        self,
        project_name: str,
        git_ref: str = "main"
    ) -> Optional[VercelDeployment]:
        """
        Trigger a new deployment for a project.
        
        Args:
            project_name: Vercel project name
            git_ref: Git branch or commit to deploy
            
        Returns:
            VercelDeployment on success
        """
        if not self.is_configured:
            return None
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({})
            payload = {
                "name": project_name,
                "target": "production",
                "gitSource": {
                    "ref": git_ref,
                    "type": "branch"
                }
            }
            
            response = await client.post("/v13/deployments", json=payload, params=params)
            
            if response.status_code in (200, 201):
                data = response.json()
                deployment = VercelDeployment(
                    id=data["id"],
                    url=f"https://{data.get('url', '')}",
                    state=data.get("readyState", "BUILDING"),
                    created_at=data.get("createdAt", 0),
                )
                logger.info("[VERCEL] Triggered deployment: %s", deployment.url)
                return deployment
            else:
                logger.error(
                    "[VERCEL] Failed to trigger deployment: %s - %s",
                    response.status_code,
                    response.text
                )
                return None
                
        except Exception as e:
            logger.error("[VERCEL] Error triggering deployment: %s", e, exc_info=True)
            return None
    
    async def get_deployment(self, deployment_id: str) -> Optional[VercelDeployment]:
        """Get deployment status."""
        if not self.is_configured:
            return None
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({})
            response = await client.get(f"/v13/deployments/{deployment_id}", params=params)
            
            if response.status_code == 200:
                data = response.json()
                return VercelDeployment(
                    id=data["id"],
                    url=f"https://{data.get('url', '')}",
                    state=data.get("readyState", "UNKNOWN"),
                    created_at=data.get("createdAt", 0),
                    ready_at=data.get("readyAt"),
                )
            return None
        except Exception as e:
            logger.error("[VERCEL] Error getting deployment: %s", e)
            return None
    
    async def get_production_deployment(
        self,
        project_name: str
    ) -> Optional[VercelDeployment]:
        """Get the current production deployment for a project."""
        if not self.is_configured:
            return None
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({"target": "production", "limit": 1})
            response = await client.get(
                f"/v6/deployments",
                params={**params, "projectId": project_name}
            )
            
            if response.status_code == 200:
                data = response.json()
                deployments = data.get("deployments", [])
                if deployments:
                    d = deployments[0]
                    return VercelDeployment(
                        id=d["uid"],
                        url=f"https://{d.get('url', '')}",
                        state=d.get("readyState", "UNKNOWN"),
                        created_at=d.get("createdAt", 0),
                        ready_at=d.get("readyAt"),
                    )
            return None
        except Exception as e:
            logger.error("[VERCEL] Error getting production deployment: %s", e)
            return None
    
    async def add_domain(
        self,
        project_name: str,
        domain: str
    ) -> bool:
        """Add a custom domain to a project."""
        if not self.is_configured:
            return False
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({})
            response = await client.post(
                f"/v10/projects/{project_name}/domains",
                json={"name": domain},
                params=params
            )
            
            success = response.status_code in (200, 201)
            if success:
                logger.info("[VERCEL] Added domain %s to project %s", domain, project_name)
            return success
            
        except Exception as e:
            logger.error("[VERCEL] Error adding domain: %s", e)
            return False


# Global instance (lazy-loaded with settings)
_vercel_service: Optional[VercelService] = None


def get_vercel_service() -> VercelService:
    """Get the global Vercel service instance."""
    global _vercel_service
    if _vercel_service is None:
        from app.config import settings
        _vercel_service = VercelService(
            token=settings.VERCEL_TOKEN,
            team_id=settings.VERCEL_TEAM_ID or None
        )
    return _vercel_service


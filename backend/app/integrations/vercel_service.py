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
    
    async def deploy_files(
        self,
        name: str,
        files: Dict[str, str],
        framework: str = "nextjs"
    ) -> Optional[VercelDeployment]:
        """
        Deploy files directly to Vercel without GitHub.
        
        This is used for Enjineer preview deployments where we upload
        the generated files directly.
        
        Args:
            name: Deployment name (used for URL)
            files: Dict of {path: content} for all project files
            framework: Framework preset (nextjs, react, static)
            
        Returns:
            VercelDeployment on success, None on failure
        """
        if not self.is_configured:
            logger.warning("[VERCEL] Not configured, skipping file deployment")
            return None
        
        client = await self._get_client()
        
        try:
            # Build files array for Vercel API
            # Each file needs: file (path), data (content)
            vercel_files = []
            for path, content in files.items():
                # Normalize path - remove leading slash for Vercel
                clean_path = path.lstrip('/')
                if not clean_path:
                    continue
                    
                vercel_files.append({
                    "file": clean_path,
                    "data": content
                })
            
            if not vercel_files:
                logger.error("[VERCEL] No files to deploy")
                return None
            
            # Determine project settings based on framework
            project_settings = {}
            if framework == "nextjs":
                project_settings = {
                    "framework": "nextjs",
                    "buildCommand": "npm run build",
                    "outputDirectory": ".next",
                    "installCommand": "npm install"
                }
            elif framework == "react":
                project_settings = {
                    "framework": "create-react-app",
                    "buildCommand": "npm run build",
                    "outputDirectory": "build",
                    "installCommand": "npm install"
                }
            else:
                # Static site - no build needed
                project_settings = {
                    "framework": None
                }
            
            payload = {
                "name": name,
                "files": vercel_files,
                # Don't specify target - Vercel will create a preview deployment by default
                "projectSettings": project_settings
            }
            
            params = self._add_team_param({})
            response = await client.post("/v13/deployments", json=payload, params=params)
            
            if response.status_code in (200, 201):
                data = response.json()
                deployment = VercelDeployment(
                    id=data["id"],
                    url=f"https://{data.get('url', '')}",
                    state=data.get("readyState", "BUILDING"),
                    created_at=data.get("createdAt", 0),
                )
                logger.info("[VERCEL] Created file deployment: %s", deployment.url)
                return deployment
            else:
                logger.error(
                    "[VERCEL] Failed to deploy files: %s - %s",
                    response.status_code,
                    response.text
                )
                return None
                
        except Exception as e:
            logger.error("[VERCEL] Error deploying files: %s", e, exc_info=True)
            return None
    
    async def delete_deployment(self, deployment_id: str) -> bool:
        """
        Delete a deployment.
        
        Used for cleaning up temporary preview deployments.
        
        Args:
            deployment_id: The deployment ID to delete
            
        Returns:
            True on success, False on failure
        """
        if not self.is_configured:
            return False
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({})
            response = await client.delete(f"/v13/deployments/{deployment_id}", params=params)
            
            success = response.status_code in (200, 204)
            if success:
                logger.info("[VERCEL] Deleted deployment: %s", deployment_id)
            else:
                logger.warning(
                    "[VERCEL] Failed to delete deployment %s: %s",
                    deployment_id,
                    response.text
                )
            return success
            
        except Exception as e:
            logger.error("[VERCEL] Error deleting deployment: %s", e)
            return False

    async def create_project_for_files(
        self,
        name: str,
        framework: str = "nextjs"
    ) -> Optional[VercelProject]:
        """
        Create a Vercel project for file-based deployments (no GitHub).
        
        Used by Enjineer to create persistent projects that receive
        multiple deployments over time.
        
        Args:
            name: Project name (will be used in URLs)
            framework: Framework preset (nextjs, react, static)
            
        Returns:
            VercelProject on success, None on failure
        """
        if not self.is_configured:
            logger.warning("[VERCEL] Not configured, skipping project creation")
            return None
        
        client = await self._get_client()
        
        # Determine build settings based on framework
        build_settings = {}
        if framework == "nextjs":
            build_settings = {
                "framework": "nextjs",
                "buildCommand": "npm run build",
                "outputDirectory": ".next",
                "installCommand": "npm install"
            }
        elif framework == "react":
            build_settings = {
                "framework": "create-react-app",
                "buildCommand": "npm run build",
                "outputDirectory": "build",
                "installCommand": "npm install"
            }
        # Static sites don't need build settings
        
        payload = {
            "name": name,
            **build_settings
        }
        
        try:
            params = self._add_team_param({})
            response = await client.post("/v10/projects", json=payload, params=params)
            
            if response.status_code in (200, 201):
                data = response.json()
                project = VercelProject(
                    id=data["id"],
                    name=data["name"],
                    account_id=data["accountId"],
                    link=data.get("link"),
                )
                logger.info("[VERCEL] Created file-based project: %s (id=%s)", project.name, project.id)
                return project
            elif response.status_code == 409:
                # Project already exists, fetch it
                logger.info("[VERCEL] Project %s already exists, fetching...", name)
                return await self.get_project(name)
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

    async def deploy_to_project(
        self,
        project_name: str,
        files: Dict[str, str],
        target: str = "preview",
        framework: str = "nextjs"
    ) -> Optional[VercelDeployment]:
        """
        Deploy files to an existing Vercel project.
        
        This ensures deployments go to the same project, keeping
        the same domain aliases and settings.
        
        Args:
            project_name: Existing Vercel project name
            files: Dict of {path: content} for all project files
            target: Deployment target ('preview' or 'production')
            framework: Framework preset
            
        Returns:
            VercelDeployment on success, None on failure
        """
        if not self.is_configured:
            logger.warning("[VERCEL] Not configured, skipping deployment")
            return None
        
        client = await self._get_client()
        
        try:
            # Build files array for Vercel API
            vercel_files = []
            for path, content in files.items():
                clean_path = path.lstrip('/')
                if not clean_path:
                    continue
                vercel_files.append({
                    "file": clean_path,
                    "data": content
                })
            
            if not vercel_files:
                logger.error("[VERCEL] No files to deploy")
                return None
            
            # Build settings based on framework
            project_settings = {}
            if framework == "nextjs":
                project_settings = {
                    "framework": "nextjs",
                    "buildCommand": "npm run build",
                    "outputDirectory": ".next",
                    "installCommand": "npm install"
                }
            elif framework == "react":
                project_settings = {
                    "framework": "create-react-app",
                    "buildCommand": "npm run build",
                    "outputDirectory": "build",
                    "installCommand": "npm install"
                }
            
            payload = {
                "name": project_name,  # Deploy to existing project
                "files": vercel_files,
                "projectSettings": project_settings
            }
            
            # Only include target for production deployments
            # Preview deployments should NOT specify target (Vercel default is preview)
            if target == "production":
                payload["target"] = "production"
            
            params = self._add_team_param({})
            response = await client.post("/v13/deployments", json=payload, params=params)
            
            if response.status_code in (200, 201):
                data = response.json()
                deployment = VercelDeployment(
                    id=data["id"],
                    url=f"https://{data.get('url', '')}",
                    state=data.get("readyState", "BUILDING"),
                    created_at=data.get("createdAt", 0),
                )
                logger.info("[VERCEL] Deployed to project %s: %s", project_name, deployment.url)
                return deployment
            else:
                logger.error(
                    "[VERCEL] Failed to deploy to project: %s - %s",
                    response.status_code,
                    response.text
                )
                return None
                
        except Exception as e:
            logger.error("[VERCEL] Error deploying to project: %s", e, exc_info=True)
            return None

    async def set_deployment_alias(
        self,
        deployment_id: str,
        alias: str
    ) -> bool:
        """
        Assign a custom domain alias to a deployment.
        
        This makes the deployment accessible at the specified domain.
        The domain must already be configured in Vercel.
        
        Args:
            deployment_id: The deployment to alias
            alias: The domain to point to this deployment
            
        Returns:
            True on success, False on failure
        """
        if not self.is_configured:
            return False
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({})
            payload = {"alias": alias}
            
            response = await client.post(
                f"/v2/deployments/{deployment_id}/aliases",
                json=payload,
                params=params
            )
            
            if response.status_code in (200, 201):
                logger.info("[VERCEL] Set alias %s for deployment %s", alias, deployment_id)
                return True
            else:
                logger.error(
                    "[VERCEL] Failed to set alias: %s - %s",
                    response.status_code,
                    response.text
                )
                return False
                
        except Exception as e:
            logger.error("[VERCEL] Error setting alias: %s", e)
            return False

    async def list_project_deployments(
        self,
        project_name: str,
        limit: int = 20
    ) -> list:
        """
        List recent deployments for a project.
        
        Used for cleanup and management.
        
        Args:
            project_name: Vercel project name
            limit: Maximum number of deployments to return
            
        Returns:
            List of deployment dicts
        """
        if not self.is_configured:
            return []
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({"projectId": project_name, "limit": limit})
            response = await client.get("/v6/deployments", params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("deployments", [])
            return []
            
        except Exception as e:
            logger.error("[VERCEL] Error listing deployments: %s", e)
            return []

    async def cleanup_old_deployments(
        self,
        project_name: str,
        keep_count: int = 3
    ) -> int:
        """
        Delete old deployments, keeping only the most recent ones.
        
        Args:
            project_name: Vercel project name
            keep_count: Number of recent deployments to keep
            
        Returns:
            Number of deployments deleted
        """
        deployments = await self.list_project_deployments(project_name, limit=50)
        
        if len(deployments) <= keep_count:
            return 0
        
        # Sort by creation time (newest first) and skip the ones to keep
        sorted_deps = sorted(deployments, key=lambda d: d.get("createdAt", 0), reverse=True)
        to_delete = sorted_deps[keep_count:]
        
        deleted = 0
        for dep in to_delete:
            dep_id = dep.get("uid") or dep.get("id")
            if dep_id and await self.delete_deployment(dep_id):
                deleted += 1
        
        logger.info("[VERCEL] Cleaned up %d old deployments from %s", deleted, project_name)
        return deleted

    async def delete_project(self, project_name: str) -> bool:
        """
        Delete a Vercel project and all its deployments.
        
        Args:
            project_name: Project name to delete
            
        Returns:
            True on success, False on failure
        """
        if not self.is_configured:
            return False
        
        client = await self._get_client()
        
        try:
            params = self._add_team_param({})
            response = await client.delete(f"/v9/projects/{project_name}", params=params)
            
            success = response.status_code in (200, 204)
            if success:
                logger.info("[VERCEL] Deleted project: %s", project_name)
            else:
                logger.warning(
                    "[VERCEL] Failed to delete project %s: %s",
                    project_name,
                    response.text
                )
            return success
            
        except Exception as e:
            logger.error("[VERCEL] Error deleting project: %s", e)
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


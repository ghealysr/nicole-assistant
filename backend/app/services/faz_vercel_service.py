"""
Faz Code Vercel Service

Handles Vercel project creation, deployments, and domain management for Faz Code projects.
Uses Vercel's REST API for programmatic deployment.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx

from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)


class VercelService:
    """
    Service for Vercel deployment operations.
    
    Capabilities:
    - Create Vercel projects from GitHub repos
    - Trigger deployments
    - Get deployment status
    - Manage environment variables
    """
    
    BASE_URL = "https://api.vercel.com"
    
    def __init__(self, token: Optional[str] = None, team_id: Optional[str] = None):
        """
        Initialize Vercel service.
        
        Args:
            token: Vercel access token (or use from settings)
            team_id: Vercel team ID (optional)
        """
        self.token = token or settings.VERCEL_TOKEN
        self.team_id = team_id or getattr(settings, 'VERCEL_TEAM_ID', None)
        
        if not self.token:
            logger.warning("[Vercel] No Vercel token configured")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    def _add_team_param(self, url: str) -> str:
        """Add team_id query parameter if configured."""
        if self.team_id:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}teamId={self.team_id}"
        return url
    
    async def create_project(
        self,
        name: str,
        github_repo: str,
        framework: str = "nextjs",
        build_command: Optional[str] = None,
        output_directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Vercel project from GitHub repository.
        
        Args:
            name: Project name
            github_repo: GitHub repo in format "owner/repo"
            framework: Framework preset (nextjs, vite, etc.)
            build_command: Custom build command
            output_directory: Output directory for build
            
        Returns:
            Project info dict
        """
        if not self.token:
            return {"error": "Vercel token not configured"}
        
        # Slugify name
        project_name = name.lower().replace(" ", "-").replace("_", "-")[:50]
        
        url = self._add_team_param(f"{self.BASE_URL}/v10/projects")
        
        payload: Dict[str, Any] = {
            "name": project_name,
            "framework": framework,
            "gitRepository": {
                "type": "github",
                "repo": github_repo,
            },
        }
        
        if build_command:
            payload["buildCommand"] = build_command
        if output_directory:
            payload["outputDirectory"] = output_directory
        
        # Add environment variables for Next.js
        payload["environmentVariables"] = [
            {"key": "NEXT_TELEMETRY_DISABLED", "value": "1", "target": ["production", "preview"]},
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"[Vercel] Created project: {data.get('name')}")
                    return {
                        "success": True,
                        "project_id": data.get("id"),
                        "name": data.get("name"),
                        "account_id": data.get("accountId"),
                        "framework": data.get("framework"),
                    }
                elif response.status_code == 409:
                    # Project already exists
                    return await self.get_project(project_name)
                else:
                    error_data = response.json()
                    logger.error(f"[Vercel] Create project failed: {response.status_code} {error_data}")
                    return {"error": f"Vercel API error: {error_data.get('error', {}).get('message', response.status_code)}"}
                    
        except Exception as e:
            logger.exception(f"[Vercel] Create project error: {e}")
            return {"error": str(e)}
    
    async def get_project(self, name: str) -> Dict[str, Any]:
        """Get project info by name or ID."""
        if not self.token:
            return {"error": "Vercel token not configured"}
        
        url = self._add_team_param(f"{self.BASE_URL}/v9/projects/{name}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "project_id": data.get("id"),
                        "name": data.get("name"),
                        "account_id": data.get("accountId"),
                        "framework": data.get("framework"),
                        "production_url": f"https://{data.get('name')}.vercel.app",
                    }
                else:
                    return {"error": f"Project not found: {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    async def trigger_deployment(
        self,
        project_id: str,
        target: str = "production",
    ) -> Dict[str, Any]:
        """
        Trigger a new deployment for a project.
        
        Args:
            project_id: Vercel project ID
            target: Deployment target (production, preview)
            
        Returns:
            Deployment info
        """
        if not self.token:
            return {"error": "Vercel token not configured"}
        
        url = self._add_team_param(f"{self.BASE_URL}/v13/deployments")
        
        payload = {
            "name": project_id,
            "target": target,
            "gitSource": {
                "type": "github",
                "ref": "main",
            },
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"[Vercel] Triggered deployment: {data.get('id')}")
                    return {
                        "success": True,
                        "deployment_id": data.get("id"),
                        "url": data.get("url"),
                        "state": data.get("state"),
                        "readyState": data.get("readyState"),
                    }
                else:
                    error_data = response.json()
                    return {"error": f"Deployment failed: {error_data.get('error', {}).get('message', response.status_code)}"}
                    
        except Exception as e:
            logger.exception(f"[Vercel] Trigger deployment error: {e}")
            return {"error": str(e)}
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status."""
        if not self.token:
            return {"error": "Vercel token not configured"}
        
        url = self._add_team_param(f"{self.BASE_URL}/v13/deployments/{deployment_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "deployment_id": data.get("id"),
                        "url": data.get("url"),
                        "state": data.get("state"),
                        "readyState": data.get("readyState"),
                        "ready": data.get("readyState") == "READY",
                        "production_url": f"https://{data.get('url')}" if data.get("url") else None,
                    }
                else:
                    return {"error": f"Deployment not found: {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    async def get_latest_deployment(self, project_id: str) -> Dict[str, Any]:
        """Get the latest deployment for a project."""
        if not self.token:
            return {"error": "Vercel token not configured"}
        
        url = self._add_team_param(
            f"{self.BASE_URL}/v6/deployments?projectId={project_id}&limit=1"
        )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    deployments = data.get("deployments", [])
                    
                    if deployments:
                        d = deployments[0]
                        return {
                            "success": True,
                            "deployment_id": d.get("uid"),
                            "url": d.get("url"),
                            "state": d.get("state"),
                            "ready": d.get("state") == "READY",
                            "created_at": d.get("created"),
                        }
                    return {"error": "No deployments found"}
                else:
                    return {"error": f"Failed to get deployments: {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    async def set_environment_variables(
        self,
        project_id: str,
        env_vars: Dict[str, str],
        target: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Set environment variables for a project.
        
        Args:
            project_id: Vercel project ID
            env_vars: Dict of key -> value
            target: Deployment targets (production, preview, development)
        """
        if not self.token:
            return {"error": "Vercel token not configured"}
        
        target = target or ["production", "preview"]
        url = self._add_team_param(f"{self.BASE_URL}/v10/projects/{project_id}/env")
        
        results = []
        
        try:
            async with httpx.AsyncClient() as client:
                for key, value in env_vars.items():
                    payload = {
                        "key": key,
                        "value": value,
                        "type": "encrypted",
                        "target": target,
                    }
                    
                    response = await client.post(
                        url,
                        headers=self.headers,
                        json=payload,
                        timeout=15.0,
                    )
                    
                    if response.status_code in (200, 201):
                        results.append({"key": key, "success": True})
                    else:
                        results.append({"key": key, "success": False, "error": response.status_code})
                
                return {"success": True, "results": results}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a Vercel project."""
        if not self.token:
            return {"error": "Vercel token not configured"}
        
        url = self._add_team_param(f"{self.BASE_URL}/v9/projects/{project_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 204:
                    logger.info(f"[Vercel] Deleted project: {project_id}")
                    return {"success": True}
                else:
                    return {"error": f"Failed to delete: {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
vercel_service = VercelService()


# =============================================================================
# DATABASE INTEGRATION
# =============================================================================

async def deploy_project_to_vercel(
    project_id: int,
    user_id: int,
    github_repo: str,
) -> Dict[str, Any]:
    """
    Deploy a Faz Code project to Vercel.
    
    Creates a Vercel project linked to GitHub repo and triggers deployment.
    
    Args:
        project_id: The project ID
        user_id: The user ID
        github_repo: GitHub repo in format "owner/repo"
        
    Returns:
        Deployment result with production URL
    """
    try:
        # Get project
        project = await db.fetchrow(
            """SELECT name, slug, github_repo 
               FROM faz_projects WHERE project_id = $1 AND user_id = $2""",
            project_id,
            user_id,
        )
        
        if not project:
            return {"error": "Project not found"}
        
        # Use provided github_repo or from project
        repo = github_repo or project.get("github_repo")
        if not repo:
            return {"error": "No GitHub repository configured"}
        
        # Extract owner/repo from URL if full URL provided
        if "github.com" in repo:
            repo = repo.replace("https://github.com/", "").rstrip("/")
        
        # Create Vercel project
        vercel_result = await vercel_service.create_project(
            name=f"faz-{project['slug']}",
            github_repo=repo,
            framework="nextjs",
        )
        
        if vercel_result.get("error"):
            return vercel_result
        
        vercel_project_id = vercel_result["project_id"]
        
        # Trigger deployment
        deploy_result = await vercel_service.trigger_deployment(
            project_id=vercel_project_id,
            target="production",
        )
        
        if deploy_result.get("error"):
            # Even if deployment trigger fails, project is created
            logger.warning(f"[Vercel] Deployment trigger failed but project created: {deploy_result}")
        
        # Construct production URL
        production_url = f"https://faz-{project['slug']}.vercel.app"
        
        # Update project with Vercel info
        await db.execute(
            """UPDATE faz_projects 
               SET vercel_project_id = $1, 
                   production_url = $2,
                   status = 'deploying',
                   updated_at = NOW() 
               WHERE project_id = $3""",
            vercel_project_id,
            production_url,
            project_id,
        )
        
        logger.info(f"[Vercel] Deployed project {project_id} to {production_url}")
        
        return {
            "success": True,
            "vercel_project_id": vercel_project_id,
            "production_url": production_url,
            "deployment_url": deploy_result.get("url"),
            "deployment_id": deploy_result.get("deployment_id"),
        }
        
    except Exception as e:
        logger.exception(f"[Vercel] Deploy error: {e}")
        return {"error": str(e)}


async def check_deployment_status(project_id: int) -> Dict[str, Any]:
    """Check and update deployment status for a project."""
    try:
        project = await db.fetchrow(
            "SELECT vercel_project_id, status FROM faz_projects WHERE project_id = $1",
            project_id,
        )
        
        if not project or not project["vercel_project_id"]:
            return {"error": "Project not deployed to Vercel"}
        
        # Get latest deployment
        result = await vercel_service.get_latest_deployment(project["vercel_project_id"])
        
        if result.get("success") and result.get("ready"):
            # Update status to deployed
            await db.execute(
                "UPDATE faz_projects SET status = 'deployed', updated_at = NOW() WHERE project_id = $1",
                project_id,
            )
            return {"success": True, "status": "deployed", **result}
        
        return result
        
    except Exception as e:
        return {"error": str(e)}


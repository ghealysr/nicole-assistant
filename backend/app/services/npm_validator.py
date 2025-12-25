"""
NPM Package Validator Service
=============================
Validates npm packages exist in the registry before adding to package.json.
Prevents invalid dependency errors that cause deployment failures.

Features:
- Package existence validation
- Version resolution
- Peer dependency checking
- React 19 compatibility warnings
- Caching to reduce API calls

Author: Nicole V7 Engineer Intelligence
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import httpx

from app.database import db

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ValidationResult:
    """Result of package validation."""
    package: str
    version: str
    valid: bool
    resolved_version: Optional[str] = None
    peer_dependencies: Dict[str, str] = field(default_factory=dict)
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class PackageJsonAudit:
    """Result of full package.json audit."""
    valid: bool
    total_packages: int
    invalid_packages: List[ValidationResult] = field(default_factory=list)
    peer_conflicts: List[str] = field(default_factory=list)
    deprecation_warnings: List[str] = field(default_factory=list)
    react_19_warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# ============================================================================
# KNOWN COMPATIBILITY ISSUES
# ============================================================================

# Packages known to have React 19 issues
REACT_19_INCOMPATIBLE = {
    "react-helmet": "Use react-helmet-async instead",
    "react-router-dom": "Requires v6.4+ for React 19",
    "@emotion/react": "Requires v11.11+ for React 19",
    "styled-components": "Requires v6+ for React 19",
    "react-beautiful-dnd": "Use @hello-pangea/dnd instead",
    "react-query": "Use @tanstack/react-query instead",
    "recoil": "Use jotai or zustand instead",
}

# Packages that don't exist or are commonly misspelled
KNOWN_INVALID_PACKAGES = {
    "@heroicons/react/outline": "Use @heroicons/react/24/outline",
    "@heroicons/react/solid": "Use @heroicons/react/24/solid",
    "next-fonts": "Use next/font (built-in)",
    "next-images": "Use next/image (built-in)",
    "@next/mdx": "Use next-mdx-remote or contentlayer",
    "framer-motion": "Use motion (v12 renamed)",
}

# Recommended replacements for deprecated packages
PACKAGE_REPLACEMENTS = {
    "moment": "date-fns or dayjs",
    "request": "node-fetch or axios",
    "uuid": "crypto.randomUUID() (built-in)",
    "lodash": "lodash-es (tree-shakeable)",
    "classnames": "clsx (smaller)",
}


# ============================================================================
# NPM VALIDATOR SERVICE
# ============================================================================

class NpmValidatorService:
    """
    Validates NPM packages before adding to projects.
    
    Prevents the "Module not found" deployment failures by checking
    the npm registry BEFORE adding packages to package.json.
    """
    
    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._cache_ttl = timedelta(hours=24)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Accept": "application/json"}
            )
        return self._http_client
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    # ========================================================================
    # CACHE OPERATIONS
    # ========================================================================
    
    async def _get_cached(
        self, 
        package: str, 
        version: str
    ) -> Optional[ValidationResult]:
        """Check cache for previous validation."""
        try:
            row = await db.fetchrow(
                """
                SELECT valid, resolved_version, peer_deps, deprecated, deprecation_message
                FROM enjineer_npm_cache
                WHERE package_name = $1 
                  AND version = $2
                  AND checked_at > NOW() - INTERVAL '24 hours'
                """,
                package, version
            )
            
            if row:
                return ValidationResult(
                    package=package,
                    version=version,
                    valid=row["valid"],
                    resolved_version=row["resolved_version"],
                    peer_dependencies=row["peer_deps"] or {},
                    deprecated=row["deprecated"],
                    deprecation_message=row["deprecation_message"],
                )
            return None
        except Exception as e:
            logger.warning(f"[NPM] Cache lookup failed: {e}")
            return None
    
    async def _set_cache(self, result: ValidationResult):
        """Cache validation result."""
        try:
            await db.execute(
                """
                INSERT INTO enjineer_npm_cache 
                (package_name, version, valid, resolved_version, peer_deps, deprecated, deprecation_message, checked_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (package_name, version) 
                DO UPDATE SET 
                    valid = EXCLUDED.valid,
                    resolved_version = EXCLUDED.resolved_version,
                    peer_deps = EXCLUDED.peer_deps,
                    deprecated = EXCLUDED.deprecated,
                    deprecation_message = EXCLUDED.deprecation_message,
                    checked_at = NOW()
                """,
                result.package,
                result.version,
                result.valid,
                result.resolved_version,
                result.peer_dependencies,
                result.deprecated,
                result.deprecation_message,
            )
        except Exception as e:
            logger.warning(f"[NPM] Cache write failed: {e}")
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    async def validate_package(
        self,
        package: str,
        version: str = "latest"
    ) -> ValidationResult:
        """
        Validate a single package exists in npm registry.
        
        Args:
            package: Package name (e.g., "react", "@types/node")
            version: Version string (e.g., "^18.0.0", "latest")
            
        Returns:
            ValidationResult with validity and metadata
        """
        # Check for known invalid packages first
        if package in KNOWN_INVALID_PACKAGES:
            return ValidationResult(
                package=package,
                version=version,
                valid=False,
                error=f"Package does not exist. {KNOWN_INVALID_PACKAGES[package]}"
            )
        
        # Check cache
        cached = await self._get_cached(package, version)
        if cached:
            logger.debug(f"[NPM] Cache hit: {package}@{version}")
            return cached
        
        # Query npm registry
        client = await self._get_client()
        
        try:
            # Handle scoped packages (@org/name)
            if package.startswith("@"):
                encoded_package = package.replace("/", "%2F")
            else:
                encoded_package = package
            
            url = f"https://registry.npmjs.org/{encoded_package}"
            response = await client.get(url)
            
            if response.status_code == 404:
                result = ValidationResult(
                    package=package,
                    version=version,
                    valid=False,
                    error=f"Package '{package}' does not exist in npm registry"
                )
                await self._set_cache(result)
                return result
            
            if response.status_code != 200:
                return ValidationResult(
                    package=package,
                    version=version,
                    valid=False,
                    error=f"npm registry returned status {response.status_code}"
                )
            
            data = response.json()
            
            # Parse version
            base_version = self._parse_version(version)
            available_versions = list(data.get("versions", {}).keys())
            
            if not available_versions:
                result = ValidationResult(
                    package=package,
                    version=version,
                    valid=False,
                    error=f"Package '{package}' has no published versions"
                )
                await self._set_cache(result)
                return result
            
            # Find matching version
            if version == "latest":
                resolved = data.get("dist-tags", {}).get("latest", available_versions[-1])
            else:
                resolved = self._find_matching_version(base_version, available_versions)
            
            if not resolved:
                result = ValidationResult(
                    package=package,
                    version=version,
                    valid=False,
                    error=f"Version '{version}' not found. Latest: {available_versions[-1]}"
                )
                await self._set_cache(result)
                return result
            
            # Get version metadata
            version_data = data.get("versions", {}).get(resolved, {})
            peer_deps = version_data.get("peerDependencies", {})
            
            # Check for deprecation
            deprecated = bool(version_data.get("deprecated"))
            deprecation_msg = version_data.get("deprecated")
            
            # Build warnings
            warnings = []
            if deprecated:
                warnings.append(f"Package is deprecated: {deprecation_msg}")
            if package in PACKAGE_REPLACEMENTS:
                warnings.append(f"Consider using: {PACKAGE_REPLACEMENTS[package]}")
            
            result = ValidationResult(
                package=package,
                version=version,
                valid=True,
                resolved_version=resolved,
                peer_dependencies=peer_deps,
                deprecated=deprecated,
                deprecation_message=deprecation_msg,
                warnings=warnings,
            )
            
            await self._set_cache(result)
            return result
            
        except httpx.TimeoutException:
            return ValidationResult(
                package=package,
                version=version,
                valid=False,
                error="npm registry request timed out"
            )
        except Exception as e:
            logger.error(f"[NPM] Validation failed for {package}@{version}: {e}")
            return ValidationResult(
                package=package,
                version=version,
                valid=False,
                error=f"Validation failed: {str(e)}"
            )
    
    def _parse_version(self, version: str) -> str:
        """Extract base version from semver string."""
        # Remove ^, ~, >=, etc.
        return re.sub(r'^[\^~>=<]+', '', version)
    
    def _find_matching_version(
        self, 
        requested: str, 
        available: List[str]
    ) -> Optional[str]:
        """Find a matching version from available versions."""
        # Exact match
        if requested in available:
            return requested
        
        # Try to find compatible version
        for version in reversed(available):
            if version.startswith(requested.split('.')[0]):
                return version
        
        # No match found
        return None
    
    # ========================================================================
    # PACKAGE.JSON AUDIT
    # ========================================================================
    
    async def audit_package_json(
        self,
        package_json: Dict[str, Any]
    ) -> PackageJsonAudit:
        """
        Audit all dependencies in a package.json.
        
        Args:
            package_json: Parsed package.json contents
            
        Returns:
            PackageJsonAudit with all validation results
        """
        all_deps: Dict[str, str] = {}
        all_deps.update(package_json.get("dependencies", {}))
        all_deps.update(package_json.get("devDependencies", {}))
        
        invalid_packages: List[ValidationResult] = []
        peer_conflicts: List[str] = []
        deprecation_warnings: List[str] = []
        react_19_warnings: List[str] = []
        recommendations: List[str] = []
        
        # Check React version
        react_version = all_deps.get("react", "")
        is_react_19 = "19" in react_version or "rc" in react_version or "canary" in react_version
        
        # Validate each package concurrently
        tasks = [
            self.validate_package(name, version)
            for name, version in all_deps.items()
        ]
        results = await asyncio.gather(*tasks)
        
        # Process results
        all_peer_deps: Dict[str, Set[str]] = {}
        
        for result in results:
            if not result.valid:
                invalid_packages.append(result)
                logger.warning(f"[NPM] ❌ Invalid: {result.package}@{result.version} - {result.error}")
            
            if result.deprecated:
                deprecation_warnings.append(
                    f"{result.package}: {result.deprecation_message}"
                )
            
            if result.warnings:
                recommendations.extend(result.warnings)
            
            # Track peer dependencies
            for peer, peer_version in result.peer_dependencies.items():
                if peer not in all_peer_deps:
                    all_peer_deps[peer] = set()
                all_peer_deps[peer].add(f"{result.package} requires {peer}@{peer_version}")
            
            # Check React 19 compatibility
            if is_react_19 and result.package in REACT_19_INCOMPATIBLE:
                react_19_warnings.append(
                    f"{result.package}: {REACT_19_INCOMPATIBLE[result.package]}"
                )
        
        # Check for peer dependency conflicts
        for peer, requirements in all_peer_deps.items():
            installed_version = all_deps.get(peer)
            if installed_version is None and peer not in ["react", "react-dom"]:
                # Missing peer dependency
                peer_conflicts.append(
                    f"Missing peer: {peer} - required by: {', '.join(requirements)}"
                )
        
        return PackageJsonAudit(
            valid=len(invalid_packages) == 0,
            total_packages=len(all_deps),
            invalid_packages=invalid_packages,
            peer_conflicts=peer_conflicts,
            deprecation_warnings=deprecation_warnings,
            react_19_warnings=react_19_warnings,
            recommendations=list(set(recommendations)),  # Dedupe
        )
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    async def suggest_version(self, package: str) -> Optional[str]:
        """Get the latest stable version of a package."""
        result = await self.validate_package(package, "latest")
        return result.resolved_version if result.valid else None
    
    async def check_exists(self, package: str) -> bool:
        """Quick check if a package exists."""
        result = await self.validate_package(package, "latest")
        return result.valid


# Global service instance
npm_validator = NpmValidatorService()


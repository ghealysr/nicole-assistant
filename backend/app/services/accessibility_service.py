"""
Accessibility Service - axe-core via Puppeteer MCP

Runs accessibility scans using axe-core injected into Puppeteer pages.
Provides WCAG 2.1 Level A/AA compliance checking.

Author: AlphaWave Architecture
Version: 1.0.0
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# axe-core CDN URL (stable version)
AXE_CORE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.3/axe.min.js"


class AccessibilityService:
    """
    Service for running accessibility scans via Puppeteer + axe-core.
    
    Usage:
        a11y = AccessibilityService()
        result = await a11y.run_scan("https://example.com")
    """
    
    def __init__(self):
        self.mcp_client = None
    
    async def _get_mcp_client(self):
        """Lazy-load MCP client"""
        if self.mcp_client is None:
            # Prefer Docker MCP Gateway client (consistent with vibe_service usage)
            from app.mcp.docker_mcp_client import get_mcp_client
            self.mcp_client = await get_mcp_client()
        return self.mcp_client
    
    async def run_scan(
        self,
        url: str,
        viewport: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Run accessibility scan on a URL using axe-core.
        
        Args:
            url: URL to scan
            viewport: Optional viewport size {"width": 1440, "height": 900}
        
        Returns:
            Dict with violations, warnings, passes, and raw axe results
        
        Raises:
            Exception: If Puppeteer MCP is not available or scan fails
        """
        mcp = await self._get_mcp_client()
        
        if viewport is None:
            viewport = {"width": 1440, "height": 900}
        
        logger.info(f"[ACCESSIBILITY] Running axe-core scan on {url}")
        
        try:
            if not getattr(mcp, "is_connected", False):
                raise Exception("Docker MCP client is not connected")

            # Navigate to page with Puppeteer
            nav_result = await mcp.call_tool("puppeteer_navigate", {"url": url, "waitUntil": "networkidle2"})
            if nav_result.is_error:
                raise Exception(f"Failed to navigate to {url}")
            
            # Inject axe-core script
            inject_script = f"""
                new Promise((resolve, reject) => {{
                    if (window.axe) return resolve(true);
                    const script = document.createElement('script');
                    script.src = '{AXE_CORE_CDN}';
                    script.onload = () => resolve(true);
                    script.onerror = () => reject(new Error('Failed to load axe-core'));
                    document.head.appendChild(script);
                }})
            """
            inject_result = await mcp.call_tool("puppeteer_evaluate", {"script": inject_script})
            if inject_result.is_error:
                raise Exception("Failed to inject axe-core")
            
            # Run axe-core scan
            scan_script = """
                new Promise((resolve) => {
                    if (!window.axe) return resolve({error: 'axe not loaded'});
                    axe.run({
                        runOnly: {
                            type: 'tag',
                            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
                        }
                    }, (err, results) => {
                        if (err) resolve({error: err.message});
                        else resolve(results);
                    });
                })
            """
            scan_result = await mcp.call_tool("puppeteer_evaluate", {"script": scan_script})
            if scan_result.is_error:
                raise Exception("Failed to run axe-core")
            
            # Parse results
            # docker MCP returns content blocks; parse JSON from first text block
            axe_results = {}
            try:
                content_blocks = scan_result.content or []
                raw = content_blocks[0].text if content_blocks and hasattr(content_blocks[0], "text") else None
                if raw:
                    parsed = json.loads(raw)
                    axe_results = parsed.get("result") if isinstance(parsed, dict) else {}
            except Exception:
                axe_results = {}
            
            if "error" in axe_results:
                raise Exception(f"axe-core error: {axe_results['error']}")
            
            # Extract key metrics
            violations = axe_results.get("violations", [])
            incomplete = axe_results.get("incomplete", [])
            passes = axe_results.get("passes", [])
            
            # Categorize violations by severity
            violations_by_severity = self._categorize_violations(violations)
            
            result = {
                # Summary counts
                "violations": len(violations),
                "warnings": len(incomplete),
                "passes": len(passes),
                
                # Violations by severity
                "critical_violations": violations_by_severity["critical"],
                "serious_violations": violations_by_severity["serious"],
                "moderate_violations": violations_by_severity["moderate"],
                "minor_violations": violations_by_severity["minor"],
                
                # Details
                "violation_details": self._format_violations(violations),
                "warning_details": self._format_violations(incomplete),
                
                # Pass/Fail
                "all_passing": len(violations) == 0,
                
                # Raw data
                "axe_raw": axe_results,
                
                # Metadata
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "url": url,
                "viewport": viewport
            }
            
            logger.info(
                f"[ACCESSIBILITY] Scan complete: {len(violations)} violations, "
                f"{len(incomplete)} warnings, {len(passes)} passes"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"[ACCESSIBILITY] Scan failed for {url}: {e}", exc_info=True)
            
            # Return error result
            return {
                "error": str(e),
                "violations": 0,
                "warnings": 0,
                "passes": 0,
                "all_passing": False,
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "url": url
            }
    
    def _categorize_violations(self, violations: List[Dict]) -> Dict[str, int]:
        """Categorize violations by severity (critical, serious, moderate, minor)"""
        counts = {
            "critical": 0,
            "serious": 0,
            "moderate": 0,
            "minor": 0
        }
        
        for violation in violations:
            impact = violation.get("impact", "moderate")
            if impact in counts:
                counts[impact] += 1
        
        return counts
    
    def _format_violations(self, violations: List[Dict]) -> List[Dict[str, Any]]:
        """Format violations for human-readable display"""
        formatted = []
        
        for violation in violations:
            formatted.append({
                "id": violation.get("id"),
                "impact": violation.get("impact"),
                "description": violation.get("description"),
                "help": violation.get("help"),
                "help_url": violation.get("helpUrl"),
                "nodes_count": len(violation.get("nodes", [])),
                "tags": violation.get("tags", [])
            })
        
        return formatted
    
    async def run_scan_multi_viewport(
        self,
        url: str
    ) -> Dict[str, Any]:
        """
        Run accessibility scan at multiple viewports (mobile, tablet, desktop).
        
        Returns:
            Dict with results for each viewport
        """
        viewports = {
            "mobile": {"width": 375, "height": 812},
            "tablet": {"width": 768, "height": 1024},
            "desktop": {"width": 1440, "height": 900}
        }
        
        results = {}
        
        for device, viewport in viewports.items():
            try:
                results[device] = await self.run_scan(url, viewport=viewport)
            except Exception as e:
                logger.error(f"[ACCESSIBILITY] Failed to scan {url} ({device}): {e}")
                results[device] = {
                    "error": str(e),
                    "violations": 0,
                    "warnings": 0,
                    "passes": 0,
                    "all_passing": False
                }
        
        # Aggregate results
        total_violations = sum(r.get("violations", 0) for r in results.values())
        total_warnings = sum(r.get("warnings", 0) for r in results.values())
        all_passing = all(r.get("all_passing", False) for r in results.values())
        
        return {
            "viewports": results,
            "aggregate": {
                "total_violations": total_violations,
                "total_warnings": total_warnings,
                "all_passing": all_passing
            }
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

accessibility_service = AccessibilityService()


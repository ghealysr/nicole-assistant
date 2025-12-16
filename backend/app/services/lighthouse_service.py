"""
Lighthouse Service - PageSpeed Insights API Integration

Provides Lighthouse scores via Google's PageSpeed Insights API:
- Performance, Accessibility, Best Practices, SEO scores
- Core Web Vitals (LCP, FID, CLS)
- Detailed audit results

Author: AlphaWave Architecture
Version: 1.0.0
"""

import logging
import httpx
from typing import Dict, Any, Optional, Literal
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

# PageSpeed Insights API endpoint
PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# API key from environment
PAGESPEED_API_KEY = getattr(settings, "PAGESPEED_API_KEY", "AIzaSyBCHN4ej7qDAwsGhLmZMs_wqd7fi5kSM6c")


class LighthouseService:
    """
    Service for running Lighthouse audits via PageSpeed Insights API.
    
    Usage:
        lighthouse = LighthouseService()
        result = await lighthouse.run_audit("https://example.com", strategy="mobile")
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or PAGESPEED_API_KEY
        if not self.api_key:
            logger.warning("[LIGHTHOUSE] No API key configured. Set PAGESPEED_API_KEY in .env")
    
    async def run_audit(
        self,
        url: str,
        strategy: Literal["mobile", "desktop"] = "mobile",
        categories: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Run Lighthouse audit via PageSpeed Insights API.
        
        Args:
            url: URL to audit
            strategy: "mobile" or "desktop"
            categories: List of categories to audit (default: all)
        
        Returns:
            Dict with scores, metrics, and raw data
        
        Raises:
            httpx.HTTPError: If API call fails
        """
        if not self.api_key:
            raise ValueError("PageSpeed Insights API key not configured")
        
        # Default categories
        if categories is None:
            categories = ["performance", "accessibility", "best-practices", "seo"]
        
        # Build request params
        params = {
            "url": url,
            "key": self.api_key,
            "strategy": strategy,
        }
        
        # Add categories
        for category in categories:
            params[f"category"] = category
        
        logger.info(f"[LIGHTHOUSE] Running audit for {url} ({strategy})")
        
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.get(PAGESPEED_API_URL, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Extract scores and metrics
            result = self._parse_lighthouse_result(data)
            
            logger.info(
                f"[LIGHTHOUSE] Audit complete: Performance={result['performance']}, "
                f"Accessibility={result['accessibility']}, "
                f"Best Practices={result['best_practices']}, "
                f"SEO={result['seo']}"
            )
            
            return result
        
        except httpx.HTTPError as e:
            logger.error(f"[LIGHTHOUSE] API error for {url}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[LIGHTHOUSE] Unexpected error for {url}: {e}", exc_info=True)
            raise
    
    def _parse_lighthouse_result(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse PageSpeed Insights API response into simplified format.
        
        Extracts:
        - Category scores (0-100)
        - Core Web Vitals
        - Key metrics
        - Raw data for storage
        """
        lighthouse_result = api_response.get("lighthouseResult", {})
        categories = lighthouse_result.get("categories", {})
        audits = lighthouse_result.get("audits", {})
        
        # Category scores (convert 0-1 to 0-100)
        performance_score = categories.get("performance", {}).get("score")
        accessibility_score = categories.get("accessibility", {}).get("score")
        best_practices_score = categories.get("best-practices", {}).get("score")
        seo_score = categories.get("seo", {}).get("score")
        
        # Core Web Vitals
        lcp = audits.get("largest-contentful-paint", {}).get("numericValue")
        fid = audits.get("max-potential-fid", {}).get("numericValue")  # FID estimate
        cls = audits.get("cumulative-layout-shift", {}).get("numericValue")
        
        # First Contentful Paint
        fcp = audits.get("first-contentful-paint", {}).get("numericValue")
        
        # Time to Interactive
        tti = audits.get("interactive", {}).get("numericValue")
        
        # Speed Index
        speed_index = audits.get("speed-index", {}).get("numericValue")
        
        # Total Blocking Time
        tbt = audits.get("total-blocking-time", {}).get("numericValue")
        
        return {
            # Scores (0-100)
            "performance": int(performance_score * 100) if performance_score is not None else None,
            "accessibility": int(accessibility_score * 100) if accessibility_score is not None else None,
            "best_practices": int(best_practices_score * 100) if best_practices_score is not None else None,
            "seo": int(seo_score * 100) if seo_score is not None else None,
            
            # Core Web Vitals
            "lcp_score": round(lcp / 1000, 2) if lcp else None,  # Convert ms to seconds
            "fid_score": round(fid, 2) if fid else None,  # Already in ms
            "cls_score": round(cls, 4) if cls else None,  # Score value
            
            # Additional metrics
            "fcp": round(fcp / 1000, 2) if fcp else None,
            "tti": round(tti / 1000, 2) if tti else None,
            "speed_index": round(speed_index / 1000, 2) if speed_index else None,
            "tbt": round(tbt, 2) if tbt else None,
            
            # Pass/Fail indicators
            "all_passing": self._check_all_passing(
                performance_score,
                accessibility_score,
                best_practices_score,
                seo_score
            ),
            
            # Raw data for storage
            "lighthouse_raw": lighthouse_result,
            
            # Metadata
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "fetch_time": api_response.get("analysisUTCTimestamp")
        }
    
    def _check_all_passing(
        self,
        performance: Optional[float],
        accessibility: Optional[float],
        best_practices: Optional[float],
        seo: Optional[float]
    ) -> bool:
        """
        Check if all quality gates pass.
        
        Quality gates:
        - Performance >= 90
        - Accessibility >= 90
        - Best Practices >= 90
        - SEO >= 90
        """
        if any(score is None for score in [performance, accessibility, best_practices, seo]):
            return False
        
        return (
            performance >= 0.90 and
            accessibility >= 0.90 and
            best_practices >= 0.90 and
            seo >= 0.90
        )
    
    async def run_audit_both_strategies(self, url: str) -> Dict[str, Any]:
        """
        Run Lighthouse audit for both mobile and desktop.
        
        Returns:
            Dict with "mobile" and "desktop" keys
        """
        results = {}
        
        for strategy in ["mobile", "desktop"]:
            try:
                results[strategy] = await self.run_audit(url, strategy=strategy)
            except Exception as e:
                logger.error(f"[LIGHTHOUSE] Failed to audit {url} ({strategy}): {e}")
                results[strategy] = {
                    "error": str(e),
                    "performance": None,
                    "accessibility": None,
                    "best_practices": None,
                    "seo": None
                }
        
        return results


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

lighthouse_service = LighthouseService()

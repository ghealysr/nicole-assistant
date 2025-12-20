"""
Faz Code Screenshot Service

Captures screenshots of generated websites for QA and preview purposes.
Uses Playwright for reliable cross-browser rendering.
"""

import logging
import asyncio
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import tempfile
import os

logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("[Screenshot] Playwright not installed. Install with: pip install playwright && playwright install")


class ScreenshotService:
    """
    Service for capturing website screenshots.
    
    Supports:
    - Full page screenshots
    - Viewport-specific screenshots (desktop, tablet, mobile)
    - Element-specific screenshots
    - PDF generation
    """
    
    VIEWPORTS = {
        'desktop': {'width': 1920, 'height': 1080},
        'laptop': {'width': 1440, 'height': 900},
        'tablet': {'width': 768, 'height': 1024},
        'mobile': {'width': 375, 'height': 812},
    }
    
    def __init__(self):
        self._browser: Optional[Browser] = None
        self._playwright = None
    
    async def _ensure_browser(self) -> Browser:
        """Ensure browser is launched."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed")
        
        if self._browser is None or not self._browser.is_connected():
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu'],
            )
        
        return self._browser
    
    async def capture_url(
        self,
        url: str,
        viewport: str = 'desktop',
        full_page: bool = False,
        wait_for_selector: Optional[str] = None,
        wait_time_ms: int = 2000,
    ) -> Dict[str, Any]:
        """
        Capture a screenshot of a URL.
        
        Args:
            url: The URL to screenshot
            viewport: Viewport size ('desktop', 'laptop', 'tablet', 'mobile')
            full_page: Whether to capture the full scrollable page
            wait_for_selector: CSS selector to wait for before screenshot
            wait_time_ms: Additional wait time after page load
            
        Returns:
            Dict with 'success', 'image_base64', 'width', 'height'
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'error': 'Playwright not installed',
                'fallback': True,
            }
        
        try:
            browser = await self._ensure_browser()
            
            # Get viewport dimensions
            vp = self.VIEWPORTS.get(viewport, self.VIEWPORTS['desktop'])
            
            # Create page with viewport
            context = await browser.new_context(
                viewport=vp,
                device_scale_factor=2,  # Retina quality
            )
            page = await context.new_page()
            
            try:
                # Navigate
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait for selector if specified
                if wait_for_selector:
                    await page.wait_for_selector(wait_for_selector, timeout=10000)
                
                # Additional wait for animations/JS
                if wait_time_ms > 0:
                    await asyncio.sleep(wait_time_ms / 1000)
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(
                    full_page=full_page,
                    type='png',
                )
                
                # Get actual dimensions
                dimensions = await page.evaluate('''() => ({
                    width: document.documentElement.scrollWidth,
                    height: document.documentElement.scrollHeight,
                })''')
                
                return {
                    'success': True,
                    'image_base64': base64.b64encode(screenshot_bytes).decode('utf-8'),
                    'width': dimensions['width'],
                    'height': dimensions['height'],
                    'viewport': viewport,
                    'url': url,
                }
                
            finally:
                await context.close()
                
        except Exception as e:
            logger.exception(f"[Screenshot] Failed to capture {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }
    
    async def capture_html(
        self,
        html_content: str,
        css_content: Optional[str] = None,
        js_content: Optional[str] = None,
        viewport: str = 'desktop',
        full_page: bool = False,
    ) -> Dict[str, Any]:
        """
        Capture a screenshot of raw HTML content.
        
        Args:
            html_content: HTML to render
            css_content: Optional CSS to inject
            js_content: Optional JS to inject
            viewport: Viewport size
            full_page: Whether to capture full page
            
        Returns:
            Dict with 'success', 'image_base64', etc.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'error': 'Playwright not installed',
            }
        
        try:
            browser = await self._ensure_browser()
            vp = self.VIEWPORTS.get(viewport, self.VIEWPORTS['desktop'])
            
            context = await browser.new_context(
                viewport=vp,
                device_scale_factor=2,
            )
            page = await context.new_page()
            
            try:
                # Inject CSS and JS into HTML if provided
                full_html = html_content
                
                if css_content and '<style>' not in full_html:
                    full_html = full_html.replace('</head>', f'<style>{css_content}</style></head>')
                
                if js_content and '<script>' not in full_html:
                    full_html = full_html.replace('</body>', f'<script>{js_content}</script></body>')
                
                # Set content
                await page.set_content(full_html, wait_until='networkidle')
                
                # Wait for any animations
                await asyncio.sleep(0.5)
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(
                    full_page=full_page,
                    type='png',
                )
                
                return {
                    'success': True,
                    'image_base64': base64.b64encode(screenshot_bytes).decode('utf-8'),
                    'viewport': viewport,
                }
                
            finally:
                await context.close()
                
        except Exception as e:
            logger.exception(f"[Screenshot] Failed to capture HTML: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    async def capture_multi_viewport(
        self,
        url: str,
        viewports: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Capture screenshots at multiple viewport sizes.
        
        Args:
            url: The URL to screenshot
            viewports: List of viewport names (defaults to all)
            
        Returns:
            Dict with viewport -> screenshot result
        """
        viewports = viewports or list(self.VIEWPORTS.keys())
        
        results = {}
        for vp in viewports:
            results[vp] = await self.capture_url(url, viewport=vp)
        
        return {
            'success': all(r.get('success') for r in results.values()),
            'screenshots': results,
        }
    
    async def generate_pdf(
        self,
        url: str,
        format: str = 'A4',
    ) -> Dict[str, Any]:
        """Generate a PDF of the page."""
        if not PLAYWRIGHT_AVAILABLE:
            return {'success': False, 'error': 'Playwright not installed'}
        
        try:
            browser = await self._ensure_browser()
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='networkidle')
                await asyncio.sleep(1)
                
                pdf_bytes = await page.pdf(
                    format=format,
                    print_background=True,
                )
                
                return {
                    'success': True,
                    'pdf_base64': base64.b64encode(pdf_bytes).decode('utf-8'),
                    'format': format,
                }
                
            finally:
                await context.close()
                
        except Exception as e:
            logger.exception(f"[Screenshot] PDF generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def close(self):
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# Singleton instance
screenshot_service = ScreenshotService()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def capture_project_screenshots(
    project_id: int,
    preview_url: str,
    viewports: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Capture screenshots for a Faz Code project.
    
    Saves screenshots to the faz_project_artifacts table.
    """
    from app.database import db
    import json
    
    viewports = viewports or ['desktop', 'mobile']
    
    results = await screenshot_service.capture_multi_viewport(preview_url, viewports)
    
    if results.get('success'):
        # Store each screenshot as an artifact
        for vp, screenshot in results.get('screenshots', {}).items():
            if screenshot.get('success'):
                await db.execute(
                    """INSERT INTO faz_project_artifacts
                       (project_id, artifact_type, content, generated_by, created_at)
                       VALUES ($1, $2, $3, $4, NOW())""",
                    project_id,
                    f'screenshot_{vp}',
                    json.dumps({
                        'viewport': vp,
                        'image_base64': screenshot.get('image_base64'),
                        'width': screenshot.get('width'),
                        'height': screenshot.get('height'),
                    }),
                    'qa_agent',
                )
        
        logger.info(f"[Screenshot] Captured {len(viewports)} screenshots for project {project_id}")
    
    return results


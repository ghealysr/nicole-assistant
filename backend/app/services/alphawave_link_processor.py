"""
Link/URL Processor for Nicole V7.
Extracts and processes content from URLs sent in chat.

Features:
- Automatic URL detection in messages
- Web page content extraction
- Article/content summarization
- Integration with document intelligence
"""

import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import httpx

from app.services.alphawave_document_service import document_service
from app.integrations.alphawave_claude import claude_client

logger = logging.getLogger(__name__)


# URL patterns to detect
URL_PATTERN = re.compile(
    r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?',
    re.IGNORECASE
)

# Domains to skip (social media profiles, etc. that don't have good content)
SKIP_DOMAINS = {
    "twitter.com", "x.com",  # Requires auth
    "facebook.com", "fb.com",  # Requires auth
    "instagram.com",  # Requires auth
    "linkedin.com",  # Requires auth
    "tiktok.com",  # Video content
    "youtube.com", "youtu.be",  # Video content (handle separately)
}


class AlphawaveLinkProcessor:
    """
    Service for processing URLs/links in chat messages.
    
    Detects URLs, fetches content, and creates document records.
    """
    
    def __init__(self):
        """Initialize link processor."""
        pass
    
    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text message.
        
        Args:
            text: Message text
            
        Returns:
            List of extracted URLs
        """
        urls = URL_PATTERN.findall(text)
        
        # Filter out skipped domains and clean URLs
        valid_urls = []
        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                
                # Remove www. prefix for comparison
                if domain.startswith("www."):
                    domain = domain[4:]
                
                # Skip certain domains
                if domain in SKIP_DOMAINS:
                    continue
                
                # Clean URL (remove trailing punctuation)
                clean_url = url.rstrip(".,;:!?)")
                valid_urls.append(clean_url)
                
            except Exception:
                continue
        
        return valid_urls
    
    async def process_urls_in_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        tiger_user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process all URLs found in a message.
        
        Args:
            user_id: User UUID string
            message: Chat message text
            conversation_id: Associated conversation
            
        Returns:
            List of processing results for each URL
        """
        urls = self.extract_urls(message)
        
        if not urls:
            return []
        
        logger.info(f"[LINK] Found {len(urls)} URLs in message")
        
        results = []
        for url in urls[:3]:  # Limit to 3 URLs per message
            try:
                result = await document_service.process_url(
                    user_id=user_id,
                    url=url,
                    conversation_id=conversation_id,
                    tiger_user_id=tiger_user_id,
                )
                results.append(result)
                
                logger.info(
                    f"[LINK] Processed {url[:50]}... -> "
                    f"status={result.get('status')}"
                )
                
            except Exception as e:
                logger.error(f"[LINK] Failed to process {url}: {e}")
                results.append({
                    "url": url,
                    "error": str(e),
                    "status": "failed",
                })
        
        return results
    
    async def get_url_summary(
        self,
        url: str,
        max_length: int = 500,
    ) -> Optional[str]:
        """
        Get a quick summary of a URL without full processing.
        
        Useful for providing context in chat without storing.
        
        Args:
            url: URL to summarize
            max_length: Maximum summary length
            
        Returns:
            Summary string or None if failed
        """
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
            ) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; NicoleBot/1.0)"
                    },
                )
                response.raise_for_status()
                
                content = response.text
                
                # Extract title
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else ""
                
                # Simple text extraction
                # Remove scripts and styles
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
                
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', content)
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Truncate
                if len(text) > 3000:
                    text = text[:3000]
                
                # Use Claude for quick summary
                prompt = f"""Summarize this web page content in 2-3 sentences:

Title: {title}

Content:
{text}

Provide a brief, informative summary."""

                summary = await claude_client.generate_response(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.3,
                )
                
                return summary[:max_length] if summary else None
                
        except Exception as e:
            logger.warning(f"[LINK] Quick summary failed for {url}: {e}")
            return None
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return domain in ("youtube.com", "www.youtube.com", "youtu.be")
        except Exception:
            return False
    
    def extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        try:
            parsed = urlparse(url)
            
            if "youtu.be" in parsed.netloc:
                return parsed.path.lstrip("/")
            
            if "youtube.com" in parsed.netloc:
                # Handle /watch?v=VIDEO_ID format
                if "v=" in url:
                    return url.split("v=")[1].split("&")[0]
            
            return None
        except Exception:
            return None


# Global instance
link_processor = AlphawaveLinkProcessor()


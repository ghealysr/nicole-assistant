"""
Nicole V7 Research Service

Orchestrates research requests using Gemini 3 Pro with:
- Google Search grounding (FREE until Jan 2026)
- Claude synthesis for Nicole's voice
- Result storage and retrieval
- Cost tracking

This service bridges Gemini's research capabilities with Nicole's personality.
"""

import logging
import json
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from app.database import db
from app.integrations.alphawave_gemini import gemini_client, ResearchType
from app.integrations.alphawave_claude import claude_client
from app.services.alphawave_cloudinary_service import cloudinary_service
from app.services.alphawave_memory_service import memory_service

logger = logging.getLogger(__name__)


class ResearchStatus(str, Enum):
    """Research request status."""
    PENDING = "pending"
    RESEARCHING = "researching"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ResearchStatusUpdate:
    """Status update for streaming."""
    status: ResearchStatus
    message: str
    progress: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class ResearchResult:
    """Final research result."""
    request_id: int
    query: str
    research_type: str
    executive_summary: str
    findings: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    recommendations: List[str]
    nicole_synthesis: str
    cost_usd: Decimal
    elapsed_seconds: float


class ResearchOrchestrator:
    """
    Nicole's research orchestration layer.
    
    Flow:
    1. Receive research request from chat
    2. Execute via Gemini 3 Pro with search grounding
    3. Synthesize results with Claude (Nicole's voice)
    4. Store results in database
    5. Return formatted response
    """
    
    # Research trigger patterns
    RESEARCH_TRIGGERS = [
        r"research\s+(.*)",
        r"find\s+(?:me\s+)?(?:information|data|examples)\s+(?:about|on)\s+(.*)",
        r"what's\s+(?:the\s+)?latest\s+(?:on|about)\s+(.*)",
        r"deep\s+dive\s+(?:into|on)\s+(.*)",
        r"analyze\s+(.*)",
        r"compare\s+(.*)",
        r"investigate\s+(.*)"
    ]
    
    # Vibe-specific triggers
    VIBE_TRIGGERS = [
        r"find\s+(?:me\s+)?(?:website|design|ui|ux)\s+inspiration\s+(?:for\s+)?(.*)",
        r"show\s+me\s+(?:examples|designs)\s+(?:like|similar\s+to)\s+(.*)",
        r"what\s+(?:do|does)\s+(.*)\s+(?:websites?|designs?)\s+look\s+like"
    ]
    
    def __init__(self):
        """Initialize research orchestrator."""
        self.gemini = gemini_client
        self.claude = claude_client
    
    def detect_research_intent(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Detect if a message is a research request.
        
        Returns:
            Dict with research_type and query, or None
        """
        import re
        
        message_lower = message.lower()
        
        # Check Vibe triggers first (more specific)
        for pattern in self.VIBE_TRIGGERS:
            match = re.search(pattern, message_lower)
            if match:
                return {
                    "research_type": ResearchType.VIBE_INSPIRATION,
                    "query": match.group(1) if match.groups() else message
                }
        
        # Check general triggers
        for pattern in self.RESEARCH_TRIGGERS:
            match = re.search(pattern, message_lower)
            if match:
                return {
                    "research_type": ResearchType.GENERAL,
                    "query": match.group(1) if match.groups() else message
                }
        
        return None
    
    async def execute_research(
        self,
        query: str,
        research_type: ResearchType = ResearchType.GENERAL,
        user_id: int = 0,
        project_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[ResearchStatusUpdate]:
        """
        Execute research with status updates.
        
        Yields status updates for frontend display.
        """
        request_id = None
        
        try:
            # 1. Store request
            yield ResearchStatusUpdate(
                status=ResearchStatus.PENDING,
                message="Starting research...",
                progress=0
            )
            
            request_id = await self._store_request(
                query=query,
                research_type=research_type,
                user_id=user_id,
                project_id=project_id,
                context=context
            )
            
            # 2. Execute Gemini research
            yield ResearchStatusUpdate(
                status=ResearchStatus.RESEARCHING,
                message="Searching across multiple sources...",
                progress=20
            )
            
            gemini_result = await self.gemini.deep_research(
                query=query,
                research_type=research_type,
                context=context,
                enable_thinking=True
            )
            
            if not gemini_result.get("success"):
                yield ResearchStatusUpdate(
                    status=ResearchStatus.FAILED,
                    message=f"Research failed: {gemini_result.get('error', 'Unknown error')}",
                    data=gemini_result
                )
                return
            
            # 3. Store raw results
            await self._store_raw_results(request_id, gemini_result)
            
            yield ResearchStatusUpdate(
                status=ResearchStatus.SYNTHESIZING,
                message="Analyzing findings...",
                progress=60
            )
            
            # 4. Synthesize with Claude (Nicole's voice)
            synthesis = await self._synthesize_with_nicole(
                query=query,
                raw_results=gemini_result,
                research_type=research_type
            )
            
            # 5. Capture screenshots of top sources for visual context
            yield ResearchStatusUpdate(
                status=ResearchStatus.SYNTHESIZING,
                message="Capturing screenshots of key sources...",
                progress=80
            )
            sources = gemini_result.get("sources", [])
            logger.info(f"[RESEARCH] Found {len(sources)} sources from Gemini for request {request_id}")
            screenshots = await self._capture_screenshots(
                sources=sources,
                request_id=request_id,
                max_screenshots=3  # Capture top 3 sources
            )
            logger.info(f"[RESEARCH] Captured {len(screenshots)} screenshots for request {request_id}")
            
            # 6. Store final report with screenshots
            await self._store_report(request_id, gemini_result, synthesis, screenshots)
            
            # 7. Update request status
            await self._update_request_status(request_id, ResearchStatus.COMPLETE)
            
            # 8. Save research findings to Nicole's memory for future reference
            await self._save_to_memory(
                user_id=user_id,
                query=query,
                synthesis=synthesis,
                research_type=research_type,
                request_id=request_id
            )
            
            # Build response matching frontend ResearchResponse interface
            research_type_str = research_type.value if hasattr(research_type, 'value') else str(research_type)
            gemini_metadata = gemini_result.get("metadata", {})
            
            # Extract structured synthesis data (now returns dict)
            synthesis_data = synthesis if isinstance(synthesis, dict) else {}
            
            # Build images array for frontend
            images = []
            hero_image = None
            if screenshots and len(screenshots) > 0:
                hero_image = screenshots[0].get("url")
                images = [{
                    "url": s["url"],
                    "caption": s.get("caption", ""),
                    "source": s.get("source_url", ""),
                    "type": "screenshot"
                } for s in screenshots]
            
            yield ResearchStatusUpdate(
                status=ResearchStatus.COMPLETE,
                message="Research complete!",
                progress=100,
                data={
                    "request_id": request_id,
                    "query": query,
                    "research_type": research_type_str,
                    # Use Nicole's custom title, fallback to generated one
                    "article_title": synthesis_data.get("article_title", "Research Findings"),
                    "subtitle": synthesis_data.get("subtitle", ""),
                    # Lead paragraph as executive summary
                    "executive_summary": synthesis_data.get("lead_paragraph", gemini_result.get("results", {}).get("executive_summary", "")),
                    # Use synthesis findings if available, else raw
                    "findings": synthesis_data.get("key_findings", gemini_result.get("results", {}).get("key_findings", [])),
                    "sources": gemini_result.get("sources", []),
                    # Use synthesis recommendations if available
                    "recommendations": synthesis_data.get("recommendations", gemini_result.get("results", {}).get("recommendations", [])),
                    # Full article body
                    "nicole_synthesis": synthesis_data.get("body", str(synthesis) if not isinstance(synthesis, dict) else ""),
                    "bottom_line": synthesis_data.get("bottom_line", ""),
                    # Image data
                    "hero_image": hero_image,
                    "images": images,
                    "screenshots": screenshots or [],
                    "completed_at": datetime.now().isoformat(),
                    "metadata": {
                        "model": gemini_metadata.get("model", "gemini-3-pro-preview"),
                        "input_tokens": gemini_metadata.get("input_tokens", 0),
                        "output_tokens": gemini_metadata.get("output_tokens", 0),
                        "cost_usd": gemini_metadata.get("cost_usd", 0.0),
                        "elapsed_seconds": gemini_metadata.get("elapsed_seconds", 0.0),
                        "timestamp": datetime.now().isoformat(),
                        "screenshot_count": len(screenshots) if screenshots else 0
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"[RESEARCH] Execution failed: {e}", exc_info=True)
            if request_id:
                await self._update_request_status(request_id, ResearchStatus.FAILED)
            
            yield ResearchStatusUpdate(
                status=ResearchStatus.FAILED,
                message=f"Research failed: {str(e)}"
            )
    
    async def _synthesize_with_nicole(
        self,
        query: str,
        raw_results: Dict[str, Any],
        research_type: ResearchType
    ) -> str:
        """
        Use Claude to synthesize results as a professional journalist.
        
        Nicole transforms raw research into magazine-quality articles.
        """
        research_type_str = research_type.value if hasattr(research_type, 'value') else str(research_type)
        
        synthesis_prompt = f"""You are Nicole, a world-class research journalist and analyst working for Glen at AlphaWave. 
You combine the investigative rigor of The New Yorker, the clarity of The Economist, and the actionable insights of Harvard Business Review.

Your task: Transform this raw research data into a professional magazine-quality article.

## RAW RESEARCH DATA:
{json.dumps(raw_results.get('results', {}), indent=2, default=str)}

## ORIGINAL QUERY:
{query}

## RESEARCH TYPE:
{research_type_str}

## YOUR DELIVERABLE - RESPOND IN THIS EXACT JSON FORMAT:
{{
    "article_title": "A compelling, journalist-crafted headline (NOT the user's query - create something engaging)",
    "subtitle": "A brief subheading that captures the key insight",
    "lead_paragraph": "The opening paragraph that hooks the reader and summarizes the key finding",
    "body": "2-4 paragraphs of well-structured prose. Use clear topic sentences. Include specific examples and data points. Write like a senior journalist at The New Yorker.",
    "key_findings": [
        "• Finding 1: Specific, actionable insight with evidence",
        "• Finding 2: Another key discovery with supporting detail",
        "• Finding 3: Third major finding (3-5 total)"
    ],
    "recommendations": [
        "→ Recommendation 1: Specific action Glen should take",
        "→ Recommendation 2: Next step with rationale"
    ],
    "bottom_line": "One powerful concluding sentence that answers Glen's original question directly"
}}

## WRITING GUIDELINES:
- Create a CUSTOM TITLE - do NOT use the user's query as the headline
- Write in Nicole's voice: warm but professional, direct but thorough
- Focus on answering Glen's actual questions - what did he really want to know?
- Include specific names, numbers, and facts from the research
- Use bullet points (•) for findings and arrows (→) for recommendations
- Be concise - quality over quantity
- If for Vibe project: focus on actionable design/business insights
- Reference sources naturally within the text

Respond ONLY with valid JSON, no markdown code blocks."""

        try:
            response = await self.claude.generate_response(
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=2000
            )
            
            # Parse JSON response
            try:
                # Clean potential markdown code blocks
                clean_response = response.strip()
                if clean_response.startswith("```"):
                    clean_response = clean_response.split("```")[1]
                    if clean_response.startswith("json"):
                        clean_response = clean_response[4:]
                
                synthesis_data = json.loads(clean_response)
                return synthesis_data
            except json.JSONDecodeError:
                logger.warning("[RESEARCH] Could not parse synthesis as JSON, using raw response")
                # Return structured fallback
                return {
                    "article_title": "Research Findings",
                    "subtitle": query[:100],
                    "lead_paragraph": response[:500] if len(response) > 500 else response,
                    "body": response,
                    "key_findings": [],
                    "recommendations": [],
                    "bottom_line": ""
                }
                
        except Exception as e:
            logger.warning(f"[RESEARCH] Claude synthesis failed: {e}")
            # Fallback with structured data
            return {
                "article_title": "Research Complete",
                "subtitle": query[:100],
                "lead_paragraph": raw_results.get("results", {}).get("executive_summary", "Research complete."),
                "body": raw_results.get("results", {}).get("executive_summary", ""),
                "key_findings": raw_results.get("results", {}).get("key_findings", []),
                "recommendations": raw_results.get("results", {}).get("recommendations", []),
                "bottom_line": "See findings above for details."
            }
    
    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================
    
    async def _store_request(
        self,
        query: str,
        research_type: ResearchType,
        user_id: int,
        project_id: Optional[int],
        context: Optional[Dict[str, Any]]
    ) -> int:
        """Store research request in database."""
        try:
            # Handle both enum and string research_type
            research_type_str = research_type.value if hasattr(research_type, 'value') else str(research_type)
            
            row = await db.fetchrow(
                """
                INSERT INTO research_requests (
                    type, query, context, constraints, status, project_id, user_id, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                RETURNING id
                """,
                research_type_str,
                query,
                json.dumps(context or {}),
                json.dumps({}),
                ResearchStatus.PENDING.value,
                project_id,
                user_id if user_id else None
            )
            return row["id"] if row else 0
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to store request: {e}")
            return 0
    
    async def _store_raw_results(self, request_id: int, results: Dict[str, Any]) -> None:
        """Store raw Gemini results."""
        if not request_id:
            return
        
        try:
            await db.execute(
                """
                INSERT INTO research_results (
                    request_id, raw_gemini_output, sources, created_at
                ) VALUES ($1, $2, $3, NOW())
                """,
                request_id,
                json.dumps(results, default=str),
                json.dumps(results.get("sources", []))
            )
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to store raw results: {e}")
    
    async def _capture_screenshots(
        self,
        sources: List[Dict[str, Any]],
        request_id: int,
        max_screenshots: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Capture screenshots of top research sources for visual context.
        
        Flow:
        1. Select top sources (up to max_screenshots)
        2. Try Docker MCP Gateway Puppeteer
        3. Fall back to legacy Playwright MCP
        4. Upload to Cloudinary
        5. Return array of screenshot objects
        
        Returns:
            List of dicts: [{"url": cloudinary_url, "source_url": original_url, "caption": source_title}]
        """
        screenshots = []
        
        logger.info(f"[RESEARCH] _capture_screenshots called with {len(sources)} total sources for request {request_id}")
        
        # Select top sources to screenshot (prioritize those with URLs)
        sources_to_capture = [s for s in sources if s.get("url")][:max_screenshots]
        
        if not sources_to_capture:
            logger.warning(f"[RESEARCH] No sources with URLs available for screenshots (total sources: {len(sources)})")
            logger.warning(f"[RESEARCH] Source sample: {sources[:2] if sources else 'empty'}")
            return screenshots
        
        logger.info(f"[RESEARCH] Capturing {len(sources_to_capture)} screenshots for request {request_id}")
        logger.info(f"[RESEARCH] URLs to capture: {[s.get('url', 'N/A')[:60] for s in sources_to_capture]}")
        
        for source in sources_to_capture:
            try:
                url = source.get("url", "")
                title = source.get("title", url)
                
                if not url:
                    continue
                
                # Try Docker MCP Gateway first (Puppeteer)
                base64_data = None
                try:
                    from app.mcp.docker_mcp_client import get_mcp_client
                    mcp = await get_mcp_client()
                    
                    if mcp.is_connected:
                        tools = await mcp.list_tools()
                        puppeteer_tools = [t for t in tools if "puppeteer" in t.name.lower()]
                        
                        if puppeteer_tools:
                            # Navigate and screenshot
                            nav_result = await mcp.call_tool("puppeteer_navigate", {"url": url})
                            if not nav_result.is_error:
                                screenshot_result = await mcp.call_tool("puppeteer_screenshot", {})
                                
                                if not screenshot_result.is_error and screenshot_result.content:
                                    content = screenshot_result.content
                                    if isinstance(content, str):
                                        try:
                                            data = json.loads(content)
                                            base64_data = data.get("data") or data.get("screenshot")
                                        except:
                                            if len(content) > 100 and "," not in content[:50]:
                                                base64_data = content
                                    logger.info(f"[RESEARCH] Screenshot captured via Docker MCP Gateway: {url}")
                except Exception as e:
                    logger.warning(f"[RESEARCH] Docker MCP screenshot failed for {url}: {e}")
                
                # Upload to Cloudinary if we got base64 data
                if base64_data:
                    try:
                        cloudinary_url = await cloudinary_service.upload_screenshot(
                            base64_image=base64_data,
                            folder=f"research/{request_id}",
                            public_id=f"source_{len(screenshots) + 1}",
                            context={"url": url, "title": title}
                        )
                        
                        if cloudinary_url:
                            screenshots.append({
                                "url": cloudinary_url,
                                "source_url": url,
                                "caption": title,
                                "captured_at": datetime.now().isoformat()
                            })
                            logger.info(f"[RESEARCH] Screenshot uploaded to Cloudinary: {cloudinary_url}")
                    except Exception as e:
                        logger.error(f"[RESEARCH] Failed to upload screenshot to Cloudinary: {e}")
                
            except Exception as e:
                logger.error(f"[RESEARCH] Screenshot capture failed for {source.get('url')}: {e}")
                continue
        
        logger.info(f"[RESEARCH] Successfully captured {len(screenshots)} screenshots")
        return screenshots
    
    async def _store_report(
        self,
        request_id: int,
        results: Dict[str, Any],
        synthesis: Any,
        screenshots: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Store synthesized report with all structured fields for template rendering.
        
        Fields stored:
        - article_title: Journalist-crafted headline
        - subtitle: Brief subheading
        - lead_paragraph: Opening hook paragraph
        - body: Full article prose
        - bottom_line: Powerful concluding sentence
        - executive_summary: Gemini's raw summary (fallback)
        - findings: Key findings array
        - recommendations: Actionable recommendations
        - hero_image_url: Primary hero image (first screenshot)
        - images: Array of image objects
        - screenshots: Array of screenshot objects with source URLs
        """
        if not request_id:
            return
        
        try:
            parsed = results.get("results", {})
            
            # Extract structured fields from synthesis (dict or string)
            if isinstance(synthesis, dict):
                article_title = synthesis.get("article_title", "")
                subtitle = synthesis.get("subtitle", "")
                lead_paragraph = synthesis.get("lead_paragraph", "")
                body = synthesis.get("body", "")
                bottom_line = synthesis.get("bottom_line", "")
                key_findings = synthesis.get("key_findings", [])
                recommendations = synthesis.get("recommendations", [])
                # Legacy field for backwards compatibility
                nicole_synthesis = json.dumps(synthesis)
            else:
                # Fallback for string synthesis
                article_title = ""
                subtitle = ""
                lead_paragraph = ""
                body = str(synthesis)
                bottom_line = ""
                key_findings = parsed.get("key_findings", [])
                recommendations = parsed.get("recommendations", [])
                nicole_synthesis = str(synthesis)
            
            # Use Gemini's executive_summary as fallback if no lead_paragraph
            executive_summary = parsed.get("executive_summary", "") or lead_paragraph
            
            # Prepare image data
            hero_image_url = None
            images = []
            screenshots_json = []
            
            if screenshots and len(screenshots) > 0:
                # Use first screenshot as hero image
                hero_image_url = screenshots[0].get("url")
                # Store all screenshots
                screenshots_json = screenshots
                # Also add to images array for template flexibility
                images = [{
                    "url": s["url"],
                    "caption": s.get("caption", ""),
                    "source": s.get("source_url", ""),
                    "type": "screenshot"
                } for s in screenshots]
            
            # CRITICAL: Pass Python lists directly to asyncpg for JSONB columns
            # Do NOT use json.dumps() or it will store as TEXT instead of JSONB
            await db.execute(
                """
                INSERT INTO research_reports (
                    request_id, article_title, subtitle, lead_paragraph, body, bottom_line,
                    executive_summary, findings, recommendations, nicole_synthesis,
                    hero_image_url, images, screenshots, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13::jsonb, NOW())
                ON CONFLICT (request_id) DO UPDATE SET
                    article_title = EXCLUDED.article_title,
                    subtitle = EXCLUDED.subtitle,
                    lead_paragraph = EXCLUDED.lead_paragraph,
                    body = EXCLUDED.body,
                    bottom_line = EXCLUDED.bottom_line,
                    executive_summary = EXCLUDED.executive_summary,
                    findings = EXCLUDED.findings,
                    recommendations = EXCLUDED.recommendations,
                    nicole_synthesis = EXCLUDED.nicole_synthesis,
                    hero_image_url = EXCLUDED.hero_image_url,
                    images = EXCLUDED.images,
                    screenshots = EXCLUDED.screenshots
                """,
                request_id,
                article_title,
                subtitle,
                lead_paragraph,
                body,
                bottom_line,
                executive_summary,
                json.dumps(key_findings),
                json.dumps(recommendations),
                nicole_synthesis,
                hero_image_url,
                images,  # Pass Python list directly, not json.dumps()
                screenshots_json  # Pass Python list directly, not json.dumps()
            )
            
            image_count = len(screenshots) if screenshots else 0
            logger.info(f"[RESEARCH] Stored report for request {request_id} with title: {article_title[:50]}... ({image_count} images)")
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to store report: {e}", exc_info=True)
    
    async def _update_request_status(self, request_id: int, status: ResearchStatus) -> None:
        """Update request status."""
        if not request_id:
            return
        
        try:
            status_str = status.value if hasattr(status, 'value') else str(status)
            await db.execute(
                """
                UPDATE research_requests 
                SET status = $1::VARCHAR, completed_at = CASE WHEN $1 IN ('complete', 'failed') THEN NOW() ELSE completed_at END
                WHERE id = $2
                """,
                status_str,
                request_id
            )
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to update status: {e}")
    
    async def _save_to_memory(
        self,
        user_id: int,
        query: str,
        synthesis: dict,
        research_type: ResearchType,
        request_id: int
    ) -> None:
        """
        Save research findings to Nicole's memory system.
        
        This ensures Nicole remembers research she's done and can reference it
        in future conversations without the user needing to re-research.
        """
        if not user_id or user_id == 0:
            logger.info("[RESEARCH] Skipping memory save - no user_id")
            return
        
        try:
            research_type_str = research_type.value if hasattr(research_type, 'value') else str(research_type)
            
            # Build comprehensive memory content
            title = synthesis.get("article_title", "Research Findings")
            bottom_line = synthesis.get("bottom_line", "")
            lead = synthesis.get("lead_paragraph", "")
            findings = synthesis.get("key_findings", [])
            
            # Create a concise but informative memory entry
            findings_text = "\n".join([f"- {f}" for f in findings[:5]]) if findings else ""
            
            memory_content = f"""Research on "{query}":

{title}

{lead}

Key Findings:
{findings_text}

Bottom Line: {bottom_line}

[Research ID: {request_id} | Type: {research_type_str}]"""

            # Save to memory with high importance (research is valuable)
            await memory_service.save_memory(
                user_id=user_id,
                memory_type="fact",  # Research findings are factual knowledge
                content=memory_content,
                context="research",
                importance=0.8,  # High importance - research is valuable
                source="nicole",  # Nicole conducted the research
                is_shared=False,
            )
            
            logger.info(f"[RESEARCH] Saved research to memory for user {user_id}: {query[:50]}...")
            
        except Exception as e:
            # Don't fail the research if memory save fails
            logger.error(f"[RESEARCH] Failed to save to memory: {e}")
    
    async def get_research(self, request_id: int) -> Optional[Dict[str, Any]]:
        """
        Get research results by ID with all structured fields for template rendering.
        
        Returns complete research data including:
        - article_title, subtitle, lead_paragraph, body, bottom_line (template fields)
        - findings, recommendations (structured data)
        - sources (from Gemini research)
        - metadata (query, type, timestamps)
        """
        try:
            row = await db.fetchrow(
                """
                SELECT 
                    rr.id, rr.type, rr.query, rr.status, rr.created_at, rr.completed_at,
                    rep.article_title, rep.subtitle, rep.lead_paragraph, rep.body, rep.bottom_line,
                    rep.executive_summary, rep.findings, rep.recommendations, rep.nicole_synthesis,
                    rep.hero_image_url, rep.images, rep.screenshots,
                    res.raw_gemini_output, res.sources
                FROM research_requests rr
                LEFT JOIN research_reports rep ON rep.request_id = rr.id
                LEFT JOIN research_results res ON res.request_id = rr.id
                WHERE rr.id = $1
                """,
                request_id
            )
            
            if not row:
                return None
            
            # Parse sources from various possible locations
            sources = []
            if row["sources"]:
                try:
                    sources = json.loads(row["sources"]) if isinstance(row["sources"], str) else row["sources"]
                except:
                    sources = []
            
            # Parse findings - could be string or already parsed
            findings = []
            if row["findings"]:
                try:
                    findings = json.loads(row["findings"]) if isinstance(row["findings"], str) else row["findings"]
                except:
                    findings = []
            
            # Parse recommendations
            recommendations = []
            if row["recommendations"]:
                try:
                    recommendations = json.loads(row["recommendations"]) if isinstance(row["recommendations"], str) else row["recommendations"]
                except:
                    recommendations = []
            
            # Parse images
            images = []
            if row.get("images"):
                try:
                    images = json.loads(row["images"]) if isinstance(row["images"], str) else row["images"]
                except:
                    images = []
            
            # Parse screenshots
            screenshots = []
            if row.get("screenshots"):
                try:
                    screenshots = json.loads(row["screenshots"]) if isinstance(row["screenshots"], str) else row["screenshots"]
                except:
                    screenshots = []
            
            return {
                # Request metadata
                "request_id": row["id"],
                "research_type": row["type"],
                "query": row["query"],
                "status": row["status"],
                
                # Template fields - structured content from Claude synthesis
                "article_title": row["article_title"] or "",
                "subtitle": row["subtitle"] or "",
                "lead_paragraph": row["lead_paragraph"] or "",
                "body": row["body"] or "",
                "bottom_line": row["bottom_line"] or "",
                
                # Legacy/fallback fields
                "executive_summary": row["executive_summary"] or row["lead_paragraph"] or "",
                "nicole_synthesis": row["nicole_synthesis"] or row["body"] or "",
                
                # Structured data
                "findings": findings,
                "recommendations": recommendations,
                "sources": sources,
                
                # Image data
                "hero_image": row.get("hero_image_url") or "",
                "images": images,
                "screenshots": screenshots,
                
                # Metadata for templates
                "metadata": {
                    "model": "gemini-2.5-pro",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "elapsed_seconds": 0.0,
                    "timestamp": row["completed_at"].isoformat() if row["completed_at"] else None,
                    "screenshot_count": len(screenshots)
                },
                
                # Timestamps
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None
            }
            
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to get research: {e}", exc_info=True)
            return None


# Singleton instance
research_orchestrator = ResearchOrchestrator()


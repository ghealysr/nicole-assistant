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
            
            # 5. Store final report
            await self._store_report(request_id, gemini_result, synthesis)
            
            # 6. Update request status
            await self._update_request_status(request_id, ResearchStatus.COMPLETE)
            
            # Build response matching frontend ResearchResponse interface
            research_type_str = research_type.value if hasattr(research_type, 'value') else str(research_type)
            gemini_metadata = gemini_result.get("metadata", {})
            
            # Extract structured synthesis data (now returns dict)
            synthesis_data = synthesis if isinstance(synthesis, dict) else {}
            
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
                    "completed_at": datetime.now().isoformat(),
                    "metadata": {
                        "model": gemini_metadata.get("model", "gemini-3-pro-preview"),
                        "input_tokens": gemini_metadata.get("input_tokens", 0),
                        "output_tokens": gemini_metadata.get("output_tokens", 0),
                        "cost_usd": gemini_metadata.get("cost_usd", 0.0),
                        "elapsed_seconds": gemini_metadata.get("elapsed_seconds", 0.0),
                        "timestamp": datetime.now().isoformat()
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
    
    async def _store_report(
        self,
        request_id: int,
        results: Dict[str, Any],
        synthesis: str
    ) -> None:
        """Store synthesized report."""
        if not request_id:
            return
        
        try:
            parsed = results.get("results", {})
            await db.execute(
                """
                INSERT INTO research_reports (
                    request_id, title, executive_summary, findings, 
                    recommendations, artifact_html, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                request_id,
                f"Research: {results.get('query', '')[:100]}",
                parsed.get("executive_summary", ""),
                json.dumps(parsed.get("key_findings", [])),
                json.dumps(parsed.get("recommendations", [])),
                synthesis  # Nicole's synthesis as the artifact
            )
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to store report: {e}")
    
    async def _update_request_status(self, request_id: int, status: ResearchStatus) -> None:
        """Update request status."""
        if not request_id:
            return
        
        try:
            await db.execute(
                """
                UPDATE research_requests 
                SET status = $1, completed_at = CASE WHEN $1 IN ('complete', 'failed') THEN NOW() ELSE NULL END
                WHERE id = $2
                """,
                status.value,
                request_id
            )
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to update status: {e}")
    
    async def get_research(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Get research results by ID."""
        try:
            row = await db.fetchrow(
                """
                SELECT 
                    rr.id, rr.type, rr.query, rr.status, rr.created_at, rr.completed_at,
                    rep.executive_summary, rep.findings, rep.recommendations, rep.artifact_html,
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
            
            return {
                "id": row["id"],
                "type": row["type"],
                "query": row["query"],
                "status": row["status"],
                "executive_summary": row["executive_summary"],
                "findings": json.loads(row["findings"]) if row["findings"] else [],
                "recommendations": json.loads(row["recommendations"]) if row["recommendations"] else [],
                "nicole_synthesis": row["artifact_html"],
                "sources": json.loads(row["sources"]) if row["sources"] else [],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None
            }
            
        except Exception as e:
            logger.error(f"[RESEARCH] Failed to get research: {e}")
            return None


# Singleton instance
research_orchestrator = ResearchOrchestrator()


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
            
            yield ResearchStatusUpdate(
                status=ResearchStatus.COMPLETE,
                message="Research complete!",
                progress=100,
                data={
                    "request_id": request_id,
                    "query": query,
                    "executive_summary": gemini_result.get("results", {}).get("executive_summary", ""),
                    "findings": gemini_result.get("results", {}).get("key_findings", []),
                    "sources": gemini_result.get("sources", []),
                    "recommendations": gemini_result.get("results", {}).get("recommendations", []),
                    "nicole_synthesis": synthesis,
                    "metadata": gemini_result.get("metadata", {})
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
        Use Claude to synthesize results in Nicole's voice.
        """
        synthesis_prompt = f"""You are Nicole, Glen's AI companion. You've just completed research on his behalf.
Present these findings in your natural voice - warm, direct, insightful.

RAW RESEARCH DATA:
{json.dumps(raw_results.get('results', {}), indent=2, default=str)}

ORIGINAL QUERY:
{query}

RESEARCH TYPE:
{research_type.value}

GUIDELINES:
- Speak as Nicole, not as a generic AI
- Highlight what Glen would care about most
- Be concise but thorough
- If this is for a Vibe project, focus on actionable design insights
- Include your own analysis and recommendations
- Reference specific sources naturally

Provide a 2-3 paragraph synthesis that Nicole would present to Glen."""

        try:
            response = await self.claude.generate_response(
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=1000
            )
            return response
        except Exception as e:
            logger.warning(f"[RESEARCH] Claude synthesis failed: {e}")
            # Fallback to executive summary
            return raw_results.get("results", {}).get("executive_summary", "Research complete. See findings below.")
    
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
            row = await db.fetchrow(
                """
                INSERT INTO research_requests (
                    type, query, context, constraints, status, project_id, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                RETURNING id
                """,
                research_type.value,
                query,
                json.dumps(context or {}),
                json.dumps({"user_id": user_id}),
                ResearchStatus.PENDING.value,
                project_id
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
                    request_id, raw_response, sources, images, created_at
                ) VALUES ($1, $2, $3, $4, NOW())
                """,
                request_id,
                json.dumps(results, default=str),
                json.dumps(results.get("sources", [])),
                json.dumps([])  # Images captured separately
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
                    res.raw_response, res.sources
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


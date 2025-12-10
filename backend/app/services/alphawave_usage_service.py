"""
Nicole V7 Usage Tracking Service

Production-grade usage monitoring for:
- Token consumption (Claude, OpenAI)
- API cost calculation and tracking
- Storage usage monitoring
- Future cost projections

All data stored in Tiger Postgres for historical analysis.

Architecture:
1. Track → Record every API call with token counts
2. Aggregate → Calculate daily/monthly totals
3. Project → Estimate future costs based on trends
4. Alert → Flag unusual usage patterns
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.database import db
from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# COST CONSTANTS (as of Dec 2024)
# =============================================================================

# Claude API Pricing (per 1M tokens)
CLAUDE_PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
}

# OpenAI Embedding Pricing (per 1M tokens)
OPENAI_PRICING = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
    "text-embedding-ada-002": 0.10,
}

# Tiger Cloud Pricing (estimated monthly)
TIGER_PRICING = {
    "compute_per_gb_hour": 0.016,  # Per GB-hour
    "storage_per_gb_month": 0.10,  # Per GB per month
}

# Azure Document Intelligence Pricing
AZURE_PRICING = {
    "document_pages": 0.01,  # Per page
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UsageSummary:
    """Summary of usage for a time period."""
    period_start: date
    period_end: date
    
    # Token counts
    claude_input_tokens: int
    claude_output_tokens: int
    openai_embedding_tokens: int
    
    # Request counts
    claude_requests: int
    embedding_requests: int
    document_pages_processed: int
    
    # Calculated costs (USD)
    claude_cost: Decimal
    openai_cost: Decimal
    azure_cost: Decimal
    tiger_cost: Decimal
    total_cost: Decimal
    
    # Storage
    document_storage_bytes: int
    embedding_storage_bytes: int
    total_storage_bytes: int


@dataclass
class CostProjection:
    """Future cost projection based on current usage."""
    daily_average: Decimal
    monthly_estimate: Decimal
    annual_estimate: Decimal
    trend: str  # "increasing", "stable", "decreasing"
    trend_percentage: float


# =============================================================================
# USAGE TRACKING SERVICE
# =============================================================================

class AlphawaveUsageService:
    """
    Production-grade usage tracking and cost monitoring.
    
    Tracks all API calls, calculates costs, and projects future spending.
    Designed for power users who need detailed visibility into system costs.
    """
    
    def __init__(self):
        """Initialize usage service."""
        self._ensure_tables_exist_task = None
        logger.info("[USAGE] Service initialized")
    
    # =========================================================================
    # TRACKING METHODS
    # =========================================================================
    
    async def track_claude_usage(
        self,
        user_id: int,
        model: str,
        input_tokens: int,
        output_tokens: int,
        request_type: str = "chat",
        conversation_id: Optional[int] = None,
    ) -> None:
        """
        Track a Claude API call.
        
        Args:
            user_id: Tiger user ID
            model: Model used (e.g., "claude-3-5-sonnet-20241022")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            request_type: Type of request (chat, analysis, etc.)
            conversation_id: Associated conversation if any
        """
        # Calculate cost
        pricing = CLAUDE_PRICING.get(model, CLAUDE_PRICING["claude-3-5-sonnet-20241022"])
        input_cost = Decimal(str(input_tokens)) * Decimal(str(pricing["input"])) / Decimal("1000000")
        output_cost = Decimal(str(output_tokens)) * Decimal(str(pricing["output"])) / Decimal("1000000")
        total_cost = input_cost + output_cost
        
        try:
            await db.execute(
                """
                INSERT INTO api_usage_log (
                    user_id, service, model, request_type,
                    input_tokens, output_tokens, cost_usd,
                    conversation_id, created_at
                ) VALUES ($1, 'claude', $2, $3, $4, $5, $6, $7, NOW())
                """,
                user_id,
                model,
                request_type,
                input_tokens,
                output_tokens,
                float(total_cost),
                conversation_id,
            )
        except Exception as e:
            # Don't fail the main request if tracking fails
            logger.warning(f"[USAGE] Failed to track Claude usage: {e}")
    
    async def track_embedding_usage(
        self,
        user_id: int,
        model: str,
        tokens: int,
        request_type: str = "embedding",
        document_id: Optional[int] = None,
    ) -> None:
        """Track an OpenAI embedding API call."""
        pricing = OPENAI_PRICING.get(model, OPENAI_PRICING["text-embedding-3-small"])
        cost = Decimal(str(tokens)) * Decimal(str(pricing)) / Decimal("1000000")
        
        try:
            await db.execute(
                """
                INSERT INTO api_usage_log (
                    user_id, service, model, request_type,
                    input_tokens, output_tokens, cost_usd,
                    metadata, created_at
                ) VALUES ($1, 'openai', $2, $3, $4, 0, $5, $6, NOW())
                """,
                user_id,
                model,
                request_type,
                tokens,
                float(cost),
                {"document_id": document_id} if document_id else None,
            )
        except Exception as e:
            logger.warning(f"[USAGE] Failed to track embedding usage: {e}")
    
    async def track_document_processing(
        self,
        user_id: int,
        pages: int,
        file_size_bytes: int,
        document_id: int,
    ) -> None:
        """Track document processing (Azure Document Intelligence)."""
        cost = Decimal(str(pages)) * Decimal(str(AZURE_PRICING["document_pages"]))
        
        try:
            await db.execute(
                """
                INSERT INTO api_usage_log (
                    user_id, service, model, request_type,
                    input_tokens, output_tokens, cost_usd,
                    metadata, created_at
                ) VALUES ($1, 'azure', 'document-intelligence', 'document_processing',
                         $2, 0, $3, $4, NOW())
                """,
                user_id,
                pages,  # Using pages as "tokens" for document processing
                float(cost),
                {"document_id": document_id, "file_size_bytes": file_size_bytes},
            )
        except Exception as e:
            logger.warning(f"[USAGE] Failed to track document processing: {e}")
    
    # =========================================================================
    # AGGREGATION METHODS
    # =========================================================================
    
    async def get_usage_summary(
        self,
        user_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage summary for a user.
        
        Args:
            user_id: Tiger user ID
            days: Number of days to summarize (default 30)
            
        Returns:
            Complete usage summary with costs and projections
        """
        period_start = date.today() - timedelta(days=days)
        period_end = date.today()
        
        try:
            # Get aggregated usage data
            usage_row = await db.fetchrow(
                """
                SELECT
                    -- Claude usage
                    COALESCE(SUM(CASE WHEN service = 'claude' THEN input_tokens ELSE 0 END), 0) AS claude_input_tokens,
                    COALESCE(SUM(CASE WHEN service = 'claude' THEN output_tokens ELSE 0 END), 0) AS claude_output_tokens,
                    COALESCE(COUNT(CASE WHEN service = 'claude' THEN 1 END), 0) AS claude_requests,
                    COALESCE(SUM(CASE WHEN service = 'claude' THEN cost_usd ELSE 0 END), 0) AS claude_cost,
                    
                    -- OpenAI usage
                    COALESCE(SUM(CASE WHEN service = 'openai' THEN input_tokens ELSE 0 END), 0) AS openai_tokens,
                    COALESCE(COUNT(CASE WHEN service = 'openai' THEN 1 END), 0) AS embedding_requests,
                    COALESCE(SUM(CASE WHEN service = 'openai' THEN cost_usd ELSE 0 END), 0) AS openai_cost,
                    
                    -- Azure usage
                    COALESCE(SUM(CASE WHEN service = 'azure' THEN input_tokens ELSE 0 END), 0) AS document_pages,
                    COALESCE(SUM(CASE WHEN service = 'azure' THEN cost_usd ELSE 0 END), 0) AS azure_cost,
                    
                    -- Total
                    COALESCE(SUM(cost_usd), 0) AS total_api_cost
                FROM api_usage_log
                WHERE user_id = $1
                  AND created_at >= $2
                  AND created_at < $3 + INTERVAL '1 day'
                """,
                user_id,
                period_start,
                period_end,
            )
            
            # Get storage usage
            storage_row = await db.fetchrow(
                """
                SELECT
                    COALESCE(SUM(file_size), 0) AS document_storage,
                    COALESCE(COUNT(*), 0) AS document_count
                FROM uploaded_files
                WHERE user_id = $1
                """,
                user_id,
            )
            
            # Estimate embedding storage (1536 dims * 4 bytes * chunk count)
            chunk_row = await db.fetchrow(
                """
                SELECT COUNT(*) AS chunk_count
                FROM document_chunks dc
                JOIN document_repository dr ON dr.doc_id = dc.doc_id
                WHERE dr.user_id = $1
                """,
                user_id,
            )
            
            embedding_storage = (chunk_row["chunk_count"] or 0) * 1536 * 4
            document_storage = storage_row["document_storage"] or 0
            total_storage = document_storage + embedding_storage
            
            # Calculate Tiger storage cost (estimated)
            storage_gb = total_storage / (1024 ** 3)
            tiger_cost = Decimal(str(storage_gb)) * Decimal(str(TIGER_PRICING["storage_per_gb_month"]))
            
            # Calculate total
            api_cost = Decimal(str(usage_row["total_api_cost"] or 0))
            total_cost = api_cost + tiger_cost
            
            # Get daily breakdown for trend analysis
            daily_costs = await db.fetch(
                """
                SELECT
                    DATE(created_at) AS day,
                    SUM(cost_usd) AS daily_cost
                FROM api_usage_log
                WHERE user_id = $1
                  AND created_at >= $2
                GROUP BY DATE(created_at)
                ORDER BY day
                """,
                user_id,
                period_start,
            )
            
            # Calculate projections
            projection = self._calculate_projections(daily_costs, days)
            
            return {
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                    "days": days,
                },
                "tokens": {
                    "claude_input": usage_row["claude_input_tokens"] or 0,
                    "claude_output": usage_row["claude_output_tokens"] or 0,
                    "openai_embedding": usage_row["openai_tokens"] or 0,
                    "total": (usage_row["claude_input_tokens"] or 0) + 
                             (usage_row["claude_output_tokens"] or 0) + 
                             (usage_row["openai_tokens"] or 0),
                },
                "requests": {
                    "claude": usage_row["claude_requests"] or 0,
                    "embedding": usage_row["embedding_requests"] or 0,
                    "document_pages": usage_row["document_pages"] or 0,
                },
                "costs": {
                    "claude": round(float(usage_row["claude_cost"] or 0), 4),
                    "openai": round(float(usage_row["openai_cost"] or 0), 4),
                    "azure": round(float(usage_row["azure_cost"] or 0), 4),
                    "tiger_storage": round(float(tiger_cost), 4),
                    "total": round(float(total_cost), 4),
                },
                "storage": {
                    "documents_bytes": document_storage,
                    "documents_formatted": self._format_bytes(document_storage),
                    "embeddings_bytes": embedding_storage,
                    "embeddings_formatted": self._format_bytes(embedding_storage),
                    "total_bytes": total_storage,
                    "total_formatted": self._format_bytes(total_storage),
                    "document_count": storage_row["document_count"] or 0,
                    "chunk_count": chunk_row["chunk_count"] or 0,
                },
                "projections": projection,
                "daily_breakdown": [
                    {"date": str(r["day"]), "cost": round(float(r["daily_cost"] or 0), 4)}
                    for r in daily_costs
                ],
            }
            
        except Exception as e:
            logger.error(f"[USAGE] Failed to get usage summary: {e}", exc_info=True)
            return self._empty_usage_summary(period_start, period_end, days)
    
    async def get_diagnostics(
        self,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Get system diagnostics for troubleshooting.
        
        Returns information about:
        - Recent errors
        - API health
        - Memory system health
        - Document processing status
        - Background job status
        """
        try:
            # Get recent errors from logs (if we have an errors table)
            # For now, check for failed documents
            failed_docs = await db.fetch(
                """
                SELECT doc_id, title, created_at
                FROM document_repository
                WHERE user_id = $1
                  AND summary IS NULL
                  AND created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 5
                """,
                user_id,
            )
            
            # Get memory health
            memory_health = await db.fetchrow(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE confidence_score < 0.3) AS low_confidence,
                    COUNT(*) FILTER (WHERE archived_at IS NOT NULL) AS archived,
                    AVG(confidence_score) AS avg_confidence,
                    MAX(created_at) AS last_memory_created,
                    MAX(last_accessed) AS last_memory_accessed
                FROM memory_entries
                WHERE user_id = $1
                """,
                user_id,
            )
            
            # Get recent API failures (from usage log metadata)
            api_health = await db.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_requests_24h,
                    COUNT(*) FILTER (WHERE cost_usd = 0 AND service = 'claude') AS potential_failures
                FROM api_usage_log
                WHERE user_id = $1
                  AND created_at > NOW() - INTERVAL '24 hours'
                """,
                user_id,
            )
            
            # Check for stale data
            stale_check = await db.fetchrow(
                """
                SELECT
                    (SELECT MAX(created_at) FROM conversations WHERE user_id = $1) AS last_conversation,
                    (SELECT MAX(created_at) FROM messages m 
                     JOIN conversations c ON c.conversation_id = m.conversation_id 
                     WHERE c.user_id = $1) AS last_message,
                    (SELECT MAX(created_at) FROM memory_entries WHERE user_id = $1) AS last_memory,
                    (SELECT MAX(created_at) FROM uploaded_files WHERE user_id = $1) AS last_upload
                """,
                user_id,
            )
            
            # Build diagnostics
            issues = []
            warnings = []
            
            # Check for failed documents
            if failed_docs:
                issues.append({
                    "type": "document_processing",
                    "severity": "warning",
                    "message": f"{len(failed_docs)} document(s) may have failed processing",
                    "details": [{"id": d["doc_id"], "title": d["title"]} for d in failed_docs],
                })
            
            # Check for low confidence memories
            if memory_health["low_confidence"] and memory_health["low_confidence"] > 10:
                warnings.append({
                    "type": "memory_quality",
                    "severity": "info",
                    "message": f"{memory_health['low_confidence']} memories have low confidence scores",
                })
            
            # Check for stale activity
            if stale_check["last_message"]:
                hours_since_message = (datetime.utcnow() - stale_check["last_message"]).total_seconds() / 3600
                if hours_since_message > 168:  # 7 days
                    warnings.append({
                        "type": "activity",
                        "severity": "info",
                        "message": f"No messages in {int(hours_since_message / 24)} days",
                    })
            
            # Calculate overall health score
            health_score = 100
            health_score -= len(issues) * 15
            health_score -= len(warnings) * 5
            health_score = max(0, health_score)
            
            health_status = "healthy"
            if health_score < 70:
                health_status = "degraded"
            if health_score < 50:
                health_status = "unhealthy"
            
            return {
                "health": {
                    "score": health_score,
                    "status": health_status,
                },
                "memory_system": {
                    "total_memories": memory_health["total"] or 0,
                    "low_confidence_count": memory_health["low_confidence"] or 0,
                    "archived_count": memory_health["archived"] or 0,
                    "avg_confidence": round(float(memory_health["avg_confidence"] or 0), 2),
                    "last_memory_created": memory_health["last_memory_created"].isoformat() if memory_health["last_memory_created"] else None,
                    "last_memory_accessed": memory_health["last_memory_accessed"].isoformat() if memory_health["last_memory_accessed"] else None,
                },
                "api_health": {
                    "requests_24h": api_health["total_requests_24h"] or 0,
                    "potential_failures": api_health["potential_failures"] or 0,
                    "success_rate": round(
                        100 - ((api_health["potential_failures"] or 0) / max(1, api_health["total_requests_24h"] or 1) * 100),
                        1
                    ),
                },
                "activity": {
                    "last_conversation": stale_check["last_conversation"].isoformat() if stale_check["last_conversation"] else None,
                    "last_message": stale_check["last_message"].isoformat() if stale_check["last_message"] else None,
                    "last_memory": stale_check["last_memory"].isoformat() if stale_check["last_memory"] else None,
                    "last_upload": stale_check["last_upload"].isoformat() if stale_check["last_upload"] else None,
                },
                "issues": issues,
                "warnings": warnings,
            }
            
        except Exception as e:
            logger.error(f"[USAGE] Failed to get diagnostics: {e}", exc_info=True)
            return {
                "health": {"score": 0, "status": "error"},
                "error": str(e),
                "issues": [{"type": "system", "severity": "error", "message": "Failed to retrieve diagnostics"}],
                "warnings": [],
            }
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _calculate_projections(
        self,
        daily_costs: List[Dict],
        days: int,
    ) -> Dict[str, Any]:
        """Calculate future cost projections based on historical data."""
        if not daily_costs:
            return {
                "daily_average": 0,
                "monthly_estimate": 0,
                "annual_estimate": 0,
                "trend": "stable",
                "trend_percentage": 0,
            }
        
        costs = [float(r["daily_cost"] or 0) for r in daily_costs]
        
        # Daily average
        daily_avg = sum(costs) / len(costs) if costs else 0
        
        # Monthly and annual estimates
        monthly_est = daily_avg * 30
        annual_est = daily_avg * 365
        
        # Trend analysis (compare first half to second half)
        if len(costs) >= 4:
            mid = len(costs) // 2
            first_half_avg = sum(costs[:mid]) / mid if mid > 0 else 0
            second_half_avg = sum(costs[mid:]) / (len(costs) - mid) if (len(costs) - mid) > 0 else 0
            
            if first_half_avg > 0:
                trend_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100
            else:
                trend_pct = 0
            
            if trend_pct > 10:
                trend = "increasing"
            elif trend_pct < -10:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
            trend_pct = 0
        
        return {
            "daily_average": round(daily_avg, 4),
            "monthly_estimate": round(monthly_est, 2),
            "annual_estimate": round(annual_est, 2),
            "trend": trend,
            "trend_percentage": round(trend_pct, 1),
        }
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        if bytes_val == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        val = float(bytes_val)
        
        while val >= 1024 and i < len(units) - 1:
            val /= 1024
            i += 1
        
        return f"{val:.1f} {units[i]}"
    
    def _empty_usage_summary(
        self,
        start: date,
        end: date,
        days: int,
    ) -> Dict[str, Any]:
        """Return empty usage summary structure."""
        return {
            "period": {"start": start.isoformat(), "end": end.isoformat(), "days": days},
            "tokens": {"claude_input": 0, "claude_output": 0, "openai_embedding": 0, "total": 0},
            "requests": {"claude": 0, "embedding": 0, "document_pages": 0},
            "costs": {"claude": 0, "openai": 0, "azure": 0, "tiger_storage": 0, "total": 0},
            "storage": {
                "documents_bytes": 0, "documents_formatted": "0 B",
                "embeddings_bytes": 0, "embeddings_formatted": "0 B",
                "total_bytes": 0, "total_formatted": "0 B",
                "document_count": 0, "chunk_count": 0,
            },
            "projections": {
                "daily_average": 0, "monthly_estimate": 0, "annual_estimate": 0,
                "trend": "no_data", "trend_percentage": 0,
            },
            "daily_breakdown": [],
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

usage_service = AlphawaveUsageService()


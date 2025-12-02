"""
Nicole V7 Memory Background Jobs

Scheduled tasks that maintain the health and quality of Nicole's memory system.

Jobs:
1. Memory Decay - Reduce confidence of unused memories
2. Memory Consolidation - Merge similar/duplicate memories
3. Self-Reflection - Analyze patterns and insights
4. Knowledge Base Organization - Auto-organize memories into KBs
5. Memory Cleanup - Archive very low confidence memories

Design Philosophy:
- Run during low-activity periods
- Be conservative - don't lose important memories
- Log all actions for transparency
- Respect user preferences

Author: Nicole V7 Memory System
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from app.database import db
from app.services.memory_intelligence import memory_intelligence
from app.integrations.alphawave_claude import claude_client

logger = logging.getLogger(__name__)


# =============================================================================
# MEMORY DECAY JOB
# =============================================================================

async def run_memory_decay_job() -> Dict[str, Any]:
    """
    Apply confidence decay to unused memories.
    
    This job:
    1. Finds memories not accessed in 30+ days
    2. Reduces their confidence by a small amount
    3. Archives memories that fall below threshold
    4. Protects high-importance memories from aggressive decay
    
    Returns:
        Dict with job results
    """
    logger.info("[MEMORY JOB] Starting memory decay job...")
    
    results = {
        "job": "memory_decay",
        "started_at": datetime.utcnow().isoformat(),
        "decayed_count": 0,
        "archived_count": 0,
        "protected_count": 0,
        "errors": [],
    }
    
    try:
        # Try to use the SQL function first
        try:
            row = await db.fetchrow(
                "SELECT * FROM decay_unused_memories($1, $2, $3, $4)",
                30,     # days threshold
                Decimal("0.03"),  # decay amount (3%)
                Decimal("0.10"),  # minimum confidence
                Decimal("0.15"),  # archive threshold
            )
            
            if row:
                results["decayed_count"] = row.get("decayed_count", 0)
                results["archived_count"] = row.get("archived_count", 0)
                
        except Exception as func_err:
            logger.warning(f"[MEMORY JOB] SQL function not available, using fallback: {func_err}")
            
            # Fallback: Manual decay
            # Get candidates for decay
            candidates = await db.fetch(
                """
                SELECT memory_id, user_id, confidence, importance, last_accessed
                FROM memory_entries
                WHERE archived_at IS NULL
                  AND (last_accessed IS NULL OR last_accessed < NOW() - INTERVAL '30 days')
                  AND confidence > 0.10
                ORDER BY last_accessed ASC NULLS FIRST
                LIMIT 500
                """
            )
            
            for mem in candidates:
                # Protect high-importance memories
                if float(mem["importance"]) > 0.8 and float(mem["confidence"]) > 0.5:
                    results["protected_count"] += 1
                    continue
                
                # Calculate decay amount based on time since access
                days_since_access = 30  # Default if never accessed
                if mem["last_accessed"]:
                    days_since_access = (datetime.utcnow() - mem["last_accessed"].replace(tzinfo=None)).days
                
                # More aggressive decay for very old memories
                decay_amount = 0.03 if days_since_access < 60 else 0.05
                new_confidence = max(0.10, float(mem["confidence"]) - decay_amount)
                
                # Apply decay
                await db.execute(
                    """
                    UPDATE memory_entries
                    SET confidence = $1, updated_at = NOW()
                    WHERE memory_id = $2
                    """,
                    Decimal(str(new_confidence)),
                    mem["memory_id"],
                )
                results["decayed_count"] += 1
                
                # Archive if below threshold
                if new_confidence <= 0.15 and float(mem["importance"]) < 0.7:
                    await db.execute(
                        """
                        UPDATE memory_entries
                        SET archived_at = NOW(), updated_at = NOW()
                        WHERE memory_id = $1
                        """,
                        mem["memory_id"],
                    )
                    results["archived_count"] += 1
                    
                    # Log the action
                    await _log_job_action(
                        mem["user_id"],
                        "decay_applied",
                        "memory",
                        mem["memory_id"],
                        f"Archived due to low confidence ({new_confidence:.2f})"
                    )
        
        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = True
        
        logger.info(
            f"[MEMORY JOB] Decay complete: {results['decayed_count']} decayed, "
            f"{results['archived_count']} archived, {results['protected_count']} protected"
        )
        
    except Exception as e:
        logger.error(f"[MEMORY JOB] Decay job failed: {e}", exc_info=True)
        results["errors"].append(str(e))
        results["success"] = False
    
    return results


# =============================================================================
# MEMORY CONSOLIDATION JOB
# =============================================================================

async def run_memory_consolidation_job(
    max_consolidations: int = 10,
) -> Dict[str, Any]:
    """
    Find and consolidate similar/duplicate memories.
    
    This job:
    1. Finds pairs of highly similar memories
    2. Uses AI to merge them intelligently
    3. Archives the source memories
    4. Creates relationship links for context
    
    Args:
        max_consolidations: Maximum consolidations per run
        
    Returns:
        Dict with job results
    """
    logger.info("[MEMORY JOB] Starting memory consolidation job...")
    
    results = {
        "job": "memory_consolidation",
        "started_at": datetime.utcnow().isoformat(),
        "consolidated_count": 0,
        "memories_merged": 0,
        "errors": [],
    }
    
    try:
        # Get all active users
        users = await db.fetch(
            """
            SELECT DISTINCT user_id FROM memory_entries
            WHERE archived_at IS NULL
            AND created_at > NOW() - INTERVAL '90 days'
            """
        )
        
        for user_row in users:
            user_id = user_row["user_id"]
            
            # Find consolidation candidates for this user
            candidates = await memory_intelligence.find_consolidation_candidates(
                user_id=user_id,
                limit=max_consolidations,
            )
            
            # Group candidates by first memory to avoid duplicate work
            processed_ids = set()
            
            for mem1_id, mem2_id, similarity, reason in candidates:
                if mem1_id in processed_ids or mem2_id in processed_ids:
                    continue
                
                try:
                    # Consolidate the pair
                    new_memory_id = await memory_intelligence.consolidate_memories(
                        user_id=user_id,
                        memory_ids=[mem1_id, mem2_id],
                        consolidation_type="deduplicate" if similarity > 0.95 else "merge",
                    )
                    
                    if new_memory_id:
                        results["consolidated_count"] += 1
                        results["memories_merged"] += 2
                        processed_ids.add(mem1_id)
                        processed_ids.add(mem2_id)
                        
                        logger.info(
                            f"[MEMORY JOB] Consolidated {mem1_id} + {mem2_id} -> {new_memory_id} "
                            f"(similarity: {similarity:.2f})"
                        )
                        
                except Exception as cons_err:
                    logger.warning(f"[MEMORY JOB] Consolidation failed for {mem1_id}, {mem2_id}: {cons_err}")
                    results["errors"].append(f"Consolidation error: {cons_err}")
                
                # Limit per user
                if results["consolidated_count"] >= max_consolidations:
                    break
        
        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = True
        
        logger.info(
            f"[MEMORY JOB] Consolidation complete: {results['consolidated_count']} consolidations, "
            f"{results['memories_merged']} memories merged"
        )
        
    except Exception as e:
        logger.error(f"[MEMORY JOB] Consolidation job failed: {e}", exc_info=True)
        results["errors"].append(str(e))
        results["success"] = False
    
    return results


# =============================================================================
# SELF-REFLECTION JOB
# =============================================================================

async def run_self_reflection_job() -> Dict[str, Any]:
    """
    Nicole reflects on memory patterns and generates insights.
    
    This job:
    1. Analyzes memory patterns for each user
    2. Identifies frequently accessed topics
    3. Detects potential knowledge gaps
    4. Suggests organization improvements
    5. Creates insight memories for Nicole to reference
    
    Returns:
        Dict with job results
    """
    logger.info("[MEMORY JOB] Starting self-reflection job...")
    
    results = {
        "job": "self_reflection",
        "started_at": datetime.utcnow().isoformat(),
        "users_analyzed": 0,
        "insights_generated": 0,
        "kbs_suggested": 0,
        "errors": [],
    }
    
    try:
        # Get active users (those with recent memories)
        users = await db.fetch(
            """
            SELECT DISTINCT user_id FROM memory_entries
            WHERE archived_at IS NULL
            AND created_at > NOW() - INTERVAL '30 days'
            """
        )
        
        for user_row in users:
            user_id = user_row["user_id"]
            
            try:
                # Get memory statistics
                stats = await db.fetchrow(
                    """
                    SELECT
                        COUNT(*) AS total_memories,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') AS recent_memories,
                        AVG(confidence) AS avg_confidence,
                        AVG(importance) AS avg_importance,
                        COUNT(DISTINCT category) AS unique_categories,
                        SUM(access_count) AS total_accesses
                    FROM memory_entries
                    WHERE user_id = $1 AND archived_at IS NULL
                    """,
                    user_id
                )
                
                # Get most accessed memories
                top_memories = await db.fetch(
                    """
                    SELECT content, memory_type, access_count, category
                    FROM memory_entries
                    WHERE user_id = $1 AND archived_at IS NULL
                    ORDER BY access_count DESC
                    LIMIT 10
                    """,
                    user_id
                )
                
                # Get memory types distribution
                type_dist = await db.fetch(
                    """
                    SELECT memory_type::TEXT, COUNT(*) AS count
                    FROM memory_entries
                    WHERE user_id = $1 AND archived_at IS NULL
                    GROUP BY memory_type
                    ORDER BY count DESC
                    """,
                    user_id
                )
                
                # Generate reflection using Claude
                reflection_prompt = f"""Analyze these memory statistics and provide brief insights:

STATISTICS:
- Total memories: {stats['total_memories']}
- Recent (7 days): {stats['recent_memories']}
- Average confidence: {float(stats['avg_confidence'] or 0):.2f}
- Average importance: {float(stats['avg_importance'] or 0):.2f}
- Unique categories: {stats['unique_categories']}
- Total accesses: {stats['total_accesses']}

MEMORY TYPE DISTRIBUTION:
{chr(10).join(f"- {t['memory_type']}: {t['count']}" for t in type_dist)}

MOST ACCESSED MEMORIES:
{chr(10).join(f"- [{m['memory_type']}] {m['content'][:50]}... (accessed {m['access_count']}x)" for m in top_memories[:5])}

Provide 2-3 brief insights about:
1. What topics are most important to this user
2. Any patterns you notice
3. Suggestions for better organization (if any)

Keep response under 200 words. Be specific and actionable."""

                try:
                    reflection = await claude_client.generate_response(
                        messages=[{"role": "user", "content": reflection_prompt}],
                        system_prompt="You are analyzing memory patterns. Be concise and insightful.",
                        max_tokens=300,
                        temperature=0.5,
                    )
                    
                    # Save reflection as a system memory
                    await db.execute(
                        """
                        INSERT INTO memory_entries (
                            user_id, content, memory_type, category, confidence, importance,
                            created_by, created_at, updated_at
                        ) VALUES ($1, $2, 'insight'::memory_type_enum, 'system_reflection', 0.6, 0.3, 'nicole', NOW(), NOW())
                        """,
                        user_id,
                        f"[Self-Reflection {datetime.utcnow().strftime('%Y-%m-%d')}]\n{reflection.strip()}"
                    )
                    
                    results["insights_generated"] += 1
                    
                    # Log the action
                    await _log_job_action(
                        user_id,
                        "self_reflection",
                        "memory",
                        0,  # No specific target
                        "Generated periodic self-reflection insights"
                    )
                    
                except Exception as ai_err:
                    logger.warning(f"[MEMORY JOB] Reflection generation failed for user {user_id}: {ai_err}")
                
                # Check if we should suggest new knowledge bases
                categories = await db.fetch(
                    """
                    SELECT category, COUNT(*) AS count
                    FROM memory_entries
                    WHERE user_id = $1 
                      AND archived_at IS NULL
                      AND category IS NOT NULL
                      AND knowledge_base_id IS NULL
                    GROUP BY category
                    HAVING COUNT(*) >= 5
                    ORDER BY count DESC
                    LIMIT 3
                    """,
                    user_id
                )
                
                for cat in categories:
                    if await memory_intelligence.should_create_knowledge_base(user_id, cat["category"], threshold=5):
                        kb_id = await memory_intelligence.create_knowledge_base(
                            user_id=user_id,
                            name=cat["category"].title(),
                            kb_type="topic",
                            description=f"Auto-organized from {cat['count']} related memories"
                        )
                        
                        if kb_id:
                            await memory_intelligence.organize_memories_into_kb(
                                user_id, kb_id, cat["category"]
                            )
                            results["kbs_suggested"] += 1
                
                results["users_analyzed"] += 1
                
            except Exception as user_err:
                logger.warning(f"[MEMORY JOB] Reflection failed for user {user_id}: {user_err}")
                results["errors"].append(f"User {user_id}: {user_err}")
        
        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = True
        
        logger.info(
            f"[MEMORY JOB] Self-reflection complete: {results['users_analyzed']} users, "
            f"{results['insights_generated']} insights, {results['kbs_suggested']} KBs created"
        )
        
    except Exception as e:
        logger.error(f"[MEMORY JOB] Self-reflection job failed: {e}", exc_info=True)
        results["errors"].append(str(e))
        results["success"] = False
    
    return results


# =============================================================================
# RELATIONSHIP MAINTENANCE JOB
# =============================================================================

async def run_relationship_maintenance_job() -> Dict[str, Any]:
    """
    Maintain and strengthen memory relationships.
    
    This job:
    1. Finds memories that should be linked but aren't
    2. Updates relationship weights based on co-access patterns
    3. Removes weak relationships that haven't been useful
    
    Returns:
        Dict with job results
    """
    logger.info("[MEMORY JOB] Starting relationship maintenance job...")
    
    results = {
        "job": "relationship_maintenance",
        "started_at": datetime.utcnow().isoformat(),
        "new_links": 0,
        "strengthened": 0,
        "weakened": 0,
        "removed": 0,
        "errors": [],
    }
    
    try:
        # Get users with enough memories to have relationships
        users = await db.fetch(
            """
            SELECT user_id, COUNT(*) AS mem_count
            FROM memory_entries
            WHERE archived_at IS NULL
            GROUP BY user_id
            HAVING COUNT(*) >= 10
            """
        )
        
        for user_row in users:
            user_id = user_row["user_id"]
            
            try:
                # Find memories accessed together (co-access pattern)
                # This indicates they're related in the user's mind
                co_accessed = await db.fetch(
                    """
                    SELECT 
                        m1.memory_id AS mem1,
                        m2.memory_id AS mem2,
                        COUNT(*) AS co_access_count
                    FROM memory_entries m1
                    JOIN memory_entries m2 ON m1.user_id = m2.user_id
                    WHERE m1.user_id = $1
                      AND m1.memory_id < m2.memory_id
                      AND m1.archived_at IS NULL
                      AND m2.archived_at IS NULL
                      AND m1.last_accessed IS NOT NULL
                      AND m2.last_accessed IS NOT NULL
                      AND ABS(EXTRACT(EPOCH FROM (m1.last_accessed - m2.last_accessed))) < 300
                    GROUP BY m1.memory_id, m2.memory_id
                    HAVING COUNT(*) >= 2
                    LIMIT 20
                    """,
                    user_id
                )
                
                for pair in co_accessed:
                    # Check if relationship exists
                    existing = await db.fetchrow(
                        """
                        SELECT link_id, weight FROM memory_links
                        WHERE source_memory_id = $1 AND target_memory_id = $2
                        """,
                        pair["mem1"], pair["mem2"]
                    )
                    
                    if existing:
                        # Strengthen existing relationship
                        new_weight = min(1.0, float(existing["weight"]) + 0.05)
                        await db.execute(
                            "UPDATE memory_links SET weight = $1 WHERE link_id = $2",
                            Decimal(str(new_weight)),
                            existing["link_id"]
                        )
                        results["strengthened"] += 1
                    else:
                        # Create new relationship
                        await db.execute(
                            """
                            INSERT INTO memory_links (
                                source_memory_id, target_memory_id, relationship_type,
                                weight, bidirectional, reasoning, created_by
                            ) VALUES ($1, $2, 'related_to', 0.6, TRUE, 'Co-access pattern detected', 'system')
                            ON CONFLICT DO NOTHING
                            """,
                            pair["mem1"], pair["mem2"]
                        )
                        results["new_links"] += 1
                
                # Weaken relationships that haven't been useful
                await db.execute(
                    """
                    UPDATE memory_links
                    SET weight = GREATEST(0.1, weight - 0.05)
                    WHERE source_memory_id IN (
                        SELECT memory_id FROM memory_entries WHERE user_id = $1
                    )
                    AND created_at < NOW() - INTERVAL '30 days'
                    AND weight < 0.5
                    """,
                    user_id
                )
                
                # Remove very weak relationships
                removed = await db.execute(
                    """
                    DELETE FROM memory_links
                    WHERE source_memory_id IN (
                        SELECT memory_id FROM memory_entries WHERE user_id = $1
                    )
                    AND weight <= 0.1
                    AND created_at < NOW() - INTERVAL '60 days'
                    """,
                    user_id
                )
                
                # Extract count from result
                if removed and "DELETE" in removed:
                    try:
                        results["removed"] += int(removed.split()[-1])
                    except (ValueError, IndexError):
                        pass
                
            except Exception as user_err:
                logger.warning(f"[MEMORY JOB] Relationship maintenance failed for user {user_id}: {user_err}")
                results["errors"].append(f"User {user_id}: {user_err}")
        
        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = True
        
        logger.info(
            f"[MEMORY JOB] Relationship maintenance complete: {results['new_links']} new, "
            f"{results['strengthened']} strengthened, {results['removed']} removed"
        )
        
    except Exception as e:
        logger.error(f"[MEMORY JOB] Relationship maintenance failed: {e}", exc_info=True)
        results["errors"].append(str(e))
        results["success"] = False
    
    return results


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _log_job_action(
    user_id: int,
    action_type: str,
    target_type: str,
    target_id: int,
    reason: str,
) -> None:
    """
    Log a background job action to nicole_actions.
    
    nicole_actions schema:
    - action_id, action_type (enum), target_type (enum), target_id, user_id,
    - reason, context (jsonb), success, error_message, processing_time_ms,
    - tokens_used, created_at
    """
    import json
    
    # Map action_type to valid enum values
    action_map = {
        "decay_applied": "decay_applied",
        "self_reflection": "self_reflection",
        "consolidate": "consolidate",
        "link_memories": "link_memories",
        "organize_memories": "organize_memories",
        "create_kb": "create_kb",
        "archive_memory": "archive_memory",
        "boost_confidence": "boost_confidence",
        "pattern_detected": "pattern_detected",
    }
    db_action_type = action_map.get(action_type, "decay_applied")
    
    # Map target_type to valid enum values
    target_map = {
        "memory": "memory",
        "knowledge_base": "knowledge_base",
        "tag": "tag",
        "link": "link",
        "user": "user",
    }
    db_target_type = target_map.get(target_type, "memory")
    
    try:
        await db.execute(
            """
            INSERT INTO nicole_actions (
                action_type, target_type, target_id, user_id, reason, context, success, created_at
            ) VALUES ($1::nicole_action_type_enum, $2::target_type_enum, $3, $4, $5, $6, TRUE, NOW())
            """,
            db_action_type,
            db_target_type,
            target_id,
            user_id,
            reason,
            json.dumps({"source": "background_job"})
        )
    except Exception as e:
        logger.debug(f"[MEMORY JOB] Failed to log action: {e}")


# =============================================================================
# JOB SCHEDULER INTEGRATION
# =============================================================================

async def run_all_memory_jobs() -> Dict[str, Any]:
    """
    Run all memory maintenance jobs in sequence.
    
    Intended to be called by APScheduler daily during low-activity hours.
    """
    logger.info("[MEMORY JOB] Starting all memory maintenance jobs...")
    
    all_results = {
        "started_at": datetime.utcnow().isoformat(),
        "jobs": {},
    }
    
    # Run jobs in order of importance
    jobs = [
        ("decay", run_memory_decay_job),
        ("consolidation", run_memory_consolidation_job),
        ("relationships", run_relationship_maintenance_job),
        ("reflection", run_self_reflection_job),
    ]
    
    for job_name, job_func in jobs:
        try:
            result = await job_func()
            all_results["jobs"][job_name] = result
        except Exception as e:
            logger.error(f"[MEMORY JOB] Job '{job_name}' failed: {e}")
            all_results["jobs"][job_name] = {"success": False, "error": str(e)}
    
    all_results["completed_at"] = datetime.utcnow().isoformat()
    
    # Log summary
    successful = sum(1 for r in all_results["jobs"].values() if r.get("success", False))
    logger.info(f"[MEMORY JOB] All jobs complete: {successful}/{len(jobs)} successful")
    
    return all_results


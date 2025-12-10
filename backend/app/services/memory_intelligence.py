"""
Nicole V7 Memory Intelligence Service

This service provides the "brain" behind Nicole's memory system - the intelligent
processing that decides WHAT to remember, HOW to organize it, and WHEN to act.

Key Capabilities:
1. Intelligent Memory Extraction - Uses Claude to analyze conversations
2. Dynamic Tag Generation - Creates meaningful tags based on content
3. Relationship Mapping - Intelligently links related memories
4. Memory Consolidation - Merges similar/duplicate memories
5. Self-Reflection - Periodic analysis of memory patterns
6. Proactive Organization - Creates knowledge bases when patterns emerge

Design Philosophy:
- Quality over quantity: Only save meaningful memories
- Smart linking: Connect memories that truly relate
- Guardrails: Prevent memory bloat and confusion
- Autonomy with oversight: Nicole manages but user controls

Author: Nicole V7 Memory System
"""

import asyncio
import logging
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from app.database import db
from app.integrations.alphawave_claude import claude_client
from app.integrations.alphawave_openai import openai_client

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExtractedMemory:
    """Represents a memory extracted from conversation."""
    content: str
    memory_type: str
    importance: float
    confidence: float
    suggested_tags: List[str]
    entities: List[str]  # People, places, things mentioned
    context: str
    should_link_to: List[int]  # Memory IDs this relates to
    reasoning: str  # Why this should be remembered


@dataclass
class MemoryAnalysis:
    """Result of analyzing a message for memories."""
    should_save: bool
    memories: List[ExtractedMemory]
    suggested_kb: Optional[str]  # Suggested knowledge base
    detected_correction: bool
    correction_target: Optional[int]  # Memory ID being corrected
    analysis_reasoning: str


@dataclass
class RelationshipCandidate:
    """A potential relationship between memories."""
    source_id: int
    target_id: int
    relationship_type: str
    weight: float
    reasoning: str
    bidirectional: bool


# =============================================================================
# MEMORY INTELLIGENCE SERVICE
# =============================================================================

class MemoryIntelligenceService:
    """
    The intelligent core of Nicole's memory system.
    
    This service makes decisions about:
    - What information is worth remembering
    - How to categorize and tag memories
    - Which memories are related
    - When to consolidate or archive memories
    - How to organize memories into knowledge bases
    """
    
    def __init__(self):
        self._min_memory_length = 10  # Minimum content length
        self._max_daily_memories = 100  # Prevent memory bloat
        self._similarity_threshold = 0.85  # For duplicate detection
        self._relationship_threshold = 0.6  # Minimum for auto-linking
        
    # =========================================================================
    # INTELLIGENT MEMORY EXTRACTION
    # =========================================================================
    
    async def analyze_message_for_memories(
        self,
        user_id: int,
        user_message: str,
        assistant_response: str,
        conversation_id: int,
        user_name: str = "User",
    ) -> MemoryAnalysis:
        """
        Intelligently analyze a conversation exchange to extract memories.
        
        This is the main entry point for memory extraction. It uses Claude
        to understand the semantic meaning and decide what's worth remembering.
        
        Args:
            user_id: Tiger user ID
            user_message: What the user said
            assistant_response: What Nicole said
            conversation_id: Current conversation ID
            user_name: User's name for context
            
        Returns:
            MemoryAnalysis with extracted memories and recommendations
        """
        # Quick pre-filter - skip very short or generic messages
        if len(user_message) < self._min_memory_length:
            return MemoryAnalysis(
                should_save=False,
                memories=[],
                suggested_kb=None,
                detected_correction=False,
                correction_target=None,
                analysis_reasoning="Message too short to contain meaningful memory"
            )
        
        # Check daily memory limit
        today_count = await self._get_today_memory_count(user_id)
        if today_count >= self._max_daily_memories:
            logger.warning(f"[MEMORY INTEL] Daily limit reached for user {user_id}")
            return MemoryAnalysis(
                should_save=False,
                memories=[],
                suggested_kb=None,
                detected_correction=False,
                correction_target=None,
                analysis_reasoning="Daily memory limit reached - prioritizing quality"
            )
        
        # Get recent memories for context
        recent_memories = await self._get_recent_memory_context(user_id, limit=10)
        
        # Use Claude to analyze the message
        analysis_prompt = f"""Analyze this conversation exchange and determine what, if anything, should be remembered about {user_name}.

USER MESSAGE: "{user_message}"

NICOLE'S RESPONSE: "{assistant_response}"

RECENT MEMORIES ABOUT THIS USER:
{self._format_memories_for_prompt(recent_memories)}

INSTRUCTIONS:
1. Determine if this message contains information worth remembering long-term
2. Identify the TYPE of memory (preference, fact, goal, relationship, correction, pattern)
3. Extract the CORE information to remember (be concise but complete)
4. Suggest relevant TAGS from: important, personal, family, work, health, financial, emotional, routine, preference, goal, correction, relationship, location, time-sensitive
5. Identify any ENTITIES mentioned (people, places, specific things)
6. Check if this CORRECTS or UPDATES any existing memory
7. Rate IMPORTANCE (0.0-1.0) based on how useful this will be for future interactions
8. Provide your REASONING for the decision

RESPOND IN JSON FORMAT:
{{
    "should_remember": true/false,
    "reasoning": "Why this should/shouldn't be remembered",
    "memories": [
        {{
            "content": "The concise memory to store",
            "type": "preference|fact|goal|relationship|correction|pattern",
            "importance": 0.0-1.0,
            "confidence": 0.0-1.0,
            "tags": ["tag1", "tag2"],
            "entities": ["entity1", "entity2"],
            "context": "Brief context about when/why this was shared"
        }}
    ],
    "is_correction": true/false,
    "corrects_memory_about": "topic being corrected if applicable",
    "suggested_knowledge_base": "name if a new KB should be created, null otherwise"
}}

GUIDELINES:
- Only remember MEANINGFUL information (not "hello" or "thanks")
- Preferences are valuable (food, colors, activities, etc.)
- Facts about the user are valuable (job, family, location, etc.)
- Goals and aspirations are valuable
- Corrections should UPDATE existing knowledge, not duplicate
- Don't remember every detail - focus on what will be useful later
- If unsure, err on the side of NOT remembering"""

        try:
            response = await claude_client.generate_response(
                messages=[{"role": "user", "content": analysis_prompt}],
                system_prompt="You are a memory analysis system. Extract meaningful memories from conversations. Respond only with valid JSON.",
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for consistent analysis
            )
            
            # Parse the JSON response
            analysis_data = self._parse_json_response(response)
            
            if not analysis_data:
                logger.warning("[MEMORY INTEL] Failed to parse Claude response")
                return self._fallback_pattern_extraction(user_message, user_id)
            
            # Convert to MemoryAnalysis
            memories = []
            for mem_data in analysis_data.get("memories", []):
                # Find related memories
                related_ids = await self._find_related_memories(
                    user_id, 
                    mem_data.get("content", ""),
                    mem_data.get("entities", [])
                )
                
                memories.append(ExtractedMemory(
                    content=mem_data.get("content", ""),
                    memory_type=mem_data.get("type", "fact"),
                    importance=float(mem_data.get("importance", 0.5)),
                    confidence=float(mem_data.get("confidence", 0.8)),
                    suggested_tags=mem_data.get("tags", []),
                    entities=mem_data.get("entities", []),
                    context=mem_data.get("context", ""),
                    should_link_to=related_ids,
                    reasoning=analysis_data.get("reasoning", "")
                ))
            
            # Find correction target if this is a correction
            correction_target = None
            if analysis_data.get("is_correction"):
                correction_target = await self._find_correction_target(
                    user_id,
                    analysis_data.get("corrects_memory_about", "")
                )
            
            return MemoryAnalysis(
                should_save=analysis_data.get("should_remember", False),
                memories=memories,
                suggested_kb=analysis_data.get("suggested_knowledge_base"),
                detected_correction=analysis_data.get("is_correction", False),
                correction_target=correction_target,
                analysis_reasoning=analysis_data.get("reasoning", "")
            )
            
        except Exception as e:
            logger.error(f"[MEMORY INTEL] Analysis failed: {e}", exc_info=True)
            return self._fallback_pattern_extraction(user_message, user_id)
    
    def _fallback_pattern_extraction(
        self, 
        message: str, 
        user_id: int
    ) -> MemoryAnalysis:
        """
        Fallback pattern-based extraction when AI analysis fails.
        Uses regex patterns to identify common memory-worthy content.
        """
        memories = []
        message_lower = message.lower()
        
        # Pattern definitions with types and importance
        patterns = {
            "preference": [
                (r"(?:i|my)\s+(?:like|love|prefer|enjoy|hate|dislike)\s+(.+)", 0.7),
                (r"my\s+favorite\s+(\w+)\s+(?:is|are)\s+(.+)", 0.8),
                (r"i\s+always\s+(.+)", 0.6),
                (r"i\s+never\s+(.+)", 0.6),
            ],
            "fact": [
                (r"my\s+(?:name|birthday|age|job|work)\s+(?:is|are)\s+(.+)", 0.8),
                (r"i\s+(?:am|work\s+as|live\s+in)\s+(.+)", 0.7),
                (r"i\s+have\s+(\d+)\s+(.+)", 0.6),
            ],
            "goal": [
                (r"i\s+(?:want|need|plan)\s+to\s+(.+)", 0.7),
                (r"my\s+goal\s+is\s+(.+)", 0.8),
                (r"i'm\s+(?:trying|working)\s+(?:to|on)\s+(.+)", 0.7),
            ],
            "relationship": [
                (r"my\s+(?:wife|husband|son|daughter|mother|father|brother|sister|friend)\s+(.+)", 0.8),
            ],
        }
        
        for mem_type, pattern_list in patterns.items():
            for pattern, importance in pattern_list:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    memories.append(ExtractedMemory(
                        content=message,
                        memory_type=mem_type,
                        importance=importance,
                        confidence=0.7,  # Lower confidence for pattern matching
                        suggested_tags=[mem_type],
                        entities=[],
                        context="Pattern-matched extraction",
                        should_link_to=[],
                        reasoning=f"Matched {mem_type} pattern"
                    ))
                    break  # One memory per type per message
        
        # Check for explicit memory requests
        explicit_keywords = ["remember that", "don't forget", "keep in mind", "note that"]
        if any(kw in message_lower for kw in explicit_keywords):
            memories.append(ExtractedMemory(
                content=message,
                memory_type="fact",
                importance=0.9,
                confidence=0.9,
                suggested_tags=["important"],
                entities=[],
                context="Explicit memory request",
                should_link_to=[],
                reasoning="User explicitly asked to remember"
            ))
        
        return MemoryAnalysis(
            should_save=len(memories) > 0,
            memories=memories,
            suggested_kb=None,
            detected_correction=False,
            correction_target=None,
            analysis_reasoning="Fallback pattern extraction"
        )
    
    # =========================================================================
    # INTELLIGENT TAG GENERATION
    # =========================================================================
    
    async def generate_tags_for_memory(
        self,
        user_id: int,
        content: str,
        memory_type: str,
        suggested_tags: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Generate or select appropriate tags for a memory.
        
        This function:
        1. Maps suggested tags to existing system tags
        2. Creates new auto-tags for entities/topics if needed
        3. Returns tag IDs to assign
        
        Args:
            user_id: Tiger user ID
            content: Memory content
            memory_type: Type of memory
            suggested_tags: Tags suggested by analysis
            
        Returns:
            List of tag dicts with id, name, and whether it's new
        """
        result_tags = []
        
        # Get system tags
        system_tags = await db.fetch(
            "SELECT tag_id, name FROM memory_tags WHERE user_id IS NULL"
        )
        system_tag_map = {t["name"].lower(): t["tag_id"] for t in system_tags}
        
        # Get user's existing custom tags
        user_tags = await db.fetch(
            "SELECT tag_id, name FROM memory_tags WHERE user_id = $1",
            user_id
        )
        user_tag_map = {t["name"].lower(): t["tag_id"] for t in user_tags}
        
        # Process suggested tags
        for tag_name in suggested_tags:
            tag_lower = tag_name.lower().strip()
            
            # Check if it's a system tag
            if tag_lower in system_tag_map:
                result_tags.append({
                    "tag_id": system_tag_map[tag_lower],
                    "name": tag_lower,
                    "is_new": False
                })
            # Check if user already has this tag
            elif tag_lower in user_tag_map:
                result_tags.append({
                    "tag_id": user_tag_map[tag_lower],
                    "name": tag_lower,
                    "is_new": False
                })
            # Create new auto-tag if it seems meaningful
            elif len(tag_lower) >= 3 and self._is_valid_tag_name(tag_lower):
                new_tag = await self._create_auto_tag(user_id, tag_lower, content)
                if new_tag:
                    result_tags.append({
                        "tag_id": new_tag["tag_id"],
                        "name": tag_lower,
                        "is_new": True
                    })
        
        # Always add memory_type as a tag if it's a system tag
        if memory_type.lower() in system_tag_map and memory_type.lower() not in [t["name"] for t in result_tags]:
            result_tags.append({
                "tag_id": system_tag_map[memory_type.lower()],
                "name": memory_type.lower(),
                "is_new": False
            })
        
        return result_tags[:5]  # Limit to 5 tags per memory
    
    def _is_valid_tag_name(self, name: str) -> bool:
        """Check if a tag name is valid (not too generic, not gibberish)."""
        # Reject very common words
        common_words = {"the", "and", "for", "that", "this", "with", "from", "have", "been"}
        if name in common_words:
            return False
        
        # Reject if too many numbers
        if sum(c.isdigit() for c in name) > len(name) / 2:
            return False
        
        # Reject if no letters
        if not any(c.isalpha() for c in name):
            return False
        
        return True
    
    async def _create_auto_tag(
        self,
        user_id: int,
        tag_name: str,
        content: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create an auto-generated tag for a user.
        
        memory_tags schema: tag_id, user_id, name, description, color, icon,
        tag_type (enum), auto_criteria, confidence_threshold, usage_count,
        last_used_at, created_at
        """
        try:
            # Generate a color based on the tag name hash
            colors = ["#EF4444", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6", "#EC4899", "#06B6D4"]
            color = colors[hash(tag_name) % len(colors)]
            
            row = await db.fetchrow(
                """
                INSERT INTO memory_tags (user_id, name, tag_type, color, auto_criteria, created_at)
                VALUES ($1, $2, 'auto'::tag_type_enum, $3, $4, NOW())
                ON CONFLICT (user_id, name) DO UPDATE SET last_used_at = NOW()
                RETURNING tag_id, name
                """,
                user_id,
                tag_name,
                color,
                f"Auto-created from memory containing: {content[:50]}..."
            )
            return dict(row) if row else None
        except Exception as e:
            logger.warning(f"[MEMORY INTEL] Failed to create auto-tag '{tag_name}': {e}")
            return None
    
    # =========================================================================
    # INTELLIGENT RELATIONSHIP MAPPING
    # =========================================================================
    
    async def find_and_create_relationships(
        self,
        user_id: int,
        new_memory_id: int,
        content: str,
        entities: List[str],
        suggested_links: List[int],
    ) -> List[RelationshipCandidate]:
        """
        Intelligently find and create relationships between memories.
        
        This function:
        1. Uses vector similarity to find semantically related memories
        2. Checks for entity overlap (same people, places, things)
        3. Identifies temporal relationships
        4. Creates relationships with appropriate types and weights
        
        GUARDRAILS:
        - Only link memories with similarity > threshold
        - Don't create redundant links
        - Limit total links per memory to prevent web of connections
        - Prefer strong, meaningful connections over weak ones
        """
        relationships = []
        
        # Get the new memory's embedding
        new_memory = await db.fetchrow(
            "SELECT embedding, memory_type, category FROM memory_entries WHERE memory_id = $1",
            new_memory_id
        )
        
        if not new_memory or not new_memory["embedding"]:
            logger.debug("[MEMORY INTEL] New memory has no embedding, skipping relationship search")
            return relationships
        
        # Find similar memories by vector similarity
        similar_memories = await db.fetch(
            """
            SELECT 
                memory_id,
                content,
                memory_type,
                category,
                1 - (embedding <=> $1::vector) AS similarity
            FROM memory_entries
            WHERE user_id = $2
              AND memory_id != $3
              AND archived_at IS NULL
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT 10
            """,
            str(new_memory["embedding"]),
            user_id,
            new_memory_id
        )
        
        # Analyze each potential relationship
        for mem in similar_memories:
            similarity = float(mem["similarity"])
            
            # Skip if similarity is too low
            if similarity < self._relationship_threshold:
                continue
            
            # Determine relationship type based on analysis
            rel_type, weight, reasoning = self._determine_relationship_type(
                new_content=content,
                existing_content=mem["content"],
                new_type=new_memory["memory_type"],
                existing_type=mem["memory_type"],
                similarity=similarity,
                entities=entities
            )
            
            if rel_type:
                relationships.append(RelationshipCandidate(
                    source_id=new_memory_id,
                    target_id=mem["memory_id"],
                    relationship_type=rel_type,
                    weight=weight,
                    reasoning=reasoning,
                    bidirectional=rel_type in ["same_topic", "same_entity", "related_to"]
                ))
        
        # Also check suggested links from analysis
        for suggested_id in suggested_links:
            if suggested_id not in [r.target_id for r in relationships]:
                relationships.append(RelationshipCandidate(
                    source_id=new_memory_id,
                    target_id=suggested_id,
                    relationship_type="related_to",
                    weight=0.7,
                    reasoning="Suggested by memory analysis",
                    bidirectional=True
                ))
        
        # Limit to top 5 relationships
        relationships.sort(key=lambda r: r.weight, reverse=True)
        return relationships[:5]
    
    def _determine_relationship_type(
        self,
        new_content: str,
        existing_content: str,
        new_type: str,
        existing_type: str,
        similarity: float,
        entities: List[str],
    ) -> Tuple[Optional[str], float, str]:
        """
        Determine the type of relationship between two memories.
        
        Returns:
            Tuple of (relationship_type, weight, reasoning) or (None, 0, "") if no relationship
        """
        new_lower = new_content.lower()
        existing_lower = existing_content.lower()
        
        # Check for correction/contradiction
        correction_indicators = ["actually", "not anymore", "changed", "wrong", "incorrect", "used to"]
        if any(ind in new_lower for ind in correction_indicators) and similarity > 0.7:
            return ("supersedes", 0.9, "New memory appears to correct/update existing")
        
        # Check for elaboration (same topic, more detail)
        if new_type == existing_type and similarity > 0.8:
            if len(new_content) > len(existing_content) * 1.5:
                return ("elaborates", 0.8, "New memory adds detail to existing")
        
        # Check for same entity (shared names, places)
        shared_entities = []
        for entity in entities:
            if entity.lower() in existing_lower:
                shared_entities.append(entity)
        
        if shared_entities:
            return ("same_entity", min(0.9, 0.6 + 0.1 * len(shared_entities)), 
                   f"Shared entities: {', '.join(shared_entities)}")
        
        # High similarity = same topic
        if similarity > 0.8:
            return ("same_topic", similarity, f"High semantic similarity: {similarity:.2f}")
        
        # Moderate similarity = related
        if similarity > self._relationship_threshold:
            return ("related_to", similarity * 0.8, f"Semantic similarity: {similarity:.2f}")
        
        return (None, 0, "")
    
    async def save_relationships(
        self,
        user_id: int,
        relationships: List[RelationshipCandidate],
    ) -> int:
        """
        Save relationship candidates to the database.
        
        Note: memory_links table has relationship_type as TEXT (not enum),
        and does not have bidirectional or reasoning columns.
        """
        saved_count = 0
        
        for rel in relationships:
            try:
                # memory_links schema: link_id, source_memory_id, target_memory_id, 
                # relationship_type (TEXT), weight, created_at, created_by
                await db.execute(
                    """
                    INSERT INTO memory_links (
                        source_memory_id, target_memory_id, relationship_type,
                        weight, created_by, created_at
                    ) VALUES ($1, $2, $3, $4, 'nicole', NOW())
                    ON CONFLICT (source_memory_id, target_memory_id, relationship_type) 
                    DO UPDATE SET weight = $4
                    """,
                    rel.source_id,
                    rel.target_id,
                    rel.relationship_type,  # TEXT column, no enum cast
                    Decimal(str(rel.weight)),
                )
                saved_count += 1
                
                # Create reverse link if bidirectional
                if rel.bidirectional:
                    await db.execute(
                        """
                        INSERT INTO memory_links (
                            source_memory_id, target_memory_id, relationship_type,
                            weight, created_by, created_at
                        ) VALUES ($1, $2, $3, $4, 'nicole', NOW())
                        ON CONFLICT (source_memory_id, target_memory_id, relationship_type) 
                        DO UPDATE SET weight = $4
                        """,
                        rel.target_id,  # Reversed
                        rel.source_id,  # Reversed
                        rel.relationship_type,
                        Decimal(str(rel.weight)),
                    )
                
                # Log the action
                await self._log_nicole_action(
                    user_id=user_id,
                    action_type="link_memories",
                    target_type="link",
                    target_id=rel.source_id,
                    reason=rel.reasoning,
                    context={
                        "target_memory_id": rel.target_id, 
                        "type": rel.relationship_type,
                        "bidirectional": rel.bidirectional,
                        "reasoning": rel.reasoning
                    }
                )
                
            except Exception as e:
                logger.warning(f"[MEMORY INTEL] Failed to save relationship: {e}")
        
        return saved_count
    
    # =========================================================================
    # MEMORY CONSOLIDATION
    # =========================================================================
    
    async def find_consolidation_candidates(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Tuple[int, int, float, str]]:
        """
        Find pairs of memories that should be consolidated.
        
        Uses vector similarity to find memories that are semantically similar
        and could potentially be merged.
        
        Returns list of tuples: (memory_id_1, memory_id_2, similarity, reason)
        """
        candidates = []
        
        try:
            # Get recent memories with embeddings
            memories = await db.fetch(
                """
                SELECT memory_id, content, embedding
                FROM memory_entries
                WHERE user_id = $1
                  AND archived_at IS NULL
                  AND embedding IS NOT NULL
                  AND created_at > NOW() - INTERVAL '90 days'
                ORDER BY created_at DESC
                LIMIT 100
                """,
                user_id
            )
            
            if len(memories) < 2:
                return []
            
            # For each memory, find similar ones using vector search
            processed_pairs = set()
            
            for mem in memories[:20]:  # Limit to avoid O(n^2) explosion
                # Find similar memories
                similar = await db.fetch(
                    """
                    SELECT 
                        memory_id,
                        content,
                        1 - (embedding <=> $1::vector) AS similarity
                    FROM memory_entries
                    WHERE user_id = $2
                      AND memory_id != $3
                      AND archived_at IS NULL
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT 5
                    """,
                    str(mem["embedding"]) if mem["embedding"] else None,
                    user_id,
                    mem["memory_id"]
                )
                
                for sim_mem in similar:
                    similarity = float(sim_mem["similarity"])
                    
                    # Only consider high similarity pairs
                    if similarity < self._similarity_threshold:
                        continue
                    
                    # Create a consistent pair key to avoid duplicates
                    pair_key = tuple(sorted([mem["memory_id"], sim_mem["memory_id"]]))
                    if pair_key in processed_pairs:
                        continue
                    
                    processed_pairs.add(pair_key)
                    
                    # Analyze why these should be consolidated
                    reason = self._analyze_consolidation_reason(
                        mem["content"],
                        sim_mem["content"],
                        similarity
                    )
                    
                    candidates.append((
                        mem["memory_id"],
                        sim_mem["memory_id"],
                        similarity,
                        reason
                    ))
                    
                    if len(candidates) >= limit:
                        break
                
                if len(candidates) >= limit:
                    break
            
            # Sort by similarity (highest first)
            candidates.sort(key=lambda x: x[2], reverse=True)
            return candidates[:limit]
            
        except Exception as e:
            logger.warning(f"[MEMORY INTEL] find_consolidation_candidates failed: {e}")
            return []
    
    def _analyze_consolidation_reason(
        self,
        content1: str,
        content2: str,
        similarity: float,
    ) -> str:
        """Determine why two memories should be consolidated."""
        if similarity > 0.95:
            return "Near-duplicate memories"
        elif similarity > 0.9:
            return "Very similar content, likely redundant"
        elif similarity > 0.85:
            return "Related information that could be merged"
        else:
            return "Potentially related memories"
    
    async def consolidate_memories(
        self,
        user_id: int,
        memory_ids: List[int],
        consolidation_type: str = "merge",
    ) -> Optional[int]:
        """
        Consolidate multiple memories into one using AI.
        
        Args:
            user_id: Tiger user ID
            memory_ids: List of memory IDs to consolidate
            consolidation_type: merge, summarize, deduplicate, or upgrade
            
        Returns:
            New memory ID or None if failed
        """
        if len(memory_ids) < 2:
            return None
        
        # Fetch the memories
        memories = []
        for mid in memory_ids:
            mem = await db.fetchrow(
                "SELECT * FROM memory_entries WHERE memory_id = $1 AND user_id = $2",
                mid, user_id
            )
            if mem:
                memories.append(dict(mem))
        
        if len(memories) < 2:
            return None
        
        # Use Claude to create consolidated content
        consolidation_prompt = f"""Consolidate these {len(memories)} memories into a single, clear memory entry.

MEMORIES TO CONSOLIDATE:
{chr(10).join(f'- {m["content"]}' for m in memories)}

CONSOLIDATION TYPE: {consolidation_type}

INSTRUCTIONS:
- For 'merge': Combine all information into one comprehensive memory
- For 'summarize': Create a concise summary capturing the key points
- For 'deduplicate': Keep the most complete version, discard redundancy
- For 'upgrade': Take the newest/most accurate information

Respond with ONLY the consolidated memory text (no explanations)."""

        try:
            consolidated_content = await claude_client.generate_response(
                messages=[{"role": "user", "content": consolidation_prompt}],
                system_prompt="You consolidate memories into clear, concise statements.",
                max_tokens=500,
                temperature=0.3,
            )
            
            # Generate embedding for consolidated content
            embedding = await openai_client.generate_embedding(consolidated_content.strip())
            embedding_str = f'[{",".join(map(str, embedding))}]'
            
            # Determine the best memory type and importance
            memory_type = max(set(m["memory_type"] for m in memories), key=lambda t: sum(1 for m in memories if m["memory_type"] == t))
            importance = max(float(m["importance"]) for m in memories)
            
            # Create the consolidated memory
            new_memory = await db.fetchrow(
                """
                INSERT INTO memory_entries (
                    user_id, content, memory_type, embedding, category,
                    confidence, importance, created_by, created_at, updated_at
                ) VALUES ($1, $2, $3::memory_type_enum, $4::vector, $5, $6, $7, 'nicole', NOW(), NOW())
                RETURNING memory_id
                """,
                user_id,
                consolidated_content.strip(),
                memory_type,
                embedding_str,
                f"Consolidated from {len(memories)} memories",
                Decimal("0.9"),  # High confidence for AI-consolidated
                Decimal(str(importance)),
            )
            
            if not new_memory:
                return None
            
            new_memory_id = new_memory["memory_id"]
            
            # Record the consolidation
            # memory_consolidations schema: consolidation_id, result_memory_id, source_memory_ids (ARRAY),
            # consolidation_type (enum), reason, model_used, similarity_score, confidence, created_at
            await db.execute(
                """
                INSERT INTO memory_consolidations (
                    result_memory_id, source_memory_ids, consolidation_type,
                    reason, model_used, similarity_score, confidence, created_at
                ) VALUES ($1, $2, $3::consolidation_type_enum, $4, $5, $6, $7, NOW())
                """,
                new_memory_id,
                memory_ids,
                consolidation_type,
                f"Consolidated {len(memories)} similar memories",
                "claude-sonnet",  # model_used
                Decimal(str(self._similarity_threshold)),
                Decimal("0.9"),  # confidence
            )
            
            # Archive the source memories
            for mid in memory_ids:
                await db.execute(
                    "UPDATE memory_entries SET archived_at = NOW() WHERE memory_id = $1",
                    mid
                )
            
            # Log the action
            await self._log_nicole_action(
                user_id=user_id,
                action_type="consolidate",
                target_type="memory",
                target_id=new_memory_id,
                reason=f"Consolidated {len(memories)} similar memories",
                context={"source_ids": memory_ids, "type": consolidation_type}
            )
            
            logger.info(f"[MEMORY INTEL] Consolidated {len(memories)} memories into {new_memory_id}")
            return new_memory_id
            
        except Exception as e:
            logger.error(f"[MEMORY INTEL] Consolidation failed: {e}", exc_info=True)
            return None
    
    # =========================================================================
    # KNOWLEDGE BASE MANAGEMENT
    # =========================================================================
    
    async def should_create_knowledge_base(
        self,
        user_id: int,
        topic: str,
        threshold: int = 5,
    ) -> bool:
        """
        Determine if a new knowledge base should be created for a topic.
        
        A KB should be created when:
        - There are multiple memories about the same topic
        - The topic is distinct enough to warrant organization
        - No existing KB covers this topic
        """
        # Check if KB already exists
        existing = await db.fetchrow(
            "SELECT kb_id FROM knowledge_bases WHERE user_id = $1 AND LOWER(name) = LOWER($2)",
            user_id, topic
        )
        if existing:
            return False
        
        # Count memories that would belong to this KB
        count = await db.fetchval(
            """
            SELECT COUNT(*) FROM memory_entries
            WHERE user_id = $1
              AND archived_at IS NULL
              AND (
                  LOWER(content) LIKE '%' || LOWER($2) || '%'
                  OR LOWER(category) LIKE '%' || LOWER($2) || '%'
              )
            """,
            user_id, topic
        )
        
        return count >= threshold
    
    async def create_knowledge_base(
        self,
        user_id: int,
        name: str,
        kb_type: str = "topic",
        description: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create a new knowledge base.
        
        knowledge_bases schema: kb_id, user_id, name, description, icon, color,
        parent_id, kb_type (enum), is_shared, shared_with, memory_count, 
        last_memory_at, created_at, updated_at, archived_at, created_by
        """
        try:
            row = await db.fetchrow(
                """
                INSERT INTO knowledge_bases (
                    user_id, name, description, kb_type, created_by, created_at, updated_at
                ) VALUES ($1, $2, $3, $4::kb_type_enum, 'nicole', NOW(), NOW())
                ON CONFLICT (user_id, name) WHERE parent_id IS NULL DO NOTHING
                RETURNING kb_id
                """,
                user_id,
                name,
                description or f"Knowledge base for {name}",
                kb_type
            )
            
            if row:
                await self._log_nicole_action(
                    user_id=user_id,
                    action_type="create_kb",
                    target_type="knowledge_base",
                    target_id=row["kb_id"],
                    reason=f"Created KB for organizing memories about {name}"
                )
                return row["kb_id"]
            return None
            
        except Exception as e:
            logger.error(f"[MEMORY INTEL] Failed to create KB: {e}")
            return None
    
    async def organize_memories_into_kb(
        self,
        user_id: int,
        kb_id: int,
        topic: str,
    ) -> int:
        """Move relevant memories into a knowledge base."""
        result = await db.execute(
            """
            UPDATE memory_entries
            SET knowledge_base_id = $1, updated_at = NOW()
            WHERE user_id = $2
              AND archived_at IS NULL
              AND knowledge_base_id IS NULL
              AND (
                  LOWER(content) LIKE '%' || LOWER($3) || '%'
                  OR LOWER(category) LIKE '%' || LOWER($3) || '%'
              )
            """,
            kb_id, user_id, topic
        )
        
        # Extract count from result
        count = int(result.split()[-1]) if result else 0
        
        if count > 0:
            await self._log_nicole_action(
                user_id=user_id,
                action_type="organize_memories",
                target_type="knowledge_base",
                target_id=kb_id,
                reason=f"Organized {count} memories about {topic}",
                context={"topic": topic, "count": count}
            )
        
        return count
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _get_today_memory_count(self, user_id: int) -> int:
        """Get count of memories created today for rate limiting."""
        count = await db.fetchval(
            """
            SELECT COUNT(*) FROM memory_entries
            WHERE user_id = $1 AND created_at > NOW() - INTERVAL '24 hours'
            """,
            user_id
        )
        return count or 0
    
    async def _get_recent_memory_context(
        self, 
        user_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent memories for context in analysis."""
        rows = await db.fetch(
            """
            SELECT memory_id, content, memory_type, confidence, importance, created_at
            FROM memory_entries
            WHERE user_id = $1 AND archived_at IS NULL
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id, limit
        )
        return [dict(r) for r in rows]
    
    def _format_memories_for_prompt(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories for inclusion in AI prompt."""
        if not memories:
            return "No recent memories."
        
        lines = []
        for m in memories:
            mem_type = m.get("memory_type", "unknown")
            content = m.get("content", "")[:100]
            lines.append(f"- [{mem_type}] {content}")
        
        return "\n".join(lines)
    
    async def _find_related_memories(
        self,
        user_id: int,
        content: str,
        entities: List[str],
    ) -> List[int]:
        """Find memory IDs that relate to the given content."""
        related_ids = []
        
        # Search by entities
        for entity in entities[:3]:  # Limit entity searches
            rows = await db.fetch(
                """
                SELECT memory_id FROM memory_entries
                WHERE user_id = $1
                  AND archived_at IS NULL
                  AND LOWER(content) LIKE '%' || LOWER($2) || '%'
                LIMIT 3
                """,
                user_id, entity
            )
            related_ids.extend(r["memory_id"] for r in rows)
        
        return list(set(related_ids))[:5]  # Dedupe and limit
    
    async def _find_correction_target(
        self,
        user_id: int,
        topic: str,
    ) -> Optional[int]:
        """Find the memory that a correction is targeting."""
        if not topic:
            return None
        
        row = await db.fetchrow(
            """
            SELECT memory_id FROM memory_entries
            WHERE user_id = $1
              AND archived_at IS NULL
              AND LOWER(content) LIKE '%' || LOWER($2) || '%'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id, topic
        )
        return row["memory_id"] if row else None
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from Claude response, handling markdown code blocks."""
        # Try to extract JSON from code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            response = json_match.group(1)
        
        # Clean up common issues
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    pass
            return None
    
    async def _log_nicole_action(
        self,
        user_id: int,
        action_type: str,
        target_type: str,
        target_id: int,
        reason: str,
        context: Optional[Dict] = None,
    ) -> None:
        """
        Log an action taken by Nicole to the nicole_actions audit table.
        
        nicole_actions schema:
        - action_id (bigint)
        - action_type (nicole_action_type_enum)
        - target_type (target_type_enum)
        - target_id (bigint)
        - user_id (bigint)
        - reason (text)
        - context (jsonb)
        - success (boolean)
        - error_message (text)
        - processing_time_ms (integer)
        - tokens_used (integer)
        - created_at (timestamptz)
        """
        # Map action_type to valid enum values
        action_map = {
            "create_memory": "create_memory",
            "update_memory": "update_memory",
            "archive_memory": "archive_memory",
            "create_kb": "create_kb",
            "organize_memories": "organize_memories",
            "consolidate": "consolidate",
            "create_tag": "create_tag",
            "tag_memory": "tag_memory",
            "link_memories": "link_memories",
            "boost_confidence": "boost_confidence",
            "decay_applied": "decay_applied",
            "self_reflection": "self_reflection",
            "pattern_detected": "pattern_detected",
        }
        db_action_type = action_map.get(action_type, "create_memory")
        
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
                json.dumps(context) if context else None
            )
        except Exception as e:
            logger.debug(f"[MEMORY INTEL] Failed to log action: {e}")


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

memory_intelligence = MemoryIntelligenceService()

# Alias for backward compatibility with imports
memory_intelligence_service = memory_intelligence


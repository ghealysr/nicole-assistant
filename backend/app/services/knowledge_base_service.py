"""
Nicole V7 Knowledge Base Service

Production-grade service for managing design knowledge that Nicole
references when building $2-5K client websites.

Features:
- Full-text search with PostgreSQL GIN indexes
- Section-level granular retrieval
- Usage tracking for popularity ranking
- Search result caching
- Prepared for Qdrant vector integration

Architecture: asyncpg-native (matches TigerDatabaseManager pattern)
"""

import hashlib
import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.database import db

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """
    Core service for knowledge base operations.
    
    Uses Tiger Postgres via asyncpg for all database operations.
    Designed for high-performance retrieval during Nicole's coding sessions.
    """
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    async def create_file(
        self,
        slug: str,
        title: str,
        content: str,
        category: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: int = 1  # Glen's user_id
    ) -> Dict[str, Any]:
        """
        Create a new knowledge base file.
        
        Args:
            slug: URL-friendly unique identifier (e.g., 'hero-sections')
            title: Human-readable title
            content: Full markdown content
            category: Classification (patterns, animation, components, fundamentals, core)
            description: Optional summary for search results
            tags: Optional list of tags for filtering
            created_by: User ID of creator (default: Glen = 1)
            
        Returns:
            Dict with created file metadata including id, sections count
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        word_count = len(content.split())
        file_size = len(content.encode('utf-8'))
        
        async with db.acquire() as conn:
            # Insert file
            row = await conn.fetchrow("""
                INSERT INTO knowledge_base_files 
                (slug, title, description, category, content, content_hash,
                 tags, file_size_bytes, word_count, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id, slug, title, category, word_count, created_at
            """, slug, title, description, category, content, content_hash,
                tags or [], file_size, word_count, created_by)
            
            file_id = row['id']
            
            # Parse and create sections
            sections_created = await self._parse_and_create_sections(conn, file_id, content)
            
            logger.info(f"[KB] Created '{slug}' ({word_count} words, {sections_created} sections)")
            
            return {
                **dict(row),
                'sections_count': sections_created
            }
    
    async def _parse_and_create_sections(
        self,
        conn,
        file_id: int,
        content: str
    ) -> int:
        """
        Parse markdown headings and create section records.
        
        Enables granular retrieval - don't return entire 50KB file
        when only a specific section is relevant.
        
        Returns:
            Number of sections created
        """
        # Regex to match markdown headings
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        lines = content.split('\n')
        
        sections = []
        current_section = None
        section_order = 0
        
        for line in lines:
            match = re.match(heading_pattern, line)
            
            if match:
                # Save previous section if exists
                if current_section and current_section['content'].strip():
                    sections.append(current_section)
                
                # Start new section
                level = len(match.group(1))
                heading = match.group(2).strip()
                
                current_section = {
                    'heading': heading,
                    'level': level,
                    'section_order': section_order,
                    'content': ''
                }
                section_order += 1
            elif current_section:
                current_section['content'] += line + '\n'
        
        # Save last section
        if current_section and current_section['content'].strip():
            sections.append(current_section)
        
        # Bulk insert sections
        for section in sections:
            word_count = len(section['content'].split())
            await conn.execute("""
                INSERT INTO knowledge_base_sections 
                (file_id, heading, level, content, section_order, word_count)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, file_id, section['heading'], section['level'],
                section['content'].strip(), section['section_order'], word_count)
        
        return len(sections)
    
    async def get_file_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a knowledge file by its slug.
        
        Args:
            slug: Unique identifier (e.g., 'hero-sections')
            
        Returns:
            File metadata and content, or None if not found
        """
        async with db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, slug, title, description, category, content,
                       tags, word_count, usage_count, created_at, updated_at
                FROM knowledge_base_files
                WHERE slug = $1 AND is_active = true
            """, slug)
            
            if row:
                # Increment usage count asynchronously (fire-and-forget pattern)
                await conn.execute("""
                    UPDATE knowledge_base_files
                    SET usage_count = usage_count + 1, last_accessed = NOW()
                    WHERE id = $1
                """, row['id'])
                
                return dict(row)
            return None
    
    async def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a knowledge file by ID."""
        async with db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, slug, title, description, category, content,
                       tags, word_count, usage_count, created_at, updated_at
                FROM knowledge_base_files
                WHERE id = $1 AND is_active = true
            """, file_id)
            
            return dict(row) if row else None
    
    async def update_file(
        self,
        slug: str,
        content: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing knowledge file.
        
        Increments version number and re-parses sections.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        word_count = len(content.split())
        file_size = len(content.encode('utf-8'))
        
        async with db.transaction() as conn:
            # Update file
            row = await conn.fetchrow("""
                UPDATE knowledge_base_files
                SET content = $2,
                    content_hash = $3,
                    word_count = $4,
                    file_size_bytes = $5,
                    version = version + 1,
                    title = COALESCE($6, title),
                    description = COALESCE($7, description),
                    tags = COALESCE($8, tags)
                WHERE slug = $1 AND is_active = true
                RETURNING id, slug, title, version, word_count
            """, slug, content, content_hash, word_count, file_size,
                title, description, tags)
            
            if not row:
                return None
            
            file_id = row['id']
            
            # Delete old sections
            await conn.execute("""
                DELETE FROM knowledge_base_sections WHERE file_id = $1
            """, file_id)
            
            # Re-parse and create new sections
            sections_created = await self._parse_and_create_sections(conn, file_id, content)
            
            logger.info(f"[KB] Updated '{slug}' to v{row['version']} ({sections_created} sections)")
            
            return {
                **dict(row),
                'sections_count': sections_created
            }
    
    async def delete_file(self, slug: str) -> bool:
        """Soft delete a knowledge file."""
        async with db.acquire() as conn:
            result = await conn.execute("""
                UPDATE knowledge_base_files
                SET is_active = false
                WHERE slug = $1 AND is_active = true
            """, slug)
            
            deleted = 'UPDATE 1' in result
            if deleted:
                logger.info(f"[KB] Soft-deleted '{slug}'")
            return deleted
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    async def search_fulltext(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across knowledge base files.
        
        Uses PostgreSQL's tsvector for efficient text matching.
        Results ranked by relevance and usage popularity.
        
        Args:
            query: Search terms
            category: Optional category filter
            tags: Optional tag filter (matches any)
            limit: Max results to return
            
        Returns:
            List of matching files with relevance rank
        """
        async with db.acquire() as conn:
            # Build dynamic query based on filters
            conditions = ["is_active = true"]
            params = [query]
            param_idx = 2
            
            if category:
                conditions.append(f"category = ${param_idx}")
                params.append(category)
                param_idx += 1
            
            if tags:
                conditions.append(f"tags && ${param_idx}")  # Array overlap
                params.append(tags)
                param_idx += 1
            
            params.append(limit)
            
            where_clause = " AND ".join(conditions)
            
            rows = await conn.fetch(f"""
                SELECT 
                    id, slug, title, category, description, tags,
                    word_count, usage_count,
                    ts_rank(
                        to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || content),
                        plainto_tsquery('english', $1)
                    ) as relevance
                FROM knowledge_base_files
                WHERE {where_clause}
                  AND to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || content) 
                      @@ plainto_tsquery('english', $1)
                ORDER BY relevance DESC, usage_count DESC
                LIMIT ${param_idx}
            """, *params)
            
            return [dict(r) for r in rows]
    
    async def search_sections(
        self,
        query: str,
        file_id: Optional[int] = None,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search within sections for more granular results.
        
        Args:
            query: Search query string
            file_id: Optional filter to specific file
            category: Optional filter to specific category (e.g., 'qa', 'fundamentals')
            limit: Maximum results to return
            
        Returns:
            List of matching sections with relevance scores
        """
        async with db.acquire() as conn:
            if file_id:
                # Search within specific file
                rows = await conn.fetch("""
                    SELECT 
                        s.id, s.file_id, s.heading, s.level, s.content, s.word_count,
                        f.slug as file_slug, f.title as file_title, f.category,
                        ts_rank(to_tsvector('english', s.heading || ' ' || s.content),
                                plainto_tsquery('english', $1)) as relevance
                    FROM knowledge_base_sections s
                    JOIN knowledge_base_files f ON s.file_id = f.id
                    WHERE f.is_active = true
                      AND s.file_id = $2
                      AND to_tsvector('english', s.heading || ' ' || s.content) 
                          @@ plainto_tsquery('english', $1)
                    ORDER BY relevance DESC
                    LIMIT $3
                """, query, file_id, limit)
            elif category:
                # Search within specific category (e.g., 'qa')
                rows = await conn.fetch("""
                    SELECT 
                        s.id, s.file_id, s.heading, s.level, s.content, s.word_count,
                        f.slug as file_slug, f.title as file_title, f.category,
                        ts_rank(to_tsvector('english', s.heading || ' ' || s.content),
                                plainto_tsquery('english', $1)) as relevance
                    FROM knowledge_base_sections s
                    JOIN knowledge_base_files f ON s.file_id = f.id
                    WHERE f.is_active = true
                      AND f.category = $2
                      AND to_tsvector('english', s.heading || ' ' || s.content) 
                          @@ plainto_tsquery('english', $1)
                    ORDER BY relevance DESC
                    LIMIT $3
                """, query, category, limit)
            else:
                # Search all sections
                rows = await conn.fetch("""
                    SELECT 
                        s.id, s.file_id, s.heading, s.level, s.content, s.word_count,
                        f.slug as file_slug, f.title as file_title, f.category,
                        ts_rank(to_tsvector('english', s.heading || ' ' || s.content),
                                plainto_tsquery('english', $1)) as relevance
                    FROM knowledge_base_sections s
                    JOIN knowledge_base_files f ON s.file_id = f.id
                    WHERE f.is_active = true
                      AND to_tsvector('english', s.heading || ' ' || s.content) 
                          @@ plainto_tsquery('english', $1)
                    ORDER BY relevance DESC
                    LIMIT $2
                """, query, limit)
            
            return [dict(r) for r in rows]
    
    async def get_by_category(
        self,
        category: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all files in a category, sorted by usage."""
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, slug, title, description, tags, word_count, usage_count
                FROM knowledge_base_files
                WHERE category = $1 AND is_active = true
                ORDER BY usage_count DESC, title
                LIMIT $2
            """, category, limit)
            
            return [dict(r) for r in rows]
    
    async def get_by_tags(
        self,
        tags: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get files matching any of the specified tags."""
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, slug, title, category, description, tags, usage_count
                FROM knowledge_base_files
                WHERE tags && $1 AND is_active = true
                ORDER BY usage_count DESC
                LIMIT $2
            """, tags, limit)
            
            return [dict(r) for r in rows]
    
    # =========================================================================
    # CONTEXT RETRIEVAL (For Nicole's System Prompt)
    # =========================================================================
    
    async def get_relevant_context(
        self,
        query: str,
        max_sections: int = 5,
        max_tokens: int = 4000,
        category: Optional[str] = None
    ) -> str:
        """
        Retrieve relevant knowledge context for Nicole's system prompt.
        
        This is the primary method Nicole uses to augment her responses
        with design knowledge during coding sessions.
        
        Args:
            query: User's request or project context
            max_sections: Maximum sections to include
            max_tokens: Approximate token limit (1 word ≈ 1.3 tokens)
            category: Optional category filter (e.g., 'qa', 'fundamentals', 'patterns')
            
        Returns:
            Formatted markdown context string
        """
        max_words = int(max_tokens / 1.3)
        
        # Search for relevant sections (with optional category filter)
        sections = await self.search_sections(query, category=category, limit=max_sections * 2)
        
        if not sections:
            return ""
        
        context_parts = []
        total_words = 0
        
        for section in sections[:max_sections]:
            section_words = section.get('word_count', 0)
            
            if total_words + section_words > max_words:
                # Truncate if needed
                remaining_words = max_words - total_words
                if remaining_words < 100:
                    break
                content = ' '.join(section['content'].split()[:remaining_words])
            else:
                content = section['content']
            
            context_parts.append(f"""
### {section['heading']} (from {section['file_title']})

{content}
""")
            total_words += section_words
            
            if total_words >= max_words:
                break
        
        if context_parts:
            return f"""
## 📚 Relevant Design Knowledge

{chr(10).join(context_parts)}
"""
        return ""
    
    async def get_all_slugs(self) -> List[str]:
        """Get list of all active knowledge file slugs."""
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT slug FROM knowledge_base_files
                WHERE is_active = true
                ORDER BY category, title
            """)
            return [r['slug'] for r in rows]
    
    # =========================================================================
    # USAGE TRACKING
    # =========================================================================
    
    async def log_access(
        self,
        file_id: int,
        user_id: int = 1,
        query_text: Optional[str] = None,
        access_method: str = "direct",
        section_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> None:
        """
        Log knowledge base access for analytics.
        
        Args:
            file_id: Accessed file ID
            user_id: User who accessed (default: Glen = 1)
            query_text: Search query that led to access
            access_method: How accessed ('search', 'direct', 'recommended', 'nicole_context')
            section_id: Specific section if applicable
            session_id: For grouping related accesses
        """
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO knowledge_base_usage_log 
                (file_id, section_id, user_id, query_text, access_method, session_id)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, file_id, section_id, user_id, query_text, access_method, session_id)
    
    async def get_popular_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most accessed knowledge files."""
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, slug, title, category, description, usage_count, last_accessed
                FROM knowledge_base_files
                WHERE is_active = true
                ORDER BY usage_count DESC
                LIMIT $1
            """, limit)
            
            return [dict(r) for r in rows]
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get overall knowledge base usage statistics."""
        async with db.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(word_count) as total_words,
                    SUM(usage_count) as total_accesses,
                    COUNT(DISTINCT category) as categories
                FROM knowledge_base_files
                WHERE is_active = true
            """)
            
            recent_accesses = await conn.fetchval("""
                SELECT COUNT(*) FROM knowledge_base_usage_log
                WHERE accessed_at > NOW() - INTERVAL '24 hours'
            """)
            
            return {
                **dict(stats),
                'accesses_24h': recent_accesses
            }
    
    # =========================================================================
    # SEARCH CACHE
    # =========================================================================
    
    async def get_cached_search(self, query: str) -> Optional[List[int]]:
        """Check if search results are cached."""
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()
        
        async with db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT result_file_ids
                FROM knowledge_base_search_cache
                WHERE query_hash = $1 AND expires_at > NOW()
            """, query_hash)
            
            if row:
                # Increment hit count
                await conn.execute("""
                    UPDATE knowledge_base_search_cache
                    SET hit_count = hit_count + 1, last_hit_at = NOW()
                    WHERE query_hash = $1
                """, query_hash)
                return row['result_file_ids']
            
            return None
    
    async def cache_search_results(
        self,
        query: str,
        file_ids: List[int],
        section_ids: Optional[List[int]] = None,
        search_type: str = "fulltext",
        ttl_hours: int = 24
    ) -> None:
        """Cache search results for faster repeated queries."""
        query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO knowledge_base_search_cache 
                (query_text, query_hash, result_file_ids, result_section_ids, search_type, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (query_hash) 
                DO UPDATE SET 
                    result_file_ids = EXCLUDED.result_file_ids,
                    result_section_ids = EXCLUDED.result_section_ids,
                    hit_count = knowledge_base_search_cache.hit_count + 1,
                    last_hit_at = NOW(),
                    expires_at = EXCLUDED.expires_at
            """, query, query_hash, file_ids, section_ids, search_type, expires_at)
    
    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries. Call periodically."""
        async with db.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM knowledge_base_search_cache
                WHERE expires_at < NOW()
            """)
            
            deleted = int(result.split()[-1]) if result else 0
            if deleted > 0:
                logger.info(f"[KB] Cleaned up {deleted} expired cache entries")
            return deleted


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

kb_service = KnowledgeBaseService()


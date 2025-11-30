-- ============================================================================
-- NICOLE V7 MEMORY SYSTEM FUNCTIONS
-- Tiger Postgres + pgvectorscale
-- ============================================================================
-- 
-- This migration adds the SQL functions required by the memory service:
--   1. search_memories_hybrid() - Combined vector + keyword search
--   2. boost_memory_access() - Increment access count and confidence
--   3. decay_unused_memories() - Scheduled decay for stale memories
--   4. get_memory_context() - Build context for AI prompts
--
-- Prerequisites:
--   - nicole_v7_final_schema.sql must be applied first
--   - Extensions: vector, pg_trgm
--
-- ============================================================================

-- ============================================================================
-- FUNCTION 1: HYBRID MEMORY SEARCH
-- ============================================================================
-- Combines vector similarity with keyword matching and confidence weighting
-- Returns memories ranked by composite score

CREATE OR REPLACE FUNCTION search_memories_hybrid(
    p_user_id BIGINT,
    p_query_embedding vector(1536),
    p_query_text TEXT,
    p_limit INTEGER DEFAULT 10,
    p_min_confidence NUMERIC DEFAULT 0.2
)
RETURNS TABLE (
    memory_id BIGINT,
    user_id BIGINT,
    content TEXT,
    memory_type TEXT,
    context TEXT,
    source_type TEXT,
    source_id BIGINT,
    confidence_score NUMERIC,
    importance_score NUMERIC,
    access_count INTEGER,
    last_accessed TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    vector_score FLOAT,
    keyword_score FLOAT,
    composite_score FLOAT
) AS $$
DECLARE
    v_query_tsquery tsquery;
BEGIN
    -- Build text search query
    v_query_tsquery := plainto_tsquery('english', p_query_text);
    
    RETURN QUERY
    WITH vector_matches AS (
        -- Vector similarity search using pgvectorscale
        SELECT 
            m.memory_id,
            1 - (m.embedding <=> p_query_embedding) AS v_score
        FROM memory_entries m
        WHERE m.user_id = p_user_id
          AND m.archived_at IS NULL
          AND m.confidence >= p_min_confidence
          AND m.embedding IS NOT NULL
        ORDER BY m.embedding <=> p_query_embedding
        LIMIT p_limit * 3  -- Get more candidates for re-ranking
    ),
    keyword_matches AS (
        -- Full-text search with trigram similarity
        SELECT 
            m.memory_id,
            GREATEST(
                ts_rank_cd(to_tsvector('english', m.content), v_query_tsquery),
                similarity(m.content, p_query_text)
            ) AS k_score
        FROM memory_entries m
        WHERE m.user_id = p_user_id
          AND m.archived_at IS NULL
          AND m.confidence >= p_min_confidence
          AND (
              to_tsvector('english', m.content) @@ v_query_tsquery
              OR m.content ILIKE '%' || p_query_text || '%'
              OR similarity(m.content, p_query_text) > 0.1
          )
        LIMIT p_limit * 3
    ),
    combined AS (
        -- Merge and score
        SELECT 
            COALESCE(vm.memory_id, km.memory_id) AS mem_id,
            COALESCE(vm.v_score, 0.0) AS vec_score,
            COALESCE(km.k_score, 0.0) AS key_score
        FROM vector_matches vm
        FULL OUTER JOIN keyword_matches km ON vm.memory_id = km.memory_id
    ),
    ranked AS (
        SELECT 
            c.mem_id,
            c.vec_score,
            c.key_score,
            -- Composite score: 60% vector, 30% keyword, 10% recency/confidence boost
            (
                0.6 * c.vec_score + 
                0.3 * c.key_score + 
                0.1 * (
                    COALESCE(m.confidence, 0.5) * 0.5 +
                    COALESCE(m.importance, 0.5) * 0.3 +
                    CASE 
                        WHEN m.last_accessed > NOW() - INTERVAL '7 days' THEN 0.2
                        WHEN m.last_accessed > NOW() - INTERVAL '30 days' THEN 0.1
                        ELSE 0.0
                    END
                )
            ) AS comp_score
        FROM combined c
        JOIN memory_entries m ON m.memory_id = c.mem_id
    )
    SELECT 
        m.memory_id,
        m.user_id,
        m.content,
        m.memory_type::TEXT,
        m.category AS context,
        'chat'::TEXT AS source_type,
        m.source_conversation_id AS source_id,
        m.confidence AS confidence_score,
        m.importance AS importance_score,
        m.access_count,
        m.last_accessed,
        '{}'::JSONB AS metadata,
        m.created_at,
        m.updated_at,
        m.archived_at,
        r.vec_score::FLOAT AS vector_score,
        r.key_score::FLOAT AS keyword_score,
        r.comp_score::FLOAT AS composite_score
    FROM ranked r
    JOIN memory_entries m ON m.memory_id = r.mem_id
    WHERE r.comp_score > 0.05  -- Minimum relevance threshold
    ORDER BY r.comp_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION search_memories_hybrid IS 
'Hybrid search combining vector similarity and keyword matching with confidence weighting.
Used by memory_service.search_memory() for context retrieval.';


-- ============================================================================
-- FUNCTION 2: BOOST MEMORY ACCESS
-- ============================================================================
-- Called when a memory is retrieved/used, updates access metrics

CREATE OR REPLACE FUNCTION boost_memory_access(
    p_memory_id BIGINT,
    p_confidence_boost NUMERIC DEFAULT 0.02
)
RETURNS VOID AS $$
BEGIN
    UPDATE memory_entries
    SET 
        access_count = access_count + 1,
        last_accessed = NOW(),
        -- Boost confidence slightly, cap at 1.0
        confidence = LEAST(1.0, confidence + p_confidence_boost),
        updated_at = NOW()
    WHERE memory_id = p_memory_id
      AND archived_at IS NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION boost_memory_access IS 
'Increments access count and slightly boosts confidence when a memory is retrieved.
Implements the "memories that are used become stronger" principle.';


-- ============================================================================
-- FUNCTION 3: DECAY UNUSED MEMORIES
-- ============================================================================
-- Background job function to decay memories that haven't been accessed

CREATE OR REPLACE FUNCTION decay_unused_memories(
    p_decay_threshold_days INTEGER DEFAULT 30,
    p_decay_amount NUMERIC DEFAULT 0.05,
    p_min_confidence NUMERIC DEFAULT 0.1,
    p_archive_threshold NUMERIC DEFAULT 0.15
)
RETURNS TABLE (
    decayed_count INTEGER,
    archived_count INTEGER
) AS $$
DECLARE
    v_decayed INTEGER := 0;
    v_archived INTEGER := 0;
BEGIN
    -- Decay confidence for unused memories
    WITH decayed AS (
        UPDATE memory_entries
        SET 
            confidence = GREATEST(p_min_confidence, confidence - p_decay_amount),
            updated_at = NOW()
        WHERE archived_at IS NULL
          AND (
              last_accessed IS NULL 
              OR last_accessed < NOW() - (p_decay_threshold_days || ' days')::INTERVAL
          )
          AND confidence > p_min_confidence
          -- Don't decay high-importance memories as quickly
          AND NOT (importance > 0.8 AND confidence > 0.5)
        RETURNING memory_id
    )
    SELECT COUNT(*) INTO v_decayed FROM decayed;
    
    -- Archive memories that have decayed below threshold
    WITH archived AS (
        UPDATE memory_entries
        SET 
            archived_at = NOW(),
            updated_at = NOW()
        WHERE archived_at IS NULL
          AND confidence <= p_archive_threshold
          AND importance < 0.7  -- Never auto-archive important memories
          AND created_at < NOW() - INTERVAL '7 days'  -- Give new memories time
        RETURNING memory_id
    )
    SELECT COUNT(*) INTO v_archived FROM archived;
    
    RETURN QUERY SELECT v_decayed, v_archived;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION decay_unused_memories IS 
'Background job function that decays unused memories and archives low-confidence ones.
Run daily via APScheduler. Implements memory lifecycle management.';


-- ============================================================================
-- FUNCTION 4: GET MEMORY CONTEXT
-- ============================================================================
-- Builds a formatted context string for AI prompts

CREATE OR REPLACE FUNCTION get_memory_context(
    p_user_id BIGINT,
    p_query_embedding vector(1536),
    p_query_text TEXT,
    p_max_tokens INTEGER DEFAULT 2000
)
RETURNS TEXT AS $$
DECLARE
    v_context TEXT := '';
    v_token_estimate INTEGER := 0;
    v_memory RECORD;
BEGIN
    FOR v_memory IN 
        SELECT 
            memory_type,
            content,
            confidence_score,
            importance_score
        FROM search_memories_hybrid(
            p_user_id, 
            p_query_embedding, 
            p_query_text, 
            15,  -- Get top 15 candidates
            0.3  -- Minimum confidence
        )
        ORDER BY composite_score DESC
    LOOP
        -- Rough token estimate (4 chars per token)
        v_token_estimate := v_token_estimate + (LENGTH(v_memory.content) / 4);
        
        EXIT WHEN v_token_estimate > p_max_tokens;
        
        -- Format memory entry
        v_context := v_context || format(
            E'• [%s] %s\n',
            UPPER(v_memory.memory_type),
            v_memory.content
        );
    END LOOP;
    
    RETURN v_context;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_memory_context IS 
'Builds a formatted context string from relevant memories for inclusion in AI prompts.
Respects token limits and prioritizes by composite relevance score.';


-- ============================================================================
-- FUNCTION 5: MEMORY STATS
-- ============================================================================
-- Returns comprehensive statistics for a user's memory system

CREATE OR REPLACE FUNCTION get_memory_stats(p_user_id BIGINT)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_memories', COUNT(*) FILTER (WHERE archived_at IS NULL),
        'archived_memories', COUNT(*) FILTER (WHERE archived_at IS NOT NULL),
        'by_type', jsonb_object_agg(
            COALESCE(memory_type::TEXT, 'unknown'),
            type_count
        ),
        'avg_confidence', ROUND(AVG(confidence)::NUMERIC, 3),
        'avg_importance', ROUND(AVG(importance)::NUMERIC, 3),
        'total_accesses', SUM(access_count),
        'memories_this_week', COUNT(*) FILTER (
            WHERE created_at > NOW() - INTERVAL '7 days' AND archived_at IS NULL
        ),
        'most_accessed', (
            SELECT jsonb_agg(jsonb_build_object(
                'memory_id', memory_id,
                'content', LEFT(content, 50),
                'access_count', access_count
            ))
            FROM (
                SELECT memory_id, content, access_count
                FROM memory_entries
                WHERE user_id = p_user_id AND archived_at IS NULL
                ORDER BY access_count DESC
                LIMIT 5
            ) top
        ),
        'last_updated', MAX(updated_at)
    ) INTO v_result
    FROM (
        SELECT 
            m.*,
            COUNT(*) OVER (PARTITION BY memory_type) AS type_count
        FROM memory_entries m
        WHERE m.user_id = p_user_id
    ) stats;
    
    RETURN COALESCE(v_result, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_memory_stats IS 
'Returns comprehensive statistics about a user''s memory system.
Used by the memory dashboard and analytics endpoints.';


-- ============================================================================
-- FUNCTION 6: CONSOLIDATE SIMILAR MEMORIES
-- ============================================================================
-- Finds and marks similar memories for potential consolidation

CREATE OR REPLACE FUNCTION find_similar_memories(
    p_user_id BIGINT,
    p_similarity_threshold NUMERIC DEFAULT 0.85,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    memory_id_1 BIGINT,
    memory_id_2 BIGINT,
    similarity_score FLOAT,
    content_1 TEXT,
    content_2 TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m1.memory_id AS memory_id_1,
        m2.memory_id AS memory_id_2,
        (1 - (m1.embedding <=> m2.embedding))::FLOAT AS similarity_score,
        m1.content AS content_1,
        m2.content AS content_2
    FROM memory_entries m1
    JOIN memory_entries m2 ON m1.memory_id < m2.memory_id
    WHERE m1.user_id = p_user_id
      AND m2.user_id = p_user_id
      AND m1.archived_at IS NULL
      AND m2.archived_at IS NULL
      AND m1.embedding IS NOT NULL
      AND m2.embedding IS NOT NULL
      AND (1 - (m1.embedding <=> m2.embedding)) > p_similarity_threshold
    ORDER BY (1 - (m1.embedding <=> m2.embedding)) DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION find_similar_memories IS 
'Identifies pairs of similar memories that may be candidates for consolidation.
Used by Nicole''s proactive memory management.';


-- ============================================================================
-- FUNCTION 7: CREATE MEMORY WITH EMBEDDING
-- ============================================================================
-- Convenience function for inserting a memory with all fields

CREATE OR REPLACE FUNCTION create_memory(
    p_user_id BIGINT,
    p_content TEXT,
    p_memory_type memory_type_enum,
    p_embedding vector(1536) DEFAULT NULL,
    p_category TEXT DEFAULT NULL,
    p_confidence NUMERIC DEFAULT 1.0,
    p_importance NUMERIC DEFAULT 0.5,
    p_source_conversation_id BIGINT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'assistant'
)
RETURNS BIGINT AS $$
DECLARE
    v_memory_id BIGINT;
BEGIN
    INSERT INTO memory_entries (
        user_id,
        content,
        memory_type,
        embedding,
        category,
        confidence,
        importance,
        source_conversation_id,
        created_by,
        created_at,
        updated_at
    ) VALUES (
        p_user_id,
        p_content,
        p_memory_type,
        p_embedding,
        p_category,
        p_confidence,
        p_importance,
        p_source_conversation_id,
        p_created_by,
        NOW(),
        NOW()
    )
    RETURNING memory_id INTO v_memory_id;
    
    RETURN v_memory_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_memory IS 
'Convenience function for creating a memory entry with all standard fields.';


-- ============================================================================
-- REFRESH MATERIALIZED VIEWS (for background job)
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_memory_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_active_memories;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_patterns;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_memory_views IS 
'Refreshes materialized views for memory analytics. Run hourly via background job.';


-- ============================================================================
-- INDEXES FOR FUNCTION PERFORMANCE
-- ============================================================================

-- Ensure trigram index exists for similarity searches
CREATE INDEX IF NOT EXISTS idx_memory_content_trgm 
ON memory_entries USING gin (content gin_trgm_ops)
WHERE archived_at IS NULL;

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_memory_content_fts 
ON memory_entries USING gin (to_tsvector('english', content))
WHERE archived_at IS NULL;

-- Composite index for decay queries
CREATE INDEX IF NOT EXISTS idx_memory_decay_candidates
ON memory_entries (user_id, last_accessed, confidence)
WHERE archived_at IS NULL;


-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION search_memories_hybrid TO tsdbadmin;
GRANT EXECUTE ON FUNCTION boost_memory_access TO tsdbadmin;
GRANT EXECUTE ON FUNCTION decay_unused_memories TO tsdbadmin;
GRANT EXECUTE ON FUNCTION get_memory_context TO tsdbadmin;
GRANT EXECUTE ON FUNCTION get_memory_stats TO tsdbadmin;
GRANT EXECUTE ON FUNCTION find_similar_memories TO tsdbadmin;
GRANT EXECUTE ON FUNCTION create_memory TO tsdbadmin;
GRANT EXECUTE ON FUNCTION refresh_memory_views TO tsdbadmin;


-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- 
-- Functions created:
--   ✅ search_memories_hybrid() - Hybrid vector + keyword search
--   ✅ boost_memory_access() - Access tracking and confidence boost
--   ✅ decay_unused_memories() - Scheduled memory decay
--   ✅ get_memory_context() - AI prompt context builder
--   ✅ get_memory_stats() - User memory statistics
--   ✅ find_similar_memories() - Consolidation candidates
--   ✅ create_memory() - Convenience insert function
--   ✅ refresh_memory_views() - Materialized view refresh
--
-- Next steps:
--   1. Apply this migration: psql $TIGER_DATABASE_URL -f 002_memory_functions.sql
--   2. Verify functions: SELECT * FROM search_memories_hybrid(1, NULL, 'test', 5, 0.2);
--   3. Schedule decay_unused_memories() in APScheduler
--
-- ============================================================================


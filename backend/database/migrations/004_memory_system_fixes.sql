-- ═══════════════════════════════════════════════════════════════════════════════
-- Nicole V7 - Memory System Fixes Migration
-- ═══════════════════════════════════════════════════════════════════════════════
-- 
-- This migration adds missing columns and indexes identified during QA review:
-- 1. Add reasoning and bidirectional columns to memory_links
-- 2. Add unique constraint for knowledge_bases
-- 3. Create find_similar_memories function
--
-- Run with: psql $TIGER_DATABASE_URL -f 004_memory_system_fixes.sql
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. ADD MISSING COLUMNS TO memory_links
-- ─────────────────────────────────────────────────────────────────────────────

-- Add reasoning column for storing why relationship was created
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_links' AND column_name = 'reasoning'
    ) THEN
        ALTER TABLE memory_links ADD COLUMN reasoning TEXT;
        COMMENT ON COLUMN memory_links.reasoning IS 'Explanation for why this relationship was created';
    END IF;
END $$;

-- Add bidirectional flag
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_links' AND column_name = 'bidirectional'
    ) THEN
        ALTER TABLE memory_links ADD COLUMN bidirectional BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN memory_links.bidirectional IS 'Whether this relationship applies in both directions';
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. ADD UNIQUE CONSTRAINT FOR knowledge_bases IF MISSING
-- ─────────────────────────────────────────────────────────────────────────────

-- Create unique constraint for user_id + name when parent_id is NULL
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'unique_kb_user_name_root'
    ) THEN
        CREATE UNIQUE INDEX unique_kb_user_name_root 
        ON knowledge_bases (user_id, name) 
        WHERE parent_id IS NULL;
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. CREATE find_similar_memories FUNCTION (if not exists)
-- ─────────────────────────────────────────────────────────────────────────────

-- This function finds pairs of similar memories for consolidation
CREATE OR REPLACE FUNCTION find_similar_memories(
    p_user_id BIGINT,
    p_min_similarity NUMERIC DEFAULT 0.85,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    memory_id_1 BIGINT,
    content_1 TEXT,
    memory_id_2 BIGINT,
    content_2 TEXT,
    similarity_score DOUBLE PRECISION
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH memory_pairs AS (
        SELECT 
            m1.memory_id AS mid1,
            m1.content AS content1,
            m2.memory_id AS mid2,
            m2.content AS content2,
            1 - (m1.embedding <=> m2.embedding) AS similarity
        FROM memory_entries m1
        JOIN memory_entries m2 ON m1.user_id = m2.user_id 
            AND m1.memory_id < m2.memory_id
        WHERE m1.user_id = p_user_id
          AND m1.archived_at IS NULL
          AND m2.archived_at IS NULL
          AND m1.embedding IS NOT NULL
          AND m2.embedding IS NOT NULL
          AND m1.created_at > NOW() - INTERVAL '90 days'
          AND m2.created_at > NOW() - INTERVAL '90 days'
    )
    SELECT 
        mid1 AS memory_id_1,
        content1 AS content_1,
        mid2 AS memory_id_2,
        content2 AS content_2,
        similarity AS similarity_score
    FROM memory_pairs
    WHERE similarity >= p_min_similarity
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION find_similar_memories IS 'Finds pairs of similar memories for potential consolidation';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. CREATE INDEXES FOR BETTER PERFORMANCE
-- ─────────────────────────────────────────────────────────────────────────────

-- Index for finding memories by knowledge_base
CREATE INDEX IF NOT EXISTS idx_memory_kb_id 
ON memory_entries (knowledge_base_id) 
WHERE knowledge_base_id IS NOT NULL AND archived_at IS NULL;

-- Index for finding memories by creation date (for recent queries)
CREATE INDEX IF NOT EXISTS idx_memory_recent 
ON memory_entries (user_id, created_at DESC) 
WHERE archived_at IS NULL;

-- Index for tag lookups by type
CREATE INDEX IF NOT EXISTS idx_tags_by_type 
ON memory_tags (tag_type, user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. VERIFY MIGRATION
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
    v_has_reasoning BOOLEAN;
    v_has_bidirectional BOOLEAN;
    v_has_function BOOLEAN;
BEGIN
    -- Check columns
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_links' AND column_name = 'reasoning'
    ) INTO v_has_reasoning;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_links' AND column_name = 'bidirectional'
    ) INTO v_has_bidirectional;
    
    -- Check function
    SELECT EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'find_similar_memories'
    ) INTO v_has_function;
    
    -- Report
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE 'Migration 004 Verification:';
    RAISE NOTICE '  - memory_links.reasoning: %', CASE WHEN v_has_reasoning THEN 'OK' ELSE 'MISSING' END;
    RAISE NOTICE '  - memory_links.bidirectional: %', CASE WHEN v_has_bidirectional THEN 'OK' ELSE 'MISSING' END;
    RAISE NOTICE '  - find_similar_memories function: %', CASE WHEN v_has_function THEN 'OK' ELSE 'MISSING' END;
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
END $$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- MIGRATION COMPLETE
-- ═══════════════════════════════════════════════════════════════════════════════


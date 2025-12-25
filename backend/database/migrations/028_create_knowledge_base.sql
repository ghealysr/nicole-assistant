-- ============================================================
-- NICOLE V7 KNOWLEDGE BASE SCHEMA
-- Migration: 028_create_knowledge_base.sql
-- Author: Claude for Glen/Nicole V7
-- Date: 2025-12-25
-- 
-- Purpose: Production knowledge base for elite web design
-- documentation that Nicole references when building websites.
-- ============================================================

BEGIN;

-- Enable pg_trgm for fuzzy text search (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- TABLE 1: knowledge_base_files
-- Primary storage for knowledge markdown files
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_base_files (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,                              -- e.g., 'hero-sections', 'shadcn-reference'
    title TEXT NOT NULL,                                    -- Human-readable title
    description TEXT,                                       -- Summary for search results
    category TEXT NOT NULL,                                 -- 'patterns', 'animation', 'components', 'fundamentals', 'core'
    content TEXT NOT NULL,                                  -- Full markdown content
    content_hash TEXT,                                      -- SHA256 hash for change detection
    version INTEGER DEFAULT 1,                              -- Version tracking for updates
    tags TEXT[],                                            -- Array: ['react', 'nextjs', 'accessibility']
    file_size_bytes INTEGER,                                -- Content size in bytes
    word_count INTEGER,                                     -- Word count for estimating read time
    is_active BOOLEAN DEFAULT true,                         -- Soft delete flag
    usage_count INTEGER DEFAULT 0,                          -- Access counter for popularity ranking
    last_accessed TIMESTAMPTZ,                              -- Last access timestamp
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by BIGINT REFERENCES users(user_id)             -- Owner (Glen = user_id 1)
);

COMMENT ON TABLE knowledge_base_files IS 'Stores design knowledge markdown files for Nicole AI reference';
COMMENT ON COLUMN knowledge_base_files.slug IS 'URL-friendly unique identifier';
COMMENT ON COLUMN knowledge_base_files.category IS 'Classification: patterns, animation, components, fundamentals, core';

-- ============================================================
-- TABLE 2: knowledge_base_sections
-- Granular section breakdown for targeted retrieval
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_base_sections (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_id BIGINT NOT NULL REFERENCES knowledge_base_files(id) ON DELETE CASCADE,
    heading TEXT NOT NULL,                                  -- Section heading text
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 6),   -- h1=1, h2=2, etc.
    content TEXT NOT NULL,                                  -- Section content (markdown)
    section_order INTEGER NOT NULL,                         -- Position within file
    word_count INTEGER,                                     -- Section word count
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE knowledge_base_sections IS 'Parsed sections from knowledge files for granular retrieval';

-- ============================================================
-- TABLE 3: knowledge_base_embeddings
-- Vector embeddings for semantic search (Qdrant integration)
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_base_embeddings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_id BIGINT NOT NULL REFERENCES knowledge_base_files(id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES knowledge_base_sections(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,                               -- Text that was embedded (max ~512 tokens)
    chunk_hash TEXT NOT NULL,                               -- SHA256 for deduplication
    qdrant_point_id TEXT UNIQUE,                            -- UUID pointing to Qdrant vector
    embedding_model TEXT DEFAULT 'text-embedding-3-small',  -- OpenAI model used
    embedding_dimensions INTEGER DEFAULT 1536,              -- Vector dimensions
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE knowledge_base_embeddings IS 'Vector embeddings linked to Qdrant for semantic search';

-- ============================================================
-- TABLE 4: knowledge_base_usage_log
-- Access tracking for analytics and popularity ranking
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_base_usage_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_id BIGINT REFERENCES knowledge_base_files(id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES knowledge_base_sections(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(user_id),               -- User who accessed
    query_text TEXT,                                        -- Search query that led to access
    access_method TEXT,                                     -- 'search', 'direct', 'recommended', 'nicole_context'
    was_helpful BOOLEAN,                                    -- User feedback (optional)
    session_id TEXT,                                        -- For grouping related accesses
    accessed_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE knowledge_base_usage_log IS 'Tracks knowledge base access patterns for analytics';

-- ============================================================
-- TABLE 5: knowledge_base_search_cache
-- Cache frequently searched queries for performance
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_base_search_cache (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_text TEXT NOT NULL,                               -- Original query
    query_hash TEXT UNIQUE NOT NULL,                        -- SHA256 of normalized query
    result_file_ids BIGINT[],                               -- Matching file IDs in rank order
    result_section_ids BIGINT[],                            -- Matching section IDs
    search_type TEXT,                                       -- 'semantic', 'fulltext', 'hybrid'
    hit_count INTEGER DEFAULT 1,                            -- Cache hit counter
    last_hit_at TIMESTAMPTZ DEFAULT NOW(),                  -- Last cache hit
    expires_at TIMESTAMPTZ,                                 -- TTL (default 24 hours)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE knowledge_base_search_cache IS 'Caches search results to reduce repeated vector operations';

-- ============================================================
-- INDEXES: Performance optimization
-- ============================================================

-- knowledge_base_files indexes
CREATE INDEX IF NOT EXISTS idx_kb_files_slug ON knowledge_base_files(slug);
CREATE INDEX IF NOT EXISTS idx_kb_files_category ON knowledge_base_files(category);
CREATE INDEX IF NOT EXISTS idx_kb_files_tags ON knowledge_base_files USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_kb_files_active ON knowledge_base_files(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_kb_files_usage ON knowledge_base_files(usage_count DESC, last_accessed DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_kb_files_content_fts ON knowledge_base_files USING GIN(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_kb_files_title_trgm ON knowledge_base_files USING GIN(title gin_trgm_ops);

-- knowledge_base_sections indexes
CREATE INDEX IF NOT EXISTS idx_kb_sections_file_order ON knowledge_base_sections(file_id, section_order);
CREATE INDEX IF NOT EXISTS idx_kb_sections_content_fts ON knowledge_base_sections USING GIN(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_kb_sections_heading_trgm ON knowledge_base_sections USING GIN(heading gin_trgm_ops);

-- knowledge_base_embeddings indexes
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_file ON knowledge_base_embeddings(file_id);
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_section ON knowledge_base_embeddings(section_id);
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_qdrant ON knowledge_base_embeddings(qdrant_point_id);
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_hash ON knowledge_base_embeddings(chunk_hash);

-- knowledge_base_usage_log indexes
CREATE INDEX IF NOT EXISTS idx_kb_usage_file_time ON knowledge_base_usage_log(file_id, accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_usage_user ON knowledge_base_usage_log(user_id, accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_kb_usage_method ON knowledge_base_usage_log(access_method);

-- knowledge_base_search_cache indexes
CREATE INDEX IF NOT EXISTS idx_kb_cache_hash ON knowledge_base_search_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_kb_cache_expires ON knowledge_base_search_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_kb_cache_hits ON knowledge_base_search_cache(hit_count DESC);

-- ============================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================
CREATE OR REPLACE FUNCTION update_kb_files_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_kb_files_updated_at ON knowledge_base_files;
CREATE TRIGGER trigger_update_kb_files_updated_at
    BEFORE UPDATE ON knowledge_base_files
    FOR EACH ROW
    EXECUTE FUNCTION update_kb_files_updated_at();

-- ============================================================
-- HELPER FUNCTION: Cleanup expired cache entries
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_kb_search_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM knowledge_base_search_cache
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_kb_search_cache IS 'Removes expired search cache entries. Call periodically.';

COMMIT;


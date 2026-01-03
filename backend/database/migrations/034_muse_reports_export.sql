-- ============================================================================
-- Migration: 034_muse_reports_export.sql
-- Purpose: Add design report generation and export package support for Muse
-- Author: Anthropic Quality Implementation
-- Date: 2026-01-02
-- ============================================================================

-- ============================================================================
-- 1. MUSE REPORTS TABLE
-- Stores generated design reports and cursor prompts
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    style_guide_id BIGINT REFERENCES muse_style_guides(id) ON DELETE SET NULL,
    
    -- Report Content
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN (
        'design_report',      -- Full design story document
        'cursor_prompt',      -- Implementation brief for Cursor
        'executive_summary',  -- Short summary for stakeholders
        'technical_spec'      -- Developer-focused specification
    )),
    
    -- Versioning (supports revisions)
    version INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Generated Content
    title VARCHAR(500),
    content_markdown TEXT NOT NULL,
    content_html TEXT,  -- Pre-rendered for display
    
    -- Metadata
    word_count INTEGER,
    generation_tokens INTEGER DEFAULT 0,
    generation_model VARCHAR(100),
    generation_duration_ms INTEGER,
    
    -- Export tracking
    download_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure only one latest version per session/type
CREATE UNIQUE INDEX IF NOT EXISTS idx_muse_reports_latest 
ON muse_reports(session_id, report_type) 
WHERE is_latest = TRUE;

CREATE INDEX IF NOT EXISTS idx_muse_reports_session ON muse_reports(session_id);
CREATE INDEX IF NOT EXISTS idx_muse_reports_type ON muse_reports(report_type);

-- ============================================================================
-- 2. MUSE EXPORT PACKAGES TABLE
-- Tracks generated ZIP packages for download
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_export_packages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    
    -- Package Info
    package_name VARCHAR(255) NOT NULL,
    package_format VARCHAR(50) NOT NULL CHECK (package_format IN (
        'full',           -- Complete package with all assets
        'tokens_only',    -- Just design tokens
        'cursor_ready',   -- Optimized for Cursor workflow
        'figma_ready'     -- Optimized for Figma import
    )),
    
    -- Contents manifest
    contents_manifest JSONB NOT NULL DEFAULT '{}',
    -- Example: {"files": ["design-report.md", "cursor-prompt.md", "tokens.json"], 
    --           "images": ["mood-1.png", "mood-2.png"], "total_size_bytes": 1234567}
    
    -- Storage
    file_path TEXT,           -- Local path if stored on disk
    blob_data BYTEA,          -- Direct storage for small packages
    storage_method VARCHAR(50) DEFAULT 'blob',  -- 'blob', 'disk', 's3'
    size_bytes INTEGER,
    
    -- Access
    download_token UUID DEFAULT gen_random_uuid(),  -- For secure downloads
    download_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_packages_session ON muse_export_packages(session_id);
CREATE INDEX IF NOT EXISTS idx_muse_packages_token ON muse_export_packages(download_token);

-- ============================================================================
-- 3. ADD EXPORT FIELDS TO RESEARCH SESSIONS
-- Track export state and preferences
-- ============================================================================

ALTER TABLE muse_research_sessions
ADD COLUMN IF NOT EXISTS export_ready BOOLEAN DEFAULT FALSE;

ALTER TABLE muse_research_sessions
ADD COLUMN IF NOT EXISTS last_export_at TIMESTAMPTZ;

ALTER TABLE muse_research_sessions
ADD COLUMN IF NOT EXISTS export_preferences JSONB DEFAULT '{}';
-- Example: {"include_mood_images": true, "include_inspirations": false, "format": "full"}

-- ============================================================================
-- 4. KNOWLEDGE BASE PATTERN STORAGE
-- For programmatic access to design patterns
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_pattern_library (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    -- Pattern Classification
    category VARCHAR(100) NOT NULL CHECK (category IN (
        'color_palette',
        'font_pairing',
        'layout_template',
        'hero_pattern',
        'section_pattern',
        'animation_pattern'
    )),
    subcategory VARCHAR(100),
    
    -- Pattern Data
    name VARCHAR(255) NOT NULL,
    description TEXT,
    pattern_data JSONB NOT NULL,
    
    -- Usage Analytics
    usage_count INTEGER DEFAULT 0,
    success_rating NUMERIC(3,2),  -- 0.00 to 1.00
    
    -- Metadata
    source VARCHAR(100),  -- 'curated', 'learned', 'user_submitted'
    tags TEXT[],
    
    -- Vector for semantic search
    embedding vector(1536),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_patterns_category ON muse_pattern_library(category);
CREATE INDEX IF NOT EXISTS idx_muse_patterns_tags ON muse_pattern_library USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_muse_patterns_embedding ON muse_pattern_library 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- 5. HELPER FUNCTIONS
-- ============================================================================

-- Function to get the latest report of a specific type
CREATE OR REPLACE FUNCTION get_latest_report(
    p_session_id BIGINT,
    p_report_type VARCHAR(50)
) RETURNS TABLE (
    id BIGINT,
    version INTEGER,
    content_markdown TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT r.id, r.version, r.content_markdown, r.created_at
    FROM muse_reports r
    WHERE r.session_id = p_session_id 
      AND r.report_type = p_report_type
      AND r.is_latest = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to create a new report version
CREATE OR REPLACE FUNCTION create_report_version(
    p_session_id BIGINT,
    p_report_type VARCHAR(50),
    p_content TEXT,
    p_title VARCHAR(500) DEFAULT NULL,
    p_model VARCHAR(100) DEFAULT NULL,
    p_tokens INTEGER DEFAULT 0
) RETURNS BIGINT AS $$
DECLARE
    v_next_version INTEGER;
    v_new_id BIGINT;
BEGIN
    -- Get next version number
    SELECT COALESCE(MAX(version), 0) + 1 INTO v_next_version
    FROM muse_reports
    WHERE session_id = p_session_id AND report_type = p_report_type;
    
    -- Mark old versions as not latest
    UPDATE muse_reports 
    SET is_latest = FALSE, updated_at = NOW()
    WHERE session_id = p_session_id 
      AND report_type = p_report_type 
      AND is_latest = TRUE;
    
    -- Insert new version
    INSERT INTO muse_reports (
        session_id, report_type, version, is_latest,
        title, content_markdown, word_count,
        generation_tokens, generation_model
    ) VALUES (
        p_session_id, p_report_type, v_next_version, TRUE,
        p_title, p_content, array_length(regexp_split_to_array(p_content, '\s+'), 1),
        p_tokens, p_model
    ) RETURNING id INTO v_new_id;
    
    RETURN v_new_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 6. GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON muse_reports TO tsdbadmin;
GRANT ALL PRIVILEGES ON muse_export_packages TO tsdbadmin;
GRANT ALL PRIVILEGES ON muse_pattern_library TO tsdbadmin;
GRANT EXECUTE ON FUNCTION get_latest_report TO tsdbadmin;
GRANT EXECUTE ON FUNCTION create_report_version TO tsdbadmin;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================


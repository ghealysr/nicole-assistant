-- ============================================================================
-- Migration: 033_muse_ab_testing.sql
-- Purpose: Add A/B testing and analytics tracking for Muse mood board selections
-- Author: Nicole V7 Architecture
-- Date: 2025-12-26
-- Updated: 2025-12-27 (Fixed column structure)
-- ============================================================================

-- ============================================================================
-- 1. MOOD BOARD ANALYTICS (Event-based tracking)
-- Simple event tracking for impressions and selections
-- ============================================================================

DROP TABLE IF EXISTS muse_moodboard_analytics CASCADE;

CREATE TABLE muse_moodboard_analytics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    moodboard_id BIGINT REFERENCES muse_moodboards(id) ON DELETE CASCADE,
    
    -- Event type: 'impression' or 'selection'
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('impression', 'selection')),
    
    -- Flexible event data (view duration, user feedback, etc.)
    event_data JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for querying
CREATE INDEX idx_muse_analytics_session ON muse_moodboard_analytics(session_id);
CREATE INDEX idx_muse_analytics_moodboard ON muse_moodboard_analytics(moodboard_id);
CREATE INDEX idx_muse_analytics_event_type ON muse_moodboard_analytics(event_type);

-- ============================================================================
-- 2. MOOD BOARD PREVIEW IMAGES
-- Store Imagen-generated preview images
-- ============================================================================

ALTER TABLE muse_moodboards 
ADD COLUMN IF NOT EXISTS preview_image_generated TEXT;  -- Base64 Imagen preview

ALTER TABLE muse_moodboards 
ADD COLUMN IF NOT EXISTS preview_generation_prompt TEXT;

ALTER TABLE muse_moodboards 
ADD COLUMN IF NOT EXISTS preview_generation_tokens INTEGER DEFAULT 0;

-- Selection count for A/B testing
ALTER TABLE muse_moodboards 
ADD COLUMN IF NOT EXISTS selection_count INTEGER DEFAULT 0;

-- ============================================================================
-- 3. STYLE GUIDE EXPORTS
-- Track export history by format
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_style_guide_exports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    style_guide_id BIGINT REFERENCES muse_style_guides(id) ON DELETE CASCADE,
    
    export_format VARCHAR(50) NOT NULL CHECK (export_format IN (
        'figma_tokens',
        'css_variables', 
        'tailwind_config',
        'design_tokens_json'
    )),
    export_data TEXT NOT NULL,
    exported_by_user_id TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_exports_style_guide 
ON muse_style_guide_exports(style_guide_id);

CREATE INDEX IF NOT EXISTS idx_muse_exports_format 
ON muse_style_guide_exports(export_format);

-- Cache last export timestamps on style guides
ALTER TABLE muse_style_guides
ADD COLUMN IF NOT EXISTS last_export_figma_tokens TIMESTAMPTZ;

ALTER TABLE muse_style_guides
ADD COLUMN IF NOT EXISTS last_export_css_variables TIMESTAMPTZ;

ALTER TABLE muse_style_guides
ADD COLUMN IF NOT EXISTS last_export_tailwind_config TIMESTAMPTZ;

-- ============================================================================
-- 4. UPDATE SESSION STATUS CONSTRAINT
-- Add streaming and new status values
-- ============================================================================

ALTER TABLE muse_research_sessions 
DROP CONSTRAINT IF EXISTS muse_research_sessions_session_status_check;

ALTER TABLE muse_research_sessions 
ADD CONSTRAINT muse_research_sessions_session_status_check CHECK (session_status IN (
    'intake', 'planning', 'analyzing_brief', 'analyzing_inspiration', 
    'awaiting_questions', 'awaiting_answers', 'web_research', 'research_complete',
    'generating_moodboards', 'streaming_moodboards', 'awaiting_selection', 
    'generating_design', 'awaiting_approval', 'approved', 'revising_design',
    'handed_off', 'failed', 'cancelled'
));

-- ============================================================================
-- 5. ANALYTICS VIEWS (for reporting)
-- ============================================================================

CREATE OR REPLACE VIEW muse_selection_patterns AS
SELECT 
    mb.aesthetic_movement,
    COUNT(DISTINCT CASE WHEN ma.event_type = 'impression' THEN ma.id END) as total_impressions,
    COUNT(DISTINCT CASE WHEN ma.event_type = 'selection' THEN ma.id END) as total_selections,
    ROUND(
        COUNT(DISTINCT CASE WHEN ma.event_type = 'selection' THEN ma.id END)::NUMERIC /
        NULLIF(COUNT(DISTINCT CASE WHEN ma.event_type = 'impression' THEN ma.id END), 0) * 100,
        1
    ) as conversion_rate
FROM muse_moodboards mb
LEFT JOIN muse_moodboard_analytics ma ON ma.moodboard_id = mb.id
WHERE mb.created_at > NOW() - INTERVAL '90 days'
GROUP BY mb.aesthetic_movement
HAVING COUNT(DISTINCT CASE WHEN ma.event_type = 'impression' THEN ma.id END) >= 3
ORDER BY total_selections DESC;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tsdbadmin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tsdbadmin;
GRANT SELECT ON muse_selection_patterns TO tsdbadmin;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- ============================================================================
-- FAZ CODE ENHANCEMENTS - Phase 6 Implementation
-- Migration: 022
-- Date: December 20, 2025
-- 
-- This migration adds:
-- 1. Screenshot storage for QA
-- 2. Connection tracking for WebSocket analytics
-- 3. Deployment history tracking
-- ============================================================================

-- ============================================================================
-- TABLE: faz_screenshots
-- Stores project screenshots from QA and research agents
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_screenshots (
    screenshot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- Screenshot type
    screenshot_type VARCHAR(30) NOT NULL CHECK (screenshot_type IN (
        'qa_desktop',       -- QA agent desktop screenshot
        'qa_tablet',        -- QA agent tablet screenshot
        'qa_mobile',        -- QA agent mobile screenshot
        'research_inspiration', -- Research agent competitor screenshot
        'preview',          -- Live preview screenshot
        'deployment'        -- Post-deployment screenshot
    )),
    
    -- Content (base64 encoded or URL)
    image_data TEXT,        -- Base64 encoded image data
    image_url VARCHAR(500), -- Or URL if stored externally (Cloudinary, S3)
    
    -- Metadata
    viewport_width INTEGER,
    viewport_height INTEGER,
    source_url VARCHAR(500),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    captured_by VARCHAR(50), -- Agent or 'user'
    
    -- For research agent - link to inspiration site
    inspiration_notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_screenshots_project ON faz_screenshots(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_screenshots_type ON faz_screenshots(screenshot_type);

-- ============================================================================
-- TABLE: faz_deployments
-- Tracks deployment history
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_deployments (
    deployment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- Deployment info
    deployment_type VARCHAR(20) NOT NULL CHECK (deployment_type IN ('preview', 'production')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'building', 'deploying', 'success', 'failed', 'cancelled'
    )),
    
    -- GitHub info
    github_repo VARCHAR(200),
    github_commit_sha VARCHAR(64),
    github_branch VARCHAR(100) DEFAULT 'main',
    
    -- Vercel info
    vercel_deployment_id VARCHAR(100),
    vercel_deployment_url VARCHAR(500),
    vercel_production_url VARCHAR(500),
    
    -- Metrics
    build_duration_ms INTEGER,
    deploy_duration_ms INTEGER,
    files_deployed INTEGER,
    
    -- Error tracking
    error_message TEXT,
    error_stage VARCHAR(50), -- 'github', 'vercel_create', 'vercel_deploy'
    
    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_deployments_project ON faz_deployments(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_deployments_status ON faz_deployments(status);

-- ============================================================================
-- TABLE: faz_ws_analytics
-- Tracks WebSocket connection analytics
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_ws_analytics (
    analytics_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    
    -- Session info
    session_id UUID,
    connection_started TIMESTAMPTZ NOT NULL,
    connection_ended TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Activity metrics
    messages_sent INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    files_watched INTEGER DEFAULT 0,
    activities_streamed INTEGER DEFAULT 0,
    
    -- Connection quality
    ping_count INTEGER DEFAULT 0,
    avg_latency_ms INTEGER,
    reconnect_count INTEGER DEFAULT 0,
    
    -- Device info (optional)
    user_agent TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_ws_analytics_project ON faz_ws_analytics(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_ws_analytics_user ON faz_ws_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_faz_ws_analytics_time ON faz_ws_analytics(connection_started DESC);

-- ============================================================================
-- ALTER faz_projects: Add deployment tracking fields
-- ============================================================================
ALTER TABLE faz_projects 
ADD COLUMN IF NOT EXISTS deployment_count INTEGER DEFAULT 0;

ALTER TABLE faz_projects 
ADD COLUMN IF NOT EXISTS last_deployed_at TIMESTAMPTZ;

ALTER TABLE faz_projects 
ADD COLUMN IF NOT EXISTS status_history JSONB DEFAULT '[]'::jsonb;

-- ============================================================================
-- FUNCTION: Increment deployment count
-- ============================================================================
CREATE OR REPLACE FUNCTION faz_increment_deployment_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'success' THEN
        UPDATE faz_projects 
        SET deployment_count = deployment_count + 1,
            last_deployed_at = NOW(),
            updated_at = NOW()
        WHERE project_id = NEW.project_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_faz_deployment_count ON faz_deployments;
CREATE TRIGGER trg_faz_deployment_count
    AFTER UPDATE OF status ON faz_deployments
    FOR EACH ROW
    EXECUTE FUNCTION faz_increment_deployment_count();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE faz_screenshots IS 'Stores screenshots from QA, research, and deployment';
COMMENT ON TABLE faz_deployments IS 'Tracks deployment history with GitHub and Vercel info';
COMMENT ON TABLE faz_ws_analytics IS 'WebSocket connection analytics for monitoring';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration 022 complete: faz_screenshots, faz_deployments, faz_ws_analytics created';
END $$;


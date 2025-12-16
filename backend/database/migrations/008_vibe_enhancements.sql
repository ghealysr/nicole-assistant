-- ============================================================================
-- Migration: 008_vibe_enhancements.sql
-- Description: Vibe Dashboard V3.0 - Structured intake, iterations, QA scores
-- Author: AlphaWave Architecture
-- Date: December 15, 2025
-- 
-- SAFETY: This migration is ADDITIVE ONLY
-- - Creates 4 new tables
-- - Adds columns to vibe_projects (with defaults)
-- - No data modification
-- - Fully reversible
-- ============================================================================

-- Ensure we're in the right database
\c tsdb;

-- ============================================================================
-- TABLE 1: vibe_iterations
-- Purpose: Track Glen's feedback and fix cycles
-- ============================================================================
CREATE TABLE IF NOT EXISTS vibe_iterations (
    iteration_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id) ON DELETE CASCADE,
    iteration_number INTEGER NOT NULL DEFAULT 1,
    
    -- Type of iteration
    iteration_type TEXT NOT NULL CHECK (iteration_type IN ('bug_fix', 'design_change', 'feature_add')),
    
    -- Glen's feedback
    feedback TEXT NOT NULL,
    feedback_category TEXT CHECK (feedback_category IN ('visual', 'functional', 'content', 'performance', NULL)),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    
    -- What was affected/changed
    affected_pages TEXT[],
    files_affected TEXT[],
    changes_summary TEXT,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved', 'wont_fix')),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    
    -- Ensure unique iteration numbers per project
    CONSTRAINT unique_iteration_number UNIQUE (project_id, iteration_number)
);

-- Indexes for performance
CREATE INDEX idx_vibe_iterations_project ON vibe_iterations(project_id);
CREATE INDEX idx_vibe_iterations_status ON vibe_iterations(status);
CREATE INDEX idx_vibe_iterations_created ON vibe_iterations(created_at DESC);

COMMENT ON TABLE vibe_iterations IS 'Tracks feedback/fix cycles for Vibe projects';
COMMENT ON COLUMN vibe_iterations.iteration_type IS 'bug_fix: Fix broken functionality, design_change: Visual/layout changes, feature_add: New functionality';
COMMENT ON COLUMN vibe_iterations.priority IS 'low: Nice to have, medium: Should fix, high: Important, critical: Blocking';


-- ============================================================================
-- TABLE 2: vibe_qa_scores
-- Purpose: Store quality metrics per build/iteration
-- ============================================================================
CREATE TABLE IF NOT EXISTS vibe_qa_scores (
    score_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id) ON DELETE CASCADE,
    iteration_id INTEGER REFERENCES vibe_iterations(iteration_id) ON DELETE SET NULL,
    
    -- Lighthouse scores (0-100, from PageSpeed Insights API)
    lighthouse_performance INTEGER CHECK (lighthouse_performance BETWEEN 0 AND 100),
    lighthouse_accessibility INTEGER CHECK (lighthouse_accessibility BETWEEN 0 AND 100),
    lighthouse_best_practices INTEGER CHECK (lighthouse_best_practices BETWEEN 0 AND 100),
    lighthouse_seo INTEGER CHECK (lighthouse_seo BETWEEN 0 AND 100),
    
    -- Core Web Vitals (from Lighthouse)
    lcp_score DECIMAL(10,2),  -- Largest Contentful Paint (seconds)
    fid_score DECIMAL(10,2),  -- First Input Delay (milliseconds)
    cls_score DECIMAL(10,4),  -- Cumulative Layout Shift (score)
    
    -- Accessibility (from axe-core via Puppeteer)
    accessibility_violations INTEGER DEFAULT 0,
    accessibility_warnings INTEGER DEFAULT 0,
    accessibility_passes INTEGER DEFAULT 0,
    
    -- Tests (Jest + React Testing Library)
    tests_total INTEGER DEFAULT 0,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    test_coverage_percent DECIMAL(5,2),
    
    -- Screenshots (Cloudinary URLs)
    screenshot_mobile TEXT,
    screenshot_tablet TEXT,
    screenshot_desktop TEXT,
    
    -- Raw data (for detailed analysis)
    lighthouse_raw JSONB,
    axe_raw JSONB,
    test_results_raw JSONB,
    
    -- Computed quality gate status
    all_passing BOOLEAN DEFAULT FALSE,
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_vibe_qa_scores_project ON vibe_qa_scores(project_id);
CREATE INDEX idx_vibe_qa_scores_iteration ON vibe_qa_scores(iteration_id);
CREATE INDEX idx_vibe_qa_scores_created ON vibe_qa_scores(created_at DESC);
CREATE INDEX idx_vibe_qa_scores_passing ON vibe_qa_scores(all_passing);

COMMENT ON TABLE vibe_qa_scores IS 'Quality metrics from Lighthouse, axe-core, and tests';
COMMENT ON COLUMN vibe_qa_scores.lighthouse_performance IS 'PageSpeed Insights performance score (0-100)';
COMMENT ON COLUMN vibe_qa_scores.all_passing IS 'TRUE if all quality gates pass (perf >= 90, a11y >= 90, no violations, all tests pass)';


-- ============================================================================
-- TABLE 3: vibe_uploads
-- Purpose: Store uploaded files during intake (logos, images, docs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vibe_uploads (
    upload_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id) ON DELETE CASCADE,
    
    -- File classification
    file_type TEXT NOT NULL CHECK (file_type IN ('image', 'document', 'logo', 'inspiration', 'brand_asset', 'other')),
    
    -- File metadata
    original_filename TEXT NOT NULL,
    storage_url TEXT NOT NULL,  -- Cloudinary URL
    file_size_bytes INTEGER,
    mime_type TEXT,
    
    -- Optional description from Glen
    description TEXT,
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_vibe_uploads_project ON vibe_uploads(project_id);
CREATE INDEX idx_vibe_uploads_type ON vibe_uploads(file_type);

COMMENT ON TABLE vibe_uploads IS 'Files uploaded during intake (logos, brand assets, reference docs)';


-- ============================================================================
-- TABLE 4: vibe_competitor_sites
-- Purpose: Track competitor URLs for research during intake
-- ============================================================================
CREATE TABLE IF NOT EXISTS vibe_competitor_sites (
    competitor_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id) ON DELETE CASCADE,
    
    -- Competitor info
    url TEXT NOT NULL,
    screenshot_url TEXT,  -- Captured via Puppeteer MCP
    notes TEXT,
    
    -- Timestamps
    captured_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_vibe_competitors_project ON vibe_competitor_sites(project_id);

COMMENT ON TABLE vibe_competitor_sites IS 'Competitor URLs analyzed during intake for design inspiration';


-- ============================================================================
-- ALTER: vibe_projects
-- Purpose: Add new columns for enhanced workflow
-- ============================================================================

-- Iteration tracking
ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS iteration_count INTEGER DEFAULT 0;

ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS max_iterations INTEGER DEFAULT 5;

-- Architecture approval tracking
ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS architecture_approved_at TIMESTAMPTZ;

ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS architecture_approved_by TEXT;

ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS architecture_feedback TEXT;

-- Glen review tracking
ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS glen_approved_at TIMESTAMPTZ;

ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS glen_approved_by TEXT;

-- Preview URL (Vercel preview deployment)
ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS preview_url TEXT;

-- Structured intake form data (JSONB for flexibility)
ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS intake_form JSONB;

-- Build strategy tracking
ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS build_strategy TEXT DEFAULT 'chunked' CHECK (build_strategy IN ('chunked', 'monolithic'));

ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS chunks_completed INTEGER DEFAULT 0;

ALTER TABLE vibe_projects 
ADD COLUMN IF NOT EXISTS total_chunks INTEGER DEFAULT 0;

COMMENT ON COLUMN vibe_projects.iteration_count IS 'Number of feedback iterations completed';
COMMENT ON COLUMN vibe_projects.max_iterations IS 'Maximum allowed iterations before forcing approval';
COMMENT ON COLUMN vibe_projects.preview_url IS 'Vercel preview URL for Glen review';
COMMENT ON COLUMN vibe_projects.intake_form IS 'Structured intake form data (business info, design prefs, technical reqs)';
COMMENT ON COLUMN vibe_projects.build_strategy IS 'chunked: Build in phases with tests, monolithic: Generate all at once';


-- ============================================================================
-- INDEXES for existing tables (if not already present)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_vibe_projects_status ON vibe_projects(status);
CREATE INDEX IF NOT EXISTS idx_vibe_projects_user_status ON vibe_projects(user_id, status);
CREATE INDEX IF NOT EXISTS idx_vibe_files_project ON vibe_files(project_id);
CREATE INDEX IF NOT EXISTS idx_vibe_activities_project_created ON vibe_activities(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vibe_inspirations_project ON vibe_inspirations(project_id);
CREATE INDEX IF NOT EXISTS idx_vibe_lessons_project ON vibe_lessons(project_id);


-- ============================================================================
-- VALIDATION: Ensure all tables exist
-- ============================================================================
DO $$
BEGIN
    -- Check if all new tables were created
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'vibe_iterations') THEN
        RAISE EXCEPTION 'Migration failed: vibe_iterations table not created';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'vibe_qa_scores') THEN
        RAISE EXCEPTION 'Migration failed: vibe_qa_scores table not created';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'vibe_uploads') THEN
        RAISE EXCEPTION 'Migration failed: vibe_uploads table not created';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'vibe_competitor_sites') THEN
        RAISE EXCEPTION 'Migration failed: vibe_competitor_sites table not created';
    END IF;
    
    RAISE NOTICE 'Migration 008_vibe_enhancements completed successfully!';
    RAISE NOTICE '  - Created 4 new tables';
    RAISE NOTICE '  - Added 12 new columns to vibe_projects';
    RAISE NOTICE '  - Created 12 new indexes';
    RAISE NOTICE 'Vibe Dashboard V3.0 database ready!';
END $$;


-- ============================================================================
-- ROLLBACK SCRIPT (for reference - DO NOT RUN unless reverting)
-- ============================================================================
/*
-- To rollback this migration:

DROP TABLE IF EXISTS vibe_competitor_sites CASCADE;
DROP TABLE IF EXISTS vibe_uploads CASCADE;
DROP TABLE IF EXISTS vibe_qa_scores CASCADE;
DROP TABLE IF EXISTS vibe_iterations CASCADE;

ALTER TABLE vibe_projects DROP COLUMN IF EXISTS iteration_count;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS max_iterations;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS architecture_approved_at;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS architecture_approved_by;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS architecture_feedback;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS glen_approved_at;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS glen_approved_by;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS preview_url;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS intake_form;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS build_strategy;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS chunks_completed;
ALTER TABLE vibe_projects DROP COLUMN IF EXISTS total_chunks;
*/

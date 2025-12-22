-- ============================================================================
-- VIBE SCHEMA IMPROVEMENTS
-- Migration: 009
-- 
-- Fixes:
-- - Add composite index for file lookups
-- - Add unique constraint on file paths per project
-- - Improve API cost precision
-- - Add activity tracking table
-- - Add proper timestamps and defaults
-- ============================================================================

-- 1. Add composite unique constraint on vibe_files
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'vibe_files_project_path_unique'
    ) THEN
        ALTER TABLE vibe_files 
        ADD CONSTRAINT vibe_files_project_path_unique 
        UNIQUE (project_id, file_path);
    END IF;
EXCEPTION
    WHEN duplicate_table THEN NULL;
END $$;

-- 2. Add composite index if not exists (for efficient lookups)
CREATE INDEX IF NOT EXISTS idx_vibe_files_project_path 
ON vibe_files(project_id, file_path);

-- 3. Add index on lessons for efficient retrieval
CREATE INDEX IF NOT EXISTS idx_vibe_lessons_project_type_category 
ON vibe_lessons(project_type, lesson_category);

CREATE INDEX IF NOT EXISTS idx_vibe_lessons_times_applied 
ON vibe_lessons(times_applied DESC);

-- 4. Increase API cost precision (support micro-dollar tracking)
DO $$
BEGIN
    -- Check current column type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vibe_projects' 
        AND column_name = 'api_cost'
        AND numeric_precision < 12
    ) THEN
        ALTER TABLE vibe_projects 
        ALTER COLUMN api_cost TYPE DECIMAL(12,8);
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'API cost column update skipped: %', SQLERRM;
END $$;

-- 5. Create vibe_activities table for detailed activity logging
CREATE TABLE IF NOT EXISTS vibe_activities (
    activity_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES vibe_projects(project_id) ON DELETE CASCADE,
    
    -- Activity details
    activity_type TEXT NOT NULL CHECK (activity_type IN (
        'project_created', 'intake_message', 'brief_extracted',
        'architecture_generated', 'build_started', 'build_completed',
        'qa_passed', 'qa_failed', 'review_approved', 'review_rejected',
        'manually_approved', 'deployment_started', 'deployment_completed',
        'status_changed', 'file_updated', 'error'
    )),
    
    -- Content
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Actor (null = system)
    user_id BIGINT,
    agent_name TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Activity indexes
CREATE INDEX IF NOT EXISTS idx_vibe_activities_project 
ON vibe_activities(project_id);

CREATE INDEX IF NOT EXISTS idx_vibe_activities_created 
ON vibe_activities(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vibe_activities_type 
ON vibe_activities(activity_type);

-- 6. Add completed_at column if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vibe_projects' 
        AND column_name = 'completed_at'
    ) THEN
        ALTER TABLE vibe_projects 
        ADD COLUMN completed_at TIMESTAMPTZ;
    END IF;
END $$;

-- 7. Add trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_vibe_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to vibe_projects
DROP TRIGGER IF EXISTS trigger_vibe_projects_updated_at ON vibe_projects;
CREATE TRIGGER trigger_vibe_projects_updated_at
    BEFORE UPDATE ON vibe_projects
    FOR EACH ROW
    EXECUTE FUNCTION update_vibe_updated_at();

-- Apply trigger to vibe_files
DROP TRIGGER IF EXISTS trigger_vibe_files_updated_at ON vibe_files;
CREATE TRIGGER trigger_vibe_files_updated_at
    BEFORE UPDATE ON vibe_files
    FOR EACH ROW
    EXECUTE FUNCTION update_vibe_updated_at();

-- 8. Set completed_at automatically when status becomes 'deployed' or 'delivered'
CREATE OR REPLACE FUNCTION set_vibe_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('deployed', 'delivered') AND OLD.status NOT IN ('deployed', 'delivered') THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_vibe_set_completed_at ON vibe_projects;
CREATE TRIGGER trigger_vibe_set_completed_at
    BEFORE UPDATE ON vibe_projects
    FOR EACH ROW
    EXECUTE FUNCTION set_vibe_completed_at();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE vibe_activities IS 'Audit log of all project activities for timeline display';
COMMENT ON COLUMN vibe_activities.activity_type IS 'Type of activity (enum)';
COMMENT ON COLUMN vibe_activities.metadata IS 'Additional context in JSON format';
COMMENT ON COLUMN vibe_activities.agent_name IS 'Name of AI agent that performed the action';

COMMENT ON TRIGGER trigger_vibe_projects_updated_at ON vibe_projects IS 'Auto-update updated_at on row changes';
COMMENT ON TRIGGER trigger_vibe_set_completed_at ON vibe_projects IS 'Auto-set completed_at when project reaches final status';




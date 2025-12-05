-- ═══════════════════════════════════════════════════════════════════════════════
-- Nicole V7 - Skill Runs Table Migration
-- 
-- PURPOSE:
--   Creates the skill_runs table to persist skill execution telemetry for:
--   - Execution history and audit trail
--   - Performance monitoring and optimization
--   - Error tracking and debugging
--   - Usage analytics and reporting
--
-- SCHEMA:
--   skill_runs stores individual execution records with:
--   - Unique run identifier (UUID)
--   - Skill and user context
--   - Execution timestamps and duration
--   - Status and output/error information
--   - Environment metadata
--
-- INDEXES:
--   - By skill_id for skill-specific queries
--   - By user_id for user-specific history
--   - By created_at (DESC) for recent queries
--   - By status for filtering
--
-- USAGE:
--   psql "$TIGER_DATABASE_URL" -f database/migrations/006_skill_runs.sql
--
-- Author: Nicole V7 Skills System
-- Date: December 5, 2025
-- ═══════════════════════════════════════════════════════════════════════════════

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create skill_runs table
CREATE TABLE IF NOT EXISTS skill_runs (
    -- Primary key
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Skill identification
    skill_id TEXT NOT NULL,
    
    -- User context
    user_id INTEGER NOT NULL,
    conversation_id INTEGER,
    
    -- Execution status
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'timeout', 'cancelled')),
    
    -- Environment context
    environment TEXT DEFAULT 'production',
    
    -- Timing information
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_seconds NUMERIC(10, 3),
    
    -- Output and error tracking
    log_path TEXT,
    output_preview TEXT,  -- First 500 chars of output
    error_message TEXT,
    
    -- Metadata for extensibility
    metadata JSONB DEFAULT '{}',
    
    -- Audit timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add table comment
COMMENT ON TABLE skill_runs IS 'Stores execution history for Nicole skill runs';

-- Add column comments
COMMENT ON COLUMN skill_runs.run_id IS 'Unique identifier for this execution';
COMMENT ON COLUMN skill_runs.skill_id IS 'ID of the skill that was executed';
COMMENT ON COLUMN skill_runs.user_id IS 'Tiger user ID who triggered the execution';
COMMENT ON COLUMN skill_runs.conversation_id IS 'Associated conversation (if any)';
COMMENT ON COLUMN skill_runs.status IS 'Execution result: success, failed, timeout, cancelled';
COMMENT ON COLUMN skill_runs.environment IS 'Execution environment (production, development, etc.)';
COMMENT ON COLUMN skill_runs.started_at IS 'When execution started';
COMMENT ON COLUMN skill_runs.finished_at IS 'When execution completed';
COMMENT ON COLUMN skill_runs.duration_seconds IS 'Total execution time';
COMMENT ON COLUMN skill_runs.log_path IS 'Path to execution log file';
COMMENT ON COLUMN skill_runs.output_preview IS 'First 500 chars of skill output';
COMMENT ON COLUMN skill_runs.error_message IS 'Error message if execution failed';
COMMENT ON COLUMN skill_runs.metadata IS 'Additional execution metadata (JSON)';

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_skill_runs_skill_id ON skill_runs (skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_runs_user_id ON skill_runs (user_id);
CREATE INDEX IF NOT EXISTS idx_skill_runs_created_at ON skill_runs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_runs_status ON skill_runs (status);
CREATE INDEX IF NOT EXISTS idx_skill_runs_skill_user ON skill_runs (skill_id, user_id);

-- Grant permissions (adjust role names as needed for your setup)
-- GRANT SELECT, INSERT ON skill_runs TO nicole_api;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO nicole_api;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 006_skill_runs completed successfully';
END $$;


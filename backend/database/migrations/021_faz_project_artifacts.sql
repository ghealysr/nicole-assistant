-- ============================================================================
-- FAZ PROJECT ARTIFACTS - Document Storage for Interactive Pipeline
-- Migration: 021
-- Date: December 20, 2025
-- 
-- This migration adds:
-- 1. faz_project_artifacts table for storing pipeline documents
-- 2. Extended status values for interactive pipeline mode
-- 3. Phase tracking for approval gates
-- ============================================================================

-- ============================================================================
-- TABLE: faz_project_artifacts
-- Stores generated documents like PROJECT_BRIEF.md, RESEARCH.md, PLAN.md
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_project_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- Artifact identification
    artifact_type VARCHAR(50) NOT NULL CHECK (artifact_type IN (
        'project_brief',    -- Nicole's understanding of the project
        'research',         -- Research agent findings
        'architecture',     -- Planning agent output
        'design_system',    -- Design agent tokens
        'qa_report',        -- QA agent review
        'review_summary',   -- Final review
        'custom'            -- User-added documents
    )),
    
    -- Content
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    content_format VARCHAR(20) DEFAULT 'markdown' CHECK (content_format IN (
        'markdown', 'json', 'yaml', 'text'
    )),
    
    -- Metadata
    generated_by VARCHAR(50),  -- Agent name
    version INTEGER DEFAULT 1,
    is_approved BOOLEAN DEFAULT false,
    approved_at TIMESTAMPTZ,
    approved_by BIGINT REFERENCES users(user_id),
    
    -- For user feedback
    user_feedback TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Only one active version per type per project
    CONSTRAINT faz_artifacts_unique_type UNIQUE (project_id, artifact_type, version)
);

CREATE INDEX IF NOT EXISTS idx_faz_artifacts_project ON faz_project_artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_type ON faz_project_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_approved ON faz_project_artifacts(is_approved) WHERE is_approved = true;

-- ============================================================================
-- ALTER faz_projects: Add interactive pipeline fields
-- ============================================================================

-- Add new columns for interactive mode
ALTER TABLE faz_projects 
ADD COLUMN IF NOT EXISTS pipeline_mode VARCHAR(20) DEFAULT 'auto' CHECK (pipeline_mode IN ('auto', 'interactive'));

ALTER TABLE faz_projects
ADD COLUMN IF NOT EXISTS current_phase VARCHAR(30);

ALTER TABLE faz_projects
ADD COLUMN IF NOT EXISTS awaiting_approval_for VARCHAR(50);

ALTER TABLE faz_projects
ADD COLUMN IF NOT EXISTS last_gate_reached_at TIMESTAMPTZ;

-- Drop existing constraint and recreate with new values
-- Note: This requires the column to be empty of invalid values first
DO $$
BEGIN
    -- Check if constraint exists before trying to drop
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'faz_projects_status_check' 
        AND table_name = 'faz_projects'
    ) THEN
        ALTER TABLE faz_projects DROP CONSTRAINT faz_projects_status_check;
    END IF;
EXCEPTION WHEN OTHERS THEN
    -- Constraint might have a different name, try pattern match
    NULL;
END $$;

-- Add updated constraint with interactive statuses
ALTER TABLE faz_projects 
ADD CONSTRAINT faz_projects_status_check CHECK (status IN (
    -- Original statuses
    'intake', 'planning', 'researching', 'designing', 'building', 
    'qa', 'review', 'approved', 'deploying', 'deployed', 'delivered', 'archived',
    -- Interactive pipeline statuses
    'awaiting_confirm',         -- Waiting for user to confirm Nicole's understanding
    'awaiting_research_review', -- Waiting for user to review research
    'awaiting_plan_approval',   -- Waiting for user to approve architecture
    'awaiting_design_approval', -- Waiting for user to approve design
    'awaiting_qa_approval',     -- Waiting for user to review QA results
    'awaiting_final_approval',  -- Waiting for final review approval
    -- Error/pause states
    'paused', 'failed', 'cancelled'
));

-- ============================================================================
-- TABLE: faz_phase_history
-- Tracks phase transitions for audit and debugging
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_phase_history (
    history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- Phase transition
    from_phase VARCHAR(50),
    to_phase VARCHAR(50) NOT NULL,
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    
    -- Context
    triggered_by VARCHAR(50),  -- 'system', 'user', agent name
    trigger_action VARCHAR(50), -- 'approve', 'reject', 'auto', 'timeout'
    notes TEXT,
    
    -- Metrics
    phase_duration_ms INTEGER,
    tokens_used INTEGER DEFAULT 0,
    cost_cents NUMERIC(10,4) DEFAULT 0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_phase_history_project ON faz_phase_history(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_phase_history_time ON faz_phase_history(created_at DESC);

-- ============================================================================
-- UPDATE agent registry with correct model
-- ============================================================================
UPDATE faz_agent_registry 
SET model_name = 'gpt-4o',
    updated_at = NOW()
WHERE agent_id = 'memory';

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE faz_project_artifacts IS 'Stores pipeline documents (briefs, research, plans) for user review';
COMMENT ON TABLE faz_phase_history IS 'Audit trail of pipeline phase transitions';
COMMENT ON COLUMN faz_projects.pipeline_mode IS 'auto = run without stops, interactive = pause at gates';
COMMENT ON COLUMN faz_projects.awaiting_approval_for IS 'Which artifact/phase is awaiting user approval';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    artifact_exists BOOLEAN;
    history_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'faz_project_artifacts'
    ) INTO artifact_exists;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'faz_phase_history'
    ) INTO history_exists;
    
    IF NOT artifact_exists OR NOT history_exists THEN
        RAISE EXCEPTION 'Migration 021 incomplete: artifacts=%, history=%', artifact_exists, history_exists;
    END IF;
    
    RAISE NOTICE 'Migration 021 complete: faz_project_artifacts and faz_phase_history created';
END $$;


-- ============================================================================
-- Migration: 032_muse_research_planning.sql
-- Purpose: Add research planning and user interaction columns to Muse
-- Author: Nicole V7 Architecture
-- Date: 2025-12-26
-- ============================================================================

-- Add research planning columns to sessions
ALTER TABLE muse_research_sessions 
ADD COLUMN IF NOT EXISTS research_plan JSONB DEFAULT NULL;

ALTER TABLE muse_research_sessions 
ADD COLUMN IF NOT EXISTS user_question_answers JSONB DEFAULT NULL;

-- Update session status check constraint to include new statuses
ALTER TABLE muse_research_sessions 
DROP CONSTRAINT IF EXISTS muse_research_sessions_session_status_check;

ALTER TABLE muse_research_sessions 
ADD CONSTRAINT muse_research_sessions_session_status_check 
CHECK (session_status IN (
    'intake',               -- Initial form submitted
    'planning',             -- Creating research plan (NEW)
    'awaiting_answers',     -- Waiting for user answers to questions (NEW)
    'analyzing_brief',      -- Extracting keywords/intent
    'researching',          -- Web research in progress
    'analyzing_inspiration', -- Processing user images/links
    'generating_moodboards', -- Creating 4 mood board options
    'awaiting_selection',    -- User choosing mood board
    'generating_design',     -- Full design generation
    'revising_design',       -- User requested revisions (NEW)
    'awaiting_approval',     -- User reviewing full design
    'approved',              -- Ready for Nicole handoff
    'handed_off',            -- Sent to Nicole
    'failed',                -- Error occurred
    'cancelled'              -- User cancelled
));

-- Create index for faster research plan queries
CREATE INDEX IF NOT EXISTS idx_muse_sessions_research_plan 
ON muse_research_sessions USING GIN (research_plan);

-- Add more event types for research planning
COMMENT ON TABLE muse_research_events IS 
'Event types now include: 
  - session_created, status_updated
  - research_plan_created, questions_answered
  - phase_started, phase_progress, phase_complete
  - analyzing_inspiration, inspiration_analyzed
  - moodboard_generated, moodboard_selected
  - revision_started, revision_progress, revision_complete
  - design_approved, error_occurred';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================


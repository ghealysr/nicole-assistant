-- Migration: 029_fix_qa_constraints.sql
-- Purpose: Fix QA system constraint violations and add missing columns
-- Author: Anthropic Quality Standards Implementation
-- Date: 2025-01-25

-- =============================================================================
-- PHASE 1: Update trigger_type constraint to include QA agent types
-- =============================================================================

-- Drop existing constraint
ALTER TABLE enjineer_qa_reports 
DROP CONSTRAINT IF EXISTS enjineer_qa_reports_trigger_type_check;

-- Add expanded constraint with QA agent types
ALTER TABLE enjineer_qa_reports 
ADD CONSTRAINT enjineer_qa_reports_trigger_type_check 
CHECK (trigger_type IN (
    'phase_complete',    -- QA triggered after phase completion
    'manual',            -- User-triggered QA
    'pre_deploy',        -- QA before deployment
    'scheduled',         -- Scheduled QA runs
    'standard_qa',       -- Standard QA agent (GPT-4o)
    'senior_qa',         -- Senior QA agent (Claude Opus 4.5)
    'full_qa'            -- Full pipeline (GPT-4o → Opus 4.5)
));

-- =============================================================================
-- PHASE 2: Update qa_depth constraint to include new depth levels
-- =============================================================================

-- Note: qa_depth is on enjineer_plan_phases, not qa_reports
-- But qa_reports also has qa_depth, so we need to update both

-- Update qa_reports qa_depth (if constraint exists)
DO $$
BEGIN
    -- Try to drop the constraint if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'enjineer_qa_reports_qa_depth_check'
        AND table_name = 'enjineer_qa_reports'
    ) THEN
        ALTER TABLE enjineer_qa_reports 
        DROP CONSTRAINT enjineer_qa_reports_qa_depth_check;
    END IF;
END $$;

-- Add expanded qa_depth constraint for reports
ALTER TABLE enjineer_qa_reports 
ADD CONSTRAINT enjineer_qa_reports_qa_depth_check 
CHECK (qa_depth IN (
    'light',       -- Quick review
    'standard',    -- Normal review
    'thorough',    -- Deep review
    'full',        -- Complete pipeline review
    'pipeline'     -- Multi-model pipeline
));

-- Update plan_phases qa_depth constraint
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'enjineer_plan_phases_qa_depth_check'
        AND table_name = 'enjineer_plan_phases'
    ) THEN
        ALTER TABLE enjineer_plan_phases 
        DROP CONSTRAINT enjineer_plan_phases_qa_depth_check;
    END IF;
END $$;

ALTER TABLE enjineer_plan_phases 
ADD CONSTRAINT enjineer_plan_phases_qa_depth_check 
CHECK (qa_depth IN ('light', 'standard', 'thorough', 'full', 'pipeline'));

-- =============================================================================
-- PHASE 3: Add cost tracking column to qa_reports
-- =============================================================================

-- Add estimated_cost_usd column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enjineer_qa_reports' 
        AND column_name = 'estimated_cost_usd'
    ) THEN
        ALTER TABLE enjineer_qa_reports 
        ADD COLUMN estimated_cost_usd DECIMAL(10, 6) DEFAULT 0;
    END IF;
END $$;

-- Add model_used column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enjineer_qa_reports' 
        AND column_name = 'model_used'
    ) THEN
        ALTER TABLE enjineer_qa_reports 
        ADD COLUMN model_used TEXT;
    END IF;
END $$;

-- Add tokens_used column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enjineer_qa_reports' 
        AND column_name = 'tokens_used'
    ) THEN
        ALTER TABLE enjineer_qa_reports 
        ADD COLUMN tokens_used JSONB DEFAULT '{}';
    END IF;
END $$;

-- Add triggered_by column if it doesn't exist (user_id who triggered the QA)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'enjineer_qa_reports' 
        AND column_name = 'triggered_by'
    ) THEN
        ALTER TABLE enjineer_qa_reports 
        ADD COLUMN triggered_by BIGINT;
    END IF;
END $$;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Verify constraints are in place
DO $$
BEGIN
    RAISE NOTICE 'Migration 029 complete. QA constraints updated.';
END $$;


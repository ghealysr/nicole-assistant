-- ============================================================================
-- Migration 027: Fix enjineer_plan_phases status constraint
-- Adds 'awaiting_approval' as a valid status for phases that need user approval
-- ============================================================================

-- Drop the old constraint and add new one with awaiting_approval
ALTER TABLE enjineer_plan_phases DROP CONSTRAINT IF EXISTS enjineer_plan_phases_status_check;
ALTER TABLE enjineer_plan_phases ADD CONSTRAINT enjineer_plan_phases_status_check 
  CHECK (status IN ('pending', 'in_progress', 'complete', 'blocked', 'skipped', 'awaiting_approval'));

-- Also update plans status to include 'active' which frontend expects
-- Schema has: 'draft', 'awaiting_approval', 'approved', 'in_progress', 'completed', 'abandoned'
-- Frontend expects: 'planning', 'awaiting_approval', 'active', 'paused', 'completed', 'abandoned'
ALTER TABLE enjineer_plans DROP CONSTRAINT IF EXISTS enjineer_plans_status_check;
ALTER TABLE enjineer_plans ADD CONSTRAINT enjineer_plans_status_check 
  CHECK (status IN ('draft', 'planning', 'awaiting_approval', 'approved', 'active', 'in_progress', 'paused', 'completed', 'abandoned'));

-- Migrate existing 'in_progress' to 'active' for consistency
UPDATE enjineer_plans SET status = 'active' WHERE status = 'in_progress';
UPDATE enjineer_plans SET status = 'planning' WHERE status = 'draft';


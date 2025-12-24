-- ============================================================================
-- Migration 027: Fix enjineer_plan_phases status constraint
-- Adds 'awaiting_approval' as a valid status for phases that need user approval
-- ============================================================================

-- Drop the old constraint and add new one with awaiting_approval
ALTER TABLE enjineer_plan_phases DROP CONSTRAINT IF EXISTS enjineer_plan_phases_status_check;
ALTER TABLE enjineer_plan_phases ADD CONSTRAINT enjineer_plan_phases_status_check 
  CHECK (status IN ('pending', 'in_progress', 'complete', 'blocked', 'skipped', 'awaiting_approval'));

-- Note: enjineer_plans.status constraint from migration 025 is already correct:
-- CHECK (status IN ('draft', 'awaiting_approval', 'approved', 'in_progress', 'completed', 'abandoned'))
-- Frontend has been updated to match these values.


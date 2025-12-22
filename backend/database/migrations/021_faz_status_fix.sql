-- Migration 021: Fix Faz Projects Status Constraint
-- Adds missing status values: 'failed', 'paused'

-- Drop the old constraint
ALTER TABLE faz_projects DROP CONSTRAINT IF EXISTS faz_projects_status_check;

-- Add new constraint with all required status values
ALTER TABLE faz_projects ADD CONSTRAINT faz_projects_status_check CHECK (status IN (
    'intake', 'planning', 'researching', 'designing', 'building', 
    'qa', 'review', 'approved', 'deploying', 'deployed', 'delivered', 'archived',
    'failed', 'paused'
));

-- Also fix faz_agent_activities status constraint if needed
ALTER TABLE faz_agent_activities DROP CONSTRAINT IF EXISTS faz_agent_activities_status_check;
ALTER TABLE faz_agent_activities ADD CONSTRAINT faz_agent_activities_status_check CHECK (status IN (
    'running', 'complete', 'error', 'cancelled', 'pending'
));

SELECT 'Faz status constraints updated successfully' AS result;



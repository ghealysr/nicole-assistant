-- ============================================================================
-- Migration 026: Enjineer Vercel Integration
-- 
-- Adds persistent Vercel project tracking for consistent preview URLs
-- and production deployment pipeline support.
-- ============================================================================

-- Add Vercel integration columns to enjineer_projects
ALTER TABLE enjineer_projects 
ADD COLUMN IF NOT EXISTS vercel_project_id TEXT,
ADD COLUMN IF NOT EXISTS vercel_project_name TEXT,
ADD COLUMN IF NOT EXISTS preview_domain TEXT,
ADD COLUMN IF NOT EXISTS production_domain TEXT,
ADD COLUMN IF NOT EXISTS last_preview_deployment_id TEXT,
ADD COLUMN IF NOT EXISTS last_preview_url TEXT,
ADD COLUMN IF NOT EXISTS last_preview_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_production_deployment_id TEXT,
ADD COLUMN IF NOT EXISTS last_production_url TEXT,
ADD COLUMN IF NOT EXISTS last_production_at TIMESTAMPTZ;

-- Create index for quick Vercel project lookups
CREATE INDEX IF NOT EXISTS idx_enjineer_projects_vercel 
ON enjineer_projects(vercel_project_id) WHERE vercel_project_id IS NOT NULL;

-- Update deployments table to support both preview and production
ALTER TABLE enjineer_deployments
ADD COLUMN IF NOT EXISTS is_preview BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS domain_alias TEXT;

-- Create a table for tracking domain configurations
CREATE TABLE IF NOT EXISTS enjineer_domain_configs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    domain_type TEXT NOT NULL CHECK (domain_type IN ('preview', 'production', 'custom')),
    verified BOOLEAN DEFAULT FALSE,
    vercel_domain_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, domain)
);

CREATE INDEX IF NOT EXISTS idx_enjineer_domain_configs_project 
ON enjineer_domain_configs(project_id);

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON COLUMN enjineer_projects.vercel_project_id IS 'Vercel project ID for this Enjineer project';
COMMENT ON COLUMN enjineer_projects.vercel_project_name IS 'Vercel project name (used in API calls)';
COMMENT ON COLUMN enjineer_projects.preview_domain IS 'Persistent preview domain (e.g., project-5.enjineer.alphawavetech.com)';
COMMENT ON COLUMN enjineer_projects.production_domain IS 'Production domain if deployed';
COMMENT ON COLUMN enjineer_projects.last_preview_url IS 'URL of the most recent preview deployment';
COMMENT ON COLUMN enjineer_projects.last_preview_at IS 'Timestamp of last preview deployment';



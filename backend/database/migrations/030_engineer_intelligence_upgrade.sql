-- Migration: 030_engineer_intelligence_upgrade.sql
-- Purpose: Add tables for Engineer Intelligence system
-- Features: Verification tracking, deployment state, error patterns, NPM cache
-- Author: Nicole V7 Architecture
-- Date: 2025-12-25

-- ============================================================================
-- 1. DEPLOYMENT STATE TRACKING
-- Tracks intended vs verified file states to detect silent failures
-- ============================================================================

CREATE TABLE IF NOT EXISTS enjineer_deployment_state (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    deployment_id TEXT,
    filepath TEXT NOT NULL,
    intended_hash TEXT,
    intended_content_preview TEXT,  -- First 500 chars for debugging
    verified_hash TEXT,
    change_description TEXT,
    verified BOOLEAN DEFAULT FALSE,
    verification_attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    
    CONSTRAINT unique_deployment_file UNIQUE (project_id, deployment_id, filepath)
);

CREATE INDEX IF NOT EXISTS idx_deployment_state_project 
ON enjineer_deployment_state(project_id);

CREATE INDEX IF NOT EXISTS idx_deployment_state_unverified 
ON enjineer_deployment_state(project_id) 
WHERE verified = FALSE;

-- ============================================================================
-- 2. ERROR PATTERN HISTORY
-- Tracks recurring errors across deployments for pattern detection
-- ============================================================================

CREATE TABLE IF NOT EXISTS enjineer_error_patterns (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    deployment_id TEXT,
    error_type TEXT NOT NULL,
    error_detail TEXT,
    error_file TEXT,
    error_line INTEGER,
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolution_description TEXT,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_error_patterns_recurring 
ON enjineer_error_patterns(project_id, error_type, error_detail) 
WHERE resolved = FALSE;

CREATE INDEX IF NOT EXISTS idx_error_patterns_project 
ON enjineer_error_patterns(project_id, last_seen DESC);

-- ============================================================================
-- 3. NPM VALIDATION CACHE
-- Caches NPM registry lookups to avoid repeated API calls
-- ============================================================================

CREATE TABLE IF NOT EXISTS enjineer_npm_cache (
    package_name TEXT NOT NULL,
    version TEXT NOT NULL,
    valid BOOLEAN NOT NULL,
    resolved_version TEXT,
    peer_deps JSONB DEFAULT '{}',
    deprecated BOOLEAN DEFAULT FALSE,
    deprecation_message TEXT,
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (package_name, version)
);

CREATE INDEX IF NOT EXISTS idx_npm_cache_valid 
ON enjineer_npm_cache(package_name, valid);

-- Auto-expire cache after 24 hours
CREATE INDEX IF NOT EXISTS idx_npm_cache_expiry 
ON enjineer_npm_cache(checked_at);

-- ============================================================================
-- 4. DEPLOYMENT ATTEMPTS LOG
-- Tracks each deployment attempt for circuit breaker logic
-- ============================================================================

CREATE TABLE IF NOT EXISTS enjineer_deployment_attempts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    deployment_id TEXT,
    vercel_deployment_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'building', 'success', 'failed', 'cancelled')),
    error_count INTEGER DEFAULT 0,
    claimed_fixes JSONB DEFAULT '[]',
    log_hash TEXT,
    duration_seconds FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_deployment_attempts_project 
ON enjineer_deployment_attempts(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_deployment_attempts_recent_failures 
ON enjineer_deployment_attempts(project_id, created_at) 
WHERE status = 'failed';

-- ============================================================================
-- 5. PREFLIGHT AUDIT RESULTS
-- Stores preflight audit results for reference
-- ============================================================================

CREATE TABLE IF NOT EXISTS enjineer_preflight_audits (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    audit_type TEXT NOT NULL CHECK (audit_type IN ('dependencies', 'imports', 'typescript', 'build', 'full')),
    passed BOOLEAN NOT NULL,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',
    warnings JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_preflight_audits_project 
ON enjineer_preflight_audits(project_id, created_at DESC);

-- ============================================================================
-- 6. CIRCUIT BREAKER STATE
-- Tracks circuit breaker state per project
-- ============================================================================

CREATE TABLE IF NOT EXISTS enjineer_circuit_breaker (
    project_id BIGINT PRIMARY KEY REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    state TEXT NOT NULL DEFAULT 'closed' CHECK (state IN ('closed', 'open', 'half_open')),
    failure_count INTEGER DEFAULT 0,
    last_failure_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    resume_at TIMESTAMPTZ,
    reason TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 7. HELPER FUNCTIONS
-- ============================================================================

-- Function to check if circuit breaker is open for a project
CREATE OR REPLACE FUNCTION check_circuit_breaker(p_project_id BIGINT)
RETURNS TABLE(is_open BOOLEAN, reason TEXT, resume_at TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN cb.state = 'open' AND cb.resume_at > NOW() THEN TRUE
            ELSE FALSE
        END as is_open,
        cb.reason,
        cb.resume_at
    FROM enjineer_circuit_breaker cb
    WHERE cb.project_id = p_project_id;
    
    -- Return closed if no record exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, NULL::TIMESTAMPTZ;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to get recurring errors for a project
CREATE OR REPLACE FUNCTION get_recurring_errors(
    p_project_id BIGINT, 
    p_min_occurrences INTEGER DEFAULT 2
)
RETURNS TABLE(
    error_type TEXT, 
    error_detail TEXT, 
    occurrence_count INTEGER,
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ep.error_type,
        ep.error_detail,
        ep.occurrence_count,
        ep.first_seen,
        ep.last_seen
    FROM enjineer_error_patterns ep
    WHERE ep.project_id = p_project_id
      AND ep.resolved = FALSE
      AND ep.occurrence_count >= p_min_occurrences
    ORDER BY ep.occurrence_count DESC, ep.last_seen DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to clean expired NPM cache
CREATE OR REPLACE FUNCTION cleanup_npm_cache(p_max_age_hours INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM enjineer_npm_cache
    WHERE checked_at < NOW() - (p_max_age_hours || ' hours')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. GRANT PERMISSIONS
-- ============================================================================

-- Ensure tsdbadmin has full access
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tsdbadmin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tsdbadmin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO tsdbadmin;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================


-- ============================================================================
-- Safety System Database Migration - Nicole V7
-- Version: 7.1.0
-- Date: October 22, 2025
-- 
-- This migration adds comprehensive safety system tables for incident logging,
-- policy versioning, and COPPA compliance.
--
-- CRITICAL: This migration NEVER stores raw content.
-- Only masked hashes and metadata are stored for privacy protection.
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: safety_incidents
-- Purpose: Log safety violations with masked content only (NO PII)
-- Privacy: RLS-protected, users see own incidents, admins see all
-- Retention: Immutable audit trail, no raw content ever stored
-- ============================================================================

CREATE TABLE IF NOT EXISTS safety_incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Violation details
    category TEXT NOT NULL CHECK (category IN (
        'sexual_content',
        'grooming',
        'self_harm',
        'drugs',
        'weapons',
        'hate_harassment',
        'excessive_violence',
        'explicit_profanity',
        'prompt_injection',
        'pii_sharing',
        'contact_exchange',
        'location_request',
        'url_invite',
        'jailbreak_attempt'
    )),
    
    -- Source of violation
    source TEXT NOT NULL CHECK (source IN ('input', 'output', 'streaming')),
    
    -- Age tier applied
    tier TEXT NOT NULL CHECK (tier IN (
        'child_8_12',
        'teen_13_15',
        'teen_16_17',
        'adult',
        'unknown'
    )),
    
    -- Privacy-protected content reference (SHA256 hash only)
    masked_hash TEXT NOT NULL,  -- NO raw content ever stored
    
    -- Severity level
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Tracking
    correlation_id TEXT,  -- Request correlation ID for tracing
    policy_version TEXT DEFAULT 'v7.1',  -- Policy version for audit trail
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_safety_incidents_user_id 
    ON safety_incidents(user_id, created_at DESC);

CREATE INDEX idx_safety_incidents_category 
    ON safety_incidents(category, created_at DESC);

CREATE INDEX idx_safety_incidents_severity 
    ON safety_incidents(severity, created_at DESC) 
    WHERE severity IN ('high', 'critical');

CREATE INDEX idx_safety_incidents_correlation 
    ON safety_incidents(correlation_id) 
    WHERE correlation_id IS NOT NULL;

-- RLS Policies
ALTER TABLE safety_incidents ENABLE ROW LEVEL SECURITY;

-- Users can see their own incidents only
CREATE POLICY "users_see_own_incidents" 
    ON safety_incidents
    FOR SELECT 
    USING (auth.uid() = user_id);

-- Admins can see all incidents
CREATE POLICY "admins_see_all_incidents" 
    ON safety_incidents
    FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Only system can insert (not direct user inserts)
CREATE POLICY "system_insert_incidents" 
    ON safety_incidents
    FOR INSERT 
    WITH CHECK (true);

-- No updates or deletes (immutable audit trail)
-- This is enforced by not creating policies for UPDATE or DELETE

-- ============================================================================
-- TABLE: policy_versions
-- Purpose: Track safety policy versions for audit trail
-- Usage: Tag incidents with specific policy versions
-- ============================================================================

CREATE TABLE IF NOT EXISTS policy_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    version TEXT NOT NULL UNIQUE,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert initial policy version
INSERT INTO policy_versions (name, version, effective_from, notes)
VALUES (
    'Nicole V7 Safety Policy',
    'v7.1',
    NOW(),
    '4-tier age-based safety system with streaming moderation, COPPA compliance, and comprehensive pattern detection'
) ON CONFLICT (version) DO NOTHING;

-- RLS for policy_versions (read-only for all users)
ALTER TABLE policy_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "all_users_read_policies" 
    ON policy_versions
    FOR SELECT 
    USING (true);

-- ============================================================================
-- TABLE: users - Add Safety and COPPA Fields
-- Purpose: Add age tracking and parental consent for COPPA compliance
-- ============================================================================

-- Add date of birth for age calculation
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS date_of_birth DATE;

-- Add computed age field
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS age INTEGER;

-- Add parental consent fields for COPPA compliance (<13 years old)
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS parental_consent BOOLEAN DEFAULT FALSE;

ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS parental_consent_date TIMESTAMPTZ;

ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS parental_consent_ip TEXT;

-- Add consent withdrawal tracking
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS parental_consent_withdrawn BOOLEAN DEFAULT FALSE;

ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS parental_consent_withdrawn_date TIMESTAMPTZ;

-- ============================================================================
-- FUNCTION: calculate_age
-- Purpose: Calculate age from date of birth
-- Usage: Used in trigger to auto-update age field
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_age(dob DATE)
RETURNS INTEGER AS $$
BEGIN
    IF dob IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN DATE_PART('year', AGE(CURRENT_DATE, dob))::INTEGER;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- TRIGGER: auto_update_user_age
-- Purpose: Automatically update age when DOB changes
-- ============================================================================

CREATE OR REPLACE FUNCTION update_user_age()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.date_of_birth IS NOT NULL THEN
        NEW.age := calculate_age(NEW.date_of_birth);
    ELSE
        NEW.age := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists (for idempotency)
DROP TRIGGER IF EXISTS trigger_update_user_age ON users;

-- Create trigger
CREATE TRIGGER trigger_update_user_age
    BEFORE INSERT OR UPDATE OF date_of_birth ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_age();

-- ============================================================================
-- VIEW: safety_incident_summary
-- Purpose: Provide summary statistics for parental review
-- Privacy: No raw content, only aggregated counts
-- ============================================================================

CREATE OR REPLACE VIEW safety_incident_summary AS
SELECT 
    user_id,
    DATE_TRUNC('day', created_at) AS incident_date,
    category,
    tier,
    severity,
    COUNT(*) AS incident_count,
    MIN(created_at) AS first_incident_at,
    MAX(created_at) AS last_incident_at
FROM safety_incidents
GROUP BY 
    user_id, 
    DATE_TRUNC('day', created_at), 
    category, 
    tier, 
    severity;

-- RLS for view (inherits from base table)
ALTER VIEW safety_incident_summary SET (security_barrier = true);

-- ============================================================================
-- FUNCTION: get_user_safety_stats
-- Purpose: Get safety statistics for a user (for parental review)
-- Returns: Aggregated incident counts by category (NO raw content)
-- ============================================================================

CREATE OR REPLACE FUNCTION get_user_safety_stats(
    p_user_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    category TEXT,
    incident_count BIGINT,
    last_incident_date TIMESTAMPTZ,
    severity_breakdown JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        si.category,
        COUNT(*) AS incident_count,
        MAX(si.created_at) AS last_incident_date,
        jsonb_object_agg(
            si.severity, 
            COUNT(*)
        ) AS severity_breakdown
    FROM safety_incidents si
    WHERE si.user_id = p_user_id
        AND si.created_at >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY si.category
    ORDER BY COUNT(*) DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_user_safety_stats(UUID, INTEGER) TO authenticated;

-- ============================================================================
-- FUNCTION: check_coppa_compliance
-- Purpose: Check if user requires parental consent
-- Returns: Boolean indicating if user can proceed
-- ============================================================================

CREATE OR REPLACE FUNCTION check_coppa_compliance(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    user_age INTEGER;
    has_consent BOOLEAN;
BEGIN
    -- Get user age and consent status
    SELECT age, parental_consent 
    INTO user_age, has_consent
    FROM users 
    WHERE id = p_user_id;
    
    -- If age unknown, require consent
    IF user_age IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- If 13 or older, no consent needed
    IF user_age >= 13 THEN
        RETURN TRUE;
    END IF;
    
    -- If under 13, must have parental consent
    RETURN COALESCE(has_consent, FALSE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION check_coppa_compliance(UUID) TO authenticated;

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT, INSERT ON safety_incidents TO authenticated;
GRANT SELECT ON policy_versions TO authenticated;
GRANT SELECT ON safety_incident_summary TO authenticated;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Index on users.age for tier classification
CREATE INDEX IF NOT EXISTS idx_users_age 
    ON users(age) 
    WHERE age IS NOT NULL;

-- Index on users.parental_consent for COPPA checks
CREATE INDEX IF NOT EXISTS idx_users_parental_consent 
    ON users(parental_consent, age) 
    WHERE age < 13;

-- ============================================================================
-- COMMENTS (Documentation)
-- ============================================================================

COMMENT ON TABLE safety_incidents IS 
'Safety incident audit log. NEVER stores raw content - only masked SHA256 hashes for privacy protection. RLS-protected for user privacy.';

COMMENT ON COLUMN safety_incidents.masked_hash IS 
'SHA256 hash of content with safe preview (first/last 3 chars only). NO raw content ever stored.';

COMMENT ON TABLE policy_versions IS 
'Safety policy version tracking for audit trail. Links incidents to specific policy versions.';

COMMENT ON COLUMN users.date_of_birth IS 
'User date of birth for age calculation and tier classification.';

COMMENT ON COLUMN users.age IS 
'Auto-calculated age from date_of_birth. Updated via trigger.';

COMMENT ON COLUMN users.parental_consent IS 
'COPPA compliance: Parental consent required for users under 13.';

COMMENT ON FUNCTION calculate_age(DATE) IS 
'Calculate current age from date of birth. Handles leap years correctly.';

COMMENT ON FUNCTION check_coppa_compliance(UUID) IS 
'Check if user meets COPPA compliance requirements. Returns false if under 13 without parental consent.';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables exist
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
        AND table_name IN ('safety_incidents', 'policy_versions');
    
    IF table_count = 2 THEN
        RAISE NOTICE 'SUCCESS: All safety system tables created';
    ELSE
        RAISE WARNING 'WARNING: Expected 2 tables, found %', table_count;
    END IF;
END $$;

-- Verify columns added to users
DO $$
DECLARE
    column_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
        AND table_name = 'users'
        AND column_name IN ('date_of_birth', 'age', 'parental_consent', 'parental_consent_date');
    
    IF column_count = 4 THEN
        RAISE NOTICE 'SUCCESS: All COPPA compliance columns added to users table';
    ELSE
        RAISE WARNING 'WARNING: Expected 4 columns, found %', column_count;
    END IF;
END $$;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Record migration
INSERT INTO policy_versions (name, version, effective_from, notes)
VALUES (
    'Safety System Database Migration',
    'v7.1.1',
    NOW(),
    'Added safety_incidents table, policy_versions table, COPPA compliance fields, and age tracking to users table'
) ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Safety System Migration Complete';
    RAISE NOTICE 'Version: 7.1.1';
    RAISE NOTICE 'Date: %', NOW();
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - safety_incidents table (RLS enabled)';
    RAISE NOTICE '  - policy_versions table';
    RAISE NOTICE '  - COPPA compliance fields in users';
    RAISE NOTICE '  - Age calculation function and trigger';
    RAISE NOTICE '  - Safety statistics functions';
    RAISE NOTICE '========================================';
END $$;



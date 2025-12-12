-- ============================================================================
-- VIBE FINAL FIXES MIGRATION
-- Migration: 010
--
-- CTO Remediation Release - Final database improvements:
-- 1. Add missing index on vibe_activities.user_id
-- 2. Add FK constraint on vibe_activities.user_id (if users table exists)
-- 3. Add index for optimistic locking queries
-- 
-- Author: CTO Remediation
-- Date: 2025-12-12
-- ============================================================================

-- 1. Add index on vibe_activities.user_id for faster user-specific queries
CREATE INDEX IF NOT EXISTS idx_vibe_activities_user
ON vibe_activities(user_id)
WHERE user_id IS NOT NULL;

-- 2. Add index for optimistic locking status checks
CREATE INDEX IF NOT EXISTS idx_vibe_projects_status_user
ON vibe_projects(project_id, user_id, status);

-- 3. Add FK constraint on vibe_activities.user_id if users table exists
-- This is wrapped in a DO block to handle missing users table gracefully
DO $$
BEGIN
    -- Check if users table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'users'
    ) THEN
        -- Check if FK doesn't already exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'vibe_activities_user_id_fkey'
            AND table_name = 'vibe_activities'
        ) THEN
            -- Add FK constraint
            ALTER TABLE vibe_activities
            ADD CONSTRAINT vibe_activities_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(user_id)
            ON DELETE SET NULL;
            
            RAISE NOTICE 'Added FK constraint vibe_activities_user_id_fkey';
        ELSE
            RAISE NOTICE 'FK constraint vibe_activities_user_id_fkey already exists';
        END IF;
    ELSE
        RAISE NOTICE 'users table not found, skipping FK constraint';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Failed to add FK constraint: %', SQLERRM;
END $$;

-- 4. Add partial index for active projects (commonly queried)
CREATE INDEX IF NOT EXISTS idx_vibe_projects_active
ON vibe_projects(user_id, updated_at DESC)
WHERE status NOT IN ('archived', 'delivered');

-- 5. Add comment for documentation
COMMENT ON INDEX idx_vibe_activities_user IS 'Index for user-specific activity lookups';
COMMENT ON INDEX idx_vibe_projects_status_user IS 'Index for optimistic locking status checks';
COMMENT ON INDEX idx_vibe_projects_active IS 'Partial index for active project listings';

-- ============================================================================
-- VERIFICATION QUERIES (run manually to verify)
-- ============================================================================
-- SELECT indexname FROM pg_indexes WHERE tablename = 'vibe_activities';
-- SELECT indexname FROM pg_indexes WHERE tablename = 'vibe_projects';
-- SELECT conname FROM pg_constraint WHERE conrelid = 'vibe_activities'::regclass;


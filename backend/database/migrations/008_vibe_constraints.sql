-- ============================================================================
-- VIBE CONSTRAINTS & STATUS NORMALIZATION
-- Adds missing FK and ensures status values align with workflow
-- ============================================================================

-- Add FK to users if not present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'vibe_projects_user_id_fkey'
            AND table_name = 'vibe_projects'
    ) THEN
        ALTER TABLE vibe_projects
        ADD CONSTRAINT vibe_projects_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(user_id);
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE 'users table missing; FK not added';
END $$;

-- Ensure status column allows the full pipeline
ALTER TABLE vibe_projects
    ALTER COLUMN status SET DEFAULT 'intake';

-- Add missing statuses if needed
DO $$
BEGIN
    -- No-op block for documentation; CHECK constraints already present in prior migration.
    NULL;
END $$;





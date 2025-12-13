-- ============================================================================
-- Research User Scoping
-- Adds user_id to research tables for future multi-user support
-- ============================================================================

-- Add user_id column to research_requests
ALTER TABLE research_requests 
ADD COLUMN IF NOT EXISTS user_id INTEGER;

-- Create index for user lookups
CREATE INDEX IF NOT EXISTS idx_research_requests_user 
ON research_requests(user_id);

-- Add composite index for user + status queries
CREATE INDEX IF NOT EXISTS idx_research_requests_user_status 
ON research_requests(user_id, status);

-- Add composite index for user + created_at (recent queries)
CREATE INDEX IF NOT EXISTS idx_research_requests_user_recent 
ON research_requests(user_id, created_at DESC);

-- Comment
COMMENT ON COLUMN research_requests.user_id IS 'User who initiated the research request';


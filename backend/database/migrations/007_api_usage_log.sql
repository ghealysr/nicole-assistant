-- ============================================================
-- NICOLE V7 - API USAGE TRACKING TABLE
-- Migration 007: Track API usage for cost monitoring
-- ============================================================

-- API Usage Log - Track every API call for cost analysis
CREATE TABLE IF NOT EXISTS api_usage_log (
    usage_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Service identification
    service TEXT NOT NULL CHECK (service IN ('claude', 'openai', 'azure', 'brave', 'other')),
    model TEXT,
    request_type TEXT,
    
    -- Token counts
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Cost (calculated at time of request)
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
    
    -- Optional references
    conversation_id BIGINT REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_usage_user_date ON api_usage_log (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_service ON api_usage_log (service, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_daily ON api_usage_log (user_id, DATE(created_at));

-- Comment for documentation
COMMENT ON TABLE api_usage_log IS 'Tracks all API usage for cost monitoring and analysis. Records token counts and calculated costs for Claude, OpenAI, Azure, and other services.';


-- ============================================================================
-- Workflow Tracking Schema
-- ============================================================================
-- Adds tables for tracking Nicole's multi-step workflow executions
-- Enables workflow analytics, debugging, and audit trails
--
-- Author: Nicole V7 Engineering
-- Date: December 20, 2025
-- ============================================================================

-- Workflow Runs - Track complete workflow executions
CREATE TABLE IF NOT EXISTS workflow_runs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
  run_id VARCHAR(100) UNIQUE NOT NULL, -- External run ID (wf_<name>_<uuid>)
  workflow_name VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  input_data JSONB,
  output_data JSONB,
  error_message TEXT,
  
  -- Progress tracking
  steps_completed INTEGER DEFAULT 0,
  steps_total INTEGER,
  
  -- Timing
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  duration_ms INTEGER,
  
  -- Audit
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Workflow Steps - Track individual step executions within a workflow
CREATE TABLE IF NOT EXISTS workflow_steps (
  id SERIAL PRIMARY KEY,
  workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
  step_number INTEGER NOT NULL,
  step_name VARCHAR(100) NOT NULL,
  tool_name VARCHAR(100) NOT NULL,
  tool_args JSONB,
  result JSONB,
  status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
  error_message TEXT,
  
  -- Retry tracking
  retry_count INTEGER DEFAULT 0,
  
  -- Timing
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  duration_ms INTEGER,
  
  -- Audit
  created_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT workflow_steps_unique_step UNIQUE (workflow_run_id, step_number)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id ON workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow_name ON workflow_runs(workflow_name);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_started_at ON workflow_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_run_id ON workflow_runs(run_id);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_run_id ON workflow_steps(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_status ON workflow_steps(status);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_tool_name ON workflow_steps(tool_name);

-- Updated_at trigger for workflow_runs
CREATE OR REPLACE FUNCTION update_workflow_runs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_workflow_runs_updated_at ON workflow_runs;
CREATE TRIGGER trigger_update_workflow_runs_updated_at
  BEFORE UPDATE ON workflow_runs
  FOR EACH ROW
  EXECUTE FUNCTION update_workflow_runs_updated_at();

-- Comments for documentation
COMMENT ON TABLE workflow_runs IS 'Tracks complete multi-step workflow executions';
COMMENT ON TABLE workflow_steps IS 'Tracks individual steps within workflow executions';

COMMENT ON COLUMN workflow_runs.run_id IS 'External run ID in format: wf_<workflow_name>_<uuid>';
COMMENT ON COLUMN workflow_runs.status IS 'Current workflow status: pending, running, completed, failed, cancelled';
COMMENT ON COLUMN workflow_runs.input_data IS 'JSON input parameters provided to the workflow';
COMMENT ON COLUMN workflow_runs.output_data IS 'JSON output/result data from completed workflow';
COMMENT ON COLUMN workflow_runs.duration_ms IS 'Total execution time in milliseconds';

COMMENT ON COLUMN workflow_steps.step_number IS '1-indexed step number within the workflow';
COMMENT ON COLUMN workflow_steps.status IS 'Step status: pending, running, completed, failed, skipped';
COMMENT ON COLUMN workflow_steps.retry_count IS 'Number of times this step was retried before success/failure';
COMMENT ON COLUMN workflow_steps.duration_ms IS 'Step execution time in milliseconds';

-- ============================================================================
-- Utility Views for Analytics
-- ============================================================================

-- View: Workflow execution summary
CREATE OR REPLACE VIEW workflow_execution_summary AS
SELECT 
  workflow_name,
  COUNT(*) as total_runs,
  COUNT(*) FILTER (WHERE status = 'completed') as completed_runs,
  COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
  COUNT(*) FILTER (WHERE status = 'running') as active_runs,
  ROUND(AVG(duration_ms)) as avg_duration_ms,
  ROUND(AVG(steps_completed::NUMERIC / NULLIF(steps_total, 0) * 100), 2) as avg_completion_rate,
  MAX(started_at) as last_run_at
FROM workflow_runs
GROUP BY workflow_name
ORDER BY total_runs DESC;

COMMENT ON VIEW workflow_execution_summary IS 'Summary statistics for each workflow type';

-- View: Recent workflow failures
CREATE OR REPLACE VIEW recent_workflow_failures AS
SELECT 
  run_id,
  workflow_name,
  user_id,
  error_message,
  steps_completed,
  steps_total,
  started_at,
  duration_ms
FROM workflow_runs
WHERE status = 'failed'
ORDER BY started_at DESC
LIMIT 100;

COMMENT ON VIEW recent_workflow_failures IS 'Most recent 100 workflow failures for debugging';

-- ============================================================================
-- Grant Permissions
-- ============================================================================

-- Grant access to nicole-api user (adjust user name as needed)
GRANT SELECT, INSERT, UPDATE, DELETE ON workflow_runs TO "nicole-api";
GRANT SELECT, INSERT, UPDATE, DELETE ON workflow_steps TO "nicole-api";
GRANT USAGE, SELECT ON SEQUENCE workflow_runs_id_seq TO "nicole-api";
GRANT USAGE, SELECT ON SEQUENCE workflow_steps_id_seq TO "nicole-api";
GRANT SELECT ON workflow_execution_summary TO "nicole-api";
GRANT SELECT ON recent_workflow_failures TO "nicole-api";

-- ============================================================================
-- Sample Queries for Reference
-- ============================================================================

-- Find slowest workflows
-- SELECT workflow_name, AVG(duration_ms) as avg_ms 
-- FROM workflow_runs WHERE status = 'completed'
-- GROUP BY workflow_name ORDER BY avg_ms DESC;

-- Find most failed workflow steps
-- SELECT tool_name, COUNT(*) as failures
-- FROM workflow_steps WHERE status = 'failed'
-- GROUP BY tool_name ORDER BY failures DESC;

-- Get workflow execution timeline for a specific run
-- SELECT step_number, step_name, status, duration_ms, error_message
-- FROM workflow_steps WHERE workflow_run_id = <run_id>
-- ORDER BY step_number;

-- ============================================================================
-- Migration Complete
-- ============================================================================


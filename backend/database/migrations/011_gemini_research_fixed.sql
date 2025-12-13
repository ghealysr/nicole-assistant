-- ============================================================================
-- Gemini Research System - Fixed Migration
-- Creates tables for research requests, results, and vibe inspirations
-- Fixed: Uses project_id as FK (not id), proper column names
-- ============================================================================

-- Research Requests Table
CREATE TABLE IF NOT EXISTS research_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    type VARCHAR(50) NOT NULL DEFAULT 'general',  -- general, vibe_inspiration, competitor, technical
    query TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    constraints JSONB DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, researching, synthesizing, complete, failed
    project_id INTEGER REFERENCES vibe_projects(project_id) ON DELETE SET NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_research_requests_status ON research_requests(status);
CREATE INDEX IF NOT EXISTS idx_research_requests_user ON research_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_research_requests_project ON research_requests(project_id);
CREATE INDEX IF NOT EXISTS idx_research_requests_created ON research_requests(created_at DESC);

-- Research Results Table (raw Gemini + Claude synthesis)
CREATE TABLE IF NOT EXISTS research_results (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES research_requests(id) ON DELETE CASCADE,
    raw_gemini_output JSONB NOT NULL DEFAULT '{}',
    claude_synthesis JSONB DEFAULT '{}',
    sources JSONB DEFAULT '[]',
    thinking_content TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_results_request ON research_results(request_id);

-- Research Reports Table (final structured output)
CREATE TABLE IF NOT EXISTS research_reports (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES research_requests(id) ON DELETE CASCADE,
    executive_summary TEXT,
    findings JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    nicole_synthesis TEXT,
    sources JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_reports_request ON research_reports(request_id);

-- Vibe Inspirations Table (design inspiration storage)
CREATE TABLE IF NOT EXISTS vibe_inspirations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES vibe_projects(project_id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    screenshot_url TEXT,
    source_site TEXT,
    design_elements JSONB DEFAULT '{}',
    relevance_notes TEXT,
    user_feedback JSONB,
    saved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vibe_inspirations_project ON vibe_inspirations(project_id);
CREATE INDEX IF NOT EXISTS idx_vibe_inspirations_saved ON vibe_inspirations(project_id, saved) WHERE saved = true;

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trigger_vibe_inspirations_updated ON vibe_inspirations;
CREATE TRIGGER trigger_vibe_inspirations_updated
BEFORE UPDATE ON vibe_inspirations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (single user, adjust if needed)
COMMENT ON TABLE research_requests IS 'Gemini research requests with status tracking';
COMMENT ON TABLE research_results IS 'Raw research outputs from Gemini + Claude synthesis';
COMMENT ON TABLE research_reports IS 'Final structured research reports';
COMMENT ON TABLE vibe_inspirations IS 'Saved design inspirations for Vibe projects';


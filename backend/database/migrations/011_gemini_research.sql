-- ============================================================================
-- Gemini 3 Pro Research Integration Schema
-- Nicole V7 - Deep Research with Google Search Grounding
-- ============================================================================

-- Research requests tracking
CREATE TABLE IF NOT EXISTS research_requests (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('general', 'vibe_inspiration', 'competitor', 'technical')),
    query TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    constraints JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'researching', 'synthesizing', 'complete', 'failed')),
    project_id INTEGER REFERENCES vibe_projects(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for research_requests
CREATE INDEX IF NOT EXISTS idx_research_requests_status ON research_requests(status);
CREATE INDEX IF NOT EXISTS idx_research_requests_type ON research_requests(type);
CREATE INDEX IF NOT EXISTS idx_research_requests_project ON research_requests(project_id);
CREATE INDEX IF NOT EXISTS idx_research_requests_created ON research_requests(created_at DESC);

-- Raw research results from Gemini
CREATE TABLE IF NOT EXISTS research_results (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES research_requests(id) ON DELETE CASCADE,
    raw_response JSONB NOT NULL,
    sources JSONB DEFAULT '[]',
    images JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_results_request ON research_results(request_id);

-- Synthesized reports (Claude processed with Nicole's voice)
CREATE TABLE IF NOT EXISTS research_reports (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES research_requests(id) ON DELETE CASCADE,
    title TEXT,
    executive_summary TEXT,
    findings JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    artifact_html TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_reports_request ON research_reports(request_id);

-- Vibe project inspirations (for feedback loop)
CREATE TABLE IF NOT EXISTS vibe_inspirations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES vibe_projects(id) ON DELETE CASCADE,
    research_request_id INTEGER REFERENCES research_requests(id) ON DELETE SET NULL,
    image_url TEXT NOT NULL,
    screenshot_url TEXT,
    source_site TEXT,
    design_elements JSONB DEFAULT '{}',
    relevance_notes TEXT,
    user_feedback JSONB,
    saved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vibe_inspirations_project ON vibe_inspirations(project_id);
CREATE INDEX IF NOT EXISTS idx_vibe_inspirations_saved ON vibe_inspirations(saved) WHERE saved = true;

-- Comments
COMMENT ON TABLE research_requests IS 'Tracks all research requests made via Gemini 3 Pro';
COMMENT ON TABLE research_results IS 'Raw Gemini responses with grounding data';
COMMENT ON TABLE research_reports IS 'Claude-synthesized reports in Nicole''s voice';
COMMENT ON TABLE vibe_inspirations IS 'Design inspirations saved from research for Vibe projects';

-- ============================================================================
-- Add Gemini to image generation tracking
-- ============================================================================

-- Add gemini as a model option (if image_jobs table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'image_jobs') THEN
        -- Add constraint check for gemini model if not exists
        -- This allows gemini-3-pro-image-preview as a valid model
        NULL; -- No-op, just checking
    END IF;
END $$;




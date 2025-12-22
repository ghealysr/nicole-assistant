-- ============================================================================
-- VIBE DASHBOARD MIGRATION
-- AlphaWave Project Management System
-- ============================================================================

-- Create vibe_projects table
CREATE TABLE IF NOT EXISTS vibe_projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    
    -- Basic info
    name TEXT NOT NULL,
    project_type TEXT NOT NULL CHECK (project_type IN (
        'website', 'chatbot', 'assistant', 'integration'
    )),
    client_name TEXT,
    client_email TEXT,
    
    -- Project data (flexible JSON)
    brief JSONB DEFAULT '{}',
    architecture JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    
    -- Status (simple state)
    status TEXT NOT NULL DEFAULT 'intake' CHECK (status IN (
        'intake', 'planning', 'building', 'qa', 'review', 
        'approved', 'deploying', 'deployed', 'delivered', 'archived'
    )),
    
    -- Tracking
    estimated_price DECIMAL(10,2),
    api_cost DECIMAL(10,6) DEFAULT 0,
    
    -- URLs
    preview_url TEXT,
    production_url TEXT,
    github_repo TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create indexes for vibe_projects
CREATE INDEX IF NOT EXISTS idx_vibe_projects_user ON vibe_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_vibe_projects_status ON vibe_projects(status);
CREATE INDEX IF NOT EXISTS idx_vibe_projects_created ON vibe_projects(created_at DESC);

-- Create vibe_files table
CREATE TABLE IF NOT EXISTS vibe_files (
    file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES vibe_projects(project_id) ON DELETE CASCADE,
    
    file_path TEXT NOT NULL,
    content TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for vibe_files
CREATE INDEX IF NOT EXISTS idx_vibe_files_project ON vibe_files(project_id);
CREATE INDEX IF NOT EXISTS idx_vibe_files_path ON vibe_files(project_id, file_path);

-- Create vibe_lessons table for learning system
CREATE TABLE IF NOT EXISTS vibe_lessons (
    lesson_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES vibe_projects(project_id) ON DELETE SET NULL,
    
    -- Lesson categorization
    project_type TEXT NOT NULL,
    lesson_category TEXT NOT NULL CHECK (lesson_category IN (
        'design', 'content', 'seo', 'code', 'architecture',
        'client_feedback', 'performance', 'accessibility', 'ux'
    )),
    
    -- Lesson content
    issue TEXT NOT NULL,
    solution TEXT NOT NULL,
    impact TEXT DEFAULT 'medium' CHECK (impact IN ('high', 'medium', 'low')),
    
    -- Searchability
    tags TEXT[] DEFAULT '{}',
    embedding VECTOR(1536),
    
    -- Validation
    validated BOOLEAN DEFAULT FALSE,
    validated_by BIGINT,
    
    -- Usage tracking
    times_applied INTEGER DEFAULT 0,
    last_applied TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for vibe_lessons
CREATE INDEX IF NOT EXISTS idx_vibe_lessons_project_type ON vibe_lessons(project_type);
CREATE INDEX IF NOT EXISTS idx_vibe_lessons_category ON vibe_lessons(lesson_category);

-- Create vector index for lessons if pgvector is available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_vibe_lessons_embedding ON vibe_lessons USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Vector index creation skipped (pgvector may not be available)';
END $$;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE vibe_projects IS 'AlphaWave Vibe projects - websites, chatbots, integrations';
COMMENT ON TABLE vibe_files IS 'Generated code files for Vibe projects';
COMMENT ON TABLE vibe_lessons IS 'Learning system - extracted lessons from completed projects';

COMMENT ON COLUMN vibe_projects.brief IS 'Client requirements gathered during intake (JSON)';
COMMENT ON COLUMN vibe_projects.architecture IS 'Technical architecture spec from Opus (JSON)';
COMMENT ON COLUMN vibe_projects.config IS 'Build configuration (colors, fonts, etc.)';
COMMENT ON COLUMN vibe_projects.api_cost IS 'Cumulative API costs for this project';




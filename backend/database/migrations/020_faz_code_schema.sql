-- ============================================================================
-- FAZ CODE SCHEMA - AI-Powered Web Development Platform
-- Migration: 020
-- Date: December 16, 2025
-- 
-- This migration creates the complete Faz Code schema for:
-- - Project management
-- - Agent pipeline orchestration
-- - Learning system (errors, artifacts, skills)
-- - QA scoring
-- ============================================================================

-- Ensure extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- TABLE 1: faz_projects
-- Core project table with full lifecycle tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Basic info
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Input
    original_prompt TEXT NOT NULL,
    parsed_requirements JSONB DEFAULT '{}',
    target_audience TEXT,
    design_preferences JSONB DEFAULT '{}',
    
    -- Architecture (from planning agent)
    architecture JSONB DEFAULT '{}',
    tech_stack JSONB DEFAULT '{
        "framework": "nextjs",
        "styling": "tailwind",
        "database": null,
        "auth": null
    }',
    design_tokens JSONB DEFAULT '{}',
    
    -- Status tracking
    status VARCHAR(30) NOT NULL DEFAULT 'intake' CHECK (status IN (
        'intake', 'planning', 'researching', 'designing', 'building', 
        'qa', 'review', 'approved', 'deploying', 'deployed', 'delivered', 'archived'
    )),
    status_history JSONB DEFAULT '[]',
    current_agent VARCHAR(50),
    
    -- Deployment
    vercel_project_id VARCHAR(100),
    vercel_deployment_url TEXT,
    github_repo TEXT,
    preview_url TEXT,
    production_url TEXT,
    custom_domain VARCHAR(255),
    
    -- Cost tracking
    total_tokens_used INTEGER DEFAULT 0,
    total_cost_cents INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    
    CONSTRAINT faz_projects_slug_unique UNIQUE (user_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_faz_projects_user ON faz_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_faz_projects_status ON faz_projects(status);
CREATE INDEX IF NOT EXISTS idx_faz_projects_created ON faz_projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_faz_projects_slug ON faz_projects(slug);

-- ============================================================================
-- TABLE 2: faz_files
-- Generated code files with version tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_files (
    file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- File identification
    path VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    extension VARCHAR(20),
    
    -- Content
    content TEXT NOT NULL,
    content_hash VARCHAR(64),
    
    -- Metadata
    file_type VARCHAR(50), -- component, page, config, style, asset
    language VARCHAR(50), -- typescript, css, json
    line_count INTEGER DEFAULT 0,
    
    -- Generation tracking
    generated_by VARCHAR(50),
    generation_prompt TEXT,
    generation_model VARCHAR(100),
    
    -- Version tracking
    version INTEGER DEFAULT 1,
    previous_version_id BIGINT REFERENCES faz_files(file_id),
    
    -- Status
    status VARCHAR(30) DEFAULT 'generated' CHECK (status IN (
        'generated', 'modified', 'approved', 'error', 'deleted'
    )),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT faz_files_path_version_unique UNIQUE (project_id, path, version)
);

CREATE INDEX IF NOT EXISTS idx_faz_files_project ON faz_files(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_files_path ON faz_files(project_id, path);
CREATE INDEX IF NOT EXISTS idx_faz_files_type ON faz_files(file_type);
CREATE INDEX IF NOT EXISTS idx_faz_files_generated_by ON faz_files(generated_by);

-- ============================================================================
-- TABLE 3: faz_agent_activities
-- Complete audit trail of all agent actions
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_agent_activities (
    activity_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- Agent identification
    agent_name VARCHAR(50) NOT NULL,
    agent_model VARCHAR(100) NOT NULL,
    
    -- Activity details
    activity_type VARCHAR(50) NOT NULL CHECK (activity_type IN (
        'route', 'analyze', 'generate', 'review', 'approve', 'reject',
        'error', 'learn', 'tool_call', 'handoff', 'thinking', 'complete'
    )),
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    
    -- For chat display
    content_type VARCHAR(30) DEFAULT 'status', -- status, thinking, response, tool_call, error
    full_content TEXT,
    
    -- Token tracking
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_cents NUMERIC(10,4) DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN (
        'running', 'complete', 'error', 'cancelled'
    )),
    error_message TEXT,
    
    -- Handoff tracking
    handed_off_to VARCHAR(50),
    handoff_payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_faz_activities_project ON faz_agent_activities(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_activities_agent ON faz_agent_activities(agent_name);
CREATE INDEX IF NOT EXISTS idx_faz_activities_time ON faz_agent_activities(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_faz_activities_type ON faz_agent_activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_faz_activities_project_time ON faz_agent_activities(project_id, started_at DESC);

-- ============================================================================
-- TABLE 4: faz_code_memories
-- Persistent memory system (Letta/Mem0 style)
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_code_memories (
    memory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES faz_projects(project_id) ON DELETE SET NULL,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Memory content
    memory_type VARCHAR(50) NOT NULL CHECK (memory_type IN (
        'conversation', 'decision', 'pattern', 'preference', 'context', 'error', 'success'
    )),
    content TEXT NOT NULL,
    summary TEXT,
    
    -- Embedding for vector search
    embedding VECTOR(1536),
    
    -- Memory tier
    memory_tier VARCHAR(20) DEFAULT 'session' CHECK (memory_tier IN (
        'session', 'project', 'global'
    )),
    
    -- Importance scoring
    importance_score FLOAT DEFAULT 0.5,
    stability_score FLOAT DEFAULT 0.5,
    
    -- Access tracking
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    
    -- Decay management
    decay_rate FLOAT DEFAULT 0.1,
    
    -- Source tracking
    source_agent VARCHAR(50),
    source_activity_id BIGINT REFERENCES faz_agent_activities(activity_id),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_memories_project ON faz_code_memories(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_memories_user ON faz_code_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_faz_memories_tier ON faz_code_memories(memory_tier);
CREATE INDEX IF NOT EXISTS idx_faz_memories_type ON faz_code_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_faz_memories_embedding ON faz_code_memories 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- TABLE 5: faz_error_solutions
-- Learning from past errors (auto-populated by memory agent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_error_solutions (
    solution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    -- Error identification
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    error_code VARCHAR(50),
    stack_trace TEXT,
    
    -- Context
    file_path VARCHAR(500),
    code_before TEXT,
    code_after TEXT,
    surrounding_context TEXT,
    
    -- Solution
    solution_description TEXT NOT NULL,
    solution_steps JSONB DEFAULT '[]',
    
    -- Embedding for similarity search
    error_embedding VECTOR(1536),
    
    -- Success tracking
    times_suggested INTEGER DEFAULT 0,
    times_accepted INTEGER DEFAULT 0,
    times_rejected INTEGER DEFAULT 0,
    
    -- Metadata
    framework VARCHAR(100) DEFAULT 'nextjs',
    language VARCHAR(50) DEFAULT 'typescript',
    tags TEXT[] DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_faz_errors_type ON faz_error_solutions(error_type);
CREATE INDEX IF NOT EXISTS idx_faz_errors_framework ON faz_error_solutions(framework);
CREATE INDEX IF NOT EXISTS idx_faz_errors_embedding ON faz_error_solutions 
    USING ivfflat (error_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_faz_errors_tags ON faz_error_solutions USING GIN(tags);

-- ============================================================================
-- TABLE 6: faz_code_artifacts
-- Reusable code components extracted from successful projects
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_code_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    -- Identification
    artifact_type VARCHAR(50) NOT NULL CHECK (artifact_type IN (
        'component', 'hook', 'utility', 'integration', 'template', 'pattern', 'layout'
    )),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    
    -- Content
    code TEXT NOT NULL,
    description TEXT,
    usage_example TEXT,
    
    -- Classification
    framework VARCHAR(100) DEFAULT 'nextjs',
    language VARCHAR(50) DEFAULT 'typescript',
    category VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    
    -- Dependencies
    dependencies JSONB DEFAULT '{}',
    peer_dependencies JSONB DEFAULT '{}',
    
    -- Embeddings
    description_embedding VECTOR(1536),
    code_embedding VECTOR(1536),
    
    -- Quality metrics
    times_used INTEGER DEFAULT 0,
    times_modified_after_use INTEGER DEFAULT 0,
    avg_satisfaction_score FLOAT,
    
    -- Versioning
    version VARCHAR(20) DEFAULT '1.0.0',
    parent_artifact_id BIGINT REFERENCES faz_code_artifacts(artifact_id),
    is_latest BOOLEAN DEFAULT true,
    
    -- Source
    source_project_id BIGINT REFERENCES faz_projects(project_id),
    extracted_by VARCHAR(50),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT faz_artifacts_slug_unique UNIQUE (slug, version)
);

CREATE INDEX IF NOT EXISTS idx_faz_artifacts_type ON faz_code_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_category ON faz_code_artifacts(category);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_tags ON faz_code_artifacts USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_desc_embedding ON faz_code_artifacts 
    USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_code_embedding ON faz_code_artifacts 
    USING ivfflat (code_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_faz_artifacts_latest ON faz_code_artifacts(is_latest) WHERE is_latest = true;

-- ============================================================================
-- TABLE 7: faz_skill_library
-- Learned skills and approaches (Letta-style)
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_skill_library (
    skill_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    -- Skill identification
    skill_name VARCHAR(200) NOT NULL,
    skill_category VARCHAR(100) CHECK (skill_category IN (
        'architecture', 'styling', 'state_management', 'api_integration', 
        'testing', 'deployment', 'performance', 'accessibility', 'seo'
    )),
    
    -- Skill content
    description TEXT NOT NULL,
    approach TEXT NOT NULL,
    pitfalls TEXT[] DEFAULT '{}',
    verification_strategy TEXT,
    
    -- Example
    example_prompt TEXT,
    example_output TEXT,
    
    -- Embedding
    skill_embedding VECTOR(1536),
    
    -- Success tracking
    times_applied INTEGER DEFAULT 0,
    times_successful INTEGER DEFAULT 0,
    
    -- Source
    learned_from_project_id BIGINT REFERENCES faz_projects(project_id),
    
    -- Metadata
    applicable_frameworks TEXT[] DEFAULT ARRAY['nextjs'],
    difficulty_level VARCHAR(20) DEFAULT 'intermediate' CHECK (difficulty_level IN (
        'beginner', 'intermediate', 'advanced'
    )),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_skills_category ON faz_skill_library(skill_category);
CREATE INDEX IF NOT EXISTS idx_faz_skills_embedding ON faz_skill_library 
    USING ivfflat (skill_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_faz_skills_frameworks ON faz_skill_library USING GIN(applicable_frameworks);

-- ============================================================================
-- TABLE 8: faz_qa_scores
-- Quality assurance metrics per build
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_qa_scores (
    score_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- Lighthouse scores (0-100)
    performance_score INTEGER CHECK (performance_score BETWEEN 0 AND 100),
    accessibility_score INTEGER CHECK (accessibility_score BETWEEN 0 AND 100),
    best_practices_score INTEGER CHECK (best_practices_score BETWEEN 0 AND 100),
    seo_score INTEGER CHECK (seo_score BETWEEN 0 AND 100),
    
    -- Core Web Vitals
    first_contentful_paint_ms INTEGER,
    largest_contentful_paint_ms INTEGER,
    total_blocking_time_ms INTEGER,
    cumulative_layout_shift FLOAT,
    speed_index INTEGER,
    
    -- Issues found
    issues JSONB DEFAULT '[]',
    
    -- Screenshots
    desktop_screenshot_url TEXT,
    tablet_screenshot_url TEXT,
    mobile_screenshot_url TEXT,
    
    -- Test results
    test_results JSONB DEFAULT '{}',
    
    -- Run metadata
    run_number INTEGER DEFAULT 1,
    viewport VARCHAR(50),
    
    -- Overall
    all_passing BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_qa_project ON faz_qa_scores(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_qa_time ON faz_qa_scores(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_faz_qa_passing ON faz_qa_scores(all_passing);

-- ============================================================================
-- TABLE 9: faz_conversations
-- Chat history for each project
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_conversations (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES faz_projects(project_id) ON DELETE CASCADE,
    
    -- Message
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    
    -- Agent attribution
    agent_name VARCHAR(50),
    model_used VARCHAR(100),
    
    -- Tokens
    tokens_used INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faz_conv_project ON faz_conversations(project_id);
CREATE INDEX IF NOT EXISTS idx_faz_conv_time ON faz_conversations(created_at);

-- ============================================================================
-- TABLE 10: faz_user_preferences
-- Learned user preferences for personalization
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_user_preferences (
    pref_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Preference
    preference_type VARCHAR(50) NOT NULL CHECK (preference_type IN (
        'styling', 'framework', 'patterns', 'naming', 'structure', 'colors', 'fonts'
    )),
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT NOT NULL,
    
    -- Confidence
    confidence_score FLOAT DEFAULT 0.5,
    observation_count INTEGER DEFAULT 1,
    
    -- Examples
    examples JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT faz_prefs_unique UNIQUE (user_id, preference_type, preference_key)
);

CREATE INDEX IF NOT EXISTS idx_faz_prefs_user ON faz_user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_faz_prefs_type ON faz_user_preferences(preference_type);

-- ============================================================================
-- AGENT REGISTRY (Seed Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS faz_agent_registry (
    agent_id VARCHAR(50) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    agent_role VARCHAR(100) NOT NULL,
    
    -- Model assignment
    model_provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    
    -- Capabilities
    capabilities TEXT[] NOT NULL,
    available_tools TEXT[] DEFAULT '{}',
    
    -- Routing
    valid_handoff_targets TEXT[] DEFAULT '{}',
    receives_handoffs_from TEXT[] DEFAULT '{}',
    
    -- Configuration
    system_prompt TEXT,
    temperature NUMERIC(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed agent registry
INSERT INTO faz_agent_registry (agent_id, agent_name, agent_role, model_provider, model_name, capabilities, available_tools, valid_handoff_targets, receives_handoffs_from)
VALUES 
    ('nicole', 'Nicole', 'Orchestrator', 'anthropic', 'claude-opus-4-5-20251101',
     ARRAY['routing', 'intent_analysis', 'conflict_resolution', 'user_communication'],
     ARRAY[]::TEXT[],
     ARRAY['planning', 'research', 'design', 'coding', 'qa', 'review'],
     ARRAY[]::TEXT[]),
     
    ('planning', 'Planning Agent', 'Architect', 'anthropic', 'claude-opus-4-5-20251101',
     ARRAY['architecture', 'file_structure', 'component_breakdown', 'api_design'],
     ARRAY['memory_search'],
     ARRAY['design', 'coding'],
     ARRAY['nicole', 'research']),
     
    ('research', 'Research Agent', 'Analyst', 'google', 'gemini-3-pro-preview',
     ARRAY['web_search', 'competitor_analysis', 'design_inspiration', 'screenshot_analysis'],
     ARRAY['brave_web_search', 'puppeteer_screenshot', 'puppeteer_navigate'],
     ARRAY['planning', 'design'],
     ARRAY['nicole']),
     
    ('design', 'Design Agent', 'Designer', 'google', 'gemini-3-pro-preview',
     ARRAY['color_theory', 'typography', 'component_design', 'responsive_layout', 'design_tokens'],
     ARRAY['brave_web_search'],
     ARRAY['coding'],
     ARRAY['nicole', 'planning', 'research']),
     
    ('coding', 'Coding Agent', 'Developer', 'google', 'gemini-3-pro-preview',
     ARRAY['code_generation', 'refactoring', 'debugging', 'file_operations'],
     ARRAY[]::TEXT[],
     ARRAY['qa'],
     ARRAY['nicole', 'planning', 'design']),
     
    ('qa', 'QA Agent', 'Tester', 'anthropic', 'claude-sonnet-4-5-20250929',
     ARRAY['lighthouse_audit', 'accessibility_scan', 'error_detection', 'screenshot_capture'],
     ARRAY['puppeteer_screenshot', 'puppeteer_navigate', 'puppeteer_evaluate'],
     ARRAY['coding', 'review'],
     ARRAY['coding']),
     
    ('review', 'Review Agent', 'Reviewer', 'anthropic', 'claude-opus-4-5-20251101',
     ARRAY['code_review', 'security_audit', 'best_practices', 'final_approval'],
     ARRAY[]::TEXT[],
     ARRAY['coding'],
     ARRAY['qa']),
     
    ('memory', 'Memory Agent', 'Learning', 'openai', 'gpt-5-codex',
     ARRAY['error_extraction', 'skill_learning', 'preference_detection', 'artifact_storage'],
     ARRAY[]::TEXT[],
     ARRAY[]::TEXT[],
     ARRAY['nicole', 'coding', 'qa', 'review'])
ON CONFLICT (agent_id) DO UPDATE SET
    model_name = EXCLUDED.model_name,
    capabilities = EXCLUDED.capabilities,
    available_tools = EXCLUDED.available_tools,
    valid_handoff_targets = EXCLUDED.valid_handoff_targets,
    receives_handoffs_from = EXCLUDED.receives_handoffs_from,
    updated_at = NOW();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE faz_projects IS 'Faz Code projects - AI-generated websites';
COMMENT ON TABLE faz_files IS 'Generated code files with version tracking';
COMMENT ON TABLE faz_agent_activities IS 'Audit trail of all agent activities';
COMMENT ON TABLE faz_code_memories IS 'Persistent memory system for learning';
COMMENT ON TABLE faz_error_solutions IS 'Learned error solutions for auto-fix';
COMMENT ON TABLE faz_code_artifacts IS 'Reusable code components extracted from projects';
COMMENT ON TABLE faz_skill_library IS 'Learned skills and approaches';
COMMENT ON TABLE faz_qa_scores IS 'Quality assurance metrics';
COMMENT ON TABLE faz_conversations IS 'Chat history per project';
COMMENT ON TABLE faz_user_preferences IS 'Learned user preferences';
COMMENT ON TABLE faz_agent_registry IS 'Agent configuration and routing rules';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count 
    FROM information_schema.tables 
    WHERE table_name LIKE 'faz_%';
    
    IF table_count < 10 THEN
        RAISE EXCEPTION 'Migration incomplete: only % faz_* tables created', table_count;
    END IF;
    
    RAISE NOTICE 'Faz Code schema created successfully: % tables', table_count;
END $$;



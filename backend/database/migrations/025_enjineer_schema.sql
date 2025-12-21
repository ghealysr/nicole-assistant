-- ============================================================================
-- ENJINEER DATABASE SCHEMA
-- Migration 025: Core tables for the Enjineer AI coding dashboard
-- ============================================================================

-- Projects table
CREATE TABLE IF NOT EXISTS enjineer_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    tech_stack JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active' 
        CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    conversation_id UUID,
    intake_data JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Plan versions
CREATE TABLE IF NOT EXISTS enjineer_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'awaiting_approval', 'approved', 'in_progress', 'completed', 'abandoned')),
    current_phase_number INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(project_id, version)
);

-- Plan phases
CREATE TABLE IF NOT EXISTS enjineer_plan_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES enjineer_plans(id) ON DELETE CASCADE,
    phase_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'complete', 'blocked', 'skipped')),
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    agents_required TEXT[] DEFAULT '{}',
    qa_depth TEXT DEFAULT 'standard' CHECK (qa_depth IN ('light', 'standard', 'thorough')),
    qa_focus TEXT[] DEFAULT '{}',
    requires_approval BOOLEAN NOT NULL DEFAULT false,
    approval_status TEXT CHECK (approval_status IN ('pending', 'approved', 'changes_requested')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    notes TEXT,
    UNIQUE(plan_id, phase_number)
);

-- Virtual file system
CREATE TABLE IF NOT EXISTS enjineer_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    content TEXT,
    language TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    modified_by TEXT,
    locked_by TEXT,
    lock_expires_at TIMESTAMPTZ,
    checksum TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, path)
);

-- File version history
CREATE TABLE IF NOT EXISTS enjineer_file_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES enjineer_files(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    modified_by TEXT NOT NULL,
    diff_from_previous TEXT,
    commit_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(file_id, version)
);

-- Agent executions
CREATE TABLE IF NOT EXISTS enjineer_agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES enjineer_plans(id),
    phase_number INTEGER,
    agent_type TEXT NOT NULL CHECK (agent_type IN ('qa', 'engineer', 'sr_qa', 'nicole')),
    instruction TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    focus_areas TEXT[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'success', 'partial', 'failed', 'cancelled')),
    result JSONB,
    error_message TEXT,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    duration_seconds FLOAT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- QA reports
CREATE TABLE IF NOT EXISTS enjineer_qa_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    execution_id UUID REFERENCES enjineer_agent_executions(id),
    plan_id UUID REFERENCES enjineer_plans(id),
    phase_number INTEGER,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('phase_complete', 'manual', 'pre_deploy', 'scheduled')),
    qa_depth TEXT NOT NULL,
    overall_status TEXT NOT NULL CHECK (overall_status IN ('pass', 'fail', 'partial')),
    checks JSONB NOT NULL DEFAULT '[]',
    summary TEXT,
    blocking_issues_count INTEGER DEFAULT 0,
    warnings_count INTEGER DEFAULT 0,
    passed_count INTEGER DEFAULT 0,
    screenshots JSONB DEFAULT '[]',
    duration_seconds FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Approvals
CREATE TABLE IF NOT EXISTS enjineer_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    approval_type TEXT NOT NULL 
        CHECK (approval_type IN ('plan', 'phase', 'agent', 'deploy', 'destructive', 'qa_override')),
    reference_type TEXT,
    reference_id UUID,
    title TEXT NOT NULL,
    description TEXT,
    context JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    response_note TEXT
);

-- Deployments
CREATE TABLE IF NOT EXISTS enjineer_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('vercel', 'digitalocean', 'other')),
    platform_deployment_id TEXT,
    environment TEXT DEFAULT 'production' CHECK (environment IN ('preview', 'staging', 'production')),
    url TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'building', 'deploying', 'success', 'failed', 'cancelled')),
    build_log TEXT,
    error_message TEXT,
    commit_sha TEXT,
    duration_seconds FLOAT,
    deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Assets
CREATE TABLE IF NOT EXISTS enjineer_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL 
        CHECK (asset_type IN ('inspiration', 'generated', 'screenshot', 'reference')),
    url TEXT NOT NULL,
    thumbnail_url TEXT,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Session state (for resume)
CREATE TABLE IF NOT EXISTS enjineer_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    state JSONB NOT NULL DEFAULT '{}',
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

-- Chat messages (for conversation history)
CREATE TABLE IF NOT EXISTS enjineer_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_enjineer_projects_user ON enjineer_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_enjineer_projects_status ON enjineer_projects(status);
CREATE INDEX IF NOT EXISTS idx_enjineer_plans_project ON enjineer_plans(project_id);
CREATE INDEX IF NOT EXISTS idx_enjineer_plans_status ON enjineer_plans(project_id, status);
CREATE INDEX IF NOT EXISTS idx_enjineer_files_project ON enjineer_files(project_id);
CREATE INDEX IF NOT EXISTS idx_enjineer_files_path ON enjineer_files(project_id, path);
CREATE INDEX IF NOT EXISTS idx_enjineer_files_locked ON enjineer_files(project_id) WHERE locked_by IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_enjineer_agent_executions_project ON enjineer_agent_executions(project_id);
CREATE INDEX IF NOT EXISTS idx_enjineer_agent_executions_status ON enjineer_agent_executions(project_id, status);
CREATE INDEX IF NOT EXISTS idx_enjineer_qa_reports_project ON enjineer_qa_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_enjineer_approvals_pending ON enjineer_approvals(project_id, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_enjineer_deployments_project ON enjineer_deployments(project_id);
CREATE INDEX IF NOT EXISTS idx_enjineer_sessions_project ON enjineer_sessions(project_id, user_id);
CREATE INDEX IF NOT EXISTS idx_enjineer_messages_project ON enjineer_messages(project_id);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION enjineer_update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS enjineer_projects_updated_at ON enjineer_projects;
CREATE TRIGGER enjineer_projects_updated_at
    BEFORE UPDATE ON enjineer_projects
    FOR EACH ROW EXECUTE FUNCTION enjineer_update_updated_at();

DROP TRIGGER IF EXISTS enjineer_files_updated_at ON enjineer_files;
CREATE TRIGGER enjineer_files_updated_at
    BEFORE UPDATE ON enjineer_files
    FOR EACH ROW EXECUTE FUNCTION enjineer_update_updated_at();


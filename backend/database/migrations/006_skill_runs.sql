-- Skill run history table
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS skill_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    conversation_id INTEGER,
    status TEXT NOT NULL,
    environment TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    duration_seconds DOUBLE PRECISION,
    log_path TEXT,
    output_preview TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS skill_runs_skill_id_idx ON skill_runs (skill_id);
CREATE INDEX IF NOT EXISTS skill_runs_user_id_idx ON skill_runs (user_id);
CREATE INDEX IF NOT EXISTS skill_runs_created_at_idx ON skill_runs (created_at DESC);


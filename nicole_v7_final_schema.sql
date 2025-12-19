-- ============================================================================
-- NICOLE V7 FINAL SCHEMA (Tiger/Timescale Production)
-- ============================================================================
-- Version: 3.0-Eden (Cognitive Architecture)
-- Combines: V2 baseline + Creative enhancements from technical review
-- Features: Temporal awareness, memory graph, dream synthesis, lifelong learning
-- ============================================================================

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgvectorscale CASCADE;

-- ============================================================================
-- ENUMS (Type Safety)
-- ============================================================================

CREATE TYPE user_role_enum AS ENUM ('admin', 'user', 'family_member', 'child');
CREATE TYPE conversation_status_enum AS ENUM ('active', 'archived', 'deleted');
CREATE TYPE message_role_enum AS ENUM ('user', 'assistant', 'system');
CREATE TYPE memory_type_enum AS ENUM ('identity', 'preference', 'event', 'relationship', 'workflow', 'insight');
CREATE TYPE correction_status_enum AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE feedback_type_enum AS ENUM ('positive', 'negative', 'correction');
CREATE TYPE sport_enum AS ENUM ('nfl', 'nba', 'mlb', 'nhl', 'mma', 'boxing');
CREATE TYPE prediction_outcome_enum AS ENUM ('win', 'loss', 'push', 'pending');
CREATE TYPE job_status_enum AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE emotion_enum AS ENUM ('joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust', 'trust', 'anticipation', 'nostalgia', 'stress', 'curiosity', 'calm', 'excited', 'frustrated');
CREATE TYPE dream_tone_enum AS ENUM ('hopeful', 'melancholic', 'anxious', 'peaceful', 'energetic', 'reflective');

-- ============================================================================
-- SCHEMA VERSIONING
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_versions (
    version_id SERIAL PRIMARY KEY,
    version_name TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    description TEXT
);

INSERT INTO schema_versions (version_name, description) 
VALUES ('3.0-Eden', 'Cognitive architecture with temporal awareness, memory graph, and dream synthesis')
ON CONFLICT (version_name) DO NOTHING;

-- ============================================================================
-- TRIGGER FUNCTION (updated_at)
-- ============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CORE USER & CONVERSATION TABLES (4 tables)
-- ============================================================================

-- 1. Users
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    auth_id TEXT UNIQUE,
    user_role user_role_enum NOT NULL DEFAULT 'user',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER t_users_updated
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 2. Conversations
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT,
    conversation_status conversation_status_enum NOT NULL DEFAULT 'active',
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations (user_id, conversation_status, updated_at DESC);

CREATE TRIGGER t_conversations_updated
BEFORE UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 3. Messages (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message_role message_role_enum NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    emotion emotion_enum,
    tokens_input INTEGER CHECK (tokens_input >= 0),
    tokens_output INTEGER CHECK (tokens_output >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_user_time ON messages (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_emotion ON messages (emotion) WHERE emotion IS NOT NULL;

SELECT create_hypertable('messages', 'created_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 days');

ALTER TABLE messages SET (timescaledb.compress, 
    timescaledb.compress_segmentby = 'user_id,conversation_id',
    timescaledb.compress_orderby = 'created_at DESC'
);

SELECT add_compression_policy('messages', INTERVAL '30 days', if_not_exists => TRUE);

-- 4. Conversation Summaries
CREATE TABLE IF NOT EXISTS conversation_summaries (
    summary_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    key_topics TEXT[],
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_summaries_conversation ON conversation_summaries (conversation_id);

-- ============================================================================
-- MEMORY SYSTEM WITH TEMPORAL AWARENESS (7 tables)
-- ============================================================================

-- 5. Memory Entries (Enhanced with temporal awareness)
CREATE TABLE IF NOT EXISTS memory_entries (
    memory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    memory_type memory_type_enum NOT NULL,
    category TEXT,
    embedding vector(1536),
    embedding_v2 vector(768), -- For future compressed embeddings
    confidence NUMERIC(4,3) CHECK (confidence >= 0 AND confidence <= 1),
    importance NUMERIC(4,3) CHECK (importance >= 0 AND importance <= 1),
    access_count INTEGER DEFAULT 0 CHECK (access_count >= 0),
    last_accessed TIMESTAMPTZ,
    is_time_bound BOOLEAN DEFAULT FALSE,
    expiration_date DATE,
    epoch_id INTEGER DEFAULT 1, -- Memory epoch for consolidation
    source_conversation_id BIGINT REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    source_message_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at TIMESTAMPTZ,
    created_by TEXT DEFAULT 'assistant'
);

CREATE INDEX IF NOT EXISTS idx_memory_user_type ON memory_entries (user_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_confidence ON memory_entries (confidence DESC) WHERE archived_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory_entries (importance DESC) WHERE archived_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_memory_epoch ON memory_entries (user_id, epoch_id);
CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memory_entries (last_accessed DESC NULLS LAST);

-- Vector search indexes (both current and future compressed)
CREATE INDEX IF NOT EXISTS idx_memory_embedding ON memory_entries 
    USING diskann (embedding) 
    WHERE archived_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_memory_embedding_v2 ON memory_entries 
    USING diskann (embedding_v2) 
    WHERE embedding_v2 IS NOT NULL AND archived_at IS NULL;

CREATE TRIGGER t_memory_updated
BEFORE UPDATE ON memory_entries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 6. Memory Links (Associative graph for creative reasoning)
CREATE TABLE IF NOT EXISTS memory_links (
    link_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_memory_id BIGINT NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    target_memory_id BIGINT NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    weight NUMERIC(4,3) CHECK (weight >= 0 AND weight <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT DEFAULT 'assistant',
    UNIQUE(source_memory_id, target_memory_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_memory_links_source ON memory_links (source_memory_id, weight DESC);
CREATE INDEX IF NOT EXISTS idx_memory_links_target ON memory_links (target_memory_id, weight DESC);
CREATE INDEX IF NOT EXISTS idx_memory_links_type ON memory_links (relationship_type);

-- 7. Memory Snapshots (Temporal summaries)
CREATE TABLE IF NOT EXISTS memory_snapshots (
    snapshot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    summary_text TEXT NOT NULL,
    summary_vector vector(1536),
    memory_count INTEGER CHECK (memory_count >= 0),
    dominant_themes TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_user_date ON memory_snapshots (user_id, snapshot_date DESC);

-- 8. Corrections
CREATE TABLE IF NOT EXISTS corrections (
    correction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    memory_id BIGINT REFERENCES memory_entries(memory_id) ON DELETE SET NULL,
    old_content TEXT NOT NULL,
    new_content TEXT NOT NULL,
    correction_status correction_status_enum NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT DEFAULT 'user'
);

CREATE INDEX IF NOT EXISTS idx_corrections_user_status ON corrections (user_id, correction_status);
CREATE INDEX IF NOT EXISTS idx_corrections_memory ON corrections (memory_id);

-- 9. Memory Feedback
CREATE TABLE IF NOT EXISTS memory_feedback (
    feedback_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    memory_id BIGINT REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    feedback_type feedback_type_enum NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_memory ON memory_feedback (memory_id);

-- 10. Dreams (Creative memory synthesis)
CREATE TABLE IF NOT EXISTS dreams (
    dream_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    seed_memory_ids BIGINT[],
    generated_story TEXT NOT NULL,
    emotional_tone dream_tone_enum NOT NULL,
    themes TEXT[],
    insights JSONB,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT DEFAULT 'assistant'
);

CREATE INDEX IF NOT EXISTS idx_dreams_user_date ON dreams (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dreams_tone ON dreams (emotional_tone);

-- 11. Contextual Links (Cross-modal memory stitching)
CREATE TABLE IF NOT EXISTS contextual_links (
    link_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    memory_id BIGINT REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    photo_id BIGINT,
    journal_id BIGINT,
    spotify_track_id BIGINT,
    context_description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contextual_memory ON contextual_links (memory_id);
CREATE INDEX IF NOT EXISTS idx_contextual_photo ON contextual_links (photo_id) WHERE photo_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contextual_journal ON contextual_links (journal_id) WHERE journal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contextual_music ON contextual_links (spotify_track_id) WHERE spotify_track_id IS NOT NULL;

-- ============================================================================
-- LIFE TRACKING & PATTERNS (3 tables)
-- ============================================================================

-- 12. Daily Journals
CREATE TABLE IF NOT EXISTS daily_journals (
    journal_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    journal_date DATE NOT NULL,
    content TEXT NOT NULL,
    mood emotion_enum,
    sentiment_score NUMERIC(4,3) CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, journal_date)
);

CREATE INDEX IF NOT EXISTS idx_journals_user_date ON daily_journals (user_id, journal_date DESC);
CREATE INDEX IF NOT EXISTS idx_journals_mood ON daily_journals (mood) WHERE mood IS NOT NULL;

CREATE TRIGGER t_journals_updated
BEFORE UPDATE ON daily_journals
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 13. Spotify Tracks (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS spotify_tracks (
    track_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    spotify_track_id TEXT NOT NULL,
    track_name TEXT NOT NULL,
    artist_name TEXT NOT NULL,
    played_at TIMESTAMPTZ NOT NULL,
    duration_ms INTEGER CHECK (duration_ms > 0),
    valence NUMERIC(4,3) CHECK (valence >= 0 AND valence <= 1),
    energy NUMERIC(4,3) CHECK (energy >= 0 AND energy <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, spotify_track_id, played_at)
);

CREATE INDEX IF NOT EXISTS idx_spotify_user_time ON spotify_tracks (user_id, played_at DESC);
CREATE INDEX IF NOT EXISTS idx_spotify_valence ON spotify_tracks (valence) WHERE valence IS NOT NULL;

SELECT create_hypertable('spotify_tracks', 'played_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '30 days');

ALTER TABLE spotify_tracks SET (timescaledb.compress);
SELECT add_compression_policy('spotify_tracks', INTERVAL '90 days', if_not_exists => TRUE);

-- 14. Health Metrics (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS health_metrics (
    metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    sleep_hours NUMERIC(4,2) CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
    steps INTEGER CHECK (steps >= 0),
    heart_rate_avg INTEGER CHECK (heart_rate_avg >= 0),
    workout_minutes INTEGER CHECK (workout_minutes >= 0),
    weight NUMERIC(5,2) CHECK (weight >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_health_user_date ON health_metrics (user_id, metric_date DESC);

SELECT create_hypertable('health_metrics', 'created_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '30 days');

ALTER TABLE health_metrics SET (timescaledb.compress);
SELECT add_compression_policy('health_metrics', INTERVAL '180 days', if_not_exists => TRUE);

-- ============================================================================
-- FAMILY MANAGEMENT (3 tables)
-- ============================================================================

-- 15. Family Members
CREATE TABLE IF NOT EXISTS family_members (
    member_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    birth_date DATE,
    contact_info JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_family_user ON family_members (user_id);

-- 16. Family Events
CREATE TABLE IF NOT EXISTS family_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    event_date DATE NOT NULL,
    description TEXT,
    attendees BIGINT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_user_date ON family_events (user_id, event_date DESC);

-- 17. Allowances
CREATE TABLE IF NOT EXISTS allowances (
    allowance_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    child_id BIGINT NOT NULL REFERENCES family_members(member_id) ON DELETE CASCADE,
    amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    payment_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_allowances_child_date ON allowances (child_id, payment_date DESC);

-- ============================================================================
-- BUSINESS MANAGEMENT (3 tables)
-- ============================================================================

-- 18. Clients
CREATE TABLE IF NOT EXISTS clients (
    client_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    client_name TEXT NOT NULL,
    company TEXT,
    contact_info JSONB,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_clients_user ON clients (user_id, updated_at DESC);

CREATE TRIGGER t_clients_updated
BEFORE UPDATE ON clients
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 19. Projects
CREATE TABLE IF NOT EXISTS projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    client_id BIGINT REFERENCES clients(client_id) ON DELETE SET NULL,
    project_name TEXT NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    project_status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_user_status ON projects (user_id, project_status, updated_at DESC);

CREATE TRIGGER t_projects_updated
BEFORE UPDATE ON projects
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 20. Tasks
CREATE TABLE IF NOT EXISTS tasks (
    task_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES projects(project_id) ON DELETE CASCADE,
    task_title TEXT NOT NULL,
    description TEXT,
    due_date DATE,
    task_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks (user_id, task_status, due_date);

CREATE TRIGGER t_tasks_updated
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- FILE & MEDIA MANAGEMENT (5 tables)
-- ============================================================================

-- 21. Uploaded Files
CREATE TABLE IF NOT EXISTS uploaded_files (
    file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER CHECK (file_size >= 0),
    upload_source TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_files_user_date ON uploaded_files (user_id, created_at DESC);

-- 22. Photos
CREATE TABLE IF NOT EXISTS photos (
    photo_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_id BIGINT REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
    caption TEXT,
    taken_at TIMESTAMPTZ,
    location TEXT,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_photos_user_date ON photos (user_id, taken_at DESC NULLS LAST);

-- 23. Photo Memories
CREATE TABLE IF NOT EXISTS photo_memories (
    photo_memory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    photo_id BIGINT NOT NULL REFERENCES photos(photo_id) ON DELETE CASCADE,
    memory_text TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_photo_memories_photo ON photo_memories (photo_id);

-- 24. Document Repository
CREATE TABLE IF NOT EXISTS document_repository (
    doc_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_id BIGINT REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    doc_type TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_docs_user_type ON document_repository (user_id, doc_type, updated_at DESC);

CREATE TRIGGER t_docs_updated
BEFORE UPDATE ON document_repository
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 25. Document Chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doc_id BIGINT NOT NULL REFERENCES document_repository(doc_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks (doc_id, chunk_index);

-- ============================================================================
-- CREATIVE OUTPUT (1 table)
-- ============================================================================

-- 26. Generated Artifacts
CREATE TABLE IF NOT EXISTS generated_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    prompt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_user_type ON generated_artifacts (user_id, artifact_type, created_at DESC);

-- ============================================================================
-- SPORTS BETTING (4 tables)
-- ============================================================================

-- 27. Sports Predictions
CREATE TABLE IF NOT EXISTS sports_predictions (
    prediction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    sport sport_enum NOT NULL,
    event_name TEXT NOT NULL,
    prediction_date DATE NOT NULL,
    prediction_details JSONB NOT NULL,
    bet_amount NUMERIC(10,2) CHECK (bet_amount > 0),
    outcome prediction_outcome_enum DEFAULT 'pending',
    profit_loss NUMERIC(10,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    created_by TEXT DEFAULT 'assistant'
);

CREATE INDEX IF NOT EXISTS idx_predictions_user_date ON sports_predictions (user_id, prediction_date DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_outcome ON sports_predictions (outcome) WHERE outcome IS NOT NULL;

-- 28. Sports Data Cache
CREATE TABLE IF NOT EXISTS sports_data_cache (
    cache_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_type TEXT NOT NULL,
    sport sport_enum NOT NULL,
    data_date DATE NOT NULL,
    raw_data JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sports_cache_type_date ON sports_data_cache (data_type, sport, data_date DESC);

SELECT add_retention_policy('sports_data_cache', INTERVAL '90 days', if_not_exists => TRUE);

-- 29. Sports Learning Log
CREATE TABLE IF NOT EXISTS sports_learning_log (
    log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    review_date DATE NOT NULL,
    analysis TEXT NOT NULL,
    adjustments JSONB,
    performance_metrics JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sports_learning_user_date ON sports_learning_log (user_id, review_date DESC);

-- ============================================================================
-- PERSONAL HISTORY & SYSTEM TABLES (6 tables)
-- ============================================================================

-- 30. Life Story Entries
CREATE TABLE IF NOT EXISTS life_story_entries (
    entry_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    date_period TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_life_story_user_category ON life_story_entries (user_id, category);

-- 31. API Logs (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS api_logs (
    log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    api_name TEXT NOT NULL,
    endpoint TEXT,
    tokens_input INTEGER CHECK (tokens_input >= 0),
    tokens_output INTEGER CHECK (tokens_output >= 0),
    cost NUMERIC(10,6) CHECK (cost >= 0),
    latency_ms INTEGER CHECK (latency_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_logs_user_date ON api_logs (user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_logs_api_date ON api_logs (api_name, created_at DESC);

SELECT create_hypertable('api_logs', 'created_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');

ALTER TABLE api_logs SET (timescaledb.compress);
SELECT add_compression_policy('api_logs', INTERVAL '7 days', if_not_exists => TRUE);

-- 32. Scheduled Jobs
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    job_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_name TEXT NOT NULL UNIQUE,
    job_type TEXT NOT NULL,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    job_status job_status_enum NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_next ON scheduled_jobs (job_status, next_run) WHERE job_status != 'completed';

-- 33. Nicole Reflections
CREATE TABLE IF NOT EXISTS nicole_reflections (
    reflection_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    reflection_date DATE NOT NULL,
    reflection_type TEXT NOT NULL,
    content TEXT NOT NULL,
    insights JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reflections_user_date ON nicole_reflections (user_id, reflection_date DESC);

-- 34. Saved Dashboards
CREATE TABLE IF NOT EXISTS saved_dashboards (
    dashboard_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    dashboard_spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_dashboards_user ON saved_dashboards (user_id, last_used DESC NULLS LAST);

-- 35. Project Domains
CREATE TABLE IF NOT EXISTS project_domains (
    domain_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    project_name TEXT NOT NULL,
    domain_type TEXT NOT NULL,
    notion_database_id TEXT,
    notion_page_id TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_domains_user ON project_domains (user_id, updated_at DESC);

CREATE TRIGGER t_domains_updated
BEFORE UPDATE ON project_domains
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- MATERIALIZED VIEWS (Performance optimization)
-- ============================================================================

-- User Memory Context (Fast lookup for active memories)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_user_active_memories AS
SELECT 
    user_id,
    memory_type,
    COUNT(*) as memory_count,
    AVG(confidence) as avg_confidence,
    MAX(last_accessed) as most_recent_access
FROM memory_entries
WHERE archived_at IS NULL
GROUP BY user_id, memory_type;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_active_memories ON mv_user_active_memories (user_id, memory_type);

-- User Pattern Summary (Daily aggregates)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_user_patterns AS
SELECT 
    h.user_id,
    h.metric_date,
    h.sleep_hours,
    j.sentiment_score,
    COUNT(DISTINCT s.track_id) as songs_played,
    AVG(s.valence) as avg_music_valence
FROM health_metrics h
LEFT JOIN daily_journals j ON h.user_id = j.user_id AND h.metric_date = j.journal_date
LEFT JOIN spotify_tracks s ON h.user_id = s.user_id AND DATE(s.played_at) = h.metric_date
GROUP BY h.user_id, h.metric_date, h.sleep_hours, j.sentiment_score;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_patterns ON mv_user_patterns (user_id, metric_date DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE corrections ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE dreams ENABLE ROW LEVEL SECURITY;
ALTER TABLE contextual_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_journals ENABLE ROW LEVEL SECURITY;
ALTER TABLE spotify_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE allowances ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_repository ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sports_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sports_learning_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE life_story_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE nicole_reflections ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_domains ENABLE ROW LEVEL SECURITY;

-- User access policies (users own their data)
CREATE POLICY users_own_conversations ON conversations
    FOR ALL 
    USING (user_id = current_setting('app.current_user_id')::BIGINT);

CREATE POLICY users_own_messages ON messages
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::BIGINT);

CREATE POLICY users_own_memories ON memory_entries
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::BIGINT);

-- Admin access (can see all data)
CREATE POLICY admin_full_access ON conversations
    FOR ALL
    TO tsdbadmin
    USING (true);

CREATE POLICY admin_full_access_msgs ON messages
    FOR ALL
    TO tsdbadmin
    USING (true);

CREATE POLICY admin_full_access_mem ON memory_entries
    FOR ALL
    TO tsdbadmin
    USING (true);

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tsdbadmin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tsdbadmin;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO tsdbadmin;

-- ============================================================================
-- IMAGE GENERATION SYSTEM (Advanced Multi-Model Studio)
-- ============================================================================
-- Migration: 008_image_generation_system.sql
-- Features: Multi-model generation, job tracking, preset management
-- Models: Recraft V3, FLUX 1.1 Pro, Ideogram V2, Gemini Imagen 3, OpenAI DALL-E 3
-- ============================================================================

-- Jobs organize generations by project/use case
CREATE TABLE IF NOT EXISTS image_jobs (
    job_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    title TEXT NOT NULL,
    project TEXT,  -- "AlphaWave" | "Grace & Grit" | "Tampa Renegades" | NULL
    use_case TEXT,  -- "logo" | "hero" | "social" | "poster" | "icon" | "mockup"
    preset_used TEXT,  -- Which preset was used to start
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_jobs_user ON image_jobs(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_image_jobs_project ON image_jobs(project, use_case) WHERE project IS NOT NULL;

ALTER TABLE image_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "users_own_image_jobs" ON image_jobs FOR ALL USING (auth.uid() = user_id);

-- Variants are all generations belonging to a job
CREATE TABLE IF NOT EXISTS image_variants (
    variant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES image_jobs(job_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    version_number INTEGER NOT NULL,  -- v1, v2, v3...
    
    -- Model information
    model_key TEXT NOT NULL,  -- "recraft" | "flux_pro" | "flux_schnell" | "ideogram" | "imagen3" | "dall_e_3"
    model_version TEXT,  -- Model version string
    
    -- Prompts
    original_prompt TEXT NOT NULL,
    enhanced_prompt TEXT,  -- What AI enhanced it to
    negative_prompt TEXT,
    
    -- Parameters (full JSON for reproducibility)
    parameters JSONB NOT NULL,
    
    -- Output files (Cloudinary URLs for persistence)
    cdn_url TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    
    -- Metadata for nerd stats
    seed INTEGER,
    generation_time_ms INTEGER,  -- How long it took
    cost_usd NUMERIC(10, 4),  -- Actual cost
    replicate_prediction_id TEXT,  -- For debugging
    
    -- Hash for deduplication
    image_hash TEXT UNIQUE,
    
    -- User feedback
    is_favorite BOOLEAN DEFAULT FALSE,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_variants_job ON image_variants(job_id, version_number);
CREATE INDEX IF NOT EXISTS idx_image_variants_user ON image_variants(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_image_variants_hash ON image_variants(image_hash) WHERE image_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_image_variants_favorites ON image_variants(user_id, is_favorite) WHERE is_favorite = TRUE;

ALTER TABLE image_variants ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "users_own_image_variants" ON image_variants FOR ALL USING (auth.uid() = user_id);

-- Presets for quick generation
CREATE TABLE IF NOT EXISTS image_presets (
    preset_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    preset_key TEXT NOT NULL,  -- "aw_logo_vector", "grace_grit_ig"
    name TEXT NOT NULL,  -- "AW Logo - Vector Square"
    model_key TEXT NOT NULL,
    parameters JSONB NOT NULL,
    batch_count INTEGER DEFAULT 1,
    smart_prompt_enabled BOOLEAN DEFAULT TRUE,
    use_case TEXT,
    is_system BOOLEAN DEFAULT FALSE,  -- System vs user-created
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_image_presets_key ON image_presets(user_id, preset_key);
ALTER TABLE image_presets ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "users_own_presets" ON image_presets FOR ALL USING (auth.uid() = user_id);

-- ============================================================================
-- SUMMARY V3.0-EDEN
-- ============================================================================
-- Total Tables: 39 (38 data tables + schema_versions)
-- New Tables Added (vs V2):
--   âœ… memory_links (associative graph)
--   âœ… memory_snapshots (temporal summaries)
--   âœ… dreams (creative synthesis)
--   âœ… contextual_links (cross-modal stitching)
--   ✅ image_jobs (multi-model image generation tracking)
--   ✅ image_variants (generated images with full metadata)
--   ✅ image_presets (quick generation templates)
-- 
-- Enhanced Features:
--   âœ… Temporal awareness (epoch_id, access_count, last_accessed)
--   âœ… Memory decay architecture ready
--   âœ… Vector compression path (embedding_v2)
--   âœ… Emotion taxonomy (enum)
--   âœ… Materialized views for performance
--   âœ… Dream tone classification
--   âœ… Complete RLS policies
-- 
-- Cognitive Architecture Elements:
--   âœ… Memory graph for associative reasoning
--   âœ… Dream synthesis for creative consolidation
--   âœ… Cross-modal linking (photos+music+journals+memories)
--   âœ… Temporal snapshots for "who I was" tracking
--   âœ… Pattern detection foundation (materialized views)
-- 
-- Ready for: Lifelong learning, autonomous evolution, creative reasoning
-- ============================================================================

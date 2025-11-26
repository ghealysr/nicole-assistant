-- Nicole V7 - Complete Supabase Database Schema
-- Production-quality PostgreSQL schema with RLS policies

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================
-- USERS TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT CHECK (role IN ('admin', 'child', 'parent', 'standard')) DEFAULT 'standard',
    relationship TEXT CHECK (relationship IN ('creator', 'son', 'nicoles_mother', 'nicoles_father', 'friend', 'partner', 'family')),
    image_limit_weekly INTEGER DEFAULT 5 CHECK (image_limit_weekly >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE
);

-- RLS for users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_data" ON users
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "admin_access_users" ON users
    FOR ALL USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- ==============================================
-- CONVERSATIONS TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Conversation',
    knowledge_base_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC);

-- RLS for conversations
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_conversations" ON conversations
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "admin_access_conversations" ON conversations
    FOR ALL USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- ==============================================
-- MESSAGES TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant')) NOT NULL,
    content TEXT NOT NULL,
    emotion TEXT,
    attachments JSONB DEFAULT '{}'::jsonb,
    tool_calls JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- RLS for messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_messages" ON messages
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "admin_access_messages" ON messages
    FOR ALL USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- ==============================================
-- MEMORY ENTRIES TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS memory_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    memory_type TEXT CHECK (memory_type IN ('fact', 'preference', 'pattern', 'relationship', 'goal', 'correction')) NOT NULL,
    content TEXT NOT NULL,
    context TEXT,
    confidence_score DECIMAL(3,2) DEFAULT 1.0 CHECK (confidence_score BETWEEN 0 AND 1),
    importance_score DECIMAL(3,2) DEFAULT 0.5 CHECK (importance_score BETWEEN 0 AND 1),
    access_count INTEGER DEFAULT 0 CHECK (access_count >= 0),
    last_accessed TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archived_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_memory_user_id ON memory_entries(user_id);
CREATE INDEX idx_memory_type ON memory_entries(memory_type);
CREATE INDEX idx_memory_confidence ON memory_entries(confidence_score DESC);
CREATE INDEX idx_memory_archived ON memory_entries(archived_at) WHERE archived_at IS NULL;

-- RLS for memory entries
ALTER TABLE memory_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_memories" ON memory_entries
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "admin_access_memories" ON memory_entries
    FOR ALL USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- ==============================================
-- API LOGS TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS api_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    api_name TEXT NOT NULL,
    endpoint TEXT,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost DECIMAL(10,6),
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for cost tracking
CREATE INDEX idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX idx_api_logs_created_at ON api_logs(created_at DESC);
CREATE INDEX idx_api_logs_api_name ON api_logs(api_name);

-- RLS for api_logs
ALTER TABLE api_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_api_logs" ON api_logs
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "admin_access_api_logs" ON api_logs
    FOR ALL USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- ==============================================
-- UPLOADED FILES TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS uploaded_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT,
    file_size BIGINT,
    storage_url TEXT NOT NULL,
    cdn_url TEXT,
    thumbnail_url TEXT,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index
CREATE INDEX idx_files_user_id ON uploaded_files(user_id);
CREATE INDEX idx_files_uploaded_at ON uploaded_files(uploaded_at DESC);

-- RLS for uploaded files
ALTER TABLE uploaded_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_files" ON uploaded_files
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "admin_access_files" ON uploaded_files
    FOR ALL USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- ==============================================
-- DAILY JOURNALS TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS daily_journals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    user_entry TEXT,
    nicole_response TEXT,
    spotify_top_artists JSONB,
    spotify_top_tracks JSONB,
    spotify_listening_duration INTEGER,
    health_steps INTEGER,
    health_sleep_hours DECIMAL(4,2),
    health_heart_rate_avg INTEGER,
    health_active_energy INTEGER,
    patterns_detected JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE,
    responded_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, date)
);

-- Index
CREATE INDEX idx_journals_user_id ON daily_journals(user_id);
CREATE INDEX idx_journals_date ON daily_journals(date DESC);

-- RLS for daily journals
ALTER TABLE daily_journals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_journals" ON daily_journals
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "admin_access_journals" ON daily_journals
    FOR ALL USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- ==============================================
-- CORRECTIONS TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS corrections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    correction_text TEXT NOT NULL,
    context TEXT,
    applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index
CREATE INDEX idx_corrections_user_id ON corrections(user_id);
CREATE INDEX idx_corrections_applied ON corrections(applied);

-- RLS for corrections
ALTER TABLE corrections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_corrections" ON corrections
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ==============================================
-- FEEDBACK TABLE
-- ==============================================
CREATE TABLE IF NOT EXISTS memory_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    feedback_type TEXT CHECK (feedback_type IN ('thumbs_up', 'thumbs_down', 'copy')) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index
CREATE INDEX idx_feedback_message_id ON memory_feedback(message_id);
CREATE INDEX idx_feedback_user_id ON memory_feedback(user_id);

-- RLS for feedback
ALTER TABLE memory_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_feedback" ON memory_feedback
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ==============================================
-- Insert test admin user (Glen)
-- ==============================================
-- Note: Actual user creation handled by Supabase Auth
-- This is just the profile data

INSERT INTO users (id, email, full_name, role, relationship, image_limit_weekly)
VALUES 
    ('00000000-0000-0000-0000-000000000001'::uuid, 'glen@alphawavetech.com', 'Glen Healy', 'admin', 'creator', 999999)
ON CONFLICT (email) DO NOTHING;

-- ==============================================
-- GRANTS (if needed for service role)
-- ==============================================
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;


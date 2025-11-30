-- ============================================================
-- NICOLE V7 COMPLETE SCHEMA - TIGER POSTGRES
-- 36 Tables with pgvectorscale, TimescaleDB, RLS
-- ============================================================

-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ============================================================
-- SECTION 1: CORE TABLES (6 tables)
-- ============================================================

-- 1. Users
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'child', 'parent', 'standard')),
    relationship TEXT NOT NULL CHECK (relationship IN ('creator', 'son', 'nicoles_mother', 'father', 'friend')),
    image_limit_weekly INTEGER NOT NULL DEFAULT 5,
    date_of_birth DATE,
    parental_consent BOOLEAN NOT NULL DEFAULT FALSE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ,
    CONSTRAINT users_email_unique UNIQUE (email)
);

CREATE INDEX idx_users_email_lower ON users (LOWER(email));
CREATE INDEX idx_users_role ON users (role);

-- 2. Conversations
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    knowledge_base_id BIGINT,
    message_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations (user_id, updated_at DESC);

-- 3. Messages
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    emotion TEXT,
    attachments JSONB DEFAULT '[]',
    tool_calls JSONB DEFAULT '[]',
    tokens_used INTEGER,
    model_used TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages (conversation_id, created_at);
CREATE INDEX idx_messages_user ON messages (user_id, created_at DESC);
CREATE INDEX idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_messages_content_fts ON messages USING GIN (to_tsvector('english', content));

-- 4. Memory Entries (Core Memory System)
CREATE TABLE IF NOT EXISTS memory_entries (
    memory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL CHECK (memory_type IN ('fact', 'preference', 'pattern', 'relationship', 'goal', 'correction', 'document', 'conversation')),
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    context TEXT,
    source_type TEXT DEFAULT 'chat',
    source_id BIGINT,
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 1.000 CHECK (confidence_score BETWEEN 0 AND 1),
    importance_score NUMERIC(4,3) NOT NULL DEFAULT 0.500 CHECK (importance_score BETWEEN 0 AND 1),
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE INDEX idx_memory_user_active ON memory_entries (user_id, confidence_score DESC, importance_score DESC) WHERE archived_at IS NULL;
CREATE INDEX idx_memory_embedding ON memory_entries USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100) WHERE archived_at IS NULL;
CREATE INDEX idx_memory_content_fts ON memory_entries USING GIN (to_tsvector('english', content)) WHERE archived_at IS NULL;
CREATE INDEX idx_memory_tags ON memory_entries USING GIN (tags) WHERE archived_at IS NULL;
CREATE INDEX idx_memory_type ON memory_entries (user_id, memory_type) WHERE archived_at IS NULL;

-- 5. Knowledge Bases
CREATE TABLE IF NOT EXISTS knowledge_bases (
    knowledge_base_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    kb_type TEXT NOT NULL DEFAULT 'general' CHECK (kb_type IN ('general', 'project', 'domain', 'shared')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    memory_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kb_user ON knowledge_bases (user_id, is_active);

-- 6. Memory Knowledge Base Links
CREATE TABLE IF NOT EXISTS memory_knowledge_base_links (
    link_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    memory_id BIGINT NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    knowledge_base_id BIGINT NOT NULL REFERENCES knowledge_bases(knowledge_base_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_memory_kb UNIQUE (memory_id, knowledge_base_id)
);

CREATE INDEX idx_memory_kb_links ON memory_knowledge_base_links (knowledge_base_id);

-- ============================================================
-- SECTION 2: MEMORY MANAGEMENT TABLES (6 tables)
-- ============================================================

-- 7. Memory Tags
CREATE TABLE IF NOT EXISTS memory_tags (
    tag_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#6366f1',
    usage_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_user_tag UNIQUE (user_id, name)
);

CREATE INDEX idx_tags_user ON memory_tags (user_id);

-- 8. Memory Tag Links
CREATE TABLE IF NOT EXISTS memory_tag_links (
    link_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    memory_id BIGINT NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    tag_id BIGINT NOT NULL REFERENCES memory_tags(tag_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_memory_tag UNIQUE (memory_id, tag_id)
);

CREATE INDEX idx_memory_tag_links ON memory_tag_links (tag_id);

-- 9. Corrections
CREATE TABLE IF NOT EXISTS corrections (
    correction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    original_memory_id BIGINT REFERENCES memory_entries(memory_id),
    original_message_id BIGINT REFERENCES messages(message_id),
    correction_text TEXT NOT NULL,
    context TEXT,
    applied BOOLEAN NOT NULL DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_corrections_user ON corrections (user_id, applied, created_at DESC);

-- 10. Memory Feedback
CREATE TABLE IF NOT EXISTS memory_feedback (
    feedback_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id BIGINT REFERENCES messages(message_id) ON DELETE CASCADE,
    memory_id BIGINT REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down', 'copy', 'flag', 'pin')),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_message ON memory_feedback (message_id);
CREATE INDEX idx_feedback_memory ON memory_feedback (memory_id);

-- 11. Memory Relationships
CREATE TABLE IF NOT EXISTS memory_relationships (
    relationship_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_memory_id BIGINT NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    target_memory_id BIGINT NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('related', 'contradicts', 'supports', 'supersedes', 'derived_from')),
    strength NUMERIC(4,3) DEFAULT 0.500,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_memory_relationship UNIQUE (source_memory_id, target_memory_id, relationship_type)
);

CREATE INDEX idx_memory_rel_source ON memory_relationships (source_memory_id);
CREATE INDEX idx_memory_rel_target ON memory_relationships (target_memory_id);

-- 12. Nicole Memory Actions (Audit Trail)
CREATE TABLE IF NOT EXISTS nicole_memory_actions (
    action_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    memory_id BIGINT REFERENCES memory_entries(memory_id) ON DELETE SET NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('create', 'update', 'archive', 'restore', 'delete', 'merge', 'split', 'tag', 'untag', 'link_kb', 'unlink_kb')),
    action_reason TEXT,
    previous_state JSONB,
    new_state JSONB,
    triggered_by TEXT NOT NULL DEFAULT 'nicole' CHECK (triggered_by IN ('nicole', 'user', 'system', 'decay_job')),
    conversation_id BIGINT REFERENCES conversations(conversation_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_nicole_actions_user ON nicole_memory_actions (user_id, created_at DESC);
CREATE INDEX idx_nicole_actions_memory ON nicole_memory_actions (memory_id);

-- ============================================================
-- SECTION 3: DOCUMENT TABLES (4 tables)
-- ============================================================

-- 13. Uploaded Files
CREATE TABLE IF NOT EXISTS uploaded_files (
    file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    storage_url TEXT NOT NULL,
    cdn_url TEXT,
    thumbnail_url TEXT,
    checksum TEXT,
    processing_status TEXT NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_error TEXT,
    metadata JSONB DEFAULT '{}',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_files_user ON uploaded_files (user_id, uploaded_at DESC);
CREATE INDEX idx_files_status ON uploaded_files (processing_status) WHERE processing_status != 'completed';

-- 14. Document Repository
CREATE TABLE IF NOT EXISTS document_repository (
    document_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_id BIGINT NOT NULL REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    title TEXT,
    extracted_text TEXT,
    extracted_entities JSONB DEFAULT '{}',
    page_count INTEGER,
    language TEXT DEFAULT 'en',
    summary TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_docs_user ON document_repository (user_id, created_at DESC);
CREATE INDEX idx_docs_embedding ON document_repository USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- 15. Document Chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES document_repository(document_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536),
    page_number INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON document_chunks (document_id, chunk_index);
CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_fts ON document_chunks USING GIN (to_tsvector('english', chunk_text));

-- 16. Photos
CREATE TABLE IF NOT EXISTS photos (
    photo_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_id BIGINT NOT NULL REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
    vision_analysis JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    location TEXT,
    people_detected TEXT[] DEFAULT '{}',
    taken_at TIMESTAMPTZ,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_photos_user ON photos (user_id, created_at DESC);
CREATE INDEX idx_photos_tags ON photos USING GIN (tags);

-- ============================================================
-- SECTION 4: LIFE INTEGRATION TABLES (6 tables)
-- ============================================================

-- 17. Daily Journals
CREATE TABLE IF NOT EXISTS daily_journals (
    journal_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    journal_date DATE NOT NULL,
    user_entry TEXT,
    nicole_response TEXT,
    spotify_data JSONB DEFAULT '{}',
    health_data JSONB DEFAULT '{}',
    patterns_detected JSONB DEFAULT '[]',
    mood_score NUMERIC(3,2),
    submitted_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_user_journal_date UNIQUE (user_id, journal_date)
);

CREATE INDEX idx_journals_user ON daily_journals (user_id, journal_date DESC);


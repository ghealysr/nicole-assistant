-- Nicole V7 - Document Intelligence Schema
-- Production-grade document storage for perfect recall
-- Run this in Supabase SQL Editor

-- ==============================================
-- DOCUMENT REPOSITORY TABLE
-- Stores processed document metadata
-- ==============================================
CREATE TABLE IF NOT EXISTS document_repository (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,  -- References auth.users, not custom users table
    
    -- Document info
    title TEXT NOT NULL,
    filename TEXT,
    source_type TEXT CHECK (source_type IN ('upload', 'url', 'paste')) NOT NULL,
    source_url TEXT,  -- Original URL if from web
    content_type TEXT,  -- MIME type
    file_size_bytes BIGINT,
    
    -- Extracted content
    full_text TEXT,  -- Complete extracted text
    summary TEXT,  -- AI-generated summary
    key_points JSONB DEFAULT '[]'::jsonb,  -- Array of key points
    entities JSONB DEFAULT '{}'::jsonb,  -- Named entities extracted
    
    -- Processing status
    status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    error_message TEXT,
    
    -- Metadata
    page_count INTEGER,
    word_count INTEGER,
    language TEXT DEFAULT 'en',
    
    -- Storage
    storage_path TEXT,  -- Path in Supabase Storage
    thumbnail_url TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE,
    
    -- For conversation context (optional)
    conversation_id UUID
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_docs_user_id ON document_repository(user_id);
CREATE INDEX IF NOT EXISTS idx_docs_status ON document_repository(status);
CREATE INDEX IF NOT EXISTS idx_docs_created_at ON document_repository(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_docs_source_type ON document_repository(source_type);

-- Full-text search on document content
CREATE INDEX IF NOT EXISTS idx_docs_fulltext ON document_repository 
    USING gin(to_tsvector('english', COALESCE(full_text, '') || ' ' || COALESCE(title, '')));

-- RLS
ALTER TABLE document_repository ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for re-running)
DROP POLICY IF EXISTS "users_own_documents" ON document_repository;
DROP POLICY IF EXISTS "admin_access_documents" ON document_repository;
DROP POLICY IF EXISTS "service_role_documents" ON document_repository;

-- Users can only access their own documents
CREATE POLICY "users_own_documents" ON document_repository
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Service role can access all (for backend operations)
CREATE POLICY "service_role_documents" ON document_repository
    FOR ALL USING (auth.role() = 'service_role');


-- ==============================================
-- DOCUMENT CHUNKS TABLE
-- Stores searchable chunks for semantic retrieval
-- ==============================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES document_repository(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,  -- For RLS filtering
    
    -- Chunk content
    chunk_index INTEGER NOT NULL,  -- Order within document
    content TEXT NOT NULL,  -- Chunk text
    token_count INTEGER,
    
    -- Context
    page_number INTEGER,
    section_title TEXT,
    
    -- For retrieval
    embedding_id TEXT,  -- ID in Qdrant
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_user_id ON document_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_index ON document_chunks(chunk_index);

-- Full-text search on chunks
CREATE INDEX IF NOT EXISTS idx_chunks_fulltext ON document_chunks USING gin(to_tsvector('english', content));

-- RLS
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "users_own_chunks" ON document_chunks;
DROP POLICY IF EXISTS "admin_access_chunks" ON document_chunks;
DROP POLICY IF EXISTS "service_role_chunks" ON document_chunks;

-- Users can only access their own chunks
CREATE POLICY "users_own_chunks" ON document_chunks
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Service role can access all
CREATE POLICY "service_role_chunks" ON document_chunks
    FOR ALL USING (auth.role() = 'service_role');


-- ==============================================
-- SUPABASE STORAGE BUCKET
-- Create the documents bucket if it doesn't exist
-- ==============================================
-- Note: Run this separately or via Supabase Dashboard > Storage
-- INSERT INTO storage.buckets (id, name, public) 
-- VALUES ('documents', 'documents', false)
-- ON CONFLICT (id) DO NOTHING;


-- ==============================================
-- GRANTS
-- ==============================================
GRANT ALL ON document_repository TO authenticated;
GRANT ALL ON document_repository TO service_role;
GRANT ALL ON document_chunks TO authenticated;
GRANT ALL ON document_chunks TO service_role;

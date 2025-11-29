-- ═══════════════════════════════════════════════════════════════════════════════
-- Nicole V7 - Complete Memory System Schema
-- ═══════════════════════════════════════════════════════════════════════════════
-- 
-- This schema implements the full memory system as specified in the Master Plan:
-- - Knowledge Bases (project/topic organization with hierarchy)
-- - Enhanced Memory Entries (with knowledge base linking)
-- - Memory Tags (flexible categorization)
-- - Memory Relationships (linking related memories)
-- - Memory Consolidations (merged/summarized memories)
-- - Nicole's Memory Actions (proactive memory management)
--
-- DEPLOYMENT INSTRUCTIONS:
-- 1. Run Part 1 first (creates tables)
-- 2. Run Part 2 second (creates indexes)
-- 3. Run Part 3 third (enables RLS and policies)
-- 4. Run Part 4 fourth (grants permissions)
--
-- Author: Nicole V7 Memory System Implementation
-- Date: November 2025
-- ═══════════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 1: CREATE TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Drop existing tables if needed (careful in production!)
-- DROP TABLE IF EXISTS memory_consolidations CASCADE;
-- DROP TABLE IF EXISTS memory_relationships CASCADE;
-- DROP TABLE IF EXISTS memory_tag_assignments CASCADE;
-- DROP TABLE IF EXISTS memory_tags CASCADE;
-- DROP TABLE IF EXISTS nicole_memory_actions CASCADE;
-- DROP TABLE IF EXISTS knowledge_bases CASCADE;

-- ─────────────────────────────────────────────────────────────────────────────
-- KNOWLEDGE BASES TABLE
-- Organizes memories into projects, topics, or domains
-- Supports hierarchical structure (folders within folders)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Ownership
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Organization
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT '📁',  -- Emoji or icon identifier
    color TEXT DEFAULT '#B8A8D4',  -- Hex color for UI
    
    -- Hierarchy (NULL = root level)
    parent_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    
    -- Classification
    kb_type TEXT NOT NULL CHECK (kb_type IN (
        'project',      -- Work projects, coding projects
        'topic',        -- Learning topics, interests
        'client',       -- Client-specific knowledge
        'personal',     -- Personal life organization
        'family',       -- Family-related memories
        'health',       -- Health and wellness
        'financial',    -- Financial matters
        'system'        -- Nicole's internal organization
    )) DEFAULT 'topic',
    
    -- Sharing (for family memories)
    is_shared BOOLEAN DEFAULT FALSE,
    shared_with UUID[] DEFAULT '{}',  -- Array of user IDs who can access
    
    -- Metadata
    memory_count INTEGER DEFAULT 0,  -- Denormalized for performance
    last_memory_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_hierarchy CHECK (id != parent_id)
);

COMMENT ON TABLE knowledge_bases IS 'Organizes memories into hierarchical projects/topics. Nicole can create and manage these.';

-- ─────────────────────────────────────────────────────────────────────────────
-- MEMORY TAGS TABLE
-- Flexible tagging system for memories
-- Includes both predefined system tags and custom user tags
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Ownership (NULL = system tag available to all)
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Tag details
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#9CA3AF',
    icon TEXT,
    
    -- Classification
    tag_type TEXT NOT NULL CHECK (tag_type IN (
        'system',       -- Predefined system tags
        'custom',       -- User-created tags
        'auto',         -- Auto-generated by Nicole
        'emotion',      -- Emotional context tags
        'temporal'      -- Time-based tags (e.g., "2024", "summer")
    )) DEFAULT 'custom',
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint per user (or system-wide for system tags)
    CONSTRAINT unique_tag_per_user UNIQUE (user_id, name)
);

COMMENT ON TABLE memory_tags IS 'Flexible tagging system. System tags are shared, custom tags are per-user.';

-- ─────────────────────────────────────────────────────────────────────────────
-- MEMORY TAG ASSIGNMENTS TABLE
-- Many-to-many relationship between memories and tags
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_tag_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES memory_tags(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by TEXT CHECK (assigned_by IN ('user', 'nicole', 'system')) DEFAULT 'user',
    
    CONSTRAINT unique_memory_tag UNIQUE (memory_id, tag_id)
);

COMMENT ON TABLE memory_tag_assignments IS 'Links memories to their tags. Tracks who assigned the tag.';

-- ─────────────────────────────────────────────────────────────────────────────
-- MEMORY RELATIONSHIPS TABLE
-- Links related memories together
-- Enables Nicole to understand memory connections
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- The two related memories
    source_memory_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
    target_memory_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
    
    -- Relationship type
    relationship_type TEXT NOT NULL CHECK (relationship_type IN (
        'related_to',       -- General relation
        'contradicts',      -- Memory contradicts another (correction)
        'elaborates',       -- Memory adds detail to another
        'supersedes',       -- Memory replaces/updates another
        'derived_from',     -- Memory was created from another
        'references',       -- Memory references another
        'same_topic',       -- Memories are about same topic
        'same_entity',      -- Memories are about same person/thing
        'temporal_sequence' -- Memories are part of a sequence
    )) DEFAULT 'related_to',
    
    -- Relationship strength (0-1)
    strength DECIMAL(3,2) DEFAULT 0.5 CHECK (strength BETWEEN 0 AND 1),
    
    -- Who created this relationship
    created_by TEXT CHECK (created_by IN ('user', 'nicole', 'system')) DEFAULT 'nicole',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent self-references and duplicates
    CONSTRAINT no_self_reference CHECK (source_memory_id != target_memory_id),
    CONSTRAINT unique_relationship UNIQUE (source_memory_id, target_memory_id, relationship_type)
);

COMMENT ON TABLE memory_relationships IS 'Links related memories. Nicole uses this to understand memory connections.';

-- ─────────────────────────────────────────────────────────────────────────────
-- MEMORY CONSOLIDATIONS TABLE
-- Tracks when memories are merged/summarized
-- Maintains links to original memories
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_consolidations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- The consolidated (summary) memory
    consolidated_memory_id UUID NOT NULL REFERENCES memory_entries(id) ON DELETE CASCADE,
    
    -- Original memories that were merged
    source_memory_ids UUID[] NOT NULL,
    
    -- Consolidation metadata
    consolidation_type TEXT NOT NULL CHECK (consolidation_type IN (
        'merge',        -- Multiple memories merged into one
        'summarize',    -- Long memory summarized
        'deduplicate',  -- Duplicate memories merged
        'upgrade'       -- Memory updated with new information
    )),
    
    -- Processing metadata
    reason TEXT,  -- Why this consolidation was made
    model_used TEXT,  -- Which AI model performed the consolidation
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE memory_consolidations IS 'Tracks memory consolidations. Maintains audit trail of merged memories.';

-- ─────────────────────────────────────────────────────────────────────────────
-- NICOLE'S MEMORY ACTIONS TABLE
-- Audit log of Nicole's proactive memory management
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nicole_memory_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Action details
    action_type TEXT NOT NULL CHECK (action_type IN (
        'create_memory',        -- Nicole created a new memory
        'create_knowledge_base', -- Nicole created a new KB
        'organize_memories',    -- Nicole moved memories to a KB
        'consolidate_memories', -- Nicole merged memories
        'tag_memory',           -- Nicole added tags
        'link_memories',        -- Nicole created relationships
        'archive_memory',       -- Nicole archived a memory
        'boost_confidence',     -- Nicole increased confidence
        'decay_memory'          -- Scheduled decay applied
    )),
    
    -- Target of action
    target_type TEXT NOT NULL CHECK (target_type IN ('memory', 'knowledge_base', 'tag', 'relationship')),
    target_id UUID NOT NULL,
    
    -- Context
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT,  -- Why Nicole took this action
    context JSONB,  -- Additional context data
    
    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE nicole_memory_actions IS 'Audit log of Nicole''s proactive memory management actions.';

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 2: ALTER EXISTING TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Add knowledge_base_id to memory_entries (if column doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'knowledge_base_id'
    ) THEN
        ALTER TABLE memory_entries 
        ADD COLUMN knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add source column to memory_entries (who/what created this memory)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'source'
    ) THEN
        ALTER TABLE memory_entries 
        ADD COLUMN source TEXT CHECK (source IN ('user', 'nicole', 'system', 'extraction', 'consolidation')) DEFAULT 'user';
    END IF;
END $$;

-- Add is_shared column to memory_entries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'is_shared'
    ) THEN
        ALTER TABLE memory_entries 
        ADD COLUMN is_shared BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Add parent_memory_id for memory hierarchies (corrections, elaborations)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'parent_memory_id'
    ) THEN
        ALTER TABLE memory_entries 
        ADD COLUMN parent_memory_id UUID REFERENCES memory_entries(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add embedding_status to track vector storage state
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'embedding_status'
    ) THEN
        ALTER TABLE memory_entries 
        ADD COLUMN embedding_status TEXT CHECK (embedding_status IN ('pending', 'completed', 'failed', 'skipped')) DEFAULT 'pending';
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 3: CREATE INDEXES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Knowledge Bases indexes
CREATE INDEX IF NOT EXISTS idx_kb_user_id ON knowledge_bases(user_id);
CREATE INDEX IF NOT EXISTS idx_kb_parent_id ON knowledge_bases(parent_id);
CREATE INDEX IF NOT EXISTS idx_kb_type ON knowledge_bases(kb_type);
CREATE INDEX IF NOT EXISTS idx_kb_shared ON knowledge_bases(is_shared) WHERE is_shared = TRUE;
CREATE INDEX IF NOT EXISTS idx_kb_not_archived ON knowledge_bases(user_id) WHERE archived_at IS NULL;

-- Memory Tags indexes
CREATE INDEX IF NOT EXISTS idx_tags_user_id ON memory_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_tags_type ON memory_tags(tag_type);
CREATE INDEX IF NOT EXISTS idx_tags_system ON memory_tags(tag_type) WHERE tag_type = 'system';

-- Tag Assignments indexes
CREATE INDEX IF NOT EXISTS idx_tag_assign_memory ON memory_tag_assignments(memory_id);
CREATE INDEX IF NOT EXISTS idx_tag_assign_tag ON memory_tag_assignments(tag_id);

-- Memory Relationships indexes
CREATE INDEX IF NOT EXISTS idx_rel_source ON memory_relationships(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON memory_relationships(target_memory_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON memory_relationships(relationship_type);

-- Memory Consolidations indexes
CREATE INDEX IF NOT EXISTS idx_consol_memory ON memory_consolidations(consolidated_memory_id);

-- Nicole Actions indexes
CREATE INDEX IF NOT EXISTS idx_nicole_actions_user ON nicole_memory_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_nicole_actions_type ON nicole_memory_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_nicole_actions_target ON nicole_memory_actions(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_nicole_actions_date ON nicole_memory_actions(created_at DESC);

-- Memory Entries new column indexes
CREATE INDEX IF NOT EXISTS idx_memory_kb ON memory_entries(knowledge_base_id) WHERE knowledge_base_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_source ON memory_entries(source);
CREATE INDEX IF NOT EXISTS idx_memory_shared ON memory_entries(is_shared) WHERE is_shared = TRUE;
CREATE INDEX IF NOT EXISTS idx_memory_parent ON memory_entries(parent_memory_id) WHERE parent_memory_id IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 4: ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════════════════

-- Enable RLS on all new tables
ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_tag_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_consolidations ENABLE ROW LEVEL SECURITY;
ALTER TABLE nicole_memory_actions ENABLE ROW LEVEL SECURITY;

-- Knowledge Bases policies
CREATE POLICY "users_own_knowledge_bases" ON knowledge_bases
    FOR ALL USING (auth.uid() = user_id OR auth.uid() = ANY(shared_with))
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "service_role_kb" ON knowledge_bases
    FOR ALL USING (true);

-- Memory Tags policies (system tags visible to all, custom to owner)
CREATE POLICY "users_see_own_and_system_tags" ON memory_tags
    FOR SELECT USING (user_id IS NULL OR auth.uid() = user_id);

CREATE POLICY "users_manage_own_tags" ON memory_tags
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "service_role_tags" ON memory_tags
    FOR ALL USING (true);

-- Tag Assignments policies (through memory ownership)
CREATE POLICY "users_own_tag_assignments" ON memory_tag_assignments
    FOR ALL USING (
        memory_id IN (SELECT id FROM memory_entries WHERE user_id = auth.uid())
    );

CREATE POLICY "service_role_tag_assign" ON memory_tag_assignments
    FOR ALL USING (true);

-- Memory Relationships policies (through memory ownership)
CREATE POLICY "users_own_memory_relationships" ON memory_relationships
    FOR ALL USING (
        source_memory_id IN (SELECT id FROM memory_entries WHERE user_id = auth.uid())
    );

CREATE POLICY "service_role_relationships" ON memory_relationships
    FOR ALL USING (true);

-- Memory Consolidations policies (through memory ownership)
CREATE POLICY "users_own_consolidations" ON memory_consolidations
    FOR ALL USING (
        consolidated_memory_id IN (SELECT id FROM memory_entries WHERE user_id = auth.uid())
    );

CREATE POLICY "service_role_consolidations" ON memory_consolidations
    FOR ALL USING (true);

-- Nicole Actions policies (user sees their own actions)
CREATE POLICY "users_see_own_nicole_actions" ON nicole_memory_actions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "service_role_nicole_actions" ON nicole_memory_actions
    FOR ALL USING (true);

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 5: GRANTS
-- ═══════════════════════════════════════════════════════════════════════════════

GRANT ALL ON knowledge_bases TO authenticated;
GRANT ALL ON knowledge_bases TO service_role;
GRANT ALL ON memory_tags TO authenticated;
GRANT ALL ON memory_tags TO service_role;
GRANT ALL ON memory_tag_assignments TO authenticated;
GRANT ALL ON memory_tag_assignments TO service_role;
GRANT ALL ON memory_relationships TO authenticated;
GRANT ALL ON memory_relationships TO service_role;
GRANT ALL ON memory_consolidations TO authenticated;
GRANT ALL ON memory_consolidations TO service_role;
GRANT ALL ON nicole_memory_actions TO authenticated;
GRANT ALL ON nicole_memory_actions TO service_role;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 6: INSERT DEFAULT SYSTEM TAGS
-- ═══════════════════════════════════════════════════════════════════════════════

INSERT INTO memory_tags (user_id, name, description, color, icon, tag_type) VALUES
    (NULL, 'important', 'High priority memory', '#EF4444', '⭐', 'system'),
    (NULL, 'verified', 'Confirmed accurate', '#10B981', '✓', 'system'),
    (NULL, 'needs-review', 'May need correction', '#F59E0B', '⚠️', 'system'),
    (NULL, 'outdated', 'Information may be stale', '#6B7280', '📅', 'system'),
    (NULL, 'personal', 'Personal/private', '#8B5CF6', '🔒', 'system'),
    (NULL, 'family', 'Family related', '#EC4899', '👨‍👩‍👧‍👦', 'system'),
    (NULL, 'work', 'Work/business related', '#3B82F6', '💼', 'system'),
    (NULL, 'health', 'Health related', '#22C55E', '🏥', 'system'),
    (NULL, 'financial', 'Financial matters', '#84CC16', '💰', 'system'),
    (NULL, 'emotional', 'Emotional context', '#F472B6', '💜', 'system'),
    (NULL, 'routine', 'Daily routine/habit', '#06B6D4', '🔄', 'system'),
    (NULL, 'preference', 'User preference', '#A855F7', '💡', 'system'),
    (NULL, 'goal', 'Goal or aspiration', '#FBBF24', '🎯', 'system'),
    (NULL, 'correction', 'Corrected information', '#F97316', '✏️', 'system')
ON CONFLICT (user_id, name) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 7: HELPER FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════════════════

-- Function to update knowledge base memory count
CREATE OR REPLACE FUNCTION update_kb_memory_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.knowledge_base_id IS NOT NULL THEN
        UPDATE knowledge_bases 
        SET memory_count = memory_count + 1,
            last_memory_at = NOW(),
            updated_at = NOW()
        WHERE id = NEW.knowledge_base_id;
    ELSIF TG_OP = 'DELETE' AND OLD.knowledge_base_id IS NOT NULL THEN
        UPDATE knowledge_bases 
        SET memory_count = GREATEST(0, memory_count - 1),
            updated_at = NOW()
        WHERE id = OLD.knowledge_base_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.knowledge_base_id IS DISTINCT FROM NEW.knowledge_base_id THEN
            IF OLD.knowledge_base_id IS NOT NULL THEN
                UPDATE knowledge_bases 
                SET memory_count = GREATEST(0, memory_count - 1),
                    updated_at = NOW()
                WHERE id = OLD.knowledge_base_id;
            END IF;
            IF NEW.knowledge_base_id IS NOT NULL THEN
                UPDATE knowledge_bases 
                SET memory_count = memory_count + 1,
                    last_memory_at = NOW(),
                    updated_at = NOW()
                WHERE id = NEW.knowledge_base_id;
            END IF;
        END IF;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create trigger for memory count updates
DROP TRIGGER IF EXISTS trigger_update_kb_memory_count ON memory_entries;
CREATE TRIGGER trigger_update_kb_memory_count
    AFTER INSERT OR UPDATE OR DELETE ON memory_entries
    FOR EACH ROW EXECUTE FUNCTION update_kb_memory_count();

-- Function to increment tag usage count
CREATE OR REPLACE FUNCTION increment_tag_usage()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE memory_tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for tag usage
DROP TRIGGER IF EXISTS trigger_increment_tag_usage ON memory_tag_assignments;
CREATE TRIGGER trigger_increment_tag_usage
    AFTER INSERT ON memory_tag_assignments
    FOR EACH ROW EXECUTE FUNCTION increment_tag_usage();

-- ═══════════════════════════════════════════════════════════════════════════════
-- DEPLOYMENT COMPLETE
-- ═══════════════════════════════════════════════════════════════════════════════
-- 
-- Next steps:
-- 1. Run this SQL in Supabase SQL Editor
-- 2. Verify tables were created: SELECT * FROM knowledge_bases LIMIT 1;
-- 3. Verify system tags: SELECT * FROM memory_tags WHERE tag_type = 'system';
-- 4. Update backend to use new schema
--
-- ═══════════════════════════════════════════════════════════════════════════════


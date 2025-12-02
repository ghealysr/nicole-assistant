-- ═══════════════════════════════════════════════════════════════════════════════
-- Nicole V7 - Conversation Pinning & Management
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- Adds pinning capability to conversations for the Chats panel.
-- Also adds message_count for display and auto-cleanup logic.
--
-- Author: Nicole V7 Chat System
-- Date: December 2025
-- ═══════════════════════════════════════════════════════════════════════════════

-- Add pinning columns to conversations table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' AND column_name = 'is_pinned') THEN
        ALTER TABLE conversations ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' AND column_name = 'pin_order') THEN
        ALTER TABLE conversations ADD COLUMN pin_order INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conversations' AND column_name = 'message_count') THEN
        ALTER TABLE conversations ADD COLUMN message_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- Create index for pinned conversations
CREATE INDEX IF NOT EXISTS idx_conversations_pinned 
ON conversations (user_id, is_pinned, pin_order) 
WHERE is_pinned = TRUE;

-- Function to update message count on conversation
CREATE OR REPLACE FUNCTION update_conversation_message_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE conversations 
        SET message_count = message_count + 1,
            last_message_at = NOW(),
            updated_at = NOW()
        WHERE conversation_id = NEW.conversation_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE conversations 
        SET message_count = GREATEST(0, message_count - 1),
            updated_at = NOW()
        WHERE conversation_id = OLD.conversation_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for message count updates
DROP TRIGGER IF EXISTS trg_update_conversation_message_count ON messages;
CREATE TRIGGER trg_update_conversation_message_count
AFTER INSERT OR DELETE ON messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_message_count();

-- Function to auto-delete short conversations older than 3 days
-- This should be called by a scheduled job
CREATE OR REPLACE FUNCTION cleanup_short_conversations(p_user_id BIGINT DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM conversations
        WHERE message_count <= 3
          AND created_at < NOW() - INTERVAL '3 days'
          AND is_pinned = FALSE
          AND conversation_status != 'deleted'
          AND (p_user_id IS NULL OR user_id = p_user_id)
        RETURNING conversation_id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════════
-- DEPLOYMENT COMPLETE
-- ═══════════════════════════════════════════════════════════════════════════════


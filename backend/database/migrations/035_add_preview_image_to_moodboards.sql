-- ============================================================================
-- Migration: 035_add_preview_image_to_moodboards.sql
-- Purpose: Add preview_image_b64 column to muse_moodboards table
-- Author: Anthropic Quality Implementation
-- Date: 2026-01-03
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'muse_moodboards' 
        AND column_name = 'preview_image_b64'
    ) THEN
        ALTER TABLE muse_moodboards ADD COLUMN preview_image_b64 TEXT;
    END IF;
END
$$;


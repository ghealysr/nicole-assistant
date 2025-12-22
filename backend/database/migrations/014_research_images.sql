-- ============================================================================
-- Research Images Migration
-- Adds image storage and screenshot URLs to research tables
-- ============================================================================

-- Add image fields to research_reports
ALTER TABLE research_reports
ADD COLUMN IF NOT EXISTS hero_image_url TEXT,
ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS screenshots JSONB DEFAULT '[]';

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_research_reports_images 
ON research_reports USING GIN (images);

CREATE INDEX IF NOT EXISTS idx_research_reports_screenshots 
ON research_reports USING GIN (screenshots);

-- Add comments
COMMENT ON COLUMN research_reports.hero_image_url IS 'Primary hero image URL for the research article';
COMMENT ON COLUMN research_reports.images IS 'Array of image objects: [{url, caption, source, relevance}]';
COMMENT ON COLUMN research_reports.screenshots IS 'Array of screenshot objects: [{url, source_url, captured_at, caption}]';

-- Optional: Migrate existing cloudinary URLs from metadata if any exist
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT id, metadata FROM research_reports WHERE metadata IS NOT NULL
    LOOP
        BEGIN
            -- Check if metadata contains cloudinary URLs and migrate them
            IF r.metadata ? 'images' OR r.metadata ? 'screenshots' THEN
                UPDATE research_reports
                SET
                    images = COALESCE((r.metadata->>'images')::jsonb, '[]'::jsonb),
                    screenshots = COALESCE((r.metadata->>'screenshots')::jsonb, '[]'::jsonb)
                WHERE id = r.id;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Failed to migrate images for report ID %: %', r.id, SQLERRM;
        END;
    END LOOP;
END $$;



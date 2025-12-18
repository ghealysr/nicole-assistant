-- ============================================================================
-- Research Template Fields Migration
-- Adds structured fields for template rendering
-- Fixes data persistence gap identified in CTO audit
-- ============================================================================

-- Add new columns for structured synthesis data
ALTER TABLE research_reports 
ADD COLUMN IF NOT EXISTS article_title TEXT,
ADD COLUMN IF NOT EXISTS subtitle TEXT,
ADD COLUMN IF NOT EXISTS lead_paragraph TEXT,
ADD COLUMN IF NOT EXISTS body TEXT,
ADD COLUMN IF NOT EXISTS bottom_line TEXT;

-- Add unique constraint on request_id for ON CONFLICT support
-- First drop any existing index if it exists
DROP INDEX IF EXISTS idx_research_reports_request;
ALTER TABLE research_reports DROP CONSTRAINT IF EXISTS research_reports_request_id_unique;
ALTER TABLE research_reports ADD CONSTRAINT research_reports_request_id_unique UNIQUE (request_id);

-- Add comments for clarity
COMMENT ON COLUMN research_reports.article_title IS 'Journalist-crafted headline from Claude synthesis';
COMMENT ON COLUMN research_reports.subtitle IS 'Brief subheading capturing key insight';
COMMENT ON COLUMN research_reports.lead_paragraph IS 'Opening paragraph that hooks reader';
COMMENT ON COLUMN research_reports.body IS 'Full article body - 2-4 paragraphs of prose';
COMMENT ON COLUMN research_reports.bottom_line IS 'Powerful concluding sentence answering the query';

-- Create index for faster article title searches
CREATE INDEX IF NOT EXISTS idx_research_reports_title ON research_reports(article_title) WHERE article_title IS NOT NULL;

-- Migrate existing data: If nicole_synthesis contains JSON, extract fields
-- This is a best-effort migration for existing records
DO $$
DECLARE
    r RECORD;
    synthesis_json JSONB;
BEGIN
    FOR r IN SELECT id, nicole_synthesis FROM research_reports WHERE nicole_synthesis IS NOT NULL
    LOOP
        BEGIN
            -- Try to parse as JSON
            synthesis_json := r.nicole_synthesis::JSONB;
            
            -- Extract and update fields if JSON parsing succeeds
            UPDATE research_reports SET
                article_title = COALESCE(article_title, synthesis_json->>'article_title', synthesis_json->>'articletitle'),
                subtitle = COALESCE(subtitle, synthesis_json->>'subtitle'),
                lead_paragraph = COALESCE(lead_paragraph, synthesis_json->>'lead_paragraph', synthesis_json->>'leadparagraph'),
                body = COALESCE(body, synthesis_json->>'body'),
                bottom_line = COALESCE(bottom_line, synthesis_json->>'bottom_line', synthesis_json->>'bottomline')
            WHERE id = r.id;
        EXCEPTION WHEN OTHERS THEN
            -- If not valid JSON, copy to body field
            UPDATE research_reports SET body = COALESCE(body, r.nicole_synthesis) WHERE id = r.id;
        END;
    END LOOP;
END $$;


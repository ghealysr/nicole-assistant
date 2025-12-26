-- ============================================================================
-- Migration: 031_muse_design_research.sql
-- Purpose: Create tables for Muse Design Research Agent
-- Features: Research sessions, inspiration images, mood boards, style guides
-- Author: Nicole V7 Architecture
-- Date: 2025-12-26
-- ============================================================================

-- ============================================================================
-- 1. DESIGN RESEARCH SESSIONS
-- Tracks the complete research workflow for a project
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_research_sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    
    -- Session metadata
    session_status VARCHAR(50) DEFAULT 'intake' 
        CHECK (session_status IN (
            'intake',           -- Initial form submitted
            'analyzing_brief',  -- Extracting keywords/intent
            'researching',      -- Web research in progress
            'analyzing_inspiration', -- Processing user images/links
            'generating_moodboards', -- Creating 4 mood board options
            'awaiting_selection',    -- User choosing mood board
            'generating_design',     -- Full design generation
            'awaiting_approval',     -- User reviewing full design
            'approved',              -- Ready for Nicole handoff
            'handed_off',            -- Sent to Nicole
            'failed',                -- Error occurred
            'cancelled'              -- User cancelled
        )),
    
    -- User input
    design_brief TEXT NOT NULL,
    target_audience TEXT,
    brand_keywords TEXT[],            -- Array of brand personality keywords
    aesthetic_preferences TEXT,       -- Free-form aesthetic description
    anti_patterns TEXT,               -- What to avoid
    
    -- Brief analysis results (Phase 1)
    brief_analysis JSONB DEFAULT '{}',
    extracted_keywords TEXT[],
    detected_movements TEXT[],        -- Art Deco, Brutalism, etc.
    emotional_targets TEXT[],         -- Bold, Playful, Professional, etc.
    
    -- Research findings (Phase 2)
    web_research_results JSONB DEFAULT '[]',
    typography_research JSONB DEFAULT '{}',
    color_research JSONB DEFAULT '{}',
    pattern_research JSONB DEFAULT '{}',
    
    -- Selected mood board
    selected_moodboard_id BIGINT,     -- FK added after moodboards table
    
    -- Approved style guide
    approved_style_guide_id BIGINT,   -- FK added after style_guides table
    
    -- Progress tracking
    current_phase VARCHAR(50) DEFAULT 'intake',
    phase_progress INTEGER DEFAULT 0,  -- 0-100
    phase_message TEXT,
    
    -- Cost tracking
    gemini_pro_tokens INTEGER DEFAULT 0,
    gemini_flash_tokens INTEGER DEFAULT 0,
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_duration_seconds INTEGER,
    
    -- Error handling
    error_message TEXT,
    last_checkpoint VARCHAR(50),       -- Resume point if failed
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_sessions_project 
ON muse_research_sessions(project_id);

CREATE INDEX IF NOT EXISTS idx_muse_sessions_status 
ON muse_research_sessions(session_status);

-- ============================================================================
-- 2. INSPIRATION INPUTS
-- User-provided images and links for research
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_inspiration_inputs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    
    -- Input type
    input_type VARCHAR(20) NOT NULL CHECK (input_type IN ('image', 'url')),
    
    -- For images
    image_data TEXT,                   -- Base64 encoded image
    image_filename TEXT,
    image_mime_type VARCHAR(50),
    
    -- For URLs
    url TEXT,
    url_screenshot TEXT,               -- Base64 screenshot of the URL
    url_title TEXT,
    
    -- User annotation
    user_notes TEXT,                   -- What they like about this
    focus_elements TEXT[],             -- 'colors', 'typography', 'layout', 'animation'
    
    -- Gemini analysis
    analysis_complete BOOLEAN DEFAULT FALSE,
    gemini_analysis JSONB DEFAULT '{}',
    extracted_colors JSONB DEFAULT '[]',    -- Array of hex codes
    typography_notes TEXT,
    layout_notes TEXT,
    motion_notes TEXT,
    applicability_score INTEGER CHECK (applicability_score BETWEEN 1 AND 10),
    
    -- Curation
    is_primary BOOLEAN DEFAULT FALSE,  -- Is this the main inspiration?
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_inspiration_session 
ON muse_inspiration_inputs(session_id);

-- ============================================================================
-- 3. MOOD BOARDS
-- Generated mood board options (typically 4 per session)
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_moodboards (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    
    -- Identification
    option_number INTEGER NOT NULL CHECK (option_number BETWEEN 1 AND 10),
    title VARCHAR(255) NOT NULL,       -- "Atomic Elegance", "Retro Boldness", etc.
    description TEXT,
    
    -- Core aesthetic
    aesthetic_movement VARCHAR(100),   -- Primary design movement
    emotional_tone TEXT[],             -- Array of emotional descriptors
    
    -- Color palette (5-7 colors)
    color_palette JSONB NOT NULL,      -- {primary: "#...", secondary: "#...", accent: "#...", ...}
    color_rationale TEXT,
    
    -- Typography
    heading_font VARCHAR(100),
    heading_font_url TEXT,             -- Google Fonts URL or CDN
    body_font VARCHAR(100),
    body_font_url TEXT,
    accent_font VARCHAR(100),
    font_rationale TEXT,
    
    -- Visual elements
    imagery_style TEXT,                -- "Editorial photography", "Abstract 3D", etc.
    iconography_style TEXT,            -- "Outlined", "Filled", "Duotone", etc.
    pattern_usage TEXT,
    texture_notes TEXT,
    
    -- Layout approach
    layout_philosophy TEXT,            -- "Asymmetric bold", "Grid-based minimal", etc.
    spacing_approach TEXT,             -- "Airy", "Compact", "Balanced"
    
    -- Motion/Animation
    motion_philosophy TEXT,            -- "Subtle micro-interactions", "Dramatic reveals"
    recommended_animations TEXT[],
    
    -- Preview (visual representation)
    preview_data JSONB DEFAULT '{}',   -- Color swatches, font specimens, etc.
    preview_image TEXT,                -- Base64 generated preview image
    
    -- Selection status
    is_selected BOOLEAN DEFAULT FALSE,
    selection_notes TEXT,              -- Why user selected this
    
    -- Generation metadata
    generation_prompt TEXT,            -- The prompt used to generate this
    gemini_tokens_used INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_moodboards_session 
ON muse_moodboards(session_id);

-- Add FK for selected moodboard
ALTER TABLE muse_research_sessions 
ADD CONSTRAINT fk_selected_moodboard 
FOREIGN KEY (selected_moodboard_id) 
REFERENCES muse_moodboards(id) ON DELETE SET NULL;

-- ============================================================================
-- 4. STYLE GUIDES
-- Complete design specification generated from selected mood board
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_style_guides (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    moodboard_id BIGINT REFERENCES muse_moodboards(id) ON DELETE SET NULL,
    project_id BIGINT REFERENCES enjineer_projects(id) ON DELETE CASCADE,
    
    -- Version control
    version INTEGER DEFAULT 1,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMPTZ,
    
    -- Design tokens - Colors
    colors JSONB NOT NULL,
    -- Structure: {
    --   primary: { 50: "#...", 100: "#...", ..., 900: "#..." },
    --   secondary: {...},
    --   accent: {...},
    --   neutral: {...},
    --   semantic: { success: "#...", warning: "#...", error: "#...", info: "#..." }
    -- }
    
    -- Design tokens - Typography
    typography JSONB NOT NULL,
    -- Structure: {
    --   families: { heading: "...", body: "...", accent: "..." },
    --   scale: { xs: "0.75rem", sm: "0.875rem", ..., "6xl": "3.75rem" },
    --   weights: { light: 300, normal: 400, medium: 500, semibold: 600, bold: 700 },
    --   lineHeights: { tight: 1.25, normal: 1.5, relaxed: 1.75 },
    --   letterSpacing: { tight: "-0.025em", normal: "0", wide: "0.025em" }
    -- }
    
    -- Design tokens - Spacing
    spacing JSONB NOT NULL,
    -- Structure: { base: 4, scale: [0, 1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96] }
    
    -- Design tokens - Borders & Radii
    borders JSONB DEFAULT '{}',
    radii JSONB DEFAULT '{}',
    
    -- Design tokens - Shadows
    shadows JSONB DEFAULT '{}',
    
    -- Design tokens - Breakpoints
    breakpoints JSONB DEFAULT '{}',
    
    -- Design tokens - Animations
    animations JSONB DEFAULT '{}',
    -- Structure: {
    --   durations: { fast: "150ms", normal: "300ms", slow: "500ms" },
    --   easings: { default: "ease-out", bounce: "cubic-bezier(...)" }
    -- }
    
    -- Visual language
    imagery_guidelines TEXT,
    iconography_source VARCHAR(100),   -- "lucide", "heroicons", "phosphor", etc.
    iconography_style VARCHAR(50),     -- "outline", "solid", "duotone"
    pattern_library JSONB DEFAULT '[]',
    texture_guidelines TEXT,
    
    -- Component specifications
    component_specs JSONB DEFAULT '{}',
    -- Structure: {
    --   buttons: { variants: [...], sizes: [...], radii: "..." },
    --   cards: {...},
    --   inputs: {...},
    --   navigation: {...}
    -- }
    
    -- Layout specifications
    layout_specs JSONB DEFAULT '{}',
    
    -- Anti-patterns (what NOT to do)
    anti_patterns JSONB DEFAULT '[]',
    
    -- Implementation hints
    tailwind_config JSONB DEFAULT '{}',
    css_variables TEXT,
    implementation_notes TEXT,
    
    -- Nicole handoff
    nicole_context_summary TEXT,       -- Condensed summary for Nicole's prompt
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_style_guides_project 
ON muse_style_guides(project_id);

-- Add FK for approved style guide
ALTER TABLE muse_research_sessions 
ADD CONSTRAINT fk_approved_style_guide 
FOREIGN KEY (approved_style_guide_id) 
REFERENCES muse_style_guides(id) ON DELETE SET NULL;

-- ============================================================================
-- 5. PAGE DESIGNS
-- Full page design specifications
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_page_designs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    style_guide_id BIGINT REFERENCES muse_style_guides(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    
    -- Page identification
    page_type VARCHAR(100) NOT NULL,   -- "homepage", "about", "services", "contact", etc.
    page_title VARCHAR(255),
    
    -- Structure
    sections JSONB NOT NULL,           -- Array of section specs
    -- Structure: [
    --   { type: "hero", variant: "split", content: {...}, styling: {...} },
    --   { type: "features", variant: "bento", content: {...}, styling: {...} },
    --   ...
    -- ]
    
    -- Component usage
    components_used JSONB DEFAULT '[]',
    
    -- Responsive specifications
    desktop_notes TEXT,
    tablet_notes TEXT,
    mobile_notes TEXT,
    
    -- Interaction design
    animations JSONB DEFAULT '[]',
    micro_interactions JSONB DEFAULT '[]',
    
    -- Assets needed
    required_assets JSONB DEFAULT '[]',
    
    -- Approval
    is_approved BOOLEAN DEFAULT FALSE,
    revision_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_page_designs_style_guide 
ON muse_page_designs(style_guide_id);

-- ============================================================================
-- 6. RESEARCH EVENTS
-- Real-time progress streaming
-- ============================================================================

CREATE TABLE IF NOT EXISTS muse_research_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id BIGINT REFERENCES muse_research_sessions(id) ON DELETE CASCADE,
    
    event_type VARCHAR(100) NOT NULL,
    -- Types: phase_started, phase_progress, phase_complete, 
    --        finding_discovered, inspiration_analyzed, moodboard_generated,
    --        error_occurred, user_action_required
    
    event_data JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_muse_events_session_created 
ON muse_research_events(session_id, created_at DESC);

-- ============================================================================
-- 7. HELPER FUNCTIONS
-- ============================================================================

-- Get active research session for a project
CREATE OR REPLACE FUNCTION get_active_research_session(p_project_id BIGINT)
RETURNS TABLE(
    session_id BIGINT,
    session_status VARCHAR(50),
    current_phase VARCHAR(50),
    phase_progress INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mrs.id as session_id,
        mrs.session_status,
        mrs.current_phase,
        mrs.phase_progress
    FROM muse_research_sessions mrs
    WHERE mrs.project_id = p_project_id
      AND mrs.session_status NOT IN ('completed', 'failed', 'cancelled', 'handed_off')
    ORDER BY mrs.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Calculate total research cost for a session
CREATE OR REPLACE FUNCTION calculate_research_cost(p_session_id BIGINT)
RETURNS DECIMAL(10, 4) AS $$
DECLARE
    v_pro_tokens INTEGER;
    v_flash_tokens INTEGER;
    v_moodboard_tokens INTEGER;
    v_total_cost DECIMAL(10, 4);
BEGIN
    -- Get session tokens
    SELECT gemini_pro_tokens, gemini_flash_tokens
    INTO v_pro_tokens, v_flash_tokens
    FROM muse_research_sessions
    WHERE id = p_session_id;
    
    -- Get moodboard tokens
    SELECT COALESCE(SUM(gemini_tokens_used), 0)
    INTO v_moodboard_tokens
    FROM muse_moodboards
    WHERE session_id = p_session_id;
    
    -- Calculate cost (Gemini Pro: $0.0025/1K input, Flash: $0.000125/1K input)
    v_total_cost := (v_pro_tokens / 1000.0 * 0.0025) + 
                    (v_flash_tokens / 1000.0 * 0.000125) +
                    (v_moodboard_tokens / 1000.0 * 0.0025);
    
    RETURN v_total_cost;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. UPDATE ENJINEER_PROJECTS FOR DESIGN MODE
-- ============================================================================

ALTER TABLE enjineer_projects 
ADD COLUMN IF NOT EXISTS design_mode VARCHAR(20) DEFAULT 'quick' 
    CHECK (design_mode IN ('quick', 'research'));

ALTER TABLE enjineer_projects 
ADD COLUMN IF NOT EXISTS research_session_id BIGINT;

ALTER TABLE enjineer_projects 
ADD COLUMN IF NOT EXISTS active_style_guide_id BIGINT;

-- ============================================================================
-- 9. GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tsdbadmin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tsdbadmin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO tsdbadmin;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================


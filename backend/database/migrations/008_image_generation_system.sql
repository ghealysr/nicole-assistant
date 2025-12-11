-- ============================================
-- IMAGE GENERATION - JOBS + VARIANTS SYSTEM
-- ============================================

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
    model_key TEXT NOT NULL,  -- "recraft" | "flux_pro" | "flux_schnell" | "ideogram"
    model_version TEXT,  -- Replicate version string
    
    -- Prompts
    original_prompt TEXT NOT NULL,
    enhanced_prompt TEXT,  -- What Claude enhanced it to
    negative_prompt TEXT,
    
    -- Parameters (full JSON for reproducibility)
    parameters JSONB NOT NULL,
    
    -- Output files
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


-- Insert system presets (idempotent upsert)
INSERT INTO image_presets (user_id, preset_key, name, model_key, parameters, batch_count, use_case, is_system)
SELECT * FROM (VALUES
    (1, 'aw_logo_vector', 'AW Logo - Vector Square', 'recraft', 
     '{"style": "vector_illustration", "size": "1024x1024", "colors": ["#0066CC", "#00CCFF", "#FFFFFF"], "output_format": "png"}'::jsonb, 
     4, 'logo', TRUE),
    (1, 'grace_grit_ig', 'Grace & Grit IG Post', 'ideogram', 
     '{"aspect_ratio": "1:1", "style_type": "Design", "magic_prompt_option": "Auto"}'::jsonb, 
     1, 'social', TRUE),
    (1, 'saas_hero', 'Hero Image - SaaS Landing', 'flux_pro', 
     '{"aspect_ratio": "16:9", "steps": 28, "guidance": 3.5, "output_quality": 100}'::jsonb, 
     1, 'hero', TRUE),
    (1, 'quick_thumb', 'Quick Thumbnail - Fast', 'flux_schnell', 
     '{"aspect_ratio": "1:1", "output_quality": 90}'::jsonb, 
     1, 'thumbnail', TRUE),
    (1, 'tampa_poster', 'Tampa Brand Poster', 'ideogram', 
     '{"aspect_ratio": "2:3", "style_type": "Design"}'::jsonb, 
     1, 'poster', TRUE)
) AS v(user_id, preset_key, name, model_key, parameters, batch_count, use_case, is_system)
ON CONFLICT (user_id, preset_key) DO NOTHING;


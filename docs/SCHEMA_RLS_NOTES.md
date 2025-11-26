# Schema & RLS Completion Notes

This project currently includes a subset schema in `docs/supabase_schema.sql`. To align with the Master Plan (30 tables) and enforce RLS:

- Implement remaining tables: daily_journals, spotify_tracks, health_metrics, family_members, family_events, allowances, clients, projects, tasks, uploaded_files, photos, photo_memories, document_repository, document_chunks, generated_artifacts, saved_dashboards, sports_predictions, sports_data_cache, sports_learning_log, life_story_entries, api_logs, scheduled_jobs, nicole_reflections, etc.
- For each table:
  - `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;`
  - RLS policies for user isolation:
    - `FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)` when applicable.
  - Admin override policy for `role = 'admin'` via `USING (auth.uid() IN (SELECT id FROM users WHERE role = 'admin'))`.
- Create required indexes for common access patterns (e.g., `messages(conversation_id, created_at)`).
- Ensure enum constraints match Pydantic models (roles, memory_type, etc.).
- Set database JWT secret:
  ```sql
  ALTER DATABASE postgres SET "app.settings.jwt_secret" TO '<SUPABASE_JWT_SECRET>';
  ```

Use Supabase SQL editor to apply changes, then test RLS with two different JWTs to confirm isolation.

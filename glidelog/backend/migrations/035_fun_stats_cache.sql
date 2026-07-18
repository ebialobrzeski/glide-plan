-- Migration 035: fun_stats_cache table
--
-- Stores AI-generated humorous pilot statistics per user.
-- Cached for 24 hours; regenerated automatically after sync with new flights.

CREATE TABLE IF NOT EXISTS fun_stats_cache (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    generated_at TIMESTAMPTZ NOT NULL,
    content      JSONB       NOT NULL,   -- list of 8 stat objects {title, value, comment}
    model_used   VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fun_stats_cache_user ON fun_stats_cache(user_id);

-- Migration 027: GlideLog — connectors table
CREATE TABLE IF NOT EXISTS connectors (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                 VARCHAR(30) NOT NULL
                         CHECK (type IN ('echrono', 'leonardo', 'weglide', 'seeyou', 'manual')),
    display_name         VARCHAR(255) NOT NULL,
    base_url             VARCHAR(512),
    login_encrypted      TEXT,
    password_encrypted   TEXT,
    config               JSONB,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_at         TIMESTAMPTZ,
    last_sync_status     VARCHAR(20),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_connectors_user ON connectors (user_id);
CREATE INDEX IF NOT EXISTS idx_connectors_active ON connectors (user_id, is_active) WHERE is_active = TRUE;

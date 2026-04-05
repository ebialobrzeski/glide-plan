-- Migration 029: GlideLog — sync_log table
CREATE TABLE IF NOT EXISTS sync_log (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connector_id      UUID REFERENCES connectors(id) ON DELETE SET NULL,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,
    status            VARCHAR(20) NOT NULL DEFAULT 'running'
                      CHECK (status IN ('running', 'success', 'error')),
    message           TEXT,
    flights_imported  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sync_log_user      ON sync_log (user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_connector ON sync_log (connector_id) WHERE connector_id IS NOT NULL;

-- Migration 030: GlideLog — import_log table
CREATE TABLE IF NOT EXISTS import_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type     VARCHAR(30) NOT NULL,
    filename        VARCHAR(255),
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    flights_new     INTEGER NOT NULL DEFAULT 0,
    flights_dup     INTEGER NOT NULL DEFAULT 0,
    flights_error   INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'success'
                    CHECK (status IN ('success', 'partial', 'error')),
    message         TEXT
);

CREATE INDEX IF NOT EXISTS idx_import_log_user ON import_log (user_id, imported_at DESC);

-- Add FK from flights to import_log now that import_log exists
ALTER TABLE flights
    ADD CONSTRAINT fk_flights_import FOREIGN KEY (import_id) REFERENCES import_log(id) ON DELETE SET NULL;

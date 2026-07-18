-- Migration 028: GlideLog — flights table
CREATE TABLE IF NOT EXISTS flights (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id      VARCHAR(64),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date             DATE NOT NULL,
    aircraft_type    VARCHAR(100),
    aircraft_reg     VARCHAR(20),
    pilot            VARCHAR(255),
    instructor       VARCHAR(255),
    task             VARCHAR(100),
    launch_type      VARCHAR(10),
    takeoff_airport  VARCHAR(10),
    takeoff_time     TIME,
    landing_airport  VARCHAR(10),
    landing_time     TIME,
    flight_time_min  INTEGER,
    landings         INTEGER,
    is_instructor    BOOLEAN NOT NULL DEFAULT FALSE,
    price            NUMERIC(10, 2),
    raw_data         JSONB,
    source           VARCHAR(20) NOT NULL DEFAULT 'echrono'
                     CHECK (source IN ('echrono', 'manual', 'import')),
    connector_id     UUID REFERENCES connectors(id) ON DELETE SET NULL,
    import_id        UUID,
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_flights_user        ON flights (user_id);
CREATE INDEX IF NOT EXISTS idx_flights_date        ON flights (user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_flights_external    ON flights (external_id) WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_flights_connector   ON flights (connector_id) WHERE connector_id IS NOT NULL;

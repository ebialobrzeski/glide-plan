-- Migration 026: GlideLog — add logbook columns to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS logbook_enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS logbook_medical_expiry  DATE,
    ADD COLUMN IF NOT EXISTS logbook_license_date    DATE,
    ADD COLUMN IF NOT EXISTS logbook_launch_methods  TEXT[];

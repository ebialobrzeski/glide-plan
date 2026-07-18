-- Migration 031: pilot_profiles — child table for manually entered pilot data
--
-- Stores data that cannot be derived from flight logs and must be entered
-- manually by the pilot: medical certificates, licence details, exam records,
-- additional endorsements, and optional pre-logbook counters.
--
-- Relationship: users 1──0..1 pilot_profiles  (UNIQUE constraint on user_id)

CREATE TABLE IF NOT EXISTS pilot_profiles (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID        NOT NULL UNIQUE
                                        REFERENCES users(id) ON DELETE CASCADE,

    -- Club / home airfield
    club_name               VARCHAR(255),
    home_airfield           VARCHAR(10),        -- ICAO code e.g. 'EPBK'

    -- SPL Licence (EASA Part-FCL / SFCL)
    license_number          VARCHAR(50),
    license_date            DATE,               -- date of first issue

    -- Medical certificate (Part-MED)
    medical_class           VARCHAR(20),        -- 'LAPL' | 'Class 2' | 'Class 1'
    medical_expiry          DATE,
    medical_issue_date      DATE,

    -- Launch methods authorised by practical exam (SFCL.130)
    -- Array of codes: 'W' = winch, 'S' = aerotow, 'E' = self-launch/TMG
    launch_methods_exam     VARCHAR(5)[],

    -- Skill test / proficiency check
    skill_test_date         DATE,
    skill_test_examiner     VARCHAR(255),

    -- Additional endorsements
    has_tmg                 BOOLEAN     NOT NULL DEFAULT FALSE,  -- Touring Motor Glider
    tmg_date                DATE,

    has_aerobatics          BOOLEAN     NOT NULL DEFAULT FALSE,
    aerobatics_date         DATE,

    has_tow                 BOOLEAN     NOT NULL DEFAULT FALSE,  -- tow-plane / aerotow
    tow_date                DATE,

    -- Pre-logbook counters (manually entered for flights before this system)
    -- Stored in minutes and launches respectively, added to computed totals.
    pic_hours_pre_logbook   INTEGER,    -- PIC minutes logged before this system
    pic_launches_pre_logbook INTEGER,   -- PIC launches logged before this system

    -- Free-text notes
    notes                   TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pilot_profiles_user ON pilot_profiles(user_id);

-- Trigger: keep updated_at current
CREATE OR REPLACE FUNCTION update_pilot_profiles_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_pilot_profiles_updated_at ON pilot_profiles;
CREATE TRIGGER trg_pilot_profiles_updated_at
    BEFORE UPDATE ON pilot_profiles
    FOR EACH ROW EXECUTE FUNCTION update_pilot_profiles_updated_at();

-- Migrate existing GlideLog data from the users columns (migration 026) into
-- the new table for any users who already have data there.
INSERT INTO pilot_profiles (user_id, medical_expiry, license_date, launch_methods_exam)
SELECT
    id,
    logbook_medical_expiry,
    logbook_license_date,
    logbook_launch_methods
FROM users
WHERE
    (logbook_medical_expiry IS NOT NULL
     OR logbook_license_date IS NOT NULL
     OR logbook_launch_methods IS NOT NULL)
ON CONFLICT (user_id) DO NOTHING;

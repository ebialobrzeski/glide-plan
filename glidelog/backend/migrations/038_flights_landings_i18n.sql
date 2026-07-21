-- Migration 038: i18n key for the flights table "Landings" column
--
-- Adds the translation key used by templates/logbook/flights.html for the
-- number-of-landings column (sourced from eChronometraż "Lądowania").

-- ─────────────────────────────────────────────────────────────────────────────
-- Translation key
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translation_keys (key, default_value, category, description) VALUES
('logbook.tbl.landings', 'Landings', 'logbook.tbl', 'Flights table column: number of landings')
ON CONFLICT (key) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Polish (pl)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'pl', v FROM (VALUES
('logbook.tbl.landings', 'Lądowania')
) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;

-- ─────────────────────────────────────────────────────────────────────────────
-- German (de)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'de', v FROM (VALUES
('logbook.tbl.landings', 'Landungen')
) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;

-- ─────────────────────────────────────────────────────────────────────────────
-- Czech (cs)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'cs', v FROM (VALUES
('logbook.tbl.landings', 'Počet přistání')
) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;

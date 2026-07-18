-- Migration 037: i18n keys for pilot profile save feedback on the settings page

INSERT INTO translation_keys (key, default_value, category, description) VALUES
('logbook.settings.profile_saved',      'Profile saved',          'logbook.settings', NULL),
('logbook.settings.profile_save_error', 'Failed to save profile', 'logbook.settings', NULL)
ON CONFLICT (key) DO NOTHING;

-- Polish (pl)
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'pl', v FROM (VALUES
('logbook.settings.profile_saved',      'Profil zapisany'),
('logbook.settings.profile_save_error', 'Nie udało się zapisać profilu')
) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO NOTHING;

-- German (de)
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'de', v FROM (VALUES
('logbook.settings.profile_saved',      'Profil gespeichert'),
('logbook.settings.profile_save_error', 'Profil konnte nicht gespeichert werden')
) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO NOTHING;

-- Czech (cs)
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'cs', v FROM (VALUES
('logbook.settings.profile_saved',      'Profil uložen'),
('logbook.settings.profile_save_error', 'Profil se nepodařilo uložit')
) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO NOTHING;

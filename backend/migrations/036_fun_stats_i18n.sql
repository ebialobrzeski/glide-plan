-- Migration 036: fun_stats i18n keys
--
-- Translation keys for the "Na wesoło / Fun Stats" page.

INSERT INTO translation_keys (key, default_value, category, description) VALUES

('logbook.fun_stats.nav',               'For Fun',                              'logbook.fun_stats', NULL),
('logbook.fun_stats.page_title',        'Fun Stats',                            'logbook.fun_stats', NULL),
('logbook.fun_stats.subtitle',          'Your flights, but make it fun',        'logbook.fun_stats', NULL),
('logbook.fun_stats.generating',        'Generating your stats…',               'logbook.fun_stats', NULL),
('logbook.fun_stats.generating_hint',   'This may take a few seconds.',         'logbook.fun_stats', NULL),
('logbook.fun_stats.refresh',           'Regenerate',                           'logbook.fun_stats', NULL),
('logbook.fun_stats.refresh_unavail',   'Available again in {time}',            'logbook.fun_stats', NULL),
('logbook.fun_stats.generated_at',      'Generated at',                         'logbook.fun_stats', NULL),
('logbook.fun_stats.model_used',        'Model',                                'logbook.fun_stats', NULL),
('logbook.fun_stats.disclaimer',        'For fun only — not official statistics.', 'logbook.fun_stats', NULL),
('logbook.fun_stats.error',             'Could not load fun stats. Try again later.', 'logbook.fun_stats', NULL),
('logbook.fun_stats.no_flights',        'No flights yet — add some flights first!', 'logbook.fun_stats', NULL),
('logbook.fun_stats.timeout',           'Generation took too long. Please try again.', 'logbook.fun_stats', NULL)

ON CONFLICT (key) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- Polish (pl) translations
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'pl', v FROM (VALUES

('logbook.fun_stats.nav',               'Na wesoło'),
('logbook.fun_stats.page_title',        'Na wesoło'),
('logbook.fun_stats.subtitle',          'Twoje loty, ale z humorem'),
('logbook.fun_stats.generating',        'Generowanie statystyk…'),
('logbook.fun_stats.generating_hint',   'To może potrwać kilka sekund.'),
('logbook.fun_stats.refresh',           'Wygeneruj ponownie'),
('logbook.fun_stats.refresh_unavail',   'Dostępne ponownie za {time}'),
('logbook.fun_stats.generated_at',      'Wygenerowano'),
('logbook.fun_stats.model_used',        'Model'),
('logbook.fun_stats.disclaimer',        'Tylko dla zabawy — nie są to oficjalne statystyki.'),
('logbook.fun_stats.error',             'Nie udało się załadować statystyk. Spróbuj później.'),
('logbook.fun_stats.no_flights',        'Jeszcze brak lotów — najpierw dodaj loty!'),
('logbook.fun_stats.timeout',           'Generowanie trwało zbyt długo. Spróbuj ponownie.')

) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;


-- ─────────────────────────────────────────────────────────────────────────────
-- German (de) translations
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'de', v FROM (VALUES

('logbook.fun_stats.nav',               'Zum Spaß'),
('logbook.fun_stats.page_title',        'Spaß-Statistiken'),
('logbook.fun_stats.subtitle',          'Deine Flüge, aber mit Humor'),
('logbook.fun_stats.generating',        'Statistiken werden generiert…'),
('logbook.fun_stats.generating_hint',   'Das kann einige Sekunden dauern.'),
('logbook.fun_stats.refresh',           'Neu generieren'),
('logbook.fun_stats.refresh_unavail',   'Wieder verfügbar in {time}'),
('logbook.fun_stats.generated_at',      'Generiert am'),
('logbook.fun_stats.model_used',        'Modell'),
('logbook.fun_stats.disclaimer',        'Nur zum Spaß — keine offiziellen Statistiken.'),
('logbook.fun_stats.error',             'Spaß-Statistiken konnten nicht geladen werden. Später erneut versuchen.'),
('logbook.fun_stats.no_flights',        'Noch keine Flüge — erst Flüge hinzufügen!'),
('logbook.fun_stats.timeout',           'Generierung hat zu lange gedauert. Bitte erneut versuchen.')

) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;


-- ─────────────────────────────────────────────────────────────────────────────
-- Czech (cs) translations
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'cs', v FROM (VALUES

('logbook.fun_stats.nav',               'Pro zábavu'),
('logbook.fun_stats.page_title',        'Zábavné statistiky'),
('logbook.fun_stats.subtitle',          'Tvoje lety, ale s humorem'),
('logbook.fun_stats.generating',        'Generování statistik…'),
('logbook.fun_stats.generating_hint',   'Může to trvat několik sekund.'),
('logbook.fun_stats.refresh',           'Vygenerovat znovu'),
('logbook.fun_stats.refresh_unavail',   'Dostupné znovu za {time}'),
('logbook.fun_stats.generated_at',      'Vygenerováno'),
('logbook.fun_stats.model_used',        'Model'),
('logbook.fun_stats.disclaimer',        'Jen pro zábavu — nejde o oficiální statistiky.'),
('logbook.fun_stats.error',             'Statistiky se nepodařilo načíst. Zkuste to později.'),
('logbook.fun_stats.no_flights',        'Zatím žádné lety — nejprve přidejte lety!'),
('logbook.fun_stats.timeout',           'Generování trvalo příliš dlouho. Zkuste to znovu.')

) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;

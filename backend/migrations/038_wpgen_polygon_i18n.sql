-- Migration 038: i18n for custom polygon area selection in the waypoint generator.
-- Updates the "Select Area" tooltip (now polygon-based) and adds keys for the
-- point-by-point drawing flow.

-- ─────────────────────────────────────────────────────────────────────────────
-- New translation keys (English defaults)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translation_keys (key, default_value, category, description) VALUES
    ('wpgen.area_points',       '{n}-point area',                                                                 'wpgen', 'Selected custom area summary; {n} = number of points'),
    ('wpgen.select_start',      'Click on the map to add area points (min 3), then click Finish or double-click.', 'wpgen', 'Hint shown when polygon selection starts'),
    ('wpgen.select_hint',       'Click to add points ({n} so far). At least 3 needed.',                           'wpgen', 'Hint while placing polygon points before 3 are set; {n} = points placed'),
    ('wpgen.select_hint_ready', 'Click to add more points, or click Finish / double-click to close ({n} so far).','wpgen', 'Hint once a polygon has 3+ points; {n} = points placed'),
    ('wpgen.finish_area',       'Finish',                                                                         'wpgen', 'Button label to close the polygon while drawing'),
    ('wpgen.need_three',        'An area needs at least 3 points.',                                               'wpgen', 'Error when finishing a polygon with fewer than 3 points')
ON CONFLICT (key) DO NOTHING;

-- Updated tooltip text for the (now polygon) Select Area button
UPDATE translation_keys
   SET default_value = 'Click points on the map to outline a custom area, double-click to finish'
 WHERE key = 'wpgen.select_area_title';

-- ─────────────────────────────────────────────────────────────────────────────
-- Polish
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'pl', val FROM (VALUES
    ('wpgen.area_points',       'Obszar z {n} punktów'),
    ('wpgen.select_start',      'Klikaj na mapie, aby dodać punkty obszaru (min. 3), potem kliknij Zakończ lub kliknij dwukrotnie.'),
    ('wpgen.select_hint',       'Klikaj, aby dodać punkty (dotąd: {n}). Potrzeba co najmniej 3.'),
    ('wpgen.select_hint_ready', 'Klikaj, aby dodać kolejne punkty, albo kliknij Zakończ / kliknij dwukrotnie, aby zamknąć (dotąd: {n}).'),
    ('wpgen.finish_area',       'Zakończ'),
    ('wpgen.need_three',        'Obszar wymaga co najmniej 3 punktów.')
) AS t(key, val)
JOIN translation_keys tk ON tk.key = t.key
ON CONFLICT (key_id, language_code) DO NOTHING;

UPDATE translations SET value = 'Klikaj punkty na mapie, aby wyznaczyć własny obszar; kliknij dwukrotnie, aby zakończyć'
  FROM translation_keys tk
 WHERE translations.key_id = tk.id AND tk.key = 'wpgen.select_area_title' AND translations.language_code = 'pl';

-- ─────────────────────────────────────────────────────────────────────────────
-- German
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'de', val FROM (VALUES
    ('wpgen.area_points',       'Bereich mit {n} Punkten'),
    ('wpgen.select_start',      'Auf die Karte klicken, um Bereichspunkte zu setzen (mind. 3), dann auf Fertig klicken oder doppelklicken.'),
    ('wpgen.select_hint',       'Klicken, um Punkte zu setzen (bisher {n}). Mindestens 3 nötig.'),
    ('wpgen.select_hint_ready', 'Weitere Punkte anklicken oder auf Fertig klicken / Doppelklick zum Schließen (bisher {n}).'),
    ('wpgen.finish_area',       'Fertig'),
    ('wpgen.need_three',        'Ein Bereich braucht mindestens 3 Punkte.')
) AS t(key, val)
JOIN translation_keys tk ON tk.key = t.key
ON CONFLICT (key_id, language_code) DO NOTHING;

UPDATE translations SET value = 'Punkte auf der Karte anklicken, um einen eigenen Bereich zu umreißen; Doppelklick zum Abschließen'
  FROM translation_keys tk
 WHERE translations.key_id = tk.id AND tk.key = 'wpgen.select_area_title' AND translations.language_code = 'de';

-- ─────────────────────────────────────────────────────────────────────────────
-- Czech
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'cs', val FROM (VALUES
    ('wpgen.area_points',       'Oblast z {n} bodů'),
    ('wpgen.select_start',      'Klikáním na mapu přidávejte body oblasti (min. 3), pak klikněte na Dokončit nebo dvojklik.'),
    ('wpgen.select_hint',       'Klikáním přidávejte body (zatím {n}). Potřeba alespoň 3.'),
    ('wpgen.select_hint_ready', 'Klikáním přidávejte další body, nebo klikněte na Dokončit / dvojklikem zavřete (zatím {n}).'),
    ('wpgen.finish_area',       'Dokončit'),
    ('wpgen.need_three',        'Oblast potřebuje alespoň 3 body.')
) AS t(key, val)
JOIN translation_keys tk ON tk.key = t.key
ON CONFLICT (key_id, language_code) DO NOTHING;

UPDATE translations SET value = 'Klikáním na body na mapě vytvořte vlastní oblast; dvojklikem dokončíte'
  FROM translation_keys tk
 WHERE translations.key_id = tk.id AND tk.key = 'wpgen.select_area_title' AND translations.language_code = 'cs';

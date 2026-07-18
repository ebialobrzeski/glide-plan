-- Migration 033: GlideLog missing i18n keys
--
-- Adds translation keys that are referenced in templates but were missing from 032.
-- Also adds keys for fully-translated pages: flights, settings, connectors, admin.

-- ─────────────────────────────────────────────────────────────────────────────
-- Translation keys
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translation_keys (key, default_value, category, description) VALUES

-- Filter bar (statistics page)
('logbook.filter.range',        'Date range:',  'logbook.filter', 'Statistics page date range label'),
('logbook.filter.apply',        'Apply',        'logbook.filter', 'Apply date filter button'),
('logbook.filter.all_time',     'All time',     'logbook.filter', 'Reset filter / show all time'),

-- KPI extras (dashboard lifetime strip)
('logbook.kpi.all_time',        'All time',     'logbook.kpi', 'Lifetime totals label'),
('logbook.kpi.airtime',         'airtime',      'logbook.kpi', 'Airtime noun (after a duration value)'),
('logbook.kpi.spent',           'spent',        'logbook.kpi', 'Spent (money) noun'),
('logbook.kpi.since',           'since',        'logbook.kpi', 'Since year prefix'),

-- Statistics extras
('logbook.stats.all_time',      'All time',     'logbook.stats', 'All-time label in stats header'),
('logbook.stats.monthly_cost',  'Monthly cost (zł)', 'logbook.stats', 'Monthly cost chart title'),

-- Flights page
('logbook.flights.page_title',       'Flights',             'logbook.flights', NULL),
('logbook.flights.date_from',        'Date from',           'logbook.flights', NULL),
('logbook.flights.date_to',          'Date to',             'logbook.flights', NULL),
('logbook.flights.aircraft_type',    'Aircraft type',       'logbook.flights', NULL),
('logbook.flights.launch_method',    'Launch method',       'logbook.flights', NULL),
('logbook.flights.all',              'All',                 'logbook.flights', NULL),
('logbook.flights.winch',            'W — winch',           'logbook.flights', NULL),
('logbook.flights.aerotow',          'S — aerotow',         'logbook.flights', NULL),
('logbook.flights.electric',         'E — electric/motor',  'logbook.flights', NULL),
('logbook.flights.search',           'Search',              'logbook.flights', NULL),
('logbook.flights.clear',            'Clear',               'logbook.flights', NULL),
('logbook.flights.add_flight',       'Add flight',          'logbook.flights', NULL),
('logbook.flights.loading',          'Loading…',            'logbook.flights', NULL),
('logbook.flights.duration_min',     'Duration (min)',       'logbook.flights', NULL),
('logbook.flights.prev',             '‹ Prev',              'logbook.flights', NULL),
('logbook.flights.next',             'Next ›',              'logbook.flights', NULL),
('logbook.flights.pilot',            'Pilot',               'logbook.flights', NULL),
('logbook.flights.instructor',       'Instructor',          'logbook.flights', NULL),
('logbook.flights.takeoff_airport',  'Takeoff airport',     'logbook.flights', NULL),
('logbook.flights.landing_airport',  'Landing airport',     'logbook.flights', NULL),
('logbook.flights.takeoff_time',     'Takeoff time',        'logbook.flights', NULL),
('logbook.flights.landing_time',     'Landing time',        'logbook.flights', NULL),
('logbook.flights.flight_time_min',  'Flight time (min)',   'logbook.flights', NULL),
('logbook.flights.registration',     'Registration',        'logbook.flights', NULL),
('logbook.flights.add_modal_title',  'Add flight manually', 'logbook.flights', NULL),
('logbook.flights.delete_confirm',   'Delete this flight?', 'logbook.flights', NULL),
('logbook.flights.deleted',          'Flight deleted',      'logbook.flights', NULL),
('logbook.flights.saved',            'Flight saved',        'logbook.flights', NULL),

-- Settings page
('logbook.settings.pilot_profile',    'Pilot profile',                           'logbook.settings', NULL),
('logbook.settings.medical_expiry',   'Medical certificate expiry',              'logbook.settings', NULL),
('logbook.settings.license_date_spl', 'SPL licence date',                        'logbook.settings', NULL),
('logbook.settings.sync',             'Synchronisation',                         'logbook.settings', NULL),
('logbook.settings.sync_desc',        'To sync flights, configure a connection on the Sources page.', 'logbook.settings', NULL),
('logbook.settings.sync_now',         'Sync now',                                'logbook.settings', NULL),
('logbook.settings.sync_loading',     'Loading status…',                         'logbook.settings', NULL),
('logbook.settings.sync_none',        'No synchronisation data.',                'logbook.settings', NULL),
('logbook.settings.sync_last',        'Last sync:',                              'logbook.settings', NULL),
('logbook.settings.sync_started',     'Sync started',                            'logbook.settings', NULL),
('logbook.settings.no_sources',       'No data sources configured.',             'logbook.settings', NULL),

-- Connectors page
('logbook.connectors.title',          'Data sources',          'logbook.connectors', NULL),
('logbook.connectors.add_source',     'Add source',            'logbook.connectors', NULL),
('logbook.connectors.add_title',      'Add source',            'logbook.connectors', NULL),
('logbook.connectors.edit_title',     'Edit source',           'logbook.connectors', NULL),
('logbook.connectors.type',           'Type *',                'logbook.connectors', NULL),
('logbook.connectors.display_name',   'Display name *',        'logbook.connectors', NULL),
('logbook.connectors.url',            'System URL',            'logbook.connectors', NULL),
('logbook.connectors.login',          'Login',                 'logbook.connectors', NULL),
('logbook.connectors.password',       'Password',              'logbook.connectors', NULL),
('logbook.connectors.empty',          'No data sources configured. Add the first source.', 'logbook.connectors', NULL),
('logbook.connectors.inactive',       'inactive',              'logbook.connectors', NULL),
('logbook.connectors.last_sync',      'Last sync:',            'logbook.connectors', NULL),
('logbook.connectors.test',           'Test',                  'logbook.connectors', NULL),
('logbook.connectors.sync',           'Sync',                  'logbook.connectors', NULL),
('logbook.connectors.updated',        'Updated',               'logbook.connectors', NULL),
('logbook.connectors.deleted',        'Deleted',               'logbook.connectors', NULL),
('logbook.connectors.test_ok',        'Connection OK',         'logbook.connectors', NULL),
('logbook.connectors.test_fail',      'Connection failed',     'logbook.connectors', NULL),
('logbook.connectors.sync_started',   'Sync started',          'logbook.connectors', NULL),

-- Admin page
('logbook.admin.title',         'Admin panel',   'logbook.admin', NULL),
('logbook.admin.users',         'Users',         'logbook.admin', NULL),
('logbook.admin.email',         'Email',         'logbook.admin', NULL),
('logbook.admin.name',          'Name',          'logbook.admin', NULL),
('logbook.admin.tier',          'Tier',          'logbook.admin', NULL),
('logbook.admin.active',        'Active',        'logbook.admin', NULL),
('logbook.admin.flights_count', 'Flights',       'logbook.admin', NULL),
('logbook.admin.airtime',       'Airtime',       'logbook.admin', NULL),
('logbook.admin.deactivate',    'Deactivate',    'logbook.admin', NULL),
('logbook.admin.activate',      'Activate',      'logbook.admin', NULL),
('logbook.admin.yes',           'yes',           'logbook.admin', NULL),
('logbook.admin.no',            'no',            'logbook.admin', NULL),
('logbook.admin.updated',       'Updated',       'logbook.admin', NULL),
('logbook.admin.no_users',      'No users',      'logbook.admin', NULL),

-- Mobile nav
('logbook.nav.open_menu',   'Open menu',   'logbook.nav', 'Mobile hamburger button aria-label')

ON CONFLICT (key) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- Polish (pl) translations
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'pl', v FROM (VALUES

('logbook.filter.range',        'Zakres dat:'),
('logbook.filter.apply',        'Zastosuj'),
('logbook.filter.all_time',     'Cały czas'),

('logbook.kpi.all_time',        'Łącznie'),
('logbook.kpi.airtime',         'w powietrzu'),
('logbook.kpi.spent',           'wydane'),
('logbook.kpi.since',           'od'),

('logbook.stats.all_time',      'Łącznie'),
('logbook.stats.monthly_cost',  'Koszty miesięczne (zł)'),

('logbook.flights.page_title',       'Loty'),
('logbook.flights.date_from',        'Data od'),
('logbook.flights.date_to',          'Data do'),
('logbook.flights.aircraft_type',    'Typ statku'),
('logbook.flights.launch_method',    'Metoda startu'),
('logbook.flights.all',              'Wszystkie'),
('logbook.flights.winch',            'W — wyciągarka'),
('logbook.flights.aerotow',          'S — aerohol'),
('logbook.flights.electric',         'E — elektryczny'),
('logbook.flights.search',           'Szukaj'),
('logbook.flights.clear',            'Wyczyść'),
('logbook.flights.add_flight',       'Dodaj lot'),
('logbook.flights.loading',          'Ładowanie…'),
('logbook.flights.duration_min',     'Czas (min)'),
('logbook.flights.prev',             '‹ Wstecz'),
('logbook.flights.next',             'Dalej ›'),
('logbook.flights.pilot',            'Pilot'),
('logbook.flights.instructor',       'Instruktor'),
('logbook.flights.takeoff_airport',  'Lotnisko startu'),
('logbook.flights.landing_airport',  'Lotnisko lądowania'),
('logbook.flights.takeoff_time',     'Czas startu'),
('logbook.flights.landing_time',     'Czas lądowania'),
('logbook.flights.flight_time_min',  'Czas lotu (min)'),
('logbook.flights.registration',     'Rejestracja'),
('logbook.flights.add_modal_title',  'Ręczny wpis lotu'),
('logbook.flights.delete_confirm',   'Usunąć ten lot?'),
('logbook.flights.deleted',          'Lot usunięty'),
('logbook.flights.saved',            'Lot zapisany'),

('logbook.settings.pilot_profile',    'Profil pilota'),
('logbook.settings.medical_expiry',   'Ważność orzeczenia lekarskiego'),
('logbook.settings.license_date_spl', 'Data uzyskania licencji SPL'),
('logbook.settings.sync',             'Synchronizacja'),
('logbook.settings.sync_desc',        'Aby zsynchronizować loty, skonfiguruj połączenie na stronie Źródła danych.'),
('logbook.settings.sync_now',         'Synchronizuj teraz'),
('logbook.settings.sync_loading',     'Ładowanie statusu…'),
('logbook.settings.sync_none',        'Brak danych o synchronizacji.'),
('logbook.settings.sync_last',        'Ostatnia synchronizacja:'),
('logbook.settings.sync_started',     'Synchronizacja uruchomiona'),
('logbook.settings.no_sources',       'Brak skonfigurowanych źródeł danych.'),

('logbook.connectors.title',          'Źródła danych'),
('logbook.connectors.add_source',     'Dodaj źródło'),
('logbook.connectors.add_title',      'Dodaj źródło'),
('logbook.connectors.edit_title',     'Edytuj źródło'),
('logbook.connectors.type',           'Typ *'),
('logbook.connectors.display_name',   'Nazwa wyświetlana *'),
('logbook.connectors.url',            'URL systemu'),
('logbook.connectors.login',          'Login'),
('logbook.connectors.password',       'Hasło'),
('logbook.connectors.empty',          'Brak skonfigurowanych źródeł. Dodaj pierwsze źródło.'),
('logbook.connectors.inactive',       'nieaktywny'),
('logbook.connectors.last_sync',      'Ostatni sync:'),
('logbook.connectors.test',           'Test'),
('logbook.connectors.sync',           'Sync'),
('logbook.connectors.updated',        'Zaktualizowano'),
('logbook.connectors.deleted',        'Usunięto'),
('logbook.connectors.test_ok',        'Połączenie OK'),
('logbook.connectors.test_fail',      'Błąd połączenia'),
('logbook.connectors.sync_started',   'Synchronizacja uruchomiona'),

('logbook.admin.title',         'Panel administracyjny'),
('logbook.admin.users',         'Użytkownicy'),
('logbook.admin.email',         'Email'),
('logbook.admin.name',          'Imię'),
('logbook.admin.tier',          'Tier'),
('logbook.admin.active',        'Aktywny'),
('logbook.admin.flights_count', 'Loty'),
('logbook.admin.airtime',       'Nalot'),
('logbook.admin.deactivate',    'Dezaktywuj'),
('logbook.admin.activate',      'Aktywuj'),
('logbook.admin.yes',           'tak'),
('logbook.admin.no',            'nie'),
('logbook.admin.updated',       'Zaktualizowano'),
('logbook.admin.no_users',      'Brak użytkowników'),

('logbook.nav.open_menu',   'Otwórz menu')

) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;


-- ─────────────────────────────────────────────────────────────────────────────
-- German (de) translations
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'de', v FROM (VALUES

('logbook.filter.range',        'Zeitraum:'),
('logbook.filter.apply',        'Anwenden'),
('logbook.filter.all_time',     'Gesamtzeit'),

('logbook.kpi.all_time',        'Gesamt'),
('logbook.kpi.airtime',         'Flugzeit'),
('logbook.kpi.spent',           'ausgegeben'),
('logbook.kpi.since',           'seit'),

('logbook.stats.all_time',      'Gesamt'),
('logbook.stats.monthly_cost',  'Monatliche Kosten (PLN)'),

('logbook.flights.page_title',       'Flüge'),
('logbook.flights.date_from',        'Datum von'),
('logbook.flights.date_to',          'Datum bis'),
('logbook.flights.aircraft_type',    'Luftfahrzeugtyp'),
('logbook.flights.launch_method',    'Startmethode'),
('logbook.flights.all',              'Alle'),
('logbook.flights.winch',            'W — Winde'),
('logbook.flights.aerotow',          'S — Schlepp'),
('logbook.flights.electric',         'E — Motor'),
('logbook.flights.search',           'Suchen'),
('logbook.flights.clear',            'Zurücksetzen'),
('logbook.flights.add_flight',       'Flug hinzufügen'),
('logbook.flights.loading',          'Laden…'),
('logbook.flights.duration_min',     'Dauer (min)'),
('logbook.flights.prev',             '‹ Zurück'),
('logbook.flights.next',             'Weiter ›'),
('logbook.flights.pilot',            'Pilot'),
('logbook.flights.instructor',       'Fluglehrer'),
('logbook.flights.takeoff_airport',  'Startflugplatz'),
('logbook.flights.landing_airport',  'Landeflugplatz'),
('logbook.flights.takeoff_time',     'Startzeit'),
('logbook.flights.landing_time',     'Landezeit'),
('logbook.flights.flight_time_min',  'Flugzeit (min)'),
('logbook.flights.registration',     'Kennzeichen'),
('logbook.flights.add_modal_title',  'Flug manuell eingeben'),
('logbook.flights.delete_confirm',   'Diesen Flug löschen?'),
('logbook.flights.deleted',          'Flug gelöscht'),
('logbook.flights.saved',            'Flug gespeichert'),

('logbook.settings.pilot_profile',    'Pilotenprofil'),
('logbook.settings.medical_expiry',   'Ablaufdatum Tauglichkeitszeugnis'),
('logbook.settings.license_date_spl', 'SPL-Lizenzdatum'),
('logbook.settings.sync',             'Synchronisation'),
('logbook.settings.sync_desc',        'Um Flüge zu synchronisieren, konfigurieren Sie eine Verbindung auf der Seite Datenquellen.'),
('logbook.settings.sync_now',         'Jetzt synchronisieren'),
('logbook.settings.sync_loading',     'Status wird geladen…'),
('logbook.settings.sync_none',        'Keine Synchronisationsdaten vorhanden.'),
('logbook.settings.sync_last',        'Letzte Synchronisation:'),
('logbook.settings.sync_started',     'Synchronisation gestartet'),
('logbook.settings.no_sources',       'Keine Datenquellen konfiguriert.'),

('logbook.connectors.title',          'Datenquellen'),
('logbook.connectors.add_source',     'Quelle hinzufügen'),
('logbook.connectors.add_title',      'Quelle hinzufügen'),
('logbook.connectors.edit_title',     'Quelle bearbeiten'),
('logbook.connectors.type',           'Typ *'),
('logbook.connectors.display_name',   'Anzeigename *'),
('logbook.connectors.url',            'System-URL'),
('logbook.connectors.login',          'Anmeldename'),
('logbook.connectors.password',       'Passwort'),
('logbook.connectors.empty',          'Keine Datenquellen konfiguriert. Erste Quelle hinzufügen.'),
('logbook.connectors.inactive',       'inaktiv'),
('logbook.connectors.last_sync',      'Letzte Sync:'),
('logbook.connectors.test',           'Test'),
('logbook.connectors.sync',           'Sync'),
('logbook.connectors.updated',        'Aktualisiert'),
('logbook.connectors.deleted',        'Gelöscht'),
('logbook.connectors.test_ok',        'Verbindung OK'),
('logbook.connectors.test_fail',      'Verbindung fehlgeschlagen'),
('logbook.connectors.sync_started',   'Synchronisation gestartet'),

('logbook.admin.title',         'Administrationspanel'),
('logbook.admin.users',         'Benutzer'),
('logbook.admin.email',         'E-Mail'),
('logbook.admin.name',          'Name'),
('logbook.admin.tier',          'Stufe'),
('logbook.admin.active',        'Aktiv'),
('logbook.admin.flights_count', 'Flüge'),
('logbook.admin.airtime',       'Flugzeit'),
('logbook.admin.deactivate',    'Deaktivieren'),
('logbook.admin.activate',      'Aktivieren'),
('logbook.admin.yes',           'ja'),
('logbook.admin.no',            'nein'),
('logbook.admin.updated',       'Aktualisiert'),
('logbook.admin.no_users',      'Keine Benutzer'),

('logbook.nav.open_menu',   'Menü öffnen')

) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;


-- ─────────────────────────────────────────────────────────────────────────────
-- Czech (cs) translations
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO translations (key_id, language_code, value)
SELECT id, 'cs', v FROM (VALUES

('logbook.filter.range',        'Časové rozmezí:'),
('logbook.filter.apply',        'Použít'),
('logbook.filter.all_time',     'Vše'),

('logbook.kpi.all_time',        'Celkem'),
('logbook.kpi.airtime',         've vzduchu'),
('logbook.kpi.spent',           'utraceno'),
('logbook.kpi.since',           'od'),

('logbook.stats.all_time',      'Celkem'),
('logbook.stats.monthly_cost',  'Měsíční náklady (PLN)'),

('logbook.flights.page_title',       'Lety'),
('logbook.flights.date_from',        'Datum od'),
('logbook.flights.date_to',          'Datum do'),
('logbook.flights.aircraft_type',    'Typ letadla'),
('logbook.flights.launch_method',    'Způsob startu'),
('logbook.flights.all',              'Vše'),
('logbook.flights.winch',            'W — naviják'),
('logbook.flights.aerotow',          'S — aerovlek'),
('logbook.flights.electric',         'E — motor'),
('logbook.flights.search',           'Hledat'),
('logbook.flights.clear',            'Vymazat'),
('logbook.flights.add_flight',       'Přidat let'),
('logbook.flights.loading',          'Načítání…'),
('logbook.flights.duration_min',     'Trvání (min)'),
('logbook.flights.prev',             '‹ Zpět'),
('logbook.flights.next',             'Dále ›'),
('logbook.flights.pilot',            'Pilot'),
('logbook.flights.instructor',       'Instruktor'),
('logbook.flights.takeoff_airport',  'Letiště vzletu'),
('logbook.flights.landing_airport',  'Letiště přistání'),
('logbook.flights.takeoff_time',     'Čas vzletu'),
('logbook.flights.landing_time',     'Čas přistání'),
('logbook.flights.flight_time_min',  'Doba letu (min)'),
('logbook.flights.registration',     'Poznávací značka'),
('logbook.flights.add_modal_title',  'Ruční zadání letu'),
('logbook.flights.delete_confirm',   'Smazat tento let?'),
('logbook.flights.deleted',          'Let smazán'),
('logbook.flights.saved',            'Let uložen'),

('logbook.settings.pilot_profile',    'Profil pilota'),
('logbook.settings.medical_expiry',   'Platnost zdravotního průkazu'),
('logbook.settings.license_date_spl', 'Datum vydání licence SPL'),
('logbook.settings.sync',             'Synchronizace'),
('logbook.settings.sync_desc',        'Pro synchronizaci letů nakonfigurujte připojení na stránce Zdroje.'),
('logbook.settings.sync_now',         'Synchronizovat nyní'),
('logbook.settings.sync_loading',     'Načítání stavu…'),
('logbook.settings.sync_none',        'Žádná data o synchronizaci.'),
('logbook.settings.sync_last',        'Poslední synchronizace:'),
('logbook.settings.sync_started',     'Synchronizace spuštěna'),
('logbook.settings.no_sources',       'Žádné zdroje dat nejsou nakonfigurovány.'),

('logbook.connectors.title',          'Zdroje dat'),
('logbook.connectors.add_source',     'Přidat zdroj'),
('logbook.connectors.add_title',      'Přidat zdroj'),
('logbook.connectors.edit_title',     'Upravit zdroj'),
('logbook.connectors.type',           'Typ *'),
('logbook.connectors.display_name',   'Zobrazovaný název *'),
('logbook.connectors.url',            'URL systému'),
('logbook.connectors.login',          'Přihlášení'),
('logbook.connectors.password',       'Heslo'),
('logbook.connectors.empty',          'Žádné zdroje dat nejsou nakonfigurovány. Přidejte první zdroj.'),
('logbook.connectors.inactive',       'neaktivní'),
('logbook.connectors.last_sync',      'Poslední sync:'),
('logbook.connectors.test',           'Test'),
('logbook.connectors.sync',           'Sync'),
('logbook.connectors.updated',        'Aktualizováno'),
('logbook.connectors.deleted',        'Smazáno'),
('logbook.connectors.test_ok',        'Připojení OK'),
('logbook.connectors.test_fail',      'Připojení selhalo'),
('logbook.connectors.sync_started',   'Synchronizace spuštěna'),

('logbook.admin.title',         'Administrační panel'),
('logbook.admin.users',         'Uživatelé'),
('logbook.admin.email',         'E-mail'),
('logbook.admin.name',          'Jméno'),
('logbook.admin.tier',          'Úroveň'),
('logbook.admin.active',        'Aktivní'),
('logbook.admin.flights_count', 'Lety'),
('logbook.admin.airtime',       'Nalétáno'),
('logbook.admin.deactivate',    'Deaktivovat'),
('logbook.admin.activate',      'Aktivovat'),
('logbook.admin.yes',           'ano'),
('logbook.admin.no',            'ne'),
('logbook.admin.updated',       'Aktualizováno'),
('logbook.admin.no_users',      'Žádní uživatelé'),

('logbook.nav.open_menu',   'Otevřít menu')

) AS t(k, v)
JOIN translation_keys ON translation_keys.key = t.k
ON CONFLICT (key_id, language_code) DO UPDATE SET value = EXCLUDED.value;
